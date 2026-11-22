"""Closed optional pactl transport for an already-running local PipeWire-Pulse.

No daemon launch, subscription, recording, device graph edit or arbitrary argv.
Native protocol/daemon races after inspection are not an atomic server binding.
"""
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import time

MAX_OUTPUT = 2 * 1024 * 1024
TIMEOUT = 8
PROFILE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:+(), /-]{0,255}\Z')
CARD = re.compile(r'alsa_card\.[A-Za-z0-9_.-]{1,240}\Z')
SERIAL = re.compile(r'[1-9][0-9]{0,19}\Z')


class AudioError(ValueError):
    def __init__(self, code, transaction=None):
        super().__init__(code)
        self.code = code
        self.transaction = transaction


def bounded_read(path, limit):
    with Path(path).open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise AudioError('oversized-input')
    return data


def normal_user():
    if (os.getuid() == 0 or os.geteuid() != os.getuid()
            or os.environ.get('SUDO_USER') or os.environ.get('PKEXEC_UID')):
        raise AudioError('normal-user-required')


def daemon_identity(directory):
    """Compare the live process executable with the installed system binary."""
    executable = '/usr/bin/pipewire-pulse'
    if os.readlink(directory / 'exe') != executable:
        return None
    running, installed = (directory / 'exe').stat(), Path(executable).stat()
    if ((running.st_dev, running.st_ino) != (installed.st_dev, installed.st_ino)
            or installed.st_uid != 0 or not stat.S_ISREG(installed.st_mode)
            or installed.st_mode & 0o022):
        return None
    return {'exe': executable, 'exe_dev': running.st_dev, 'exe_ino': running.st_ino}


def native_context(run_root=Path('/run/user'), proc=Path('/proc')):
    """Read-only listener ownership proof; never connects to or starts a service."""
    normal_user()
    uid = os.getuid()
    if any(os.environ.get(key) for key in ('PULSE_SERVER', 'PULSE_COOKIE', 'PULSE_CLIENTCONFIG', 'PULSE_RUNTIME_PATH')):
        raise AudioError('custom-audio-environment-refused')
    expected_runtime = '/run/user/%s' % uid
    if os.environ.get('XDG_RUNTIME_DIR') not in (None, '', expected_runtime):
        raise AudioError('custom-audio-environment-refused')
    runtime = run_root / str(uid)
    if any(path.is_symlink() for path in (runtime, *runtime.parents)):
        raise AudioError('unsafe-runtime')
    info = runtime.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_mode & 0o077:
        raise AudioError('unsafe-runtime')
    pulse = runtime / 'pulse'
    if pulse.is_symlink() or pulse.stat().st_uid != uid or not pulse.is_dir() or pulse.stat().st_mode & 0o022:
        raise AudioError('unsafe-runtime')
    socket = pulse / 'native'
    info = socket.lstat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != uid:
        raise AudioError('owned-listener-required')
    listeners = []
    for line in bounded_read(proc / 'net/unix', MAX_OUTPUT).decode('utf-8', 'replace').splitlines():
        fields = line.split(maxsplit=7)
        if len(fields) == 8 and fields[7] == str(socket):
            if fields[3] == '00010000' and fields[4] == '0001' and fields[5] == '01' and fields[6].isdigit():
                listeners.append(fields[6])
    if len(listeners) != 1:
        raise AudioError('owned-listener-required')
    matches = []
    entries = list(itertools.islice(proc.iterdir(), 65537))
    if len(entries) > 65536:
        raise AudioError('process-inventory-limit')
    for directory in entries:
        if not directory.name.isdigit():
            continue
        try:
            if directory.is_symlink() or directory.stat().st_uid != uid:
                continue
            identity = daemon_identity(directory)
            if identity is None:
                continue
            fields = bounded_read(directory / 'stat', 4096).decode().rsplit(')', 1)[1].split()
            if len(fields) < 20 or not fields[19].isdigit():
                continue
            fds = list(itertools.islice((directory / 'fd').iterdir(), 16385))
            if len(fds) > 16384:
                continue
            held = False
            for fd in fds:
                try:
                    held = os.readlink(fd) == 'socket:[' + listeners[0] + ']'
                except OSError:
                    continue
                if held:
                    break
            if held:
                matches.append({**identity, 'pid': int(directory.name), 'start': fields[19]})
        except (OSError, ValueError, IndexError):
            continue
    if len(matches) != 1:
        raise AudioError('already-running-owned-server-required')
    return {**matches[0], 'uid': uid, 'socket': str(socket),
            'socket_dev': info.st_dev, 'socket_ino': info.st_ino, 'listener': listeners[0]}


