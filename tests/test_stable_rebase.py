"""Stable component provenance, dependency closure and retained Ubuntu boundaries."""
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
import check_clock_preview as preview
import check_clock_model
import menu_model
import network_frontend
import weather_frontend

STABLE = 'ac2690cd7be4f47e4a255f5e2e78d904d436b068'
BASE = '03ff1eff3812933f7088484533784d2f63eaf19a'


class StableComponentTests(unittest.TestCase):
    def test_component_profile_is_stable_not_quattro(self):
        files, meta = preview.verified_sources(ROOT)
        pin = json.loads((ROOT / 'upstream/omarchy-source.json').read_text())
        self.assertEqual(preview.COMMIT, STABLE)
        self.assertEqual(pin['observed_tag'], 'v4.5.0')
        self.assertEqual(meta['source']['commit'], STABLE)
        self.assertEqual(pin['reference_comparison']['commit'], BASE)
        self.assertEqual(pin['stable_component_review']['mapped_source_parents'], 72)
        self.assertNotIn('ShellIpc', files['ClockControlView.qml'].decode())
        for record in meta['upstream'].values():
            self.assertIn('/' + STABLE + '/', record['url'])

    def test_wall_clock_dependency_is_packaged_for_all_clock_views(self):
        files, _ = preview.verified_sources(ROOT)
        self.assertEqual(files['WallClock.qml'],
                         (ROOT / 'vendor/omarchy/shell/plugins/panels/clock/WallClock.qml').read_bytes())
        for name in ('ClockLabel.qml', 'ClockControlView.qml', 'CalendarPanel.qml'):
            self.assertIn(b'WallClock {', files[name])
            self.assertNotIn(b'SystemClock {', files[name])
        self.assertIn(b'Model.msUntilNextTick(Date.now(), step)', files['WallClock.qml'])
        self.assertIn(b'function msUntilNextTick(nowMs, step)', files['Model.js'])
        self.assertIn('DST epoch tick bounded', check_clock_model.qml_probe('utc'))

    def test_shared_motion_contract_and_geometry_are_complete(self):
        files, _ = preview.verified_sources(ROOT)
        self.assertIn(b'easeOut: [0.23, 1.0, 0.32, 1.0, 1.0, 1.0]', files['Commons/Style.qml'])
        for name in ('Ui/Button.qml', 'Ui/WidgetButton.qml', 'Ui/PopupCard.qml', 'DockWindow.qml'):
            self.assertIn(b'Style.easeOut', files[name])
        keyboard = files['Ui/KeyboardPanel.qml']
        self.assertIn(b'visible: open\n', keyboard)
        keyboard_code = b'\n'.join(line for line in keyboard.splitlines()
                                   if not line.lstrip().startswith(b'//'))
        self.assertNotIn(b'WlrKeyboardFocus.Exclusive', keyboard_code)
        self.assertIn(b'barThickness + gap', keyboard)
        self.assertIn(b'function morphFromLastCard()', keyboard)
        self.assertIn(b'notePopoutCard(card, "center")', files['TrialPanel.qml'])
        self.assertIn(b'notePopoutCard(card, "right")', files['PortTrayHost.qml'])
        self.assertIn(b'card.section !== section', files['TrialPanel.qml'])
        self.assertIn(b'Style.duration(250)', files['TrialPanel.qml'])
        self.assertIn(b'pressFeedbackButtons: Qt.NoButton', files['ClockControlView.qml'])

    def test_network_stable_portal_and_dns_keep_ubuntu_backend(self):
        original = (ROOT / 'vendor/omarchy/shell/plugins/panels/network/Panel.qml').read_bytes()
        surface = network_frontend.derive_network(original).decode()
        self.assertIn('id: portalAction', surface)
        self.assertIn('active: root.dnsEffective === provider', surface)
        self.assertNotIn('omarchy-network-captive-portal', surface)
        self.assertNotIn('ping.omacom.io', surface)
        self.assertIn('http://connectivity-check.ubuntu.com/', surface)
        controller = (ROOT / 'config/shell/preview/NetworkPanelController.qml').read_text()
        self.assertIn('pendingDnsProvider !== "" ? pendingDnsProvider : dnsProvider', controller)

    def test_weather_uses_stable_surface_without_new_location_endpoint(self):
        original = (ROOT / 'vendor/omarchy/shell/plugins/panels/weather/Panel.qml').read_bytes()
        surface = weather_frontend.derive_panel(original).decode()
        self.assertIn('Model.effectiveLocation', surface)
        self.assertIn('name: String(text || "").trim()', surface)
        self.assertIn('root.probeCommand("locate", [])', surface)
        self.assertNotIn('https://geo.omarchy.org/', surface)
        self.assertNotIn('["curl"', surface)
        self.assertIn('centerOnBar: false', surface)

    def test_changed_stable_extraction_witnesses_still_fail_closed(self):
        network = (ROOT / 'vendor/omarchy/shell/plugins/panels/network/Panel.qml').read_bytes()
        weather = (ROOT / 'vendor/omarchy/shell/plugins/panels/weather/Panel.qml').read_bytes()
        with self.assertRaises(ValueError):
            network_frontend.derive_network(network.replace(b'id: portalAction', b'id: unreviewed'))
        with self.assertRaises(ValueError):
            weather_frontend.derive_panel(weather.replace(b'https://geo.omarchy.org/', b'https://unreviewed.invalid/'))


