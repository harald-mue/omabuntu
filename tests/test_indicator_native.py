"""Synthetic native protocols only: never invoke host buses/controllers."""
import copy
import json
from pathlib import Path
import sys
import os
import socket
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from indicator_native import Native, NativeError, action_key


class Sunset(Native):
    def __init__(self):
        super().__init__()
        self.identity = False
        self.kelvin = 6000
        self.gamma = 87.5
        self.context = {'socket': [1, 2], 'process': {'pid': 3, 'start': '4'}}
        self.commands = []
        self.change_owner = False

    def sunset(self, command, expected=None):
        self.commands.append(command)
        if expected is not None and (expected != self.context or self.change_owner):
            raise NativeError('controller-owner-changed')
        if command == 'identity get':
            value = 'true' if self.identity else 'false'
        elif command == 'temperature':
            value = str(self.kelvin)
        elif command == 'gamma':
            value = str(self.gamma)
        elif command in ('identity true', 'identity false'):
            self.identity = command.endswith('true')
            value = 'ok'
        else:
            raise AssertionError(command)
        return value, copy.deepcopy(self.context)


class Bus(Native):
    def __init__(self):
        super().__init__()
        self.active = False
        self.owner_value = ':1.3'
        self.notification_owner = ':1.3'
        self.guid = 'a' * 32
        self.calls = []
        self.interface = '<node><interface name="org.erikreider.swaync.cc"><method name="GetDnd"><arg type="b" direction="out"/></method><method name="SetDnd"><arg type="b" direction="in"/></method></interface></node>'

    def supported_swaync(self):
        return '0.12.4-synthetic'

    def call(self, destination, path, interface, method, signature='', values=()):
        self.calls.append((destination, method, signature, values))
        if method == 'GetNameOwner':
            return {'type': 's', 'data': [self.notification_owner if values[0] == 'org.freedesktop.Notifications' else self.owner_value]}
        if method == 'GetConnectionUnixProcessID':
            return {'type': 'u', 'data': [123]}
        if method == 'GetId':
            return {'type': 's', 'data': [self.guid]}
        if method == 'Introspect':
            return {'type': 's', 'data': [self.interface]}
        if method == 'GetDnd':
            return {'type': 'b', 'data': [self.active]}
        if method == 'SetDnd':
            self.active = values == ('true',)
            return {'type': '', 'data': []}
        raise AssertionError(method)


