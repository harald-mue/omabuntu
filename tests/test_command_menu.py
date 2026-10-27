"""Contracts for the command menu offscreen fixture derivation."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_command_menu as checker


SURFACE = ROOT / "config/shell/preview/CommandMenu.qml"


class DerivationTests(unittest.TestCase):
    def setUp(self):
        self.text = SURFACE.read_text()

    def test_derivation_keeps_the_reviewed_logic(self):
        derived = checker.derive_surface(self.text)
        for kept in ("function rebuildDisplay()", "function activateIndex(index)",
                     "function openRoute(route)", "MenuModel.swapProviderRows",
                     "Process {", "OMABUNTU_MENU_HELPER", "probeCount()"):
            self.assertIn(kept, derived)
        self.assertIn("Window {", derived)

    def test_derivation_removes_host_registration(self):
        derived = checker.derive_surface(self.text)
        for forbidden in ("PanelWindow", "GlobalShortcut", "WlrLayershell", "Hyprland",
                          "focusedScreen", "ExclusionMode"):
            self.assertNotIn(forbidden, derived)

    def test_changed_surface_is_rejected(self):
        with self.assertRaises(ValueError):
            checker.derive_surface(self.text.replace("PanelWindow {", "Item {"))
        with self.assertRaises(ValueError):
            checker.derive_surface(self.text.replace("import Quickshell.Hyprland\n", ""))

    def test_probe_drives_the_full_surface(self):
        for label in ("root row count", "gate refusal", "when hides the row",
                      "cursor skips the disabled row", "theme row opens the picker",
                      "search rows", "system route"):
            self.assertIn(label, checker.PROBE)
        self.assertIn(checker.MARKER, checker.PROBE)

    def test_display_rows_supply_font_role_for_every_delegate(self):
        model = (ROOT / 'config/shell/preview/MenuModel.js').read_text()
        display = model.split('function displayRow(', 1)[1].split('\n}', 1)[0]
        self.assertIn('font: entry.font || ""', display)
        self.assertIn('required property string font', self.text)
        self.assertIn('font: String(row.font || "")', self.text)

    def test_fixture_rejects_delegate_creation_errors(self):
        self.assertFalse(checker.log_is_clean('Cannot create delegate'))
        self.assertFalse(checker.log_is_clean('Required property font was not initialized'))
        self.assertFalse(checker.log_is_clean('ReferenceError: example'))
        self.assertTrue(checker.log_is_clean('Configuration Loaded'))

    def test_overlay_rows_are_action_rows(self):
        for entry in ("learn.hidden-row", "learn.disabled-row", "learn.checked-row"):
            self.assertIn(entry, checker.OVERLAY)
        self.assertIn('"action"', checker.OVERLAY)


if __name__ == "__main__":
    unittest.main()
