#!/usr/bin/env python3
"""Compile the sealed desktop surfaces in isolation, without any host session."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess

import check_clock_preview as preview
import check_runtime
import audio_port_fixtures
from network_frontend import block

PROBE = '''import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import "FixtureBluetooth"
import "FixturePower"
import "FixtureHyprland"
ShellRoot {
  id: test
  property var views: []
  property var workspaceSwitcher: null
  Timer { interval: 2000; running: true; onTriggered: { console.error("DESKTOP_COMPILE_FAILED: fixture did not finish"); Qt.exit(45); } }
  Window { width: 1200; height: 800; visible: true; Item { id: surface; anchors.fill: parent } }
  QtObject {
    id: bar
    property bool vertical: false
    property string position: "top"
    property int barSize: 26
    property color foreground: "#cacccc"
    property color barForeground: foreground
    property color background: "#101315"
    property color urgent: "#ee8888"
    property string fontFamily: "JetBrainsMono Nerd Font"
    property bool foregroundAnimationEnabled: false
    function registerClickTarget(target) {}
    function unregisterClickTarget(target) {}
    function showTooltip(item, text) {}
    function hideTooltip(item) {}
    function requestPopout(owner) {}
    function releasePopout(owner) {}
  }
  Timer {
    interval: 1; running: true
    onTriggered: {
      var names = ["BluetoothControlView.qml", "DisplayControlView.qml", "PowerControlView.qml", "FloatingDock.qml"];
      for (var i = 0; i < names.length; i++) {
        var factory = Qt.createComponent(names[i], Component.PreferSynchronous);
        if (factory.status !== Component.Ready) {
          console.error("DESKTOP_COMPILE_FAILED", names[i], factory.errorString()); Qt.exit(43); return;
        }
        if (i === 3) {
          var dock = factory.createObject(test);
          if (!dock) throw new Error("Dock construction");
          test.views.push(dock);
        }
        if (i < 3) {
          var view = factory.createObject(surface, {bar:bar});
          if (!view || !view.panelWindow.ensureContent()) { console.error("DESKTOP_CREATE_FAILED", names[i]); Qt.exit(44); return; }
          test.views.push(view);
          if (i === 0) {
            if (view.connectedDevices.length !== 1 || view.scrollRows.length !== 1) throw new Error("Bluetooth groups");
            var device = Bluetooth.defaultAdapter.devices.values[1];
            view.connectDevice(device);
            view.disconnectDevice(device);
            view.forgetDevice(device);
            if (device.connects !== 1 || device.disconnects !== 1 || device.forgets !== 1) throw new Error("Native device action routing");
            view.toggle();
            if (!Bluetooth.defaultAdapter.discovering) throw new Error("Discovery start");
            view.close();
            if (Bluetooth.defaultAdapter.discovering) throw new Error("Owned discovery stop");
          }
          if (i === 1) {
            view.brightnessAvailable = true;
            view.brightnessPercent = 70;
            view.displays = [{name:"eDP-1", enabled:true, focused:true}];
            view.focusedMonitor = "eDP-1";
          }
          if (i === 2) {
            if (Math.abs(view.batteryFraction - 0.63) > 0.001 || view.activeProfile !== "balanced") throw new Error("UPower readings");
            view.setProfile("power-saver");
            if (PowerProfiles.profile !== PowerProfile.PowerSaver || view.previousProfiles[0] !== "balanced") throw new Error("Power profile action");
          }
        }
        factory.destroy();
      }
      var clockFactory = Qt.createComponent("ClockControlView.qml", Component.PreferSynchronous);
      if (clockFactory.status !== Component.Ready) {
        console.error("DESKTOP_COMPILE_FAILED", "ClockControlView.qml", clockFactory.errorString()); Qt.exit(43); return;
      }
      var clock = clockFactory.createObject(surface, {bar:bar, settings:{format:"dddd HH:mm"}});
      clockFactory.destroy();
      if (!clock) { console.error("DESKTOP_CREATE_FAILED", "ClockControlView.qml"); Qt.exit(44); return; }
      clock.togglePanel();
      if (!clock.opened) throw new Error("Calendar did not open");
      var calFactory = Qt.createComponent("CalendarPanel.qml", Component.PreferSynchronous);
      if (calFactory.status !== Component.Ready) {
        console.error("DESKTOP_COMPILE_FAILED", "CalendarPanel.qml", calFactory.errorString()); Qt.exit(43); return;
      }
      var cal = calFactory.createObject(surface, {bar:bar, anchorItem:surface, settings:{birthYear:1979}});
      calFactory.destroy();
      if (!cal || cal.weeks.length !== 6) throw new Error("Calendar grid");
      var stamp = cal.viewYear * 12 + cal.viewMonth;
      cal.moveMonth(1);
      if (cal.viewYear * 12 + cal.viewMonth !== stamp + 1) throw new Error("Month step");
      if (cal.birthYear !== 1979) throw new Error("Birth year");
      cal.toggleWeekStart();
      clock.togglePanel();
      if (clock.opened) throw new Error("Calendar did not close");
      finish.start();
    }
  }
  Timer {
    id: finish; interval: 100
    onTriggered: {
      var adapter = Bluetooth.defaultAdapter;
      BluetoothDiscovery.acquire("first", adapter);
      BluetoothDiscovery.acquire("second", adapter);
      BluetoothDiscovery.release("first");
      if (!adapter.discovering) throw new Error("Another panel still owns discovery");
      BluetoothDiscovery.release("second");
      if (adapter.discovering) throw new Error("Last discovery owner did not release");
      adapter.discovering = true;
      BluetoothDiscovery.acquire("external", adapter);
      BluetoothDiscovery.release("external");
      if (!adapter.discovering) throw new Error("Stopped an external discovery session");
      adapter.discovering = false;
      if (TrialDesktopState.isFloating(2)) throw new Error("Unexpected dock grant");
      TrialDesktopState.applied(2, "floating");
      if (!TrialDesktopState.isFloating(2) || TrialDesktopState.isFloating(3)) throw new Error("Scoped dock grant");
      TrialDesktopState.applied(2, "dwindle");
      if (TrialDesktopState.isFloating(2)) throw new Error("Dock grant not revoked");
      var wsFactory = Qt.createComponent("WorkspaceSwitcher.qml", Component.PreferSynchronous);
      if (wsFactory.status !== Component.Ready) throw new Error(wsFactory.errorString());
      var ws = wsFactory.createObject(surface, {activeId:1, liveModes:true});
      if (!ws) throw new Error("Workspace switcher construction");
      ws.fixtureBusy = true;
      Hyprland.toplevels.values = [
        {address:"0x123", workspace:{id:1}, lastIpcObject:{floating:false}},
        {address:"0x456", workspace:{id:1}, lastIpcObject:{floating:true}},
        {address:"0x789", workspace:{id:2}, lastIpcObject:{floating:false}}];
      // State may arrive after both the switcher and application windows.
      TrialDesktopState.applySaved("1 floating\\n2 scrolling\\n");
      if (ws.activeMode !== "floating" || ws.claimQueue.length !== 2) throw new Error("Late floating restore");
      ws.restoreFloating();
      if (ws.claimQueue.length !== 2) throw new Error("Duplicate queued claims");
      ws.fixtureBusy = false;
      ws.drainClaims(); ws.drainClaims();
      if (ws.fixtureClaims.length !== 2 || ws.claimQueue.length !== 0) throw new Error("Lost window burst");
      TrialDesktopState.applied(1, "dwindle");
      if (TrialDesktopState.savedMode(1) !== undefined || ws.activeMode !== "dwindle") throw new Error("Default mode stale");
      TrialDesktopState.applySaved("");
      console.log("OMABUNTU_WORKSPACE_RESTORE_OK");
      test.workspaceSwitcher = ws;
      ws.fixtureBusy = true;
      TrialDesktopState.applySaved("1 floating\\n2 scrolling\\n");
      ws.claimQueue = [];
      ws.fixtureClaims = [];
      Hyprland.rawEvent({name:"fullscreen", data:"0"});
      Hyprland.rawEvent({name:"fullscreen", data:"1"});
      if (ws.claimQueue.length !== 0) throw new Error("Fullscreen arrangement must be delayed");
      checkFullscreen.start();
    }
  }
  Timer {
    id: checkFullscreen; interval: 50
    onTriggered: {
      var ws = test.workspaceSwitcher;
      if (ws.claimQueue.length !== 2) throw new Error("Fullscreen event did not queue floating-workspace candidates");
      ws.fixtureBusy = false;
      ws.drainClaims(); ws.drainClaims();
      if (ws.fixtureClaims.length !== 2 || ws.claimQueue.length !== 0) throw new Error("Fullscreen queue lost candidates");
      for (var i = 0; i < ws.fixtureClaims.length; i++) {
        if (ws.fixtureClaims[i].indexOf('local id = "1"') < 0) throw new Error("Fullscreen arrangement touched tiled workspace");
      }
      ws.fixtureBusy = true;
      Hyprland.rawEvent({name:"fullscreen", data:"0"});
      TrialDesktopState.applied(1, "dwindle");
      checkRevoked.start();
    }
  }
  Timer {
    id: checkRevoked; interval: 50
    onTriggered: {
      var ws = test.workspaceSwitcher;
      if (ws.claimQueue.length !== 0) throw new Error("Revoked floating grant consumed a fullscreen event");
      console.log("OMABUNTU_WORKSPACE_FULLSCREEN_OK");
      Hyprland.toplevels.values = [
        {address:"0x123", workspace:{id:2}, lastIpcObject:{floating:false}},
        {address:"0x456", workspace:{id:1}, lastIpcObject:{floating:true}},
        {address:"0x789", workspace:{id:2}, lastIpcObject:{floating:false}},
        {address:"0x999", workspace:{id:-99}, lastIpcObject:{floating:false}}];
      TrialDesktopState.applySaved("1 floating\\n2 scrolling\\n");
      ws.claimQueue = []; ws.fixtureClaims = [];
      Hyprland.rawEvent({name:"changefloatingmode", data:"123,1"});
      if (ws.claimQueue.length !== 0) throw new Error("Floating-on event must not claim");
      Hyprland.toplevels.values[0].workspace = {id:1};
      Hyprland.rawEvent({name:"movewindowv2", data:"123,1,1"});
      checkDragMove.start();
    }
  }
  Timer {
    id: checkDragMove; interval: 50
    onTriggered: {
      var ws = test.workspaceSwitcher;
      if (ws.claimQueue.length !== 1) throw new Error("Recorded drag move not queued");
      ws.fixtureBusy = false; ws.drainClaims(); ws.fixtureBusy = true;
      ws.fixtureClaims = [];
      // The native drop occurs later than the move, with no second move event.
      Hyprland.rawEvent({name:"changefloatingmode", data:"123,0"});
      Hyprland.rawEvent({name:"changefloatingmode", data:"123,0"});
      Hyprland.rawEvent({name:"changefloatingmode", data:"456,1"});
      Hyprland.rawEvent({name:"changefloatingmode", data:"789,0"});
      Hyprland.rawEvent({name:"changefloatingmode", data:"999,0"});
      Hyprland.rawEvent({name:"changefloatingmode", data:"aaa,0"});
      Hyprland.rawEvent({name:"changefloatingmode", data:"not-hex,0"});
      Hyprland.rawEvent({name:"changefloatingmode", data:"123,0,extra"});
      if (ws.claimQueue.length !== 0) throw new Error("Retile correction must be delayed");
      checkDragDrop.start();
    }
  }
  Timer {
    id: checkDragDrop; interval: 50
    onTriggered: {
      var ws = test.workspaceSwitcher;
      if (ws.claimQueue.length !== 1 || ws.claimQueue[0].address !== "0x123")
        throw new Error("Drop did not queue one addressed floating-workspace correction");
      ws.fixtureBusy = false; ws.drainClaims(); ws.fixtureBusy = true;
      if (ws.fixtureClaims.length !== 1 || ws.fixtureClaims[0].indexOf("address:0x123") < 0)
        throw new Error("Drop correction lost serialized claim");
      ws.fixtureClaims = [];
      // This manual retile is intentionally corrected under the approved policy.
      Hyprland.rawEvent({name:"changefloatingmode", data:"456,0"});
      checkManualRetile.start();
    }
  }
  Timer {
    id: checkManualRetile; interval: 50
    onTriggered: {
      var ws = test.workspaceSwitcher;
      if (ws.claimQueue.length !== 1 || ws.claimQueue[0].address !== "0x456")
        throw new Error("Manual retile did not follow approved workspace policy");
      ws.claimQueue = [];
      ws.liveModes = false;
      Hyprland.rawEvent({name:"changefloatingmode", data:"123,0"});
      checkDisabledRetile.start();
    }
  }
  Timer {
    id: checkDisabledRetile; interval: 50
    onTriggered: {
      var ws = test.workspaceSwitcher;
      if (ws.claimQueue.length !== 0) throw new Error("Disabled policy queued a correction");
      ws.liveModes = true;
      ws.claimQueue = [];
      ws.fixtureApplying = true;
      ws.fixtureApplyId = 1;
      ws.fixtureApplyMode = "dwindle";
      Hyprland.rawEvent({name:"changefloatingmode", data:"123,0"});
      checkModeSwitchRetile.start();
    }
  }
  Timer {
    id: checkModeSwitchRetile; interval: 50
    onTriggered: {
      var ws = test.workspaceSwitcher;
      if (ws.claimQueue.length !== 0) throw new Error("Retile correction undid an in-flight workspace mode switch");
      ws.claimQueue = [{address:"0x123", id:1}];
      ws.fixtureBusy = false; ws.drainClaims(); ws.fixtureBusy = true;
      if (ws.claimQueue.length !== 0 || ws.fixtureClaims.length !== 0)
        throw new Error("An old queued claim undid the workspace mode switch");
      ws.fixtureApplying = false;
      Hyprland.rawEvent({name:"changefloatingmode", data:"123,0"});
      TrialDesktopState.applied(1, "dwindle");
      checkRevokedRetile.start();
    }
  }
  Timer {
    id: checkRevokedRetile; interval: 50
    onTriggered: {
      var ws = test.workspaceSwitcher;
      if (ws.claimQueue.length !== 0) throw new Error("Revoked grant queued a retile correction");
      console.log("OMABUNTU_WORKSPACE_RETILE_OK");
      console.log("OMABUNTU_DESKTOP_COMPILE_OK"); Qt.quit();
    }
  }
}
'''


def run(root, build):
    files, _ = preview.verified_sources(root)
    _, runtime, _ = check_runtime.verify_stage(root, build)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    case = root / 'work/desktop-panels' / stamp
    for name in ('probe', 'home/runtime', 'home/config', 'home/cache', 'home/state', 'home/data'):
        (case / name).mkdir(mode=0o700, parents=True, exist_ok=True)
    for name, data in files.items():
        path = case / 'probe' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name == 'Ui/KeyboardPanel.qml':
            data = audio_port_fixtures.KEYBOARD_SURFACE.replace('Math.min(cap,value+28)', 'Math.min(cap || 1000,value+28)').encode()
        if name == 'BluetoothActions.qml':
            data = data.replace(b'import Quickshell.Bluetooth', b'import "FixtureBluetooth"')
        if name == 'PowerPanelController.qml':
            data = data.replace(b'import Quickshell.Services.UPower', b'import "FixturePower"')
        if name in ('FloatingDock.qml', 'DockWindow.qml', 'WorkspaceSwitcher.qml'):
            data = data.replace(b'import Quickshell.Hyprland', b'import "FixtureHyprland"')
        if name == 'WorkspaceSwitcher.qml':
            # Exercise state/queue logic without executing compositor commands.
            data = data.replace(b'id: root', b'id: root\n  property bool fixtureBusy: false\n  property var fixtureClaims: []', 1)
            data = data.replace(b'claimProc.running', b'root.fixtureBusy')
            data = data.replace(b'id: root\n', b'id: root\n  property bool fixtureApplying: false\n  property int fixtureApplyId: -1\n  property string fixtureApplyMode: ""\n', 1)
            data = data.replace(b'applyProc.running', b'root.fixtureApplying')
            data = data.replace(b'applyProc.requestId', b'root.fixtureApplyId')
            data = data.replace(b'applyProc.requestMode', b'root.fixtureApplyMode')
            data = data.replace(b'claimProc.exec(["hyprctl", "eval", script])',
                                b'root.fixtureClaims = root.fixtureClaims.concat([script])')
        if name == 'DockWindow.qml':
            text = data.decode()
            text = text.replace('PanelWindow {', '''Item {
  property var screen: null
  property int exclusionMode
  property int exclusiveZone
  property color color
  property var mask
  readonly property Item contentItem: window''', 1)
            text = text.replace(block(text, '  anchors {'), '')
            text = '\n'.join(line for line in text.splitlines() if 'WlrLayershell.' not in line)
            data = text.encode()
        path.write_bytes(data)
    fake = case / 'probe/FixtureHyprland'
    fake.mkdir()
    (fake / 'qmldir').write_text('singleton Hyprland 1.0 Hyprland.qml\nHyprlandFocusGrab 1.0 FocusGrab.qml\n')
    (fake / 'Hyprland.qml').write_text('pragma Singleton\nimport QtQml\nQtObject { property QtObject toplevels: QtObject { property var values: [] }; property var workspaces: ({values:[]}); property var focusedWorkspace: null; signal rawEvent(var event); function refreshWorkspaces() {} function refreshToplevels() {} function monitorFor(screen) { return null; } }')
    (fake / 'FocusGrab.qml').write_text('import QtQuick\nItem { property bool active: false; property var windows: []; signal cleared() }\n')
    fake = case / 'probe/FixtureBluetooth'
    fake.mkdir()
    (fake / 'qmldir').write_text('singleton Bluetooth 1.0 Bluetooth.qml\n')
    (fake / 'Bluetooth.qml').write_text('''pragma Singleton
import QtQml
QtObject {
  property QtObject defaultAdapter: QtObject {
    property bool enabled: true
    property bool discovering: false
    property var devices: ({values:[
      {address:"AA:BB:CC:DD:EE:01", name:"Speaker", connected:true, paired:true, batteryAvailable:true, battery:0.8},
      {address:"AA:BB:CC:DD:EE:02", name:"Headset", connected:false, paired:true, connects:0, disconnects:0, forgets:0,
       connect:function(){this.connects++}, disconnect:function(){this.disconnects++}, forget:function(){this.forgets++}}
    ]})
  }
}
''')
    fake = case / 'probe/FixturePower'
    fake.mkdir()
    (fake / 'qmldir').write_text('singleton UPower 1.0 UPower.qml\nsingleton PowerProfiles 1.0 PowerProfiles.qml\nsingleton PowerProfile 1.0 PowerProfile.qml\nsingleton UPowerDeviceState 1.0 UPowerDeviceState.qml\n')
    (fake / 'UPower.qml').write_text('pragma Singleton\nimport QtQml\nQtObject { property bool onBattery: true; property var displayDevice: ({isPresent:true, percentage:0.63, state:2, energyCapacity:60, changeRate:8, timeToEmpty:3600, timeToFull:0}) }')
    (fake / 'PowerProfiles.qml').write_text('pragma Singleton\nimport QtQml\nQtObject { property int profile: 1; property bool hasPerformanceProfile: true }')
    (fake / 'PowerProfile.qml').write_text('pragma Singleton\nimport QtQml\nQtObject { enum Profile { PowerSaver, Balanced, Performance } }')
    (fake / 'UPowerDeviceState.qml').write_text('pragma Singleton\nimport QtQml\nQtObject { enum State { Unknown, Charging, Discharging, Empty, FullyCharged, PendingCharge } }')
    (case / 'probe/shell.qml').write_text(PROBE)
    (case / 'probe/fonts.conf').write_text('<fontconfig><dir>/usr/share/fonts</dir></fontconfig>')
    command = check_runtime.sandbox_command(runtime, case, [check_runtime.PREFIX + '/bin/quickshell', '--no-color', '--path', '/probe/shell.qml'])
    index = command.index('QML_IMPORT_PATH')
    command[index + 1] += ':/probe'
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    except subprocess.TimeoutExpired as error:
        # Preserve partial evidence instead of losing it to a Python traceback.
        output = (error.stdout or b'') + (error.stderr or b'')
        result = subprocess.CompletedProcess(command, 124, output.decode(errors='replace'), '\nProbe timed out\n')
    text = result.stdout + result.stderr
    (case / 'output.log').write_text(text)
    ok = (result.returncode == 0 and 'OMABUNTU_DESKTOP_COMPILE_OK' in text
          and not any(marker in text for marker in ('DESKTOP_COMPILE_FAILED', 'DESKTOP_CREATE_FAILED', 'TypeError:', 'ReferenceError:', 'Cannot assign', 'Unable to assign', 'Binding loop')))
    report = {'status': 'isolated-compile-passed' if ok else ('timeout' if result.returncode == 124 else 'failed'), 'returncode': result.returncode,
              'limits': 'Compilation and original panel construction with synthetic layer ownership, BlueZ and UPower. Mock action routing, shared discovery leases, dock provenance, the derived calendar grid, late workspace-state loading, fullscreen restore scheduling, the native drag event sequence, addressed retile policy, serialized claims and workspace-mode-switch suppression are tested. No native device actions, popup/focus or visual acceptance.'}
    (case / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(case / 'report.json')
    if not ok:
        print('\n'.join(line for line in text.splitlines() if any(key in line for key in ('ERROR', 'FAILED', 'unavailable', 'Type ', 'Cannot', 'Expected'))))
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--build-dir', type=Path)
    args = parser.parse_args(argv)
    if not args.run:
        print('Plan only: isolated desktop fixtures; use --run --build-dir work/builds/<build-id> after approval.')
        return 0
    if args.build_dir is None:
        parser.error('--run requires --build-dir')
    root = Path(__file__).resolve().parents[1]
    return run(root, args.build_dir)


if __name__ == '__main__':
    raise SystemExit(main())
