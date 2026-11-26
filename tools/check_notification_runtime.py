#!/usr/bin/env python3
"""Test the actual exclusive server on isolated private buses; never deploy."""
import argparse
import datetime
import json
import os
import shutil
from pathlib import Path
import subprocess

import build_runtime as builder
import build_notification_runtime as variant
import check_runtime

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ('free-name-and-native-notify', 'refuse-replacement', 'conflict-no-queue-no-late-takeover',
          'negative-control-original-late-takeover', 'missing-bus-fails-closed', 'bus-loss-fails-closed')
QML = '''//@ pragma IgnoreSystemSettings
import QtQml
import Quickshell
import Quickshell.Services.Notifications
ShellRoot {
 property bool quitAfterNotice: __QUIT__
 Timer { id: quitSoon; interval:100; onTriggered: Qt.quit() }
 Timer { interval:12000; running:true; onTriggered:{console.error("PRIVATE_PROBE_WATCHDOG");Qt.exit(98)} }
 NotificationServer {
  keepOnReload:false
  actionsSupported:true
  onNotification:function(n){n.tracked=true;console.log("PRIVATE_NATIVE_NOTIFY_RECEIVED");if(quitAfterNotice)quitSoon.start()}
 }
}
'''
BUS = '''<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig><type>session</type><listen>unix:path=/home/probe/runtime/private-bus</listen>
<auth>EXTERNAL</auth><policy context="default"><allow user="*"/><allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/></policy>
<limit name="max_completed_connections">32</limit></busconfig>
'''
DRIVER = r'''import ast,json,os,re,resource,signal,subprocess,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,resource.getrlimit(resource.RLIMIT_CORE)[1]))
NAME='org.freedesktop.Notifications'
ADDRESS='unix:path=/home/probe/runtime/private-bus'
BASE='/baseline/bin/quickshell'; CANDIDATE='/opt/omabuntu-runtime/bin/quickshell'
results=[];children=[];files=[];bus=None;number=0

def require(value,message):
 if not value:raise AssertionError(message)

def call(method,*args,dest='org.freedesktop.DBus',path='/org/freedesktop/DBus'):
 env=dict(os.environ,DBUS_SESSION_BUS_ADDRESS=ADDRESS)
 r=subprocess.run(['gdbus','call','--session','--dest',dest,'--object-path',path,'--method',method,*args],env=env,capture_output=True,text=True,timeout=3)
 if r.returncode:raise RuntimeError(r.stderr.strip())
 text=re.sub(r'\buint32\s+','',r.stdout.strip())
 return ast.literal_eval(text)[0]

def owner():
 try:return call('org.freedesktop.DBus.GetNameOwner',NAME)
 except RuntimeError as e:
  if 'NameHasNoOwner' in str(e):return None
  raise

def eventually(test,message,timeout=3):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  if test():return
  time.sleep(.025)
 raise AssertionError(message)

def start_bus():
 global bus,number
 number+=1
 stream=Path('/home/probe/bus-'+str(number)+'.log').open('w');files.append(stream)
 bus=subprocess.Popen(['dbus-daemon','--nofork','--nopidfile','--config-file=/probe/bus.conf'],stdout=stream,stderr=subprocess.STDOUT)
 children.append(bus)
 eventually(lambda:Path('/home/probe/runtime/private-bus').is_socket(),'private bus socket ready')
 eventually(lambda:call('org.freedesktop.DBus.GetId') is not None,'private bus answers')

def stop(p):
 if p.poll() is None:
  p.terminate()
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)

def start(name,baseline=False,oneshot=False,missing=False):
 path='/home/probe/'+name+'.log'
 stream=Path(path).open('w');files.append(stream)
 env=dict(os.environ,DBUS_SESSION_BUS_ADDRESS='unix:path=/nonexistent/test-bus' if missing else ADDRESS,
          QML_IMPORT_PATH=('/baseline' if baseline else '/opt/omabuntu-runtime')+'/lib/qt6/qml')
 command=[BASE if baseline else CANDIDATE,'--no-color','--no-detailed-logs','--path','/probe/'+('once' if oneshot else 'hold')+'.qml']
 p=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT);children.append(p)
 return p,path

def owner_is(p):
 value=owner()
 return bool(value and call('org.freedesktop.DBus.GetConnectionUnixProcessID',value)==p.pid)

def failed_closed(p,log,reason):
 code=p.wait(timeout=3)
 require(code in (-signal.SIGABRT,128+signal.SIGABRT),'expected native fail-fast SIGABRT')
 text=Path(log).read_text()
 require('OMABUNTU_NOTIFICATION_EXCLUSIVE_V1: '+reason in text,'exact native failure reason')
 require('PRIVATE_PROBE_WATCHDOG' not in text,'not a lifetime watchdog failure')

def checked(name,fn):
 start=time.monotonic();fn();results.append({'name':name,'passed':True,'seconds':round(time.monotonic()-start,3)})

try:
 start_bus()
 def free():
  p,log=start('free',oneshot=True)
  eventually(lambda:owner_is(p),'candidate owns free name')
  unique=owner()
  caps=call('org.freedesktop.Notifications.GetCapabilities',dest=unique,path='/org/freedesktop/Notifications')
  require('actions' in caps,'actual NotificationServer capabilities')
  ident=call('org.freedesktop.Notifications.Notify','Fixture','0','','Synthetic notice','Synthetic body','[]','{}','1000',dest=unique,path='/org/freedesktop/Notifications')
  require(isinstance(ident,int) and ident>0,'native Notify returns an ID')
  require(p.wait(timeout=3)==0,'clean native exit after synthetic notification')
  require('PRIVATE_NATIVE_NOTIFY_RECEIVED' in Path(log).read_text(),'actual native notification signal received')
  eventually(lambda:owner() is None,'clean exit releases bus name')
 checked('free-name-and-native-notify',free)
 def replacement():
  p,log=start('replacement-owner');eventually(lambda:owner_is(p),'candidate owns name')
  unique=owner()
  require(call('org.freedesktop.DBus.RequestName',NAME,'6')==3,'foreign replacement refused with EXISTS')
  require(owner()==unique,'replacement did not change owner')
  require(call('org.freedesktop.DBus.ListQueuedOwners',NAME)==[unique],'no foreign queued owner')
  stop(p);eventually(lambda:owner() is None,'owner exits without successor')
 checked('refuse-replacement',replacement)
 def conflict():
  holder,_=start('conflict-holder',baseline=True);eventually(lambda:owner_is(holder),'baseline holder ready')
  unique=owner();p,log=start('conflict-candidate')
  failed_closed(p,log,'notification role unavailable')
  require(owner()==unique,'existing owner untouched')
  require(call('org.freedesktop.DBus.ListQueuedOwners',NAME)==[unique],'candidate did not queue')
  stop(holder);eventually(lambda:owner() is None,'name released by original holder')
  time.sleep(.7);require(owner() is None and p.poll() is not None,'no candidate late takeover')
 checked('conflict-no-queue-no-late-takeover',conflict)
 def negative():
  holder,_=start('negative-holder',baseline=True);eventually(lambda:owner_is(holder),'negative holder ready')
  waiter,log=start('negative-waiter',baseline=True)
  eventually(lambda:'Registration will be attempted again' in Path(log).read_text(),'unpatched waiter reaches known retry path')
  require(owner_is(holder),'unpatched waiter initially cannot own')
  stop(holder);eventually(lambda:owner_is(waiter),'negative control reproduces original late takeover')
  stop(waiter);eventually(lambda:owner() is None,'negative control cleanup')
 checked('negative-control-original-late-takeover',negative)
 def missing():
  p,log=start('missing',missing=True);failed_closed(p,log,'session bus unavailable')
  require(owner() is None,'missing-bus probe did not affect private owner')
 checked('missing-bus-fails-closed',missing)
 def loss():
  p,log=start('bus-loss');eventually(lambda:owner_is(p),'bus-loss owner ready')
  stop(bus);failed_closed(p,log,'session bus disconnected')
  # Daemon shutdown may leave its private socket file. The replacement daemon
  # handles only that disposable test address; no host path is ever exposed.
  socket=Path('/home/probe/runtime/private-bus')
  if socket.exists():socket.unlink()
  start_bus();require(owner() is None,'no takeover after private bus recreation')
 checked('bus-loss-fails-closed',loss)
 report={'status':'private-bus-checks-passed','checks':results,'host_bus_exposed':False}
except Exception as error:
 report={'status':'failed','checks':results,'error':type(error).__name__+': '+str(error),'host_bus_exposed':False}
finally:
 for p in reversed(children):stop(p)
 for f in files:f.close()
Path('/home/probe/native-results.json').write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(0 if report['status']=='private-bus-checks-passed' else 1)
'''


