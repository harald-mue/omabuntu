"""Ubuntu NetworkManager helper contracts. No live network command is run."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import network_nm as nm


UUID = "4071d115-3f9a-4662-b556-303a3acfff59"
WIRED = "99c03144-0db1-3b83-86ad-5d843dfd9e8c"
VPN = "11111111-2222-3333-4444-555555555555"


class Fake:
    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    def __call__(self, argv, timeout):
        self.calls.append(list(argv))
        for prefix, value in self.replies.items():
            if list(argv) == list(prefix):
                return value
        if len(argv) >= 3 and argv[:3] == ["nmcli", "connection", "modify"]:
            return 0, ""
        raise AssertionError(argv)


def base_replies(**extra):
    replies = {
        ("ip", "-4", "route", "show", "default"): (0, "default via 192.0.2.1 dev wlan0\n"),
        ("nmcli", "-g", "GENERAL.CON-UUID", "device", "show", "wlan0"): (0, UUID + "\n"),
        ("nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"): (0, "wlan0:wifi:connected\n"),
        ("nmcli", "-g", "ipv4.ignore-auto-dns", "connection", "show", UUID): (0, "no\n"),
        ("nmcli", "-g", "ipv4.dns", "connection", "show", UUID): (0, "\n"),
        ("nmcli", "-g", "ipv6.ignore-auto-dns", "connection", "show", UUID): (0, "no\n"),
        ("nmcli", "-g", "ipv6.dns", "connection", "show", UUID): (0, "\n"),
        ("iw", "dev", "wlan0", "link"): (0, "SSID: Cafe\n\tfreq: 5240\n"),
        ("nmcli", "-t", "-f", "SSID,FREQ", "dev", "wifi", "list", "ifname", "wlan0", "--rescan", "no"):
            (0, "Cafe:2412 MHz\nCafe:5240 MHz\nOther:2412 MHz\n"),
        ("nmcli", "-g", "802-11-wireless.band", "connection", "show", UUID): (0, "\n"),
        ("nmcli", "-t", "-f", "UUID,TYPE,NAME,DEVICE", "connection", "show"):
            (0, f"{WIRED}:802-3-ethernet:Wired connection 1:\n"
                f"{VPN}:vpn:Office\\:Tunnel:\n"
                f"{UUID}:802-11-wireless:Cafe:wlan0\n"),
    }
    replies.update(extra)
    return replies


class NetworkNmTests(unittest.TestCase):
    def test_status_reads_dhcp_bands_and_saved_profiles(self):
        fake = Fake(base_replies())
        result = nm.status(fake)
        self.assertEqual(result["dns"], "DHCP")
        self.assertEqual(result["band"], "5")
        self.assertEqual(result["selected"], "auto")
        self.assertEqual(result["available"], ["2.4", "5"])
        self.assertEqual(result["ethernet"], [{"uuid": WIRED, "name": "Wired connection 1", "active": False}])
        self.assertEqual(result["vpn"], [{"uuid": VPN, "name": "Office:Tunnel", "active": False}])
        self.assertFalse(any(call[1] == "--show-secrets" for call in fake.calls))

    def test_active_ap_signal_is_cached_bounded_and_interface_scoped(self):
        command = ("nmcli", "-t", "-f", "IN-USE,SIGNAL", "dev", "wifi", "list",
                   "ifname", "wlan0", "--rescan", "no")
        for text, expected in [(":99\n*:73\n", 73), ("*:101\n", -1),
                               ("*:oops\n", -1), ("*:0\n", 0), ("", -1)]:
            replies = base_replies()
            replies[command] = (0, text)
            fake = Fake(replies)
            self.assertEqual(nm.dispatch(["nm", "signal"], fake),
                             {"ok": True, "iface": "wlan0", "signal": expected})
            self.assertEqual(len(fake.calls), 2)
        replies[command] = (1, "unavailable")
        self.assertEqual(nm.active_ap_signal(Fake(replies))["signal"], -1)
        replies[("nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status")] = (0, "")
        self.assertEqual(nm.active_ap_signal(Fake(replies)), {"ok": True, "iface": "", "signal": -1})

    def test_dns_change_touches_only_the_active_profile_and_reverts(self):
        replies = base_replies()
        replies[("nmcli", "device", "reapply", "wlan0")] = (1, "")
        fake = Fake(replies)
        result = nm.dispatch(["network_nm.py", "dns-set", "Cloudflare"], fake)
        self.assertEqual(result, {"ok": False, "error": "reverted"})
        modified = [call for call in fake.calls if call[:3] == ["nmcli", "connection", "modify"]]
        self.assertEqual(len(modified), 2)
        self.assertEqual(modified[0][3], UUID)
        self.assertIn("1.1.1.1,1.0.0.1", modified[0])
        self.assertEqual(modified[1][5], "no")
        self.assertEqual(modified[1][7], "")
        self.assertNotIn(WIRED, json.dumps(modified))

    def test_band_pin_reverts_when_reconnect_fails(self):
        replies = base_replies()
        replies[("nmcli", "connection", "up", UUID)] = (1, "")
        fake = Fake(replies)
        result = nm.dispatch(["network_nm.py", "band-set", "5"], fake)
        self.assertEqual(result["error"], "reverted")
        modified = [call for call in fake.calls if call[:3] == ["nmcli", "connection", "modify"]]
        self.assertEqual(modified[0][-1], "a")
        self.assertEqual(modified[1][-1], "")

    def test_unavailable_band_is_not_written(self):
        fake = Fake(base_replies())
        result = nm.dispatch(["network_nm.py", "band-set", "6"], fake)
        self.assertEqual(result["error"], "not-available")
        self.assertFalse(any(call[:3] == ["nmcli", "connection", "modify"] for call in fake.calls))

    def test_profile_actions_reject_wifi(self):
        replies = base_replies()
        replies[("nmcli", "-g", "connection.type", "connection", "show", UUID)] = (0, "802-11-wireless\n")
        replies[("nmcli", "-g", "connection.type", "connection", "show", VPN)] = (0, "vpn\n")
        replies[("nmcli", "connection", "up", VPN)] = (0, "")
        fake = Fake(replies)
        self.assertEqual(nm.dispatch(["nm", "connect", UUID], fake)["error"], "profile")
        self.assertEqual(nm.dispatch(["nm", "connect", VPN], fake), {"ok": True})
        self.assertTrue(any(call[:4] == ["nmcli", "connection", "up", VPN] for call in fake.calls))

    def test_qr_matrix_hides_the_passphrase_and_refuses_enterprise(self):
        secret = "fixture-psk-value"
        replies = base_replies()
        replies[("nmcli", "-g", "802-11-wireless.ssid", "connection", "show", UUID)] = (0, "Cafe\n")
        replies[("nmcli", "-g", "802-11-wireless-security.key-mgmt", "connection", "show", UUID)] = (0, "wpa-psk\n")
        replies[("nmcli", "--show-secrets", "-g", "802-11-wireless-security.psk", "connection", "show", UUID)] = (0, secret + "\n")
        fake = Fake(replies)
        result = nm.dispatch(["nm", "qr"], fake)
        encoded = json.dumps(result)
        self.assertTrue(result["ok"])
        self.assertNotIn(secret, encoded)
        self.assertNotIn("Cafe", encoded)
        self.assertEqual(len(result["modules"]), result["size"] * result["size"])
        self.assertTrue(set(result["modules"]) <= {"0", "1"})
        replies[("nmcli", "-g", "802-11-wireless-security.key-mgmt", "connection", "show", UUID)] = (0, "wpa-eap\n")
        fake = Fake(replies)
        refused = nm.dispatch(["nm", "qr"], fake)
        self.assertEqual(refused["error"], "enterprise")
        self.assertFalse(any("--show-secrets" in call for call in fake.calls))

    def test_speed_is_bounded_and_reports_megabits(self):
        calls = []

        def run(argv, timeout):
            calls.append((list(argv), timeout))
            if "%{speed_download}" in argv:
                return 0, "1250000\n"
            if "%{speed_upload}" in argv:
                return 0, "250000\n"
            raise AssertionError(argv)

        result = nm.speed(run)
        self.assertEqual(result, {"ok": True, "down": 10.0, "up": 2.0})
        self.assertTrue(all(timeout <= 12 and "--max-time" in argv and "8" in argv for argv, timeout in calls))
        self.assertTrue(all("https://speed.cloudflare.com/" in argv[-1] or argv[-1].startswith("@") for argv, _timeout in calls))

    def test_usage_and_custom_dns_reject_non_addresses(self):
        fake = Fake(base_replies())
        self.assertEqual(nm.dispatch(["nm"], fake)["error"], "usage")
        self.assertEqual(nm.dispatch(["nm", "dns-set", "Custom", "not-an-address"], fake)["error"], "dns")
        self.assertFalse(any(call[:3] == ["nmcli", "connection", "modify"] for call in fake.calls))


if __name__ == "__main__":
    unittest.main()
