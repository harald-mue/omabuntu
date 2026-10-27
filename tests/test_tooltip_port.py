"""Tooltip source/lifecycle contracts; unit tests never touch a desktop."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_clock_preview as preview
import tooltip_port as port
import tooltip_port_fixtures as fixtures


class TooltipPortTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "vendor/omarchy/shell/plugins/bar/Bar.qml").read_bytes()

    def test_owner_does_not_force_an_unanchored_controls_tooltip(self):
        owner = (ROOT / "config/shell/preview/PortTrayHost.qml").read_text()
        self.assertNotIn("ToolTip {", owner)
        self.assertNotIn("tooltip.visible = true", owner)
        self.assertIn("tooltipHost.showTooltip(item, text)", owner)
        self.assertIn("tooltipHost.hideTooltip(item)", owner)
        self.assertIn("BarTooltip { host: tooltipHost }", owner)

    def test_popup_uses_original_anchor_and_independent_surface(self):
        text = port.derive_window(self.source).decode()
        self.assertIn("PopupWindow {", text)
        self.assertIn("host.tooltipTarget.QsWindow.window", text)
        self.assertIn("window: barWindow", text)
        self.assertIn("adjustment: PopupAdjustment.Slide", text)
        self.assertIn("target.height + 6", text)
        self.assertIn("barWindow.contentItem.mapFromItem(target, localX, localY)", text)
        self.assertIn("textFormat: Text.PlainText", text)
        self.assertNotIn("keyboardFocus", text)
        self.assertNotIn("grab:", text)

    def test_bubble_markup_is_original_except_owner_name(self):
        parent = self.source.decode()
        original = parent[parent.index("      BorderSurface {\n        id: tooltipBubble"):parent.index("    Component {\n      id: horizontalBar")]
        original = "\n".join(line[4:] if line.startswith("    ") else line for line in original.splitlines())
        self.assertIn(original.replace("root.", "host."), port.derive_window(self.source).decode())

    def test_original_empty_target_delay_and_generation_guards(self):
        text = port.derive_host(self.source).decode()
        for token in ("!targetTooltipHovered(target) || !text", "interval: 400", "interval: 100",
                      "request !== tooltipRequest", "tooltipTarget !== target && pendingTooltipTarget !== target",
                      "tooltipTimer.stop()", "target.tooltipHovered === true"):
            self.assertIn(token, text)
        for forbidden in ("Process {", "FileView {", "ShellIpc", "Quickshell.Io", "execDetached", "barHiddenProbe"):
            self.assertNotIn(forbidden, text)

    def test_staging_checks_exact_source_and_derived_hashes(self):
        files, meta = preview.verified_sources(ROOT)
        self.assertEqual(files["BarTooltip.qml"], port.derive_window(self.source))
        self.assertEqual(files["BarTooltipHost.qml"], port.derive_host(self.source))
        for target in ("BarTooltip.qml", "BarTooltipHost.qml"):
            self.assertEqual(meta["upstream"][target]["path"], "shell/plugins/bar/Bar.qml")
            self.assertEqual(meta["upstream"][target]["source_modifications"], [])
        with self.assertRaises(ValueError):
            port.derive_window(self.source.replace(b"      id: tooltipWindow", b"      changed"))
        with self.assertRaises(ValueError):
            port.derive_host(b"not the original bar")

    def test_fixed_offscreen_cases_and_negative_control(self):
        self.assertEqual(len(fixtures.CASES), 7)
        with self.assertRaises(ValueError):
            fixtures.fixture("host-pointer")
        text = fixtures.fixture("stale-hide")
        self.assertIn("host.hideTooltip(first)", text)
        self.assertIn("400ms delay respected", text)
        self.assertNotIn("Services.Pipewire", text)
        self.assertNotIn("Services.Networking", text)
        self.assertIn("textFormat: Text.PlainText", fixtures.bubble_fixture(port.derive_window(self.source)).decode())

    def test_classifier_rejects_warnings_and_unexpected_errors(self):
        good = "Configuration Loaded\n" + fixtures.MARKER + "::empty\n"
        self.assertTrue(fixtures.classify("empty", 0, good))
        self.assertFalse(fixtures.classify("empty", 0, good + "WARN clipped popup\n"))
        self.assertFalse(fixtures.classify("empty", -11, good))
        self.assertFalse(fixtures.classify("negative", 42, "ERROR unrelated\n"))
        self.assertTrue(fixtures.classify("negative", 42, "ERROR deliberate tooltip assertion\n"))


if __name__ == "__main__":
    unittest.main()
