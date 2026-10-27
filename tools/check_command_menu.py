#!/usr/bin/env python3
"""Plan or run the isolated offscreen check of the command menu surface.

Default prints the plan and runs nothing. --run requires the pinned staged
runtime and Bubblewrap. It stages a private probe under work/menu-port/,
derives the fixture copy of CommandMenu.qml (PanelWindow becomes a plain
Window; layershell, Hyprland and both GlobalShortcut registrations are
removed; probe accessors are appended; every other line stays the real
reviewed logic), and drives it with synthetic key events against the real
Python helper inside a bwrap sandbox: definitions, guard batch, providers,
search, navigation, the system route and the power gate refusal. No host
session, shortcut registration, hyprctl success, or network is involved.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import check_clock_preview as preview
import check_runtime

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'OMABUNTU_MENU_FIXTURE_OK'
HELPERS = ('menu_model.py', 'menu_common.py', 'theme_backend.py',
           'font_backend.py', 'background_backend.py', 'power_actions.py')
DATA = (('omabuntu-menu.jsonc', 'config/shell/omabuntu-menu.jsonc'),
        ('themes.json', 'config/menu/themes.json'))

# User overlay staged into the sandbox: a when-hidden row, a disabled row
# and a checked row under Learn, so the guard contract is exercised offline.
OVERLAY = '''{
  "learn.hidden-row": {"label": "Hidden row", "when": "false", "action": "xdg-open:https://help.ubuntu.com/"},
  "learn.disabled-row": {"label": "Disabled row", "disabled": "true", "action": "systemctl:poweroff"},
  "learn.checked-row": {"label": "Checked row", "checked": "true", "action": "xdg-open:https://help.ubuntu.com/"},
}
'''

PROBE = '''//@ pragma IgnoreSystemSettings
import QtQuick
import Quickshell
ShellRoot {
  id: test
  property var menu: null
  property int appsOpened: 0
  property int keysOpened: 0
  property int themesOpened: 0
  property int stage: 0
  property int tries: 0
  function assert(value, message) { if (!value) throw new Error(String(message)) }
  property string lastWait: ""
  function ready(value, message) { if (!value) { lastWait = String(message); throw new Error("NOTREADY " + lastWait) } lastWait = "" }
  function fail(error) { console.error("OMABUNTU_MENU_ASSERT", String(error)); Qt.exit(42) }
  function rowAt(i) { return menu.probeRow(i) }
  function rowLabel(i) { return String(rowAt(i).label) }
  function findRow(label) {
    for (var i = 0; i < menu.probeCount(); i++) if (rowLabel(i) === label) return i
    return -1
  }
  function rowLabels() {
    var out = []
    for (var i = 0; i < menu.probeCount(); i++) out.push(rowLabel(i))
    return out.join(", ")
  }
  property var stages: [
    function() {
      var factory = Qt.createComponent("CommandMenu.qml", Component.PreferSynchronous)
      assert(factory.status === Component.Ready, "component " + factory.errorString())
      menu = factory.createObject(null)
      factory.destroy()
      assert(menu !== null, "menu construction")
      menu.openApps = function() { appsOpened += 1 }
      menu.openKeybindings = function() { keysOpened += 1 }
      menu.openThemes = function() { themesOpened += 1 }
      menu.openRoute("root")
      assert(menu.shown === true, "open shows the menu")
    },
    function() {
      ready(Object.keys(menu.items).length >= 5, "definitions")
      assert(menu.activeMenu === "root", "root route")
    },
    function() {
      ready(menu.whenResults["system.suspend"] !== undefined, "guard batch")
      assert(menu.disabledResults["learn.disabled-row"] === true, "disabled guard")
      assert(menu.checkedResults["learn.checked-row"] === true, "checked guard")
    },
    function() {
      assert(menu.probeCount() === 4, "root row count")
      assert(rowLabel(0) === "Apps", "apps label")
      assert(findRow("Learn") === 1 && findRow("Style") === 2 && findRow("System") === 3, "root labels")
      assert(rowAt(3).kind === "menu", "system is a submenu")
    },
    function() {
      menu.select(1)
      assert(menu.selectedIndex === 1, "cursor down")
      menu.activateIndex(1)
      assert(menu.activeMenu === "learn", "learn route")
      menu.handleKey({ key: Qt.Key_Backspace, text: "" })
      assert(menu.activeMenu === "root", "back out")
      menu.select(3)
      menu.activateIndex(3)
      assert(menu.activeMenu === "system", "system route")
    },
    function() {
      var expected = 3 + (menu.whenResults["system.suspend"] ? 1 : 0) + (menu.whenResults["system.hibernate"] ? 1 : 0)
      assert(menu.probeCount() === expected, "system row count follows guards")
      assert(findRow("Logout") >= 0 && findRow("Reboot") >= 0 && findRow("Shutdown") >= 0, "system labels")
      assert(rowAt(findRow("Reboot")).kind === "action", "reboot is an action")
    },
    function() {
      var reboot = findRow("Reboot")
      menu.selectedIndex = reboot
      menu.cursorActive = true
      menu.activateIndex(reboot)
    },
    function() {
      ready(menu.note === "Power actions are not enabled yet.", "gate refusal")
      assert(menu.shown === true, "refusal keeps the menu open")
      menu.handleKey({ key: Qt.Key_Escape, text: "" })
      assert(menu.shown === false, "escape closes")
    },
    function() {
      menu.openRoute("learn")
      ready(menu.probeCount() >= 5, "learn rows")
      assert(findRow("Hidden row") < 0, "when hides the row")
      var disabled = findRow("Disabled row \u2713")
      assert(disabled >= 0, "disabled suffix")
      assert(findRow("Checked row \u2713") >= 0, "checked suffix")
      assert(menu.rowSelectable(disabled) === false, "disabled row is not selectable")
      menu.select(0)
      for (var i = 0; i < 8; i++) {
        menu.select(1)
        assert(menu.selectedIndex !== disabled, "cursor skips the disabled row")
      }
    },
    function() {
      menu.openRoute("root")
      menu.select(0)
      menu.activateIndex(0)
      assert(appsOpened === 1, "apps route runs")
      assert(menu.shown === false, "internal route closes the menu")
    },
    function() {
      menu.openRoute("root")
      menu.setFilter("the")
      ready(menu.probeCount() === 4, "search rows: " + rowLabels())
      var theme = findRow("Theme")
      assert(theme >= 0, "theme drilldown row")
      assert(String(rowAt(theme).detail) === "Style", "drilldown detail")
      assert(String(rowAt(theme).section) === "drilldown", "drilldown section")
    },
    function() {
      var theme = findRow("Theme")
      assert(theme >= 0, "theme row present")
      assert(String(rowAt(theme).kind) === "action", "theme row kind is action: " + rowAt(theme).kind)
      assert(String(rowAt(theme).action) === "omabuntu-open:themes", "theme row action: " + rowAt(theme).action)
      menu.selectedIndex = theme
      menu.cursorActive = true
      menu.activateIndex(theme)
      assert(themesOpened === 1, "theme row opens the picker")
      assert(menu.shown === false, "picker route closes the menu")
      console.log("__MARKER__")
      menu.destroy()
      Qt.callLater(function() { Qt.quit() })
    }
  ]
  Timer {
    interval: 25; repeat: true; running: true
    onTriggered: {
      if (stage >= stages.length) return
      tries += 1
      if (tries > 400) { fail("timeout at stage " + stage + " waiting: " + lastWait); return }
      try {
        stages[stage]()
        stage += 1
        tries = 0
      } catch (error) {
        var text = String(error && error.message !== undefined ? error.message : error)
        if (text.indexOf("NOTREADY") === 0) return
        fail(text)
      }
    }
  }
}
'''.replace('__MARKER__', MARKER)


def _replace(text, old, new='', label=None):
    if text.count(old) != 1:
        raise ValueError('Menu surface witness differs: %r' % (label or old[:40]))
    return text.replace(old, new)


def derive_surface(text):
    """Fixture ownership copy: Window instead of PanelWindow, no shortcut
    registration, no Hyprland. The menu logic itself stays byte-for-byte."""
    text = _replace(text, 'import Quickshell.Hyprland\n', '', 'hyprland import')
    text = _replace(text, 'import Quickshell.Wayland\n', '', 'wayland import')
    text = _replace(text, 'import QtQuick\n', 'import QtQuick\nimport QtQuick.Window\n', 'qtquick import')
    text = _replace(text, 'PanelWindow {', 'Window {\n  width: 1280\n  height: 800', 'panel window')
    for old in ('  anchors { top: true; bottom: true; left: true; right: true }\n',
                '  exclusionMode: ExclusionMode.Normal\n', '  exclusiveZone: 0\n',
                '  WlrLayershell.namespace: "omabuntu-menu"\n',
                '  WlrLayershell.layer: WlrLayer.Overlay\n',
                '  WlrLayershell.keyboardFocus: shown ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None\n'):
        text = _replace(text, old, '', 'surface property')
    text = _replace(text, '    root.screen = root.focusedScreen()\n', '', 'screen assignment')
    start = text.index('  function focusedScreen() {')
    end = text.index('    return screens[0]\n  }\n') + len('    return screens[0]\n  }\n')
    if 'function focusedScreen' in text[:start] or 'function focusedScreen' in text[end:]:
        raise ValueError('Menu surface witness differs: focusedScreen duplicates')
    text = text[:start] + text[end:]
    start = text.index('  GlobalShortcut {')
    tail = text.index('  Rectangle {', start)
    if text.count('  GlobalShortcut {') != 2:
        raise ValueError('Menu surface witness differs: shortcut blocks')
    text = text[:start] + text[tail:]
    if 'GlobalShortcut' in text or 'WlrLayershell' in text or 'Hyprland' in text:
        raise ValueError('Menu surface retains a host registration')
    close = text.rstrip().rfind('}')
    if close < 0:
        raise ValueError('Menu surface has no closing brace')
    text = (text.rstrip()[:close]
            + '''
  // Probe accessors for the offscreen fixture only. The model, rebuild and
  // search logic above is the reviewed surface unchanged.
  function probeCount() { return displayModel.count }
  function probeRow(index) { return displayModel.get(index) }
'''
            + text.rstrip()[close:])
    return text


def _setenv(command, key, value):
    position = command.index('--chdir')
    command[position:position] = ['--setenv', key, value]


def log_is_clean(text):
    """A model-only success marker cannot excuse missing rendered rows."""
    return not any(marker in text for marker in (
        'OMABUNTU_MENU_ASSERT', 'TypeError:', 'ReferenceError:',
        'is not installed', 'Binding loop', 'Cannot create delegate',
        'Required property'))


def run(root, build, timeout=120):
    files, _ = preview.verified_sources(root)
    _, runtime, _ = check_runtime.verify_stage(root, build)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    case = root / 'work/menu-port' / stamp
    for name in ('probe/helpers', 'home/runtime', 'home/cache',
                 'home/data', 'home/state/current', 'home/config/omabuntu'):
        (case / name).mkdir(mode=0o700, parents=True, exist_ok=True)
    (case / 'home/config/omabuntu/menu.jsonc').write_text(OVERLAY)
    for name, data in files.items():
        if name == 'CommandMenu.qml':
            data = derive_surface(data.decode()).encode()
        path = case / 'probe' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for name in HELPERS:
        (case / 'probe/helpers' / name).write_bytes((root / 'tools' / name).read_bytes())
    for target, source in DATA:
        (case / 'probe' / target).write_bytes((root / source).read_bytes())
    (case / 'probe/shell.qml').write_text(PROBE)
    (case / 'probe/fonts.conf').write_text('<fontconfig><dir>/usr/share/fonts</dir></fontconfig>')
    command = check_runtime.sandbox_command(
        runtime, case, [check_runtime.PREFIX + '/bin/quickshell', '--no-color', '--path', '/probe/shell.qml'])
    position = command.index('QML_IMPORT_PATH')
    command[position + 1] += ':/probe'
    _setenv(command, 'OMABUNTU_MENU_HELPER', '/probe/helpers/menu_model.py')
    _setenv(command, 'OMABUNTU_MENU_DEFINITIONS', '/probe/omabuntu-menu.jsonc')
    _setenv(command, 'OMABUNTU_MENU_THEMES', '/probe/themes.json')
    _setenv(command, 'OMABUNTU_STATE_HOME', '/home/probe/state')
    _setenv(command, 'PYTHONDONTWRITEBYTECODE', '1')
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    text = result.stdout + result.stderr
    (case / 'output.log').write_text(text)
    checks = [{'name': 'surface', 'returncode': result.returncode,
               'marker': MARKER in text, 'log_sha256': hashlib.sha256(text.encode()).hexdigest()}]
    ok = (result.returncode == 0 and MARKER in text and 'Configuration Loaded' in text
          and log_is_clean(text))
    report = {'status': 'isolated-menu-fixtures-passed' if ok else 'failed', 'checks': checks,
              'limits': ('Synthetic key events and the real helper inside bwrap; guards from the'
                         ' sandboxed /sys and a staged overlay; no shortcut registration, hyprctl'
                         ' success, font/background provider run, native focus or visual acceptance.')}
    (case / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(case / 'report.json')
    if not ok:
        print('\n'.join(line for line in text.splitlines()
                        if any(key in line for key in ('ERROR', 'ASSERT', 'not installed', 'TypeError', 'Cannot'))))
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--build-dir', type=Path)
    args = parser.parse_args(argv)
    if not args.run:
        print('Plan only: isolated command-menu fixture; use --run --build-dir work/builds/<build-id> after approval.')
        return 0
    if args.build_dir is None:
        parser.error('--run requires --build-dir')
    root = Path(__file__).resolve().parents[1]
    return run(root, args.build_dir)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
