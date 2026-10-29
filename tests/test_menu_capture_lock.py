"""Menu dispatch tests: never start a real lock or take a screenshot."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import capture_screenshot
import menu_model


class MenuSessionActionTests(unittest.TestCase):
    def test_lock_uses_only_installed_manager_and_has_no_lifetime_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            launcher = home / '.local/bin/omabuntu'
            launcher.parent.mkdir(parents=True)
            launcher.write_text('#!/bin/sh\n')
            launcher.chmod(0o700)
            with patch.object(Path, 'home', return_value=home), \
                 patch.object(menu_model.subprocess, 'Popen') as spawn:
                result = menu_model.launch_session_action('omabuntu-session:lock')
            self.assertTrue(result['ok'])
            self.assertEqual(spawn.call_args.args[0], [str(launcher), 'lock', '--apply'])
            self.assertEqual(spawn.call_args.kwargs, {
                'stdin': subprocess.DEVNULL, 'stdout': subprocess.DEVNULL,
                'stderr': subprocess.DEVNULL, 'start_new_session': True})

    def test_lock_missing_manager_is_refused(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(Path, 'home', return_value=Path(directory)), \
             patch.object(menu_model.subprocess, 'Popen') as spawn:
            self.assertFalse(menu_model.launch_session_action('omabuntu-session:lock')['ok'])
            spawn.assert_not_called()

    def test_screenshot_uses_existing_capture_wrapper_without_arguments(self):
        with patch.object(capture_screenshot, 'approved_binary'), \
             patch.object(menu_model.subprocess, 'Popen') as spawn:
            result = menu_model.launch_session_action('omabuntu-session:screenshot')
        self.assertTrue(result['ok'])
        self.assertEqual(spawn.call_args.args[0],
                         [sys.executable, str(ROOT / 'tools/capture_screenshot.py')])
        self.assertNotIn('timeout', spawn.call_args.kwargs)
        self.assertTrue(spawn.call_args.kwargs['start_new_session'])

    def test_missing_omasnap_is_reported_without_launch(self):
        with patch.object(capture_screenshot, 'approved_binary',
                          side_effect=capture_screenshot.CaptureError('missing')), \
             patch.object(menu_model.subprocess, 'Popen') as spawn:
            self.assertEqual(menu_model.launch_session_action('omabuntu-session:screenshot')['error'], 'missing')
            spawn.assert_not_called()

    def test_forged_actions_and_unknown_rows_do_not_launch(self):
        with patch.object(menu_model.subprocess, 'Popen') as spawn:
            for action in ('hyprlock', 'omabuntu-session:lock;id',
                           'omabuntu-session:screenshot --save', 'omabuntu-session:logout'):
                self.assertIsNone(menu_model.ACTION_RE.fullmatch(action))
                self.assertFalse(menu_model.launch_session_action(action)['ok'])
            self.assertFalse(menu_model.run_item('system.fake', ({}, []))['ok'])
            spawn.assert_not_called()

    def test_menu_rows_dispatch_and_follow_upstream_order(self):
        items, order = menu_model.merge_menu_sources(menu_model.parse_menu_jsonc(
            (ROOT / 'config/shell/omabuntu-menu.jsonc').read_text()))
        self.assertLess(order.index('system.lock'), order.index('system.suspend'))
        with patch.object(menu_model, 'launch_session_action', return_value={'ok': True}) as launch:
            for row_id, token in [('system.lock', 'lock'), ('trigger.capture.screenshot', 'screenshot')]:
                self.assertTrue(menu_model.run_item(row_id, (items, order))['ok'])
                launch.assert_called_with('omabuntu-session:' + token)


if __name__ == '__main__':
    unittest.main()
