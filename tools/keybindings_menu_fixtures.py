"""Isolated keybindings menu fixture. No host compositor or hyprctl."""
import json

CASES = ("navigate", "negative")
MARKER = "OMABUNTU_KEYS_FIXTURE_OK"


def _label(chord, action):
    return f"{chord:<35} \u2192 {action}"


ROWS = [
    {"label": _label("SUPER + W", "Close window"), "dispatcher": "lua",
     "arg": "hl.dsp.window.close()"},
    {"label": _label("SUPER + Return", "Launch terminal"), "dispatcher": "exec", "arg": "ghostty"},
    {"label": _label("SUPER + left", "Focus left"), "dispatcher": "lua",
     "arg": "hl.dsp.focus({ direction = \"left\" })"},
]


def fixture_menu(data):
    """Drop native layer and shortcut ownership only in the isolated copy."""
    text = data.decode()

    def replace(old, new=""):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError("Keybindings fixture witness differs")
        text = text.replace(old, new)

    replace("import QtQuick\n", "import QtQuick\nimport QtQuick.Window\n")
    replace("import Quickshell.Hyprland\n")
    replace("PanelWindow {\n", "Window {\n  width: 1280\n  height: 800\n")
    for line in (
        "  anchors { top: true; bottom: true; left: true; right: true }\n",
        "  exclusionMode: ExclusionMode.Normal\n",
        "  exclusiveZone: 0\n",
        '  WlrLayershell.namespace: "omabuntu-keybindings"\n',
        "  WlrLayershell.layer: WlrLayer.Overlay\n",
        "  WlrLayershell.keyboardFocus: shown ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None\n",
        "    root.screen = root.focusedScreen()\n",
    ):
        replace(line)
    screen = text.find("  function focusedScreen() {\n")
    helper = text.find("  function helperPath() {\n")
    query = text.find("  function queryHelper(kind, extra) {\n")
    toggle = text.find("  function toggle() {\n")
    shortcut = text.find("  GlobalShortcut {\n")
    scrim = text.find("  Rectangle {\n    anchors.fill: parent\n")
    if min(screen, helper, query, toggle, shortcut, scrim) < 0 or not (
            screen < helper and query < toggle and shortcut < scrim):
        raise ValueError("Keybindings fixture boundary differs")
    payload = json.dumps(json.dumps({"ok": True, "rows": ROWS}, ensure_ascii=False))
    replacement = (
        "  function queryHelper(kind, extra) {\n"
        "    if (kind === \"list\") {\n"
        f"      root.finishHelper(kind, root.generation, {payload});\n"
        "      return;\n"
        "    }\n"
        "    root.finishHelper(kind, root.generation, \"{\\\"ok\\\":true}\");\n"
        "  }\n\n"
    )
    text = (text[:screen] + "  function focusedScreen() { return null }\n\n" + text[helper:query]
            + replacement + text[toggle:shortcut] + text[scrim:])
    if "PanelWindow" in text or "GlobalShortcut" in text or "Hyprland" in text:
        raise ValueError("Keybindings fixture kept native ownership")
    return text.encode()


def fixture(name):
    if name not in CASES:
        raise ValueError("Unknown keybindings fixture")
    return '''//@ pragma IgnoreSystemSettings
import QtQuick
import Quickshell
ShellRoot {
  id: test
  property var menu: null
  function require(value, message) { if (!value) throw new Error(message); }
  function findArrow(item) {
    if (!item) return "";
    if (item.text && String(item.text).indexOf("\u2192") >= 0) return String(item.text);
    var children = item.children || [];
    for (var i = 0; i < children.length; ++i) {
      var found = findArrow(children[i]);
      if (found) return found;
    }
    return "";
  }
  function fail(error) { console.error("OMABUNTU_KEYS_ASSERT", String(error)); Qt.exit(42); }
  Timer { interval: 50; running: true; onTriggered: {
    try {
      var factory = Qt.createComponent("KeybindingsMenu.qml", Component.PreferSynchronous);
      require(factory.status === Component.Ready, factory.errorString());
      menu = factory.createObject(null);
      factory.destroy();
      require(menu !== null, "menu construction");
      if ("%s" === "negative") throw new Error("deliberate keybindings assertion");
      require(menu.cardWidth === 800 && menu.cardHeight === 500, "selector size");
      require(menu.rowFont === "JetBrainsMono Nerd Font", "monospace row font");
      menu.open();
      shown.start();
    } catch (error) { test.fail(error); }
  } }
  Timer { id: shown; interval: 50; onTriggered: {
    try {
      require(menu.shown && menu.matchCount === 3, "open lists the bindings");
      require(menu.selectedLabel.split("\u2192")[0].length === 36, "chord column");
      var rendered = findArrow(menu.contentItem);
      require(rendered.split("\u2192")[0].length === 36, "rendered chord column");
      menu.handleKey({ key: Qt.Key_Down, text: "" });
      require(menu.selected === 1 && menu.selectedLabel.indexOf("Launch terminal") >= 0, "down moves");
      var letters = "close";
      for (var i = 0; i < letters.length; ++i) menu.handleKey({ key: 0, text: letters.charAt(i) });
      require(menu.matchCount === 1 && menu.selectedLabel.indexOf("Close window") >= 0, "search filters");
      menu.handleKey({ key: Qt.Key_Return, text: "" });
      require(menu.shown === false, "return closes");
      require(menu.activatedDispatcher === "lua" && menu.activatedArg === "hl.dsp.window.close()", "return selects the row");
      console.log("%s::navigate");
      menu.destroy();
      Qt.callLater(function() { Qt.quit(); });
    } catch (error) { test.fail(error); }
  } }
}
''' % (name, MARKER)


def classify(name, code, text):
    import re
    if name not in CASES:
        return False
    errors = re.findall(r"^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b.*", text, re.M)
    if name == "negative":
        return code == 42 and len(errors) == 1 and "deliberate keybindings assertion" in errors[0] and MARKER not in text
    return code == 0 and not errors and text.count(MARKER + "::" + name) == 1 and "Configuration Loaded" in text
