"""Closed pactl protocol/transport, using private sockets and synthetic clients only."""
import contextlib
import copy
import json
import os
from pathlib import Path
import socket
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import audio_pactl as pactl

NAME = 'alsa_card.fixture'
A = 'output:analog-stereo+input:analog-stereo'
B = 'output:hdmi-stereo+input:analog-stereo'
CONTEXT = {'exe': '/usr/bin/pipewire-pulse', 'exe_dev': 1, 'exe_ino': 2,
           'pid': 42, 'start': '100', 'uid': 1000, 'socket': '/run/user/1000/pulse/native',
           'socket_dev': 3, 'socket_ino': 4, 'listener': '500'}


def info():
    return {'server_name': 'PulseAudio (on PipeWire 1.4.9)', 'server_version': '15.0.0',
            'server_string': 'unix:' + CONTEXT['socket'], 'is_local': 'yes',
            'server_protocol_version': 35, 'cookie': 'aabb:ccdd',
            'user_name': 'PRIVATE-USER', 'host_name': 'PRIVATE-HOST'}


def card():
    return {'index': 7, 'name': NAME, 'active_profile': A,
            'properties': {'device.api': 'alsa', 'object.serial': '70', 'private': 'PRIVATE-PROPERTY'},
            'profiles': {A: {'description': 'Analog duplex', 'sinks': 1, 'sources': 1, 'priority': 100, 'available': True},
                         B: {'description': 'HDMI duplex', 'sinks': 1, 'sources': 1, 'priority': 90, 'available': True},
                         'off': {'description': 'Off', 'sinks': 0, 'sources': 0, 'priority': 0, 'available': True}},
            'ports': {'ignored': 'PRIVATE-PORT'}}


class PactlProtocolTests(unittest.TestCase):
    def client(self, entries=None, server=None):
        self.calls = []
        server = info() if server is None else server
        entries = [card()] if entries is None else entries

        def runner(argv):
            self.calls.append(argv)
            return json.dumps(entries if argv[-2:] == ['list', 'cards'] else server).encode()
        return pactl.Client(runner=runner, probe=lambda: copy.deepcopy(CONTEXT))

    def test_projection_drops_private_raw_server_and_device_metadata(self):
        result = self.client().inspect()
        self.assertEqual(result['cards'][0]['active_profile'], A)
        self.assertEqual(result['cards'][0]['serial'], '70')
        self.assertFalse(result['partial'])
        encoded = json.dumps(result)
        for secret in ('PRIVATE-USER', 'PRIVATE-HOST', 'PRIVATE-PROPERTY', 'PRIVATE-PORT', 'aabb:ccdd'):
            self.assertNotIn(secret, encoded)
        self.assertEqual(len(result['server']['instance']), 64)
        self.assertEqual(len(self.calls), 3)
        self.assertTrue(all(argv[:2] == ['/usr/bin/pactl', '--server=unix:' + CONTEXT['socket']] for argv in self.calls))
        self.assertTrue(all('--format=json' in argv for argv in self.calls))

    def test_unknown_cards_excluded_but_invalid_alsa_marks_partial(self):
        bluetooth = card(); bluetooth['name'] = 'bluez_card.fixture'; bluetooth['properties']['device.api'] = 'bluez5'
        result = self.client([bluetooth]).inspect()
        self.assertEqual(result['excluded'], {'unadmitted': 1, 'invalid': 0})
        self.assertFalse(result['partial'])
        invalid = card(); invalid['profiles'][B]['available'] = 'yes'
        result = self.client([invalid]).inspect()
        self.assertTrue(result['partial'])
        self.assertEqual(result['cards'], [])

    def test_missing_identity_and_unknown_active_profiles_refuse_projection(self):
        for mutate in (lambda row: row['properties'].pop('object.serial'),
                       lambda row: row.update(active_profile='unknown'),
                       lambda row: row.update(index=True),
                       lambda row: row['profiles'][B].update(sinks=True),
                       lambda row: row['profiles'][B].update(description='bad\x1btext')):
            value = card(); mutate(value)
            with self.subTest(value=value):
                self.assertTrue(self.client([value]).inspect()['partial'])

    def test_duplicate_card_identity_is_not_resolved_by_first_match(self):
        with self.assertRaisesRegex(pactl.AudioError, 'ambiguous-card-identity'):
            self.client([card(), card()]).inspect()

    def test_only_explicit_local_pipewire_server_schema_is_admitted(self):
        for key, value in [('is_local', 'no'), ('server_string', 'tcp:example.invalid'),
                           ('server_name', 'pulseaudio'), ('cookie', 'invalid'),
                           ('server_protocol_version', True)]:
            raw = info(); raw[key] = value
            with self.subTest(key=key), self.assertRaises(pactl.AudioError):
                self.client(server=raw).inspect()

    def test_server_cookie_and_process_changes_reject_collection(self):
        calls = []
        def runner(argv):
            calls.append(argv)
            value = info()
            if len(calls) == 3:
                value['cookie'] = 'ffff:0000'
            return json.dumps([card()] if argv[-2:] == ['list', 'cards'] else value).encode()
        with self.assertRaisesRegex(pactl.AudioError, 'server-instance-changed'):
            pactl.Client(runner, lambda: copy.deepcopy(CONTEXT)).inspect()
        client = self.client()
        client.probe = lambda: {**CONTEXT, 'start': '200'}
        with self.assertRaisesRegex(pactl.AudioError, 'server-context-changed'):
            client.call(['info'], CONTEXT)
        self.assertEqual(self.calls, [])

    def test_closed_command_allowlist_never_accepts_arbitrary_action_or_endpoint(self):
        client = self.client()
        for args in (None, ['subscribe'], ['load-module', 'anything'], ['info', '--server=bad'],
                     ['set-card-profile', 'bluez_card.fixture', A], ['set-card-profile', NAME, '--bad'],
                     ['set-card-profile', NAME, True]):
            with self.subTest(args=args), self.assertRaisesRegex(pactl.AudioError, 'unadmitted-command'):
                client.call(args, CONTEXT)
        self.assertEqual(self.calls, [])

    def test_native_profile_argv_is_one_explicit_target_and_supports_ucm_names(self):
        calls = []
        native = card()
        ucm = 'HiFi (HDMI1, Mic1, Speaker)'
        native['profiles'][ucm] = copy.deepcopy(native['profiles'][A])
        def runner(argv):
            calls.append(argv)
            if 'set-card-profile' in argv:
                return b''
            return json.dumps([native] if argv[-2:] == ['list', 'cards'] else info()).encode()
        client = pactl.Client(runner, lambda: copy.deepcopy(CONTEXT))
        snapshot = client.inspect()
        before = {'context': snapshot['context'], 'server': snapshot['server'], 'card': snapshot['cards'][0]}
        calls.clear(); client.set_profile(before, ucm)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[-1][-3:], ['set-card-profile', NAME, ucm])
        self.assertNotIn('--format=json', calls[-1])

    def test_server_magic_change_before_setter_does_not_issue_profile_request(self):
        client = self.client()
        snapshot = client.inspect()
        before = {'context': snapshot['context'], 'server': snapshot['server'], 'card': snapshot['cards'][0]}
        calls = []
        def runner(argv):
            calls.append(argv); raw = info(); raw['cookie'] = 'ffff:0000'
            return json.dumps(raw).encode()
        client.runner = runner
        with self.assertRaisesRegex(pactl.AudioError, 'server-instance-changed'):
            client.set_profile(before, B)
        self.assertEqual(len(calls), 1)
        self.assertNotIn('set-card-profile', calls[0])

    def test_duplicate_json_invalid_encoding_numbers_and_size_refuse(self):
        for raw in (b'{"x":1,"x":2}', b'NaN', b'Infinity', b'\xff', b'not json', b'x' * (pactl.MAX_OUTPUT + 1)):
            with self.subTest(raw=raw[:30]), self.assertRaises(pactl.AudioError):
                pactl.decode(raw)


class NativeContextTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root / 'r'; self.proc = self.root / 'p'
        self.runtime = self.run / str(os.getuid())
        pulse = self.runtime / 'pulse'; pulse.mkdir(parents=True); pulse.chmod(0o700)
        self.runtime.chmod(0o700)
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(self.socket.close)
        self.endpoint = pulse / 'native'
        # Keep sun_path short even inside the deeply nested clean-source copy.
        with contextlib.chdir(pulse):
            self.socket.bind('native')
        self.socket.listen(1)
        (self.proc / 'net').mkdir(parents=True)
        (self.proc / 'net/unix').write_text('Num RefCount Protocol Flags Type St Inode Path\n'
            + '0000: 00000002 00000000 00010000 0001 01 500 ' + str(self.endpoint) + '\n')
        self.process = self.proc / '42'; (self.process / 'fd').mkdir(parents=True)
        (self.process / 'stat').write_text('42 (pipewire-pulse) ' + ' '.join(['S'] + ['0'] * 18 + ['100']))
        (self.process / 'fd/3').symlink_to('socket:[500]')
        env = patch.dict(os.environ, {}, clear=True); env.start(); self.addCleanup(env.stop)
        normal = patch.object(pactl, 'normal_user'); normal.start(); self.addCleanup(normal.stop)
        identity = patch.object(pactl, 'daemon_identity', return_value={
            'exe': '/usr/bin/pipewire-pulse', 'exe_dev': 1, 'exe_ino': 2})
        identity.start(); self.addCleanup(identity.stop)

    def probe(self):
        return pactl.native_context(self.run, self.proc)

    def test_already_running_owned_listener_proof_has_process_start_and_socket_identity(self):
        result = self.probe()
        self.assertEqual(result['pid'], 42)
        self.assertEqual(result['start'], '100')
        self.assertEqual(result['listener'], '500')
        self.assertEqual(result['socket'], str(self.endpoint))

    def test_socket_without_running_daemon_fd_refuses_before_connection(self):
        (self.process / 'fd/3').unlink()
        with self.assertRaisesRegex(pactl.AudioError, 'already-running-owned-server-required'):
            self.probe()

    def test_wrong_or_ambiguous_listener_refuses(self):
        path = self.proc / 'net/unix'; original = path.read_text()
        for raw in ('', original + original):
            path.write_text(raw)
            with self.assertRaisesRegex(pactl.AudioError, 'owned-listener-required'):
                self.probe()

    def test_two_owned_processes_holding_listener_are_ambiguous(self):
        other = self.proc / '43'; (other / 'fd').mkdir(parents=True)
        (other / 'stat').write_bytes((self.process / 'stat').read_bytes())
        (other / 'fd/4').symlink_to('socket:[500]')
        with self.assertRaisesRegex(pactl.AudioError, 'already-running-owned-server-required'):
            self.probe()

    def test_private_runtime_and_canonical_environment_required(self):
        self.runtime.chmod(0o755)
        with self.assertRaisesRegex(pactl.AudioError, 'unsafe-runtime'):
            self.probe()
        self.runtime.chmod(0o700)
        for key in ('PULSE_SERVER', 'PULSE_COOKIE', 'PULSE_CLIENTCONFIG', 'PULSE_RUNTIME_PATH', 'XDG_RUNTIME_DIR'):
            with patch.dict(os.environ, {key: 'not-the-canonical-runtime'}), self.assertRaisesRegex(pactl.AudioError, 'custom-audio-environment-refused'):
                self.probe()

    def test_symbolic_socket_refuses(self):
        self.endpoint.unlink(); self.endpoint.symlink_to(self.root / 'outside')
        with self.assertRaisesRegex(pactl.AudioError, 'owned-listener-required'):
            self.probe()


