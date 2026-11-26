#!/usr/bin/env python3
"""Explicit disposable device-free native graphics smoke test; never a desktop launch."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import build_runtime as builder
import build_notification_runtime as variant
import check_notification_runtime
import check_runtime

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {'labwc':'0.9.3-1', 'libwlroots-0.19':'0.19.2-1', 'libliftoff0':'0.5.0-1.1build1',
            'libsfdo0':'0.1.4-1', 'libxcb-ewmh2':'0.4.2-1build1', 'wayland-utils':'1.3.0-1',
            'grim':'1.4.0+ds-2build3', 'wlrctl':'0.2.2-2build1', 'wtype':'0.4-3build1'}
LAB = '/opt/native-test-lab'
QML = '''import QtQuick
import QtQuick.Effects
import Quickshell
import Quickshell.Wayland
ShellRoot {
 Variants {
  model: Quickshell.screens
  PanelWindow {
   required property var modelData
   screen:modelData
   anchors { top:true; left:true }
   implicitWidth:400; implicitHeight:180
   color:"#000000"
   exclusionMode:ExclusionMode.Ignore
   WlrLayershell.namespace:"omabuntu-private-graphics-smoke"
   WlrLayershell.layer:WlrLayer.Overlay
   Item {
    id:scene
    anchors.fill:parent
    Rectangle { id:redSource; width:80;height:80;color:"#ff0000";visible:false }
    MultiEffect { x:20;y:20;width:80;height:80;source:redSource;brightness:__TINT__;colorization:__TINT__;colorizationColor:"#00ff00" }
    Rectangle { x:120;y:20;width:80;height:80;color:"#ff0000" }
    Rectangle { id:blueSource;width:80;height:80;color:"#0000ff";visible:false }
    Rectangle { id:roundMask;width:80;height:80;color:"white";radius:24;visible:false;layer.enabled:true }
    MultiEffect { x:220;y:20;width:80;height:80;source:blueSource;maskEnabled:true;maskSource:roundMask }
    Timer { interval:700;running:true;onTriggered: {
     if(scene.GraphicsInfo.api!==GraphicsInfo.OpenGL){console.error("PRIVATE_WRONG_GRAPHICS_API");Qt.exit(31);return}
     console.log("PRIVATE_NATIVE_GRAPHICS_READY")
    } }
   }
  }
 }
 Timer { interval:10000;running:true;onTriggered:{console.error("PRIVATE_GRAPHICS_WATCHDOG");Qt.exit(98)} }
}
'''
GUARD = '''#!/usr/bin/python3
import os
from pathlib import Path
with Path('/home/probe/forbidden-actions.log').open('a') as stream:stream.write(os.path.basename(__file__)+'\\n')
raise SystemExit(125)
'''
DRIVER = r'''import json,os,re,resource,subprocess,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,resource.getrlimit(resource.RLIMIT_CORE)[1]))
count=int(os.environ['PRIVATE_OUTPUT_COUNT']);children=[];files=[];checks=[]
lab='/opt/native-test-lab/usr/bin/'
def require(value,message):
 if not value:raise AssertionError(message)
def stop(p):
 if p.poll() is None:
  p.terminate()
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)
def spawn(name,args,env=None):
 f=Path('/home/probe/'+name+'.log').open('w');files.append(f)
 p=subprocess.Popen(args,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT);children.append(p)
 return p
try:
 for forbidden in ('/run/user','/dev/dri','/dev/input','/sys','/etc/xdg','/var/run/dbus/system_bus_socket'):
  require(not Path(forbidden).exists(),'no host device/session/config path: '+forbidden)
 for key in ('HYPRLAND_INSTANCE_SIGNATURE','WAYLAND_DISPLAY','WAYLAND_SOCKET','DISPLAY'):
  require(key not in os.environ,'no inherited session environment: '+key)
 checks.append({'name':'namespace-no-host-session-or-devices','passed':True})
 for binary in ('labwc','grim','wayland-info','wlrctl','wtype'):
  r=subprocess.run(['ldd',lab+binary],capture_output=True,text=True,timeout=5)
  Path('/home/probe/linkage-'+binary+'.log').write_text(r.stdout+r.stderr)
  require(r.returncode==0 and 'not found' not in r.stdout+r.stderr,'contained dynamic linkage: '+binary)
  if binary=='labwc':
   for library in ('libwlroots-0.19.so','libliftoff.so.0','libsfdo-icon.so.0','libxcb-ewmh.so.2'):
    require('/opt/native-test-lab/usr/lib/x86_64-linux-gnu/'+library in r.stdout,'exact private lab library: '+library)
 checks.append({'name':'contained-linkage','passed':True})
 compositor=spawn('compositor',[lab+'labwc','-d','-C','/probe/labwc'])
 deadline=time.monotonic()+6;socket=None
 while time.monotonic()<deadline and compositor.poll() is None:
  sockets=[p for p in Path('/home/probe/runtime').glob('wayland-*') if p.is_socket()]
  if len(sockets)==1:socket=sockets[0];break
  time.sleep(.05)
 require(socket is not None,'private compositor socket readiness')
 compositor_text=Path('/home/probe/compositor.log').read_text()
 for marker in ('Starting headless backend','Creating pixman renderer','Created shm allocator'):
  require(marker in compositor_text,'actual compositor renderer/allocator: '+marker)
 checks.append({'name':'headless-pixman-shm-renderer','passed':True})
 env=dict(os.environ,WAYLAND_DISPLAY=socket.name)
 r=subprocess.run([lab+'wayland-info'],env=env,capture_output=True,text=True,timeout=5)
 Path('/home/probe/protocols.log').write_text(r.stdout+r.stderr)
 require(r.returncode==0,'private protocol query')
 for protocol in ('zwlr_layer_shell_v1','zwlr_screencopy_manager_v1','zwlr_virtual_pointer_manager_v1','zwp_virtual_keyboard_manager_v1','wl_shm'):
  require(protocol in r.stdout,'required global: '+protocol)
 outputs=sorted(set(re.findall(r"name:\s*['\"]?(HEADLESS-\d+)",r.stdout)))
 require(len(outputs)==count,'actual advertised headless output count')
 checks.append({'name':'headless-protocols-and-outputs','passed':True,'outputs':outputs})
 for mode in ('positive','negative'):
  p=spawn(mode,['/opt/omabuntu-runtime/bin/quickshell','--no-color','--no-detailed-logs','--path','/probe/'+mode+'.qml'],env)
  path=Path('/home/probe/'+mode+'.log');deadline=time.monotonic()+6
  while time.monotonic()<deadline and p.poll() is None:
   if path.read_text().count('PRIVATE_NATIVE_GRAPHICS_READY')>=count:break
   time.sleep(.05)
  text=path.read_text()
  require(p.poll() is None and text.count('PRIVATE_NATIVE_GRAPHICS_READY')==count,'native PanelWindow and OpenGL readiness')
  require(re.search(r'(?:GL_RENDERER|OpenGL renderer|renderer:).*llvmpipe',text,re.I),'actual llvmpipe renderer evidence')
  require(not any(s in text for s in ('PRIVATE_WRONG','PRIVATE_GRAPHICS_WATCHDOG','Failed to load configuration','TypeError:','ReferenceError:','Cannot assign','Unable to assign')),'no QML/API failure')
  for output in outputs:
   target='/home/probe/'+mode+'-'+output+'.ppm'
   r=subprocess.run([lab+'grim','-t','ppm','-o',output,target],env=env,capture_output=True,text=True,timeout=5)
   require(r.returncode==0,'native compositor output capture')
  checks.append({'name':mode+'-native-shader-capture','passed':True})
  stop(p)
 stop(compositor)
 require(not Path('/home/probe/forbidden-actions.log').exists(),'no Xwayland/service activation command executed')
 result={'status':'captured','checks':checks,'outputs':outputs}
except Exception as e:
 result={'status':'failed','checks':checks,'error':type(e).__name__+': '+str(e)}
finally:
 for p in reversed(children):stop(p)
 for f in files:f.close()
 result['children_reaped']=all(p.poll() is not None for p in children)
Path('/home/probe/graphics-results.json').write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(0 if result['status']=='captured' else 1)
'''


def package_manifest(root):
    result=[]
    for path in sorted(root.rglob('*')):
        name=str(path.relative_to(root))
        if path.is_symlink():
            if not path.resolve().is_relative_to(root.resolve()):raise ValueError('Escaping lab symlink')
            result.append({'path':name,'link':os.readlink(path)})
        elif path.is_file():
            if path.stat().st_nlink!=1 or path.stat().st_mode&0o6000:raise ValueError('Unsafe lab file')
            result.append({'path':name,'sha256':builder.digest(path),'mode':path.stat().st_mode&0o777})
        elif not path.is_dir():raise ValueError('Special lab file')
    return result


def lab_input(lab, relative, limit=2_000_000):
    path=lab/relative
    if (any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file()
            or path.stat().st_size>limit or path.stat().st_nlink!=1):
        raise ValueError('Require bounded regular lab input')
    return path


def verify_lab(root, candidate):
    lab=Path(candidate).absolute()
    if (any(p.is_symlink() for p in (lab,*lab.parents))
            or not lab.resolve().is_relative_to((root/'work').resolve())):
        raise ValueError('Require real lab directory under private work')
    records=json.loads(lab_input(lab,'packages.json').read_text())
    if set(records)!=set(PACKAGES):raise ValueError('Require the nine approved packages only')
    for name,version in PACKAGES.items():
        record=records[name]
        if record.get('version')!=version or not re.fullmatch(r'[a-f0-9]{64}',record.get('sha256','')):
            raise ValueError('Approved package pin differs')
        if builder.digest(lab_input(lab,'downloads/'+name+'.deb',limit=5_000_000))!=record['sha256']:
            raise ValueError('Downloaded package changed')
        notice=lab_input(lab,'root/usr/share/doc/'+name+'/copyright')
        if builder.digest(notice)!=record.get('copyright_sha256'):raise ValueError('Lab package notice changed')
    expected=json.loads(lab_input(lab,'root-manifest.json').read_text())
    if (lab/'root').is_symlink() or package_manifest(lab/'root')!=expected:
        raise ValueError('Extracted lab input changed')
    return lab


def sandbox(runtime, case, lab, count):
    args=check_runtime.sandbox_command(runtime,case,['/usr/bin/python3','-B','/probe/driver.py'])
    # Replace the offscreen defaults, never inherit any live-session value.
    env={'QT_QPA_PLATFORM':'wayland','QT_QUICK_BACKEND':None,'QML_IMPORT_TRACE':'0',
         'QSG_RHI_BACKEND':'opengl','QSG_INFO':'1','QSG_RENDER_LOOP':'basic',
         'QT_WAYLAND_CLIENT_BUFFER_INTEGRATION':'wayland-egl','LIBGL_ALWAYS_SOFTWARE':'1',
         'GALLIUM_DRIVER':'llvmpipe','WLR_BACKENDS':'headless','WLR_RENDERER':'pixman',
         'WLR_HEADLESS_OUTPUTS':str(count),'LABWC_UPDATE_ACTIVATION_ENV':'0',
         'WLR_XWAYLAND':'/usr/bin/Xwayland','XDG_DATA_DIRS':'/nonexistent/data',
         'PATH':LAB+'/usr/bin:/usr/bin:/bin','LD_LIBRARY_PATH':LAB+'/usr/lib/x86_64-linux-gnu',
         'PRIVATE_OUTPUT_COUNT':str(count)}
    for key,value in env.items():
        while '--setenv' in args:
            found=next((i for i in range(len(args)-2) if args[i]=='--setenv' and args[i+1]==key),None)
            if found is None:break
            del args[found:found+3]
        index=args.index('--chdir')
        args[index:index]=['--unsetenv',key] if value is None else ['--setenv',key,value]
    index=args.index('--chdir')
    mounts=['--ro-bind',str(lab/'root'),LAB,
            '--ro-bind',str(case/'probe/passwd'),'/etc/passwd',
            '--ro-bind',str(case/'probe/group'),'/etc/group']
    for binary in ('Xwayland','systemctl','dbus-update-activation-environment'):
        if not Path('/usr/bin',binary).is_file():raise ValueError('Required private guard target missing')
        mounts+=['--ro-bind',str(case/'probe/deny-exec'),'/usr/bin/'+binary]
    args[index:index]=mounts
    return args


def inspect_ppm(path, tinted):
    with path.open('rb') as stream:data=stream.read(16_000_001)
    if len(data)>16_000_000:raise ValueError('Screenshot bound exceeded')
    match=re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\n',data)
    if not match:raise ValueError('Expected native P6 screenshot')
    width,height=map(int,match.groups());raw=data[match.end():]
    if not 400<=width<=2560 or not 180<=height<=1440 or len(raw)!=width*height*3:
        raise ValueError('Screenshot dimensions/data differ')
    samples={}
    for name,x,y,expected in (('shader',50,50,(0,255,0) if tinted else (255,0,0)),
                              ('raw-control',150,50,(255,0,0)),('mask-center',260,60,(0,0,255)),
                              ('mask-corner',221,21,(0,0,0)),('background',5,5,(0,0,0))):
        value=tuple(raw[(y*width+x)*3:(y*width+x)*3+3]);samples[name]=value
        if any(abs(a-b)>3 for a,b in zip(value,expected)):raise ValueError('Native shader pixel control failed: '+name)
    return {'width':width,'height':height,'sha256':hashlib.sha256(data).hexdigest(),'samples':samples}


def run(root, lab_dir, candidate):
    lab=verify_lab(root,lab_dir)
    check_notification_runtime.eligibility(root,candidate)
    _,runtime,_=variant.verify(root,candidate)
    before=package_manifest(lab/'root');runtime_before=builder.artifact_manifest(runtime)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output=builder.private_directory(builder.private_directory(root/'work/native-graphics-probes')/stamp)
    report={'status':'running','checker_sha256':builder.digest(Path(__file__)),'cases':[],
            'package_manifest_sha256':builder.digest(lab/'root-manifest.json'),
            'runtime_sha256':builder.digest(runtime/'bin/quickshell'),
            'limits':'Disposable native graphics controls only; no original notification, Hyprland policy, input, live deployment, security or crash acceptance.'}
    for count in (1,2):
        case=builder.private_directory(output/str(count))
        for folder in ('probe','probe/labwc','home','home/runtime','home/config','home/cache','home/data','home/state'):
            builder.private_directory(case/folder)
        files={'positive.qml':QML.replace('__TINT__','1.0'),'negative.qml':QML.replace('__TINT__','0.0'),
               'driver.py':DRIVER,'deny-exec':GUARD,'labwc/rc.xml':'<labwc_config/>\n',
               'fonts.conf':'<fontconfig><dir>/usr/share/fonts</dir><cachedir>/home/probe/cache/fontconfig</cachedir></fontconfig>',
               'passwd':'probe:x:%d:%d:Private probe:/home/probe:/bin/false\n'%(os.getuid(),os.getgid()),
               'group':'probe:x:%d:\n'%os.getgid()}
        for name,data in files.items():(case/'probe'/name).write_text(data)
        (case/'probe/deny-exec').chmod(0o555)
        inputs=builder.artifact_manifest(case/'probe');command=sandbox(runtime,case,lab,count)
        with (case/'output.log').open('x') as stream:
            try:code=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=50,check=False).returncode
            except subprocess.TimeoutExpired:code=None
        path=case/'home/graphics-results.json'
        result=json.loads(path.read_text()) if path.is_file() else {'status':'failed','error':'No bounded private driver result'}
        result.update(output_count=count,returncode=code,command=command,
                      probe_inputs=inputs,inputs_unchanged=inputs==builder.artifact_manifest(case/'probe'))
        try:
            if code!=0 or result['status']!='captured' or not result['inputs_unchanged'] or not result.get('children_reaped'):
                raise ValueError(result.get('error','Native graphics driver failed'))
            result['images']={p.name:inspect_ppm(p,p.name.startswith('positive-')) for p in sorted((case/'home').glob('*.ppm'))}
            if len(result['images'])!=2*count:raise ValueError('Native image control count differs')
            result['status']='passed'
        except (ValueError,OSError) as error:result.update(status='failed',error=str(error))
        report['cases'].append(result)
        if result['status']!='passed':break
    report['inputs_unchanged']=before==package_manifest(lab/'root') and runtime_before==builder.artifact_manifest(runtime)
    report['status']='native-graphics-smoke-passed' if len(report['cases'])==2 and all(c['status']=='passed' for c in report['cases']) and report['inputs_unchanged'] else 'failed'
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(output/'report.json')
    return 0 if report['status']=='native-graphics-smoke-passed' else 1


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true')
    p.add_argument('--lab-dir',type=Path);p.add_argument('--candidate',type=Path);args=p.parse_args(argv)
    if not args.run:print('Plan only: explicit private package lab and verified runtime required; no host session');return 0
    if args.lab_dir is None or args.candidate is None:p.error('--run requires --lab-dir and --candidate')
    os.umask(0o077)
    return run(ROOT,args.lab_dir,args.candidate)


if __name__=='__main__':raise SystemExit(main())
