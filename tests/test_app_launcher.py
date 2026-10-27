"""Cold catalog regressions; unit tests never open a native app panel."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import app_launcher_fixtures as fixtures
import check_clock_preview as preview


class AppLauncherTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "config/shell/preview/AppLauncher.qml").read_bytes()

    def test_visible_panel_tracks_completed_catalog_publication(self):
        text = self.source.decode()
        self.assertIn("target: DesktopEntries", text)
        self.assertIn("function onApplicationsChanged() { if (root.shown) root.rebuild() }", text)
        self.assertNotIn("Timer {", text)
        self.assertNotIn("sleep", text)

    def test_existing_first_open_geometry_and_launch_route_are_preserved(self):
        text = self.source.decode()
        self.assertIn("root.screen = root.focusedScreen()", text)
        self.assertIn("WlrKeyboardFocus.OnDemand", text)
        self.assertNotIn("WlrKeyboardFocus.Exclusive", text)
        self.assertIn("DesktopEntries.byId(results.get(index).entryId)", text)
        self.assertIn("entry.execute()", text)
        self.assertIn('name: "apps"', text)
        self.assertIn("root.filterText = \"\"", text)
        self.assertIn("visibleRows: 4", text)

    def test_fixture_uses_the_real_model_and_grid_without_native_ownership(self):
        fixture = fixtures.fixture_launcher(self.source).decode()
        self.assertIn("Window {", fixture)
        self.assertNotIn("PanelWindow {", fixture)
        self.assertNotIn("GlobalShortcut {", fixture)
        self.assertNotIn("WlrLayershell.", fixture)
        start, end = "  function rebuild() {", "  function launchSelected() {"
        native = self.source.decode()
        original = native[native.index(start):native.index(end)]
        self.assertIn(original.replace("DesktopEntries", "FixtureEntries.DesktopEntries"), fixture)
        self.assertIn("GridView {", fixture)
        self.assertIn("target: FixtureEntries.DesktopEntries", fixture)
        native_fixture = fixtures.fixture_launcher(self.source, native=True).decode()
        self.assertIn("target: DesktopEntries", native_fixture)
        self.assertNotIn("target: FixtureEntries.DesktopEntries", native_fixture)
        with self.assertRaises(ValueError):
            fixtures.fixture_launcher(self.source.replace(b"PanelWindow {", b"changed"))

    def test_cold_fixture_publishes_without_reopening_or_executing_apps(self):
        self.assertEqual(len(fixtures.CASES), 7)
        text = fixtures.fixture("cold")
        self.assertIn("initial cold list is empty", text)
        self.assertIn("first opening refreshes after publication", text)
        self.assertIn("grid.itemAtIndex(0)", text)
        self.assertIn("late data preserves typed filter", text)
        self.assertIn("Application execution/lookup forbidden", fixtures.ENTRIES)
        self.assertIn("applicationsChanged()", fixtures.ENTRIES)
        with self.assertRaises(ValueError):
            fixtures.fixture("native-apps")

    def test_classifier_rejects_unrelated_failures_and_warnings(self):
        good = "Configuration Loaded\n" + fixtures.MARKER + "::cold\n"
        self.assertTrue(fixtures.classify("cold", 0, good))
        self.assertFalse(fixtures.classify("cold", 42, good))
        self.assertFalse(fixtures.classify("cold", 0, good + "WARN layout\n"))
        self.assertFalse(fixtures.classify("negative", 42, "ERROR unrelated\n"))
        self.assertTrue(fixtures.classify("negative", 42, "ERROR deliberate launcher assertion\n"))

    def test_closed_profile_contains_the_fixed_launcher(self):
        files, _ = preview.verified_sources(ROOT)
        self.assertEqual(files["AppLauncher.qml"], self.source)


if __name__ == "__main__":
    unittest.main()
