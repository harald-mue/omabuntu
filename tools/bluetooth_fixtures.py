"""Private fake-bus Bluetooth protocol checks; never access host BlueZ or desktop."""
import argparse
import ast
import json
import os
from pathlib import Path
import selectors
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
MODES = ('pin', 'passkey', 'confirm', 'authorization', 'service', 'display-pin',
         'display-passkey', 'display-update', 'daemon-cancel', 'reject', 'invalid-pin',
         'explicit-cancel', 'timeout', 'prompt-timeout', 'failure', 'owner-loss', 'release',
         'wrong-device', 'wrong-caller', 'unsupported-service', 'bad-signature', 'lifecycle')
SCOPE = '158000000000000000000001'
TOKEN = '158000000000000000000002'
PATH = '/org/bluez/hci0/dev_00_11_22_33_44_55'


def line(process, timeout=5):
    selector = selectors.DefaultSelector()
    try:
        selector.register(process.stdout, selectors.EVENT_READ)
        end = time.monotonic() + timeout
        data = bytearray()
        while len(data) <= 4096:
            if not selector.select(max(0, end-time.monotonic())):
                raise ValueError("Synthetic Bluetooth process deadline")
            char = os.read(process.stdout.fileno(), 1)
            if not char: raise ValueError("Synthetic Bluetooth process ended: " + process.stderr.read()[:2048])
            if char == b"\n": return data.decode("utf-8")
            data.extend(char)
        raise ValueError("Synthetic Bluetooth frame limit")
    finally:
        selector.close()


def inside(mode):
    children = []
    try:
        Path('/etc/machine-id').write_text('15800000000000000000000000000001\n')
        Path('/etc/passwd').write_text(f'probe:x:{os.getuid()}:{os.getgid()}::/tmp/home:/bin/false\n')
        Path('/etc/group').write_text(f'probe:x:{os.getgid()}:\n')
        config = Path('/tmp/bus.conf')
        config.write_text('<busconfig><type>session</type><listen>unix:path=/tmp/bluez-test-bus</listen>'
                          '<auth>EXTERNAL</auth><policy context="default"><allow send_destination="*"/>'
                          '<allow receive_sender="*"/><allow own="*"/></policy></busconfig>')
        def spawn(args, **extra):
            p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, bufsize=1, **extra)
            children.append(p)
            return p
        daemon = spawn(['/usr/bin/dbus-daemon', '--nofork', '--print-address=1', '--config-file='+str(config)])
        address = line(daemon)
        fake_mode = {'reject':'pin', 'invalid-pin':'pin', 'explicit-cancel':'pin', 'prompt-timeout':'pin',
                     'lifecycle':'pin'}.get(mode, mode)
        server = spawn(['/fixture/fake-bluez', address, fake_mode])
        assert line(server) == 'ready'
        env = dict(os.environ)
        if mode == 'timeout': env['OMABUNTU_TEST_OPERATION_MS'] = '100'
        if mode == 'prompt-timeout': env['OMABUNTU_TEST_PROMPT_MS'] = '100'
        agent = spawn(['/fixture/test-agent', '--allow-owned-agent', '--allow-system-bus-connection-risk',
                       '--scope='+SCOPE, '--test-bus='+address], env=env)
        assert json.loads(line(agent))['event'] == 'ready'
        def send(packet):
            packet['scope'] = SCOPE
            agent.stdin.write(json.dumps(packet)+'\n'); agent.stdin.flush()
        send({'op':'connect','token':TOKEN,'path':PATH,'adapter':'/org/bluez/hci0',
              'address':'00:11:22:33:44:55','paired':False,'connected':False})
        events = []; invalid_done = False
        end = time.monotonic()+8
        while time.monotonic() < end:
            event = json.loads(line(agent, 5)); events.append(event)
            assert event['scope'] == SCOPE
            if event['event'] == 'prompt':
                assert event['token'] == TOKEN
                if event['kind'].startswith('Display'):
                    assert event['code'] == '000042'
                    continue
                if mode == 'explicit-cancel': send({'op':'cancel','token':TOKEN}); continue
                if mode == 'prompt-timeout': continue
                if mode == 'invalid-pin' and not invalid_done:
                    send({'op':'answer','token':TOKEN,'prompt_id':event['prompt_id'],'accept':True,'value':'bad\nPIN'})
                    invalid_done = True
                    continue
                send({'op':'answer','token':TOKEN,'prompt_id':event['prompt_id'],
                      'accept':mode!='reject','value':'000042' if event['kind']=='RequestPasskey' else 'AB12'})
            if event['event'] == 'input-invalid':
                send({'op':'answer','token':TOKEN,'prompt_id':event['prompt_id'],'accept':True,'value':'AB12'})
            if event['event'] == 'result': break
        else: raise ValueError('Synthetic agent did not terminate operation')
        result = next(e for e in events if e['event']=='result')
        success = mode in ('pin','passkey','confirm','authorization','service','display-pin','display-passkey','display-update','invalid-pin','wrong-caller','lifecycle')
        assert result['status'] == ('observed' if success else 'cancelled' if mode in ('explicit-cancel','timeout','prompt-timeout') else 'uncertain' if mode in ('owner-loss','release') else 'error'), (mode,result)
        if mode == 'display-update':
            assert [e['entered'] for e in events if e['event']=='prompt'] == [2,6]
        if mode == 'invalid-pin': assert any(e['event']=='input-invalid' for e in events)
        if mode == 'lifecycle':
            for index, op in enumerate(('disconnect','forget')):
                token = TOKEN[:-1]+str(index+3)
                send({'op':op,'token':token,'path':PATH,'adapter':'/org/bluez/hci0',
                      'address':'00:11:22:33:44:55','paired':True,'connected':index==0})
                while True:
                    event=json.loads(line(agent))
                    if event['event']=='result': assert event['status']=='observed'; break
        if mode != 'owner-loss':
            raw = subprocess.run(['/usr/bin/gdbus','call','--address',address,'--dest','org.bluez',
                                  '--object-path','/test','--method','org.omabuntu.Test.Report'],
                                 capture_output=True,text=True,timeout=5,check=True)
            report=json.loads(ast.literal_eval(raw.stdout)[0])
            assert report['pairs']==1 and report['registers']==1
            assert report['connects']==(1 if success else 0), report
            assert report['cancels']==(1 if mode in ('explicit-cancel','timeout','prompt-timeout') else 0), report
            if mode=='lifecycle': assert report['removals']==1 and not report['connected']
            if mode=='wrong-caller': assert report['wrong_caller_denied']==1
        if mode not in ('owner-loss','release'):
            send({'op':'stop'})
        agent.wait(timeout=5)
        # Only fixed synthetic counters/status leave the sandbox, never prompt codes.
        print(json.dumps({'mode':mode,'passed':True,'events':len(events),'status':result['status']}))
    finally:
        for p in reversed(children):
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=3)


