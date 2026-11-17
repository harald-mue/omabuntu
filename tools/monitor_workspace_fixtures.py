#!/usr/bin/env python3
"""Isolated original workspace-widget checks; no real displays, IPC or services."""
import argparse
import json
from pathlib import Path
import subprocess
import datetime

import check_clock_preview
import check_runtime

ROOT = Path(__file__).resolve().parents[1]
HYPRLAND = '''pragma Singleton
import QtQml
QtObject {
  property var focusedMonitor: ({name:"DP-fixture",focused:false,activeWorkspace:{id:13}})
  property var focusedWorkspace: ({id:1})
  property var workspaces: ({values:[
    {id:13,monitor:{name:"DP-fixture"},toplevels:{values:[{}]}},
    {id:17,monitor:{name:"DP-fixture"},toplevels:{values:[]}},
    {id:22,monitor:{name:"DP-fixture"},toplevels:{values:[{}]}}
  ]})
  property QtObject toplevels: QtObject {property var values:[]}
  property bool usingLua:true
  property int refreshCount:0
  property var commands:[]
  signal rawEvent(var event)
  function monitorFor(screen) {return focusedMonitor}
  function dispatch(command) {commands=commands.concat([command])}
  function refreshMonitors() {refreshCount++}
  function refreshWorkspaces() {refreshCount++}
}
'''
FIXTURE = '''//@ pragma IgnoreSystemSettings
import QtQuick
import QtQuick.Window
import Quickshell
import "FixtureHyprland"
ShellRoot {
  id:test
  property var widget:null
  readonly property var commands:Hyprland.commands
  property QtObject bar: QtObject {
    property bool vertical:false
    property int barSize:26
    property color foreground:"white"
    property color barForeground:"white"
    property color urgent:"white"
    property string fontFamily:"monospace"
    property bool foregroundAnimationEnabled:false
    function showTooltip(item,text) {}
    function hideTooltip(item) {}
    function run(command) {throw new Error("Workspace widget must not use the shell command path")}
  }
  Window {id:host;visible:true;width:600;height:26}
  function require(ok,message) {if(!ok)throw new Error(message)}
  Timer {interval:1;running:true;onTriggered:{
    try {
      var factory=Qt.createComponent("MonitorWorkspaces.qml",Component.PreferSynchronous)
      require(factory.status===Component.Ready,factory.errorString())
      widget=factory.createObject(host.contentItem,{bar:test.bar,liveModes:false})
      require(widget!==null,"original widget construction")
      factory.destroy()
      check.start()
    }catch(error){console.error("MONITOR_FIXTURE_ASSERT",String(error));Qt.exit(42)}
  }}
  Timer {id:check;interval:100;onTriggered:{
    try {
      require(widget.block===1,"monitor-local block from visible workspace")
      require(widget.activeWorkspaceId()===13,"local active workspace, not global focus")
      require(JSON.stringify(widget.workspaceIds())==="[11,12,13,14,15,17,22]","first five, used higher slots and visitor")
      require(widget.slotOf(20)===10,"tenth slot")
      require(test.commands.length===0,"no startup action")
      widget.focusWorkspace(14)
      require(test.commands.length===1 && test.commands[0].indexOf('omabuntu_workspaces.focus(4, "DP-fixture")')>=0,"explicit local monitor target")
      widget.focusWorkspace(22)
      require(test.commands.length===2 && test.commands[1].indexOf('workspace = "22"')>=0,"visitor keeps actual ID")
      Hyprland.rawEvent({name:"changeworkspaceid"})
      require(Hyprland.refreshCount===2,"original renumber refresh")
      require(widget.implicitWidth>100 && widget.implicitHeight===26,"original row geometry")
      console.log("OMABUNTU_MONITOR_WORKSPACES_OK")
      widget.destroy();host.visible=false;Qt.callLater(function(){Qt.quit()})
    }catch(error){console.error("MONITOR_FIXTURE_ASSERT",String(error));Qt.exit(42)}
  }}
}
'''


def run(runtime, root=ROOT):
    files, _ = check_clock_preview.verified_sources(root)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    parent = check_runtime.builder.private_directory(root / 'work/workspace-widget-check')
    case = check_runtime.builder.private_directory(parent / stamp)
    for folder in ('probe', 'home', 'home/runtime', 'home/config', 'home/state', 'home/data', 'home/cache'):
        check_runtime.builder.private_directory(case / folder)
    for relative, data in files.items():
        data = data.replace(b'import Quickshell.Hyprland', b'import "FixtureHyprland"')
        depth = len(Path(relative).parts) - 1
        if depth:
            data = data.replace(b'import "FixtureHyprland"',
                                ('import "' + '../' * depth + 'FixtureHyprland"').encode())
        path = case / 'probe' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    fake = case / 'probe/FixtureHyprland'
    fake.mkdir()
    (fake / 'qmldir').write_text('singleton Hyprland 1.0 Hyprland.qml\n')
    (fake / 'Hyprland.qml').write_text(HYPRLAND)
    (case / 'probe/shell.qml').write_text(FIXTURE)
    (case / 'probe/fonts.conf').write_text('<fontconfig><dir>/usr/share/fonts</dir><cachedir>/home/probe/cache/fontconfig</cachedir></fontconfig>\n')
    command = check_runtime.sandbox_command(runtime, case, [check_runtime.PREFIX + '/bin/quickshell',
        '--no-color', '--no-detailed-logs', '--path', '/probe/shell.qml'])
    with (case / 'output.log').open('x') as log:
        try:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=20, check=False)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = None
    output = (case / 'output.log').read_text()
    import re
    ok = (code == 0 and output.count('OMABUNTU_MONITOR_WORKSPACES_OK') == 1
          and not re.search(r'^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b', output, re.M)
          and not any(word in output for word in ('MONITOR_FIXTURE_ASSERT', 'Failed to load configuration')))
    report = {'status': 'isolated-widget-passed' if ok else 'failed', 'returncode': code,
              'limits': 'Synthetic monitor state only; no real display, socket, layout apply, hotplug or visual acceptance.'}
    (case / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(case / 'report.json')
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True, help='Explicit read-only runtime prefix')
    args = parser.parse_args()
    return 0 if run(args.runtime) else 1


if __name__ == '__main__':
    raise SystemExit(main())
