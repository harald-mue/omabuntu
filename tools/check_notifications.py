#!/usr/bin/env python3
"""Fixed device-free original-notification probes; no real bus or displays."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess

import check_clock_preview as preview
import check_runtime as runtime
import notification_state

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'OMABUNTU_NOTIFICATIONS_FIXTURE_OK'
FAKE_SERVER = '''import QtQuick
QtObject {
 property bool keepOnReload:false
 property bool imageSupported:false
 property bool actionsSupported:false
 property bool bodyMarkupSupported:false
 property bool bodyHyperlinksSupported:false
 property bool persistenceSupported:false
 signal notification(var notification)
}
'''
FAKE_NOTIFICATION = '''import QtQuick
QtObject {
 property int id:42
 property bool tracked:false
 property string summary:"First message"
 property string body:"Fixture body"
 property string appName:"Fixture"
 property string appIcon:""
 property string desktopEntry:""
 property string image:""
 property int urgency:1
 property int expireTimeout:0
 property var hints:({})
 property var actions:[]
 signal closed()
 function dismiss(){closed()}
 function expire(){closed()}
}
'''
FAKE_HYPRLAND = '''pragma Singleton
import QtQuick
QtObject {
 property var focusedMonitor:null
 property var toplevels:({values:[]})
 signal rawEvent(var event)
 function monitorFor(screen){return null}
 function refreshToplevels(){}
 function dispatch(value){throw new Error("unexpected fixture focus")}
}
'''
FIXTURE = '''//@ pragma IgnoreSystemSettings
import QtQuick
import Quickshell
import "Notifications/Store.js" as Store
import "Notifications/Delivery.js" as Delivery
import "Notifications/Security.js" as Security
import "Notifications/Actions.js" as Actions
ShellRoot {
 id:test
 property var host:null
 property var notice:null
 property var card:null
 property int phase:0
 property int ticks:0
 property int actionCalls:0
 property string key:""
 QtObject {id:legacy; property bool known:true;property bool doNotDisturb:false}
 function require(value,message){if(!value)throw new Error(message)}
 function make(file,props){
  var c=Qt.createComponent(file,Component.PreferSynchronous)
  require(c.status===Component.Ready,c.errorString())
  var o=c.createObject(null,props||{});c.destroy();require(o!==null,"construction "+file);return o
 }
 Timer {interval:25;repeat:true;running:true;onTriggered:{try{
  test.ticks++;require(test.ticks<120,"bounded fixture")
  if(test.phase===0){
   test.host=make("NotificationHost.qml",{legacyDnd:legacy,menuHelper:"/probe/helpers/menu_model.py"})
   require(test.host.service===null&&test.host.dnd===legacy,"default host cannot claim notification role")
   test.host.deploymentApproved=true
   require(test.host.service===null,"deployment consent alone is not runtime proof")
   test.host.exclusiveRuntimeVerified=true
   test.phase=1;return
  }
  var s=test.host.service
  if(test.phase===1){
   if(!s||!s.quietLoaded||!s.storeReady)return
   require(test.host.dnd.known&&test.host.dnd.writable,"DND binds to original service after private state readiness")
   require(s.durationFor(1,0)===8000&&s.durationFor(0,0)===5000&&s.durationFor(2,1)===0&&s.durationFor(1,99999)===30000,"original expiry policy")
   require(!Actions.admittedArgv(["bash","-c","exit"]),"arbitrary hint command refused")
   require(!!Actions.admittedArgv(["/usr/bin/xdg-open","https://example.org/"]),"closed external URL action")
   require(!Security.safeExternalUrl("file:///etc/passwd")&&!Security.safeExternalUrl("https://user@example.org/"),"original URL policy")
   test.notice=make("FixtureNotification.qml")
   s.handleNotification(test.notice);test.phase=2;return
  }
  if(test.phase===2){
   require(s.liveCount()===1&&s.layout.decks.length===1,"deferred original arrival and deck")
   test.key=s.newestLive();require(test.key!=="","live key")
   test.card=make("Notifications/Toast.qml",{row:Store.snapshot(test.notice,test.key,{Normal:1}),scene:s})
   require(test.card.cardWidth>0&&test.card.targetHeight>0,"actual original card constructs and measures")
   test.notice.actions=[{identifier:"default",text:"Open",invoke:function(){test.actionCalls++}}]
   require(s.invokeSenderAction(test.key,"default")&&test.actionCalls===1,"original live sender action executes once")
   require(s.startKeyboard(test.key)&&s.keyboardMode,"original keyboard selection")
   require(s.keyboardPressed(Qt.Key_Escape,"")&&!s.keyboardMode,"keyboard mode releases on Escape")
   test.notice.summary="Updated message";test.phase=3;return
  }
  if(test.phase===3){
   require(s.liveCount()===1&&s.newestLive()===test.key,"replacement signal does not duplicate notification")
   require(s.liveEntries[0].summary==="Updated message","replacement updates stored snapshot")
   s.pointerIn=true;s.pointerEntered(undefined)
   var second=make("FixtureNotification.qml",{id:43})
   s.handleNotification(second)
   require(s.held.length===1,"new cards wait while original deck is being read")
   s.pointerIn=false;s.releaseHeld();test.phase=4;return
  }
  if(test.phase===4){
   require(s.liveCount()===2&&s.layout.decks.length===1,"source-grouped original deck")
   s.clearAll("dismissed",true);test.phase=5;return
  }
  if(test.phase===5){
   require(s.liveCount()===0,"deferred dismissal releases model ownership")
   require(test.host.dnd.setDoNotDisturb(true)&&s.doNotDisturb,"DND setter uses original owner")
   var quiet=make("FixtureNotification.qml",{id:44});s.handleNotification(quiet)
   require(s.liveCount()===0&&s.historyEntries[0].closed_reason==="silenced","DND holds normal content in history")
   var code=make("FixtureNotification.qml",{id:45,body:"Your verification code is 123456"})
   s.handleNotification(code);test.phase=6;return
  }
  if(test.phase===6){
   require(s.liveCount()===1,"original verification-code DND exception")
   require(JSON.stringify(s.liveEntries).indexOf("123456")<0,"code text is redacted before persistence")
   test.host.dnd.setDoNotDisturb(false)
   s.flushStore();test.card.destroy()
   test.host.deploymentApproved=false
   require(test.host.service===null&&test.host.dnd===legacy,"explicit release returns only to pre-existing adapter")
   console.log("OMABUNTU_NOTIFICATIONS_FIXTURE_OK");Qt.quit()
  }
 }catch(error){console.error("OMABUNTU_NOTIFICATIONS_ASSERT "+error);Qt.exit(42)}}}
}
'''


def fixture_service(data):
    text = data.decode()
    text = preview.notification_frontend.replace(text, 'import Quickshell.Hyprland', 'import "../FixtureHyprland"')
    text = preview.notification_frontend.replace(text, 'import Quickshell.Services.Notifications', 'import "../FixtureNotifications"')
    start = text.index('  Variants {\n    id: surfaceVariants')
    text = text[:start] + '  QtObject { id: surfaceVariants; property var instances: [] }\n}\n'
    text = preview.notification_frontend.replace(text, '  IpcHandler {', '  QtObject {')
    text = preview.notification_frontend.replace(text, '    target: "omabuntuNotifications"\n', '')
    return text.encode()


def run(build_dir):
    files, _ = preview.verified_sources(ROOT)
    _, stage, _ = runtime.verify_stage(ROOT, build_dir)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    base = runtime.builder.private_directory(ROOT / 'work/notification-probes')
    case = runtime.builder.private_directory(base / stamp)
    for name in ('probe', 'home', 'home/runtime', 'home/config', 'home/cache', 'home/state', 'home/data'):
        (case / name).mkdir(mode=0o700, exist_ok=True)
    for name, data in files.items():
        if name == 'Notifications/Service.qml':
            data = fixture_service(data)
        target = case / 'probe' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    fake = case / 'probe/FixtureNotifications';fake.mkdir()
    (fake / 'NotificationServer.qml').write_text(FAKE_SERVER)
    (fake / 'NotificationUrgency.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject { readonly property int low:0;readonly property int normal:1;readonly property int critical:2 }\n')
    # Original source uses enum-style values; a singleton's uppercase QML
    # properties are not legal. The fixed fixture injects the enum namespace.
    service = case / 'probe/Notifications/Service.qml'
    service.write_text(service.read_text().replace('NotificationUrgency.Critical', '2').replace('NotificationUrgency.Low', '0').replace('NotificationUrgency)', '({Normal:1}))'))
    (fake / 'qmldir').write_text('NotificationServer 1.0 NotificationServer.qml\n')
    hypr = case / 'probe/FixtureHyprland';hypr.mkdir()
    (hypr / 'Hyprland.qml').write_text(FAKE_HYPRLAND)
    (hypr / 'qmldir').write_text('singleton Hyprland 1.0 Hyprland.qml\n')
    (case / 'probe/FixtureNotification.qml').write_text(FAKE_NOTIFICATION)
    helpers = case / 'probe/helpers';helpers.mkdir()
    (helpers / 'notification_state.py').write_bytes((ROOT / 'tools/notification_state.py').read_bytes())
    (case / 'probe/shell.qml').write_text(FIXTURE)
    before = runtime.builder.artifact_manifest(case / 'probe')
    command = runtime.sandbox_command(stage, case, [runtime.PREFIX + '/bin/quickshell', '--no-color', '--no-detailed-logs', '--path', '/probe/shell.qml'])
    log = case / 'output.log'
    code = None
    with log.open('x') as stream:
        try:
            code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=15, check=False).returncode
        except subprocess.TimeoutExpired:
            pass
    output = log.read_text(errors='replace')
    unchanged = before == runtime.builder.artifact_manifest(case / 'probe')
    disk_checked = False
    try:
        home = case / 'home/.local/state/omabuntu'
        directory = home / 'notifications'
        assert all((directory / name).is_file() for name in notification_state.DEFAULTS)
        notification_state.prepare(home)
        assert all('123456' not in (directory / name).read_text() for name in notification_state.DEFAULTS)
        assert json.loads((directory / 'quiet.json').read_text()) == {'dnd': False}
        disk_checked = True
    except (OSError, ValueError, AssertionError):
        pass
    passed = code == 0 and unchanged and disk_checked and output.count(MARKER) == 1 and not any(x in output for x in ('WARN', 'ERROR', 'FATAL', 'CRITICAL', 'ASSERT'))
    report = {'passed': passed, 'returncode': code, 'inputs_unchanged': unchanged,
              'private_state_valid_and_code_redacted': disk_checked,
              'limits': 'Original engine/card models and synthetic owner/actions only. No real notification bus, images, clipboard, native surfaces, focus or visual acceptance.'}
    (case / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(case / 'report.json')
    return 0 if passed else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--build-dir', type=Path)
    args = parser.parse_args(argv)
    if not args.run:
        print('Plan only: fixed original notification probes in device-free containment')
        return 0
    if not args.build_dir:
        parser.error('--run requires --build-dir')
    return run(args.build_dir)


if __name__ == '__main__':
    raise SystemExit(main())
