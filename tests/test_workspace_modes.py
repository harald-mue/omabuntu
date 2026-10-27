"""Workspace layout cycle and the Hyprland-only eval."""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import workspace_modes


class WorkspaceModeTests(unittest.TestCase):
    def test_cycle_matches_the_pinned_toggle_script(self):
        found = workspace_modes.next_modes_from_toggle(workspace_modes.TOGGLE.read_text())
        for mode, nxt in found.items():
            if mode == "*":
                self.assertEqual(workspace_modes.next_mode("floating"), nxt)
                self.assertEqual(workspace_modes.next_mode("other"), nxt)
            else:
                self.assertEqual(workspace_modes.next_mode(mode), nxt)

    def test_eval_is_hyprland_lua_without_omarchy_routes(self):
        script = workspace_modes.program(3, "scrolling")
        self.assertIn('hl.workspace_rule({ workspace = id, layout = mode })', script)
        self.assertIn('local mode = "scrolling"', script)
        self.assertIn('local id = "3"', script)
        self.assertIn("omabuntu-mode-floated", script)
        floating = workspace_modes.program(3, "floating")
        self.assertIn("math.min(1100, math.floor(width * 0.64))", floating)
        self.assertIn("math.min(760, math.floor(height * 0.68))", floating)
        self.assertIn("hl.dsp.window.center", floating)
        self.assertIn("cascade * 24 - 48", floating)
        self.assertIn('hl.dispatch(hl.dsp.window.float({ action = "on", window = window }))\n    place(window)', floating)
        self.assertLess(floating.index("place(window)"), floating.index("hl.workspace_rule"))
        self.assertIn('refreshFloatedBars()', script)
        self.assertIn('refreshFloatedBars()', floating)
        self.assertNotIn('setTitlebars', script)
        self.assertNotIn('enabled = false', script)
        self.assertNotIn('hyprbars:no_bar', script)
        for forbidden in ("omarchy-", "hyprctl", "reload", "titlebars", "notify"):
            self.assertNotIn(forbidden, script)
            self.assertNotIn(forbidden, floating)
        # Plan 020: the eval persists the mode for the login restore.
        self.assertIn('workspace-layouts.txt', script)
        self.assertIn('os.remove(modespath)', script)
        self.assertIn('out:write(table.concat(merged,', script)
        self.assertIn('lid ~= id', script)
        for forbidden in ("exec", "os.execute"):
            self.assertNotIn(forbidden, script[script.index("-- Plan 020:"):])
        with self.assertRaises(ValueError):
            workspace_modes.program(0, "dwindle")
        with self.assertRaises(ValueError):
            workspace_modes.program(True, "dwindle")
        with self.assertRaises(ValueError):
            workspace_modes.program(1, "master")

    def test_claim_eval_brings_new_windows_into_floating_mode(self):
        script = workspace_modes.claim_program("0x5cf298f0d4c0", 6, 2)
        self.assertIn('local target = "address:0x5cf298f0d4c0"', script)
        self.assertIn('local id = "6"', script)
        self.assertIn('tostring(window.workspace.id) ~= id', script)
        self.assertIn('local cascade = 2', script)
        self.assertIn('cascade * 24 - 48', script)
        self.assertIn('omabuntu-mode-floated', script)
        self.assertIn('omabuntu-hyprbars-show-floated', script)
        self.assertIn('hl.dsp.window.float({ action = "on", window = target })', script)
        for forbidden in ("omarchy-", "hyprctl", "reload", "titlebars", "notify", "exec", "os.execute"):
            self.assertNotIn(forbidden, script)
        with self.assertRaises(ValueError):
            workspace_modes.claim_program("5cf298f0d4c0", 6)
        with self.assertRaises(ValueError):
            workspace_modes.claim_program("0x5cf298f0d4c0", 0)
        with self.assertRaises(ValueError):
            workspace_modes.claim_program("0x5cf298f0d4c0", 6, 5)
        mirror = (ROOT / "config/shell/preview/WorkspaceSwitcher.qml").read_text()
        self.assertIn("function claimWindow(address, workspaceId)", mirror)
        self.assertIn('"openwindow"', mirror)
        self.assertIn('TrialDesktopState.isFloating(workspaceId)', mirror)
        self.assertIn('TrialDesktopState.savedMode(String(id))', mirror)
        self.assertIn('if (saved) return saved', mirror)
        self.assertIn('function restoreFloating()', mirror)
        self.assertIn('function onSavedModesChanged()', mirror)
        self.assertIn('function onValuesChanged()', mirror)
        self.assertIn('queue.push({ address: address, id: workspaceId })', mirror)
        self.assertIn('onExited: root.drainClaims()', mirror)

    def test_switcher_keeps_the_original_glyph_function(self):
        source = workspace_modes.WIDGET.read_bytes()
        derived = workspace_modes.derive_workspaces(source).decode()
        glyph = workspace_modes.between(source.decode(), "  function modeGlyph(mode) {\n", "\n\n  // A layout only changes")
        self.assertIn(glyph, derived)
        self.assertEqual(derived.encode(), workspace_modes.MIRROR.read_bytes())
        self.assertNotIn("omarchy-hyprland-workspace-layout-toggle", derived)
        self.assertIn("onPressed: function(mouse) {", derived)
        self.assertIn("if (slot.shown && root.liveModes) root.apply(root.nextMode(root.activeMode))", derived)
        self.assertIn("root.remember(id, mode)", derived)
        self.assertNotIn("refreshWorkspaces", derived)
        self.assertIn("queuedSerial", derived)
        self.assertIn("model: 6", derived)
        self.assertNotIn("model: 10", derived)
    def test_saved_layout_singleton_seeds_modes_from_the_state_file(self):
        text = (ROOT / "config/shell/preview/TrialDesktopState.qml").read_text()
        self.assertIn('Quickshell.env("OMABUNTU_STATE_HOME")', text)
        self.assertIn('Quickshell.env("XDG_STATE_HOME")', text)
        self.assertIn('+ "/current/workspace-layouts.txt"', text)
        self.assertIn('savedModes = saved', text)
        self.assertIn('watchChanges: true', text)
        self.assertIn('onLoaded: root.applySaved(text())', text)
        self.assertIn('onLoadFailed: root.applySaved("")', text)
        self.assertIn('function savedMode(id) { return savedModes[id] }', text)
        self.assertIn('parts[1] !== "scrolling" && parts[1] !== "floating"', text)
        self.assertIn('if (modes[key] === "floating") floating[key] = true', text)
        for forbidden in ("omarchy-", "hyprctl", "exec"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
