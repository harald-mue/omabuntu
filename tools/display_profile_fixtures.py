"""Real recovery child/process death and session automation on a private fake IPC."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
MODES=('crash','partial-crash','text-crash','keep','restore','drift','automatic')
SHIM='''#!/usr/bin/python3
import socket,json,sys
s=socket.socket(socket.AF_UNIX);s.connect('/run/user/'''+str(os.getuid())+'''/hypr/fixture/.socket.sock');s.sendall((json.dumps(sys.argv[3:])+'\\n').encode());s.shutdown(socket.SHUT_WR)
b=b''
while True:
 c=s.recv(65536)
 if not c:break
 b+=c
r=json.loads(b);print(r['output']);sys.exit(r['code'])
'''


def fake_server():
    import re
    import display_profile_model as m
    import display_profiles as p
    path=Path('/run/user')/str(os.getuid())/'hypr/fixture/.socket.sock';path.parent.mkdir(parents=True,exist_ok=True)
    server=socket.socket(socket.AF_UNIX);server.bind(str(path));server.listen(16)
    state=Path('/home/probe/fake.json')
    while True:
        conn,_=server.accept()
        with conn:
            conn.settimeout(1);raw=b''
            while True:
                part=conn.recv(65536)
                if not part:break
                raw+=part
                if b'\n' in raw:break
            if not raw:continue  # SO_PEERCRED proof connection, not an action.
            args=json.loads(raw);data=json.loads(state.read_text());code=0
            if args[0]=='version':output=json.dumps({'version':'0.57.0'})
            elif args[0]=='monitors':output=json.dumps(data['monitors'])
            elif args[0]=='eval':
                program=args[1];data['calls']+=1
                name=json.loads(re.search(r'output = ("[^"]+")',program)[1]);current=next(o for o in data['monitors'] if o['name']==name)
                current['disabled']='disabled = true' in program
                if not current['disabled']:
                    value=json.loads(re.search(r'mode = ("[^"]+")',program)[1]);w,h,r=m.mode(value);current.update(width=w,height=h,refreshRate=r)
                    position=json.loads(re.search(r'position = ("[^"]+")',program)[1]);x,y=position.split('x');current.update(x=int(x),y=int(y))
                    current['scale']=float(re.search(r'scale = ([0-9.]+)',program)[1]);current['transform']=int(re.search(r'transform = (\d+)',program)[1])
                p.put(state,data);output='ok'
            else:code=1;output='unsupported synthetic request'
            conn.sendall(json.dumps({'code':code,'output':output}).encode())


def actor(mode):
    import display_profiles as p
    import display_profile_model as m
    p.CONFIRM_SECONDS=2
    service=p.Profiles(native=p.Native());inventory=service.native.inventory()
    profile={'schema_version':1,'name':'Fixture','outputs':m.snapshot(inventory),'text_size':14}
    profile['outputs'][0]['scale']=1.5
    if len(profile['outputs'])>1:profile['outputs'][1]['x']=1280
    service.save(profile,m.digest(service.store()));review=service.review('Fixture')
    if mode=='partial-crash':
        original=service.native.apply
        def die(output):original(output);os._exit(0)
        service.native.apply=die
    if mode=='text-crash':
        original_atomic=p.atomic
        def die_text(path,data):
            original_atomic(path,data)
            if path==service.text_path:os._exit(0)
        p.atomic=die_text
    result=service.apply(review,m.digest(review))
    if mode in ('keep','automatic'):service.keep(result['token'])
    if mode=='restore':service.restore(result['token'])
    if mode=='automatic':service.automatic('Fixture',True,m.digest(service.store()))
    os._exit(0)  # Simulate parent disappearance; guard has a separate session.


def inside(mode):
    import display_profiles as p
    from display_profile_model import snapshot,same
    def monitor(name,serial,x):return dict(name=name,make='Synthetic',model='Panel',serial=serial,width=1920,height=1080,refreshRate=60,scale=1,x=x,y=0,transform=0,disabled=False,mirrorOf=-1,availableModes=['1920x1080@60.00Hz'])
    state=Path('/home/probe/fake.json');initial=[monitor('DP-1','one',0)]
    if mode=='partial-crash':initial.append(monitor('DP-2','two',1920))
    p.put(state,{'monitors':initial,'calls':0});server=subprocess.Popen([sys.executable,'-B','/probe/runner.py','--server'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    watch=None
    try:
        path=Path('/run/user')/str(os.getuid())/'hypr/fixture/.socket.sock'
        for _ in range(100):
            if path.is_socket():break
            time.sleep(.02)
        subprocess.run([sys.executable,'-B','/probe/runner.py','--actor',mode],check=True,timeout=12)
        service=p.Profiles(native=p.Native())
        if mode=='drift':
            data=json.loads(state.read_text());data['monitors'][0]['x']=777;p.put(state,data)
        if mode=='automatic':
            data=json.loads(state.read_text());data['monitors']=initial;p.put(state,data)
            watch=subprocess.Popen([sys.executable,'-B','/probe/display_profiles.py','watch','--allow-session-automation'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        time.sleep(5 if mode=='automatic' else 3)
        if mode=='automatic':
            data=json.loads(state.read_text());calls=data['calls'];data['monitors'][0]['scale']=1;p.put(state,data);time.sleep(3)
            assert json.loads(state.read_text())['calls']==calls  # No external-writer override loop.
            data=json.loads(state.read_text());data['monitors'][0]['serial']='unknown';p.put(state,data);time.sleep(4)
            assert json.loads(state.read_text())['calls']==calls
            data=json.loads(state.read_text());data['monitors']=initial;p.put(state,data);time.sleep(4)
        observed=json.loads(state.read_text())
        if mode in ('crash','partial-crash','text-crash','restore'):
            assert same(snapshot(initial),snapshot(observed['monitors']));assert not service.text_path.exists();assert service.pending() is None
        elif mode=='drift':assert observed['monitors'][0]['x']==777 and service.pending()
        else:assert observed['monitors'][0]['scale']==1.5 and service.text_size()==14 and service.pending() is None
        print(json.dumps({'mode':mode,'passed':True,'calls':observed['calls']}))
    finally:
        for proc in (watch,server):
            if proc is not None:
                proc.terminate()
                try:proc.wait(timeout=3)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)


def run(build,modes=MODES):
    import check_runtime
    output=ROOT/'work/display-profiles-160'/('ipc-'+str(time.time_ns()));output.mkdir(mode=0o700)
    _,runtime,_=check_runtime.verify_stage(ROOT,build);records=[]
    for mode in modes:
        case=output/mode;(case/'probe/bin').mkdir(parents=True,mode=0o700);(case/'home').mkdir(mode=0o700)
        for name in ('display_profiles.py','display_profile_model.py'):shutil.copyfile(ROOT/'tools'/name,case/'probe'/name)
        shutil.copyfile(Path(__file__).resolve(),case/'probe/runner.py');shim=case/'probe/bin/hyprctl';shim.write_text(SHIM);shim.chmod(0o500)
        command=['/usr/bin/env','PATH=/probe/bin:/usr/bin:/bin','XDG_CURRENT_DESKTOP=Hyprland','HYPRLAND_INSTANCE_SIGNATURE=fixture','OMABUNTU_STATE_HOME=/home/probe/state','/usr/bin/python3','-B','/probe/runner.py','--inside',mode]
        result=subprocess.run(check_runtime.sandbox_command(runtime,case,command),capture_output=True,text=True,timeout=25)
        (case/'output.log').write_text(result.stdout+result.stderr);records.append({'mode':mode,'passed':result.returncode==0})
    report={'passed':all(r['passed'] for r in records),'checks':records,'limits':'Private fake Hyprland socket only; no host IPC/display/buses or native acceptance.'}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(output/'report.json');return 0 if report['passed'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--server',action='store_true');parser.add_argument('--actor');parser.add_argument('--inside');parser.add_argument('--build-dir',type=Path);args=parser.parse_args()
    if args.server:fake_server()
    elif args.actor:actor(args.actor)
    elif args.inside:inside(args.inside)
    else:raise SystemExit(run(args.build_dir))
