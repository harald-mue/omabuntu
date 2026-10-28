"""Read-only Elsewhen zone probe. Never changes the system timezone."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import elsewhen_probe


class ElsewhenProbeTests(unittest.TestCase):
    def test_source_has_no_network_or_timezone_write(self):
        text = (ROOT / "tools/elsewhen_probe.py").read_text()
        for bad in ("curl", "sudo", "set-timezone", "open-meteo", "github.com", "http"):
            self.assertNotIn(bad, text)

    def test_rejects_shell_metacharacters(self):
        self.assertEqual(elsewhen_probe.main(["probe", "UTC;id"]), 2)
        self.assertEqual(elsewhen_probe.main(["probe", "$(date)"]), 2)
        self.assertEqual(elsewhen_probe.main(["zones", "UTC"]), 2)
        self.assertEqual(elsewhen_probe.main([]), 2)

    def test_utc_probe_prints_a_parsed_offset(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/elsewhen_probe.py"), "probe", "UTC"],
                                check=False, capture_output=True, text=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("UTC|", result.stdout)
        self.assertTrue(result.stdout.strip().endswith("|+0000") or "|+0000\n" in result.stdout)

    def test_zone_list_includes_utc(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/elsewhen_probe.py"), "zones"],
                                check=False, capture_output=True, text=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("UTC\n", result.stdout)
        self.assertNotIn("set-timezone", result.stdout)


if __name__ == "__main__":
    unittest.main()