class NativeIndicatorTests(unittest.TestCase):
    def test_colour_getters_have_no_setters_and_preserve_fractional_gamma(self):
        native = Sunset()
        value = native.read('nightlight')
        self.assertTrue(value['active'])
        self.assertEqual(value['proof']['kelvin'], 6000)
        self.assertEqual(value['proof']['gamma'], 87.5)
        self.assertEqual(native.commands, ['identity get', 'temperature', 'gamma', 'identity get'])

    def test_identity_only_setter_preserves_kelvin_gamma_and_is_not_a_toggle(self):
        native = Sunset()
        before = native.read('nightlight')
        after = native.set('nightlight', False, before)
        self.assertFalse(after['active'])
        self.assertEqual(after['proof'], before['proof'])
        self.assertEqual(native.commands.count('identity true'), 1)
        self.assertFalse(any(c in ('profile', 'reset', 'identity') or c.startswith(('gamma ', 'temperature ')) for c in native.commands))

    def test_changed_temperature_or_owner_refuses_setter(self):
        for change in ('kelvin', 'context'):
            native = Sunset()
            before = native.read('nightlight')
            if change == 'kelvin':
                native.kelvin = 6100
            else:
                native.context['process']['start'] = '99'
            with self.assertRaises(NativeError):
                native.set('nightlight', False, before)
            self.assertNotIn('identity true', native.commands)

    def test_malformed_or_inconsistent_fields_fail_closed(self):
        for field, value in [('kelvin', 999), ('kelvin', 20001), ('gamma', float('nan')), ('gamma', -1)]:
            native = Sunset()
            setattr(native, field, value)
            with self.assertRaises(NativeError):
                native.read('nightlight')
        native = Sunset()
        native.change_owner = True
        with self.assertRaises(NativeError):
            native.read('nightlight')

    @patch('indicator_native.process_identity', return_value={'pid': 123, 'start': '456', 'binary': [1, 2]})
    def test_existing_swaync_owns_both_names_and_set_goes_to_unique_owner(self, identity):
        native = Bus()
        before = native.read('dnd')
        self.assertFalse(before['active'])
        after = native.set('dnd', True, before)
        self.assertTrue(after['active'])
        setters = [c for c in native.calls if c[1] == 'SetDnd']
        self.assertEqual(setters, [(':1.3', 'SetDnd', 'b', ('true',))])
        self.assertFalse(any(c[1] in ('ToggleDnd', 'StartServiceByName', 'Notify', 'GetSubscribeData') for c in native.calls))

    @patch('indicator_native.process_identity', return_value={'pid': 123, 'start': '456'})
    def test_replaced_notification_bus_or_control_owner_never_retargets(self, identity):
        for field, value in [('owner_value', ':1.4'), ('notification_owner', ':1.5'), ('guid', 'b' * 32)]:
            native = Bus()
            before = native.read('dnd')
            setattr(native, field, value)
            with self.assertRaises(NativeError):
                native.set('dnd', True, before)
            self.assertFalse(any(c[1] == 'SetDnd' for c in native.calls))

    @patch('indicator_native.process_identity', return_value={'pid': 123, 'start': '456'})
    def test_changed_api_signature_cannot_be_used_for_actions(self, identity):
        native = Bus()
        native.interface = native.interface.replace('direction="in"', 'direction="out"')
        with self.assertRaises(NativeError):
            native.read('dnd')
        self.assertFalse(any(c[1] == 'SetDnd' for c in native.calls))

    def test_user_bus_connection_risk_requires_explicit_grant_before_probing(self):
        with patch('indicator_native.runtime') as root, patch('indicator_native.subprocess.Popen') as child:
            with self.assertRaisesRegex(NativeError, 'session-bus-connection-grant-required'):
                Native().command(['call', 'org.freedesktop.DBus'])
            root.assert_not_called()
            child.assert_not_called()

    def test_nonunique_bus_destinations_and_unknown_commands_are_rejected(self):
        with self.assertRaises(NativeError):
            Native().call('org.erikreider.swaync', '/', 'x', 'SetDnd')
        with self.assertRaises(NativeError):
            Native().sunset('reset')
        with self.assertRaises(NativeError):
            Native().read('sudo')

    def test_actual_unix_framing_half_close_and_peer_proof_with_synthetic_server(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            path = Path(directory) / 'native.sock'
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.addCleanup(server.close)
            server.bind(str(path))
            server.listen(2)
            server.settimeout(3)
            commands, errors = [], []
            model = {'identity': False}
            def serve():
                try:
                    for _ in range(13):
                        connection, _ = server.accept()
                        with connection:
                            connection.settimeout(3)
                            data = b''
                            while True:
                                part = connection.recv(1024)
                                if not part:
                                    break
                                data += part
                            command = data.decode()
                            commands.append(command)
                            if command == 'identity get':
                                reply = 'true' if model['identity'] else 'false'
                            elif command == 'temperature':
                                reply = '6000'
                            elif command == 'gamma':
                                reply = '87.500000'
                            elif command == 'identity true':
                                model['identity'] = True
                                reply = 'ok'
                            else:
                                raise AssertionError(command)
                            connection.sendall(reply.encode())
                except Exception as error:
                    errors.append(str(error))
            thread = threading.Thread(target=serve, daemon=True)
            thread.start()
            info = path.stat()
            with patch.object(Native, 'supported_sunset', return_value='0.4.0-synthetic'), patch.object(Native, 'sunset_listener', return_value={'listener': '123', 'process': {'pid': os.getpid(), 'start': 'synthetic', 'exe': '/usr/bin/hyprsunset'}}), patch.object(Native, 'sunset_path', return_value=(path, [info.st_dev, info.st_ino])), patch('indicator_native.process_identity', side_effect=lambda pid, exe: {'pid': pid, 'start': 'synthetic', 'exe': exe}):
                native = Native()
                before = native.read('nightlight')
                after = native.set('nightlight', False, before)
            thread.join(4)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(commands.count('identity true'), 1)
            self.assertFalse(after['active'])
            self.assertEqual(after['proof']['gamma'], 87.5)
            self.assertEqual(after['proof']['context']['process']['pid'], os.getpid())

    def test_real_child_output_bound_timeout_and_cleanup_with_synthetic_program(self):
        real_popen = subprocess.Popen
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            root = Path(directory)
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.addCleanup(listener.close)
            listener.bind(str(root / 'bus'))
            for program, timeout, expected in [
                ('print(\'{}\')', 2, None),
                ('import sys;sys.stderr.write("x"*70000)', 2, 'native-output-bound'),
                ('import time;time.sleep(3)', .03, 'native-timeout')]:
                children, arguments = [], []
                def spawn(args, **kwargs):
                    arguments.append((args, kwargs['env']))
                    child = real_popen(['/usr/bin/python3', '-c', program], **kwargs)
                    children.append(child)
                    return child
                with patch('indicator_native.runtime', return_value=root), patch('indicator_native.binary', return_value=[1, 2]), patch.dict(os.environ, {}, clear=True), patch('indicator_native.subprocess.Popen', side_effect=spawn), patch.object(Native, 'remaining', return_value=timeout):
                    native = Native(bus_connection_granted=True)
                    if expected:
                        with self.assertRaisesRegex(NativeError, expected):
                            native.command(['call', 'synthetic'])
                    else:
                        self.assertEqual(native.command(['call', 'synthetic']), {})
                self.assertTrue(all(child.poll() is not None for child in children))
                self.assertIn('--auto-start=no', arguments[0][0])
                self.assertEqual(set(arguments[0][1]), {'PATH', 'LANG', 'LC_ALL', 'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS'})
                self.assertNotIn('HOME', arguments[0][1])

    def test_preconnect_listener_requires_exact_running_owned_controller(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            proc = Path(directory)
            (proc / 'net').mkdir()
            unix = proc / 'net/unix'
            endpoint = socket.socket(socket.AF_UNIX)
            self.addCleanup(endpoint.close)
            inode = os.fstat(endpoint.fileno()).st_ino
            unix.write_text('000: 00000002 00000000 00010000 0001 01 ' + str(inode) + ' /fixture/native.sock\n')
            (proc / '1234/fd').mkdir(parents=True)
            (proc / '1234/comm').write_text('hyprsunset\n')
            (proc / '1234/fd/9').symlink_to('/proc/self/fd/' + str(endpoint.fileno()))
            with patch('indicator_native.process_identity', return_value={'pid': 1234, 'start': '5'}):
                result = Native().sunset_listener(Path('/fixture/native.sock'), proc)
                self.assertEqual(result, {'listener': str(inode), 'process': {'pid': 1234, 'start': '5'}})
                (proc / '1234/comm').write_text('systemd\n')
                with self.assertRaises(NativeError):
                    Native().sunset_listener(Path('/fixture/native.sock'), proc)
                (proc / '1234/comm').write_text('hyprsunset\n')
                unix.write_text(unix.read_text() * 2)
                with self.assertRaises(NativeError):
                    Native().sunset_listener(Path('/fixture/native.sock'), proc)

    def test_linux_endpoint_pin_cannot_connect_to_replacement_listener(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            path = Path(directory) / 'pin.sock'
            with socket.socket(socket.AF_UNIX) as original, socket.socket(socket.AF_UNIX) as replacement:
                original.bind(str(path)); original.listen(); original.settimeout(1)
                pinned = os.open(path, os.O_PATH | os.O_NOFOLLOW)
                try:
                    old = os.fstat(pinned).st_ino
                    path.unlink(); replacement.bind(str(path)); replacement.listen(); replacement.settimeout(.02)
                    self.assertNotEqual(path.stat().st_ino, old)
                    with socket.socket(socket.AF_UNIX) as client:
                        client.settimeout(1); client.connect('/proc/self/fd/' + str(pinned))
                        connection, _ = original.accept()
                        with connection:
                            client.sendall(b'temperature')
                            self.assertEqual(connection.recv(64), b'temperature')
                    with self.assertRaises(TimeoutError):
                        replacement.accept()
                finally:
                    os.close(pinned)

    def test_absent_running_owner_refuses_before_socket_connect(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            path = Path(directory) / 'listener.sock'
            with socket.socket(socket.AF_UNIX) as server:
                server.bind(str(path)); server.listen(); info = path.stat()
                with patch.object(Native, 'supported_sunset', return_value='0.4.0-test'), patch.object(Native, 'sunset_path', return_value=(path, [info.st_dev, info.st_ino])), patch.object(Native, 'sunset_listener', side_effect=NativeError('no-running-owner')), patch('indicator_native.socket.socket') as connect:
                    with self.assertRaises(NativeError):
                        Native().sunset('identity get')
                    connect.assert_not_called()

    def test_exact_supported_package_version_is_readonly_cached_and_fail_closed(self):
        native = Native()
        with patch.object(native, 'command', return_value='installed\t0.4.0-1ubuntu1') as command:
            self.assertEqual(native.supported_sunset(), '0.4.0-1ubuntu1')
            self.assertEqual(native.supported_sunset(), '0.4.0-1ubuntu1')
            command.assert_called_once_with([], package='hyprsunset')
        native = Native()
        with patch.object(native, 'command', return_value='installed\t0.12.4-1') as command:
            self.assertEqual(native.supported_swaync(), '0.12.4-1')
            self.assertEqual(native.supported_swaync(), '0.12.4-1')
            command.assert_called_once_with([], package='sway-notification-center')
        with patch.object(Native, 'command', return_value='installed\t0.12.5-1'), self.assertRaises(NativeError):
            Native().supported_swaync()
        for value in ('config-files\t0.4.0-1', 'installed\t0.3.0-1', 'installed\t0.5.0-1', 'installed\t0.4.0-1\nother'):
            native = Native()
            with patch.object(native, 'command', return_value=value), self.assertRaises(NativeError):
                native.supported_sunset()

    def test_provider_scope_kind_state_and_native_identity_all_bind_key(self):
        value = {'active': True, 'proof': {'owner': ':1.3'}}
        key = action_key('a' * 24, 'dnd', value)
        self.assertNotEqual(key, action_key('b' * 24, 'dnd', value))
        self.assertNotEqual(key, action_key('a' * 24, 'nightlight', value))
        self.assertNotEqual(key, action_key('a' * 24, 'dnd', {**value, 'active': False}))
        self.assertNotEqual(key, action_key('a' * 24, 'dnd', {**value, 'proof': {'owner': ':1.4'}}))


if __name__ == '__main__':
    unittest.main()
