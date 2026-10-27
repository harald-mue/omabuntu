"""Launch-notice source contracts. These tests never start an application."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_clock_preview as preview


class LaunchFeedbackTests(unittest.TestCase):
    def notice(self):
        return (ROOT / "config/shell/preview/LaunchFeedback.qml").read_text()

    def test_notice_matches_the_two_second_osd_rule(self):
        text = self.notice()
        self.assertIn("interval: 2000", text)
        self.assertIn("interval: 15000", text)
        self.assertIn("toplevelCount() > root.launchToplevelCount", text)
        self.assertIn("Hyprland.activeToplevel !== root.launchActiveToplevel", text)
        self.assertIn("String.fromCodePoint(0xF14DE)", text)
        self.assertIn('WlrLayershell.namespace: "omabuntu-launch"', text)
        self.assertIn("WlrKeyboardFocus.None", text)
        self.assertIn("exclusiveZone: 0", text)
        self.assertIn("mask: Region {}", text)
        self.assertIn("Text.PlainText", text)
        self.assertEqual(text.count("Timer {"), 2)
        for forbidden in ("execDetached", "Process {", "ShellIpc", "hyprctl",
                          "omarchy-", "notify-send", "uwsm-app"):
            self.assertNotIn(forbidden, text)

    def test_grid_and_dock_share_the_notice_without_a_new_launcher(self):
        apps = (ROOT / "config/shell/preview/AppLauncher.qml").read_text()
        dock = (ROOT / "config/shell/preview/FloatingDock.qml").read_text()
        shell = (ROOT / "config/shell/preview/TrialShell.qml").read_text()
        labels = (ROOT / "config/shell/preview/I18n.qml").read_text()
        self.assertIn("root.launchFeedback.begin(String(results.get(index).name || \"\"))", apps)
        self.assertIn("DesktopEntries.byId(results.get(index).entryId)", apps)
        self.assertIn("entry.execute()", apps)
        self.assertNotIn("Timer {", apps)
        self.assertIn("root.launchFeedback.begin(String(entry.name || \"\"))", dock)
        self.assertIn("entry.execute()", dock)
        self.assertIn("LaunchFeedback.qml", shell)
        self.assertIn("launcher.launchFeedback = launchFeedback", shell)
        self.assertIn("dock.launchFeedback = launchFeedback", shell)
        self.assertIn("launchFeedback.destroy()", shell)
        self.assertIn('"appLibrary.launching"', labels)
        self.assertIn('"appLibrary.launchingApp"', labels)
        self.assertNotIn("de-DE", labels)

    def test_sealed_profile_includes_the_notice(self):
        files, _ = preview.verified_sources(ROOT)
        source = (ROOT / "config/shell/preview/LaunchFeedback.qml").read_bytes()
        self.assertEqual(files["LaunchFeedback.qml"], source)


if __name__ == "__main__":
    unittest.main()
