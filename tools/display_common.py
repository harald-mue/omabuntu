"""Neutral normal-monitor primitives; no profile workflow or automation imports."""
import base64
import contextlib
import copy
import fcntl
import json
import math
import os
from pathlib import Path
import re
import secrets
import socket
import struct
import subprocess

LIMIT = 2_000_000
TEXT_SIZES = (9, 10, 11, 12, 14, 16, 20)


def private(path, create=False):
    path = Path(path).absolute()
    if '..' in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlinked/traversing display state')
    if create:
        missing = []
        for item in (path, *path.parents):
            if item.exists():
                break
            missing.append(item)
        for item in reversed(missing):
            item.mkdir(mode=0o700)
    if path.exists() and (not path.is_dir() or path.stat().st_uid != os.getuid()
                          or path.stat().st_mode & 0o077):
        raise ValueError('Display state must be owned/private')
    return path


def read(path, default=None):
    if path.is_symlink():
        raise ValueError('Symlinked state file')
    if not path.exists():
        return copy.deepcopy(default)
    if not path.is_file() or path.stat().st_uid != os.getuid() or path.stat().st_size > LIMIT:
        raise ValueError('Invalid bounded owned state file')
    return json.loads(path.read_text())


def text_directory(home, create=False):
    # The private state root protects legacy current/ modes; do not chmod them.
    home = private(home, create)
    path = home / 'current'
    if path.is_symlink():
        raise ValueError('Symlinked current state directory')
    if create:
        path.mkdir(mode=0o700, exist_ok=True)
    if path.exists() and (not path.is_dir() or path.stat().st_uid != os.getuid()):
        raise ValueError('Foreign current state directory')
    return path


def atomic(path, data):
    if path.name == 'text-size.txt' and path.parent.name == 'current':
        text_directory(path.parent.parent, True)
    else:
        private(path.parent, True)
    if path.is_symlink():
        raise ValueError('Symlinked state destination')
    tmp = path.with_name('.' + path.name + '.' + secrets.token_hex(8))
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def put(path, value):
    data = (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode()
    if len(data) > LIMIT:
        raise ValueError('Private state capacity reached; no truncation or automatic pruning')
    atomic(path, data)


class Native:
    """Version-pinned existing-session observation and exact-owner commands."""
    def __init__(self):
        self.signature = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
        if (not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}', self.signature)
                or 'hyprland' not in os.environ.get('XDG_CURRENT_DESKTOP', '').lower().split(':')):
            raise ValueError('Require the existing Hyprland session, not GNOME')
        self.path = Path('/run/user') / str(os.getuid()) / 'hypr' / self.signature / '.socket.sock'
        self.owner = self.proof()
        version = json.loads(self.run(['version', '-j']))
        if version.get('version', '').lstrip('v') != '0.57.0':
            raise ValueError('Monitor controls require reviewed Hyprland 0.57.0')

    def proof(self):
        if not self.path.is_socket() or self.path.is_symlink() or self.path.stat().st_uid != os.getuid():
            raise ValueError('Compositor socket unavailable/foreign')
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
            peer.settimeout(2)
            peer.connect(str(self.path))
            pid, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if uid != os.getuid():
            raise ValueError('Foreign compositor peer')
        start = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[19]
        return {'signature': self.signature, 'pid': pid, 'start': start, 'inode': self.path.stat().st_ino}

    def run(self, args):
        if hasattr(self, 'owner') and self.proof() != self.owner:
            raise ValueError('Compositor owner changed')
        result = subprocess.run(['hyprctl', '-i', self.signature, *args],
                                capture_output=True, text=True, timeout=8)
        if result.returncode or len(result.stdout) > LIMIT:
            raise ValueError('Hyprland command failed or exceeded output bound')
        return result.stdout

    def inventory(self):
        return json.loads(self.run(['monitors', 'all', '-j']))


class State:
    """Shared lock/recovery boundary, without loading profile stores or history."""
    def __init__(self, root=None):
        self.home = Path(root or os.environ.get('OMABUNTU_STATE_HOME')
                         or Path.home() / '.local/state/omabuntu').absolute()
        # Preserve the legacy lock/pending paths so offline recovery and normal
        # controls cannot bypass each other's transaction exclusion.
        self.directory = private(self.home / 'display-profiles')
        self.pending_path = self.directory / 'pending.json'
        self.text_path = self.home / 'current/text-size.txt'

    @contextlib.contextmanager
    def lock(self):
        private(self.directory, True)
        fd = os.open(self.directory / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

    def pending(self):
        value = read(self.pending_path)
        if value is not None:
            if (not isinstance(value, dict) or set(value) != {'token', 'status', 'deadline'}
                    or not isinstance(value['token'], str)
                    or not re.fullmatch(r'[a-f0-9]{32}', value['token'])
                    or value['status'] not in ('prepared', 'awaiting-confirmation')):
                raise ValueError('Malformed pending monitor transaction; manual recovery required')
            deadline = value['deadline']
            if type(deadline) not in (int, float) or not math.isfinite(deadline) or not 0 <= deadline <= 1e15:
                raise ValueError('Invalid finite numeric field')
        return value

    def idle(self):
        if self.pending():
            raise ValueError('Pending monitor transaction requires Keep, Restore or explicit acknowledgement')

    def text_state(self):
        text_directory(self.home)
        if self.text_path.is_symlink():
            raise ValueError('Symlinked text-size file')
        if not self.text_path.exists():
            return {'existed': False, 'data': '', 'mode': None}
        if (not self.text_path.is_file() or self.text_path.stat().st_uid != os.getuid()
                or self.text_path.stat().st_size > 32):
            raise ValueError('Invalid shell text-size file')
        return {'existed': True, 'data': base64.b64encode(self.text_path.read_bytes()).decode(),
                'mode': self.text_path.stat().st_mode & 0o777}

    def text_size(self):
        state = self.text_state()
        value = int(base64.b64decode(state['data']).decode().strip()) if state['existed'] else 12
        if value not in TEXT_SIZES:
            raise ValueError('Unsupported existing shell text size')
        return value

    def set_text(self, value):
        if type(value) is not int or value not in TEXT_SIZES:
            raise ValueError('Unsupported shell text size')
        with self.lock():
            self.idle()
            # Do not load a profile store or enumerate profile receipts merely
            # to change the normal shell's font size. Keep its exact prior state.
            backup = self.home / 'desktop-actions' / ('text-' + secrets.token_hex(16) + '.json')
            put(backup, {'action': 'text', 'text': self.text_state()})
            atomic(self.text_path, (str(value) + '\n').encode())
        return {'text_size': self.text_size()}