class StableMenuTests(unittest.TestCase):
    def test_appearance_routes_preserve_legacy_aliases(self):
        raw = (ROOT / 'config/shell/omabuntu-menu.jsonc').read_text()
        items, order = menu_model.merge_menu_sources(menu_model.parse_menu_jsonc(raw))
        self.assertEqual(menu_model.COMMIT, STABLE)
        self.assertEqual(items['appearance']['label'], 'Appearance')
        self.assertLess(order.index('appearance'), order.index('trigger'))
        for route in ('style', 'style.theme', 'style.background', 'style.font'):
            self.assertEqual(menu_model.resolve_route(items, order, route), route.replace('style', 'appearance', 1))
        self.assertNotIn('appearance.unlock', items)
        for legacy, provider in (('style.theme', 'themes'), ('style.background', 'backgrounds'),
                                 ('style.font', 'fonts')):
            self.assertEqual(menu_model.provider_for_menu(items, legacy), provider)
        with patch.object(menu_model, 'provider_rows', return_value=[{'value': 'tokyo-night'}]):
            provider, row = menu_model.provider_row_for(items, 'style.theme.tokyo-night')
            self.assertEqual(provider, 'themes')
            self.assertEqual(row['value'], 'tokyo-night')

    def test_read_distinguishes_empty_from_malformed(self):
        self.assertEqual(menu_model.read_menu_jsonc('// empty\n'), [])
        for raw in ('{partial', 'null', '[]'):
            self.assertIsNone(menu_model.read_menu_jsonc(raw))
            self.assertEqual(menu_model.parse_menu_jsonc(raw), [])

    def test_invalid_definition_response_cannot_replace_existing_ui_rows(self):
        output = io.StringIO()
        with patch.object(menu_model, 'load_definitions', return_value=({}, [])), contextlib.redirect_stdout(output):
            self.assertEqual(menu_model.main(['defs']), 0)
        result = json.loads(output.getvalue())
        self.assertFalse(result['ok'])
        self.assertNotIn('items', result)
        surface = (ROOT / 'config/shell/preview/CommandMenu.qml').read_text()
        guard = surface.index('if (!payload || payload.ok !== true)')
        self.assertLess(guard, surface.index('root.items = payload.items'))

    def test_partial_default_or_overlay_is_rejected_without_state_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            shipped = base / 'menu.jsonc'
            overlay = base / 'omabuntu/menu.jsonc'
            overlay.parent.mkdir()
            overlay.write_text('{partial')
            shipped.write_text('{"appearance": {"label": "Appearance"}}')
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': directory}):
                self.assertEqual(menu_model.load_definitions(shipped), ({}, []))
                overlay.write_text('// empty overlay\n')
                self.assertIn('appearance', menu_model.load_definitions(shipped)[0])
                shipped.write_text('{partial')
                self.assertEqual(menu_model.load_definitions(shipped), ({}, []))
                self.assertEqual(shipped.read_text(), '{partial')


if __name__ == '__main__':
    unittest.main()
