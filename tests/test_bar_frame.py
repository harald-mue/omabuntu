"""Original section geometry and fixed-slot boundary contracts."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import bar_frame
import bar_frame_fixtures as fixtures
import check_clock_preview as preview


class BarFrameTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "vendor/omarchy/shell/plugins/bar/Bar.qml").read_bytes()
        self.frame = bar_frame.derive_frame(self.source).decode()

    def test_derived_frame_is_closed_pinned_source(self):
        files, meta = preview.verified_sources(ROOT)
        self.assertEqual(files["BarFrame.qml"].decode(), self.frame)
        self.assertEqual(meta["upstream"]["BarFrame.qml"]["stage_transform"], "fixed-horizontal-sections-v1")
        self.assertNotIn("BarFrame.qml", meta["authored"])

    def test_original_center_position_formulas_are_unchanged(self):
        for line in self.source.decode().splitlines():
            if any(key in line for key in ("centerBox.x - width", "centerBox.x + centerBox.width", "(sections.width - width) / 2", "(box.width - width) / 2")):
                self.assertIn(line, self.frame)
        self.assertIn("anchors.leftMargin: Style.space(8)", self.frame)
        self.assertIn("anchors.rightMargin: Style.space(8)", self.frame)
        self.assertIn('fixedEdge: "start"', self.frame)
        self.assertIn('fixedEdge: "end"', self.frame)

    def test_registry_drag_and_commands_are_not_staged(self):
        for forbidden in ("Process {", "FileView {", "ShellIpc", "Quickshell.Io", "WidgetPool {", "CenterGestureArea {", "DropOutline {", "registerCenterBox(", "root.barDragSource", "execDetached"):
            self.assertNotIn(forbidden, self.frame)
        self.assertIn("required property Component leftContent", self.frame)
        self.assertIn("sourceComponent: region ===", self.frame)
        self.assertNotIn("source:", self.frame)
        self.assertIn("readonly property bool centerBesideRight: false", self.frame)

    def test_narrow_layout_clips_sides_not_the_center(self):
        self.assertIn("Math.max(0, root.centerStart - 16)", self.frame)
        self.assertIn("Math.max(0, root.width - root.centerEnd - 16)", self.frame)
        self.assertIn('clip: region === "left" || region === "right"', self.frame)
        self.assertIn("readonly property real centerStart: beginList.x", self.frame)
        self.assertIn("readonly property real centerEnd: endList.x + endList.width", self.frame)

    def test_live_trial_uses_sections_not_the_sealed_preview_overlay(self):
        text = (ROOT / "config/shell/preview/TrialPanel.qml").read_text()
        self.assertIn("BarFrame {", text)
        self.assertNotIn("PreviewContent {", text)
        self.assertIn("frame.centerStart - 16", text)
        self.assertIn("ExclusionMode.Ignore : ExclusionMode.Auto", text)
        self.assertNotIn("WlrKeyboardFocus.Exclusive", text)
        self.assertIn('readonly property int barSize: 26', text)

    def test_left_adapter_is_workspaces_only(self):
        text = (ROOT / "config/shell/preview/LiveStatus.qml").read_text()
        self.assertNotIn("leftMargin: 224", text)
        self.assertNotIn("leftMargin: 268", text)
        self.assertNotIn("parent.width / 2 - 288", text)
        self.assertNotIn('text: "Apps"', text)
        self.assertNotIn("windowTitle", text)
        self.assertNotIn("activeToplevel", text)
        self.assertIn("WorkspaceSwitcher {", text)
        self.assertIn("hl.dsp.focus({ workspace = ", text)
        self.assertIn("if (id < 1 || id > 6) return", text)

    def test_extractors_fail_closed_when_source_boundaries_change(self):
        with self.assertRaises(ValueError):
            bar_frame.derive_frame(self.source.replace(b"WidgetPool { id: horizontalPool }", b"changed"))
        with self.assertRaises(ValueError):
            bar_frame.derive_frame(self.source.replace(b"visible: box.dragHere", b"changed"))

    def test_fixed_fixtures_are_synthetic_and_reject_spurious_success(self):
        self.assertEqual(len(fixtures.CASES), 7)
        with self.assertRaises(ValueError):
            fixtures.fixture("reload-desktop")
        self.assertIn("No startup dispatch allowed", fixtures.HYPRLAND)
        self.assertIn("right section does not overlap center", fixtures.fixture("narrow"))
        good = "Configuration Loaded\n" + fixtures.MARKER + "::laptop\n"
        self.assertTrue(fixtures.classify("laptop", 0, good))
        self.assertFalse(fixtures.classify("laptop", 0, good + "WARN overlap\n"))
        self.assertFalse(fixtures.classify("laptop", -11, good))
        self.assertFalse(fixtures.classify("negative", 42, "ERROR unrelated\n"))
        self.assertTrue(fixtures.classify("negative", 42, "ERROR deliberate frame assertion\n"))


if __name__ == "__main__":
    unittest.main()
