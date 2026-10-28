"""Manual-lock surface and launcher contracts; nothing here locks or authenticates."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import lock_session
import user_install


class ManualLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.release = Path(self.temp.name) / 'release'
        (self.release / 'lock').mkdir(parents=True)
        (self.release / 'lock/hyprlock.conf').write_bytes((ROOT / 'config/lock/hyprlock.conf').read_bytes())

    def test_reviewed_config_has_no_execution_or_pam_override(self):
        text = (ROOT / 'config/lock/hyprlock.conf').read_text()
        active = '\n'.join(line.split('#', 1)[0] for line in text.splitlines())
        lowered = active.lower()
        for forbidden in ('cmd[', 'onclick', 'exec', 'source', 'script', 'pam'):
            self.assertNotIn(forbidden, lowered)
        self.assertNotRegex(lowered, r'(?m)^\s*auth\s*\{')
        self.assertIn('background', active)
        self.assertIn('input-field', active)

    def test_config_with_action_is_rejected(self):
        path = self.release / 'lock/hyprlock.conf'
        path.write_text(path.read_text() + '\nlabel { text = cmd[update:1000] date }\n')
        with self.assertRaisesRegex(ValueError, 'execution directive'):
            lock_session.helper_config(self.release)

    def test_config_cannot_select_another_pam_service(self):
        path = self.release / 'lock/hyprlock.conf'
        path.write_text(path.read_text() + '\nauth { pam { module = login } }\n')
        with self.assertRaisesRegex(ValueError, 'PAM service'):
            lock_session.helper_config(self.release)

    def test_missing_or_linked_config_is_rejected(self):
        path = self.release / 'lock/hyprlock.conf'
        path.unlink()
        with self.assertRaises(ValueError):
            lock_session.helper_config(self.release)
        path.symlink_to(ROOT / 'config/lock/hyprlock.conf')
        with self.assertRaises(ValueError):
            lock_session.helper_config(self.release)

    def test_plan_does_not_start_a_locker(self):
        with patch.object(lock_session, 'preflight', return_value={'binary': '/usr/bin/hyprlock', 'config': 'x', 'display': 'wayland-1'}), \
             patch.object(lock_session.subprocess, 'run') as run, patch('builtins.print'):
            self.assertEqual(lock_session.main(['--release', str(self.release)]), 0)
        run.assert_not_called()

    def test_applied_locker_has_no_lifetime_limit_and_records_exit(self):
        directory = Path(self.temp.name) / 'lock-state'
        directory.mkdir()
        info = {'binary': '/usr/bin/hyprlock', 'config': 'x', 'display': 'wayland-1'}
        for returncode in (0, 1):
            with self.subTest(returncode=returncode):
                log = directory / 'output.log'
                if log.exists():
                    log.unlink()
                with patch.object(lock_session.os, 'getuid', return_value=1000), \
                     patch.object(lock_session, 'preflight', return_value=info), \
                     patch.object(lock_session, 'state_directory', return_value=directory), \
                     patch.object(lock_session.subprocess, 'run',
                                  return_value=subprocess.CompletedProcess([], returncode)) as run, \
                     patch('builtins.print'):
                    self.assertEqual(lock_session.main(['--release', str(self.release), '--apply']),
                                     0 if returncode == 0 else 1)
                run.assert_called_once()
                self.assertIsNone(run.call_args.kwargs.get('timeout'))
                self.assertEqual(run.call_args.args[0], ['/usr/bin/hyprlock', '--config', 'x'])
                self.assertEqual(run.call_args.kwargs['stdin'], subprocess.DEVNULL)
                self.assertEqual(json.loads((directory / 'result.json').read_text()), {
                    'returncode': returncode, 'status': 'exited' if returncode == 0 else 'failed'})

    def test_wrong_version_or_missing_binary_is_rejected(self):
        env = {'XDG_CURRENT_DESKTOP': 'Hyprland', 'HYPRLAND_INSTANCE_SIGNATURE': 'sig', 'WAYLAND_DISPLAY': 'wayland-1'}
        with patch.dict(os.environ, env, clear=True), patch.object(lock_session.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'not installed'):
                lock_session.preflight(self.release)
        with patch.dict(os.environ, env, clear=True), patch.object(lock_session.shutil, 'which', return_value='/usr/bin/hyprlock'), \
             patch.object(lock_session.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'Hyprlock version v0.9.5', '')):
            with self.assertRaisesRegex(ValueError, 'version differs'):
                lock_session.preflight(self.release)

    def test_lock_refuses_generic_or_gnome_session(self):
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'GNOME'}, clear=True), \
             patch.object(lock_session.shutil, 'which', return_value='/usr/bin/hyprlock'), \
             patch.object(lock_session.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'Hyprlock version v0.9.6', '')):
            with self.assertRaisesRegex(ValueError, 'Hyprland session'):
                lock_session.preflight(self.release)

    def test_existing_locker_blocks_a_second_one(self):
        env = {'XDG_CURRENT_DESKTOP': 'Hyprland', 'HYPRLAND_INSTANCE_SIGNATURE': 'sig', 'WAYLAND_DISPLAY': 'wayland-1'}
        with patch.dict(os.environ, env, clear=True), patch.object(lock_session.shutil, 'which', return_value='/usr/bin/hyprlock'), \
             patch.object(lock_session.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'Hyprlock version v0.9.6', '')), \
             patch.object(lock_session, 'Path') as fake:
            fake.return_value.__truediv__.return_value.is_socket.return_value = True
            with patch.object(lock_session.subprocess, 'check_output', return_value=b'[]'):
                with self.assertRaisesRegex(ValueError, 'live instance'):
                    lock_session.preflight(self.release)

    def test_lock_requires_apply_at_manager_level(self):
        app = user_install.Installation(Path(self.temp.name) / 'data', Path(self.temp.name) / 'state', Path(self.temp.name) / 'bin/omabuntu')
        with patch('builtins.print'), self.assertRaisesRegex(ValueError, 'requires --apply'):
            user_install.main(['--root', str(app.root), '--state', str(app.state), '--launcher', str(app.launcher), 'lock'])

    def test_installed_lock_never_uses_a_shell(self):
        text = (ROOT / 'tools/lock_session.py').read_text()
        self.assertNotIn('shell=True', text)
        self.assertNotIn('loginctl', text)
        self.assertNotIn('systemctl', text)
        self.assertNotIn('kill', text)
        self.assertIn("'--config'", text)
        self.assertIn('pgrep', text)

    def test_no_lock_or_idle_activation_is_packaged(self):
        packager = (ROOT / 'tools/package_user.py').read_text()
        self.assertNotIn('systemctl', packager)
        self.assertNotIn('hypridle', packager)
        self.assertIn("'autostart': False, 'lock_activation': False", packager)
        manager = (ROOT / 'tools/user_install.py').read_text()
        self.assertIn("meta.get('autostart') is not False", manager)
        self.assertIn("'autostart': False}", manager)
        self.assertNotIn('systemctl', manager)
        self.assertNotIn('hypridle', manager)


if __name__ == '__main__':
    unittest.main()
