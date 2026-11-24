"""Audio bridge protocol and recovery, exclusively synthetic native clients."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import audio_controls as controls
import audio_pactl as pulse
import audio_profiles as profiles
import audio_recovery as recovery
from test_audio_pactl import CONTEXT, info
from test_audio_profiles import FakeClient as ProfileClient, NAME, B

SCOPE = '1530' * 8


def raw_endpoint(name='virtual_input.fixture', serial='153', index=4):
    return {'index': index, 'name': name, 'properties': {'object.serial': serial, 'private': 'DO-NOT-PROJECT'},
            'channel_map': 'front-left,front-right', 'mute': False,
            'volume': {'front-left': {'value': 32768}, 'front-right': {'value': 16384}}}


class Native:
    def __init__(self):
        self.state = {'context': copy.deepcopy(CONTEXT), 'server': pulse.server_info(info(), CONTEXT),
                      'sources': [controls.endpoint(raw_endpoint(), 'source')],
                      'sinks': [controls.endpoint(raw_endpoint('alsa_output.fixture', '154', 5), 'sink')],
                      'default_source': 'virtual_input.fixture', 'default_sink': 'alsa_output.fixture'}
        self.writes = []
        self.reads = 0
        self.on_read = None
        self.failure = None

    def inspect_audio(self):
        self.reads += 1
        if self.on_read:
            self.on_read(self)
        return copy.deepcopy(self.state)

    def call(self, args, context):
        assert context == self.state['context']
        self.writes.append(args[:])
        if self.failure == 'before':
            raise pulse.AudioError('command-failed')
        rows = self.state['sources' if args[0].startswith('set-source-') else 'sinks']
        row = next(r for r in rows if r['name'] == args[1])
        if self.failure != 'ignore':
            if args[0].endswith('-volume'):
                row['levels'] = list(map(int, args[2:])); row['volume'] = max(row['levels']) / 65536
            else:
                row['muted'] = args[2] == '1'
        if self.failure == 'after':
            raise pulse.AudioError('command-timeout')
        return b''


class AudioControlsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'state'
        self.native, self.profile_client = Native(), ProfileClient()
        self.profile = profiles.Backend(self.profile_client, self.root)
        self.backend = controls.Backend(self.native, self.profile, self.root)
        gate = patch.object(pulse, 'normal_user'); gate.start(); self.addCleanup(gate.stop)

    def packet(self, op='volume', **extra):
        state = self.native.state
        row = state['sources'][0]
        return {'scope': SCOPE, 'op': op, 'target': {'name': row['name'], 'serial': row['serial']},
                'expected': controls.key(SCOPE, state), 'value': 0.25, **extra}

    def change(self, packet=None):
        return controls.dispatch(self.backend, self.packet() if packet is None else packet, write=True)

    def test_inspection_is_projected_and_does_not_allocate_state(self):
        result = controls.dispatch(self.backend, {'scope': SCOPE, 'op': 'inspect'})
        self.assertEqual(len(result['key']), 64)
        self.assertFalse(result['blocked'])
        self.assertNotIn('context', result)
        self.assertNotIn('DO-NOT-PROJECT', json.dumps(result))
        self.assertFalse(self.root.exists())
        self.assertEqual(self.native.writes, [])
        self.assertEqual(self.profile_client.writes, [])

    def test_endpoint_requires_serial_channels_and_boolean_mute(self):
        for change in ({'properties': {}}, {'channel_map': 'front-left,front-left'}, {'mute': 1},
                       {'volume': {}}, {'index': True}, {'name': '../credential'}, {'properties': {'object.serial': '0'}}):
            with self.subTest(change=change), self.assertRaises(pulse.AudioError):
                controls.endpoint({**raw_endpoint(), **change}, 'source')
        result = controls.endpoint(raw_endpoint(), 'source')
        self.assertEqual(result['levels'], [32768, 16384])
        self.assertEqual(result['volume'], 0.5)

    def test_gain_preserves_balance_and_confirms_only_readback(self):
        self.assertEqual(self.change()['status'], 'observed')
        self.assertEqual(self.native.writes, [['set-source-volume', 'virtual_input.fixture', '16384', '8192']])
        record = self.backend.journal.history()[0]
        self.assertEqual(record['status'], 'confirmed')
        self.assertEqual(record['before']['sources'][0]['levels'], [32768, 16384])
        self.assertEqual(record['after']['sources'][0]['levels'], [16384, 8192])
        self.assertTrue(recovery.valid_state(record['after']))

    def test_unchanged_gain_uses_fresh_proof_without_setter_or_receipt(self):
        result = self.change(self.packet(value=0.5))
        self.assertEqual(result, {"status": "unchanged", "receipt": None})
        self.assertEqual(self.native.writes, [])
        self.assertEqual(self.backend.journal.history(), [])

    def test_zero_gain_uses_equal_channels_for_explicit_raise(self):
        row = self.native.state['sources'][0]; row['levels'] = [0, 0]; row['volume'] = 0
        self.change()
        self.assertEqual(self.native.state['sources'][0]['levels'], [16384, 16384])

    def test_out_of_range_nan_boolean_and_non_default_refused_without_setter(self):
        for value in (-1, 1.01, float('nan'), float('inf'), True, '0.4'):
            with self.subTest(value=value), self.assertRaises(pulse.AudioError):
                self.change(self.packet(value=value))
        self.native.state['default_source'] = 'other_input'
        with self.assertRaises(pulse.AudioError): self.change()
        self.assertEqual(self.native.writes, [])
        self.assertEqual(self.backend.journal.history(), [])

    def test_missing_write_grant_scope_extra_fields_and_unadmitted_ops_refused(self):
        for packet in (self.packet(scope='wrong'), self.packet(op='exec'), self.packet(extra=True),
                       {**self.packet(), 'target': {'name': 'virtual_input.fixture', 'serial': '153', 'command': 'x'}}):
            with self.subTest(packet=packet), self.assertRaises(pulse.AudioError):
                controls.dispatch(self.backend, packet, write=True)
        with self.assertRaisesRegex(pulse.AudioError, 'audio-write-grant-required'):
            controls.dispatch(self.backend, self.packet())
        self.assertEqual(self.native.writes, [])

    def test_stale_observation_owner_serial_and_default_are_refused(self):
        packet = self.packet()
        for field, value in (('serial', '999'), ('muted', True)):
            before = copy.deepcopy(self.native.state)
            self.native.state['sources'][0][field] = value
            with self.assertRaisesRegex(pulse.AudioError, 'stale-audio-observation'): self.change(packet)
            self.native.state = before
        self.native.state['context']['socket_ino'] += 1
        with self.assertRaisesRegex(pulse.AudioError, 'stale-audio-observation'): self.change(packet)
        self.assertEqual(self.native.writes, [])

    def test_change_after_preparation_keeps_uncertain_evidence_and_no_setter(self):
        def drift(native):
            if native.reads == 2: native.state['sources'][0]['muted'] = True
        self.native.on_read = drift
        with self.assertRaisesRegex(pulse.AudioError, 'audio-state-changed-after-prepare'): self.change()
        self.assertEqual(self.native.writes, [])
        self.assertEqual(self.backend.journal.history()[0]['status'], 'prepared')

    def test_setter_error_and_bad_readback_keep_prepared_without_retry(self):
        for failure in ('before', 'after', 'ignore'):
            with self.subTest(failure=failure):
                self.native.failure = failure
                self.native.state['sources'][0].update(levels=[32768, 16384], volume=0.5)
                with self.assertRaises(pulse.AudioError): self.change()
                self.assertEqual(self.backend.journal.history()[-1]['status'], 'prepared')
                calls = len(self.native.writes)
                with self.assertRaisesRegex(pulse.AudioError, 'audio-recovery-required'): self.change()
                self.assertEqual(len(self.native.writes), calls)
                self.backend.acknowledge(self.backend.journal.history()[-1]['id'])
        self.assertEqual(len(self.native.writes), 3)

    def test_explicit_acknowledgement_is_not_restoration_and_needs_latest_token(self):
        self.native.failure = 'after'
        with self.assertRaises(pulse.AudioError): self.change()
        token = self.backend.journal.history()[0]['id']
        for kwargs in ({}, {'acknowledge': True}):
            with self.assertRaises(pulse.AudioError):
                controls.dispatch(self.backend, {'scope': SCOPE, 'op': 'ack-control', 'transaction': '00000099'}, **kwargs)
        result = controls.dispatch(self.backend, {'scope': SCOPE, 'op': 'ack-control', 'transaction': token}, acknowledge=True)
        self.assertFalse(result['restored'])
        self.assertEqual(self.backend.journal.history()[0]['status'], 'acknowledged')
        self.assertEqual(len(self.native.writes), 1)
        self.assertEqual(self.native.state['sources'][0]['volume'], 0.25)

    def test_direct_combined_mute_records_both_and_partial_failure_is_not_compensated(self):
        sink = self.native.state['sinks'][0]
        packet = self.packet(op='master', value=True, output={'name': sink['name'], 'serial': sink['serial'], 'selected': sink['name']})
        self.change(packet)
        self.assertEqual([r[0] for r in self.native.writes], ['set-sink-mute', 'set-source-mute'])
        self.assertEqual(len(self.backend.journal.history()[0]['changes']), 2)
        self.native.failure = 'after'
        packet = self.packet(op='master', value=False, output=packet['output'])
        with self.assertRaises(pulse.AudioError): self.change(packet)
        self.assertEqual(len(self.native.writes), 3)
        self.assertFalse(self.native.state['sinks'][0]['muted'])
        self.assertTrue(self.native.state['sources'][0]['muted'])

    def test_unproved_asynchronous_dsp_combined_target_is_refused(self):
        sink = self.native.state['sinks'][0]
        self.native.state['default_sink'] = 'custom_dsp'
        with self.assertRaises(pulse.AudioError):
            self.change(self.packet(op='master', value=True, output={'name': sink['name'], 'serial': sink['serial'], 'selected': 'custom_dsp'}))
        self.assertEqual(self.native.writes, [])
        self.assertEqual(self.backend.journal.history(), [])

    def test_uncertain_controls_block_original_manual_profile_backend_too(self):
        review = self.profile.review(NAME, B)
        self.native.failure = 'after'
        with self.assertRaises(pulse.AudioError): self.change()
        with self.assertRaisesRegex(pulse.AudioError, 'audio-recovery-required'):
            self.profile.apply(review, review['digest'])
        self.assertEqual(self.profile_client.writes, [])

    def test_pending_profiles_block_controls_and_profile_restore_checks_controls(self):
        review = self.profile.review(NAME, B)
        self.profile_client.fail = 'after'
        with self.assertRaises(pulse.AudioError): self.profile.apply(review, review['digest'])
        with self.assertRaisesRegex(pulse.AudioError, 'pending-profile-recovery'): self.change()
        self.assertEqual(self.native.writes, [])

    def test_profile_review_scope_and_explicit_apply_restore_surface(self):
        packet = {'scope': SCOPE, 'op': 'review-profile', 'card': NAME, 'profile': B,
                  'card_identity': {'index': 7, 'serial': '70'}, 'expected': controls.key(SCOPE, self.native.state)}
        reviewed = controls.dispatch(self.backend, packet)
        self.assertEqual(self.profile_client.writes, [])
        apply = {'scope': SCOPE, 'op': 'apply-profile', **reviewed, 'digest': reviewed['review']['digest']}
        with self.assertRaises(pulse.AudioError): controls.dispatch(self.backend, apply)
        with self.assertRaisesRegex(pulse.AudioError, 'stale-profile-ui-review'):
            controls.dispatch(self.backend, {**apply, 'scope': 'abcdef01' * 4}, write=True)
        result = controls.dispatch(self.backend, apply, write=True)
        self.assertEqual(self.profile_client.writes, [B])
        self.assertEqual(result['status'], 'profile-observed')
        history = controls.dispatch(self.backend, {'scope': SCOPE, 'op': 'history'})
        token = history['profile_history'][-1]['id']
        controls.dispatch(self.backend, {'scope': SCOPE, 'op': 'restore-profile', 'transaction': token}, write=True)
        self.assertEqual(len(self.profile_client.writes), 2)

    def test_profile_review_refuses_recycled_card_and_mixed_inventory_owner(self):
        packet = {'scope': SCOPE, 'op': 'review-profile', 'card': NAME, 'profile': B,
                  'card_identity': {'index': 7, 'serial': '70'}, 'expected': controls.key(SCOPE, self.native.state)}
        self.profile_client.raw['properties']['object.serial'] = '71'
        with self.assertRaisesRegex(pulse.AudioError, 'stale-profile-card-or-audio-owner'):
            controls.dispatch(self.backend, packet)
        self.profile_client.context['socket_ino'] += 1
        with self.assertRaisesRegex(pulse.AudioError, 'audio-owner-changed-between-inventories'):
            self.backend.inspect(SCOPE)
        self.assertEqual(self.profile_client.writes, [])
        self.assertFalse(self.root.exists())

    def test_master_toggle_refuses_a_stale_visual_mute_decision(self):
        sink = self.native.state['sinks'][0]
        with self.assertRaisesRegex(pulse.AudioError, 'audio-master-state-changed'):
            self.change(self.packet(op='master', value=False,
                output={'name': sink['name'], 'serial': sink['serial'], 'selected': sink['name']}))
        self.assertEqual(self.native.writes, [])
        self.assertEqual(self.backend.journal.history(), [])

    def test_corrupt_linked_wrong_mode_and_out_of_order_receipts_block_writes(self):
        self.change()
        path = self.backend.journal.root / '00000001.json'
        data = path.read_bytes()
        os.chmod(path, 0o644)
        with self.assertRaises(pulse.AudioError): self.change()
        os.chmod(path, 0o600)
        path.write_bytes(b'{}')
        with self.assertRaises(pulse.AudioError): self.change()
        path.write_bytes(data)
        path.rename(path.with_name('00000002.json'))
        with self.assertRaises(pulse.AudioError): self.change()
        self.assertEqual(len(self.native.writes), 1)

    def test_channel_map_change_during_gain_readback_is_uncertain(self):
        def change_channels(native):
            if native.reads == 3:
                native.state['sources'][0]['channels'].reverse()
        self.native.on_read = change_channels
        with self.assertRaisesRegex(pulse.AudioError, 'audio-readback-uncertain'): self.change()
        self.assertEqual(len(self.native.writes), 1)
        self.assertEqual(self.backend.journal.history()[0]['status'], 'prepared')

    def test_profile_restore_waits_for_explicit_control_acknowledgement(self):
        review = self.profile.review(NAME, B)
        result = self.profile.apply(review, review['digest'])
        self.native.failure = 'after'
        with self.assertRaises(pulse.AudioError): self.change()
        with self.assertRaisesRegex(pulse.AudioError, 'audio-recovery-required'):
            self.profile.restore(result['transaction'])
        self.assertEqual(self.profile_client.writes, [B])
        self.backend.acknowledge(self.backend.journal.history()[0]['id'])
        self.profile.restore(result['transaction'])
        self.assertEqual(len(self.profile_client.writes), 2)

    def test_private_modes_and_nonblocking_locks(self):
        with self.backend.journal.lock():
            with self.assertRaisesRegex(pulse.AudioError, 'audio-operation-busy'):
                with self.backend.journal.lock(): pass
        with self.profile.store.locked():
            with self.assertRaisesRegex(pulse.AudioError, 'profile-operation-busy'): self.change()
        self.change()
        self.assertEqual(self.backend.journal.root.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in self.backend.journal.root.iterdir()))

    def test_cli_grants_and_closed_json_with_no_host_commands(self):
        def invoke(args, packet):
            stream = io.BytesIO()
            with patch.object(sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(json.dumps(packet).encode()))), \
                    patch.object(sys, 'stdout', SimpleNamespace(buffer=stream)):
                status = controls.main(args, self.backend)
            return status, json.loads(stream.getvalue())
        status, result = invoke([], {'scope': SCOPE, 'op': 'inspect'})
        self.assertEqual(status, 1); self.assertFalse(result['ok']); self.assertEqual(self.native.reads, 0)
        grants = ['--allow-existing-user-audio-queries', '--allow-local-socket-activation-risk']
        status, result = invoke(grants, {'scope': SCOPE, 'op': 'inspect'})
        self.assertEqual(status, 0); self.assertEqual(result['scope'], SCOPE)
        status, _ = invoke(grants, self.packet())
        self.assertEqual(status, 1); self.assertEqual(self.native.writes, [])
        status, result = invoke(grants + ['--apply-user-audio'], self.packet())
        self.assertEqual(status, 0); self.assertTrue(result['ok'])


class AudioClientProtocolTests(unittest.TestCase):
    def client(self, mutate=None):
        self.calls = []
        source = raw_endpoint()
        sink = raw_endpoint('alsa_output.fixture', '154', 5)
        server = {**info(), 'default_source_name': source['name'], 'default_sink_name': sink['name']}
        payloads = [server, [source], [sink], copy.deepcopy(server)]
        if mutate: mutate(payloads)
        def runner(argv):
            self.calls.append(argv)
            return json.dumps(payloads[len(self.calls) - 1]).encode()
        return controls.Client(runner=runner, probe=lambda: copy.deepcopy(CONTEXT))

    def test_fixed_json_queries_and_no_raw_private_metadata(self):
        result = self.client().inspect_audio()
        self.assertEqual(len(self.calls), 4)
        self.assertTrue(all(c[:2] == ['/usr/bin/pactl', '--server=unix:' + CONTEXT['socket']] for c in self.calls))
        self.assertTrue(all('--format=json' in c for c in self.calls))
        self.assertTrue(all(c[c.index('--') + 1] in ('info', 'list') for c in self.calls))
        self.assertNotIn('DO-NOT-PROJECT', json.dumps(result))
        self.assertNotIn('PRIVATE-USER', json.dumps(result))
        self.assertTrue(recovery.valid_state(result))

    def test_duplicate_name_serial_index_and_changed_default_are_refused(self):
        for mutate in (lambda p: p[1].append(copy.deepcopy(p[1][0])),
                       lambda p: p[3].update(default_source_name='changed'),
                       lambda p: p[3].update(cookie='dead:beef')):
            with self.subTest(mutate=mutate), self.assertRaises(pulse.AudioError):
                self.client(mutate).inspect_audio()

    def test_unadmitted_commands_never_reach_runner(self):
        client = self.client()
        for args in (['set-card-profile', 'x', 'off'], ['load-module', 'x'], ['set-source-volume', 'x', '200%'],
                     ['set-source-mute', 'x', 'toggle'], ['set-sink-volume', 'x', '1'],
                     ['set-source-volume', '../x', '1'], ['set-source-volume', 'x', '65537']):
            with self.subTest(args=args), self.assertRaises(pulse.AudioError): client.call(args, CONTEXT)
        self.assertEqual(self.calls, [])

    def test_dependency_failure_is_reported_without_installation_or_runner(self):
        with patch.object(Path, 'lstat', side_effect=FileNotFoundError), patch.object(pulse, 'command') as command:
            with self.assertRaisesRegex(pulse.AudioError, 'pactl-unavailable-no-installation-attempted'):
                controls.verified_runner(['/usr/bin/pactl', 'info'])
            command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