class NativeCommandTests(unittest.TestCase):
    def child(self, program):
        return [sys.executable, '-I', '-S', '-c', program]

    def test_bounded_client_environment_stdin_and_output(self):
        with patch.dict(os.environ, {'PULSE_COOKIE': 'DO-NOT-EXPORT', 'LD_LIBRARY_PATH': '/invalid'}):
            result = pactl.command(self.child("import os,json,sys;print(json.dumps({'home':os.environ['HOME'],'secret':os.environ.get('PULSE_COOKIE'),'ld':os.environ.get('LD_LIBRARY_PATH'),'stdin':sys.stdin.read()}))"))
        self.assertEqual(json.loads(result), {'home': '/nonexistent', 'secret': None, 'ld': None, 'stdin': ''})

    def test_native_stderr_and_failed_client_output_are_not_exposed(self):
        with self.assertRaisesRegex(pactl.AudioError, '^command-failed$'):
            pactl.command(self.child("import sys;print('PRIVATE-STDOUT');sys.stderr.write('PRIVATE-STDERR');sys.exit(3)"))

    def test_oversized_stdout_and_stderr_stop_client(self):
        for stream, count in [('stdout', pactl.MAX_OUTPUT + 1), ('stderr', 70000)]:
            with self.subTest(stream=stream), self.assertRaisesRegex(pactl.AudioError, 'command-output-limit'):
                pactl.command(self.child("import sys;sys.%s.write('x'*%s)" % (stream, count)))

    def test_timeout_and_missing_client_are_explicit_errors(self):
        with patch.object(pactl, 'TIMEOUT', 0.02), self.assertRaisesRegex(pactl.AudioError, 'command-timeout'):
            pactl.command(self.child('import time;time.sleep(30)'))
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            with self.assertRaisesRegex(pactl.AudioError, 'command-unavailable'):
                pactl.command([str(Path(directory) / 'nonexistent-client')])

    def test_normal_user_gate_rejects_root_sudo_or_effective_uid_mismatch(self):
        with patch.dict(os.environ, {}, clear=True):
            for uid, euid in [(0, 0), (1000, 0)]:
                with patch.object(os, 'getuid', return_value=uid), patch.object(os, 'geteuid', return_value=euid), self.assertRaisesRegex(pactl.AudioError, 'normal-user-required'):
                    pactl.normal_user()
            with patch.object(os, 'getuid', return_value=1000), patch.object(os, 'geteuid', return_value=1000), patch.dict(os.environ, {'SUDO_USER': 'fixture'}), self.assertRaises(pactl.AudioError):
                pactl.normal_user()

    def test_live_executable_must_match_root_owned_installed_binary(self):
        good = SimpleNamespace(st_dev=1, st_ino=2, st_uid=0, st_mode=stat.S_IFREG | 0o755)
        for installed, accepted in [(good, True),
                (SimpleNamespace(**{**vars(good), 'st_ino': 3}), False),
                (SimpleNamespace(**{**vars(good), 'st_uid': 1000}), False),
                (SimpleNamespace(**{**vars(good), 'st_mode': stat.S_IFREG | 0o775}), False)]:
            with patch.object(os, 'readlink', return_value='/usr/bin/pipewire-pulse'), patch.object(Path, 'stat', side_effect=[good, installed]):
                self.assertEqual(pactl.daemon_identity(Path('/synthetic/42')) is not None, accepted)


if __name__ == '__main__':
    unittest.main()
