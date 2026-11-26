#!/usr/bin/env python3
"""One-use session notification admission; no provider/service/process activation.

The grant is local integrity/consent routing, not authentication against arbitrary
same-user code. A path in the environment alone never authorizes a notification
server. No notification payload or history is inspected here.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import stat

import notification_admission as capability

SCOPE = 'omabuntu-notification-session-v1'
MARKER = 'OMABUNTU_NOTIFICATION_SESSION_ADMITTED_V1'
KEYS = {'schema_version', 'scope', 'lifetime', 'bundle', 'release_sha256',
        'capability_sha256', 'session_sha256', 'argv', 'nonce'}


def manager(bundle):
    spec = importlib.util.spec_from_file_location('notification_session_manager', bundle / 'manager.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def session_digest(env):
    keys = ('WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS', 'XDG_RUNTIME_DIR')
    if any(not isinstance(env.get(k), str) or not env[k] for k in keys):
        raise ValueError('Require an explicit compositor/bus session')
    if not re.fullmatch(r'wayland-\d+', env['WAYLAND_DISPLAY']):
        raise ValueError('Require a named Wayland display')
    endpoint = Path(env['XDG_RUNTIME_DIR']) / env['WAYLAND_DISPLAY']
    if endpoint.is_symlink() or not endpoint.is_socket():
        raise ValueError('Require the actual compositor socket')
    identity = endpoint.stat()
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    return hashlib.sha256(json.dumps([boot, identity.st_dev, identity.st_ino,
        env.get('HYPRLAND_INSTANCE_SIGNATURE', ''), *(env[k] for k in keys)]).encode()).hexdigest()


def argv(bundle):
    return [str(bundle / 'runtime/bin/quickshell'), '--no-color', '--path', str(bundle / 'shell/TrialShell.qml')]


def private_json(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('No symlinked grant path')
    s = path.stat()
    if (not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or s.st_nlink != 1
            or stat.S_IMODE(s.st_mode) != 0o600 or s.st_size > 32768):
        raise ValueError('Require owned private bounded grant')
    if path.parent.stat().st_uid != os.getuid() or stat.S_IMODE(path.parent.stat().st_mode) & 0o077:
        raise ValueError('Require private grant directory')
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError('Require grant object')
    return value


def exclusive_json(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def verify_artifact(bundle):
    # The producer verifies the complete artifact before publishing any grant.
    # The consumer checks the pinned release digest before importing its manager.
    capability.verify(bundle)
    manager(bundle).verify_bundle(bundle, installed=True)


def issue(bundle, directory, env):
    bundle = Path(bundle).absolute()
    verify_artifact(bundle)
    directory = Path(directory).absolute()
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise ValueError('No symlinked grant directory')
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    record = {'schema_version': 1, 'scope': SCOPE, 'lifetime': 'session', 'bundle': str(bundle),
              'release_sha256': capability.digest(bundle / 'release.json'),
              'capability_sha256': capability.digest(bundle / capability.DESCRIPTOR),
              'session_sha256': session_digest(env), 'argv': argv(bundle), 'nonce': secrets.token_hex(32)}
    path = directory / 'grant.json'
    exclusive_json(path, record)
    return path


def admit(path, bundle, env, parent_pid=None):
    bundle = Path(bundle).absolute(); record = private_json(path)
    if (set(record) != KEYS or type(record.get('schema_version')) is not int
            or record['schema_version'] != 1 or record.get('scope') != SCOPE
            or record.get('lifetime') != 'session' or record.get('bundle') != str(bundle)
            or record.get('argv') != argv(bundle)
            or not isinstance(record.get('nonce'), str) or not re.fullmatch('[a-f0-9]{64}', record['nonce'])):
        raise ValueError('Grant identity/schema differs')
    if (record['release_sha256'] != capability.digest(bundle / 'release.json')
            or record['capability_sha256'] != capability.digest(bundle / capability.DESCRIPTOR)
            or record['session_sha256'] != session_digest(env)):
        raise ValueError('Grant artifact/session differs')
    verify_artifact(bundle)
    pid = os.getppid() if parent_pid is None else parent_pid
    identity = manager(bundle).identity(pid)
    if not identity or identity['argv'] != record['argv']:
        raise ValueError('Only the exact shell parent may consume the grant')
    claim = {'nonce': record['nonce'], 'pid': pid, 'identity': identity}
    exclusive_json(Path(path).parent / 'claim.json', claim)
    return claim


def main(argv_=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('admit',)); parser.add_argument('grant', type=Path)
    args = parser.parse_args(argv_)
    try:
        admit(args.grant, Path(__file__).absolute().parents[1], os.environ)
    except (OSError, ValueError, KeyError, TypeError):
        # Never report grant values or notification contents.
        print('OMABUNTU_NOTIFICATION_ADMISSION_FAILED')
        return 1
    print(MARKER)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
