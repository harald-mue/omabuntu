#!/usr/bin/env python3
"""Plan-only cross-process native notifications on a disposable private compositor/bus."""
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
import check_native_input as native_input
import check_clock_preview as preview
import check_notification_runtime as ownership
import notification_frontend

ROOT=Path(__file__).resolve().parents[1]
SERVICE='''import QtQuick
import Quickshell
import Quickshell.Io
import "Notifications" as Notifications
ShellRoot {
 QtObject {id:context;property QtObject bar:QtObject {
  property string position:"top";property int barSize:26;property bool barHidden:false
  function barSizeFor(name){return 26}
 }}
 Notifications.Service {id:service;shell:context;storageHelper:"/probe/helpers/notification_state.py"}
 IpcHandler {target:"nativeNotificationFixture"
  function metrics():string {
   var screen=Quickshell.screens[0],margin=service.marginsFor(String(screen.name))
   return JSON.stringify({ready:service.storeReady&&service.quietLoaded,
    screenWidth:screen.width,screenHeight:screen.height,
    left:screen.width-service.notificationWidth-margin.right,top:margin.top,cardWidth:service.notificationWidth})
  }
 }
 Timer {interval:35000;running:true;onTriggered:{console.error("PRIVATE_NATIVE_PROCESSES_WATCHDOG");Qt.exit(98)}}
}
'''
APPLICATION='''import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
 FloatingWindow {id:bg;visible:true;fullscreen:true;title:"Omabuntu-Separate-Application";color:"#182028"
  property int clicks:0;property int aKeys:0
  Item {id:receiver;anchors.fill:parent;focus:true
   Keys.onPressed:function(event){if(event.key===Qt.Key_A)bg.aKeys++;event.accepted=true}
   MouseArea {anchors.fill:parent;onPressed:receiver.forceActiveFocus();onClicked:bg.clicks++}
  }
 }
 IpcHandler {target:"nativeApplicationFixture"
  function metrics():string {return JSON.stringify({width:bg.width,height:bg.height,clicks:bg.clicks,aKeys:bg.aKeys,focus:receiver.activeFocus})}
 }
 Timer {interval:35000;running:true;onTriggered:{console.error("PRIVATE_NATIVE_APPLICATION_WATCHDOG");Qt.exit(98)}}
}
'''
DRIVER=native_input.BOOTSTRAP+r'''
import selectors,shlex
from native_pointer_fixture import Pointer
pointer=None;sender_events=[]
def ipc(method,*args,target='omabuntuNotifications'):
 return command([QS,'ipc','--pid',str(shell.pid),'call',target,method,*args])
def app_metrics():
 return json.loads(command([QS,'ipc','--pid',str(application.pid),'call','nativeApplicationFixture','metrics']))
def has_owner(unique):
 value=command(['gdbus','call','--session','--dest','org.freedesktop.DBus','--object-path','/org/freedesktop/DBus','--method','org.freedesktop.DBus.NameHasOwner',unique])
 require(value in ('(true,)','(false,)'),'exact private bus boolean response')
 return value=='(true,)'
class Sender:
 def __init__(self,label):
  self.stream=Path('/home/probe/'+label+'.log').open('w');files.append(self.stream)
  self.p=subprocess.Popen(['/home/probe/sender'],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stream)
  children.append(self.p);self.pending=b'';self.events=[]
  self.ready=self.event('ready')
  require(self.ready['pid']==self.p.pid and self.ready['owner']==owner(),'real persistent sender identity')
  require(dbus('org.freedesktop.DBus.GetConnectionUnixProcessID',self.ready['unique'])==self.p.pid,'sender bus PID matches')
 def event(self,kind,timeout=4):
  end=time.monotonic()+timeout
  selector=selectors.DefaultSelector();selector.register(self.p.stdout,selectors.EVENT_READ)
  try:
   for _ in range(32):
    while b'\n' not in self.pending:
     require(time.monotonic()<end and selector.select(max(0,end-time.monotonic())),'persistent sender event deadline')
     part=os.read(self.p.stdout.fileno(),4096);require(part,'persistent sender closed unexpectedly')
     self.pending+=part;require(len(self.pending)<=8192,'bounded sender event buffer')
    line,self.pending=self.pending.split(b'\n',1);value=json.loads(line)
    self.events.append(value);sender_events.append(value)
    require(value.get('event')!='failed','persistent sender refused operation')
    if value.get('event')==kind:return value
   raise AssertionError('sender event budget exceeded')
  finally:selector.close()
 def send(self,verb):
  require(verb in ('notify','replace','status','quit'),'fixed sender verb')
  self.p.stdin.write((verb+'\n').encode());self.p.stdin.flush()
 def notify(self,replace=False):
  self.send('replace' if replace else 'notify');return self.event('sent')['id']
try:
 for path in ('/run/user','/dev/dri','/dev/input','/sys','/etc/xdg','/var/run/dbus/system_bus_socket'):
  require(not Path(path).exists(),'no host path: '+path)
 require(count==1 and not any(k in env for k in ('HYPRLAND_INSTANCE_SIGNATURE','WAYLAND_DISPLAY','WAYLAND_SOCKET','DISPLAY')),'fresh private single output')
 versions=command(['/usr/bin/pkg-config','--modversion','Qt6Core','Qt6DBus'])
 require(versions.splitlines()==['6.10.2','6.10.2'],'version-matched existing Qt test dependency')
 flags=shlex.split(command(['/usr/bin/pkg-config','--cflags','--libs','Qt6Core','Qt6DBus']))
 build_commands=[['/usr/lib/qt6/libexec/moc','/probe/sender.cpp','-o','/home/probe/sender.moc'],
  ['/usr/bin/c++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-fPIC','-I/home/probe','/probe/sender.cpp','-o','/home/probe/sender',*flags]]
 for args in build_commands:
  result=subprocess.run(args,env=env,capture_output=True,text=True,timeout=35)
  with Path('/home/probe/sender-build.log').open('a') as log:log.write(result.stdout+result.stderr)
  require(result.returncode==0,'private sender compilation')
 bus=spawn('bus',['dbus-daemon','--nofork','--nopidfile','--config-file=/probe/bus.conf'])
 wait(lambda:Path('/home/probe/runtime/private-bus').is_socket(),'private bus ready')
 env['DBUS_SESSION_BUS_ADDRESS']=ADDRESS;dbus('org.freedesktop.DBus.GetId')
 compositor=spawn('compositor',[LAB+'labwc','-d','-C','/probe/labwc'],env)
 def socket():
  sockets=[p for p in Path('/home/probe/runtime').glob('wayland-*') if p.is_socket()]
  return sockets[0] if len(sockets)==1 else None
 display=wait(socket,'private compositor ready');env['WAYLAND_DISPLAY']=display.name
 protocols=command([LAB+'wayland-info']);Path('/home/probe/protocols.log').write_text(protocols)
 outputs=sorted(set(re.findall(r"name:\s*['\"]?(HEADLESS-\d+)",protocols)));require(len(outputs)==1,'one actual output')
 application=spawn('application',[QS,'--no-color','--no-detailed-logs','--path','/probe/app.qml'],env)
 wait(lambda:app_metrics()['width']==1280 and app_metrics()['height']==720,'separate native application ready')
 shell=spawn('shell',[QS,'--no-color','--no-detailed-logs','--path','/probe/shell.qml'],env)
 wait(lambda:owner() is not None and metrics()['ready'],'original native service ready')
 require(application.pid!=shell.pid and dbus('org.freedesktop.DBus.GetConnectionUnixProcessID',owner())==shell.pid,'independent app and notification owner')
 require((metrics()['screenWidth'],metrics()['screenHeight'])==(1280,720),'verified coordinate extent')
 os.environ['WAYLAND_DISPLAY']=display.name;pointer=Pointer();time.sleep(.3)
 pointer.move(300,400);time.sleep(.15);pointer.click();wait(lambda:app_metrics()['clicks']==1,'native click reaches separate app')
 command([LAB+'wtype','-s','500','-k','a','-s','100']);wait(lambda:app_metrics()['aKeys']==1,'separate app native key')
 sender=Sender('sender-one');require(len({sender.p.pid,application.pid,shell.pid})==3,'three real process identities')
 ident=sender.notify();wait(lambda:probe()['toasts']==1,'persistent sender Notify')
 require(sender.notify(replace=True)==ident,'same sender replacement ID');require(probe()['toasts']==1,'replacement not duplicated')
 time.sleep(.4);m=metrics();x=int(m['left']+m['cardWidth']/2);y=int(m['top']+25)
 pointer.move(x,y);time.sleep(.2);pointer.click()
 action=sender.event('action');closed=sender.event('closed')
 require(action['id']==ident and action['count']==1 and action['action']=='default' and closed['id']==ident and closed['reason']==2,'sender receives own action and close callbacks')
 sender.send('status');require(sender.event('status')['callbacks']==1,'persistent sender exact callback count')
 wait(lambda:probe()['toasts']==0,'native action closes original card');require(app_metrics()['clicks']==1,'card action does not leak cross-process')
 checks.append({'name':'persistent-sender-native-action-and-close-callbacks','passed':True})
 pointer.move(300,400);time.sleep(.15);pointer.click();wait(lambda:app_metrics()['clicks']==2,'separate app focus baseline')
 ident=sender.notify();wait(lambda:probe()['toasts']==1,'focus card ready');before=app_metrics()['aKeys']
 require(ipc('keyboard')=='on','original exclusive keyboard admitted')
 command([LAB+'wtype','-s','500','-k','a','-s','100'])
 require(app_metrics()['aKeys']==before and probe()['keyboardMode'],'separate process excluded during exclusive mode')
 command([LAB+'wtype','-s','500','-k','Escape','-s','100']);wait(lambda:not probe()['keyboardMode'],'native Escape releases mode')
 command([LAB+'wtype','-s','500','-k','a','-s','100']);wait(lambda:app_metrics()['aKeys']==before+1,'cross-process key handoff without refocus')
 checks.append({'name':'cross-process-exclusive-keyboard-and-escape-handoff','passed':True})
 unique=sender.ready['unique'];stop(sender.p)
 wait(lambda:not has_owner(unique),'actual sender disconnect observed')
 require(probe()['toasts']==1,'original visible snapshot survives sender exit')
 second=Sender('sender-two');require(second.p.pid!=sender.p.pid,'new sender is distinct process')
 pointer.move(x,y);time.sleep(.2);pointer.click()
 ignored=second.event('ignored-action');require(ignored['id']==ident,'later sender rejects orphan callback ID')
 wait(lambda:probe()['toasts']==0,'orphan native card closes without original sender')
 second.send('status');require(second.event('status')['callbacks']==0,'orphan does not increment later sender callbacks')
 require(not any(e['event']=='action' for e in second.events),'orphan never attributed to new sender')
 checks.append({'name':'sender-exit-orphan-card-and-later-sender-id-filtering','passed':True})
 fresh=second.notify();require(fresh!=ident,'native ID not reused for later sender')
 wait(lambda:probe()['toasts']==1,'later sender card ready');time.sleep(.4);pointer.move(x,y);time.sleep(.2);pointer.click()
 action=second.event('action');closed=second.event('closed')
 require(action['id']==fresh and action['count']==1 and closed['id']==fresh,'later sender receives only its own callback')
 second.send('status');require(second.event('status')['callbacks']==1,'later sender exact own callback count')
 wait(lambda:probe()['toasts']==0,'later sender card cleanly closed')
 checks.append({'name':'later-persistent-sender-own-callback-after-orphan','passed':True})
 capture('cross-process-final')
 log=Path('/home/probe/shell.log').read_text();app_log=Path('/home/probe/application.log').read_text()
 diagnostics=[line for line in log.splitlines() if re.search(r'^\s*(WARN|ERROR|FATAL|CRITICAL)\b',line)]
 require(len(diagnostics)==1 and '$HYPRLAND_INSTANCE_SIGNATURE is unset. Cannot connect to hyprland.' in diagnostics[0],'only absent-Hyprland service warning')
 require(not re.search(r'^\s*(WARN|ERROR|FATAL|CRITICAL)\b',app_log,re.M),'no application diagnostics')
 require('llvmpipe' in log and 'llvmpipe' in app_log,'both independent native graphics contexts')
 require(not Path('/home/probe/forbidden-actions.log').exists(),'no activation sentinel triggered')
 require(all(p.poll() is None for p in (shell,application,second.p,compositor,bus)),'owned actors healthy before diagnostic cleanup')
 result={'status':'passed','checks':checks,'app_metrics':app_metrics(),'sender_events':sender_events,
  'processes':{'service':shell.pid,'application':application.pid,'first_sender':sender.p.pid,'second_sender':second.p.pid},
  'build_commands':build_commands,'qt_versions':versions.splitlines()}
except Exception as error:
 result={'status':'failed','checks':checks,'error':type(error).__name__+': '+str(error),'sender_events':sender_events}
finally:
 if pointer is not None:
  try:pointer.close()
  except Exception:result.update(status='failed',pointer_cleanup_failed=True)
 for p in reversed(children):stop(p)
 for f in files:f.close()
 result['children_reaped']=all(p.poll() is not None for p in children)
Path('/home/probe/native-process-results.json').write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(0 if result['status']=='passed' else 1)
'''


