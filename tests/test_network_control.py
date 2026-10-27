"""Network control extraction and action boundaries. No NetworkManager is started."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_clock_preview as preview
import network_frontend
import wifi_control_fixtures as fixtures


class NetworkControlTests(unittest.TestCase):
    def test_connection_surface_is_extracted_from_the_original_panel(self):
        source = (ROOT / "vendor/omarchy/shell/plugins/panels/network/Panel.qml").read_bytes()
        output = network_frontend.derive_network(source).decode()
        self.assertEqual(output, (ROOT / "config/shell/preview/NetworkControlView.qml").read_text())
        files, meta = preview.verified_sources(ROOT)
        self.assertEqual(files["NetworkControlView.qml"].decode(), output)
        self.assertEqual(meta["upstream"]["NetworkControlView.qml"]["stage_transform"], "network-control-frontend-v1")
        self.assertEqual(meta["upstream"]["Ui/PanelActionButton.qml"]["stage_transform"], "none")
        hero_start, hero_end = "      // ---------- Hero:", "      Column {\n        visible: root.hasCaptivePortal\n"
        hero = network_frontend.between(source.decode(), hero_start, hero_end)
        self.assertEqual(output.count(hero), 1)
        self.assertEqual(output.count("visible: root.hasCaptivePortal"), 1)
        self.assertIn("root.setBand(band)", output)
        self.assertIn("root.setDns(provider)", output)
        self.assertIn("ethernetProfiles", output)
        self.assertIn("vpnProfiles", output)
        self.assertEqual(output.count('Quickshell.execDetached(["xdg-open", "http://connectivity-check.ubuntu.com/"])'), 1)
        self.assertIn("id: networkList", output)
        self.assertNotIn("height: visible ? implicitHeight : 0", output)
        self.assertIn("refuseEnterprise", output)
        self.assertNotIn("connectEnterprise", output)
        scrubbed = output.replace('Quickshell.execDetached(["xdg-open", "http://connectivity-check.ubuntu.com/"])', "", 1)
        for forbidden in ("Process {", "Quickshell.Io", "execDetached", "nmcli", "enterpriseConnect",
                          "captivePortalUrl", "omarchy-", "ShellIpc", "ping.archlinux"):
            self.assertNotIn(forbidden, scrubbed)

    def test_controller_mutates_only_explicit_network_actions(self):
        text = (ROOT / "config/shell/preview/NetworkPanelController.qml").read_text()
        self.assertEqual(text.count("Process {"), 1)
        self.assertIn("OMABUNTU_NETWORK_HELPER", text)
        self.assertIn('requestNm("dns-set"', text)
        self.assertIn('requestNm("band-set"', text)
        self.assertIn('requestNm("qr"', text)
        self.assertIn('requestNm("speed"', text)
        for forbidden in ("execDetached", "nmcli", "captivePortalUrl", "omarchy-", "nmSettings",
                          "connectivityCheckEnabled =", "ping.archlinux", "sudo"):
            self.assertNotIn(forbidden, text)
        self.assertIn("network.connectWithPsk(passphrase)".replace("network.", "item."), text)
        self.assertIn("scannerEnabled", text)
        self.assertIn("Networking.wifiEnabled = !Networking.wifiEnabled", text)
        self.assertIn("Component.onCompleted: syncWifiNetworks()", text)
        self.assertNotIn("Component.onCompleted: refresh", text)
        self.assertIn("isEnterprise(network.security) && !network.known", text)

    def test_wifi_fixtures_are_fixed_and_secret_free_in_logs(self):
        self.assertEqual(len(fixtures.CASES), 11)
        with self.assertRaises(ValueError):
            fixtures.fixture("host-wifi")
        text = fixtures.fixture("passphrase")
        self.assertIn("fixture-psk", text)
        logged = text.split("console.log", 1)[1]
        self.assertNotIn("fixture-psk", logged)
        self.assertNotIn("passwordText", logged)
        self.assertIn("pskAccepted", text)
        self.assertTrue(fixtures.classify("passphrase", 0, "Configuration Loaded\n" + fixtures.MARKER + "::passphrase\n"))
        self.assertFalse(fixtures.classify("passphrase", 0, "Configuration Loaded\nWARN secret\n" + fixtures.MARKER + "::passphrase\n"))
        self.assertTrue(fixtures.classify("negative", 42, "ERROR deliberate wifi assertion\n"))


if __name__ == "__main__":
    unittest.main()
