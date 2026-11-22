"""Owner-bound SwayNC/Hyprsunset IO; no target launch or GNOME-global writes.

User-bus connections require an explicit transport-activation-risk grant.
"""
import hashlib
import json
import itertools
import math
import os
from pathlib import Path
import re
import selectors
import socket
import stat
import struct
import subprocess
import time
import xml.etree.ElementTree as ET


class NativeError(ValueError):
    pass


def bounded(path, size=16384):
    with Path(path).open('rb') as stream:
        data = stream.read(size + 1)
    if len(data) > size:
        raise NativeError('oversized-input')
    return data


def binary(path):
    p = Path(path)
    s = p.stat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid != 0 or s.st_mode & 0o6022:
        raise NativeError('untrusted-binary')
    return [s.st_dev, s.st_ino]


def process_identity(pid, executable):
    p = Path('/proc') / str(pid)
    if p.stat().st_uid != os.getuid() or os.readlink(p / 'exe') != executable:
        raise NativeError('unexpected-owner')
    installed = binary(executable)
    running = (p / 'exe').stat()
    if installed != [running.st_dev, running.st_ino]:
        raise NativeError('owner-executable-changed')
    text = bounded(p / 'stat').decode()
    fields = text[text.rfind(')') + 2:].split()
    if fields[0] in ('Z', 'X'):
        raise NativeError('owner-not-running')
    return {'pid': pid, 'start': fields[19], 'binary': installed}


def runtime():
    uid = os.getuid()
    if uid == 0 or os.geteuid() != uid or os.environ.get('SUDO_USER') or os.environ.get('PKEXEC_UID'):
        raise NativeError('normal-user-required')
    p = Path('/run/user') / str(uid)
    if os.environ.get('XDG_RUNTIME_DIR', str(p)) != str(p):
        raise NativeError('custom-runtime-refused')
    for parent in (p, *p.parents):
        if parent.is_symlink():
            raise NativeError('unsafe-runtime')
    s = p.stat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != uid or s.st_mode & 0o077:
        raise NativeError('unsafe-runtime')
    return p


