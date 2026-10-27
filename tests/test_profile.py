"""Mocked native-profile validation tests; no compositor is started."""

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("profile_doctor", ROOT / "tools" / "omabuntu.py")
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)

EXPECTED_BUILD = {
    "version": "0.56.2", "commit": "efb50993780079460b0cbed1363e2166a2de1d9f", "dirty": False,
}


class ProfileTests(unittest.TestCase):
    def setUp(self):
        work = ROOT / "work"
        work.mkdir(mode=0o700, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="profile-tests-", dir=work)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.profile = self.root / "config" / "hypr" / "minimal.lua"
        self.profile.parent.mkdir(parents=True)
        self.profile.write_text("-- Synthetic profile\n")

    def check(self, build=None, native_status="ok", version_status="ok"):
        calls = []

        def run(args, **kwargs):
            calls.append((args, kwargs))
            if "--version-json" in args:
                return {"status": version_status, "stdout": json.dumps(EXPECTED_BUILD if build is None else build)}
            return {"status": native_status, "stdout": "synthetic validation result", "stderr": ""}

        with patch.object(doctor.shutil, "which", return_value="/usr/bin/Hyprland"):
            output, report = doctor.check_profile(self.root, run)
        return output, report, calls

    def test_expected_binary_validates_only_the_bundled_profile(self):
        output, report, calls = self.check()
        self.assertEqual(report["status"], "passed")
        snapshot = output.parent / "minimal.lua"
        self.assertEqual(calls[-1][0], ["/usr/bin/Hyprland", "--verify-config", "--config", str(snapshot)])
        self.assertEqual(snapshot.read_bytes(), self.profile.read_bytes())
        self.assertRegex(report["profile_sha256"], r"^[a-f0-9]{64}$")
        self.assertEqual(snapshot.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(output.read_text())["status"], "passed")
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_process_environment_is_isolated_from_the_live_desktop(self):
        with patch.dict(os.environ, {"DISPLAY": ":99", "WAYLAND_DISPLAY": "private", "SECRET": "synthetic"}):
            _, _, calls = self.check()
        environment = calls[-1][1]["env"]
        self.assertTrue(calls[-1][1]["cwd"].is_relative_to(self.root / "work"))
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "SECRET", "HYPRLAND_INSTANCE_SIGNATURE"):
            self.assertNotIn(key, environment)
        for key in ("HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR"):
            directory = Path(environment[key])
            self.assertTrue(directory.is_relative_to(self.root / "work"))
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)

    def test_unknown_version_commit_or_dirty_build_blocks_native_execution(self):
        for changes in ({"version": "0.55.0"}, {"commit": "unknown"}, {"dirty": True}):
            with self.subTest(changes=changes):
                _, report, calls = self.check(build={**EXPECTED_BUILD, **changes})
                self.assertEqual(report["status"], "blocked")
                self.assertEqual(len(calls), 1)

    def test_invalid_version_json_blocks_native_execution(self):
        _, report, calls = self.check(build=[])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(len(calls), 1)

    def test_failed_version_probe_blocks_native_execution(self):
        _, report, calls = self.check(version_status="failed")
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(len(calls), 1)

    def test_native_parse_failure_or_timeout_is_not_a_pass(self):
        for status in ("failed", "timeout", "error"):
            with self.subTest(status=status):
                _, report, _ = self.check(native_status=status)
                self.assertEqual(report["status"], "failed")

    def test_missing_binary_is_reported_without_execution(self):
        with patch.object(doctor.shutil, "which", return_value=None):
            _, report = doctor.check_profile(self.root, lambda *args, **kwargs: self.fail("Unexpected command"))
        self.assertEqual(report["status"], "blocked")

    def test_symlinked_profile_is_refused(self):
        self.profile.unlink()
        self.profile.symlink_to(ROOT / "config" / "hypr" / "minimal.lua")
        _, report, calls = self.check()
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(len(calls), 1)

    def test_report_category_cannot_escape_work_directory(self):
        with self.assertRaises(ValueError):
            doctor.new_report_directory(self.root, "../outside")

    def test_profile_disables_the_hyprland_logo_by_default(self):
        profile = (ROOT / "config" / "hypr" / "minimal.lua").read_text()
        self.assertRegex(profile, r"misc\s*=\s*\{\s*disable_hyprland_logo\s*=\s*true\s*,?\s*\}")

    def test_prototype_has_no_autostart_or_external_reference_loading(self):
        profile = (ROOT / "config" / "hypr" / "minimal.lua").read_text()
        code = "\n".join(line.split("--", 1)[0] for line in profile.splitlines())
        for token in ("hl.on(", "hl.exec_cmd(", "os.execute(", "io.popen(", "require(", "dofile(", "hl.plugin("):
            self.assertNotIn(token, code)
        self.assertNotIn("/home/", code)
        self.assertIn('kb_layout = "de"', code)
        self.assertIn("for workspace = 1, 10 do", code)
        self.assertIn('hl.dsp.exec_cmd("ghostty")', code)


if __name__ == "__main__":
    unittest.main()
