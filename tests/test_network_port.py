"""Synthetic network-port contracts; no network service or Qt is started."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_clock_preview as preview
import check_tray_port as harness
import network_port_fixtures as fixtures


class NetworkPortTests(unittest.TestCase):
    def test_original_network_model_is_unchanged(self):
        files, meta = preview.verified_sources(ROOT)
        self.assertEqual(files["Port/NetworkModel.js"], (ROOT / "vendor/omarchy/shell/plugins/panels/network/Model.js").read_bytes())
        self.assertEqual(meta["upstream"]["Port/NetworkModel.js"]["stage_transform"], "none")

    def test_provider_is_passive(self):
        text = (ROOT / "config/shell/preview/NetworkStatusProvider.qml").read_text()
        self.assertIn("import Quickshell.Networking", text)
        self.assertIn("Networking.devices.values", text)
        for forbidden in ("scannerEnabled", "checkConnectivity(", "wifiEnabled =", "connect(", "disconnect(", "forget(", "nmSettings", "Quickshell.Io", "Process"):
            self.assertNotIn(forbidden, text)

    def test_presentation_copies_display_data_only(self):
        text = (ROOT / "config/shell/preview/NetworkPresentation.js").read_text()
        for forbidden in (".connect(", ".forget(", ".disconnect(", ".nmSettings", "scannerEnabled", "execDetached", "Process {"):
            self.assertNotIn(forbidden, text)
        self.assertIn("Object.freeze(rows)", text)
        self.assertIn('!available ? "unknown"', text)

    def test_view_exposes_no_configuration_controls(self):
        text = (ROOT / "config/shell/preview/NetworkStatusView.qml").read_text()
        self.assertIn("BarIconButton {", text)
        self.assertIn("PopupCard {", text)
        self.assertIn("Model.connectionIcon", text)
        self.assertIn("Text.PlainText", text)
        for forbidden in ("enterpriseConnectScript", "captivePortalUrl", "connectWithPsk", "password", "Process", "execDetached"):
            self.assertNotIn(forbidden, text)
        self.assertIn("Status only", text)

    def test_only_fixed_fixture_suites_are_allowed(self):
        with self.assertRaises(ValueError):
            fixtures.fixture("native-network")
        with self.assertRaises(ValueError):
            harness.run_checks(ROOT, Path("missing"), suite="host-session")
        self.assertEqual(len(fixtures.CASES), 7)
        text = fixtures.fixture("wifi")
        self.assertNotIn("import Quickshell.Networking", text)
        self.assertIn("forbidden network mutation", text)

    def test_strict_result_classification(self):
        good = "Configuration Loaded\n" + fixtures.MARKER + "::wifi\n"
        self.assertTrue(fixtures.classify("wifi", 0, good))
        self.assertFalse(fixtures.classify("wifi", 0, good + "WARN unexpected\n"))
        self.assertFalse(fixtures.classify("wifi", -11, good))
        self.assertFalse(fixtures.classify("wifi", None, good))
        self.assertFalse(fixtures.classify("wifi", 0, "Configuration Loaded\n"))
        self.assertFalse(fixtures.classify("unknown", 0, good))
        self.assertFalse(fixtures.classify("negative", 42, "ERROR unrelated\n"))
        self.assertTrue(fixtures.classify("negative", 42, "ERROR deliberate network assertion\n"))

    def test_panel_keeps_tray_and_network_in_separate_slots(self):
        text = (ROOT / "config/shell/preview/TrialPanel.qml").read_text()
        self.assertIn("NetworkControlView {", text)
        self.assertNotIn("NetworkStatusProvider", text)
        self.assertIn("bar: trayHost.ownerApi", text)
        self.assertIn("ExclusionMode.Ignore : ExclusionMode.Auto", text)


if __name__ == "__main__":
    unittest.main()
