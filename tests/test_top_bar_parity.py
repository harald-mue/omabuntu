"""Top bar parity contracts: menu mark, keyboard layout, frame/theme looks."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

SPEC = importlib.util.spec_from_file_location("check_clock_preview", ROOT / "tools/check_clock_preview.py")
checker = importlib.util.module_from_spec(SPEC)
with patch.object(sys, "path", [str(ROOT / "tools"), *sys.path]):
    SPEC.loader.exec_module(checker)


def read(relative):
    return (ROOT / relative).read_text()


class MenuMarkTests(unittest.TestCase):
    def test_record_matches_authored_shape(self):
        record = json.loads(read("upstream/omarchy-mark.json"))
        self.assertEqual(record["schema_version"], 1)
        source = record["source"]
        self.assertEqual(source["commit"], checker.COMMIT)
        self.assertEqual(source["path"], "default/fonts/omarchy/omarchy.ttf")
        self.assertEqual(source["license"], "MIT")
        self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
        glyph = record["glyph"]
        self.assertEqual(glyph["codepoint"], "U+E900")
        self.assertEqual(glyph["units_per_em"], 1024)
        self.assertEqual(glyph["contours"], 5)
        # The authored shape draws exactly the recorded outline.
        mark = read("config/shell/preview/OmarchyMark.qml")
        self.assertIn('path: "%s"' % glyph["svg_path"], mark)
        # Third-party agent glyphs stay unrecorded; only the own mark is.
        self.assertNotIn("E901", json.dumps(record))
        self.assertIn("not imported", record["limits"])

    def test_record_source_bytes_match_pinned_font(self):
        font = ROOT / "work/bar-parity/03ff1eff/default/fonts/omarchy/omarchy.ttf"
        if not font.is_file():
            self.skipTest("private pinned font copy absent")
        record = json.loads(read("upstream/omarchy-mark.json"))["source"]
        data = font.read_bytes()
        self.assertEqual(record["bytes"], len(data))
        self.assertEqual(record["sha256"], hashlib.sha256(data).hexdigest())

    def test_menu_button_uses_original_button_slot(self):
        text = read("config/shell/preview/MenuButton.qml")
        self.assertIn("BarIconButton {", text)
        self.assertIn("iconComponent: Component {", text)
        self.assertIn("OmarchyMark {", text)
        # Upstream menu behavior: left opens the menu, right opens a terminal.
        self.assertIn("Qt.RightButton", text)
        self.assertIn("xdg-terminal-exec", text)
        self.assertNotIn("\\ue900", text)


class KeyboardLayoutTests(unittest.TestCase):
    def setUp(self):
        self.parent = (ROOT / "vendor/omarchy/shell/plugins/bar/widgets/KeyboardLayout.qml").read_bytes()
        self.mirror = (ROOT / "config/shell/preview/KeyboardLayout.qml").read_bytes()

    def test_vendored_parent_matches_pinned_blob(self):
        record = json.loads(read("upstream/clock-preview.json"))["upstream"]["KeyboardLayout.qml"]
        self.assertEqual(record["bytes"], len(self.parent))
        self.assertEqual(record["sha256"], hashlib.sha256(self.parent).hexdigest())
        self.assertEqual(record["source_modifications"], [])

    def test_mirror_is_the_reviewed_splice_of_the_parent(self):
        with patch.object(sys, "path", [str(ROOT / "tools"), *sys.path]):
            import keyboard_frontend
        self.assertEqual(self.mirror, keyboard_frontend.derive_keyboard_layout(self.parent))
        parent_text, mirror_text = self.parent.decode(), self.mirror.decode()
        # Exactly one reviewed deviation: the alwaysShow visibility setting.
        self.assertNotIn("alwaysShow", parent_text)
        self.assertEqual(mirror_text.count("alwaysShow"), 2)
        self.assertIn('root.setting("alwaysShow", true)', mirror_text)
        # The upstream parent otherwise stays intact, model included.
        for witness in ("KeyboardLayoutModel.showIndicator(layoutLabel, multipleLayouts, multipleInputs)",
                        "hyprctl switchxkblayout", "cycleLayout", "xkbcli list --load-exotic"):
            self.assertEqual(parent_text.count(witness), mirror_text.count(witness))

    def test_restricted_input_method_state_spawns_nothing(self):
        text = read("config/shell/preview/InputMethodState.qml")
        self.assertIn("readonly property var state: ({})", text)
        self.assertIn("return false", text)
        for forbidden in ("Process", "Quickshell", "OMARCHY_PATH", "execDetached", "command:"):
            self.assertNotIn(forbidden, text)

    def test_bar_mounts_keyboard_layout_after_tray(self):
        text = read("config/shell/preview/TrialPanel.qml")
        self.assertLess(text.index("PortTrayHost {"), text.index("KeyboardLayout {"))
        self.assertIn("bar: clockBar", text)


class BarRunTests(unittest.TestCase):
    SCRIPT = read("config/shell/preview/BarRun.js")

    def allowed(self, command):
        """Python mirror of BarRun.allowed; the JS patterns are asserted below."""
        parts = [segment.strip() for segment in str(command).split(";")]
        if not command or not all(parts):
            return False
        switch = re.compile(r"^hyprctl switchxkblayout ('[^']*'|\"[^\"]*\"|\S+) [0-9]+$")
        return all(switch.match(p) or p == "xdg-terminal-exec" for p in parts)

    def test_allowlist_patterns_stay_in_the_script(self):
        self.assertIn("/^hyprctl switchxkblayout ('[^']*'|\"[^\"]*\"|\\S+) [0-9]+$/", self.SCRIPT)
        self.assertIn(r"/^xdg-terminal-exec$/", self.SCRIPT)
        self.assertIn('text.split(";")', self.SCRIPT)

    def test_generated_cycle_commands_pass_and_others_refuse(self):
        # What cycleLayout builds: shellQuote'd device names joined by '; '.
        cycle = "; ".join("hyprctl switchxkblayout '%s' 0" % name
                         for name in ("at-translated-set-2-keyboard", "razer-razer-deathadder-essential-keyboard"))
        self.assertTrue(self.allowed(cycle))
        self.assertTrue(self.allowed("xdg-terminal-exec"))
        self.assertTrue(self.allowed("hyprctl switchxkblayout 'a-b c' 3"))
        for refused in ("", "hyprctl dispatch workspace 2", "hyprctl switchxkblayout atkbd next",
                        "hyprctl switchxkblayout atkbd 0; sudo rm -rf /",
                        "xdg-terminal-exec; xdg-terminal-exec && sudo id",
                        "omarchy-shell shell toggle omarchy.menu",
                        "bash -lc 'reboot'"):
            self.assertFalse(self.allowed(refused), refused)


class FrameLookTests(unittest.TestCase):
    def test_theme_state_feeds_the_palette(self):
        text = read("config/shell/preview/Color.qml")
        self.assertIn("theme.json", text)
        self.assertIn('foreground = hexColor(parsed.palette, "foreground", foreground)', text)
        self.assertIn('urgent = hexColor(parsed.palette, "red", urgent)', text)
        self.assertIn("watchChanges: true", text)
        # The fallback tokens stay the sealed defaults.
        self.assertIn('property color background: "#101315"', text)

    def test_looks_follow_upstream_names(self):
        text = read("config/shell/preview/TrialPanel.qml")
        for look in ("opaque", "glassy", "none"):
            self.assertIn('"%s"' % look, text)
        self.assertIn("Math.min(themeBackground.a, 0.35)", text)
        self.assertIn('bars.backgroundLook === "glassy"', text)
        self.assertIn('bars.backgroundLook === "none"', text)
        # No blur or compositor keyword is managed: Hyprland 0.56 has no
        # live layerrule removal, so blur stays the user's own setting.
        self.assertNotIn("hyprctl", text)

    def test_bar_off_parks_without_exclusion(self):
        text = read("config/shell/preview/TrialPanel.qml")
        self.assertIn("toggles/bar-off", text)
        self.assertIn("bars.barHidden ? -26 : 0", text)
        self.assertIn("bars.barHidden ? ExclusionMode.Ignore : ExclusionMode.Auto", text)

    def test_bar_json_state_schema_is_watched(self):
        text = read("config/shell/preview/TrialPanel.qml")
        self.assertIn("bar.json", text)
        self.assertIn("parsed.schema_version !== 1", text)
        self.assertIn("backgroundLook", text)


if __name__ == "__main__":
    unittest.main()
