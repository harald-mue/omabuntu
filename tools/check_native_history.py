#!/usr/bin/env python3
"""Plan-only original native notification persistence tests with synthetic private state."""
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
QML='''import QtQuick
import Quickshell
import Quickshell.Io
import "Notifications" as Notifications
import "Notifications/Store.js" as Store
ShellRoot {
 QtObject {id:context;property QtObject bar:QtObject {
  property string position:"top";property int barSize:26;property bool barHidden:false
  function barSizeFor(name){return 26}
 }}
 Notifications.Service {id:service;shell:context;storageHelper:"/probe/helpers/notification_state.py"}
 IpcHandler {target:"nativeNotificationFixture"
  function metrics():string {
   return JSON.stringify({ready:service.storeReady&&service.liveLoaded&&service.historyLoaded&&service.quietLoaded,
    refs:Object.keys(service.refs).length,historyKeys:service.historyEntries.map(function(r){return r.key}),
    rows:service.layout.decks.reduce(function(rows,d){return rows.concat(d.rows.map(function(r){
     return {key:r.key,restored:r.restored,transient:r.transient,code:!!(r.code||r.codes),
      redacted:Store.redacted(r),image:!!r.image,actions:service.actionsOf(r.key,service.refsRevision).length}
    }))},[])})
  }
 }
 Timer {interval:35000;running:true;onTriggered:{console.error("PRIVATE_NATIVE_HISTORY_WATCHDOG");Qt.exit(98)}}
}
'''
DRIVER=native_input.BOOTSTRAP+r'''
import copy,hashlib,shutil,sys
sys.path.insert(0,'/probe/helpers')
import notification_state as state
STATE=Path('/home/probe/.local/state/omabuntu/notifications')
CANARY='73182649';MARKER='FixtureSecretSentinel';checkpoints=[];shell=None;generation=0;diagnostics=[]

def diagnostic_records():
 result=[]
 for index in range(1,generation+1):
  log=Path('/home/probe/shell-'+str(index)+'.log').read_text()
  result.append({'generation':index,'warnings':[line for line in log.splitlines() if re.search(r'^\s*(WARN|ERROR|FATAL|CRITICAL)\b',line)],
   'llvmpipe':'llvmpipe' in log,'hidden_failure':any(s in log for s in ('TypeError:','ReferenceError:','Binding loop','Unable to assign','PRIVATE_NATIVE_HISTORY_WATCHDOG'))})
 return result

class PhaseChecks(list):
 def append(self,value):
  value['diagnostic_counts']=[len(r['warnings']) for r in diagnostic_records()]
  super().append(value)
checks=PhaseChecks()

def read_store(directory=STATE):
 state.owned(directory,True);result={}
 for name in state.DEFAULTS:
  path=directory/name;state.owned(path);value=json.loads(path.read_bytes())
  if name=='quiet.json':require(isinstance(value,dict) and set(value)=={'dnd'} and type(value['dnd']) is bool,'private quiet schema')
  else:require(isinstance(value,list) and len(value)<=100 and all(state.valid_row(r,name=='history.json') for r in value),'private entry schema')
  result[name]=value
 return result

def redacted(row):
 return row['summary']=='Verification notification' and row['body']=='[redacted]' and row['rawBody']=='' and all(row[k]=='' for k in ('app','appIcon','source','groupKey','glyph','execArgv','execActions'))

def no_canary(directory=STATE):
 for name in state.DEFAULTS:
  raw=(directory/name).read_bytes()
  require(CANARY.encode() not in raw and MARKER.encode() not in raw,'synthetic secret absent from active store bytes')

def checkpoint(label):
 target=Path('/home/probe/checkpoints')/label;target.mkdir(mode=0o700,parents=True)
 record={'label':label,'files':{}}
 for name in state.DEFAULTS:
  source=STATE/name;state.owned(source);shutil.copy2(source,target/name)
  record['files'][name]=hashlib.sha256(source.read_bytes()).hexdigest()
 checkpoints.append(record)

def send_notice(title,ident=0,transient=False,secret=False):
 app=MARKER+CANARY if secret else 'Fixture'
 body='Your verification code is '+CANARY if secret else 'Synthetic history body'
 hints="{'transient': <true>}" if transient else '{}'
 return dbus('org.freedesktop.Notifications.Notify',app,str(ident),'',title,body,'[]',hints,'30000',dest=NAME,path='/org/freedesktop/Notifications')

def persisted(predicate,label):
 return wait(lambda:predicate(read_store()),label)

def start_shell():
 global shell,generation
 generation+=1;shell=spawn('shell-'+str(generation),[QS,'--no-color','--no-detailed-logs','--path','/probe/shell.qml'],env)
 wait(lambda:owner() is not None and metrics()['ready'],'actual native history readiness')
 require(dbus('org.freedesktop.DBus.GetConnectionUnixProcessID',owner())==shell.pid,'actual history fixture owns bus name')

def stop_shell(label):
 time.sleep(.35);checkpoint(label);stop(shell);wait(lambda:owner() is None,'owned fixture releases name before restart')

def write_seed(values):
 require(shell.poll() is not None,'seed only while owned service stopped')
 for name,value in values.items():
  require(name in state.DEFAULTS,'known private seed file')
  path=STATE/name;state.owned(path);path.write_text(json.dumps(value)+'\n');state.owned(path)

try:
 for path in ('/run/user','/dev/dri','/dev/input','/sys','/etc/xdg','/var/run/dbus/system_bus_socket'):
  require(not Path(path).exists(),'no host path: '+path)
 require(count==1 and not any(k in env for k in ('HYPRLAND_INSTANCE_SIGNATURE','WAYLAND_DISPLAY','WAYLAND_SOCKET','DISPLAY')),'fresh private history environment')
 bus=spawn('bus',['dbus-daemon','--nofork','--nopidfile','--config-file=/probe/bus.conf'])
 wait(lambda:Path('/home/probe/runtime/private-bus').is_socket(),'private bus ready')
 env['DBUS_SESSION_BUS_ADDRESS']=ADDRESS;dbus('org.freedesktop.DBus.GetId')
 compositor=spawn('compositor',[LAB+'labwc','-d','-C','/probe/labwc'],env)
 def socket():
  sockets=[p for p in Path('/home/probe/runtime').glob('wayland-*') if p.is_socket()]
  return sockets[0] if len(sockets)==1 else None
 display=wait(socket,'private compositor ready');env['WAYLAND_DISPLAY']=display.name
 protocols=command([LAB+'wayland-info']);Path('/home/probe/protocols.log').write_text(protocols)
 outputs=sorted(set(re.findall(r"name:\s*['\"]?(HEADLESS-\d+)",protocols)));require(len(outputs)==1,'one actual history output')
 start_shell();require(probe()['toasts']==0,'empty private initial native state')
 send_notice('Ordinary fixture');wait(lambda:probe()['toasts']==1,'ordinary native delivery')
 persisted(lambda s:len(s['live.json'])==1,'ordinary live write');clear()
 persisted(lambda s:len(s['history.json'])==1 and not s['live.json'],'ordinary close moves live to history')
 ordinary=copy.deepcopy(read_store()['history.json'][0]);baseline=copy.deepcopy(read_store()['history.json'])
 send_notice('Transient fixture',transient=True);wait(lambda:probe()['toasts']==1,'transient native delivery')
 time.sleep(.4);require(not read_store()['live.json'],'transient absent while visible');clear()
 require(read_store()['history.json']==baseline,'transient excluded from closed history')
 checks.append({'name':'ordinary-persistence-and-transient-exclusion','passed':True})
 ident=send_notice('Persistent replacement fixture');wait(lambda:probe()['toasts']==1,'replacement initial card')
 persisted(lambda s:len(s['live.json'])==1,'replacement initial live write')
 require(send_notice('Transient replacement fixture',ident,transient=True)==ident,'native replacement identity')
 wait(lambda:metrics()['rows'][0]['transient'],'native update becomes transient')
 persisted(lambda s:not s['live.json'],'persistent-to-transient removes saved row');clear()
 require(read_store()['history.json']==baseline,'transient replacement not retained')
 ident=send_notice('Transient to ordinary fixture',transient=True);wait(lambda:probe()['toasts']==1,'reverse replacement initial')
 require(send_notice('Ordinary replacement fixture',ident)==ident,'reverse native replacement identity')
 wait(lambda:not metrics()['rows'][0]['transient'],'native update becomes persistent')
 persisted(lambda s:len(s['live.json'])==1,'transient-to-persistent live write');clear()
 persisted(lambda s:len(s['history.json'])==2,'reverse replacement kept in history')
 checks.append({'name':'native-transient-replacement-both-directions','passed':True})
 send_notice('Verification fixture',secret=True);wait(lambda:probe()['toasts']==1 and metrics()['rows'][0]['code'],'real native code detection')
 persisted(lambda s:len(s['live.json'])==1 and redacted(s['live.json'][0]),'native live code redaction');no_canary();clear()
 persisted(lambda s:redacted(s['history.json'][0]),'native closed code redaction');no_canary()
 checks.append({'name':'native-code-live-and-history-redaction','passed':True})
 send_notice('Restored verification fixture',secret=True);wait(lambda:probe()['toasts']==1,'restore code arrival')
 persisted(lambda s:len(s['live.json'])==1 and redacted(s['live.json'][0]),'restore code persisted redacted')
 send_notice('Nonrestorable transient fixture',transient=True);wait(lambda:probe()['toasts']==2,'native transient beside saved code')
 time.sleep(.4);require(len(read_store()['live.json'])==1,'only redacted persistent row saved')
 stop_shell('before-private-restart');start_shell()
 wait(lambda:probe()['toasts']==1,'only persistent card restored')
 rows=metrics()['rows'];require(rows[0]['restored'] and rows[0]['redacted'] and not rows[0]['code'] and not rows[0]['image'] and rows[0]['actions']==0 and metrics()['refs']==0,'restored placeholder has no native sender/code/image')
 no_canary();capture('restored-redacted');clear()
 persisted(lambda s:not s['live.json'] and len(s['history.json'])==4,'restored close recorded')
 checks.append({'name':'private-native-restart-redacted-restore-and-transient-absence','passed':True})
 for index in range(7):
  send_notice('Recent fixture '+chr(65+index));wait(lambda:probe()['toasts']==1,'recent history arrival');clear()
 send_notice('Recent verification fixture',secret=True);wait(lambda:probe()['toasts']==1 and metrics()['rows'][0]['code'],'recent code detected');clear()
 persisted(lambda s:len(s['history.json'])==12,'recent native history writes');no_canary()
 before=copy.deepcopy(read_store()['history.json']);require(ipc('showHistory')=='ok','original native history IPC')
 wait(lambda:probe()['toasts']==6,'original six-row native history replay')
 rows=metrics()['rows'];require(all(r['restored'] and not r['code'] and not r['image'] and r['actions']==0 for r in rows) and any(r['redacted'] for r in rows) and metrics()['refs']==0,'replay is redacted/restored without native refs')
 capture('history-replay');clear()
 require(read_store()['history.json']==before,'replay dismissal does not duplicate history');no_canary()
 checks.append({'name':'native-six-row-history-replay-with-redacted-placeholder','passed':True})
 stop_shell('before-synthetic-retention-seed')
 now=time.time();seed=[]
 for index in range(98):
  row=copy.deepcopy(ordinary);row.update(key='retention'+str(index).zfill(3),closed_ts=now-index);seed.append(row)
 legacy=copy.deepcopy(ordinary);legacy.update(key='legacyHistory',summary='Verification fixture',body='Your verification code is '+CANARY,rawBody='Your verification code is '+CANARY,app=MARKER+CANARY,source=MARKER+CANARY,closed_ts=now-98);seed.append(legacy)
 old=copy.deepcopy(ordinary);old.update(key='outsideRetention',closed_ts=now-86401);seed.append(old)
 live=copy.deepcopy(legacy);del live['closed_reason'];del live['closed_ts'];live['key']='legacyLive'
 write_seed({'history.json':seed,'live.json':[live]});checkpoint('synthetic-legacy-seed-before-start')
 start_shell();wait(lambda:probe()['toasts']==1 and len(metrics()['historyKeys'])==99,'native startup prunes aged synthetic history')
 persisted(lambda s:len(s['history.json'])==99 and redacted(s['live.json'][0]) and any(r['key']=='legacyHistory' and redacted(r) for r in s['history.json']),'legacy active files rewritten redacted')
 require('outsideRetention' not in metrics()['historyKeys'],'24-hour-old boundary excluded');no_canary()
 require(metrics()['rows'][0]['redacted'] and not metrics()['rows'][0]['code'] and metrics()['refs']==0,'legacy live restore sanitised')
 checks.append({'name':'native-legacy-code-sanitisation-and-24-hour-retention','passed':True})
 clear();persisted(lambda s:len(s['history.json'])==100,'history reaches 100')
 for title in ('Bound newest A','Bound newest B'):
  send_notice(title);wait(lambda:probe()['toasts']==1,'bound arrival');clear()
  persisted(lambda s:len(s['history.json'])==100 and s['history.json'][0]['summary']==title,'native count cap and newest order')
 final=read_store();require(final['history.json'][1]['summary']=='Bound newest A' and not any(r['key']=='retention097' for r in final['history.json']),'oldest history dropped at count cap')
 no_canary();require(not final['live.json'] and final['quiet.json']=={'dnd':False},'final live empty and private quiet unchanged')
 checks.append({'name':'native-100-row-history-cap-and-newest-order','passed':True});checkpoint('final-bounded-state')
 diagnostics=diagnostic_records()
 require(all(len(r['warnings'])==1 and '$HYPRLAND_INSTANCE_SIGNATURE is unset. Cannot connect to hyprland.' in r['warnings'][0] for r in diagnostics),'only absent-Hyprland warning on each private start')
 require(all(r['llvmpipe'] and not r['hidden_failure'] for r in diagnostics),'native rendering without hidden QML errors')
 require(not Path('/home/probe/forbidden-actions.log').exists(),'no activation sentinel triggered')
 require(all(p.poll() is None for p in (shell,compositor,bus)),'owned actors healthy before cleanup')
 result={'status':'passed','checks':checks,'generations':generation,'checkpoints':checkpoints,'final_counts':{'live':0,'history':len(final['history.json'])},'active_store_canary_absent':True}
except Exception as error:result={'status':'failed','checks':checks,'error':type(error).__name__+': '+str(error),'checkpoints':checkpoints,'generations':generation,'diagnostics':diagnostics}
finally:
 for p in reversed(children):stop(p)
 for f in files:f.close()
 result['children_reaped']=all(p.poll() is not None for p in children)
Path('/home/probe/native-history-results.json').write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(0 if result['status']=='passed' else 1)
'''


