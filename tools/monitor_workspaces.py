#!/usr/bin/env python3
"""Derive the pinned original monitor workspace policy and bar, without activation.

No host configuration reads, subprocesses, reloads, or installation. The legacy
bar remains selected until a separately approved deployment enables the policy.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = 'ac2690cd7be4f47e4a255f5e2e78d904d436b068'
POLICY = 'vendor/omarchy/default/hypr/monitor-workspaces.lua'
WIDGET = 'vendor/omarchy/shell/plugins/bar/widgets/Workspaces.qml'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Monitor workspace source witness differs: ' + old[:80])
    return text.replace(old, new, 1)


def derive_policy(source, state_adapter):
    text = source.decode()
    text = replace_once(text, 'local paths = require("default.hypr.paths")', '''-- Ubuntu namespace/state adapter; original MIT source is preserved in vendor/.
local o = { bind_expressions = {} }
function o.shell_quote(value)
  return "'" .. tostring(value):gsub("'", "'\\\"'\\\"'") .. "'"
end
local State = (function()
''' + state_adapter.decode() + '''
end)()
local paths = { state_home = os.getenv("XDG_STATE_HOME")
  or ((os.getenv("HOME") or "") .. "/.local/state") }''')
    text = replace_once(text, 'local STATE_DIR = paths.state_home .. "/omarchy"',
                        'local STATE_DIR = os.getenv("OMABUNTU_STATE_HOME") or (paths.state_home .. "/omabuntu")')
    text = replace_once(text,
                        '  hl.dispatch(hl.dsp.workspace.change_id({ workspace = tostring(old), id = id }))',
                        '''  State.renumber(workspace, id, function()
    hl.dispatch(hl.dsp.workspace.change_id({ workspace = tostring(old), id = id }))
  end)''')
    for variable, content, tail in (
            ('MERGED_FILE', 'table.concat(lines)', ''),
            ('STATE_FILE', 'content', '\n  written = content')):
        start = text.index('  local file = io.open(' + variable + ', "w")')
        end = text.index('\nend\n', start)
        text = text[:start] + '  State.atomic_text(' + variable + ', ' + content + ')' + tail + text[end:]
    text = replace_once(text, 'o.workspaces = M', 'omabuntu_workspaces = M')
    # Public expressions remain useful to the keybindings catalog without the
    # original shell/bootstrap, helper PATH or provisioning dependencies.
    text = text.replace('"o.workspaces.', '"omabuntu_workspaces.')
    return text.encode()


def derive_widget(source):
    text = source.decode()
    text = replace_once(text, '  moduleName: "omarchy.workspaces"', '''  moduleName: "omabuntu.workspaces"
  property bool liveModes: false
  WorkspaceSwitcher {
    id: layoutBackend
    visible: false
    activeId: root.activeWorkspaceId()
    liveModes: root.liveModes
  }''')
    text = replace_once(text,
                        '    path: (Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state") + "/omarchy/monitor-workspaces"',
                        '''    path: (Quickshell.env("OMABUNTU_STATE_HOME") ||
      ((Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state") + "/omabuntu")) + "/monitor-workspaces"''')
    text = text.replace('o.workspaces.focus(', 'omabuntu_workspaces.focus(')
    text = replace_once(text,
        '    if (root.bar) root.bar.run("hyprctl dispatch " + Util.shellQuote(expression))',
        '    if (Hyprland.usingLua) Hyprland.dispatch(expression)')
    text = replace_once(text,
        '      root.dispatch("omabuntu_workspaces.focus(" + root.slotOf(id) + ", \\\"" + root.monitorName + "\\\")")',
        '      root.dispatch("omabuntu_workspaces.focus(" + root.slotOf(id) + ", " + JSON.stringify(root.monitorName) + ")")')
    start = text.index('  property string activeMode: "dwindle"')
    glyph_start = text.index('  function modeGlyph(mode) {', start)
    glyph_end = text.index('\n\n  // A layout only changes', glyph_start)
    glyph = text[glyph_start:glyph_end]
    end = text.index('  readonly property real trailingGap:', glyph_end)
    text = text[:start] + '''  readonly property string activeMode: layoutBackend.activeMode

''' + glyph + '''

  // Existing Ubuntu layout backend acts on the real workspace ID, not a slot.
  function cycleLayout() {
    if (!root.liveModes) return
    if (root.monitor && !root.monitor.focused)
      root.dispatch("hl.dsp.focus({ monitor = " + JSON.stringify(root.monitorName) + " })")
    layoutBackend.apply(layoutBackend.nextMode(root.activeMode))
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) {
      var name = event ? String(event.name) : ""
      var switched = name === "workspacev2" && root.monitor !== null && root.monitor.focused
      if (switched || name === "moveworkspacev2" || name === "changeworkspaceid") {
        Hyprland.refreshMonitors()
        Hyprland.refreshWorkspaces()
      }
      if (name === "changeworkspaceid" || name === "configreloaded") {
        layoutBackend.modes = ({})
        layoutBackend.syncActive()
      }
    }
  }

''' + text[end:]
    if 'ShellIpc' in text or 'omarchy-hyprland' in text:
        raise ValueError('Monitor bar retained an upstream shell command')
    return text.encode()


def artifacts(root=ROOT):
    return {
        'config/hypr/monitor-workspaces.lua': derive_policy(
            (root / POLICY).read_bytes(), (root / 'config/hypr/workspace-state.lua').read_bytes()),
        'config/shell/preview/MonitorWorkspaces.qml': derive_widget((root / WIDGET).read_bytes()),
    }


def verify(root=ROOT):
    meta = json.loads((root / 'upstream/monitor-workspaces.json').read_text())
    required = {POLICY, WIDGET, 'vendor/omarchy/LICENSE',
                'vendor/omarchy/default/hypr/bindings/tiling.lua'}
    if (meta['schema_version'] != 1 or meta['commit'] != COMMIT or meta['license'] != 'MIT'
            or set(meta['sources']) != required):
        raise ValueError('Monitor workspace provenance differs')
    for path, expected in meta['sources'].items():
        data = (root / path).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        url = 'https://raw.githubusercontent.com/omacom/omarchy/' + COMMIT + '/' + path.removeprefix('vendor/omarchy/')
        if (hashlib.sha256(data).hexdigest() != expected['sha256'] or len(data) != expected['bytes']
                or blob != expected['git_blob_sha1'] or expected['url'] != url):
            raise ValueError('Monitor workspace source changed: ' + path)
    if (root / 'vendor/omarchy/LICENSE').read_bytes() != (root / 'licenses/Omarchy-MIT.txt').read_bytes():
        raise ValueError('Complete monitor workspace license differs')
    for path, data in artifacts(root).items():
        if (root / path).read_bytes() != data:
            raise ValueError('Monitor workspace generated mirror differs: ' + path)
    return meta


def main():
    for path, data in artifacts().items():
        (ROOT / path).write_bytes(data)
        print(path)


if __name__ == '__main__':
    main()
