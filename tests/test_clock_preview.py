"""Sealed clock-preview contracts; unit tests never start Qt or a host session."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_clock_preview", ROOT / "tools/check_clock_preview.py")
checker = importlib.util.module_from_spec(SPEC)
with patch.object(sys, "path", [str(ROOT / "tools"), *sys.path]):
    SPEC.loader.exec_module(checker)


class ClockPreviewTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "work").mkdir(mode=0o700, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "work")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        names = ["upstream/omarchy-source.json", "upstream/clock-preview.json",
                 "licenses/Omarchy-MIT.txt", "vendor/omarchy/LICENSE", *checker.AUTHORED.values(),
                 "config/shell/preview/AudioOutputView.qml",
                 "config/shell/preview/NetworkControlView.qml",
                 "config/shell/preview/WorkspaceSwitcher.qml",
                 "config/shell/preview/KeyboardLayout.qml",
                 "config/shell/preview/CalendarPanel.qml",
                 "config/shell/preview/ClockControlView.qml",
                 *("config/shell/preview/" + name for name in checker.ELSEWHEN_TRANSFORMS),
                 *("config/shell/preview/" + name for name in checker.DESKTOP_TRANSFORMS),
                 *("vendor/omarchy/" + source for source in checker.UPSTREAM.values())]
        for name in names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)

    def test_default_plan_does_not_run(self):
        with patch.object(checker, "run_checks") as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(checker.main([]), 0)
        run.assert_not_called()

    def test_run_requires_build(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            checker.main(["--run"])

    def test_upstream_bytes_unchanged_and_clock_derived_before_staging(self):
        files, meta = checker.verified_sources(self.root)
        original = (ROOT / "vendor/omarchy/shell/plugins/panels/clock/BarWidget.qml").read_bytes()
        self.assertIn(b"Panel.qml", original)
        self.assertNotIn(b"Panel.qml", files["ClockLabel.qml"])
        for forbidden in (b"ShellIpc", b"cycleFormat", b"Quickshell.Io", b"updateEntryInline", b".run("):
            self.assertIn(forbidden, original)
            self.assertNotIn(forbidden, files["ClockLabel.qml"])
        self.assertIn(b"function formatted", files["ClockLabel.qml"])
        self.assertIn(b"SystemClock", files["ClockLabel.qml"])
        for target, source in checker.UPSTREAM.items():
            if meta["upstream"][target]["stage_transform"] == "none":
                self.assertEqual(files[target], (ROOT / "vendor/omarchy" / source).read_bytes())
        self.assertEqual(meta["production_catalog"], "empty")
        self.assertEqual(meta["host_activation"], "separate-approval-required")

    def test_changed_upstream_or_extraction_rejected(self):
        path = self.root / "vendor/omarchy/shell/plugins/panels/clock/BarWidget.qml"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(checker.builder.BuildError, "source changed"):
            checker.verified_sources(self.root)

    def test_changed_authored_source_rejected(self):
        (self.root / "config/shell/preview/TrialPolicy.js").write_text("changed")
        with self.assertRaisesRegex(checker.builder.BuildError, "Authored preview source differs"):
            checker.verified_sources(self.root)

    def test_generated_audio_mirror_change_rejected(self):
        (self.root / "config/shell/preview/AudioOutputView.qml").write_text("independent layout")
        with self.assertRaisesRegex(checker.builder.BuildError, "Generated audio frontend mirror differs"):
            checker.verified_sources(self.root)

    def test_generated_network_mirror_change_rejected(self):
        (self.root / "config/shell/preview/NetworkControlView.qml").write_text("independent layout")
        with self.assertRaisesRegex(checker.builder.BuildError, "Generated network frontend mirror differs"):
            checker.verified_sources(self.root)

    def test_changed_notice_rejected(self):
        (self.root / "vendor/omarchy/LICENSE").write_text("incomplete MIT")
        with self.assertRaisesRegex(checker.builder.BuildError, "notice differs"):
            checker.verified_sources(self.root)

    def test_linked_source_rejected(self):
        path = self.root / "config/shell/preview/Style.qml"
        path.unlink()
        path.symlink_to(ROOT / "config/shell/preview/Style.qml")
        with self.assertRaisesRegex(checker.builder.BuildError, "symlink"):
            checker.verified_sources(self.root)

    def test_scope_map_or_catalog_expansion_rejected(self):
        path = self.root / "upstream/clock-preview.json"
        original = json.loads(path.read_text())
        for kind in ("module", "scope", "upstream", "authored", "catalog", "activation"):
            data = copy.deepcopy(original)
            if kind == "module":
                data["module_maps"]["Commons/qmldir"] += "InputDevices 1.0 InputDevices.qml\n"
            elif kind == "scope":
                data["scope"] = "full-shell"
            elif kind == "upstream":
                data["upstream"]["Extra.qml"] = {}
            elif kind == "authored":
                data["authored"]["Extra.qml"] = {}
            elif kind == "catalog":
                data["production_catalog"] = "enabled"
            else:
                data["host_activation"] = "automatic"
            path.write_text(json.dumps(data))
            with self.subTest(kind=kind), self.assertRaises(checker.builder.BuildError):
                checker.verified_sources(self.root)

    def test_authored_profile_has_no_process_watcher_or_command_route(self):
        for name in checker.AUTHORED.values():
            text = (ROOT / name).read_text()
            if name.endswith("TrialPanel.qml"):
                # The reviewed bar keeps exactly one Process (the upstream-style
                # bar-off flag probe) and two watched state files (bar look and
                # the toggles directory). execDetached is reachable only behind
                # the BarRun allowlist.
                self.assertEqual(text.count("property Process"), 1)
                self.assertIn("toggles/bar-off", text)
                self.assertEqual(text.count("property FileView"), 2)
                self.assertEqual(text.count("Quickshell.execDetached"), 1)
                self.assertIn("if (!BarRun.allowed(command))", text)
                for forbidden in ("ShellIpc", "omarchy-", "sudo", "hyprctl"):
                    self.assertNotIn(forbidden, text)
                continue
            if name.endswith("Color.qml"):
                # The palette and font singletons watch exactly the two reviewed
                # state files (theme colors, applied font family).
                self.assertEqual(text.count("property FileView"), 2)
                self.assertIn("theme.json", text)
                self.assertIn("font.txt", text)
                for forbidden in ("Process", "execDetached", "ShellIpc", "hyprctl"):
                    self.assertNotIn(forbidden, text)
                continue
            if name.endswith("NetworkPanelController.qml"):
                self.assertEqual(text.count("Process {"), 1)
                self.assertIn("OMABUNTU_NETWORK_HELPER", text)
                self.assertNotIn("execDetached", text)
                self.assertNotIn("nmcli", text)
                self.assertNotIn("omarchy-", text)
                continue
            if name.endswith("DockState.qml"):
                self.assertEqual(text.count("Process {"), 1)
                self.assertIn("OMABUNTU_DOCK_HELPER", text)
                for forbidden in ("execDetached", "ShellIpc", "omarchy-", "hyprctl", "FileView", "sudo"):
                    self.assertNotIn(forbidden, text)
                continue
            if name.endswith("DisplayPanelController.qml"):
                self.assertEqual(text.count("Process {"), 1)
                self.assertIn("OMABUNTU_DISPLAY_HELPER", text)
                self.assertIn('["status", "brightness", "scale"]', text)
                for forbidden in ("execDetached", "hyprctl", "busctl", "omarchy-", "sudo", "FileView"):
                    self.assertNotIn(forbidden, text)
                continue
            if name.endswith("KeybindingsMenu.qml"):
                self.assertEqual(text.count("Process {"), 1)
                self.assertIn("OMABUNTU_KEYBINDINGS_HELPER", text)
                for forbidden in ("execDetached", "hyprctl", "omarchy-", "sudo", "FileView", "Timer {"):
                    self.assertNotIn(forbidden, text)
                continue
            if name.endswith("CommandMenu.qml"):
                self.assertEqual(text.count("Process {"), 1)
                self.assertIn("OMABUNTU_MENU_HELPER", text)
                for forbidden in ("execDetached", "hyprctl", "omarchy-", "sudo", "FileView", "Timer {"):
                    self.assertNotIn(forbidden, text)
                continue
            if name.endswith("ImagePicker.qml"):
                # One helper Process; the single Timer is the pinned picker's
                # 400 ms reveal fallback, not a closing or polling timer.
                self.assertEqual(text.count("Process {"), 1)
                self.assertIn("OMABUNTU_MENU_HELPER", text)
                self.assertEqual(text.count("Timer {"), 1)
                self.assertIn("interval: 400", text)
                for forbidden in ("execDetached", "hyprctl", "omarchy-", "sudo", "FileView"):
                    self.assertNotIn(forbidden, text)
                continue
            if name.endswith("TrialDesktopState.qml"):
                # Plan 020: the singleton watches exactly the saved-layout file
                # to restore floating modes at login; it runs no commands.
                self.assertEqual(text.count("property FileView"), 1)
                self.assertIn("workspace-layouts.txt", text)
                self.assertIn("watchChanges: true", text)
                for forbidden in ("Process", "execDetached", "ShellIpc", "hyprctl", "omarchy-"):
                    self.assertNotIn(forbidden, text)
                continue
            for forbidden in ("Process {", "FileView", "watchChanges", "execDetached", "ShellIpc", "omarchy-menu"):
                self.assertNotIn(forbidden, text)

    def test_trial_panel_creates_one_bar_per_screen(self):
        text = (ROOT / "config/shell/preview/TrialPanel.qml").read_text()
        self.assertIn("model: Quickshell.screens", text)
        self.assertIn("required property var modelData", text)
        self.assertIn("screen: modelData", text)
        self.assertIn("ExclusionMode.Ignore : ExclusionMode.Auto", text)
        self.assertNotIn("exclusiveZone: 0", text)
        apps = (ROOT / "config/shell/preview/AppLauncher.qml").read_text()
        self.assertIn("exclusiveZone: 0", apps)
        self.assertIn("WlrKeyboardFocus.OnDemand", text)
        self.assertNotIn("WlrKeyboardFocus.Exclusive", text)
        self.assertNotIn("openApps: bars.openApps", text)
        # Menu button first in the left section; keyboard layout between the
        # tray and Bluetooth, in Omarchy's default order.
        self.assertLess(text.index("MenuButton {"), text.index("LiveStatus {"))
        self.assertLess(text.index("PortTrayHost {"), text.index("KeyboardLayout {"))
        self.assertLess(text.index("KeyboardLayout {"), text.index("BluetoothControlView {"))
        self.assertLess(text.index("ClockControlView {"), text.index("ElsewhenPanel {"))
        self.assertIn("centerEndContent:", text)
        self.assertIn("openMenu: bars.openMenu", text)
        # Background looks and the hidden-bar park, as upstream Bar.qml.
        self.assertIn('look === "opaque" || look === "glassy" || look === "none"', text)
        self.assertIn("bars.barHidden ? -26 : 0", text)
        self.assertIn("bars.barHidden ? ExclusionMode.Ignore : ExclusionMode.Auto", text)
        self.assertIn("clockBar.glassy ? clockBar.glassBackground : clockBar.themeBackground", text)
        self.assertIn("Math.min(themeBackground.a, 0.35)", text)
        self.assertEqual(text.count("Behavior on themeBackground"), 1)
        self.assertIn("Style.duration(420)", text)
        live = (ROOT / "config/shell/preview/LiveStatus.qml").read_text()
        switcher = (ROOT / "config/shell/preview/WorkspaceSwitcher.qml").read_text()
        self.assertIn('Hyprland.dispatch("hl.dsp.focus({ workspace = "', live)
        self.assertIn('Hyprland.dispatch("workspace "', live)
        self.assertIn("WorkspaceSwitcher {", live)
        self.assertNotIn('text: "Apps"', live)
        self.assertNotIn("windowTitle", live)
        self.assertIn("model: 6", switcher)
        self.assertNotIn('slot.workspaceId === 10 ? "0"', switcher)
        self.assertIn("function modeGlyph", switcher)
        self.assertNotIn("hyprctl", live)
        self.assertNotIn("omarchy-hyprland", switcher)
        self.assertIn('formatLocale: "en-US"', (ROOT / "config/shell/preview/I18n.qml").read_text())
        self.assertNotIn("de-DE", (ROOT / "config/shell/preview/I18n.qml").read_text())
        self.assertNotIn("close()", live)
        apps = (ROOT / "config/shell/preview/AppLauncher.qml").read_text()
        self.assertIn("DesktopEntries.byId", apps)
        self.assertIn("entry.execute()", apps)
        self.assertIn('name: "apps"', apps)
        self.assertIn("GridView", apps)
        self.assertIn("maxColumns: 7", apps)
        self.assertIn("visibleRows: 4", apps)
        self.assertIn("iconSize: 56", apps)
        self.assertNotIn("systemctl", apps)
        self.assertNotIn("omarchy-menu", apps)

    def test_fixed_probes_do_not_open_the_host_panel(self):
        self.assertEqual(checker.CASES, ("content", "render", "policy", "entry-denied", "assertion-control"))
        for name in ("content", "render", "policy", "assertion-control"):
            text = checker.probe(name)
            self.assertNotIn("TrialPanel", text)
            self.assertNotIn("PanelWindow", text)
        with self.assertRaises(checker.builder.BuildError):
            checker.probe("arbitrary")

    def test_classifier_requires_exact_marker_and_rejects_trial_start(self):
        good = "Configuration Loaded\n" + checker.MARKER + "::content\n"
        self.assertTrue(checker.classify("content", 0, good))
        self.assertFalse(checker.classify("content", 0, good + "OMABUNTU_TRIAL_STARTED\n"))
        self.assertFalse(checker.classify("content", 1, good))
        self.assertFalse(checker.classify("content", 0, good.replace("Configuration Loaded", "")))
        denied = "Configuration Loaded\nOMABUNTU_TRIAL_STOP missing or invalid grant\n"
        self.assertTrue(checker.classify("entry-denied", 0, denied))
        self.assertFalse(checker.classify("entry-denied", 0, denied + checker.MARKER + "::entry-denied\n"))
        failed = "Configuration Loaded\n ERROR OMABUNTU_PREVIEW_ASSERTION_FAILED deliberate geometry mismatch\n"
        self.assertTrue(checker.classify("assertion-control", 42, failed))
        self.assertFalse(checker.classify("assertion-control", 0, failed))
        self.assertFalse(checker.classify("assertion-control", 42, failed + checker.MARKER + "::assertion-control\n"))

    def test_elsewhen_drops_network_and_timezone_changes(self):
        files, _ = checker.verified_sources(self.root)
        for name in checker.ELSEWHEN_TRANSFORMS:
            text = files[name].decode()
            for bad in ("curl", "sudo", "open-meteo.com", "github.com",
                        "omarchy-notification", "updateEntryInline", "set-timezone", "OMARCHY_PATH", "ShellIpc"):
                self.assertNotIn(bad, text, name)
        panel = files["Elsewhen/ElsewhenPanel.qml"].decode()
        self.assertIn('"/usr/bin/python3"', panel)
        self.assertIn('"zones"', panel)
        self.assertNotIn("FileView", panel)
        listing = files["Elsewhen/qmldir"].decode()
        for name in ("ElsewhenPanel", "CityRow", "CitySearch", "Globe", "MiniGlobe", "HeroTitle"):
            self.assertIn(name + " 1.0 " + name + ".qml\n", listing)
        model = files["Elsewhen/Model.js"].decode()
        self.assertIn("function probeCommand(helper, ids, withLocal)", model)
        self.assertIn("function timezoneCommand() { return [] }", model)

    def test_image_inspector_rejects_non_png(self):
        path = self.root / "frame.png"
        path.write_bytes(b"not a png")
        with self.assertRaisesRegex(checker.builder.BuildError, "Invalid bounded preview PNG"):
            checker.inspect_png(path)

    def test_run_refuses_without_containment(self):
        with patch.object(checker.shutil, "which", return_value=None), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(checker.main(["--run", "--build-dir", "work/builds/example"]), 1)
