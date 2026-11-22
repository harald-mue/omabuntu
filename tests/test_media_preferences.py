"""Optional original media admission uses exact reversible shell preferences."""
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
import bar_layout
import menu_model


class MediaPreferenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.state = self.home / 'state'
        self.target = self.state / 'current/bar.json'
        environment = patch.dict(os.environ, {
            'HOME': str(self.home), 'OMABUNTU_STATE_HOME': str(self.state),
            'XDG_CONFIG_HOME': str(self.home / 'config'), 'XDG_CURRENT_DESKTOP': 'Hyprland',
            'XDG_SESSION_TYPE': 'wayland', 'HYPRLAND_INSTANCE_SIGNATURE': 'fixture',
            'WAYLAND_DISPLAY': 'wayland-fixture'}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        battery = patch.object(backend, 'battery_present', return_value=False)
        battery.start()
        self.addCleanup(battery.stop)
        self.items, _ = menu_model.merge_menu_sources(menu_model.parse_menu_jsonc(
            (ROOT / 'config/shell/omabuntu-menu.jsonc').read_text()))

    def test_both_media_menu_rows_have_the_existing_media_glyph(self):
        for key in ('appearance.top-bar.show-media', 'appearance.top-bar.hide-media'):
            self.assertEqual(self.items[key]['icon'], '󰝚')
        self.assertFalse(self.target.exists())

    def test_default_and_read_guards_never_enable_media_or_create_state(self):
        self.assertEqual(sum(map(len, bar_layout.defaults().values())), 12)
        self.assertEqual(len(bar_layout.WIDGETS), 14)
        self.assertFalse(bar_layout.media_visible(backend.snapshot()['bar']['bar_layout']))
        guards = backend.guards(self.items)
        self.assertTrue(guards['when']['appearance.top-bar.show-media'])
        self.assertFalse(guards['when']['appearance.top-bar.hide-media'])
        self.assertEqual(backend.change('bar-media', 'off')['status'], 'unchanged')
        self.assertFalse(self.state.exists())
        self.assertFalse((self.home / 'config').exists())

    def test_explicit_show_hide_and_reverse_rollback_restore_absence(self):
        shown = backend.change('bar-media', 'on')
        self.assertEqual(shown['status'], 'applied')
        layout = shown['appearance']['bar']['bar_layout']
        self.assertEqual(layout['centerBegin'], ['omarchy.media'])
        for region, entries in bar_layout.defaults().items():
            if region != 'centerBegin':
                self.assertEqual(layout[region], entries)
        raw = self.target.read_bytes()
        self.assertEqual(backend.change('bar-media', 'on')['status'], 'unchanged')
        self.assertEqual(self.target.read_bytes(), raw)
        guards = backend.guards(self.items)
        self.assertFalse(guards['when']['appearance.top-bar.show-media'])
        self.assertTrue(guards['when']['appearance.top-bar.hide-media'])
        hidden = backend.change('bar-media', 'off')
        self.assertEqual(hidden['appearance']['bar']['bar_layout'], bar_layout.defaults())
        backend.rollback(hidden['transaction'])
        self.assertEqual(self.target.read_bytes(), raw)
        backend.rollback(shown['transaction'])
        self.assertFalse(self.target.exists())

    def test_hide_removes_only_media_after_relocation_and_restores_exact_bytes_mode(self):
        data = {'schema_version': 1, 'background': 'glassy', 'hidden': True,
                'clock_format': 'HH:mm', 'battery_percentage': True,
                'bar_layout': bar_layout.defaults(), 'tray_settings': {'pinned': ['fixture'], 'hidden': []}}
        data['bar_layout']['right'].insert(1, 'omarchy.media')
        self.target.parent.mkdir(parents=True)
        before = json.dumps(data, indent=4).encode() + b'\n'
        self.target.write_bytes(before)
        self.target.chmod(0o640)
        hidden = backend.change('bar-media', 'off')
        current = hidden['appearance']['bar']
        self.assertEqual(current['bar_layout'], bar_layout.defaults())
        for key in ('background', 'hidden', 'clock_format', 'battery_percentage', 'tray_settings'):
            self.assertEqual(current[key], data[key])
        backend.rollback(hidden['transaction'])
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o640)

    def test_rollback_refuses_later_preference_drift(self):
        shown = backend.change('bar-media', 'on')
        after = backend.change('background', 'glassy')
        raw = self.target.read_bytes()
        with self.assertRaises(ValueError):
            backend.rollback(shown['transaction'])
        self.assertEqual(self.target.read_bytes(), raw)
        backend.rollback(after['transaction'])
        backend.rollback(shown['transaction'])
        self.assertFalse(self.target.exists())

    def test_empty_layout_admits_media_without_repopulating_other_widgets(self):
        empty = {region: [] for region in bar_layout.REGIONS}
        initial = backend.change('bar-layout', json.dumps(empty))
        shown = backend.change('bar-media', 'on')
        self.assertEqual(shown['appearance']['bar']['bar_layout'], {**empty, 'centerBegin': ['omarchy.media']})
        restored = backend.change('bar-layout-default', 'restore')
        self.assertEqual(restored['appearance']['bar']['bar_layout'], bar_layout.defaults())
        backend.rollback(restored['transaction'])
        backend.rollback(shown['transaction'])
        backend.rollback(initial['transaction'])
        self.assertFalse(self.target.exists())

    def test_rechecks_presence_under_existing_cooperating_writer_lock(self):
        directory = backend.transaction_directory
        external = {}

        def concurrent_show():
            parent = directory()
            data = backend.bar_state()
            data['bar_layout']['left'].append('omarchy.media')
            self.target.parent.mkdir(parents=True, exist_ok=True)
            external['raw'] = json.dumps(data, indent=3).encode()
            self.target.write_bytes(external['raw'])
            return parent

        with patch.object(backend, 'transaction_directory', side_effect=concurrent_show):
            result = backend.change('bar-media', 'on')
        self.assertEqual(result['status'], 'unchanged')
        self.assertEqual(self.target.read_bytes(), external['raw'])
        self.assertNotIn('transaction', result)

    def test_layout_helpers_are_detached_closed_and_idempotent(self):
        original = bar_layout.defaults()
        shown = bar_layout.with_media(original, True)
        self.assertFalse(bar_layout.media_visible(original))
        self.assertTrue(bar_layout.media_visible(shown))
        self.assertEqual(bar_layout.with_media(shown, True), shown)
        self.assertEqual(bar_layout.with_media(shown, False), original)
        with self.assertRaises(ValueError):
            bar_layout.with_media(original, 'on')
        with self.assertRaises(ValueError):
            backend.change('bar-media', 'activate-player')
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'GNOME'}):
            with self.assertRaises(ValueError):
                backend.change('bar-media', 'on')
        self.assertFalse(self.state.exists())


if __name__ == '__main__':
    unittest.main()