def eligibility(root, candidate):
    case, runtime, build = variant.verify(root, candidate)
    receipt_path = case / 'eligibility.json'
    report_path = case / 'private-bus-report.json'
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size > 2_000_000 for p in (receipt_path, report_path)):
        raise builder.BuildError('Require bounded private-bus eligibility receipts')
    receipt = json.loads(receipt_path.read_text());report = json.loads(report_path.read_text())
    if (receipt.get('schema_version') != 1 or receipt.get('status') != 'eligible-for-separate-deployment-review'
            or receipt.get('build_report_sha256') != builder.digest(case / 'report.json')
            or receipt.get('test_report_sha256') != builder.digest(report_path)
            or receipt.get('binary_sha256') != build['binary_sha256']
            or receipt.get('patch_sha256') != build['patch_sha256']
            or receipt.get('checker_sha256') != builder.digest(Path(__file__))
            or report.get('checker_sha256') != builder.digest(Path(__file__))
            or report.get('status') != 'private-bus-checks-passed' or report.get('host_bus_exposed') is not False
            or report.get('returncode') != 0 or report.get('artifacts_unchanged') is not True
            or [c.get('name') for c in report.get('checks', [])] != list(CHECKS)
            or any(c.get('passed') is not True for c in report['checks'])
            or receipt.get('live_deployment_authorized') is not False):
        raise builder.BuildError('Private-bus eligibility does not match this tested artifact/checker')
    return receipt


