"""Calendar derivation contracts. Unit tests never start Qt or a host session."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_clock_preview as preview
import clock_frontend as frontend


class ClockCalendarTests(unittest.TestCase):
    def test_mirrors_match_derivation(self):
        panel = (ROOT / "vendor/omarchy/shell/plugins/panels/clock/Panel.qml").read_bytes()
        host = (ROOT / "vendor/omarchy/shell/plugins/panels/clock/BarWidget.qml").read_bytes()
        self.assertEqual(frontend.derive_calendar(panel), (ROOT / "config/shell/preview/CalendarPanel.qml").read_bytes())
        self.assertEqual(frontend.derive_host(host), (ROOT / "config/shell/preview/ClockControlView.qml").read_bytes())

    def test_calendar_keeps_the_original_surface_without_routes(self):
        text = (ROOT / "config/shell/preview/CalendarPanel.qml").read_text()
        for token in ("monthGrid", "yearDone", "birthYear", "toggleWeekStart", "moveMonth", "Memento Mori", "KeyboardPanel"):
            self.assertIn(token, text)
        for forbidden in ("Process {", "ShellIpc", "Quickshell.Io", "omarchy-", "execDetached", "timedatectl", "sudo", "FileView"):
            self.assertNotIn(forbidden, text)
        self.assertIn("property alias controller: panelController", text)
        self.assertNotIn("\nPanel {", text)

    def test_host_opens_the_calendar_and_cycles_the_label(self):
        text = (ROOT / "config/shell/preview/ClockControlView.qml").read_text()
        self.assertIn('source: Qt.resolvedUrl("CalendarPanel.qml")', text)
        self.assertIn("function cycleFormat()", text)
        self.assertIn("function togglePanel()", text)
        self.assertNotIn("function refresh(): void", text)
        for forbidden in ("ShellIpc", "Quickshell.Io", ".run(", "omarchy-menu", "timedatectl", "sudo", "Process {"):
            self.assertNotIn(forbidden, text)

    def test_changed_panel_header_is_rejected(self):
        data = (ROOT / "vendor/omarchy/shell/plugins/panels/clock/Panel.qml").read_bytes()
        with self.assertRaises(ValueError):
            frontend.derive_calendar(data.replace(b'moduleName: "omarchy.clock"', b'moduleName: "other"', 1))

    def test_sealed_label_stays_inactive(self):
        files, _ = preview.verified_sources(ROOT)
        self.assertNotIn(b"CalendarPanel.qml", files["ClockLabel.qml"])
        self.assertNotIn(b"togglePanel", files["ClockLabel.qml"])
        self.assertNotIn(b"Panel.qml", files["ClockLabel.qml"])

    def test_trial_bar_opens_the_calendar_without_a_privileged_route(self):
        text = (ROOT / "config/shell/preview/TrialPanel.qml").read_text()
        self.assertIn("ClockControlView {", text)
        self.assertNotIn("ClockLabel {", text)
        self.assertIn("popoutState: barBus", text)
        self.assertIn('id !== "omarchy.clock"', text)
        self.assertNotIn("enabled: false", text)
        for forbidden in ("omarchy-menu", "timedatectl", "sudo", "ShellIpc"):
            self.assertNotIn(forbidden, text)
        # The one reviewed Process is the upstream bar-off flag probe, not a
        # calendar route: its command only tests a flag file's presence.
        self.assertEqual(text.count("property Process"), 1)
        self.assertIn("toggles/bar-off", text)

    def test_style_and_labels_cover_the_grid(self):
        style = (ROOT / "config/shell/preview/Style.qml").read_text()
        self.assertIn("readonly property int hairline:", style)
        self.assertIn("function normalBorderFor(", style)
        labels = (ROOT / "config/shell/preview/I18n.qml").read_text()
        for key in ("clock.monthYear", "clock.backToToday", "clock.weekShort", "clock.life", "clock.toggleFormat"):
            self.assertIn('"%s"' % key, labels)

    def test_profile_records_the_derivation(self):
        files, meta = preview.verified_sources(ROOT)
        self.assertEqual(meta["upstream"]["CalendarPanel.qml"]["stage_transform"], "clock-calendar-v1")
        self.assertEqual(meta["upstream"]["ClockControlView.qml"]["stage_transform"], "clock-calendar-host-v1")
        self.assertEqual(meta["upstream"]["ClockLabel.qml"]["stage_transform"], "readonly-clock-v1")
        self.assertEqual(files["CalendarPanel.qml"], (ROOT / "config/shell/preview/CalendarPanel.qml").read_bytes())
        self.assertEqual(files["ClockControlView.qml"], (ROOT / "config/shell/preview/ClockControlView.qml").read_bytes())


if __name__ == "__main__":
    unittest.main()
