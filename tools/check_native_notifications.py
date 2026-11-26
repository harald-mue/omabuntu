#!/usr/bin/env python3
"""Original sealed notification service on disposable native outputs/private buses only."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import zlib

import build_runtime as builder
import build_notification_runtime as variant
import check_notification_runtime as ownership
import check_clock_preview as preview
import check_native_graphics as graphics
import notification_frontend
import notification_state

ROOT=Path(__file__).resolve().parents[1]
QML='''import QtQuick
import Quickshell
import Quickshell.Io
import "Notifications" as Notifications
import qs.Commons as Commons
ShellRoot {
 QtObject { id:context
  property QtObject bar:QtObject {
   property string position:"top"
   property int barSize:26
   property bool barHidden:false
   function barSizeFor(name){return 26}
  }
 }
 Notifications.Service { id:service;shell:context;storageHelper:"/probe/helpers/notification_state.py" }
 IpcHandler {
  target:"nativeNotificationFixture"
  // Private runtime palette only, for a discriminating original shader control.
  function symbolicPalette(enabled:bool):string {
   Commons.Color.foreground=enabled?"#00ff00":"#cacccc"
   return String(Commons.Color.foreground)
  }
  function metrics():string {
   return JSON.stringify({ready:service.storeReady&&service.quietLoaded,textColor:String(Commons.Color.notifications.text),
    rows:service.layout.decks.reduce(function(rows,d){return rows.concat(d.rows.map(function(r){return {key:r.key,id:r.originalId,duration:r.duration,image:!!r.image}}))},[]),
    decks:service.layout.decks.map(function(d){return d.rows.length}),
    heights:Object.keys(service.heights).map(function(k){return service.heights[k]})})
  }
 }
 Timer {interval:35000;running:true;onTriggered:{console.error("PRIVATE_NATIVE_NOTIFICATIONS_WATCHDOG");Qt.exit(98)}}
}
'''
BUS=ownership.BUS
DRIVER=r'''import ast,json,os,re,resource,subprocess,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,resource.getrlimit(resource.RLIMIT_CORE)[1]))
count=int(os.environ['PRIVATE_OUTPUT_COUNT']);children=[];files=[];checks=[]
QS='/opt/omabuntu-runtime/bin/quickshell';LAB='/opt/native-test-lab/usr/bin/'
NAME='org.freedesktop.Notifications';ADDRESS='unix:path=/home/probe/runtime/private-bus'
env=dict(os.environ);outputs=[]
def require(ok,message):
 if not ok:raise AssertionError(message)
def spawn(name,args,environment=None):
 f=Path('/home/probe/'+name+'.log').open('w');files.append(f)
 p=subprocess.Popen(args,env=environment,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT);children.append(p);return p
def stop(p):
 if p.poll() is None:
  p.terminate()
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)
def command(args,timeout=3):
 r=subprocess.run(args,env=env,capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError(r.stderr.strip()[:1000] or 'private command failed')
 return r.stdout.strip()
def dbus(method,*args,dest='org.freedesktop.DBus',path='/org/freedesktop/DBus'):
 text=command(['gdbus','call','--session','--dest',dest,'--object-path',path,'--method',method,*args])
 return ast.literal_eval(re.sub(r'\buint32\s+','',text))[0]
def owner():
 try:return dbus('org.freedesktop.DBus.GetNameOwner',NAME)
 except RuntimeError as e:
  if 'NameHasNoOwner' in str(e):return None
  raise
def wait(test,label,timeout=5):
 end=time.monotonic()+timeout;last=None
 while time.monotonic()<end:
  try:
   value=test()
   if value:return value
  except (RuntimeError,json.JSONDecodeError) as e:last=type(e).__name__
  time.sleep(.05)
 raise AssertionError(label+(' ('+last+')' if last else ''))
def ipc(method,*args,target='omabuntuNotifications'):
 return command([QS,'ipc','--path','/probe/shell.qml','call',target,method,*args])
def probe():return json.loads(ipc('probe'))
def metrics():return json.loads(ipc('metrics',target='nativeNotificationFixture'))
def notify(title,ident=0,photo=False,actions=False,low=False,icon=''):
 hints="{'urgency': <byte 0>}" if low else ("{'image-path': <'/probe/photo.png'>}" if photo else '{}')
 return dbus('org.freedesktop.Notifications.Notify','Fixture',str(ident),icon,title,'Synthetic notification body',
             "['default', 'Open fixture']" if actions else '[]',hints,'1' if low else '30000',dest=NAME,path='/org/freedesktop/Notifications')
def capture(name):
 time.sleep(.4)
 for output in outputs:command([LAB+'grim','-t','ppm','-o',output,'/home/probe/'+name+'-'+output+'.ppm'])
def clear():
 ipc('dismissAll');wait(lambda:probe()['toasts']==0,'original deferred clear')
 time.sleep(.3)
try:
 for path in ('/run/user','/dev/dri','/dev/input','/sys','/etc/xdg','/var/run/dbus/system_bus_socket'):
  require(not Path(path).exists(),'no host path: '+path)
 require(not any(k in env for k in ('HYPRLAND_INSTANCE_SIGNATURE','WAYLAND_DISPLAY','WAYLAND_SOCKET','DISPLAY')),'no inherited session identity')
 bus=spawn('bus',['dbus-daemon','--nofork','--nopidfile','--config-file=/probe/bus.conf'])
 wait(lambda:Path('/home/probe/runtime/private-bus').is_socket(),'private bus ready')
 env['DBUS_SESSION_BUS_ADDRESS']=ADDRESS
 dbus('org.freedesktop.DBus.GetId')
 compositor=spawn('compositor',[LAB+'labwc','-d','-C','/probe/labwc'],env)
 def socket():
  sockets=[p for p in Path('/home/probe/runtime').glob('wayland-*') if p.is_socket()]
  return sockets[0] if len(sockets)==1 else None
 display=wait(socket,'private compositor ready');env['WAYLAND_DISPLAY']=display.name
 protocols=command([LAB+'wayland-info']);Path('/home/probe/protocols.log').write_text(protocols)
 outputs=sorted(set(re.findall(r"name:\s*['\"]?(HEADLESS-\d+)",protocols)))
 require(len(outputs)==count,'real output count')
 for name in ('zwlr_layer_shell_v1','zwlr_screencopy_manager_v1','zwp_virtual_keyboard_manager_v1','wl_shm'):
  require(name in protocols,'required native protocol: '+name)
 shell=spawn('shell',[QS,'--no-color','--no-detailed-logs','--path','/probe/shell.qml'],env)
 wait(lambda:owner() is not None,'actual native notification server ownership')
 unique=owner();require(dbus('org.freedesktop.DBus.GetConnectionUnixProcessID',unique)==shell.pid,'bus owned by fixture shell')
 wait(lambda:metrics()['ready'],'private original store readiness')
 p=probe();require(p['toasts']==0 and len(p['surfaces'])==count,'original native surfaces exist')
 require(all(s['mapped'] for s in p['surfaces']),'original idle surfaces mapped')
 require(not p['doNotDisturb'],'fresh private DND state')
 checks.append({'name':'actual-original-server-state-and-surfaces','passed':True,'outputs':outputs})
 capture('empty')
 ident=notify('Photo fixture',photo=True)
 wait(lambda:probe()['toasts']==1 and metrics()['rows'][0]['image'],'original native photo delivery')
 wait(lambda:any(h>0 for h in metrics()['heights']),'actual original Toast measures')
 capture('photo')
 require(len(probe()['notificationDisplays'])==1,'original deck output pinning')
 require(len(metrics()['decks'])==1,'original source deck')
 checks.append({'name':'native-original-card-photo-and-output-pin','passed':True})
 same=notify('Updated fixture',ident=ident,photo=True)
 wait(lambda:probe()['toasts']==1,'native replacement does not duplicate')
 require(same==ident and metrics()['rows'][0]['id']==ident,'original replacement identity')
 notify('Grouped fixture')
 wait(lambda:probe()['toasts']==2 and metrics()['decks']==[2],'original native grouped deck')
 capture('grouped')
 checks.append({'name':'replacement-and-source-grouping','passed':True})
 clear()
 require(ipc('symbolicPalette','true',target='nativeNotificationFixture')=='#00ff00','private shader-control palette')
 notify('Symbolic fixture',icon='fixture-symbolic')
 wait(lambda:probe()['toasts']==1,'symbolic native card ready');capture('symbolic')
 clear();notify('Color fixture',icon='fixture-color')
 wait(lambda:probe()['toasts']==1,'raw native icon card ready');capture('raw-icon')
 checks.append({'name':'original-symbolic-and-raw-icon-frames','passed':True,'text_color':metrics()['textColor']})
 clear();require(ipc('symbolicPalette','false',target='nativeNotificationFixture')=='#cacccc','restore private fixture palette')
 # This setter addresses only the actual original service in this namespace;
 # the legacy DND backend and host provider are never instantiated.
 require(ipc('setDnd','on')=='on','private DND on')
 notify('Quiet fixture');time.sleep(.2);require(probe()['toasts']==0,'private DND suppresses card')
 require(ipc('setDnd','off')=='off','private DND off')
 checks.append({'name':'private-original-dnd','passed':True})
 notify('Keyboard fixture')
 wait(lambda:probe()['toasts']==1,'keyboard card ready')
 require(ipc('keyboard')=='on','original keyboard mode admitted')
 time.sleep(.3);command([LAB+'wtype','-s','500','-k','Escape','-s','100'])
 wait(lambda:probe()['keyboardMode'] is False,'native Escape releases original keyboard mode')
 checks.append({'name':'native-keyboard-escape','passed':True})
 clear()
 receiver=spawn('signals',['gdbus','monitor','--session','--dest',unique,'--object-path','/org/freedesktop/Notifications'],env)
 wait(lambda:'Monitoring signals' in Path('/home/probe/signals.log').read_text(),'private signal observer ready')
 action_id=notify('Action fixture',actions=True)
 wait(lambda:probe()['toasts']==1,'native action card ready')
 require(ipc('keyboard')=='on','keyboard action mode admitted')
 time.sleep(.3);command([LAB+'wtype','-s','500','-k','Return','-s','100'])
 wait(lambda:'ActionInvoked' in Path('/home/probe/signals.log').read_text(),'native Return invokes real sender action signal')
 text=Path('/home/probe/signals.log').read_text()
 require(text.count('ActionInvoked')==1 and str(action_id) in text and "'default'" in text,'single matching native ActionInvoked')
 require(probe()['keyboardMode'] is False,'native action releases keyboard mode')
 checks.append({'name':'native-return-standard-action-signal','passed':True})
 clear();notify('Expiry fixture',low=True)
 wait(lambda:probe()['toasts']==1,'low urgency arrival')
 require(metrics()['rows'][0]['duration']==5000,'original minimum low lifetime')
 wait(lambda:probe()['toasts']==0,'actual original native card expiry',timeout=7)
 time.sleep(.5) # Let the original queued FileView persistence settle.
 checks.append({'name':'native-original-expiry','passed':True})
 log=Path('/home/probe/shell.log').read_text()
 require('llvmpipe' in log,'actual llvmpipe context')
 expected='$HYPRLAND_INSTANCE_SIGNATURE is unset. Cannot connect to hyprland.'
 diagnostics=[line for line in log.splitlines() if re.search(r'^\s*(WARN|ERROR|FATAL|CRITICAL)\b',line)]
 require(len(diagnostics)==1 and expected in diagnostics[0],'only explicit absent-Hyprland warning expected')
 require(not any(x in log for x in ('TypeError:','ReferenceError:','Binding loop','Cannot assign','Unable to assign','PRIVATE_NATIVE_NOTIFICATIONS_WATCHDOG')),'no hidden QML failure')
 stop(receiver);stop(shell)
 wait(lambda:owner() is None,'original shell releases notification ownership')
 stop(compositor);stop(bus)
 require(not Path('/home/probe/forbidden-actions.log').exists(),'no private activation/Xwayland guard triggered')
 result={'status':'native-original-captured','checks':checks,'outputs':outputs,'expected_absent_hyprland_warning':True}
except Exception as error:result={'status':'failed','checks':checks,'error':type(error).__name__+': '+str(error)}
finally:
 for p in reversed(children):stop(p)
 for f in files:f.close()
 result['children_reaped']=all(p.poll() is not None for p in children)
Path('/home/probe/native-results.json').write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(0 if result['status']=='native-original-captured' else 1)
'''


def fixture_photo():
    def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
    # Fixed synthetic magenta image; no imported image, network or user content.
    raw=(b'\0'+bytes((255,0,255))*64)*64
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',64,64,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')


def ppm(path):
    with path.open('rb') as stream:data=stream.read(16_000_001)
    match=re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\n',data)
    if len(data)>16_000_000 or not match:raise ValueError('Invalid native screenshot')
    width,height=map(int,match.groups());raw=data[match.end():]
    if not 800<=width<=2560 or not 400<=height<=1440 or len(raw)!=width*height*3:raise ValueError('Native screenshot extent differs')
    return width,height,raw


def images(case,outputs,text_color):
    result={};painted=[]
    if text_color!='#00ff00':raise ValueError('Distinct private symbolic control palette required')
    for output in outputs:
        before=ppm(case/'home'/('empty-'+output+'.ppm'))
        for name in ('photo','grouped','symbolic','raw-icon'):
            path=case/'home'/(name+'-'+output+'.ppm');width,height,raw=ppm(path)
            if before[:2]!=(width,height):raise ValueError('Output changed during capture')
            changed=0;photo=0
            for index in range(0,len(raw),3):
                pixel=raw[index:index+3]
                if pixel!=before[2][index:index+3]:
                    x=(index//3)%width;y=(index//3)//width
                    if x<width-500 or y>500:raise ValueError('Unexpected painting outside original notification deck')
                    changed+=1
                if pixel==bytes((255,0,255)):photo+=1
            result[path.name]={'sha256':builder.digest(path),'changed_pixels':changed,'synthetic_photo_pixels':photo}
            if name=='photo' and changed>1000 and photo>400:
                painted.append(output)
                coords=[(i//3%width,i//3//width) for i in range(0,len(raw),3) if raw[i:i+3]==bytes((255,0,255))]
                x0=min(p[0] for p in coords);x1=max(p[0] for p in coords)
                y0=min(p[1] for p in coords);y1=max(p[1] for p in coords)
                def pixel(data,x,y):return tuple(data[(y*width+x)*3:(y*width+x)*3+3])
                if not (20<=x1-x0+1<=80 and 20<=y1-y0+1<=80):raise ValueError('Original photo extent differs')
                corners=[pixel(raw,x,y) for x,y in ((x0,y0),(x1,y0),(x0,y1),(x1,y1))]
                if any(p==(255,0,255) for p in corners):raise ValueError('Original photo mask corners are not rounded')
                center=((x0+x1)//2,(y0+y1)//2)
                _,_,mono=ppm(case/'home'/('symbolic-'+output+'.ppm'))
                _,_,color=ppm(case/'home'/('raw-icon-'+output+'.ppm'))
                actual=pixel(mono,*center)
                green=lambda p:p[1]>180 and p[0]<10 and p[2]<10
                tinted=sum(green(pixel(mono,x,y)) for y in range(y0,y1+1) for x in range(x0,x1+1))
                if not green(actual) or tinted<.9*(x1-x0+1)*(y1-y0+1) or pixel(color,*center)!=(255,0,0):
                    raise ValueError('Original symbolic tint/raw icon controls differ')
                result[path.name]['original_effects']={'rounded_photo_corners':corners,'symbolic_center':actual,'symbolic_green_pixels':tinted,'raw_center':pixel(color,*center)}
    if len(painted)!=1:raise ValueError('Original photo/card must paint on exactly one output')
    return result


def validate_private_state(case):
    """Read only: do not prepare/reset missing files and mask persistence failures."""
    home=case/'home/.local/state/omabuntu';directory=home/'notifications'
    notification_state.owned(home,True);notification_state.owned(directory,True)
    values={}
    for name in notification_state.DEFAULTS:
        path=directory/name;notification_state.owned(path)
        values[name]=json.loads(path.read_bytes())
    if values['quiet.json']!={'dnd':False} or values['live.json']!=[]:
        raise ValueError('Private original final quiet/live state differs')
    history=values['history.json']
    if (not isinstance(history,list) or not 4<=len(history)<=100
            or any(not notification_state.valid_row(row,True) or row['app']!='Fixture' for row in history)
            or not any(row['closed_reason']=='silenced' for row in history)
            or not any(row['closed_reason']=='expired' for row in history)):
        raise ValueError('Private original history/persistence differs')
    return {'history_rows':len(history),'live_empty':True,'quiet_off':True}


def run(root,lab_dir,candidate):
    lab=graphics.verify_lab(root,lab_dir);ownership.eligibility(root,candidate)
    _,runtime,_=variant.verify(root,candidate)
    files,_=preview.verified_sources(root);sealed=notification_frontend.sources(root)
    for name,data in sealed.items():
        if files.get(name)!=data:raise ValueError('Native test requires unchanged sealed notification closure')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output=builder.private_directory(builder.private_directory(root/'work/native-notification-probes')/stamp)
    before_lab=graphics.package_manifest(lab/'root');before_runtime=builder.artifact_manifest(runtime)
    report={'status':'running','checker_sha256':builder.digest(Path(__file__)),'cases':[],
            'notification_profile_sha256':builder.digest(root/'upstream/notifications.json'),
            'notification_sources':{name:hashlib.sha256(data).hexdigest() for name,data in sealed.items()},
            'runtime_sha256':builder.digest(runtime/'bin/quickshell'),
            'limits':'Original native service/cards on private fixture bus. No live host, Hyprland policy, pointer/hover/click-through, clipboard, locked-session, pixel identity, security or crash acceptance.'}
    for count in (1,2):
        case=builder.private_directory(output/str(count))
        for directory in ('probe','probe/helpers','probe/labwc','home','home/runtime','home/config','home/cache','home/data','home/state'):
            builder.private_directory(case/directory)
        for name,data in files.items():
            path=case/'probe'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        fixture={'shell.qml':QML,'driver.py':DRIVER,'bus.conf':BUS,'deny-exec':graphics.GUARD,
                 'labwc/rc.xml':'<labwc_config/>\n','fonts.conf':'<fontconfig><dir>/usr/share/fonts</dir><cachedir>/home/probe/cache/fontconfig</cachedir></fontconfig>',
                 'passwd':'probe:x:%d:%d:Private probe:/home/probe:/bin/false\n'%(os.getuid(),os.getgid()),
                 'group':'probe:x:%d:\n'%os.getgid()}
        for name,data in fixture.items():(case/'probe'/name).write_text(data)
        (case/'probe/helpers/notification_state.py').write_bytes((root/'tools/notification_state.py').read_bytes())
        (case/'probe/photo.png').write_bytes(fixture_photo());(case/'probe/deny-exec').chmod(0o555)
        for directory in ('home/data/icons','home/data/icons/hicolor','home/data/icons/hicolor/scalable','home/data/icons/hicolor/scalable/status'):
            builder.private_directory(case/directory)
        icons=case/'home/data/icons/hicolor';icon_dir=icons/'scalable/status'
        (icons/'index.theme').write_text('[Icon Theme]\nName=Private fixture\nDirectories=scalable/status\n\n[scalable/status]\nSize=40\nType=Scalable\nMinSize=1\nMaxSize=512\nContext=Status\n')
        for name in ('fixture-symbolic.svg','fixture-color.svg'):
            (icon_dir/name).write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><path fill="#ff0000" d="M0 0h40v40H0z"/></svg>\n')
        icon_inputs=builder.artifact_manifest(icons)
        inputs=builder.artifact_manifest(case/'probe')
        command=graphics.sandbox(runtime,case,lab,count)
        # graphics.sandbox's driver path is identical; it retains the reviewed
        # namespace, graphics settings and execution guards without host sockets.
        with (case/'output.log').open('x') as stream:
            try:code=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=65,check=False).returncode
            except subprocess.TimeoutExpired:code=None
        path=case/'home/native-results.json'
        result=json.loads(path.read_text()) if path.is_file() else {'status':'failed','error':'Missing bounded native result'}
        result.update(output_count=count,returncode=code,command=command,inputs_unchanged=inputs==builder.artifact_manifest(case/'probe') and icon_inputs==builder.artifact_manifest(icons))
        try:
            if code!=0 or result['status']!='native-original-captured' or not result['inputs_unchanged'] or not result.get('children_reaped'):
                raise ValueError(result.get('error','Native fixture failed'))
            text_color=next(check['text_color'] for check in result['checks'] if 'text_color' in check)
            result['images']=images(case,result['outputs'],text_color)
            result['private_state']=validate_private_state(case)
            result['private_state_valid']=True;result['status']='passed'
        except (OSError,ValueError) as error:result.update(status='failed',error=str(error))
        report['cases'].append(result)
        if result['status']!='passed':break
    report['inputs_unchanged']=before_lab==graphics.package_manifest(lab/'root') and before_runtime==builder.artifact_manifest(runtime)
    report['status']='native-original-notifications-passed' if len(report['cases'])==2 and all(c['status']=='passed' for c in report['cases']) and report['inputs_unchanged'] else 'failed'
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(output/'report.json')
    return 0 if report['status']=='native-original-notifications-passed' else 1


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true')
    p.add_argument('--lab-dir',type=Path);p.add_argument('--candidate',type=Path);args=p.parse_args(argv)
    if not args.run:print('Plan only: original native notifications on disposable private bus, never host session');return 0
    if args.lab_dir is None or args.candidate is None:p.error('--run requires --lab-dir and --candidate')
    os.umask(0o077)
    return run(ROOT,args.lab_dir,args.candidate)


if __name__=='__main__':raise SystemExit(main())
