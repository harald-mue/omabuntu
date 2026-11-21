"""User-wide button-layout contracts with a fake GSettings/dconf backend only."""
import contextlib
import io
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
import window_controls as controls
import menu_model


class Settings:
    def __init__(self):
        self.default = 'appmenu:close'
        self.user = controls.SHOW
        self.writable = True
        self.calls = []
        self.fail_write = False
        self.ignore_write = False
        self.bad_get = False
        self.bad_writable = False

    @property
    def effective(self):
        return self.default if self.user is None else self.user

    def run(self, argv, **kwargs):
        self.calls.append(list(argv))
        assert kwargs['timeout'] == 10
        assert kwargs['check'] is False
        assert 'shell' not in kwargs
        out, code = '', 0
        if argv == ['/usr/bin/gsettings', 'get', controls.SCHEMA, controls.KEY]:
            out = 'bad' if self.bad_get else repr(self.effective)
        elif argv == ['/usr/bin/gsettings', 'writable', controls.SCHEMA, controls.KEY]:
            out = 'bad' if self.bad_writable else str(self.writable).lower()
        elif argv == ['/usr/bin/dconf', 'read', controls.DCONF_KEY]:
            out = '' if self.user is None else repr(self.user)
        elif argv[:4] == ['/usr/bin/gsettings', 'set', controls.SCHEMA, controls.KEY]:
            if self.fail_write:
                code = 1
            elif not self.ignore_write:
                self.user = json.loads(argv[4])
        elif argv == ['/usr/bin/gsettings', 'reset', controls.SCHEMA, controls.KEY]:
            if self.fail_write:
                code = 1
            else:
                self.user = None
        else:
            raise AssertionError('Unexpected command: ' + repr(argv))
        return subprocess.CompletedProcess(argv, code, stdout=out, stderr='fixture failure' if code else '')

    def writes(self):
        return [call for call in self.calls if call[1] in ('set', 'reset')]


class WindowControlsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.state = self.home / 'state'
        env = {'HOME': str(self.home), 'OMABUNTU_STATE_HOME': str(self.state),
               'XDG_CURRENT_DESKTOP': 'GNOME', 'XDG_SESSION_TYPE': 'wayland',
               'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/fixture/session-bus'}
        environment = patch.dict(os.environ, env, clear=True)
        environment.start(); self.addCleanup(environment.stop)
        self.settings = Settings()
        mock = patch.object(controls.subprocess, 'run', side_effect=self.settings.run)
        mock.start(); self.addCleanup(mock.stop)
        self.items, self.order = menu_model.merge_menu_sources(menu_model.parse_menu_jsonc(
            (ROOT / 'config/shell/omabuntu-menu.jsonc').read_text()))

    def journal(self, token):
        return controls.transactions() / token / 'transaction.json'

    def test_status_and_plan_read_actual_key_create_nothing(self):
        state = controls.snapshot()
        self.assertEqual(state['effective'], controls.SHOW)
        self.assertEqual(state['scope'], 'user-wide-including-gnome')
        self.assertTrue(state['shown'])
        self.assertEqual(controls.review('hide')['after'], controls.HIDE)
        self.assertFalse(self.settings.writes())
        self.assertFalse(self.state.exists())

    def test_hide_changes_exactly_one_user_wide_key_and_records_prestate(self):
        result = controls.change('hide')
        self.assertEqual(result['status'], 'applied-user-wide')
        self.assertTrue(result['window_controls']['hidden'])
        self.assertIn('GNOME', result['message'])
        case = self.journal(result['transaction']).parent
        backup = json.loads((case / 'before.json').read_text())
        self.assertEqual(backup['effective'], controls.SHOW)
        self.assertEqual(backup['user_value'], controls.SHOW)
        self.assertEqual((case / 'before.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual(case.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.settings.writes(), [['/usr/bin/gsettings', 'set', controls.SCHEMA,
                                                 controls.KEY, json.dumps(controls.HIDE)]])

    def test_show_sets_explicit_min_max_close(self):
        self.settings.user = controls.HIDE
        controls.change('show')
        self.assertEqual(self.settings.user, controls.SHOW)

    def test_repeat_is_noop_without_new_backup(self):
        controls.change('hide')
        count = len(self.settings.writes())
        self.assertEqual(controls.change('hide')['status'], 'unchanged')
        self.assertEqual(len(self.settings.writes()), count)
        self.assertEqual(len(controls.history()), 1)

    def test_initial_show_is_noop_and_creates_nothing(self):
        self.assertEqual(controls.change('show')['status'], 'unchanged')
        self.assertFalse(self.state.exists())

    def test_restore_preserves_custom_order(self):
        self.settings.user = 'close,minimize,maximize:appmenu'
        controls.change('hide')
        controls.restore()
        self.assertEqual(self.settings.user, 'close,minimize,maximize:appmenu')
        with self.assertRaises(ValueError):
            controls.restore()

    def test_restore_removes_override_if_originally_inherited(self):
        self.settings.user = None
        controls.change('hide')
        controls.restore()
        self.assertIsNone(self.settings.user)
        self.assertEqual(self.settings.effective, self.settings.default)
        self.assertEqual(self.settings.writes()[-1][1], 'reset')

    def test_empty_layout_is_valid_and_restorable(self):
        self.settings.user = ''
        self.assertTrue(controls.snapshot()['hidden'])
        controls.change('show')
        controls.restore()
        self.assertEqual(self.settings.user, '')

    def test_restore_refuses_external_setting_change(self):
        controls.change('hide')
        self.settings.user = 'close:'
        count = len(self.settings.writes())
        with self.assertRaisesRegex(ValueError, 'externally'):
            controls.restore()
        self.assertEqual(len(self.settings.writes()), count)

    def test_restore_refuses_lost_override_even_if_effective_matches(self):
        controls.change('hide')
        self.settings.default = controls.HIDE
        self.settings.user = None
        with self.assertRaisesRegex(ValueError, 'externally'):
            controls.restore()

    def test_corrupt_backup_is_refused(self):
        result = controls.change('hide')
        (self.journal(result['transaction']).parent / 'before.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            controls.restore()
        self.assertEqual(self.settings.user, controls.HIDE)

    def test_receipt_failure_restores_live_key_and_requires_recovery(self):
        original = controls.files.atomic
        def fail(path, data, mode=0o600):
            if path.name == 'transaction.json' and json.loads(data)['status'] == 'applied':
                raise OSError('fixture receipt failure')
            return original(path, data, mode)
        with patch.object(controls.files, 'atomic', side_effect=fail):
            with self.assertRaises(OSError):
                controls.change('hide')
        self.assertEqual(self.settings.user, controls.SHOW)
        self.assertTrue(controls.snapshot()['pending_recovery'])
        with self.assertRaises(ValueError):
            controls.change('hide')
        controls.restore()
        self.assertFalse(controls.snapshot()['pending_recovery'])

    def test_interrupted_after_setting_write_can_restore(self):
        result = controls.change('hide')
        path = self.journal(result['transaction']); record = json.loads(path.read_text())
        record['status'] = 'prepared'; path.write_text(json.dumps(record))
        controls.restore()
        self.assertEqual(self.settings.user, controls.SHOW)

    def test_failed_command_is_not_reported_as_success(self):
        self.settings.fail_write = True
        with self.assertRaisesRegex(ValueError, 'command failed'):
            controls.change('hide')
        self.assertEqual(self.settings.user, controls.SHOW)
        self.assertTrue(controls.snapshot()['pending_recovery'])
        self.settings.fail_write = False
        controls.restore()

    def test_ignored_write_fails_verification(self):
        self.settings.ignore_write = True
        with self.assertRaisesRegex(ValueError, 'not confirmed'):
            controls.change('hide')
        self.assertEqual(self.settings.user, controls.SHOW)

    def test_missing_command_and_timeout_are_explicit(self):
        for failure in (FileNotFoundError(), subprocess.TimeoutExpired('gsettings', 10)):
            with self.subTest(failure=type(failure)), patch.object(controls.subprocess, 'run', side_effect=failure):
                with self.assertRaisesRegex(ValueError, 'missing or timed out'):
                    controls.snapshot()
        self.assertFalse(self.state.exists())

    def test_invalid_responses_and_nonpersistent_backend_refused(self):
        self.settings.bad_get = True
        with self.assertRaises(ValueError): controls.snapshot()
        self.settings.bad_get = False; self.settings.bad_writable = True
        with self.assertRaises(ValueError): controls.snapshot()
        self.settings.bad_writable = False
        with patch.dict(os.environ, {'GSETTINGS_BACKEND': 'memory'}):
            with self.assertRaises(ValueError): controls.change('hide')
        self.assertFalse(self.settings.writes())

    def test_locked_setting_cannot_change_or_restore(self):
        self.settings.writable = False
        with self.assertRaisesRegex(ValueError, 'locked'):
            controls.change('hide')
        self.assertFalse(self.state.exists())
        self.settings.writable = True; controls.change('hide'); self.settings.writable = False
        with self.assertRaisesRegex(ValueError, 'locked'):
            controls.restore()

    def test_user_bus_and_nonroot_required_for_changes(self):
        with patch.dict(os.environ, {'DBUS_SESSION_BUS_ADDRESS': ''}):
            with self.assertRaisesRegex(ValueError, 'session bus'):
                controls.change('hide')
        with patch.object(controls.os, 'getuid', return_value=0):
            with self.assertRaisesRegex(ValueError, 'normal user'):
                controls.change('hide')
        self.assertFalse(self.settings.writes())

    def test_same_control_operates_in_gnome_and_hyprland(self):
        for desktop in ('GNOME', 'ubuntu:GNOME', 'Hyprland'):
            with self.subTest(desktop=desktop), patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': desktop}):
                controls.change('hide')
                controls.change('show')
        self.assertEqual(self.settings.user, controls.SHOW)

    def test_symlinked_state_and_nonprivate_transactions_are_refused(self):
        other = self.home / 'other'; other.mkdir()
        self.state.symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError): controls.change('hide')
        self.state.unlink()
        controls.transactions().mkdir(mode=0o755, parents=True)
        controls.transactions().chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'private'): controls.change('hide')
        self.assertFalse(self.settings.writes())

    def test_menu_actions_require_explicit_confirmation_rows(self):
        rows = [row for row in self.items.values() if row['action'].startswith('omabuntu-window-controls:')]
        self.assertEqual({row['action'] for row in rows}, set(controls.ACTIONS))
        self.assertTrue(all(row['id'].endswith('.confirm') for row in rows))
        for row in rows:
            self.assertIn('All Desktops', row['label'])
        self.assertFalse(menu_model.run_item('setup.window-controls.hide', (self.items, self.order))['ok'])
        result = menu_model.run_item('setup.window-controls.hide.confirm', (self.items, self.order))
        self.assertTrue(result['ok'])
        self.assertTrue(menu_model.run_item('setup.window-controls.restore.confirm', (self.items, self.order))['ok'])

    def test_old_partial_mode_and_forged_actions_are_refused(self):
        for action in ('omabuntu-window-controls:hide-supported', 'omabuntu-window-controls:default',
                       'omabuntu-window-controls:hide; reboot'):
            forged = dict(self.items, forged={'action': action})
            self.assertFalse(menu_model.run_item('forged', (forged, self.order))['ok'])
        self.assertFalse(self.settings.writes())

    def test_menu_checks_follow_external_changes_not_saved_policy(self):
        result = controls.guards(self.items)
        self.assertTrue(result['checked']['setup.window-controls.show'])
        self.settings.user = controls.HIDE
        result = controls.guards(self.items)
        self.assertTrue(result['checked']['setup.window-controls.hide'])
        self.assertFalse(result['checked']['setup.window-controls.show'])
        self.assertNotIn('window-controls:', menu_model.guard_script(self.items))
        self.assertFalse(self.state.exists())

    def test_menu_failures_are_reported_not_silently_closed(self):
        self.settings.writable = False
        result = menu_model.run_item('setup.window-controls.hide.confirm', (self.items, self.order))
        self.assertEqual(result['error'], 'window-controls')
        self.assertIn('locked', result['message'])

    def test_cli_reads_and_global_write_gate(self):
        for argv, code in ((['status'], 0), (['plan', 'hide'], 0), (['set', 'hide'], 1), (['restore'], 1)):
            with self.subTest(argv=argv), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(controls.main(argv), code)
                self.assertIsInstance(json.loads(output.getvalue()), dict)
        self.assertFalse(self.settings.writes())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(controls.main(['set', 'hide', '--apply-user-wide']), 0)
            self.assertEqual(controls.main(['restore', '--apply-user-wide']), 0)
        self.assertEqual(self.settings.user, controls.SHOW)

    def test_backup_validation_bounds(self):
        for value in (None, [], {'effective':'x'},
                      {'effective':'x','user_value':'y','writable':True},
                      {'effective':'x','user_value':None,'writable':1}):
            with self.subTest(value=value), self.assertRaises(ValueError): controls.validate_before(value)
        for raw in ('1', '[]', "'a\\n'", repr('x' * (controls.MAX_LAYOUT + 1))):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError): controls.parse_value(raw)

    def test_legacy_repair_does_not_undo_intentional_hide(self):
        import repair_gnome_buttons as repair
        controls.change('hide')
        before = len(self.settings.writes())
        with patch.object(repair, 'current_value', return_value=controls.HIDE):
            state = repair.review(self.home)
            self.assertTrue(state['intentional_user_wide_hide'])
            self.assertFalse(state['repair_needed'])
            self.assertFalse(repair.apply(self.home)['changed'])
        self.assertEqual(len(self.settings.writes()), before)

    def test_legacy_damage_without_global_receipt_is_still_repairable(self):
        import repair_gnome_buttons as repair
        with patch.object(repair, 'current_value', return_value=controls.HIDE):
            self.assertTrue(repair.review(self.home)['repair_needed'])
        self.assertFalse(self.state.exists())

    def test_corrupt_or_interrupted_global_receipt_defers_legacy_repair(self):
        import repair_gnome_buttons as repair
        result = controls.change('hide')
        path = self.journal(result['transaction'])
        record = json.loads(path.read_text()); record['status'] = 'prepared'
        path.write_text(json.dumps(record))
        with patch.object(repair, 'current_value', return_value=controls.HIDE):
            with self.assertRaisesRegex(ValueError, 'Interrupted'):
                repair.review(self.home)
        record['status'] = 'applied'; path.write_text(json.dumps(record))
        (path.parent / 'before.json').write_text('{}')
        with patch.object(repair, 'current_value', return_value=controls.HIDE):
            with self.assertRaisesRegex(ValueError, 'backup'):
                repair.review(self.home)

    def test_restore_receipt_failure_can_be_retried_without_another_key_write(self):
        controls.change('hide')
        original = controls.files.atomic
        def fail(path, data, mode=0o600):
            if path.name == 'transaction.json' and json.loads(data)['status'] == 'restored':
                raise OSError('fixture restore receipt failure')
            return original(path, data, mode)
        with patch.object(controls.files, 'atomic', side_effect=fail):
            with self.assertRaises(OSError): controls.restore()
        self.assertEqual(self.settings.user, controls.SHOW)
        before = len(self.settings.writes())
        controls.restore()
        self.assertEqual(len(self.settings.writes()), before)

    def test_inconsistent_probe_is_refused_before_writes(self):
        original = self.settings.run
        def inconsistent(argv, **kwargs):
            if argv[:2] == ['/usr/bin/dconf', 'read']:
                return subprocess.CompletedProcess(argv, 0, stdout=repr('other:'), stderr='')
            return original(argv, **kwargs)
        with patch.object(controls.subprocess, 'run', side_effect=inconsistent):
            with self.assertRaisesRegex(ValueError, 'during inspection'):
                controls.change('hide')
        self.assertFalse(self.settings.writes())
        self.assertFalse(self.state.exists())

    def test_packaging_feedback_and_launchers_unchanged(self):
        self.assertIn("'window_controls.py'", (ROOT / 'tools/package_user.py').read_text())
        qml = (ROOT / 'config/shell/preview/CommandMenu.qml').read_text()
        self.assertIn('if (payload.window_controls)', qml)
        self.assertIn('including GNOME', qml)
        for name in ('AppLauncher.qml', 'FloatingDock.qml'):
            text = (ROOT / 'config/shell/preview' / name).read_text()
            self.assertIn('entry.execute()', text)
            self.assertNotIn('launchApplication', text)
        self.assertNotIn('ApplicationLaunch', (ROOT / 'config/shell/preview/TrialShell.qml').read_text())


if __name__ == '__main__':
    unittest.main()
