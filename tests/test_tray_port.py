"""Synthetic contracts; no Qt, DBus or host application is started."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_clock_preview as preview
import check_tray_port as checker


class TrayPortTests(unittest.TestCase):
    def test_original_tray_is_staged_byte_identically(self):
        files, meta = preview.verified_sources(ROOT)
        self.assertEqual(files["Port/Tray.qml"], (ROOT / "vendor/omarchy/shell/plugins/bar/widgets/Tray.qml").read_bytes())
        self.assertEqual(meta["upstream"]["Port/Tray.qml"]["stage_transform"], "none")
        self.assertIn(b"QsMenuOpener", files["Port/Tray.qml"])
        self.assertIn(b"root.enterSubmenu", files["Port/Tray.qml"])

    def test_owner_has_no_external_writes_or_commands(self):
        text = (ROOT / "config/shell/preview/PortTrayHost.qml").read_text()
        for forbidden in ("Process", "FileView", "execDetached", "Quickshell.Io", "SystemTray", "dispatch("):
            self.assertNotIn(forbidden, text)
        self.assertIn('id !== "omarchy.tray"', text)
        self.assertIn("entry.pinned.slice()", text)
        self.assertIn("Port.Tray", text)

    def test_profile_admits_only_the_reviewed_dependency_set(self):
        files, _ = preview.verified_sources(ROOT)
        for name in ("Port/Tray.qml", "Port/TrayModel.js", "Ui/PopupCard.qml", "Ui/Button.qml", "Commons/Border.qml"):
            self.assertIn(name, files)
        for name in ("Style.qml", "Color.qml", "I18n.qml"):
            self.assertEqual(files["Commons/" + name], (ROOT / "config/shell/preview" / name).read_bytes())
        self.assertNotIn("shell.qml", files)

    def test_cases_are_fixed_and_synthetic(self):
        self.assertEqual(checker.CASES, ("empty", "active", "passive", "preferences", "negative"))
        with self.assertRaises(ValueError):
            checker.fixture("native-service")
        self.assertIn("import \"FixtureTray\" as F", checker.fixture("active"))

    def test_classifier_rejects_missing_marker_warnings_and_crashes(self):
        good = "Configuration Loaded\n" + checker.MARKER + "::active\n"
        self.assertTrue(checker.classify("active", 0, good))
        self.assertFalse(checker.classify("active", -11, good))
        self.assertFalse(checker.classify("active", 0, "Configuration Loaded"))
        self.assertFalse(checker.classify("active", 0, good + " WARN unexpected\n"))
        self.assertFalse(checker.classify("active", 0, good + good))
        self.assertFalse(checker.classify("negative", 42, "ERROR unrelated\n"))
        self.assertTrue(checker.classify("negative", 42, "ERROR OMABUNTU_TRAY_ASSERT deliberate tray assertion\n"))


if __name__ == "__main__":
    unittest.main()
