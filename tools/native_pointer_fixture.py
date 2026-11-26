"""Minimal owned-test Wayland virtual pointer; no CLI or host-session discovery.

Independent standard-library wire implementation of the v1 registry/virtual
pointer requests. It is usable only against the fixed disposable fixture socket.
"""
import os
from pathlib import Path
import re
import socket
import struct
import time


def words(*values):
    return struct.pack('='+'I'*len(values),*values)


def string(value):
    data=value.encode('ascii')+b'\0'
    return words(len(data))+data+b'\0'*((-len(data))%4)


def packet(target,opcode,payload=b''):
    size=8+len(payload)
    if not 1<=target<=0xffffffff or not 0<=opcode<=65535 or size>65532 or size%4:
        raise ValueError('Invalid bounded Wayland request')
    return words(target,(size<<16)|opcode)+payload


class Pointer:
    def __init__(self):
        runtime=os.environ.get('XDG_RUNTIME_DIR','');display=os.environ.get('WAYLAND_DISPLAY','')
        if runtime!='/home/probe/runtime' or not re.fullmatch(r'wayland-[0-9]+',display) or os.environ.get('PRIVATE_OUTPUT_COUNT')!='1':
            raise ValueError('Pointer requires the single-output disposable fixture')
        path=Path(runtime)/display
        if not path.is_socket() or path.is_symlink():raise ValueError('Missing private fixture socket')
        self.socket=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.socket.settimeout(2)
        self.next_id=2;self.manager=None;self.pointer=None
        try:
            self.socket.connect(str(path));self.send(1,1,words(2));self.sync()
            if self.manager is None:raise ValueError('Private virtual pointer protocol unavailable')
            manager=self.new_id();self.send(2,0,words(self.manager)+string('zwlr_virtual_pointer_manager_v1')+words(1,manager))
            self.pointer=self.new_id();self.send(manager,0,words(0,self.pointer));self.sync()
        except BaseException:
            self.socket.close();raise

    def new_id(self):
        self.next_id+=1
        if self.next_id>1000:raise ValueError('Fixture request budget exceeded')
        return self.next_id

    def send(self,target,opcode,payload=b''):
        self.socket.sendall(packet(target,opcode,payload))

    def exact(self,size):
        data=b''
        while len(data)<size:
            part=self.socket.recv(size-len(data))
            if not part:raise ValueError('Private Wayland connection closed')
            data+=part
        return data

    def sync(self):
        callback=self.new_id();self.send(1,0,words(callback))
        deadline=time.monotonic()+2
        for _ in range(256):
            if time.monotonic()>deadline:raise ValueError('Private Wayland synchronization timeout')
            target,header=struct.unpack('=II',self.exact(8));size=header>>16;opcode=header&65535
            if size<8 or size%4:raise ValueError('Invalid private Wayland event')
            payload=self.exact(size-8)
            if target==1 and opcode==0:raise ValueError('Private Wayland protocol error')
            if target==2 and opcode==0:
                if len(payload)<12:raise ValueError('Invalid private registry event')
                name,length=struct.unpack('=II',payload[:8]);end=8+length;aligned=(end+3)&~3
                if not length or aligned+4!=len(payload) or payload[end-1]!=0:raise ValueError('Invalid private registry string')
                interface=payload[8:end-1]
                if interface==b'zwlr_virtual_pointer_manager_v1':self.manager=name
            if target==callback and opcode==0:return
        raise ValueError('Private Wayland event budget exceeded')

    def move(self,x,y,width=1280,height=720):
        if any(type(v) is not int for v in (x,y,width,height)) or not 0<=x<width or not 0<=y<height or (width,height)!=(1280,720):
            raise ValueError('Unexpected fixture pointer coordinates')
        self.send(self.pointer,1,words(self.timestamp(),x,y,width,height));self.send(self.pointer,4);self.sync()

    @staticmethod
    def timestamp():return int(time.monotonic()*1000)&0xffffffff

    def click(self,button=272):
        if type(button) is not int or button not in (272,273):raise ValueError('Unsupported fixture button')
        for state in (1,0):
            self.send(self.pointer,2,words(self.timestamp(),button,state));self.send(self.pointer,4);self.sync()
            time.sleep(.05)

    def close(self):
        if self.socket is not None:
            try:
                if self.pointer is not None:self.send(self.pointer,8);self.sync()
            finally:self.socket.close();self.socket=None
