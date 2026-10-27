"""Contracts for the image picker offscreen fixture derivation."""
import re
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_image_picker as checker


SURFACE = ROOT / "config/shell/preview/ImagePicker.qml"


class DerivationTests(unittest.TestCase):
    def setUp(self):
        self.text = SURFACE.read_text()

    def test_derivation_keeps_the_reviewed_logic(self):
        derived = checker.derive_surface(self.text)
        for kept in ("function loadProviderRows(", "function applySelected()",
                     "function updateFilter(", "function selectAdjacent(direction)",
                     "ImagePickerModel.visibleWindow", "ImagePickerModel.syncWindow",
                     "MultiEffect", "Shape {", "OMABUNTU_MENU_HELPER",
                     "maybeReveal", "applySelected"):
            self.assertIn(kept, derived)
        self.assertIn("Window {", derived)

    def test_derivation_removes_host_registration(self):
        derived = checker.derive_surface(self.text)
        for forbidden in ("PanelWindow", "WlrLayershell", "ExclusionMode"):
            self.assertNotIn(forbidden, derived)

    def test_changed_surface_is_rejected(self):
        with self.assertRaises(ValueError):
            checker.derive_surface(self.text.replace("PanelWindow {", "Item {"))
        with self.assertRaises(ValueError):
            checker.derive_surface(self.text.replace("import Quickshell.Wayland\n", ""))

    def test_probe_drives_the_full_surface(self):
        for label in ("theme row count is 23", "current theme selected",
                      "palette colors on the row", "filter narrows to Tokyo Night",
                      "right arrow moves the carousel", "theme apply closes the picker",
                      "background row count", "background note",
                      "escape closes the picker"):
            self.assertIn(label, checker.PROBE)
        self.assertIn(checker.MARKER, checker.PROBE)

    def test_surface_paints_themes_from_the_recorded_palette(self):
        self.assertIn("colors.background", self.text)
        self.assertIn("colors.accent", self.text)
        self.assertNotIn("ffmpegthumbnailer", self.text)
        self.assertNotIn("omarchy-theme-remove", self.text)
        self.assertNotIn("execDetached", self.text)

    def test_background_note_only_for_an_unapplied_choice(self):
        # A running hyprpaper returns applied: true, so the stale "not
        # approved" note must not appear any more; an unapplied choice keeps
        # the recording note and the picker open.
        self.assertIn('payload.applied !== true', self.text)
        self.assertIn('root.note = "Background recorded.', self.text)
        self.assertNotIn('No wallpaper daemon is approved yet', self.text)

    def test_theme_rows_use_the_imported_preview_with_palette_fallback(self):
        # Themes mode takes the imported preview image from the provider row;
        # a theme without one keeps the palette chips as the fallback.
        self.assertIn('thumbnailPath: root.mode === "themes" ? String(row.image || "") : filePath',
                      self.text)
        self.assertIn('visible: root.mode === "themes" && !item.thumbnailPath', self.text)
        self.assertNotIn('visible: root.mode === "backgrounds"', self.text)


if __name__ == "__main__":
    unittest.main()