def compile_fake(output):
    flags = subprocess.run(['/usr/bin/pkg-config','--cflags','--libs','Qt6Core','Qt6DBus'],capture_output=True,text=True,timeout=10,check=True)
    result = subprocess.run(['/usr/bin/c++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-fPIC',
                             str(ROOT/'tests/fixtures/bluetooth_bluez.cpp'),'-o',str(output),*shlex.split(flags.stdout)],
                            capture_output=True,text=True,timeout=90)
    output.with_suffix('.build.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise ValueError('Fake BlueZ build failed; inspect private build log')


def run(build, modes=MODES):
    build=Path(build).resolve()
    if not build.is_relative_to(ROOT/'work'):raise ValueError('Use a private work/ build')
    records=[]
    for mode in modes:
        cmd=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session','--ro-bind','/usr','/usr',
             '--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64','--symlink','usr/bin','/bin',
             '--proc','/proc','--dev','/dev','--tmpfs','/tmp','--tmpfs','/etc','--dir','/run',
             '--ro-bind',str(build),'/fixture','--ro-bind',str(Path(__file__).resolve()),'/runner.py',
             '--clearenv','--setenv','PATH','/usr/bin:/bin','--setenv','HOME','/tmp/home',
             '--setenv','PYTHONDONTWRITEBYTECODE','1','--','/usr/bin/python3','-B','/runner.py','--inside',mode]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=25)
        (build/(mode+'.log')).write_text(result.stdout+result.stderr)
        record={'mode':mode,'passed':result.returncode==0}
        records.append(record)
        if result.returncode:break
    report={'passed':len(records)==len(modes) and all(r['passed'] for r in records),'checks':records,
            'limits':'Private bus/fake BlueZ only; no host buses, live registration, devices or desktop acceptance.'}
    (build/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path)
    parser.add_argument('--inside',choices=MODES)
    args=parser.parse_args(argv)
    if args.inside:inside(args.inside);return 0
    if not args.build:parser.error('--build required')
    return 0 if run(args.build)['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