def run(root,lab_dir,candidate):
    lab=graphics.verify_lab(root,lab_dir);ownership.eligibility(root,candidate)
    _,runtime,_=variant.verify(root,candidate);files,_=preview.verified_sources(root);sealed=notification_frontend.sources(root)
    if any(files.get(name)!=data for name,data in sealed.items()):raise ValueError('Sealed notification closure differs')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    case=builder.private_directory(builder.private_directory(root/'work/native-history-probes')/stamp)
    for directory in ('probe','probe/helpers','probe/labwc','home','home/runtime','home/config','home/cache','home/data','home/state'):
        builder.private_directory(case/directory)
    for name,data in files.items():
        path=case/'probe'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    fixture={'shell.qml':QML,'driver.py':DRIVER,'bus.conf':ownership.BUS,'deny-exec':graphics.GUARD,
             'labwc/rc.xml':'<labwc_config/>\n','fonts.conf':'<fontconfig><dir>/usr/share/fonts</dir><cachedir>/home/probe/cache/fontconfig</cachedir></fontconfig>',
             'passwd':'probe:x:%d:%d:Private probe:/home/probe:/bin/false\n'%(os.getuid(),os.getgid()),'group':'probe:x:%d:\n'%os.getgid()}
    for name,data in fixture.items():(case/'probe'/name).write_text(data)
    (case/'probe/helpers/notification_state.py').write_bytes((root/'tools/notification_state.py').read_bytes());(case/'probe/deny-exec').chmod(0o555)
    inputs=builder.artifact_manifest(case/'probe');before_lab=graphics.package_manifest(lab/'root');before_runtime=builder.artifact_manifest(runtime)
    command=graphics.sandbox(runtime,case,lab,1)
    with (case/'output.log').open('x') as stream:
        try:code=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=80,check=False).returncode
        except subprocess.TimeoutExpired:code=None
    result_path=case/'home/native-history-results.json'
    report=json.loads(result_path.read_text()) if result_path.is_file() else {'status':'failed','error':'Missing bounded native history result'}
    unchanged=inputs==builder.artifact_manifest(case/'probe') and before_lab==graphics.package_manifest(lab/'root') and before_runtime==builder.artifact_manifest(runtime)
    report.update(returncode=code,inputs_unchanged=unchanged,command=command,checker_sha256=builder.digest(Path(__file__)),
                  bootstrap_sha256=builder.digest(root/'tools/check_native_notifications.py'),input_checker_sha256=builder.digest(root/'tools/check_native_input.py'),
                  state_helper_sha256=builder.digest(root/'tools/notification_state.py'),staged_driver_sha256=builder.digest(case/'probe/driver.py'),
                  runtime_sha256=builder.digest(runtime/'bin/quickshell'),notification_sources={name:hashlib.sha256(data).hexdigest() for name,data in sealed.items()},
                  limits='Synthetic private native store/restart/replay only; no host state/clipboard/locked-session/adversarial security/production apps/Hyprland/crash/live migration acceptance.')
    if code!=0 or not unchanged or not report.get('children_reaped'):report['status']='failed'
    report['captures']={p.name:builder.digest(p) for p in (case/'home').glob('*.ppm')}
    (case/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(case/'report.json')
    return 0 if report['status']=='passed' else 1


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true')
    p.add_argument('--lab-dir',type=Path);p.add_argument('--candidate',type=Path);args=p.parse_args(argv)
    if not args.run:print('Plan only: synthetic private native notification history/redaction/transience');return 0
    if args.lab_dir is None or args.candidate is None:p.error('--run requires --lab-dir and --candidate')
    os.umask(0o077)
    return run(ROOT,args.lab_dir,args.candidate)


if __name__=='__main__':raise SystemExit(main())