def run(root,lab_dir,candidate):
    lab=graphics.verify_lab(root,lab_dir);ownership.eligibility(root,candidate)
    _,runtime,_=variant.verify(root,candidate);files,_=preview.verified_sources(root);sealed=notification_frontend.sources(root)
    if any(files.get(name)!=data for name,data in sealed.items()):raise ValueError('Sealed notification closure differs')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    case=builder.private_directory(builder.private_directory(root/'work/native-process-probes')/stamp)
    for directory in ('probe','probe/helpers','probe/labwc','home','home/runtime','home/config','home/cache','home/data','home/state'):
        builder.private_directory(case/directory)
    for name,data in files.items():
        path=case/'probe'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    fixture={'shell.qml':SERVICE,'app.qml':APPLICATION,'driver.py':DRIVER,'bus.conf':ownership.BUS,'deny-exec':graphics.GUARD,
             'labwc/rc.xml':'<labwc_config/>\n','fonts.conf':'<fontconfig><dir>/usr/share/fonts</dir><cachedir>/home/probe/cache/fontconfig</cachedir></fontconfig>',
             'passwd':'probe:x:%d:%d:Private probe:/home/probe:/bin/false\n'%(os.getuid(),os.getgid()),'group':'probe:x:%d:\n'%os.getgid()}
    for name,data in fixture.items():(case/'probe'/name).write_text(data)
    for source,target in (('tools/notification_state.py','helpers/notification_state.py'),('tools/native_pointer_fixture.py','native_pointer_fixture.py'),('tests/fixtures/notification_sender.cpp','sender.cpp')):
        (case/'probe'/target).write_bytes((root/source).read_bytes())
    (case/'probe/deny-exec').chmod(0o555)
    inputs=builder.artifact_manifest(case/'probe');before_lab=graphics.package_manifest(lab/'root');before_runtime=builder.artifact_manifest(runtime)
    command=graphics.sandbox(runtime,case,lab,1)
    with (case/'output.log').open('x') as stream:
        try:code=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=85,check=False).returncode
        except subprocess.TimeoutExpired:code=None
    result_path=case/'home/native-process-results.json'
    report=json.loads(result_path.read_text()) if result_path.is_file() else {'status':'failed','error':'Missing bounded cross-process result'}
    unchanged=inputs==builder.artifact_manifest(case/'probe') and before_lab==graphics.package_manifest(lab/'root') and before_runtime==builder.artifact_manifest(runtime)
    report.update(returncode=code,inputs_unchanged=unchanged,command=command,
                  checker_sha256=builder.digest(Path(__file__)),sender_source_sha256=builder.digest(root/'tests/fixtures/notification_sender.cpp'),
                  pointer_sha256=builder.digest(root/'tools/native_pointer_fixture.py'),bootstrap_sha256=builder.digest(root/'tools/check_native_notifications.py'),
                  input_checker_sha256=builder.digest(root/'tools/check_native_input.py'),staged_driver_sha256=builder.digest(case/'probe/driver.py'),
                  runtime_sha256=builder.digest(runtime/'bin/quickshell'),notification_sources={name:hashlib.sha256(data).hexdigest() for name,data in sealed.items()},
                  limits='Owned synthetic processes on one private Labwc output only; no production app/Hyprland/multi-output/clipboard/locked privacy/security/crash/live migration acceptance.')
    if code!=0 or not unchanged or not report.get('children_reaped'):report['status']='failed'
    if (case/'home/sender').is_file():report['sender_binary_sha256']=builder.digest(case/'home/sender')
    report['captures']={p.name:builder.digest(p) for p in (case/'home').glob('*.ppm')}
    (case/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(case/'report.json')
    return 0 if report['status']=='passed' else 1


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true')
    p.add_argument('--lab-dir',type=Path);p.add_argument('--candidate',type=Path);args=p.parse_args(argv)
    if not args.run:print('Plan only: separate synthetic sender/application on private bus/compositor');return 0
    if args.lab_dir is None or args.candidate is None:p.error('--run requires --lab-dir and --candidate')
    os.umask(0o077)
    return run(ROOT,args.lab_dir,args.candidate)


if __name__=='__main__':raise SystemExit(main())