def run(root, candidate, baseline):
    case, runtime, build = variant.verify(root, candidate)
    _, original, _ = check_runtime.verify_stage(root, baseline)
    if (case / 'eligibility.json').exists():
        raise builder.BuildError('Do not overwrite existing successful candidate evidence')
    previous = case / 'private-bus-report.json'
    if previous.exists():
        if previous.is_symlink() or previous.stat().st_size > 2_000_000:
            raise builder.BuildError('Unsafe previous test receipt')
        old = json.loads(previous.read_text())
        if old.get('status') != 'failed':
            raise builder.BuildError('Do not overwrite nonfailed candidate evidence')
        archive = builder.private_directory(case / 'failed-test-attempts')
        name = builder.digest(previous) + '.json'
        if not (archive / name).exists():
            shutil.copy2(previous, archive / name)
    parent = builder.private_directory(root / 'work/notification-native-probes')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    probe = builder.private_directory(parent / stamp)
    for directory in ('probe','home','home/runtime','home/config','home/data','home/state','home/cache'):
        builder.private_directory(probe / directory)
    for name, text in {'driver.py':DRIVER,'bus.conf':BUS,'hold.qml':QML.replace('__QUIT__','false'),
                       'once.qml':QML.replace('__QUIT__','true'),
                       'fonts.conf':'<fontconfig><dir>/usr/share/fonts</dir></fontconfig>',
                       'passwd':'probe:x:%d:%d:Private probe:/home/probe:/bin/false\n' % (os.getuid(), os.getgid()),
                       'group':'probe:x:%d:\n' % os.getgid()}.items():
        (probe / 'probe' / name).write_text(text)
    before = builder.artifact_manifest(case / 'stage')
    original_before = builder.artifact_manifest(original)
    command = check_runtime.sandbox_command(runtime, probe, ['/usr/bin/python3','-B','/probe/driver.py'])
    index = command.index('--chdir');command[index:index] = [
        '--ro-bind',str(original),'/baseline',
        '--ro-bind',str(probe/'probe/passwd'),'/etc/passwd',
        '--ro-bind',str(probe/'probe/group'),'/etc/group']
    log = probe / 'output.log';code = None
    with log.open('x') as stream:
        try:code = subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=45,check=False).returncode
        except subprocess.TimeoutExpired:pass
    raw = probe / 'home/native-results.json'
    result = json.loads(raw.read_text()) if raw.is_file() and raw.stat().st_size < 65536 else {'status':'failed','checks':[]}
    result.update(returncode=code,checker_sha256=builder.digest(Path(__file__)),
                  baseline_binary_sha256=builder.digest(original / 'bin/quickshell'),
                  artifacts_unchanged=(before==builder.artifact_manifest(case/'stage') and original_before==builder.artifact_manifest(original)),
                  private_probe=str(probe),limits='Native registration and synthetic notification only; not original toast/surface, live migration, application, pixel or broad security acceptance.')
    passed = (code==0 and result['status']=='private-bus-checks-passed' and result['artifacts_unchanged']
              and [c['name'] for c in result['checks']]==list(CHECKS) and all(c['passed'] for c in result['checks']))
    result['status'] = 'private-bus-checks-passed' if passed else 'failed'
    report_path = case / 'private-bus-report.json'
    report_path.write_text(json.dumps(result,indent=2)+'\n')
    if passed:
        receipt={'schema_version':1,'status':'eligible-for-separate-deployment-review',
                 'build_report_sha256':builder.digest(case/'report.json'),'test_report_sha256':builder.digest(report_path),
                 'binary_sha256':build['binary_sha256'],'patch_sha256':build['patch_sha256'],
                 'checker_sha256':builder.digest(Path(__file__)),'live_deployment_authorized':False}
        (case/'eligibility.json').write_text(json.dumps(receipt,indent=2)+'\n')
        eligibility(root,case)
    print(report_path)
    return 0 if passed else 1


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true');p.add_argument('--verify',action='store_true')
    p.add_argument('--candidate',type=Path);p.add_argument('--baseline',type=Path)
    args=p.parse_args(argv)
    if not args.run and not args.verify:
        print('Plan only: actual notification runtime on disposable private buses; no host session')
        return 0
    if args.candidate is None or (args.run and args.baseline is None):p.error('explicit candidate/baseline required')
    os.umask(0o077)
    if args.verify:
        eligibility(ROOT,args.candidate);print('Artifact-bound eligibility verified; no live deployment grant');return 0
    return run(ROOT,args.candidate,args.baseline)


if __name__=='__main__':
    raise SystemExit(main())
