"""Appearance state/menu contracts in temporary homes; no desktop commands."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import appearance_backend as backend
import menu_model
import check_clock_preview


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.state = self.home / 'state'
        self.env = {'HOME': str(self.home), 'OMABUNTU_STATE_HOME': str(self.state),
                    'XDG_CONFIG_HOME': str(self.home / 'config'),
                    'XDG_CURRENT_DESKTOP': 'Hyprland', 'XDG_SESSION_TYPE': 'wayland',
                    'HYPRLAND_INSTANCE_SIGNATURE': 'fixture', 'WAYLAND_DISPLAY': 'wayland-fixture'}
        environment = patch.dict(os.environ, self.env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        battery = patch.object(backend, 'battery_present', return_value=False)
        self.battery = battery.start()
        self.addCleanup(battery.stop)
        self.items, self.order = menu_model.merge_menu_sources(menu_model.parse_menu_jsonc(
            (ROOT / 'config/shell/omabuntu-menu.jsonc').read_text()))

    def stored(self, name, data):
        path = self.state / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return path

    def test_snapshot_and_guards_on_missing_state_create_nothing(self):
        current = backend.snapshot()
        self.assertEqual(current['bar']['background'], 'opaque')
        self.assertEqual(current['bar']['clock_format'], 'dddd HH:mm')
        self.assertFalse(current['bar']['hidden'])
        result = menu_model.evaluate_guards(self.items, run=lambda _: (0, ''))
        self.assertTrue(result['when']['appearance.top-bar.hide'])
        self.assertFalse(result['when']['appearance.top-bar.show'])
        self.assertFalse(result['when']['appearance.dock'])
        self.assertFalse(self.state.exists())
        self.assertFalse((self.home / 'config').exists())

    def test_original_menu_choices_use_only_closed_registry(self):
        rows = [entry for entry in self.items.values() if entry['action'].startswith('omabuntu-appearance:')]
        self.assertEqual(len(rows), 23)
        self.assertTrue(all(row['action'] in backend.ACTIONS for row in rows))
        self.assertNotIn('appearance.top-bar.position', self.items)
        for missing in ('appearance.unlock', 'appearance.windows', 'appearance.branding'):
            self.assertNotIn(missing, self.items)
        # Checked/visibility predicates are evaluated in Python, never bash.
        self.assertNotIn('appearance:', menu_model.guard_script(self.items))

    def test_change_records_absence_before_write_and_rollback_removes_only_file(self):
        result = backend.change('hidden', 'on')
        self.assertTrue(result['appearance']['bar']['hidden'])
        case = self.state / 'appearance-transactions' / result['transaction']
        record = json.loads((case / 'transaction.json').read_text())
        self.assertIsNone(record['before_sha256'])
        path = self.state / 'current/bar.json'
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(case.stat().st_mode & 0o777, 0o700)
        self.assertEqual(backend.rollback(result['transaction'])['status'], 'rolled-back')
        self.assertFalse(path.exists())
        self.assertTrue(case.exists())

    def test_preserves_unknown_fields_and_exact_original_bytes_mode(self):
        path = self.stored('current/bar.json', {'schema_version': 1, 'background': 'none', 'future': {'keep': True}})
        path.chmod(0o640)
        before = path.read_bytes()
        result = backend.change('clock', 'time-12h')
        self.assertEqual(result['appearance']['bar']['future'], {'keep': True})
        self.assertEqual(result['appearance']['bar']['background'], 'none')
        backend.rollback(result['transaction'])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_legacy_bar_off_flag_is_preserved_and_explicit_show_wins(self):
        flag = self.state / 'toggles/bar-off'
        flag.parent.mkdir(parents=True)
        flag.write_text('')
        self.assertTrue(backend.snapshot()['bar']['hidden'])
        result = backend.change('hidden', 'off')
        self.assertFalse(backend.snapshot()['bar']['hidden'])
        self.assertTrue(flag.exists())
        backend.rollback(result['transaction'])
        self.assertTrue(backend.snapshot()['bar']['hidden'])

    def test_dock_changes_keep_pins_unknown_fields_and_share_existing_config(self):
        path = backend.dock_state.config_path()
        path.parent.mkdir(parents=True, mode=0o700)
        path.write_text(json.dumps({'schema_version': 1, 'position': 'bottom', 'autohide': False,
                                    'pinned': ['org.example.App'], 'future': 42}))
        before = path.read_bytes()
        first = backend.change('dock-position', 'left')
        second = backend.change('dock-autohide', 'on')
        data = json.loads(path.read_text())
        self.assertEqual(data['pinned'], ['org.example.App'])
        self.assertEqual(data['future'], 42)
        self.assertEqual(data['position'], 'left')
        self.assertTrue(data['autohide'])
        backend.rollback(second['transaction'])
        backend.rollback(first['transaction'])
        self.assertEqual(path.read_bytes(), before)

    def test_rollback_refuses_later_changes_or_changed_backup(self):
        path = self.stored('current/bar.json', {'schema_version': 1, 'background': 'opaque'})
        result = backend.change('background', 'glassy')
        original_after = path.read_bytes()
        path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'changed since'):
            backend.rollback(result['transaction'])
        path.write_bytes(original_after)
        case = self.state / 'appearance-transactions' / result['transaction']
        (case / 'before').write_text('changed backup')
        with self.assertRaisesRegex(ValueError, 'backup differs'):
            backend.rollback(result['transaction'])
        self.assertEqual(path.read_bytes(), original_after)

    def test_invalid_journal_and_token_cannot_redirect_rollback(self):
        result = backend.change('background', 'none')
        path = self.state / 'current/bar.json'
        before = path.read_bytes()
        case = self.state / 'appearance-transactions' / result['transaction']
        record_path = case / 'transaction.json'
        record = json.loads(record_path.read_text())
        record['key'] = ['malformed']
        record_path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'Invalid preference transaction'):
            backend.rollback(result['transaction'])
        with self.assertRaises(ValueError):
            backend.rollback('../outside')
        self.assertEqual(path.read_bytes(), before)

    def test_gnome_mixed_and_missing_session_refuse_before_state_creation(self):
        for values in ({'XDG_CURRENT_DESKTOP': 'GNOME'}, {'XDG_CURRENT_DESKTOP': 'Hyprland:GNOME'},
                       {'XDG_SESSION_TYPE': 'x11'}, {'HYPRLAND_INSTANCE_SIGNATURE': ''},
                       {'WAYLAND_DISPLAY': ''}):
            with self.subTest(values=values), patch.dict(os.environ, values):
                with self.assertRaisesRegex(ValueError, 'Hyprland Wayland'):
                    backend.change('background', 'none')
        self.assertFalse(self.state.exists())

    def test_invalid_values_are_refused_without_state(self):
        for key, value in (('background', 'none; reboot'), ('clock', 'arbitrary'),
                           ('dock-position', '../../other'), ('unknown', 'on')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                backend.change(key, value)
        self.assertFalse(self.state.exists())

    def test_invalid_existing_bar_or_dock_is_not_overwritten(self):
        path = self.stored('current/bar.json', {'schema_version': True, 'background': 'opaque'})
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            backend.change('background', 'none')
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.state / 'appearance-transactions').exists())

    def test_invalid_dock_prevents_unrelated_bar_mutation(self):
        path = backend.dock_state.config_path()
        path.parent.mkdir(parents=True, mode=0o700)
        path.write_text('{"schema_version": 1, "pinned": "not-a-list"}')
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            backend.change('background', 'none')
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(self.state.exists())

    def test_symlink_leaf_and_ancestor_are_refused(self):
        target = self.home / 'unrelated'
        target.mkdir()
        self.state.mkdir()
        (self.state / 'current').symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            backend.change('background', 'none')
        self.assertEqual(list(target.iterdir()), [])

    def test_symlink_leaf_is_refused_without_touching_destination(self):
        target = self.home / 'unrelated.json'
        target.write_text('{}')
        path = self.state / 'current/bar.json'
        path.parent.mkdir(parents=True)
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            backend.change('background', 'none')
        self.assertEqual(target.read_text(), '{}')

    def test_failed_final_receipt_restores_original_state(self):
        path = self.stored('current/bar.json', {'schema_version': 1, 'background': 'opaque'})
        before = path.read_bytes()
        original = backend.atomic
        def write(target, raw, mode=0o600):
            if target.name == 'transaction.json' and json.loads(raw).get('status') == 'applied':
                raise OSError('simulated receipt failure')
            original(target, raw, mode)
        with patch.object(backend, 'atomic', side_effect=write), self.assertRaises(OSError):
            backend.change('background', 'none')
        self.assertEqual(path.read_bytes(), before)

    def test_guard_checked_visibility_and_workspace_context(self):
        self.battery.return_value = True
        self.stored('current/workspace-layouts.txt', {})
        (self.state / 'current/workspace-layouts.txt').write_text('2 floating\n3 scrolling\n')
        backend.change('background', 'none')
        backend.change('battery-percentage', 'on')
        result = menu_model.evaluate_guards(self.items, run=lambda _: (0, ''), workspace='2')
        self.assertTrue(result['when']['appearance.dock'])
        self.assertTrue(result['checked']['appearance.top-bar.background.clear'])
        self.assertFalse(result['when']['appearance.top-bar.indicators.battery-percentage-on'])
        self.assertTrue(result['when']['appearance.top-bar.indicators.battery-percentage-off'])
        self.assertFalse(backend.snapshot('3')['floating_workspace'])
        self.assertFalse(backend.snapshot('2; reboot')['floating_workspace'])

    def test_dispatch_and_cli_preserve_one_json_document_on_error(self):
        result = menu_model.run_item('appearance.top-bar.background.clear', (self.items, self.order))
        self.assertTrue(result['ok'])
        bad = dict(self.items, injected={'action': 'omabuntu-appearance:background:none; reboot'})
        self.assertFalse(menu_model.run_item('injected', (bad, self.order))['ok'])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            menu_model.main(['appearance-set', 'unknown', 'on'])
        self.assertFalse(json.loads(output.getvalue())['ok'])

    def test_all_clock_menu_formats_round_trip(self):
        for key, format_string in backend.CLOCKS.items():
            with self.subTest(key=key):
                result = backend.change('clock', key)
                self.assertEqual(result['appearance']['bar']['clock_format'], format_string)

    def test_packaging_and_shared_binding_contracts(self):
        files, _ = check_clock_preview.verified_sources(ROOT)
        self.assertIn('AppearanceState.qml', files)
        self.assertIn('appearance_backend.py', (ROOT / 'tools/package_user.py').read_text())
        panel = files['TrialPanel.qml'].decode()
        self.assertIn('persistAppearance: bars.appearance !== null', panel)
        self.assertIn('appearanceSettings: bars.appearance', panel)
        self.assertIn('onLoadFailed: if (bars.appearance) bars.appearance.refresh()', panel)
        self.assertIn('Quickshell.env("OMABUNTU_STATE_HOME")', panel)
        self.assertIn('persistAppearance) root.settings = entry', files['ClockControlView.qml'].decode())
        adapter = files['AppearanceState.qml'].decode()
        self.assertNotIn('Timer {', adapter)
        self.assertIn('Qt.callLater(root.pump)', adapter)
        self.assertIn('onPressed:', files['CommandMenu.qml'].decode())


if __name__ == '__main__':
    unittest.main()
