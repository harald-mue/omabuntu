#!/usr/bin/env python3
"""Plan-only original notification pointer/focus diagnostics on a private native lab."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

import build_runtime as builder
import build_notification_runtime as variant
import check_native_graphics as graphics
import check_native_notifications as notifications
import check_notification_runtime as ownership
import check_clock_preview as preview
import notification_frontend

ROOT=Path(__file__).resolve().parents[1]
QML='''import QtQuick
import Quickshell
import Quickshell.Io
import "Notifications" as Notifications
ShellRoot {
 QtObject {id:context;property QtObject bar:QtObject {
  property string position:"top";property int barSize:26;property bool barHidden:false
  function barSizeFor(name){return 26}
 }}
 FloatingWindow {
  id:bg;visible:true;fullscreen:true;title:"Omabuntu-Input-Fixture";color:"#182028"
  property int clicks:0;property int aKeys:0
  Item {id:receiver;anchors.fill:parent;focus:true
   Keys.onPressed:function(event){if(event.key===Qt.Key_A)bg.aKeys++;event.accepted=true}
   MouseArea {anchors.fill:parent;onPressed:receiver.forceActiveFocus();onClicked:bg.clicks++}
  }
 }
 Notifications.Service {id:service;shell:context;storageHelper:"/probe/helpers/notification_state.py"}
 IpcHandler {target:"nativeNotificationFixture"
  function metrics():string {
   var screen=Quickshell.screens[0],margin=service.marginsFor(String(screen.name))
   return JSON.stringify({ready:service.storeReady&&service.quietLoaded,
    width:bg.width,height:bg.height,screenWidth:screen.width,screenHeight:screen.height,
    clicks:bg.clicks,aKeys:bg.aKeys,backgroundFocus:receiver.activeFocus,
    pointerIn:service.pointerIn,hoverKey:service.hoverKey,
    left:screen.width-service.notificationWidth-margin.right,top:margin.top,
    cardWidth:service.notificationWidth,placements:service.layout.placements})
  }
 }
 Timer {interval:35000;running:true;onTriggered:{console.error("PRIVATE_NATIVE_INPUT_WATCHDOG");Qt.exit(98)}}
}
'''
# Reuse only Plan 178's test-driver bootstrap, never transform staged QML/source.
BOOTSTRAP_MARKER='try:\n for path in '
if notifications.DRIVER.count(BOOTSTRAP_MARKER)!=1:raise ValueError('Native fixture bootstrap changed')
BOOTSTRAP=notifications.DRIVER.split(BOOTSTRAP_MARKER)[0]
DRIVER=BOOTSTRAP+r'''
from native_pointer_fixture import Pointer
pointer=None
try:
 for path in ('/run/user','/dev/dri','/dev/input','/sys','/etc/xdg','/var/run/dbus/system_bus_socket'):
  require(not Path(path).exists(),'no host path: '+path)
 require(count==1,'single-output pointer fixture only')
 require(not any(k in env for k in ('HYPRLAND_INSTANCE_SIGNATURE','WAYLAND_DISPLAY','WAYLAND_SOCKET','DISPLAY')),'no inherited session')
 bus=spawn('bus',['dbus-daemon','--nofork','--nopidfile','--config-file=/probe/bus.conf'])
 wait(lambda:Path('/home/probe/runtime/private-bus').is_socket(),'private bus ready')
 env['DBUS_SESSION_BUS_ADDRESS']=ADDRESS;dbus('org.freedesktop.DBus.GetId')
 compositor=spawn('compositor',[LAB+'labwc','-d','-C','/probe/labwc'],env)
 def socket():
  sockets=[p for p in Path('/home/probe/runtime').glob('wayland-*') if p.is_socket()]
  return sockets[0] if len(sockets)==1 else None
 display=wait(socket,'private compositor ready');env['WAYLAND_DISPLAY']=display.name
 protocols=command([LAB+'wayland-info']);Path('/home/probe/protocols.log').write_text(protocols)
 outputs=sorted(set(re.findall(r"name:\s*['\"]?(HEADLESS-\d+)",protocols)))
 require(len(outputs)==1 and 'zwlr_virtual_pointer_manager_v1' in protocols,'private pointer/output globals')
 shell=spawn('shell',[QS,'--no-color','--no-detailed-logs','--path','/probe/shell.qml'],env)
 wait(lambda:owner() is not None,'original native owner')
 require(dbus('org.freedesktop.DBus.GetConnectionUnixProcessID',owner())==shell.pid,'actual original fixture owner')
 wait(lambda:metrics()['ready'] and metrics()['width']==1280 and metrics()['height']==720,'full-output native background')
 require((metrics()['screenWidth'],metrics()['screenHeight'])==(1280,720),'known single-output coordinates')
 os.environ.update(WAYLAND_DISPLAY=display.name)
 pointer=Pointer();time.sleep(.3)
 def click_through(x,y,label):
  before=metrics()['clicks'];pointer.move(x,y);time.sleep(.15);pointer.click()
  wait(lambda:metrics()['clicks']==before+1,label)
 click_through(1200,300,'idle original surface click-through inside its transparent strip')
 command([LAB+'wtype','-s','500','-k','a','-s','100'])
 wait(lambda:metrics()['aKeys']==1,'native background key before exclusive mode')
 checks.append({'name':'idle-click-through-and-native-background-key','passed':True})
 notify('Pointer fixture',low=True)
 wait(lambda:probe()['toasts']==1,'native pointer card ready');time.sleep(.4)
 m=metrics();x=int(m['left']+m['cardWidth']/2);y=int(m['top']+25)
 # The same overlay buffer is mapped both above and below its actual deck.
 click_through(1200,300,'occupied original surface outside-deck click-through')
 pointer.move(x,y)
 wait(lambda:metrics()['pointerIn'] and probe()['expanded'],'actual hover expands original deck')
 time.sleep(5.3)
 require(probe()['toasts']==1 and probe()['expanded'],'original native hover pauses minimum lifetime')
 capture('hover-held')
 pointer.move(300,400)
 wait(lambda:not metrics()['pointerIn'] and not probe()['expanded'],'actual leave collapses original deck')
 wait(lambda:probe()['toasts']==0,'original lifetime resumes after native pointer leave',timeout=6)
 checks.append({'name':'native-hover-hold-leave-and-resumed-expiry','passed':True})
 notify('Group one');notify('Group two')
 wait(lambda:probe()['toasts']==2,'grouped pointer cards ready');time.sleep(.4)
 pointer.move(x,y);wait(lambda:probe()['expanded'],'native pointer opens grouped original deck')
 capture('group-expanded');pointer.move(300,400)
 wait(lambda:not probe()['expanded'],'native pointer closes grouped original deck')
 checks.append({'name':'native-grouped-deck-hover-expansion','passed':True})
 clear();notify('Dismiss fixture')
 wait(lambda:probe()['toasts']==1,'native dismiss card ready');time.sleep(.4)
 m=metrics();before=m['clicks'];pointer.move(int(m['left']+m['cardWidth']/2),int(m['top']+25));time.sleep(.2)
 pointer.click(273)
 wait(lambda:probe()['toasts']==0,'original native right-click dismissal')
 require(metrics()['clicks']==before,'card consumes native click rather than leaking to background')
 checks.append({'name':'native-card-dismissal-not-background-click','passed':True})
 receiver_signal=spawn('signals',['gdbus','monitor','--session','--dest',owner(),'--object-path','/org/freedesktop/Notifications'],env)
 wait(lambda:'Monitoring signals' in Path('/home/probe/signals.log').read_text(),'native action observer ready')
 action_id=notify('Click action fixture',actions=True)
 wait(lambda:probe()['toasts']==1,'native left-click action card ready');time.sleep(.4)
 before=metrics()['clicks'];pointer.move(x,y);time.sleep(.2);pointer.click()
 wait(lambda:'ActionInvoked' in Path('/home/probe/signals.log').read_text(),'native left click invokes standard action')
 signals=Path('/home/probe/signals.log').read_text()
 require(signals.count('ActionInvoked')==1 and str(action_id) in signals and "'default'" in signals,'matching single native click action signal')
 require(metrics()['clicks']==before,'action click does not leak to background')
 checks.append({'name':'native-left-click-standard-action-signal','passed':True});clear()
 pointer.move(300,400);click_through(300,400,'background refocus before exclusive mode')
 notify('Focus fixture');wait(lambda:probe()['toasts']==1,'focus fixture card ready')
 before=metrics()['aKeys'];require(ipc('keyboard')=='on','original exclusive mode on')
 command([LAB+'wtype','-s','500','-k','a','-s','100'])
 require(metrics()['aKeys']==before and probe()['keyboardMode'],'exclusive mode prevents background key delivery')
 command([LAB+'wtype','-s','500','-k','Escape','-s','100'])
 wait(lambda:not probe()['keyboardMode'],'native Escape stops original exclusive mode')
 # No refocus click or handler call between Escape and this native key.
 command([LAB+'wtype','-s','500','-k','a','-s','100'])
 wait(lambda:metrics()['aKeys']==before+1,'native background key after exclusive release without refocus')
 checks.append({'name':'native-exclusive-keyboard-and-background-handoff','passed':True})
 capture('focus-returned');clear()
 log=Path('/home/probe/shell.log').read_text();compositor_log=Path('/home/probe/compositor.log').read_text()
 require('llvmpipe' in log and 'Creating pixman renderer' in compositor_log and 'Created shm allocator' in compositor_log,'actual contained graphics')
 expected='$HYPRLAND_INSTANCE_SIGNATURE is unset. Cannot connect to hyprland.'
 diagnostics=[line for line in log.splitlines() if re.search(r'^\s*(WARN|ERROR|FATAL|CRITICAL)\b',line)]
 require(len(diagnostics)==1 and expected in diagnostics[0],'only absent-Hyprland warning expected')
 require(not any(x in log for x in ('TypeError:','ReferenceError:','Binding loop','Unable to assign','PRIVATE_NATIVE_INPUT_WATCHDOG')),'no hidden QML failure')
 require(not Path('/home/probe/forbidden-actions.log').exists(),'no activation sentinel triggered')
 result={'status':'passed','checks':checks,'final_metrics':metrics(),'outputs':outputs}
except Exception as error:
 result={'status':'failed','checks':checks,'error':type(error).__name__+': '+str(error)}
 try:result['failure_metrics']=metrics();result['failure_probe']=probe()
 except Exception:pass
finally:
 if pointer is not None:
  try:pointer.close()
  except Exception:result.update(status='failed',pointer_cleanup_failed=True)
 for p in reversed(children):stop(p)
 for f in files:f.close()
 result['children_reaped']=all(p.poll() is not None for p in children)
Path('/home/probe/native-input-results.json').write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(0 if result['status']=='passed' else 1)
'''


def run(root,lab_dir,candidate):
    lab=graphics.verify_lab(root,lab_dir);ownership.eligibility(root,candidate)
    _,runtime,_=variant.verify(root,candidate);files,_=preview.verified_sources(root)
    sealed=notification_frontend.sources(root)
    if any(files.get(name)!=data for name,data in sealed.items()):raise ValueError('Original notification closure differs')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    case=builder.private_directory(builder.private_directory(root/'work/native-input-probes')/stamp)
    for directory in ('probe','probe/helpers','probe/labwc','home','home/runtime','home/config','home/cache','home/data','home/state'):
        builder.private_directory(case/directory)
    for name,data in files.items():
        path=case/'probe'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    for name,data in {'shell.qml':QML,'driver.py':DRIVER,'bus.conf':ownership.BUS,'deny-exec':graphics.GUARD,
                      'labwc/rc.xml':'<labwc_config/>\n','fonts.conf':'<fontconfig><dir>/usr/share/fonts</dir><cachedir>/home/probe/cache/fontconfig</cachedir></fontconfig>',
                      'passwd':'probe:x:%d:%d:Private probe:/home/probe:/bin/false\n'%(os.getuid(),os.getgid()),
                      'group':'probe:x:%d:\n'%os.getgid()}.items():(case/'probe'/name).write_text(data)
    for source,target in (('notification_state.py','helpers/notification_state.py'),('native_pointer_fixture.py','native_pointer_fixture.py')):
        (case/'probe'/target).write_bytes((root/'tools'/source).read_bytes())
    (case/'probe/deny-exec').chmod(0o555)
    inputs=builder.artifact_manifest(case/'probe');before_lab=graphics.package_manifest(lab/'root');before_runtime=builder.artifact_manifest(runtime)
    command=graphics.sandbox(runtime,case,lab,1)
    with (case/'output.log').open('x') as stream:
        try:code=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=55,check=False).returncode
        except subprocess.TimeoutExpired:code=None
    path=case/'home/native-input-results.json'
    report=json.loads(path.read_text()) if path.is_file() else {'status':'failed','error':'Missing bounded native input result'}
    unchanged=inputs==builder.artifact_manifest(case/'probe') and before_lab==graphics.package_manifest(lab/'root') and before_runtime==builder.artifact_manifest(runtime)
    report.update(returncode=code,command=command,inputs_unchanged=unchanged,
                  checker_sha256=builder.digest(Path(__file__)),pointer_sha256=builder.digest(root/'tools/native_pointer_fixture.py'),
                  bootstrap_checker_sha256=builder.digest(root/'tools/check_native_notifications.py'),
                  runtime_sha256=builder.digest(runtime/'bin/quickshell'),
                  notification_sources={name:hashlib.sha256(data).hexdigest() for name,data in sealed.items()},
                  limits='Single-output Labwc owned background only; no host/Hyprland/real app/clipboard/locked privacy/security/crash/live migration acceptance.')
    if code!=0 or not unchanged or not report.get('children_reaped'):report['status']='failed'
    report['captures']={p.name:builder.digest(p) for p in (case/'home').glob('*.ppm')}
    (case/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(case/'report.json')
    return 0 if report['status']=='passed' else 1


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true')
    p.add_argument('--lab-dir',type=Path);p.add_argument('--candidate',type=Path);args=p.parse_args(argv)
    if not args.run:print('Plan only: private original notification pointer/focus fixture; no host session');return 0
    if args.lab_dir is None or args.candidate is None:p.error('--run requires --lab-dir and --candidate')
    os.umask(0o077)
    return run(ROOT,args.lab_dir,args.candidate)


if __name__=='__main__':raise SystemExit(main())
