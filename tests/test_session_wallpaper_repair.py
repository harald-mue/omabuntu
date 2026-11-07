"""Plan 109: isolated session actions and wallpaper transport, no live commands."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import background_backend as background
import menu_common
import power_actions as power
import user_install


class Isolated(unittest.TestCase):
    def setUp(self):
        (ROOT / 'work').mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.state = self.base / 'state'
        self.enterContext(patch.object(background, 'background_dirs', return_value=[self.base / 'pictures']))
        self.enterContext(patch.dict(os.environ, {'OMABUNTU_STATE_HOME': str(self.state)}))


class SessionActions(Isolated):
    def session(self, unit=None):
        runtime = self.base / 'rt'
        signature = 'test_signature'
        for path in (runtime / 'wayland-1', runtime / 'hypr' / signature / '.socket.sock'):
            path.parent.mkdir(parents=True, exist_ok=True)
            sock = socket.socket(socket.AF_UNIX)
            self.addCleanup(sock.close)
            # bind(2) limits the supplied sockaddr path to 108 bytes. Use a
            # relative name so deeply nested clean exports remain testable.
            previous = Path.cwd()
            try:
                os.chdir(runtime)
                sock.bind(str(path.relative_to(runtime)))
            finally:
                os.chdir(previous)
        process = self.base / 'proc' / '123'
        process.mkdir(parents=True)
        (process / 'cgroup').write_text('0::/user.slice/session.slice/' + (unit or 'direct.scope') + '\n')
        env = {'HYPRLAND_INSTANCE_SIGNATURE': signature, 'WAYLAND_DISPLAY': 'wayland-1',
               'XDG_CURRENT_DESKTOP': 'Hyprland'}
        calls = []

        def run(argv):
            calls.append(argv)
            if argv == ['hyprctl', 'instances', '-j']:
                return 0, json.dumps([{'instance': signature, 'wl_socket': 'wayland-1', 'pid': 123}])
            return 0, '123\n'

        return run, env, runtime, calls

    def resolve(self, run, env, runtime):
        return power.logout_command(run, env, proc_root=self.base / 'proc', runtime_root=runtime)

    def test_direct_logout_resolves_only_the_current_compositor(self):
        run, env, runtime, calls = self.session()
        self.assertEqual(self.resolve(run, env, runtime), ['hyprctl', 'dispatch', 'hl.dsp.exit()'])
        self.assertEqual(calls, [['hyprctl', 'instances', '-j']])

    def test_uwsm_logout_stops_only_the_verified_unit(self):
        unit = 'wayland-wm@Hyprland.desktop.service'
        run, env, runtime, calls = self.session(unit)
        self.assertEqual(self.resolve(run, env, runtime), ['systemctl', '--user', 'stop', unit])
        self.assertEqual(calls[-1], ['systemctl', '--user', 'show', unit, '--property=MainPID', '--value'])

    def test_uwsm_identity_drift_refused(self):
        run, env, runtime, _ = self.session('wayland-wm@Hyprland.service')
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            self.resolve(lambda argv: run(argv) if argv[0] == 'hyprctl' else (0, '999'), env, runtime)

    def test_gnome_tty_stale_or_missing_socket_never_dispatches(self):
        run, env, runtime, calls = self.session()
        for change in ({'XDG_CURRENT_DESKTOP': 'GNOME'}, {'WAYLAND_DISPLAY': ''},
                       {'HYPRLAND_INSTANCE_SIGNATURE': '../other'}, {'WAYLAND_DISPLAY': 'wayland-9'},
                       {'XDG_RUNTIME_DIR': '/wrong/runtime'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(run, {**env, **change}, runtime)
        self.assertEqual(calls, [])

    def test_instance_mismatch_malformed_or_duplicate_refused(self):
        run, env, runtime, _ = self.session()
        valid = {'instance': env['HYPRLAND_INSTANCE_SIGNATURE'], 'wl_socket': 'wayland-1', 'pid': 123}
        for output in ('{}', 'broken', '[]', json.dumps([valid, valid]),
                       json.dumps([{**valid, 'pid': True}]), json.dumps([{**valid, 'wl_socket': 'wayland-2'}])):
            with self.subTest(output=output), self.assertRaises(ValueError):
                self.resolve(lambda argv: (0, output), env, runtime)

    def test_fresh_and_legacy_normal_actions_do_not_read_or_rewrite_gates(self):
        for legacy in (None, {'gates': {'reboot': False, 'shutdown': False, 'logout': False, 'hibernate': True}}):
            path = self.state / 'current/power-gates.json'
            if legacy is not None:
                menu_common.write_json(path, legacy)
            before = path.read_bytes() if path.exists() else None
            calls = []
            with patch.object(power, 'gates', side_effect=AssertionError('must not read ordinary grants')), \
                 patch.object(power, 'logout_command', return_value=power.EXIT):
                for verb, expected in [('reboot', ['systemctl', 'reboot']),
                                       ('shutdown', ['systemctl', 'poweroff']),
                                       ('poweroff', ['systemctl', 'poweroff']), ('logout', power.EXIT)]:
                    self.assertTrue(power.perform(verb, root=self.state,
                        run=lambda argv: (calls.append(argv) or (0, '')))['ok'])
                    self.assertEqual(calls[-1], expected)
            self.assertEqual(path.read_bytes() if path.exists() else None, before)

    def test_sleep_stays_gated_and_executes_nothing(self):
        calls = []
        for verb in ('suspend', 'hibernate'):
            self.assertEqual(power.perform(verb, states='mem disk',
                run=lambda argv: (calls.append(argv) or (0, '')))['error'], 'gate')
        self.assertEqual(calls, [])

    def test_missing_command_timeout_and_authorization_failure_are_visible(self):
        for error in (FileNotFoundError('missing systemctl'), subprocess.TimeoutExpired('systemctl', 10)):
            with patch.object(power, 'live_run', side_effect=error):
                self.assertFalse(power.perform('reboot')['ok'])
        result = power.perform('reboot', run=lambda argv: (1, 'Access denied by policy'))
        self.assertIn('Access denied', result['message'])

    def test_zero_exit_dispatcher_error_is_not_logout_success(self):
        with patch.object(power, 'logout_command', return_value=power.EXIT):
            result = power.perform('logout', run=lambda argv: (0, 'Invalid dispatcher'))
        self.assertFalse(result['ok'])
        self.assertIn('Invalid dispatcher', result['message'])

    def test_live_runner_rejects_wildcards_foreign_units_and_arbitrary_argv(self):
        for argv in ([], ['uwsm', 'stop'], ['systemctl', '--user', 'stop', 'wayland-wm@*.service'],
                     ['systemctl', '--user', 'stop', 'gnome-session.service'],
                     ['hyprctl', 'dispatch', 'exit'], ['systemctl', 'reboot', '--force']):
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                power.live_run(argv)


class WallpaperRepair(Isolated):
    def setUp(self):
        super().setUp()
        self.assets = self.base / 'assets'
        self.image = self.assets / 'tokyo-night' / 'one.webp'
        self.image.parent.mkdir(parents=True)
        self.image.write_bytes(b'fixture-not-decoded')
        self.calls = []
        self.active = {}

    def daemon(self, argv, timeout=5):
        self.calls.append(argv)
        if argv[1] == 'monitors':
            return 0, '[{"name":"Virtual-1"},{"name":"DP-1"}]'
        if argv[2] == 'wallpaper':
            name, path = argv[3].split(',', 1)
            self.active[name] = path
            return 0, ''
        if argv[2] == 'listactive':
            return 0, '\n'.join(name + ': ' + path for name, path in self.active.items())
        raise AssertionError(argv)

    def test_no_selected_theme_still_lists_downloaded_images(self):
        self.assertEqual(background.rows(dirs=[], root=self.state, assets=self.assets)[0]['value'], str(self.image))

    def test_contained_picker_stages_current_menu_imports(self):
        import check_image_picker
        for name in ('appearance_backend.py', 'dock_state.py', 'menu_update.py'):
            self.assertIn(name, check_image_picker.HELPERS)

    def test_each_output_receives_and_reports_the_selected_image(self):
        result = background.apply_background(str(self.image), run=self.daemon)
        self.assertTrue(result['ok'])
        self.assertTrue(result['active_reported'])
        self.assertEqual(set(self.active), {'Virtual-1', 'DP-1'})
        self.assertNotIn('rendering_verified', result)

    def test_record_and_restore_preserve_choice_and_report_specific_failures(self):
        def failure(argv, timeout=5):
            return self.daemon(argv, timeout) if argv[1] == 'monitors' else (1, 'wire handshake failed')
        result = background.set_background(str(self.image), dirs=[], root=self.state,
                                           assets=self.assets, run=failure)
        self.assertTrue(result['ok'])  # Selection was saved, not rendered.
        self.assertFalse(result['applied'])
        self.assertIn('handshake', result['message'])
        recorded = (self.state / 'current/background.json').read_bytes()
        result = background.restore_background(root=self.state, assets=self.assets, run=self.daemon)
        self.assertTrue(result['ok'])
        self.assertEqual((self.state / 'current/background.json').read_bytes(), recorded)

    def test_no_legacy_fallback_for_connection_handshake_or_image_errors(self):
        for message in ('failed to connect to hyprpaper', 'wire handshake failed',
                        'Invalid path', 'invalid hyprpaper request', 'EGL_NOT_INITIALIZED'):
            calls = []
            def run(argv, timeout=5):
                calls.append(argv)
                return (0, '[{"name":"Virtual-1"}]') if argv[1] == 'monitors' else (1, message)
            result = background.apply_background(str(self.image), run=run)
            self.assertFalse(result['ok'])
            self.assertIn(message, result['message'])
            self.assertEqual(len(calls), 2)

    def test_zero_exit_error_reply_is_not_success(self):
        def run(argv, timeout=5):
            return (0, '[{"name":"Virtual-1"}]') if argv[1] == 'monitors' else (0, 'error: Invalid path')
        self.assertFalse(background.apply_background(str(self.image), run=run)['ok'])

    def test_accepted_without_active_target_is_not_reported_applied(self):
        def run(argv, timeout=5):
            return (0, '') if argv[1:] == ['hyprpaper', 'listactive'] else self.daemon(argv, timeout)
        result = background.apply_background(str(self.image), run=run)
        self.assertEqual(result['error'], 'not-active')
        self.assertTrue(result['accepted'])

    def test_wrong_image_on_one_output_is_visible(self):
        def run(argv, timeout=5):
            if argv[1:] == ['hyprpaper', 'listactive']:
                return 0, 'Virtual-1: ' + str(self.image) + '\nDP-1: /old/image.webp'
            return self.daemon(argv, timeout)
        self.assertIn('DP-1', background.apply_background(str(self.image), run=run)['message'])

    def test_old_status_query_refusal_does_not_claim_target_verification(self):
        def run(argv, timeout=5):
            if argv[1:] == ['hyprpaper', 'listactive']:
                return 0, 'error: invalid hyprpaper request'
            return self.daemon(argv, timeout)
        result = background.apply_background(str(self.image), run=run)
        self.assertTrue(result['ok'])
        self.assertIsNone(result['active_reported'])

    def test_failed_status_query_retains_the_error(self):
        def run(argv, timeout=5):
            if argv[1:] == ['hyprpaper', 'listactive']:
                return 1, 'wire handshake failed'
            return self.daemon(argv, timeout)
        self.assertIn('wire handshake failed', background.apply_background(str(self.image), run=run)['message'])

    def test_login_cli_opts_into_bounded_readiness_retry(self):
        with patch.object(background, 'restore_background', return_value={'ok': True}) as restore, \
             patch('builtins.print'):
            self.assertEqual(background.main(['restore']), 0)
        restore.assert_called_once_with(wait_seconds=8)

    def test_invalid_selection_is_not_recorded_or_published(self):
        invalid = self.image.with_name('comma,image.webp')
        invalid.write_bytes(b'fixture')
        with patch.object(background, 'publish_lock_background') as publish:
            result = background.set_background(str(invalid), dirs=[], root=self.state,
                                               assets=self.assets, run=self.daemon)
        self.assertFalse(result['ok'])
        publish.assert_not_called()
        self.assertFalse((self.state / 'current/background.json').exists())
        self.assertEqual(self.calls, [])

    def test_readiness_retry_succeeds_without_service_activation(self):
        attempts = 0
        def run(argv, timeout=5):
            nonlocal attempts
            if argv[1:] == ['hyprpaper', 'wallpaper', 'Virtual-1,' + str(self.image)]:
                attempts += 1
                if attempts == 1:
                    return 1, 'failed to connect to hyprpaper'
            return self.daemon(argv, timeout)
        with patch.object(background.time, 'sleep') as sleep:
            result = background.apply_background(str(self.image), run=run, wait_seconds=1)
        self.assertTrue(result['ok'])
        sleep.assert_called_once()
        self.assertTrue(all(call[0] == 'hyprctl' for call in self.calls))

    def test_deadline_and_probe_timeout_do_not_spin_or_start_daemon(self):
        with patch.object(background.time, 'monotonic', side_effect=[0, 7]):
            result = background.apply_background(str(self.image), run=self.daemon)
        self.assertEqual(result['error'], 'timeout')
        self.assertEqual(self.calls, [])
        for error in (FileNotFoundError('hyprctl'), subprocess.TimeoutExpired('hyprctl', 5)):
            def run(argv, timeout=5):
                raise error
            self.assertFalse(background.apply_background(str(self.image), run=run)['ok'])

    def test_bad_monitor_reports_and_ambiguous_paths_are_refused(self):
        for output in ('broken', '{}', '[{"name":"bad,monitor"}]', '[{"name":null}]', '[]'):
            result = background.apply_background(str(self.image), run=lambda argv, t: (0, output))
            self.assertFalse(result['ok'])
        for path in ('/tmp/comma,image.jpg', 'relative.jpg', '/tmp/bad\nimage.jpg'):
            self.assertFalse(background.apply_background(path, run=self.daemon)['ok'])
        self.assertEqual(self.calls, [])

    def test_diagnostics_are_read_only_bounded_and_never_claim_rendering(self):
        calls = []
        def run(argv, timeout):
            calls.append((argv, timeout))
            if argv[0] == 'journalctl':
                return 0, 'EGL_NOT_INITIALIZED GBM failed to create screen'
            if argv[0] == 'hyprpaper':
                raise FileNotFoundError('hyprpaper')
            if argv[0] == 'systemctl':
                raise subprocess.TimeoutExpired(argv, timeout)
            return 0, ''
        before = self.state.exists()
        result = background.diagnose(run=run, root=self.state)
        self.assertTrue(result['read_only'])
        self.assertFalse(result['rendering_verified'])
        self.assertFalse(result['ok'])
        self.assertEqual(result['probes']['service']['status'], 'timeout')
        self.assertIn('egl_not_initialized', result['rendering_error_hints'])
        self.assertEqual(self.state.exists(), before)
        self.assertTrue(all(timeout <= 3 for _, timeout in calls))
        self.assertFalse(any(word in argv for argv, _ in calls
                             for word in ('start', 'stop', 'restart', 'set', 'restore')))

    def test_diagnostic_launcher_has_no_control_lock_or_state_write(self):
        app = user_install.Installation(self.base / 'data', self.state, self.base / 'bin/omabuntu')
        release = app.root / 'releases/test'
        helper = release / 'helpers/background_backend.py'
        helper.parent.mkdir(parents=True)
        helper.write_text('# fixture\n')
        done = subprocess.CompletedProcess([], 0, json.dumps({'read_only': True}), '')
        with patch.object(app, 'selected', return_value='releases/test'), \
             patch.object(user_install.subprocess, 'run', return_value=done) as run:
            self.assertTrue(app.wallpaper_status()['read_only'])
        self.assertEqual(run.call_args.args[0][-1], 'diagnose')
        self.assertEqual(run.call_args.kwargs['env']['OMABUNTU_STATE_HOME'], str(self.state))
        self.assertFalse(self.state.exists())


if __name__ == '__main__':
    unittest.main()
