#!/usr/bin/env python3
"""Plan or run the isolated offscreen check of the image picker surface.

Default prints the plan and runs nothing. --run requires the pinned staged
runtime and Bubblewrap. It stages a private probe under work/picker-port/,
derives the fixture copy of ImagePicker.qml (PanelWindow becomes a plain
Window; layershell properties are removed; the carousel, model, reveal and
dispatch logic stay the real reviewed code), and drives it against the real
Python helper inside a bwrap sandbox: 23 theme rows with the recorded
palette colors (the imported preview images stay outside the sandbox, so
the palette fallback is what the fixture exercises),
the current theme preselected, filter narrowing, carousel movement, a theme
apply that records state plus backup, background rows from a staged
~/Pictures, and a background apply that records state and shows the
daemon note. No host session, shortcut registration, hyprctl success, or
network is involved.
"""
import base64
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
MARKER = 'OMABUNTU_PICKER_FIXTURE_OK'
HELPERS = ('menu_model.py', 'menu_common.py', 'theme_backend.py',
           'font_backend.py', 'background_backend.py', 'power_actions.py')
DATA = (('omabuntu-menu.jsonc', 'config/shell/omabuntu-menu.jsonc'),
        ('themes.json', 'config/menu/themes.json'))
PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')

PROBE = '''//@ pragma IgnoreSystemSettings
import QtQuick
import Quickshell
ShellRoot {
  id: test
  property var picker: null
  property int stage: 0
  property int tries: 0
  property string lastWait: ""
  function assert(value, message) { if (!value) throw new Error(String(message)) }
  function ready(value, message) { if (!value) { lastWait = String(message); throw new Error("NOTREADY " + lastWait) } lastWait = "" }
  function fail(error) { console.error("OMABUNTU_PICKER_ASSERT", String(error)); Qt.exit(42) }
  property var stages: [
    function() {
      var factory = Qt.createComponent("ImagePicker.qml", Component.PreferSynchronous)
      assert(factory.status === Component.Ready, "component " + factory.errorString())
      picker = factory.createObject(null)
      factory.destroy()
      assert(picker !== null, "picker construction")
      picker.openThemes()
      assert(picker.shown === true, "open shows the picker")
    },
    function() {
      ready(picker.imagesLoaded, "theme rows")
      assert(picker.imageArray.length === 23, "theme row count is 23")
    },
    function() {
      ready(picker.layoutSettled, "reveal settled")
      assert(picker.currentLabel() === "Gruvbox", "current theme selected")
    },
    function() {
      var entry = picker.imageArray[picker.selectedIndex]
      assert(entry && entry.colors && String(entry.colors.accent).charAt(0) === "#", "palette colors on the row")
      assert(String(entry.colors.background).charAt(0) === "#", "palette background on the row")
    },
    function() {
      picker.updateFilter("tokyo")
      assert(picker.currentLabel() === "Tokyo Night", "filter narrows to Tokyo Night")
      picker.updateFilter("")
      assert(picker.currentLabel() === "Tokyo Night", "clearing the filter keeps the selection")
    },
    function() {
      var before = picker.selectedIndex
      picker.handleKey({ key: Qt.Key_Right, text: "" })
      assert(picker.selectedIndex !== before, "right arrow moves the carousel")
    },
    function() {
      picker.updateFilter("tokyo")
      picker.applySelected()
    },
    function() {
      ready(picker.shown === false, "theme apply closes the picker")
    },
    function() {
      picker.openBackgrounds()
    },
    function() {
      ready(picker.imagesLoaded, "background rows")
      assert(picker.imageArray.length >= 2, "background row count")
      ready(picker.layoutSettled, "background reveal")
      assert(picker.currentLabel().length > 0, "background label")
    },
    function() {
      picker.applySelected()
    },
    function() {
      ready(String(picker.note).indexOf("Background recorded") === 0, "background note")
      assert(picker.shown === true, "background apply keeps the picker open")
      picker.handleKey({ key: Qt.Key_Escape, text: "" })
      assert(picker.shown === false, "escape closes the picker")
      console.log("__MARKER__")
      picker.destroy()
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

'''.replace("__MARKER__", MARKER)


