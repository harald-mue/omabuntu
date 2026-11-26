#!/usr/bin/env python3
"""Explicit approved session notification switch/recovery, plan-only by default."""
import argparse
import ast
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import time

import native_crash_capture as capture
import notification_admission as capability
import notification_deployment as transaction
import notification_session as session
import notification_state
import user_install as deployment

NAME = 'org.freedesktop.Notifications'
ENV_FILE = 'OMABUNTU_NOTIFICATION_SESSION_FILE'


def command(args):
    return subprocess.run(args, capture_output=True, text=True, timeout=8, check=True).stdout.strip()


def dbus(method, *args, dest='org.freedesktop.DBus', path='/org/freedesktop/DBus'):
    raw = command(['gdbus', 'call', '--session', '--dest', dest, '--object-path', path, '--method', method, *args])
    if raw == '(true,)': return True
    if raw == '(false,)': return False
    return ast.literal_eval(re.sub(r'\buint32\s+', '', raw))[0] if raw != '()' else None


def owner():
    try: return dbus('org.freedesktop.DBus.GetNameOwner', NAME)
    except subprocess.CalledProcessError as error:
        if 'NameHasNoOwner' in error.stderr: return None
        raise


def wait(test, label, seconds=8):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        value = test()
        if value: return value
        time.sleep(.1)
    raise ValueError(label)


def capture_identity(record):
    directory = Path(record['log']).parent / 'native-capture'
    ready = capture.read_receipt(directory / 'ready.json')
    debugger = capture.read_receipt(directory / 'debugger.json')
    supervisor = capture.read_receipt(directory / 'supervisor.json')
    if (not capture.same_process(ready) or ready['pid'] != record['pid']
            or not capture.same_process(supervisor) or not debugger):
        raise ValueError('Capture ownership differs')
    actual = deployment.identity(debugger['pid'])
    expected = ['/usr/bin/gdb', '-nx', '-nh', '-q', '-batch', '-iex', 'set auto-load off',
                '-iex', 'set debuginfod enabled off', '-x', str(directory / 'commands.gdb'),
                '--args', *record['identity']['argv']]
    if (not actual or actual['start_ticks'] != debugger['identity']['start_ticks']
            or actual['argv'] != expected or not capture.traced_by(record['pid'], debugger['pid'])
            or (directory / 'supervisor-finished.json').exists()
            or (directory / 'capture-started.json').exists()):
        raise ValueError('Debugger identity/tracing differs or fatal capture in progress')
    return {'directory': str(directory), 'debugger': {'pid': debugger['pid'], 'identity': actual}, 'supervisor': supervisor}


@contextmanager
def captured_start(manager, expected, grant=None):
    with capture.adapted_spawn(manager, expected) as adapter:
        adapted = manager.subprocess.Popen
        def spawn(args, *a, **kw):
            if list(args) == expected and grant is not None:
                kw['env'] = {**kw['env'], ENV_FILE: str(grant)}
            return adapted(args, *a, **kw)
        manager.subprocess.Popen = spawn
        try: yield adapter
        finally: manager.subprocess.Popen = adapted