def command(argv):
    """Bound both pipe streams while running one fixed client, never a shell."""
    process = None
    selector = selectors.DefaultSelector()
    output = bytearray()
    errors = 0
    deadline = time.monotonic() + TIMEOUT
    try:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, close_fds=True,
                                   env={'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
                                        'HOME': '/nonexistent', 'XDG_CONFIG_HOME': '/nonexistent'})
        for pipe in (process.stdout, process.stderr):
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AudioError('command-timeout')
            for key, _ in selector.select(remaining):
                try:
                    data = os.read(key.fd, 65536)
                except BlockingIOError:
                    continue
                if not data:
                    selector.unregister(key.fileobj)
                elif key.fileobj is process.stdout:
                    output.extend(data)
                else:
                    errors += len(data)  # Never retain or print native stderr.
                if len(output) > MAX_OUTPUT or errors > 65536:
                    raise AudioError('command-output-limit')
        remaining = max(0, deadline - time.monotonic())
        if process.wait(timeout=remaining):
            raise AudioError('command-failed')
        return bytes(output)
    except subprocess.TimeoutExpired as error:
        raise AudioError('command-timeout') from error
    except OSError as error:
        raise AudioError('command-unavailable') from error
    finally:
        selector.close()
        if process is not None:
            if process.poll() is None:
                process.kill()  # Only this client's PID, never a daemon/group.
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass  # Bounded client cleanup; never chase or kill a daemon.
            for pipe in (process.stdout, process.stderr):
                pipe.close()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AudioError('duplicate-json-key')
        result[key] = value
    return result


def decode(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_OUTPUT:
        raise AudioError('protocol-limit')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(AudioError('invalid-json-number')))
    except (UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, AudioError):
            raise
        raise AudioError('invalid-json') from error


def text(value, limit=256):
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise AudioError('unsupported-schema')
    return value


def integer(value, maximum=2**32 - 1):
    if type(value) is not int or not 0 <= value <= maximum:
        raise AudioError('unsupported-schema')
    return value


def server_info(raw, context):
    if (not isinstance(raw, dict) or raw.get('is_local') != 'yes'
            or raw.get('server_string') != 'unix:' + context['socket']
            or not isinstance(raw.get('server_name'), str)
            or not re.fullmatch(r'PulseAudio \(on PipeWire [A-Za-z0-9.+~_-]+\)', raw['server_name'])
            or not isinstance(raw.get('cookie'), str)
            or not re.fullmatch(r'[a-fA-F0-9]{4}:[a-fA-F0-9]{4}', raw['cookie'])):
        raise AudioError('unsupported-local-server')
    # This is the server-instance magic, NOT an authentication-cookie file.
    return {'instance': hashlib.sha256(raw['cookie'].lower().encode()).hexdigest(),
            'name': text(raw['server_name']), 'version': text(raw.get('server_version'), 128),
            'protocol': integer(raw.get('server_protocol_version'), 65535)}


