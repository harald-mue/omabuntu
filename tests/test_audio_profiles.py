"""Manual profile transactions use synthetic native state, never host pactl."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import audio_pactl as pactl
import audio_profiles as profiles
from test_audio_pactl import NAME, A, B, CONTEXT, card, info

C = 'input:analog-stereo'


class FakeClient:
    def __init__(self):
        self.raw = card()
        self.raw['profiles'][C] = {'description': 'Input only', 'sinks': 0, 'sources': 1,
                                   'priority': 50, 'available': True}
        self.context = copy.deepcopy(CONTEXT)
        self.server = info()
        self.partial = False
        self.reads = 0
        self.writes = []
        self.on_read = None
        self.on_set = None
        self.fail = None
        self.other_audio_state = {'default': 'unrelated-default', 'stream': 'untouched'}

    def inspect(self):
        self.reads += 1
        if self.on_read:
            self.on_read(self)
        return {'context': copy.deepcopy(self.context),
                'server': pactl.server_info(self.server, self.context),
                'cards': [pactl.card(copy.deepcopy(self.raw))], 'partial': self.partial}

    def set_profile(self, before, profile):
        if self.on_set:
            self.on_set(self, before, profile)
        self.writes.append(profile)
        if self.fail == 'before':
            raise pactl.AudioError('command-failed')
        if self.fail != 'ignore':
            self.raw['active_profile'] = profile
        if self.fail == 'after':
            raise pactl.AudioError('command-timeout')
        if self.fail == 'interrupt':
            raise KeyboardInterrupt()


class ProfileBackendTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.client = FakeClient()
        self.backend = profiles.Backend(self.client, self.home / 'state')
        gate = patch.object(pactl, 'normal_user'); gate.start(); self.addCleanup(gate.stop)

    def review(self, profile=B):
        return self.backend.review(NAME, profile)

    def apply(self, review=None):
        review = self.review() if review is None else review
        return self.backend.apply(review, review['digest'])

    def pending(self):
        return self.backend.store.history()[-1]

    def cli(self, args):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = profiles.main(args, backend=self.backend)
        return code, json.loads(stream.getvalue())

    def test_review_is_read_only_digest_bound_and_describes_shared_scope(self):
        review = self.review()
        profiles.validate_review(review, review['digest'])
        self.assertIn('GNOME', review['notice'])
        self.assertIn('ongoing calls', review['notice'])
        self.assertEqual(review['before']['card']['active_profile'], A)
        self.assertFalse(self.backend.store.root.exists())
        self.assertEqual(self.client.writes, [])
        for private in ('PRIVATE-PROPERTY', 'PRIVATE-PORT', 'PRIVATE-USER', 'PRIVATE-HOST', 'aabb:ccdd'):
            self.assertNotIn(private, json.dumps(review))

    def test_apply_requires_matching_digest_before_native_reads_or_state_allocation(self):
        review = self.review(); reads = self.client.reads
        for approval in (None, '', '0' * 64, True):
            with self.subTest(approval=approval), self.assertRaises(pactl.AudioError):
                self.backend.apply(review, approval)
        corrupted = copy.deepcopy(review); corrupted['profile'] = C
        with self.assertRaisesRegex(pactl.AudioError, 'integrity'):
            self.backend.apply(corrupted, review['digest'])
        self.assertEqual(self.client.reads, reads)
        self.assertFalse(self.backend.store.root.exists())
        self.assertEqual(self.client.writes, [])

    def test_off_unavailable_and_missing_profiles_are_not_normal_actions(self):
        self.client.raw['profiles'][B]['available'] = False
        for choice in (B, 'off', 'not-a-profile', '--bad'):
            with self.subTest(choice=choice), self.assertRaises(pactl.AudioError):
                self.review(choice)
        self.assertEqual(self.client.writes, [])
        self.assertFalse(self.backend.store.root.exists())

    def test_noop_does_not_allocate_transaction_state(self):
        result = self.apply(self.review(A))
        self.assertEqual(result['status'], 'unchanged')
        self.assertEqual(self.client.writes, [])
        self.assertFalse(self.backend.store.root.exists())

    def test_backups_and_prepared_receipt_are_durable_before_single_native_request(self):
        observed = []
        def hook(client, before, profile):
            path, record, saved = self.pending()
            observed.append((record['status'], profile))
            self.assertEqual(saved, before)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
            for filename in ('before.json', 'transaction.json'):
                self.assertEqual(stat.S_IMODE((path / filename).stat().st_mode), 0o600)
        self.client.on_set = hook
        result = self.apply()
        self.assertEqual(observed, [('prepared', B)])
        self.assertEqual(self.client.writes, [B])
        self.assertEqual(self.client.raw['active_profile'], B)
        self.assertEqual(self.pending()[1]['status'], 'applied')
        self.assertEqual(result['status'], 'profile-observed')

    def test_drift_before_lock_does_not_create_state_or_mutate(self):
        for mutate in (lambda: self.client.raw.update(active_profile=C),
                       lambda: self.client.raw['properties'].update({'object.serial': '71'}),
                       lambda: self.client.context.update(start='200'),
                       lambda: self.client.server.update(cookie='ffff:0000'),
                       lambda: self.client.raw['profiles'][B].update(available=False)):
            review = self.review()
            saved = copy.deepcopy((self.client.raw, self.client.context, self.client.server))
            mutate()
            with self.assertRaisesRegex(pactl.AudioError, 'drift'):
                self.apply(review)
            self.client.raw, self.client.context, self.client.server = saved
        self.assertEqual(self.client.writes, [])
        self.assertFalse(self.backend.store.root.exists())

    def test_lock_recheck_and_final_prepared_recheck_refuse_external_changes(self):
        for change_at, expected in [(3, None), (4, 'cancelled')]:
            with self.subTest(change_at=change_at):
                backend = profiles.Backend(FakeClient(), self.home / str(change_at))
                review = backend.review(NAME, B)
                def drift(client):
                    if client.reads == change_at:
                        client.raw['active_profile'] = C
                backend.client.on_read = drift
                with self.assertRaisesRegex(pactl.AudioError, 'drift'):
                    backend.apply(review, review['digest'])
                self.assertEqual(backend.client.writes, [])
                history = backend.store.history()
                self.assertEqual(history[-1][1]['status'] if history else None, expected)

    def test_partial_inventory_never_authorizes_mutation(self):
        review = self.review(); self.client.partial = True
        with self.assertRaisesRegex(pactl.AudioError, 'partial-card-inventory'):
            self.apply(review)
        self.assertEqual(self.client.writes, [])
        self.assertFalse(self.backend.store.root.exists())

    def test_confirmed_request_restores_only_prior_profile_not_other_audio_state(self):
        result = self.apply()
        self.client.other_audio_state['default'] = 'later-unrelated-default'
        restored = self.backend.restore(result['transaction'])
        self.assertEqual(restored['status'], 'previous-profile-observed')
        self.assertEqual(self.client.writes, [B, A])
        self.assertEqual(self.client.other_audio_state, {'default': 'later-unrelated-default', 'stream': 'untouched'})
        self.assertEqual(self.pending()[1]['status'], 'restored')
        self.assertTrue((self.pending()[0] / 'before.json').exists())

    def test_original_off_state_can_be_restored_but_cannot_be_requested_normally(self):
        self.client.raw['active_profile'] = 'off'
        applied = self.apply()
        self.backend.restore(applied['transaction'])
        self.assertEqual(self.client.writes, [B, 'off'])
        self.assertEqual(self.client.raw['active_profile'], 'off')

    def test_failure_before_or_after_request_never_automatically_compensates(self):
        for failure, expected in [('before', A), ('after', B), ('ignore', A)]:
            with self.subTest(failure=failure):
                client = FakeClient(); backend = profiles.Backend(client, self.home / failure)
                review = backend.review(NAME, B); client.fail = failure
                with self.assertRaises(pactl.AudioError) as caught:
                    backend.apply(review, review['digest'])
                self.assertIsNotNone(caught.exception.transaction)
                self.assertEqual(client.writes, [B])
                self.assertEqual(client.raw['active_profile'], expected)
                self.assertEqual(backend.store.history()[-1][1]['status'], 'prepared')
                with self.assertRaisesRegex(pactl.AudioError, 'pending-profile-recovery'):
                    backend.apply(review, review['digest'])
                client.fail = None
                backend.restore(caught.exception.transaction)
                self.assertEqual(client.writes, [B, A] if expected == B else [B])
                self.assertEqual(backend.store.history()[-1][1]['status'], 'restored')

    def test_interruption_retains_prepared_receipt_and_never_replays(self):
        review = self.review(); self.client.fail = 'interrupt'
        with self.assertRaises(KeyboardInterrupt):
            self.apply(review)
        self.assertEqual(self.client.writes, [B])
        self.assertEqual(self.pending()[1]['status'], 'prepared')
        with self.assertRaisesRegex(pactl.AudioError, 'pending-profile-recovery'):
            self.review()

    def test_apply_receipt_failure_after_rename_keeps_pending_and_does_not_undo_profile(self):
        writer = self.backend.store.write
        def fail(path, value):
            writer(path, value)
            if value.get('status') == 'applied':
                raise OSError('fixture directory fsync failure')
        with patch.object(self.backend.store, 'write', side_effect=fail), self.assertRaises(pactl.AudioError):
            self.apply()
        self.assertEqual(self.client.writes, [B])
        self.assertEqual(self.client.raw['active_profile'], B)
        self.assertEqual(self.pending()[1]['status'], 'prepared')

    def test_restore_receipt_failure_can_be_reconciled_without_another_native_write(self):
        applied = self.apply(); writer = self.backend.store.write
        def fail(path, value):
            writer(path, value)
            if value.get('status') == 'restored':
                raise OSError('fixture restore receipt failure')
        with patch.object(self.backend.store, 'write', side_effect=fail), self.assertRaises(pactl.AudioError):
            self.backend.restore(applied['transaction'])
        self.assertEqual(self.pending()[1]['status'], 'restore-prepared')
        self.assertEqual(self.client.writes, [B, A])
        self.backend.restore(applied['transaction'])
        self.assertEqual(self.client.writes, [B, A])
        self.assertEqual(self.pending()[1]['status'], 'restored')

    def test_prepare_failure_never_reaches_native_setter_and_orphan_blocks_operations(self):
        writer = self.backend.store.write
        def fail(path, value):
            if path.name == 'transaction.json':
                raise OSError('fixture prepared receipt failure')
            writer(path, value)
        with patch.object(self.backend.store, 'write', side_effect=fail), self.assertRaises(pactl.AudioError):
            self.apply()
        self.assertEqual(self.client.writes, [])
        with self.assertRaisesRegex(pactl.AudioError, 'incomplete-profile-journal'):
            self.backend.store.history()

    def test_restore_refuses_profile_identity_server_or_availability_drift(self):
        applied = self.apply()
        baseline = copy.deepcopy((self.client.raw, self.client.context, self.client.server))
        for mutate in (lambda: self.client.raw.update(active_profile=C),
                       lambda: self.client.raw['properties'].update({'object.serial': '71'}),
                       lambda: self.client.context.update(start='200'),
                       lambda: self.client.server.update(cookie='ffff:0000'),
                       lambda: self.client.raw['profiles'][A].update(available=False)):
            mutate()
            with self.assertRaises(pactl.AudioError):
                self.backend.restore(applied['transaction'])
            self.client.raw, self.client.context, self.client.server = copy.deepcopy(baseline)
        self.assertEqual(self.client.writes, [B])

    def test_restore_native_failure_is_pending_with_no_retry_or_compensation(self):
        applied = self.apply(); self.client.fail = 'after'
        with self.assertRaises(pactl.AudioError):
            self.backend.restore(applied['transaction'])
        self.assertEqual(self.client.writes, [B, A])
        self.assertEqual(self.pending()[1]['status'], 'restore-prepared')
        self.client.fail = None
        self.backend.restore(applied['transaction'])
        self.assertEqual(self.client.writes, [B, A])

    def test_latest_first_recovery_of_stacked_changes(self):
        first = self.apply(); second = self.apply(self.review(C))
        with self.assertRaisesRegex(pactl.AudioError, 'latest-unclosed'):
            self.backend.restore(first['transaction'])
        self.backend.restore(second['transaction']); self.backend.restore(first['transaction'])
        self.assertEqual(self.client.writes, [B, C, B, A])

    def test_recovery_order_uses_receipt_sequence_not_wallclock(self):
        first = self.apply()
        older_date = profiles.datetime.datetime(2000, 1, 1, tzinfo=profiles.datetime.timezone.utc)
        with patch.object(profiles.datetime, 'datetime') as clock:
            clock.now.return_value = older_date
            second = self.apply(self.review(C))
        self.assertLess(second['transaction'], first['transaction'])
        with self.assertRaisesRegex(pactl.AudioError, 'latest-unclosed'):
            self.backend.restore(first['transaction'])
        self.backend.restore(second['transaction']); self.backend.restore(first['transaction'])
        self.assertEqual(self.client.writes, [B, C, B, A])

    def test_cooperating_writer_lock_refuses_instead_of_waiting_or_replaying(self):
        review = self.review()
        with self.backend.store.locked():
            with self.assertRaisesRegex(pactl.AudioError, 'profile-operation-busy'):
                self.apply(review)
        self.assertEqual(self.client.writes, [])
        self.assertEqual(self.backend.store.history(), [])

    def test_explicit_acknowledgement_retains_backup_and_never_claims_restored(self):
        self.client.fail = 'after'
        with self.assertRaises(pactl.AudioError) as caught:
            self.apply()
        token = caught.exception.transaction; reads = self.client.reads
        result = self.backend.acknowledge(token)
        self.assertFalse(result['restored'])
        self.assertEqual(self.client.reads, reads)
        self.assertEqual(self.client.writes, [B])
        self.assertEqual(self.pending()[1]['status'], 'acknowledged')
        self.assertTrue((self.pending()[0] / 'before.json').exists())

    def test_tampered_backup_receipt_mode_and_symlinks_refuse_without_native_writes(self):
        applied = self.apply(); path, record, _ = self.pending()
        before = path / 'before.json'; original = before.read_bytes()
        before.write_bytes(original + b' ')
        with self.assertRaisesRegex(pactl.AudioError, 'journal'):
            self.backend.restore(applied['transaction'])
        before.write_bytes(original); before.chmod(0o644)
        with self.assertRaisesRegex(pactl.AudioError, 'unsafe-profile-file'):
            self.backend.restore(applied['transaction'])
        before.chmod(0o600)
        receipt = path / 'transaction.json'; raw = receipt.read_bytes()
        broken = json.loads(raw); broken['profile'] = C
        receipt.write_bytes(profiles.encode(broken))
        with self.assertRaisesRegex(pactl.AudioError, 'integrity'):
            self.backend.restore(applied['transaction'])
        receipt.write_bytes(raw); saved = path / 'saved'; before.rename(saved); before.symlink_to(saved)
        with self.assertRaises(ValueError):
            self.backend.restore(applied['transaction'])
        self.assertEqual(self.client.writes, [B])

    def test_duplicate_receipt_sequence_and_hardlinked_backup_refuse_recovery(self):
        self.apply(); latest = self.apply(self.review(C))
        case, record, _ = self.pending()
        original = copy.deepcopy(record); record['sequence'] = 1
        self.backend.store.write(case / 'transaction.json', record)
        with self.assertRaisesRegex(pactl.AudioError, 'order-integrity'):
            self.backend.restore(latest['transaction'])
        self.backend.store.write(case / 'transaction.json', original)
        os.link(case / 'before.json', self.home / 'alias.json')
        with self.assertRaisesRegex(pactl.AudioError, 'unsafe-profile-file'):
            self.backend.restore(latest['transaction'])
        self.assertEqual(self.client.writes, [B, C])

    def test_history_and_invalid_restore_do_not_create_state_or_connect(self):
        self.assertEqual(self.backend.store.history(), [])
        with self.assertRaises(pactl.AudioError):
            self.backend.restore('../invalid')
        self.assertEqual(self.client.reads, 0)
        self.assertFalse(self.backend.store.root.exists())

    def test_cli_query_apply_and_acknowledgement_require_explicit_grants(self):
        for args in (['inspect'], ['review', NAME, B], ['restore', 'invalid'],
                     ['apply', '--review-file', 'not-read', '--approve-digest', '0'*64],
                     ['acknowledge', 'invalid']):
            with self.subTest(args=args):
                code, result = self.cli(args)
                self.assertEqual(code, 1)
                self.assertFalse(result['ok'])
        self.assertEqual(self.client.reads, 0)
        self.assertEqual(self.client.writes, [])
        self.assertFalse(self.backend.store.root.exists())
        code, result = self.cli(['inspect', '--query-running-user-audio'])
        self.assertEqual(code, 1)
        self.assertIn('activation-risk-consent', result['error'])
        code, result = self.cli(['inspect', '--allow-local-socket-activation-risk'])
        self.assertEqual(code, 1)
        self.assertIn('query-required', result['error'])
        self.assertEqual(self.client.reads, 0)

    def test_cli_review_apply_restore_roundtrip_and_history_no_server_read(self):
        risk = '--allow-local-socket-activation-risk'
        code, envelope = self.cli(['review', NAME, B, '--query-running-user-audio', risk])
        self.assertEqual(code, 0)
        path = self.home / 'review.json'
        self.backend.store.write(path, envelope)
        code, result = self.cli(['apply', '--review-file', str(path), '--approve-digest',
                                 envelope['result']['digest'], '--apply-user-audio', risk])
        self.assertEqual(code, 0, result)
        token = result['result']['transaction']; reads = self.client.reads
        self.assertEqual(self.cli(['history'])[0], 0)
        self.assertEqual(self.client.reads, reads)
        self.assertEqual(self.cli(['restore', token, '--apply-user-audio', risk])[0], 0)
        self.assertEqual(self.client.writes, [B, A])


if __name__ == '__main__':
    unittest.main()