class Native:
    def __init__(self, bus_connection_granted=False):
        self.bus_connection_granted = bus_connection_granted
        self.deadline = time.monotonic() + 18
        self.sunset_version = None
        self.swaync_version = None

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise NativeError('native-deadline')
        return min(3, remaining)

    def command(self, args, package=None):
        if package is None and not self.bus_connection_granted:
            raise NativeError('session-bus-connection-grant-required')
        root = runtime()
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}
        if package is not None:
            if args or package not in ('hyprsunset', 'sway-notification-center'):
                raise NativeError('package-query-refused')
            binary('/usr/bin/dpkg-query')
            argv = ['/usr/bin/dpkg-query', '-W', '-f=${db:Status-Status}\\t${Version}', package]
        else:
            expected = 'unix:path=' + str(root / 'bus')
            if os.environ.get('DBUS_SESSION_BUS_ADDRESS', expected) != expected:
                raise NativeError('custom-session-bus-refused')
            s = (root / 'bus').lstat()
            if not stat.S_ISSOCK(s.st_mode) or s.st_uid != os.getuid():
                raise NativeError('session-bus-unavailable')
            binary('/usr/bin/busctl')
            env.update(XDG_RUNTIME_DIR=str(root), DBUS_SESSION_BUS_ADDRESS=expected)
            argv = ['/usr/bin/busctl', '--user', '--auto-start=no', '--timeout=2', '--json=short', *args]
        end = time.monotonic() + self.remaining()
        child = subprocess.Popen(argv,
                                 env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        selector = selectors.DefaultSelector()
        selector.register(child.stdout, selectors.EVENT_READ, True)
        selector.register(child.stderr, selectors.EVENT_READ, False)
        output = bytearray()
        size = 0
        try:
            while selector.get_map():
                if time.monotonic() >= end:
                    raise NativeError('native-timeout')
                for key, _ in selector.select(0.05):
                    data = os.read(key.fileobj.fileno(), 8192)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    size += len(data)
                    if size > 65536:
                        raise NativeError('native-output-bound')
                    if key.data:
                        output.extend(data)
            child.wait(timeout=max(0.01, end-time.monotonic()))
            if child.returncode:
                raise NativeError('native-call-refused')
            if package:
                return output.decode('ascii').strip()
            return json.loads(output) if output.strip() else {'type': '', 'data': []}
        finally:
            selector.close()
            if child.poll() is None:
                child.kill()
            child.wait(timeout=2)
            child.stdout.close()
            child.stderr.close()

    def call(self, destination, path, interface, method, signature='', values=()):
        # All destinations are the existing bus daemon or fresh unique owners.
        if destination != 'org.freedesktop.DBus' and not re.fullmatch(r':[0-9]+\.[0-9]+', destination):
            raise NativeError('nonunique-destination-refused')
        args = ['call', destination, path, interface, method]
        if signature:
            args += [signature, *values]
        value = self.command(args)
        if not isinstance(value, dict):
            raise NativeError('malformed-native-response')
        return value

    def owner(self, name):
        value = self.call('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'GetNameOwner', 's', (name,))
        data = value.get('data')
        if value.get('type') != 's' or not isinstance(data, list) or len(data) != 1 or not re.fullmatch(r':[0-9]+\.[0-9]+', str(data[0])):
            raise NativeError('owner-unavailable')
        return data[0]

    def dnd_context(self):
        version = self.supported_swaync()
        owner = self.owner('org.erikreider.swaync')
        if self.owner('org.freedesktop.Notifications') != owner:
            raise NativeError('notification-owner-mismatch')
        value = self.call('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'GetConnectionUnixProcessID', 's', (owner,))
        data = value.get('data')
        if value.get('type') != 'u' or not isinstance(data, list) or len(data) != 1 or type(data[0]) is not int or data[0] <= 0:
            raise NativeError('owner-unavailable')
        bus = self.call('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'GetId')
        ids = bus.get('data')
        if bus.get('type') != 's' or not isinstance(ids, list) or len(ids) != 1 or not isinstance(ids[0], str) or not re.fullmatch(r'[0-9a-f]{32}', ids[0]):
            raise NativeError('session-bus-generation-unavailable')
        context = {'owner': owner, 'version': version, 'bus_id': ids[0], 'process': process_identity(data[0], '/usr/bin/swaync')}
        description = self.call(owner, '/org/erikreider/swaync/cc', 'org.freedesktop.DBus.Introspectable', 'Introspect')
        raw = description.get('data')
        if description.get('type') != 's' or not isinstance(raw, list) or len(raw) != 1 or not isinstance(raw[0], str):
            raise NativeError('unsupported-dnd-interface')
        try:
            node = ET.fromstring(raw[0])
        except ET.ParseError:
            raise NativeError('unsupported-dnd-interface') from None
        interfaces = [n for n in node.findall('interface') if n.get('name') == 'org.erikreider.swaync.cc']
        if len(interfaces) != 1:
            raise NativeError('unsupported-dnd-interface')
        for name, expected in (('GetDnd', ([], ['b'])), ('SetDnd', (['b'], []))):
            methods = [m for m in interfaces[0].findall('method') if m.get('name') == name]
            if len(methods) != 1:
                raise NativeError('unsupported-dnd-interface')
            signature = ([a.get('type') for a in methods[0].findall('arg') if a.get('direction', 'in') == 'in'],
                         [a.get('type') for a in methods[0].findall('arg') if a.get('direction') == 'out'])
            if signature != expected:
                raise NativeError('unsupported-dnd-interface')
        return context

    def dnd_call(self, context, method, desired=None):
        return self.call(context['owner'], '/org/erikreider/swaync/cc', 'org.erikreider.swaync.cc', method,
                         'b' if desired is not None else '', ('true' if desired else 'false',) if desired is not None else ())

    def supported_swaync(self):
        if self.swaync_version is None:
            value = self.command([], package='sway-notification-center')
            if not re.fullmatch(r'installed\t0\.12\.4(?:-[A-Za-z0-9.+~]{1,100})?', value):
                raise NativeError('unsupported-swaync-version')
            self.swaync_version = value.split('\t')[1]
        return self.swaync_version

    def supported_sunset(self):
        if self.sunset_version is None:
            value = self.command([], package='hyprsunset')
            if not re.fullmatch(r'installed\t0\.4\.0(?:-[A-Za-z0-9.+~]{1,100})?', value):
                raise NativeError('unsupported-hyprsunset-version')
            self.sunset_version = value.split('\t')[1]
        return self.sunset_version

    def sunset_path(self):
        root = runtime()
        signature = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,200}', signature):
            raise NativeError('session-signature-required')
        directory = root / 'hypr' / signature
        for parent in (directory.parent, directory):
            s = parent.lstat()
            if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or s.st_mode & 0o022:
                raise NativeError('unsafe-controller-path')
        path = directory / '.hyprsunset.sock'
        s = path.lstat()
        if not stat.S_ISSOCK(s.st_mode) or s.st_uid != os.getuid():
            raise NativeError('controller-unavailable')
        return path, [s.st_dev, s.st_ino]

    def sunset_listener(self, path, proc=Path('/proc')):
        # Select only this exact local listener; never export a socket inventory.
        listeners = []
        for line in bounded(proc / 'net/unix', 2 * 1024 * 1024).decode('utf-8', 'replace').splitlines():
            fields = line.split(maxsplit=7)
            if len(fields) == 8 and fields[7] == str(path) and fields[3:6] == ['00010000', '0001', '01'] and re.fullmatch(r'[0-9]{1,20}', fields[6]):
                listeners.append(fields[6])
        if len(listeners) != 1:
            raise NativeError('running-controller-listener-required')
        target = int(listeners[0])
        entries = list(itertools.islice(proc.iterdir(), 65537))
        if len(entries) > 65536:
            raise NativeError('process-bound')
        owners = []
        for directory in entries:
            self.remaining()
            if not directory.name.isdigit():
                continue
            try:
                if directory.stat().st_uid != os.getuid() or bounded(directory / 'comm', 64) != b'hyprsunset\n':
                    continue
                identity = process_identity(int(directory.name), '/usr/bin/hyprsunset')
                fds = list(itertools.islice((directory / 'fd').iterdir(), 65537))
                if len(fds) > 65536:
                    raise NativeError('controller-fd-bound')
                for fd in fds:
                    self.remaining()
                    try:
                        info = fd.stat()
                        matches = stat.S_ISSOCK(info.st_mode) and info.st_ino == target
                    except FileNotFoundError:
                        continue
                    if matches:
                        owners.append(identity)
                        break
            except (FileNotFoundError, ProcessLookupError):
                continue
        if len(owners) != 1:
            raise NativeError('running-controller-owner-required')
        return {'listener': listeners[0], 'process': owners[0]}

    def sunset(self, command, expected=None):
        if command not in ('temperature', 'gamma', 'identity get', 'identity true', 'identity false'):
            raise NativeError('controller-command-refused')
        version = self.supported_sunset()
        path, inode = self.sunset_path()
        # Pin the filesystem endpoint before any connect: a replaced pathname
        # cannot silently redirect a query/write to a newly activated listener.
        pinned = os.open(path, os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            info = os.fstat(pinned)
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or [info.st_dev, info.st_ino] != inode:
                raise NativeError('controller-endpoint-changed')
            owner = self.sunset_listener(path)
            proof = {'socket': inode, 'version': version, **owner}
            if (expected is not None and proof != expected) or self.sunset_path()[1] != inode:
                raise NativeError('controller-owner-changed')
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(self.remaining())
                client.connect('/proc/self/fd/' + str(pinned))
                pid, uid, _ = struct.unpack('3i', client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                if uid != os.getuid() or process_identity(pid, '/usr/bin/hyprsunset') != proof['process'] or self.sunset_path()[1] != inode:
                    raise NativeError('unexpected-controller-owner')
                client.sendall(command.encode('ascii'))
                client.shutdown(socket.SHUT_WR)
                data = bytearray()
                while True:
                    client.settimeout(self.remaining())
                    part = client.recv(1024)
                    if not part:
                        break
                    data.extend(part)
                    if len(data) > 4096:
                        raise NativeError('controller-output-bound')
            if self.sunset_path()[1] != inode or process_identity(pid, '/usr/bin/hyprsunset') != proof['process']:
                raise NativeError('controller-owner-changed')
            return data.decode('ascii').strip(), proof
        finally:
            os.close(pinned)

    def read(self, kind):
        if kind == 'dnd':
            context = self.dnd_context()
            value = self.dnd_call(context, 'GetDnd')
            data = value.get('data')
            if value.get('type') != 'b' or not isinstance(data, list) or len(data) != 1 or type(data[0]) is not bool:
                raise NativeError('malformed-dnd-state')
            if self.dnd_context() != context:
                raise NativeError('notification-owner-changed')
            return {'active': data[0], 'proof': context}
        if kind != 'nightlight':
            raise NativeError('unknown-indicator')
        identity, context = self.sunset('identity get')
        kelvin, _ = self.sunset('temperature', context)
        gamma, _ = self.sunset('gamma', context)
        again, _ = self.sunset('identity get', context)
        if identity not in ('true', 'false') or identity != again:
            raise NativeError('unstable-controller-state')
        if not re.fullmatch(r'[0-9]{4,5}', kelvin) or not 1000 <= int(kelvin) <= 20000:
            raise NativeError('malformed-temperature')
        if not re.fullmatch(r'[0-9]{1,4}(\.[0-9]{1,9})?', gamma) or not math.isfinite(float(gamma)):
            raise NativeError('malformed-gamma')
        return {'active': identity == 'false', 'proof': {'context': context, 'kelvin': int(kelvin), 'gamma': float(gamma)}}

    def set(self, kind, desired, before):
        if type(desired) is not bool or self.read(kind) != before:
            raise NativeError('state-or-owner-changed')
        if kind == 'dnd':
            self.dnd_call(before['proof'], 'SetDnd', desired)
        elif kind == 'nightlight':
            reply, _ = self.sunset('identity false' if desired else 'identity true', before['proof']['context'])
            if reply != 'ok':
                raise NativeError('controller-request-uncertain')
        else:
            raise NativeError('unknown-indicator')
        after = self.read(kind)
        if after['proof'] != before['proof'] or after['active'] != desired:
            raise NativeError('readback-uncertain')
        return after


def action_key(scope, kind, value):
    return hashlib.sha256(json.dumps([scope, kind, value], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