def card(raw):
    if (not isinstance(raw, dict) or not isinstance(raw.get('name'), str)
            or not CARD.fullmatch(raw['name']) or not isinstance(raw.get('properties'), dict)
            or raw['properties'].get('device.api') != 'alsa'):
        raise AudioError('unadmitted-card')
    serial = raw['properties'].get('object.serial')
    if not isinstance(serial, str) or not SERIAL.fullmatch(serial):
        raise AudioError('missing-card-identity')
    profiles = raw.get('profiles')
    if not isinstance(profiles, dict) or not 1 <= len(profiles) <= 128:
        raise AudioError('unsupported-profiles')
    result = {}
    for name, profile in profiles.items():
        if not PROFILE.fullmatch(name) or not isinstance(profile, dict) or type(profile.get('available')) is not bool:
            raise AudioError('unsupported-profiles')
        result[name] = {'description': text(profile.get('description')),
                        'sinks': integer(profile.get('sinks'), 64),
                        'sources': integer(profile.get('sources'), 64),
                        'priority': integer(profile.get('priority')), 'available': profile['available']}
    active = raw.get('active_profile')
    if not isinstance(active, str) or active not in result:
        raise AudioError('unsupported-active-profile')
    return {'index': integer(raw.get('index')), 'name': raw['name'], 'serial': serial,
            'active_profile': active, 'profiles': result}


class Client:
    """Injection is Python-test-only; the CLI has no endpoint/argv overrides."""
    def __init__(self, runner=command, probe=native_context):
        self.runner = runner
        self.probe = probe

    def context(self):
        try:
            return self.probe()
        except OSError as error:
            raise AudioError('running-server-context-unavailable') from error

    def call(self, args, context):
        if not isinstance(args, list) or not all(isinstance(part, str) for part in args):
            raise AudioError('unadmitted-command')
        allowed = args in (['info'], ['list', 'cards'])
        if not allowed:
            allowed = (len(args) == 3 and args[0] == 'set-card-profile'
                       and bool(CARD.fullmatch(args[1])) and bool(PROFILE.fullmatch(args[2])))
        if not allowed:
            raise AudioError('unadmitted-command')
        if self.context() != context:
            raise AudioError('server-context-changed')
        prefix = ['/usr/bin/pactl', '--server=unix:' + context['socket'], '--client-name=omabuntu-profile-review']
        if args[0] != 'set-card-profile':
            prefix += ['--format=json']
        data = self.runner(prefix + args)
        if self.context() != context:
            raise AudioError('server-context-changed')
        return data

    def inspect(self):
        context = self.context()
        before = server_info(decode(self.call(['info'], context)), context)
        raw = decode(self.call(['list', 'cards'], context))
        after = server_info(decode(self.call(['info'], context)), context)
        if before != after:
            raise AudioError('server-instance-changed')
        if not isinstance(raw, list) or len(raw) > 128:
            raise AudioError('unsupported-cards')
        cards, excluded, seen_ids, seen_names = [], {'unadmitted': 0, 'invalid': 0}, set(), set()
        for entry in raw:
            if not isinstance(entry, dict):
                excluded['invalid'] += 1
                continue
            index, name = entry.get('index'), entry.get('name')
            if type(index) is not int or not isinstance(name, str):
                excluded['invalid'] += 1
                continue
            if index in seen_ids or name in seen_names:
                raise AudioError('ambiguous-card-identity')
            seen_ids.add(index); seen_names.add(name)
            try:
                cards.append(card(entry))
            except AudioError as error:
                excluded['unadmitted' if error.code == 'unadmitted-card' else 'invalid'] += 1
        return {'context': context, 'server': after, 'cards': cards,
                'excluded': excluded, 'partial': excluded['invalid'] > 0}

    def set_profile(self, before, profile):
        context = before['context']
        info = server_info(decode(self.call(['info'], context)), context)
        if info != before['server']:
            raise AudioError('server-instance-changed')
        if self.call(['set-card-profile', before['card']['name'], profile], context).strip():
            raise AudioError('unexpected-mutation-output')
