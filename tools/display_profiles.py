#!/usr/bin/env python3
"""Private reversible monitor profiles; no installer, reload or service activation."""
import argparse
import base64
import contextlib
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import socket
import struct
import subprocess
import sys
import time

import display_profile_model as model

LIMIT = 2_000_000
CONFIRM_SECONDS = 25
TERMINAL = {'kept','restored','aborted','acknowledged'}


def private(path, create=False):
    path=Path(path).absolute()
    if '..' in path.parts or any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Symlinked/traversing display state')
    if create:
        missing=[]
        for item in (path,*path.parents):
            if item.exists():break
            missing.append(item)
        for item in reversed(missing):item.mkdir(mode=0o700)
    if path.exists() and (not path.is_dir() or path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o077):raise ValueError('Display state must be owned/private')
    return path


def read(path, default=None):
    if path.is_symlink():raise ValueError('Symlinked state file')
    if not path.exists():return copy.deepcopy(default)
    if not path.is_file() or path.stat().st_uid!=os.getuid() or path.stat().st_size>LIMIT:raise ValueError('Invalid bounded owned state file')
    return json.loads(path.read_text())


def text_directory(home, create=False):
    # Legacy current/ can be 0775. Its owned 0700 state root is the privacy
    # boundary; never chmod existing preferences merely to admit text state.
    home=private(home,create)
    path=home/'current'
    if path.is_symlink():raise ValueError('Symlinked current state directory')
    if create:path.mkdir(mode=0o700,exist_ok=True)
    if path.exists() and (not path.is_dir() or path.stat().st_uid!=os.getuid()):raise ValueError('Foreign current state directory')
    return path


def atomic(path, data):
    if path.name=='text-size.txt' and path.parent.name=='current':text_directory(path.parent.parent,True)
    else:private(path.parent,True)
    if path.is_symlink():raise ValueError('Symlinked state destination')
    tmp=path.with_name('.'+path.name+'.'+secrets.token_hex(8))
    fd=os.open(tmp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def put(path,value):
    data=(json.dumps(value,sort_keys=True,allow_nan=False)+'\n').encode()
    if len(data)>LIMIT:raise ValueError('Private state capacity reached; no truncation or automatic pruning')
    atomic(path,data)


class Native:
    def __init__(self):
        self.signature=os.environ.get('HYPRLAND_INSTANCE_SIGNATURE','')
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}',self.signature) or 'hyprland' not in os.environ.get('XDG_CURRENT_DESKTOP','').lower().split(':'):raise ValueError('Require the existing Hyprland session, not GNOME')
        self.path=Path('/run/user')/str(os.getuid())/'hypr'/self.signature/'.socket.sock'
        self.owner=self.proof()
        version=json.loads(self.run(['version','-j']))
        if version.get('version','').lstrip('v')!='0.57.0':raise ValueError('Monitor profiles require reviewed Hyprland 0.57.0')
    def proof(self):
        if not self.path.is_socket() or self.path.is_symlink() or self.path.stat().st_uid!=os.getuid():raise ValueError('Compositor socket unavailable/foreign')
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
            peer.settimeout(2);peer.connect(str(self.path));pid,uid,_=struct.unpack('3i',peer.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        if uid!=os.getuid():raise ValueError('Foreign compositor peer')
        start=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19]
        return {'signature':self.signature,'pid':pid,'start':start,'inode':self.path.stat().st_ino}
    def run(self,args):
        if hasattr(self,'owner') and self.proof()!=self.owner:raise ValueError('Compositor owner changed')
        result=subprocess.run(['hyprctl','-i',self.signature,*args],capture_output=True,text=True,timeout=8)
        if result.returncode or len(result.stdout)>LIMIT:raise ValueError('Hyprland command failed or exceeded output bound')
        return result.stdout
    def inventory(self):return json.loads(self.run(['monitors','all','-j']))
    def apply(self,output):
        if self.run(['eval',model.program(output)]).strip()!='ok':raise ValueError('Monitor rule was not acknowledged')
    def settle(self,target):
        for _ in range(20):
            current=model.snapshot(self.inventory())
            if model.same(current,target):return current
            time.sleep(.1)
        raise ValueError('Monitor readback did not converge; recovery retained')


