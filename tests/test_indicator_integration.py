"""Optional indicator layout preference transactions, not desktop changes."""
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
import check_clock_preview


class IndicatorIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.state = self.home / 'state'
        self.target = self.state / 'current/bar.json'
        environment = patch.dict(os.environ, {'HOME': str(self.home), 'OMABUNTU_STATE_HOME': str(self.state),
            'XDG_CONFIG_HOME': str(self.home / 'config'), 'XDG_CURRENT_DESKTOP': 'Hyprland',
            'XDG_SESSION_TYPE': 'wayland', 'HYPRLAND_INSTANCE_SIGNATURE': 'fixture', 'WAYLAND_DISPLAY': 'wayland-fixture'}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        battery = patch.object(backend, 'battery_present', return_value=False)
        battery.start()
        self.addCleanup(battery.stop)
        self.items, _ = menu_model.merge_menu_sources(menu_model.parse_menu_jsonc((ROOT / 'config/shell/omabuntu-menu.jsonc').read_text()))

    def test_defaults_and_read_guards_never_enable_native_queries_or_create_state(self):
        self.assertFalse(bar_layout.indicators_visible(bar_layout.defaults()))
        guards = backend.guards(self.items)
        self.assertTrue(guards['when']['appearance.top-bar.show-indicators'])
        self.assertFalse(guards['when']['appearance.top-bar.hide-indicators'])
        self.assertEqual(backend.change('bar-indicators', 'off')['status'], 'unchanged')
        self.assertFalse(self.state.exists())
        for key in ('appearance.top-bar.show-indicators', 'appearance.top-bar.hide-indicators'):
            self.assertEqual(self.items[key]['icon'], '󰔎')

    def test_show_hide_and_reverse_rollback_preserve_absence_without_native_requests(self):
        shown = backend.change('bar-indicators', 'on')
        self.assertEqual(shown['appearance']['bar']['bar_layout']['centerBegin'], ['omarchy.indicators'])
        raw = self.target.read_bytes()
        self.assertEqual(backend.change('bar-indicators', 'on')['status'], 'unchanged')
        hidden = backend.change('bar-indicators', 'off')
        self.assertEqual(hidden['appearance']['bar']['bar_layout'], bar_layout.defaults())
        backend.rollback(hidden['transaction'])
        self.assertEqual(self.target.read_bytes(), raw)
        backend.rollback(shown['transaction'])
        self.assertFalse(self.target.exists())
        self.assertFalse((self.state / 'native-indicators').exists())

    def test_relocated_indicator_hide_preserves_media_settings_exact_bytes_mode(self):
        layout = bar_layout.with_media(bar_layout.defaults(), True)
        layout['right'].insert(1, 'omarchy.indicators')
        data = {**backend.DEFAULTS, 'bar_layout': layout, 'background': 'glassy', 'hidden': True}
        self.target.parent.mkdir(parents=True)
        raw = json.dumps(data, indent=4).encode() + b'\n'
        self.target.write_bytes(raw)
        self.target.chmod(0o640)
        hidden = backend.change('bar-indicators', 'off')
        current = hidden['appearance']['bar']
        self.assertTrue(bar_layout.media_visible(current['bar_layout']))
        self.assertFalse(bar_layout.indicators_visible(current['bar_layout']))
        self.assertTrue(current['hidden'])
        self.assertEqual(current['background'], 'glassy')
        backend.rollback(hidden['transaction'])
        self.assertEqual(self.target.read_bytes(), raw)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o640)

    def test_closed_detached_registry_and_packaging_keep_other_optional_backends_out(self):
        original = bar_layout.defaults()
        shown = bar_layout.with_indicators(original, True)
        self.assertFalse(bar_layout.indicators_visible(original))
        self.assertEqual(bar_layout.with_indicators(shown, True), shown)
        self.assertEqual(bar_layout.with_indicators(shown, False), original)
        with self.assertRaises(ValueError):
            bar_layout.with_optional(original, 'recording', True)
        source = (ROOT / 'tools/package_user.py').read_text()
        self.assertIn("'indicator_native.py', 'indicator_state.py'", source)
        self.assertNotIn("'audio_profiles.py'", source)
        self.assertNotIn("'audio_pactl.py'", source)
        files, _ = check_clock_preview.verified_sources(ROOT)
        for name in ('DndIndicator.qml', 'NightLightIndicator.qml', 'IndicatorState.qml'):
            self.assertIn(name, files)
        for name in ('PasswordlessSudo.qml', 'StayAwake.qml', 'RemoteSession.qml', 'ScreenRecording.qml', 'Reminder.qml'):
            self.assertNotIn(name, files)


if __name__ == '__main__':
    unittest.main()