class Live:
    def __init__(self, bundle, directory=None):
        self.home = Path.home(); self.root = self.home / '.local/share/omabuntu'
        self.state = self.home / '.local/state/omabuntu'; self.launcher = self.home / '.local/bin/omabuntu'
        self.bundle = Path(bundle).absolute(); self.directory = directory
        self.data = {}; self.adapter = None
        self.reload()

    def reload(self):
        deployment.Installation(self.root, self.state, self.launcher).selected()
        self.manager = capture.load_manager(self.root)
        self.app = self.manager.Installation(self.root, self.state, self.launcher)

    def save(self): deployment.atomic_json(self.directory / 'journal.json', self.data)

    def unit(self):
        text = command(['systemctl', '--user', 'show', 'swaync.service', '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID', '-p', 'UnitFileState', '-p', 'FragmentPath'])
        return dict(line.split('=', 1) for line in text.splitlines())

    def preflight(self):
        self.app.require_settled()
        deployment.verify_bundle(self.bundle); capability.verify(self.bundle)
        self.target = self.app.selected(); self.old = self.app.running()
        if not self.old: raise ValueError('Require the currently owned shell')
        self.old_capture = capture_identity(self.old)
        if not Path('/usr/bin/gdb').is_file(): raise ValueError('GDB unavailable')
        if os.environ.get('XDG_RUNTIME_DIR') != '/run/user/' + str(os.getuid()):
            raise ValueError('Ambiguous runtime directory')
        self.manager.read_hyprland_instances(os.environ['HYPRLAND_INSTANCE_SIGNATURE'], os.environ['WAYLAND_DISPLAY'])
        self.overlay = deployment.read_json(self.bundle / 'native/notification-overlay.json')
        if self.overlay['base_release_sha256'] != capability.digest(self.root / self.target / 'release.json'):
            raise ValueError('Overlay is not derived from the current installed release')
        acceptance = transaction.validate_acceptance(self.bundle)
        profile = capability.load(self.bundle, capability.EVIDENCE['profile'])
        if (acceptance.get('scope') != 'omabuntu-notification-live-prerequisites-v1'
                or acceptance.get('passed') is not True or acceptance.get('sources') != profile['staged']
                or acceptance.get('session_helper_sha256') != capability.digest(self.bundle / 'helpers/notification_session.py')
                or acceptance.get('host_admission_passed') is not True
                or acceptance.get('controller_sha256') != capability.digest(Path(__file__))
                or acceptance.get('transaction_sha256') != capability.digest(Path(transaction.__file__))
                or acceptance.get('capture_sha256') != capability.digest(Path(capture.__file__))):
            raise ValueError('Missing artifact-bound native/host acceptance')
        self.provider = owner()
        if not self.provider: raise ValueError('Require the existing SwayNC owner')
        self.provider_pid = dbus('org.freedesktop.DBus.GetConnectionUnixProcessID', self.provider)
        self.provider_identity = deployment.identity(self.provider_pid)
        if not self.provider_identity or self.provider_identity['argv'] != ['/usr/bin/swaync']:
            raise ValueError('Notification owner is not the exact SwayNC process')
        self.old_unit = self.unit()
        if self.old_unit['ActiveState'] != 'active' or int(self.old_unit['MainPID']) != self.provider_pid:
            raise ValueError('Provider is not owned by the expected active user unit')
        for name in ('org.erikreider.swaync.service', 'org.erikreider.swaync.cc.service'):
            text = (Path('/usr/share/dbus-1/services') / name).read_text()
            if 'SystemdService=swaync.service' not in text or 'Exec=/usr/bin/swaync' not in text:
                raise ValueError('Unreviewed provider activation route')
        bus_pid = dbus('org.freedesktop.DBus.GetConnectionUnixProcessID', 'org.freedesktop.DBus')
        bus_identity = deployment.identity(bus_pid)
        if not bus_identity or not ('--systemd-activation' in bus_identity['argv'] or Path(bus_identity['argv'][0]).name in ('dbus-broker', 'dbus-broker-launch')):
            raise ValueError('Cannot fence direct non-systemd D-Bus activation')
        self.quiet = dbus('org.erikreider.swaync.cc.GetDnd', dest=self.provider, path='/org/erikreider/swaync/cc')
        if type(self.quiet) is not bool: raise ValueError('Unknown DND state')
        self.mask = Path(os.environ['XDG_RUNTIME_DIR']) / 'systemd/user/swaync.service'
        if self.mask.exists() or self.mask.is_symlink(): raise ValueError('Existing runtime unit override; no overwrite')
        self.env = dict(os.environ); self.env.setdefault('DBUS_SESSION_BUS_ADDRESS', 'unix:path=' + os.environ['XDG_RUNTIME_DIR'] + '/bus')
        session.session_digest(self.env)
        self.pre = {'current': self.target, 'previous': self.app.selected('previous'), 'launcher_existed': self.launcher.exists(),
                    'launcher_mode': stat.S_IMODE(self.launcher.stat().st_mode), 'launcher_sha256': capability.digest(self.launcher)}

    def snapshot(self):
        self.directory = deployment.private_directory(self.state / 'notification-migrations' / deployment.stamp())
        self.data = {'scope': 'omabuntu-notification-live-transaction-v1', 'status': 'prepared', 'bundle': str(self.bundle),
                     'bundle_sha256': capability.digest(self.bundle / 'release.json'),
                     'pre': self.pre, 'old': self.old, 'old_capture': self.old_capture, 'provider': self.provider,
                     'provider_pid': self.provider_pid, 'provider_identity': self.provider_identity,
                     'quiet': self.quiet, 'unit': self.old_unit, 'mask': str(self.mask), 'events': []}
        paths = [(self.launcher, 'launcher'), (self.state / 'running.json', 'running-before.json'),
                 (Path(self.old['log']), 'previous-output.log')]
        q = self.state / 'notifications/quiet.json'; self.data['quiet_existed'] = q.exists()
        if q.exists(): notification_state.owned(q); paths.append((q, 'quiet-before.json'))
        self.data['backups'] = []
        for source, name in paths:
            target = self.directory / name; shutil.copy2(source, target)
            self.data['backups'].append({'source': str(source), 'backup': name, 'sha256': capability.digest(source), 'mode': stat.S_IMODE(source.stat().st_mode)})
        shutil.copytree(self.old_capture['directory'], self.directory / 'previous-native-capture')
        self.save()

    def event(self, name): self.data['events'].append(name); self.save()

    def stop_owned_shell(self):
        if self.app.running() != self.old: raise ValueError('Shell changed before stop')
        self.event('stopping-owned-shell'); self.app.stop()
        wait(lambda: not capture.same_process(self.old_capture['supervisor']), 'Previous capture did not stop')
        wait(lambda: subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'quickshell'], capture_output=True, timeout=3).returncode == 1, 'Another Quickshell remains')

    def fence_provider(self):
        self.event('mask-requested')
        command(['systemctl', '--user', 'mask', '--runtime', 'swaync.service'])
        if not self.mask.is_symlink() or os.readlink(self.mask) != '/dev/null': raise ValueError('Runtime activation fence not established')
        self.event('provider-fenced')

    def stop_provider(self):
        if owner() != self.provider or deployment.identity(self.provider_pid) != self.provider_identity:
            raise ValueError('Provider changed before stop')
        self.event('provider-stop-requested'); command(['systemctl', '--user', 'stop', 'swaync.service'])
        wait(lambda: owner() is None, 'Notification name not released')

    def install(self):
        self.event('install-requested'); result = self.app.install(self.bundle)
        self.data['install'] = result; self.save(); self.reload()

    def grant(self):
        deployment.private_directory(self.state / 'notifications')
        q = self.state / 'notifications/quiet.json'
        if q.exists(): notification_state.owned(q)
        self.event('quiet-write-requested'); deployment.atomic_json(q, {'dnd': self.quiet})
        release = self.root / self.app.selected()
        grant = session.issue(release, self.directory / 'grant', self.env)
        self.data.update(grant=str(grant), grant_nonce=session.private_json(grant)['nonce'], grant_bundle=str(release)); self.save()

    def start_captured(self):
        release = self.root / self.app.selected(); expected = session.argv(release)
        self.event('captured-start-requested')
        with captured_start(self.manager, expected, self.data['grant']) as adapter:
            self.adapter = adapter; result = self.app.start(restore_background=False)
        self.data['attempt'] = result; self.save()

    def verify_ready(self):
        record = self.app.running()
        if not record: raise ValueError('New owned shell absent')
        capture_info = capture_identity(record)
        actual = wait(owner, 'No notification owner after startup')
        if dbus('org.freedesktop.DBus.GetConnectionUnixProcessID', actual) != record['pid']:
            raise ValueError('Unexpected notification owner; no takeover allowed')
        release = self.root / self.app.selected()
        raw = command([str(release / 'runtime/bin/quickshell'), 'ipc', '--path', str(release / 'shell/TrialShell.qml'), 'call', 'omabuntuNotificationRole', 'status'])
        ready = json.loads(raw)
        if ready != {'admitted': True, 'ready': True, 'quiet': self.quiet}: raise ValueError('Native readiness/DND differs')
        claim = session.private_json(Path(self.data['grant']).parent / 'claim.json')
        if claim['pid'] != record['pid'] or claim['identity'] != record['identity']: raise ValueError('Session claim differs')
        return {'status': 'live-session-active', 'shell': record, 'capture': capture_info, 'owner': actual, 'readiness': ready}

    def complete(self, result): self.data.update(status='completed', result=result); self.save()
    def record_failure(self, name): self.data.update(status='failed', error=name); self.save()

    def recover(self):
        grant_path = self.data.get('grant')
        if grant_path:
            if Path(grant_path) != self.directory / 'grant/grant.json':
                raise ValueError('Grant is outside the owned transaction')
            proof = session.private_json(Path(grant_path))
            if proof.get('session_sha256'):
                env = dict(os.environ)
                env.setdefault('DBUS_SESSION_BUS_ADDRESS', 'unix:path=/run/user/' + str(os.getuid()) + '/bus')
                if session.session_digest(env) != proof['session_sha256']:
                    raise ValueError('Recovery belongs to a different compositor session')
        for row in self.data.get('backups', []):
            name = Path(row['backup'])
            if name.is_absolute() or len(name.parts) != 1:
                raise ValueError('Unsafe recovery backup path')
            path = self.directory / name
            if path.is_symlink() or capability.digest(path) != row['sha256'] or stat.S_IMODE(path.stat().st_mode) != row['mode']:
                raise ValueError('Recovery backup integrity differs')
        self.reload(); running = self.app.running()
        if running and running != self.data['old']:
            expected_target = 'releases/' + deployment.read_json(self.bundle / 'release.json')['version']
            attempt = self.data.get('attempt') or self.data.get('result', {}).get('shell')
            if self.adapter and self.adapter.child:
                attempt = self.adapter.child.record
            if (running['release'] != expected_target or not attempt
                    or running['pid'] != attempt['pid'] or running['identity'] != attempt['identity']):
                raise ValueError('Unrelated shell; recovery refuses to stop it')
            info = capture_identity(running)
            previous_owner = owner()
            self.app.stop()
            wait(lambda: not self.app.running(), 'Attempt did not stop')
            wait(lambda: not capture.same_process(info['supervisor']), 'Attempt capture did not finish')
            if previous_owner is not None:
                wait(lambda: owner() != previous_owner, 'Attempt notification name was not released')
        if self.adapter and self.adapter.child and capture.same_process(self.adapter.child.record):
            self.adapter.child.terminate()
        grant = self.data.get('grant')
        if grant:
            p = Path(grant)
            if p != self.directory / 'grant/grant.json': raise ValueError('Grant is outside the owned transaction')
            original = session.private_json(p)
            if original.get('nonce') != self.data['grant_nonce'] or original.get('bundle') != self.data['grant_bundle']:
                raise ValueError('Grant changed outside transaction')
            deployment.atomic_json(p, {**original, 'revoked': True})
        # Restore only selectors belonging to this transaction.
        allowed = {self.pre['current'], 'releases/' + deployment.read_json(self.bundle / 'release.json')['version']}
        if (self.app.selected() not in allowed
                or self.app.selected('previous') not in {self.pre['previous'], self.pre['current']}):
            raise ValueError('Selectors changed outside transaction')
        if (self.launcher.is_symlink() or capability.digest(self.launcher) not in {
                self.pre['launcher_sha256'], hashlib.sha256(self.app.bootstrap().encode()).hexdigest()}):
            raise ValueError('Launcher changed outside transaction')
        self.app.restore(self.directory, self.pre); self.reload()
        q = self.state / 'notifications/quiet.json'
        if 'quiet-write-requested' in self.data['events']:
            if q.exists():
                notification_state.owned(q)
                shutil.copy2(q, self.directory / 'quiet-after-attempt.json')
            if self.data['quiet_existed']: shutil.copy2(self.directory / 'quiet-before.json', q)
            elif q.exists(): q.unlink()
        if 'mask-requested' in self.data['events'] and self.mask.is_symlink():
            if os.readlink(self.mask) != '/dev/null': raise ValueError('Runtime fence changed outside transaction')
            command(['systemctl', '--user', 'unmask', '--runtime', 'swaync.service'])
            if self.mask.exists() or self.mask.is_symlink():
                raise ValueError('Runtime activation fence did not restore')
        actual = owner()
        if actual is not None:
            pid = dbus('org.freedesktop.DBus.GetConnectionUnixProcessID', actual)
            identity = deployment.identity(pid)
            if not identity or identity['argv'] != ['/usr/bin/swaync']: raise ValueError('Unknown provider; no competing recovery')
        else:
            command(['systemctl', '--user', 'start', 'swaync.service']); actual = wait(owner, 'Prior provider did not return')
        pid = dbus('org.freedesktop.DBus.GetConnectionUnixProcessID', actual)
        if int(self.unit()['MainPID']) != pid or deployment.identity(pid)['argv'] != ['/usr/bin/swaync']:
            raise ValueError('Recovered provider is not the expected user unit')
        dbus('org.erikreider.swaync.cc.SetDnd', 'true' if self.data['quiet'] else 'false', dest=actual, path='/org/erikreider/swaync/cc')
        if not self.app.running():
            wait(lambda: subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'quickshell'], capture_output=True, timeout=3).returncode == 1, 'Attempt debugger/inferior still present')
            release = self.root / self.app.selected()
            with captured_start(self.manager, session.argv(release)):
                restored = self.app.start(restore_background=False)
            capture_identity(restored)
        self.data.update(status='restored', restored=self.app.running()); self.save()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--apply', action='store_true'); p.add_argument('--recover', type=Path)
    args = p.parse_args(argv); os.umask(0o077)
    if not args.apply:
        print('Plan only: exact owned session switch with prior-provider/debugger recovery; requires --apply')
        return 0
    ops = Live(args.bundle)
    fd = os.open(ops.state / 'control.lock', os.O_RDWR | os.O_NOFOLLOW)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.recover:
            ops.directory = deployment.private_directory(args.recover)
            ops.data = session.private_json(ops.directory / 'journal.json')
            if (ops.data.get('scope') != 'omabuntu-notification-live-transaction-v1'
                    or ops.data.get('bundle') != str(ops.bundle)
                    or ops.data.get('bundle_sha256') != capability.digest(ops.bundle / 'release.json')):
                raise ValueError('Recovery journal/artifact differs')
            ops.pre = ops.data['pre']; ops.mask = Path(ops.data['mask'])
            ops.recover(); result = {'status': ops.data['status']}
        else: result = transaction.switch(ops)
    print(json.dumps({'journal': str(ops.directory), **result}, indent=2)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