class Profiles:
    def __init__(self,root=None,native=None,clock=time.monotonic,guard=None):
        self.home=Path(root or os.environ.get('OMABUNTU_STATE_HOME') or Path.home()/'.local/state/omabuntu').absolute()
        self.directory=private(self.home/'display-profiles')
        self.path=self.directory/'profiles.json';self.pending_path=self.directory/'pending.json'
        self.native=native;self.clock=clock;self.guard=guard
        self.text_path=self.home/'current/text-size.txt'
    def store(self):
        data=read(self.path,{'schema_version':1,'profiles':{},'automatic':[]})
        if set(data)!={'schema_version','profiles','automatic'} or type(data['schema_version']) is not int or data['schema_version']!=1 or not isinstance(data['profiles'],dict) or len(data['profiles'])>64 or not isinstance(data['automatic'],list):raise ValueError('Invalid profile store')
        for name,entry in data['profiles'].items():
            if set(entry)!={'profile','kept_digest'} or (entry['kept_digest'] is not None and (not isinstance(entry['kept_digest'],str) or not re.fullmatch(r'[a-f0-9]{64}',entry['kept_digest']))) or model.validate(entry['profile'])['name']!=name:raise ValueError('Invalid stored profile')
        if any(n not in data['profiles'] for n in data['automatic']):raise ValueError('Invalid automatic profile selection')
        return data
    @contextlib.contextmanager
    def lock(self):
        private(self.directory,True)
        fd=os.open(self.directory/'control.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as stream:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);yield
    def text_state(self):
        text_directory(self.home)
        if self.text_path.is_symlink():raise ValueError('Symlinked text-size file')
        if not self.text_path.exists():return {'existed':False,'data':'','mode':None}
        if not self.text_path.is_file() or self.text_path.stat().st_uid!=os.getuid() or self.text_path.stat().st_size>32:raise ValueError('Invalid shell text-size file')
        return {'existed':True,'data':base64.b64encode(self.text_path.read_bytes()).decode(),'mode':self.text_path.stat().st_mode&0o777}
    def text_size(self):
        state=self.text_state()
        value=int(base64.b64decode(state['data']).decode().strip()) if state['existed'] else 12
        if value not in model.TEXT_SIZES:raise ValueError('Unsupported existing shell text size')
        return value
    def pending(self):
        value=read(self.pending_path)
        if value is not None:
            if not isinstance(value,dict) or set(value)!={'token','status','deadline'} or not isinstance(value['token'],str) or not re.fullmatch(r'[a-f0-9]{32}',value['token']) or value['status'] not in ('prepared','awaiting-confirmation'):
                raise ValueError('Malformed pending monitor transaction; manual recovery required')
            model.number(value['deadline'],0,1e15)
        return value
    def receipt(self,token):
        if not re.fullmatch(r'[a-f0-9]{32}',token):raise ValueError('Invalid transaction token')
        return self.directory/'transactions'/token/'receipt.json'
    def idle(self):
        if self.pending():raise ValueError('Pending monitor transaction requires Keep, Restore or explicit acknowledgement')
    def finish(self,record,status):
        record['status']=status;put(self.receipt(record['token']),record);put(self.pending_path,None)
    def current(self):return model.snapshot(self.native.inventory())
    def overview(self):
        data=self.store();p=self.pending()
        if p:
            record=read(self.receipt(p['token']))
            p=dict(p,status=record['status'])
        previous=[]
        for path in sorted((self.directory/'transactions').glob('*/receipt.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True)[:16]:
            entry=read(path)
            if entry['status'] not in ('kept','restored'):continue
            text=entry['text_before'];size=int(base64.b64decode(text['data']).decode().strip()) if text['existed'] else 12
            previous.append(model.validate({'schema_version':1,'name':'Before '+entry['token'][:8],'outputs':entry['review']['before'],'text_size':size}))
        return {'previous':previous,'profiles':[dict(v['profile'],automatic=n in data['automatic'],kept=v['kept_digest']==model.digest(v['profile'])) for n,v in data['profiles'].items()],
                'pending':p,'text_size':self.text_size(),'inventory':self.native.inventory()}
    def save(self,profile,expected):
        profile=model.validate(profile)
        with self.lock():
            self.idle();data=self.store()
            if model.digest(data)!=expected:raise ValueError('Profile store changed; refresh before saving')
            if profile['name'] not in data['profiles'] and len(data['profiles'])>=64:raise ValueError('Profile capacity reached')
            backup=self.directory/'backups'/(secrets.token_hex(16)+'.json');put(backup,{'store':data,'text':self.text_state()})
            data['profiles'][profile['name']]={'profile':profile,'kept_digest':None};data['automatic']=[n for n in data['automatic'] if n!=profile['name']];put(self.path,data)
        return self.overview()
    def delete(self,name,expected):
        with self.lock():
            self.idle();data=self.store()
            if model.digest(data)!=expected or name not in data['profiles']:raise ValueError('Stale profile deletion')
            put(self.directory/'backups'/(secrets.token_hex(16)+'.json'),{'store':data,'text':self.text_state()})
            del data['profiles'][name];data['automatic']=[n for n in data['automatic'] if n!=name];put(self.path,data)
        return self.overview()
    def review(self,name):
        self.idle();data=self.store();profile=model.validate(data['profiles'][name]['profile'],self.native.inventory())
        before=self.current();model.validate({'schema_version':1,'name':'Recovery','outputs':before,'text_size':self.text_size()})
        target=model.bind(profile['outputs'],self.native.inventory())
        return {'schema_version':1,'name':name,'store_digest':model.digest(data),'profile_digest':model.digest(profile),
                'owner':self.native.owner,'before':before,'target':target,'text_before':self.text_state(),
                'text_size':profile['text_size'],'confirmation_seconds':CONFIRM_SECONDS}
    def launch_guard(self,token):
        proc=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'guard',token,'--allow-recovery'],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
        import selectors
        with selectors.DefaultSelector() as poll:
            poll.register(proc.stdout,selectors.EVENT_READ)
            if not poll.select(3) or proc.stdout.readline(32)!=b'GUARD_READY\n':proc.terminate();raise ValueError('Recovery guard did not start; no monitor change issued')
        proc.stdout.close()
    def apply(self,review,approval,automatic=False):
        with self.lock():
            self.idle()
            if model.digest(review)!=approval or self.review(review['name'])!=review:raise ValueError('Review/session/topology/profile changed; no apply')
            token=secrets.token_hex(16);path=self.receipt(token)
            if len(list((self.directory/'transactions').glob('*/receipt.json')))>=4096:raise ValueError('Transaction history full; explicit archival required')
            record={'schema_version':1,'token':token,'status':'prepared','review':review,'deadline':self.clock()+CONFIRM_SECONDS,'allowed':[review['before']],'text_before':review['text_before']}
            # Journal and intent are durable before a recovery process or native write.
            put(path,record);put(self.pending_path,{'token':token,'status':'prepared','deadline':record['deadline']})
            try:
                (self.guard or self.launch_guard)(token)
                current=copy.deepcopy(review['before'])
                for output in sorted(review['target'],key=lambda o:not o['enabled']):
                    self.native.settle(current)
                    current=[copy.deepcopy(output) if model.key(o['identity'])==model.key(output['identity']) else o for o in current]
                    record['allowed'].append(copy.deepcopy(current));record['status']='applying';put(path,record)
                    self.native.apply(output)
                self.native.settle(review['target'])
                if self.text_state()!=review['text_before']:raise ValueError('Text-size writer changed during monitor apply')
                record['text_intent']={'existed':True,'data':base64.b64encode((str(review['text_size'])+'\n').encode()).decode(),'mode':0o600}
                put(path,record)
                atomic(self.text_path,(str(review['text_size'])+'\n').encode())
                record['text_after']=self.text_state();record['status']='awaiting-confirmation';put(path,record)
                put(self.pending_path,{'token':token,'status':record['status'],'deadline':record['deadline']})
            except Exception:
                record['status']='recovery-required';put(path,record)
                raise
        if automatic:self.keep(token,automatic=True)
        return {'token':token,'status':'kept' if automatic else 'awaiting-confirmation','deadline':record['deadline']}
    def load_pending(self,token):
        pending=self.pending()
        if not pending or pending['token']!=token:raise ValueError('No matching pending transaction')
        return read(self.receipt(token))
    def keep(self,token,automatic=False):
        with self.lock():
            record=self.load_pending(token);review=record['review']
            if record['status']!='awaiting-confirmation' or self.clock()>record['deadline'] or self.native.owner!=review['owner']:raise ValueError('Confirmation is stale or unavailable')
            if not model.same(self.current(),review['target']) or self.text_state()!=record['text_after']:raise ValueError('Readback drift; not confirmed')
            data=self.store()
            if model.digest(data)!=review['store_digest']:raise ValueError('Profile store changed before confirmation')
            if automatic and (review['name'] not in data['automatic'] or data['profiles'][review['name']]['kept_digest']!=review['profile_digest']):raise ValueError('Automatic application not previously accepted')
            record['store_before_keep']=copy.deepcopy(data);put(self.receipt(token),record)
            data['profiles'][review['name']]['kept_digest']=review['profile_digest'];put(self.path,data);self.finish(record,'kept')
        return {'status':'kept'}
    def restore(self,token):
        with self.lock():
            record=self.load_pending(token);review=record['review']
            if self.native.owner!=review['owner']:raise ValueError('Recovery session changed; acknowledge manually, no cross-session replay')
            current=self.current()
            if not any(model.same(current,state) for state in record['allowed']):raise ValueError('External display drift; automatic restoration refused')
            text=self.text_state()
            if text not in (record['text_before'],record.get('text_after',record['text_before']),record.get('text_intent',record['text_before']),record.get('text_restore_intent',record['text_before'])):raise ValueError('External text-size drift; no overwrite')
            inventory=self.native.inventory()
            before=model.bind(review['before'],inventory)
            old_text=record['text_before']
            old_size=int(base64.b64decode(old_text['data']).decode().strip()) if old_text['existed'] else 12
            model.validate({'schema_version':1,'name':'Recovery','outputs':before,'text_size':old_size},inventory)
            # Record reverse-operation intent as well, so interruption can recover.
            reverse=copy.deepcopy(current)
            for output in sorted(before,key=lambda o:not o['enabled']):
                self.native.settle(reverse)
                reverse=[copy.deepcopy(output) if model.key(o['identity'])==model.key(output['identity']) else o for o in reverse]
                record['allowed'].append(copy.deepcopy(reverse));put(self.receipt(token),record);self.native.apply(output)
            self.native.settle(before)
            if record['text_before']['existed']:
                record['text_restore_intent']=dict(record['text_before'],mode=0o600);put(self.receipt(token),record)
                atomic(self.text_path,base64.b64decode(record['text_before']['data']));os.chmod(self.text_path,record['text_before']['mode'])
            elif self.text_path.exists():
                self.text_path.unlink();fd=os.open(self.text_path.parent,os.O_RDONLY|os.O_DIRECTORY)
                try:os.fsync(fd)
                finally:os.close(fd)
            self.finish(record,'restored')
        return {'status':'restored'}
    def acknowledge(self,token):
        with self.lock():
            record=self.load_pending(token)
            if record['status']=='awaiting-confirmation' and self.clock()<record['deadline']:raise ValueError('Use Keep/Restore before the confirmation deadline')
            self.finish(record,'acknowledged')
        return {'status':'acknowledged-not-restored'}
    def automatic(self,name,enabled,expected):
        with self.lock():
            self.idle();data=self.store()
            if model.digest(data)!=expected or type(enabled) is not bool:raise ValueError('Stale automatic-profile selection')
            entry=data['profiles'][name]
            if enabled and entry['kept_digest']!=model.digest(entry['profile']):raise ValueError('Apply and Keep this exact profile before enabling automation')
            put(self.directory/'backups'/(secrets.token_hex(16)+'.json'),{'store':data,'text':self.text_state()})
            data['automatic']=[n for n in data['automatic'] if n!=name and (not enabled or {model.key(o['identity']) for o in data['profiles'][n]['profile']['outputs']}!={model.key(o['identity']) for o in entry['profile']['outputs']})]
            if enabled:data['automatic'].append(name)
            put(self.path,data)
        return self.overview()
    def set_text(self,value):
        if type(value) is not int or value not in model.TEXT_SIZES:raise ValueError('Unsupported shell text size')
        with self.lock():
            self.idle();put(self.directory/'backups'/(secrets.token_hex(16)+'.json'),{'store':self.store(),'text':self.text_state()})
            atomic(self.text_path,(str(value)+'\n').encode())
        return self.overview()
    def auto_tick(self,last):
        if self.pending():return last,{'status':'blocked-pending-recovery'}
        monitors=self.native.inventory();topology=model.topology(monitors)
        if last==topology:return topology,{'status':'unchanged-topology-no-write'}
        data=self.store();matches=[]
        for n in data['automatic']:
            entry=data['profiles'][n]
            if entry['kept_digest']!=model.digest(entry['profile']):continue
            try:model.validate(entry['profile'],monitors)
            except ValueError:continue
            matches.append(n)
        if len(matches)!=1:return topology,{'status':'no-unique-approved-profile'}
        review=self.review(matches[0])
        if model.same(review['before'],review['target']) and self.text_size()==review['text_size']:return topology,{'status':'already-observed'}
        return topology,self.apply(review,model.digest(review),automatic=True)


def dispatch(service,packet):
    if not isinstance(packet,dict) or 'op' not in packet:raise ValueError('Expected closed operation object')
    schemas={'status':set(),'capture':{'name'},'save':{'profile','store_digest'},'delete':{'name','store_digest'},'review':{'name'},'apply':{'review','approval'},'keep':{'token'},'restore':{'token'},'acknowledge':{'token'},'automatic':{'name','enabled','store_digest'},'text':{'value'}}
    op=packet['op']
    if op not in schemas or set(packet)!={'op'}|schemas[op]:raise ValueError('Unknown operation/keys')
    if op=='status':result=service.overview()
    elif op=='capture':result={'profile':model.validate({'schema_version':1,'name':packet['name'],'outputs':service.current(),'text_size':service.text_size()})}
    elif op=='save':result=service.save(packet['profile'],packet['store_digest'])
    elif op=='delete':result=service.delete(packet['name'],packet['store_digest'])
    elif op=='review':result={'review':service.review(packet['name'])};result['approval']=model.digest(result['review'])
    elif op=='apply':result=service.apply(packet['review'],packet['approval'])
    elif op=='keep':result=service.keep(packet['token'])
    elif op=='restore':result=service.restore(packet['token'])
    elif op=='acknowledge':result=service.acknowledge(packet['token'])
    elif op=='automatic':result=service.automatic(packet['name'],packet['enabled'],packet['store_digest'])
    else:result=service.set_text(packet['value'])
    return dict(result,store_digest=model.digest(service.store()))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('rpc','guard','watch'));parser.add_argument('token',nargs='?');parser.add_argument('--allow-recovery',action='store_true');parser.add_argument('--allow-session-automation',action='store_true');args=parser.parse_args(argv)
    service=Profiles(native=Native())
    if args.mode=='rpc':
        raw=sys.stdin.buffer.readline(65537)
        if len(raw)>65536:raise ValueError('Request too large')
        print(json.dumps(dispatch(service,json.loads(raw))))
    elif args.mode=='guard':
        if not args.allow_recovery:raise ValueError('Explicit recovery grant required')
        record=read(service.receipt(args.token))
        if not record or service.native.owner!=record['review']['owner']:raise ValueError('Recovery owner mismatch')
        print('GUARD_READY',flush=True)
        while service.clock()<record['deadline']:
            if not service.pending() or service.pending()['token']!=args.token:return
            time.sleep(.2)
        while True:
            pending=service.pending()
            if not pending or pending['token']!=args.token:return
            try:service.restore(args.token);return
            except BlockingIOError:time.sleep(.2)
            except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
                with service.lock():
                    pending=service.pending()
                    if pending and pending['token']==args.token:
                        record=service.load_pending(args.token);record['status']='recovery-required';record['error']=str(error)[:256];put(service.receipt(args.token),record)
                return
    else:
        if not args.allow_session_automation:raise ValueError('Explicit session automation grant required')
        last=None;candidate=None
        while service.store()['automatic']:
            observed=model.topology(service.native.inventory())
            if observed!=candidate:
                candidate=observed;time.sleep(2);continue
            try:last,result=service.auto_tick(last);print(json.dumps(result),flush=True)
            except (OSError,ValueError,KeyError,subprocess.SubprocessError):
                print(json.dumps({'status':'automatic-refused-check-recovery'}),flush=True)
                # Failure is not an infinite retry/override loop. Re-arm only
                # after an actual topology change or a new explicit process.
                last=model.topology(service.native.inventory())
            time.sleep(2)


if __name__=='__main__':
    os.umask(0o077)
    try:main()
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        print(json.dumps({'error':str(error)[:256]}));raise SystemExit(1)
