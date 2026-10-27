"""Keybindings menu contracts. No live compositor call is made."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import keybindings_menu as menu
import keybindings_menu_fixtures as fixtures


def bind(mod, key, description, dispatcher, arg="", keycode="0"):
    return (
        "bind\n"
        f"\tmodmask: {mod}\n"
        "\tsubmap: \n"
        f"\tkey: {key}\n"
        f"\tkeycode: {keycode}\n"
        "\tcatchall: false\n"
        f"\tdescription: {description}\n"
        f"\tdispatcher: {dispatcher}\n"
        f"\targ: {arg}\n"
    )


def actions(rows):
    return [row["label"].split("\u2192", 1)[1].strip() for row in rows]


class Runner:
    def __init__(self, binds, responses=None):
        self.binds = binds
        self.responses = responses or {}
        self.calls = []

    def __call__(self, argv, timeout=8):
        self.calls.append(list(argv))
        if argv == ["hyprctl", "binds"]:
            return 0, self.binds
        return self.responses.get(tuple(argv), (0, "ok"))


class KeybindingsMenuTests(unittest.TestCase):
    def assert_column(self, rows):
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(len(row["label"].split("\u2192", 1)[0]), 36)
            self.assertLessEqual(len(row["label"]), 78)
            self.assertEqual(row["label"].split("\u2192", 1)[0].rstrip(), row["chord"])
            self.assertEqual(row["label"].split("\u2192", 1)[1].strip(), row["action"])

    def test_rows_keep_omarchy_column_order_and_alternatives(self):
        text = "".join((
            bind(64, "SUPER + W", "Close window", "exec", "close"),
            bind(64, "SUPER + Q", "Close window", "exec", "close"),
            bind(64, "SUPER + grave", "Toggle scratchpad", "exec", "pad"),
            bind(64, "SUPER + F", "Full screen", "exec", "full"),
            bind(68, "SUPER CTRL + Q", "Calculator", "exec", "omacalc"),
            bind(0, "XF86Calculator", "Calculator", "exec", "omacalc"),
            bind(8, "ALT + TAB", "Reveal active window on top", "exec", "true"),
            bind(64, "code:201", "Copilot duplicate", "exec", "hidden"),
            bind(64, "SUPER + K", "", "__lua"),
        ))
        rows = menu.format_binds(text)
        listed = actions(rows)
        self.assert_column(rows)
        self.assertLess(listed.index("Full screen"), listed.index("Close window"))
        self.assertLess(listed.index("Close window"), listed.index("Toggle scratchpad"))
        self.assertLess(listed.index("Toggle scratchpad"), listed.index("Calculator"))
        self.assertLess(listed.index("Calculator"), listed.index("Reveal active window on top"))
        close = next(row for row in rows if row["label"].endswith("Close window"))
        self.assertIn("SUPER + W / SUPER + Q", close["label"])
        self.assertTrue(close["label"].startswith("SUPER + W"))
        scratch = next(row for row in rows if "scratchpad" in row["label"])
        self.assertIn("SUPER + ~", scratch["label"])
        self.assertNotIn("grave", scratch["label"])
        self.assertNotIn("Copilot", "".join(actions(rows)))
        self.assertNotIn("Copy URL", "".join(actions(rows)))

    def test_unresolved_or_different_actions_stay_on_separate_rows(self):
        paired = menu.format_binds("".join((
            bind(64, "SUPER + Y", "Zoom in", "exec", "zoom"),
            bind(64, "SUPER + Z", "Zoom in", "exec", "zoom"),
            bind(64, "SUPER + W", "Close window", "__lua"),
            bind(64, "SUPER + X", "Close window", "exec", "close-all"),
            bind(64, "SUPER + A", "Close window", "__lua"),
            bind(64, "SUPER + B", "Close window", "__lua"),
        )))
        self.assertEqual(actions(paired).count("Zoom in"), 2)
        self.assertEqual(actions(paired).count("Close window"), 4)
        unresolved = [row for row in paired if row["label"].rstrip().endswith("Close window")
                      and "SUPER + X" not in row["label"]]
        self.assertEqual(len(unresolved), 3)
        self.assertTrue(all(row["dispatcher"] == "" and " / " not in row["label"] for row in unresolved))
        wide_rows = menu.format_binds("".join((
            bind(73, "SUPER SHIFT ALT + BACKSPACE", "Calculator", "exec", "omacalc"),
            bind(69, "SUPER SHIFT CTRL + BACKSPACE", "Calculator", "exec", "omacalc"),
        )))
        self.assertEqual(actions(wide_rows).count("Calculator"), 2)
        self.assert_column(wide_rows)
        queued = menu.format_binds("".join((
            bind(64, "SUPER + A", "Calculator", "exec", "omacalc"),
            bind(77, "SUPER SHIFT CTRL ALT + BACKSPACE", "Calculator", "exec", "omacalc"),
            bind(64, "SUPER + B", "Calculator", "exec", "omacalc"),
        )))
        self.assertEqual(len(queued), 3)

    def test_keycodes_use_the_fallback_and_an_explicit_layout_symbol(self):
        text = bind(64, "", "Toggle scratchpad", "exec", "pad", keycode="49") + bind(
            64, "SUPER + code:20", "Expand window left", "exec", "wide")
        fallback = menu.format_binds(text)
        self.assertIn("SUPER + MINUS", fallback[0]["label"])
        self.assertIn("SUPER + code:49", fallback[1]["label"])
        named = menu.format_binds(text, symbols={"49": "grave"})
        self.assertIn("SUPER + ~", named[1]["label"])
        mouse = menu.format_binds(bind(64, "mouse:272", "Drag window", "exec", "drag"))
        self.assertIn("LEFT MOUSE BUTTON", mouse[0]["label"])

    def test_lua_scan_recovers_unlabeled_binds_without_running_them(self):
        marker = ROOT / "work" / "keybindings-scan-must-not-create"
        if marker.exists():
            marker.unlink()
        hostile = (
            'hl.exec_cmd("touch ' + str(marker) + '")\n'
            'os.execute("touch ' + str(marker) + '")\n'
            'hl.bind("SUPER + SHIFT + Escape", hl.dsp.exec_cmd("uwsm stop"))\n'
        )
        self.assertEqual(menu.scan_lua_source("while true do end\nhl.bind('SUPER + A', hl.dsp.window.close())"), [])
        self.assertEqual(menu.scan_lua_source(hostile), [])
        self.assertFalse(marker.exists())
        recovered = menu.scan_lua_source('''
hl.exec_cmd("touch ignored")
hl.bind("SUPER + Return", hl.dsp.exec_cmd("ghostty"))
hl.bind("SUPER + W", hl.dsp.window.close())
hl.bind("SUPER + SHIFT + F", hl.dsp.window.float({ action = "toggle" }))
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })
for i = 1, 10 do
  local key = i % 10
  hl.bind("SUPER + " .. key, hl.dsp.focus({ workspace = i }))
end
''')
        kinds = {(row["key"], row["kind"], row["arg"]) for row in recovered}
        self.assertIn(("Return", "exec", "ghostty"), kinds)
        self.assertIn(("W", "lua", "hl.dsp.window.close()"), kinds)
        self.assertIn(("mouse:272", "lua", "hl.dsp.window.drag()"), kinds)
        self.assertIn(("0", "lua", "hl.dsp.focus({ workspace = 10 })"), kinds)
        text = "".join((
            bind(64, "Return", "", "__lua"),
            bind(64, "W", "", "__lua"),
            bind(65, "F", "", "__lua"),
            bind(65, "Escape", "", "__lua"),
            bind(64, "mouse:272", "", "__lua"),
            bind(64, "1", "", "__lua"),
        ))
        source = '''
hl.bind("SUPER + Return", hl.dsp.exec_cmd("ghostty"))
hl.bind("SUPER + W", hl.dsp.window.close())
hl.bind("SUPER + SHIFT + F", hl.dsp.window.float({ action = "toggle" }))
hl.bind("SUPER + SHIFT + Escape", hl.dsp.exec_cmd("uwsm stop"))
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind("SUPER + 1", hl.dsp.focus({ workspace = 1 }))
'''
        rows = menu.rows_from(text, source)
        listed = actions(rows)
        self.assertEqual(listed[:2], ["Close window", "Switch to workspace 1"])
        self.assertEqual(set(listed), {
            "Close window", "Switch to workspace 1", "Toggle floating", "Drag window",
            "ghostty", "uwsm stop"})
        self.assert_column(rows)
        self.assertFalse(marker.exists())
        stopped = next(row for row in rows if row["arg"] == "uwsm stop")
        runner = Runner(text)
        self.assertEqual(menu.perform(["dispatch", stopped["dispatcher"], stopped["arg"]], runner, source)["error"],
                         "refused")
        self.assertTrue(all(call[1] != "dispatch" for call in runner.calls))

    def test_dispatch_reruns_only_a_current_binding(self):
        text = bind(64, "Return", "Terminal", "exec", "ghostty")
        runner = Runner(text, {
            ("hyprctl", "dispatch", 'hl.dsp.exec_cmd("ghostty")'): (1, "no"),
            ("hyprctl", "dispatch", "exec", "ghostty"): (0, "ok"),
        })
        self.assertEqual(menu.perform(["dispatch", "exec", "ghostty"], runner)["ok"], True)
        self.assertEqual(runner.calls[1:], [
            ["hyprctl", "dispatch", 'hl.dsp.exec_cmd("ghostty")'],
            ["hyprctl", "dispatch", "exec", "ghostty"],
        ])
        unknown = Runner(text)
        self.assertEqual(menu.perform(["dispatch", "exec", "other"], unknown)["error"], "unknown")
        self.assertEqual(unknown.calls, [["hyprctl", "binds"]])
        for innocent in ("ghostty", "uwsm-app -- ghostty", "myreboot", "clock", "block", "killactive"):
            self.assertFalse(menu.session_action(innocent))
        for blocked in ("hyprlock", "systemctl suspend", "loginctl lock-session", "swayidle", "exit", "hibernate",
                        "omabuntu lock --apply", "/home/x/.local/bin/omabuntu lock --apply"):
            self.assertTrue(menu.session_action(blocked), blocked)

    def test_configured_session_actions_stay_listed_and_do_not_run(self):
        samples = (
            ("exec", "hyprlock"),
            ("exec", "/home/x/.local/bin/omabuntu lock --apply"),
            ("exec", "systemctl suspend"),
            ("exec", "loginctl lock-session"),
            ("exec", "swayidle -w"),
            ("exit", ""),
        )
        for dispatcher, arg in samples:
            text = bind(64, "Escape", "Session action", dispatcher, arg)
            self.assertEqual(len(menu.format_binds(text)), 1)
            runner = Runner(text)
            result = menu.perform(["dispatch", dispatcher, arg], runner)
            self.assertEqual(result["error"], "refused", arg or dispatcher)
            self.assertEqual(runner.calls, [["hyprctl", "binds"]])

    def test_empty_exec_and_sendshortcut_follow_the_existing_binding(self):
        empty = bind(64, "Return", "Terminal", "exec", "")
        runner = Runner(empty)
        self.assertEqual(menu.perform(["dispatch", "exec", ""], runner)["error"], "failed")
        self.assertEqual(runner.calls, [["hyprctl", "binds"]])
        text = bind(0, "V", "Paste", "sendshortcut", "CTRL, V,")
        sent = Runner(text)
        self.assertTrue(menu.perform(["dispatch", "sendshortcut", "CTRL, V,"], sent)["ok"])
        self.assertEqual(len(sent.calls), 3)
        self.assertIn("down", sent.calls[1][2])
        self.assertIn("up", sent.calls[2][2])
        failed = menu._send_key_state("CTRL", "V", "activewindow", "down")
        fallback = Runner(text, {("hyprctl", "dispatch", failed): (1, "no")})
        self.assertTrue(menu.perform(["dispatch", "sendshortcut", "CTRL, V,"], fallback)["ok"])
        self.assertEqual(fallback.calls[-1], ["hyprctl", "dispatch", "sendshortcut", "CTRL, V,"])

    def test_undescribed_exec_shows_the_command_without_the_uwsm_prefix(self):
        rows = menu.format_binds(bind(64, "Return", "", "exec", "uwsm-app -- ghostty"))
        self.assertEqual(actions(rows), ["ghostty"])
        self.assertEqual(rows[0]["dispatcher"], "exec")
        self.assertEqual(rows[0]["arg"], "uwsm-app -- ghostty")

    def test_keymap_parser_reads_keycodes_and_skips_a_missing_tool(self):
        text = """
        <AE11> = 20;
        <TLDE> = 49;
        <AE10> = 19;
        key <AE11> { [ minus, underscore ] };
        key <TLDE> { [ grave, asciitilde ] };
        key <AE10> { [ NoSymbol ] };
        """
        symbols = menu.parse_keymap(text)
        self.assertEqual(symbols["20"], "minus")
        self.assertEqual(symbols["49"], "grave")
        self.assertNotIn("19", symbols)
        with patch.object(menu.shutil, "which", return_value=None):
            self.assertIsNone(menu.live_symbols())

    def test_config_loader_rejects_a_symlink_and_reads_a_regular_file(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as directory:
            base = Path(directory)
            source = base / "hyprland.lua"
            source.write_text("hl.bind(\"SUPER + W\", hl.dsp.window.close())\n", encoding="utf-8")
            self.assertIn("window.close", menu.load_source(source))
            link = base / "linked.lua"
            link.symlink_to(source)
            self.assertEqual(menu.load_source(link), "")

    def test_surface_is_a_fixed_selector_without_a_closing_timer(self):
        text = (ROOT / "config/shell/preview/KeybindingsMenu.qml").read_text()
        shell = (ROOT / "config/shell/preview/TrialShell.qml").read_text()
        self.assertIn("OMABUNTU_KEYBINDINGS_HELPER", text)
        self.assertEqual(text.count("Process {"), 1)
        self.assertIn("Math.min(800", text)
        self.assertIn("Math.min(500", text)
        self.assertIn("Search keybindings", text)
        self.assertIn("Session actions stay on their own keys.", text)
        self.assertNotIn("Timer {", text)
        self.assertIn("KeybindingsMenu.qml", shell)
        self.assertIn("keybindings.destroy()", shell)
        harness = (ROOT / "tools/check_tray_port.py").read_text()
        self.assertIn('"keys": (keys.CASES, keys.fixture, keys.classify)', harness)
        self.assertIn('suite == "keys" and relative == "KeybindingsMenu.qml"', harness)
        changed = fixtures.fixture_menu(text.encode()).decode()
        self.assertNotIn("GlobalShortcut", changed)
        self.assertIn("function handleKey", changed)
        self.assertEqual(fixtures.CASES, ("navigate", "negative"))
        self.assertIn("rendered chord column", fixtures.fixture("navigate"))
        self.assertTrue(fixtures.classify(
            "navigate", 0, "Configuration Loaded\n" + fixtures.MARKER + "::navigate\n"))
        self.assertFalse(fixtures.classify(
            "navigate", 0, "Configuration Loaded\nWARN unexpected\n" + fixtures.MARKER + "::navigate\n"))