def _replace(text, old, new='', label=None):
    if text.count(old) != 1:
        raise ValueError('Picker surface witness differs: %r' % (label or old[:40]))
    return text.replace(old, new)


def derive_surface(text):
    """Fixture ownership copy: Window instead of PanelWindow, no
    layershell. The picker logic itself stays byte-for-byte."""
    text = _replace(text, 'import Quickshell.Wayland\n', '', 'wayland import')
    text = _replace(text, 'import QtQuick\n', 'import QtQuick\nimport QtQuick.Window\n', 'qtquick import')
    text = _replace(text, 'PanelWindow {', 'Window {\n  width: 1280\n  height: 800', 'panel window')
    for old in ('  anchors { top: true; bottom: true; left: true; right: true }\n',
                '  exclusionMode: ExclusionMode.Normal\n', '  exclusiveZone: 0\n',
                '  WlrLayershell.namespace: "omabuntu-picker"\n',
                '  WlrLayershell.layer: WlrLayer.Overlay\n',
                '  WlrLayershell.keyboardFocus: shown ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None\n'):
        text = _replace(text, old, '', 'surface property')
    if 'WlrLayershell' in text or 'PanelWindow' in text or 'ExclusionMode' in text:
        raise ValueError('Picker surface retains a host registration')
    return text


def _setenv(command, key, value):
    position = command.index('--chdir')
    command[position:position] = ['--setenv', key, value]


def run(root, build, timeout=120):
    files, _ = preview.verified_sources(root)
    _, runtime, _ = check_runtime.verify_stage(root, build)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    case = root / 'work/picker-port' / stamp
    for name in ('probe/helpers', 'home/runtime', 'home/cache', 'home/data',
                 'home/state/current', 'home/config/omabuntu', 'home/Pictures'):
        (case / name).mkdir(mode=0o700, parents=True, exist_ok=True)
    (case / 'home/state/current/theme.json').write_text(
        json.dumps({'schema_version': 1, 'name': 'gruvbox'}) + '\n')
    (case / 'home/Pictures/omabuntu-a.png').write_bytes(PNG)
    (case / 'home/Pictures/omabuntu-b.png').write_bytes(PNG)
    for name, data in files.items():
        if name == 'ImagePicker.qml':
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
    theme = json.loads((case / 'home/state/current/theme.json').read_text())
    checks.append({'name': 'theme-recorded', 'passed': theme.get('name') == 'tokyo-night'})
    backups = any((case / 'home/state/backups').iterdir()) if (case / 'home/state/backups').is_dir() else False
    checks.append({'name': 'backup-recorded', 'passed': backups})
    background_path = case / 'home/state/current/background.json'
    background = json.loads(background_path.read_text()) if background_path.is_file() else {}
    checks.append({'name': 'background-recorded', 'passed': bool(background.get('path'))})
    ok = (result.returncode == 0 and MARKER in text and 'Configuration Loaded' in text
          and checks[1]['passed'] and checks[2]['passed'] and checks[3]['passed']
          and not any(marker in text for marker in ('OMABUNTU_PICKER_ASSERT', 'TypeError:', 'ReferenceError:',
                                                    'is not installed', 'Binding loop')))
    report = {'status': 'isolated-picker-fixtures-passed' if ok else 'failed', 'checks': checks,
              'limits': ('Synthetic key events and the real helper inside bwrap; theme previews use'
                         ' the imported upstream preview images with the recorded palette as the'
                         ' fallback (the sandbox stages no images, so the fixture drives the'
                         ' fallback); no shortcut registration, hyprctl'
                         ' success, live wallpaper apply, native focus or visual acceptance.')}
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
        print('Plan only: isolated image-picker fixture; use --run --build-dir work/builds/<build-id> after approval.')
        return 0
    if args.build_dir is None:
        parser.error('--run requires --build-dir')
    root = Path(__file__).resolve().parents[1]
    return run(root, args.build_dir)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
