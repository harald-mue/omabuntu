#!/usr/bin/env python3
"""Private native host-admission check, plan-only without --run; no host bus/state."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import check_native_history as history
import notification_admission as capability
import user_install as deployment

QML = '''import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
 QtObject {id:context;property QtObject bar:QtObject {
  property string position:"top";property int barSize:26;property bool barHidden:false
  function barSizeFor(name){return 26}
 }}
 NotificationHost {id:host;shellContext:context}
 Timer {interval:35000;running:true;onTriggered:Qt.exit(98)}
}
'''
DRIVER = history.DRIVER.split('try:\n for path in ', 1)[0] + r'''
try:
 for path in ('/run/user','/dev/dri','/dev/input','/sys','/etc/xdg','/var/run/dbus/system_bus_socket'):
  require(not Path(path).exists(),'no host path: '+path)
 require(not any(k in env for k in ('HYPRLAND_INSTANCE_SIGNATURE','WAYLAND_DISPLAY','WAYLAND_SOCKET','DISPLAY')),'no host session identity')
 bus=spawn('bus',['dbus-daemon','--nofork','--nopidfile','--config-file=/probe/bus.conf'])
 wait(lambda:Path('/home/probe/runtime/private-bus').is_socket(),'private bus ready')
 env['DBUS_SESSION_BUS_ADDRESS']=ADDRESS
 compositor=spawn('compositor',[LAB+'labwc','-d','-C','/probe/labwc'],env)
 def socket():
  values=[p for p in Path('/home/probe/runtime').glob('wayland-*') if p.is_socket()]
  return values[0] if len(values)==1 else None
 env['WAYLAND_DISPLAY']=wait(socket,'private compositor ready').name
 bundle=Path('/home/probe/bundle');shutil.copytree('/probe/fixture-bundle',bundle)
 shutil.copytree('/opt/omabuntu-runtime',bundle/'runtime',symlinks=True)
 alias=bundle/'runtime/bin/qs';alias.unlink();alias.symlink_to('quickshell')
 # The fixture is explicitly not the production TrialShell. Re-seal that test
 # root before issuing a grant; original notification/host/runtime bytes stay.
 meta=json.loads((bundle/'release.json').read_text())
 for name,row in meta['files'].items():
  if 'mode' in row and (bundle/name).exists():(bundle/name).chmod(row['mode'])
 shellqml=bundle/'shell/TrialShell.qml';shellqml.chmod(0o600);shellqml.write_text(Path('/probe/admission-shell.qml').read_text())
 shellqml.chmod(meta['files']['shell/TrialShell.qml']['mode'])
 sys.path.insert(0,str(bundle/'helpers'))
 import notification_session as admission
 manager=admission.manager(bundle)
 meta['files']=manager.file_manifest(bundle)
 release=bundle/'release.json';release.chmod(0o600);release.write_text(json.dumps(meta)+'\n');release.chmod(0o444)
 env['OMABUNTU_MENU_HELPER']=str(bundle/'helpers/menu_model.py')
 QS=str(bundle/'runtime/bin/quickshell')
 def ipc(method,*args,target='omabuntuNotifications'):
  return command([QS,'ipc','--path',str(shellqml),'call',target,method,*args])
 def grant(label):
  p=admission.issue(bundle,Path('/home/probe/grants')/label,env)
  env['OMABUNTU_NOTIFICATION_SESSION_FILE']=str(p);return p
 def launch(label):return spawn(label,admission.argv(bundle),env)
 def role():return json.loads(command([str(bundle/'runtime/bin/quickshell'),'ipc','--path',str(shellqml),'call','omabuntuNotificationRole','status']))
 proof=grant('valid');shell=launch('admitted')
 wait(lambda:owner() is not None,'admitted host owns private name')
 require(dbus('org.freedesktop.DBus.GetConnectionUnixProcessID',owner())==shell.pid,'actual admitted parent owns bus')
 wait(lambda:role()=={'admitted':True,'ready':True,'quiet':False},'native role readiness')
 claim=admission.private_json(proof.parent/'claim.json')
 require(claim['pid']==shell.pid and claim['identity']==manager.identity(shell.pid),'claim binds real parent PID/start/argv')
 send_notice('Private admitted fixture');wait(lambda:probe()['toasts']==1,'native original card from admitted host');clear()
 stop(shell);wait(lambda:owner() is None,'admitted host releases name')
 checks.append({'name':'native-artifact-session-parent-claim-owner-and-card','passed':True})
 def refused(label):
  p=launch(label);wait(lambda:p.poll() is not None,'refused shell exits')
  require(p.returncode!=0 and owner() is None,'refusal has no owner/queue')
  require('OMABUNTU_NOTIFICATION_ADMISSION_FAILED' in Path('/home/probe/'+label+'.log').read_text(),'explicit admission refusal')
  checks.append({'name':label,'passed':True})
 refused('duplicate-grant-refused')
 grant('other-session');original=env.get('HYPRLAND_INSTANCE_SIGNATURE');env['HYPRLAND_INSTANCE_SIGNATURE']='private-mismatched-session'
 refused('session-mismatch-refused')
 if original is None:del env['HYPRLAND_INSTANCE_SIGNATURE']
 else:env['HYPRLAND_INSTANCE_SIGNATURE']=original
 grant('changed-artifact');target=bundle/'shell/Notifications/Actions.js';target.chmod(0o600);target.write_bytes(target.read_bytes()+b'\n')
 refused('changed-artifact-refused')
 log=Path('/home/probe/admitted.log').read_text()
 require(not any(s in log for s in ('TypeError:','ReferenceError:','Binding loop','Unable to assign','Cannot assign')),'healthy admitted native QML')
 warnings=[line for line in log.splitlines() if re.search(r'^\s*(WARN|ERROR|FATAL|CRITICAL)\b',line)]
 require(len(warnings)==1 and '$HYPRLAND_INSTANCE_SIGNATURE is unset. Cannot connect to hyprland.' in warnings[0],'only expected absent-Hyprland warning')
 require(not Path('/home/probe/forbidden-actions.log').exists(),'no activation sentinel')
 result={'status':'passed','checks':checks,'claim_verified':True}
except Exception as error:result={'status':'failed','checks':checks,'error':type(error).__name__+': '+str(error)}
finally:
 for p in reversed(children):stop(p)
 for f in files:f.close()
 result['children_reaped']=all(p.poll() is not None for p in children)
Path('/home/probe/native-history-results.json').write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(0 if result['status']=='passed' else 1)
'''


def run(root, bundle, lab, candidate):
    deployment.verify_bundle(bundle); capability.verify(bundle)
    original = history.preview.verified_sources
    def sources(path):
        files, meta = original(path)
        for p in bundle.rglob('*'):
            if p.is_file() and not p.is_symlink() and 'runtime' not in p.relative_to(bundle).parts[:1]:
                files['fixture-bundle/' + str(p.relative_to(bundle))] = p.read_bytes()
        files['admission-shell.qml'] = QML.encode()
        return files, meta
    history.preview.verified_sources = sources
    old_driver = history.DRIVER; history.DRIVER = DRIVER
    before = set((root/'work/native-history-probes').iterdir())
    try: code = history.run(root, lab, candidate)
    finally:
        history.preview.verified_sources = original; history.DRIVER = old_driver
    added = set((root/'work/native-history-probes').iterdir()) - before
    if len(added) != 1: raise ValueError('Ambiguous private admission receipt')
    p = added.pop()/'report.json'; report = json.loads(p.read_text())
    report.update(fixture_kind='native-session-host-admission', admission_checker_sha256=capability.digest(Path(__file__)),
                  session_helper_sha256=capability.digest(bundle/'helpers/notification_session.py'),
                  limits='Private modified fixture root only, not production TrialShell/Hyprland/live migration acceptance.')
    p.write_text(json.dumps(report,indent=2)+'\n')
    return code


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true')
    p.add_argument('--bundle',type=Path);p.add_argument('--lab-dir',type=Path);p.add_argument('--candidate',type=Path)
    args=p.parse_args(argv)
    if not args.run: print('Plan only: private native session host admission/refusal');return 0
    if any(v is None for v in (args.bundle,args.lab_dir,args.candidate)):p.error('Require bundle/lab/candidate')
    os.umask(0o077)
    return run(history.ROOT,args.bundle.absolute(),args.lab_dir,args.candidate)


if __name__=='__main__':raise SystemExit(main())
