#!/usr/bin/env python3
"""Explicit session-only native capture; never attach or alter an installed release.

The manager still owns the real Quickshell PID. Only its exact spawn is adapted;
all preflight subprocesses and ordinary status/stop behavior remain unchanged.
"""
import argparse
from contextlib import contextmanager
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import user_install as deployment

FATAL_SIGNALS = ('SIGSEGV', 'SIGABRT', 'SIGBUS', 'SIGILL', 'SIGFPE', 'SIGSYS')
MAX_THREADS = 64
MAX_FRAMES = 64
MAX_TRACE_BYTES = 1_000_000


def gdb_script(directory):
    """Fixed commands: no expression evaluation, locals, arguments or memory dumps."""
    directory = str(Path(directory).absolute())
    settings = '''set pagination off
set confirm off
set verbose off
set debuginfod enabled off
set auto-load off
set startup-with-shell off
set disable-randomization off
set may-call-functions off
set follow-fork-mode parent
set detach-on-fork on
set print frame-arguments none
set print entry-values no
set print frame-info location-and-address
set print raw-values on
set print thread-events off
set backtrace limit 64
handle SIGPIPE nostop noprint pass
handle SIGTERM nostop noprint pass
handle SIGINT nostop noprint pass
'''
    body = '''import gdb, json, os, pathlib, time
base = pathlib.Path(DIRECTORY)
def save(name, value):
    target = base / name
    temporary = target.with_suffix(target.suffix + '.new')
    temporary.write_text(json.dumps(value) + '\\n')
    temporary.replace(target)
last_signal = None
exited = False
def stopped(event):
    global last_signal
    last_signal = event.stop_signal if isinstance(event, gdb.SignalEvent) else None
def finished(event):
    global exited
    exited = True
try:
    gdb.execute('starti', to_string=True)
    inferior = gdb.selected_inferior()
    save('inferior.json', {'pid': inferior.pid})
    gdb.events.stop.connect(stopped)
    gdb.events.exited.connect(finished)
    while not exited and inferior.is_valid() and inferior.pid:
        last_signal = None
        gdb.execute('continue', to_string=True)
        if last_signal in FATALS:
            save('capture-started.json', {'signal': last_signal})
            lines = ['NATIVE_STACK_CAPTURE_V1', 'signal=' + last_signal]
            threads = inferior.threads()
            for index, thread in enumerate(threads[:MAXTHREADS]):
                thread.switch()
                lines.append('THREAD ' + str(index + 1))
                try:
                    lines.append(gdb.execute('backtrace -no-filters -frame-arguments none -entry-values no -frame-info location-and-address MAXFRAMES', to_string=True))
                except gdb.error:
                    lines.append('STACK_UNAVAILABLE')
            text = '\\n'.join(lines).encode('utf-8', errors='replace')
            with (base / 'backtrace.txt').open('xb') as stream:
                stream.write(text[:MAXBYTES])
            save('capture.json', {'signal':last_signal, 'threads_seen':len(threads),
                 'threads_captured':min(len(threads), MAXTHREADS), 'frame_limit':MAXFRAMES,
                 'byte_limit':MAXBYTES, 'truncated_bytes':len(text)>MAXBYTES})
            gdb.execute('kill', to_string=True)
            break
    save('gdb-finished.json', {'fatal_signal':last_signal if last_signal in FATALS else None})
except BaseException:
    save('gdb-failed.json', {'status':'debugger-command-failed'})
finally:
    try:
        if gdb.selected_inferior().pid:
            gdb.execute('kill', to_string=True)
    except gdb.error:
        pass
'''
    body = (body.replace('DIRECTORY', repr(directory)).replace('FATALS', repr(FATAL_SIGNALS))
            .replace('MAXTHREADS', str(MAX_THREADS)).replace('MAXFRAMES', str(MAX_FRAMES))
            .replace('MAXBYTES', str(MAX_TRACE_BYTES)))
    return settings + 'python\n' + body + '\nend\nquit\n'


def read_receipt(path):
    return deployment.read_json(path) if path.exists() else None


def same_process(record):
    return bool(isinstance(record, dict) and isinstance(record.get('identity'), dict)
                and deployment.identity(record.get('pid')) == record['identity'])


def traced_by(pid, debugger_pid):
    try:
        values = dict(line.split(':', 1) for line in
                      (Path('/proc') / str(pid) / 'status').read_text().splitlines() if ':' in line)
        return int(values['PPid']) == debugger_pid and int(values['TracerPid']) == debugger_pid
    except (OSError, ValueError, KeyError):
        return False


def signal_owned(record, sig):
    if same_process(record):
        os.kill(record['pid'], sig)
        return True
    return False


def supervise(directory):
    """Own GDB and reap it; the capture deadline starts only at a fatal stop."""
    os.umask(0o077)
    import resource
    _, hard = resource.getrlimit(resource.RLIMIT_CORE)
    resource.setrlimit(resource.RLIMIT_CORE, (0, hard))
    directory = deployment.private_directory(directory)
    expected = read_receipt(directory / 'expected.json')
    args = expected['argv']
    (directory / 'commands.gdb').write_text(gdb_script(directory))
    command = ['/usr/bin/gdb', '-nx', '-nh', '-q', '-batch',
               '-iex', 'set auto-load off', '-iex', 'set debuginfod enabled off',
               '-x', str(directory / 'commands.gdb'), '--args', *args]
    debugger = subprocess.Popen(command, stdin=subprocess.DEVNULL)
    debug_identity = {'pid': debugger.pid, 'identity': deployment.identity(debugger.pid)}
    deployment.atomic_json(directory / 'debugger.json', debug_identity)
    owned = None
    capture_since = None
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, stop)
    started = time.monotonic()
    status = 'debugger-exited'
    try:
        while debugger.poll() is None:
            receipt = read_receipt(directory / 'inferior.json')
            if owned is None and receipt:
                ident = deployment.identity(receipt.get('pid'))
                if ident and ident['argv'] == args and traced_by(receipt['pid'], debugger.pid):
                    owned = {'pid': receipt['pid'], 'identity': ident}
                    deployment.atomic_json(directory / 'ready.json', owned)
            if owned is None and time.monotonic() - started > 10:
                status = 'startup-timeout'
                break
            if (directory / 'capture-started.json').exists():
                if capture_since is None:
                    capture_since = time.monotonic()
                elif time.monotonic() - capture_since > 15:
                    status = 'capture-timeout'
                    break
            if stopping:
                status = 'supervisor-stopped'
                break
            time.sleep(0.05)
    finally:
        # No arbitrary PID discovery or process-group signalling. Only the
        # exact child identity handed off by our GDB may be terminated here.
        if debugger.poll() is None:
            signal_owned(owned, signal.SIGKILL)
            debugger.terminate()
            try:
                debugger.wait(timeout=3)
            except subprocess.TimeoutExpired:
                debugger.kill()
                debugger.wait(timeout=3)
        signal_owned(owned, signal.SIGKILL)
        deployment.atomic_json(directory / 'supervisor-finished.json',
                               {'status': status, 'debugger_returncode': debugger.returncode})
    return 0 if (directory / 'gdb-finished.json').exists() else 1


class CaptureChild:
    """The minimal Popen contract used by the unchanged manager's start method."""
    def __init__(self, supervisor, record, directory):
        self.supervisor = supervisor
        self.record = record
        self.directory = directory
        self.pid = record['pid']

    def poll(self):
        if same_process(self.record) and self.supervisor.poll() is None:
            return None
        return self.supervisor.poll() if self.supervisor.poll() is not None else 1

    def terminate(self):
        signal_owned(self.record, signal.SIGTERM)
        self.supervisor.terminate()
        try:
            self.supervisor.wait(timeout=5)
        except subprocess.TimeoutExpired:
            raise ValueError('Diagnostic supervisor did not finish; inspect its private receipts')


class SpawnAdapter:
    def __init__(self, expected, original):
        self.expected = expected
        self.original = original
        self.used = False
        self.child = None

    def __call__(self, args, *positional, **kwargs):
        if args != self.expected:
            return self.original(args, *positional, **kwargs)
        if self.used or positional:
            raise ValueError('Diagnostic spawn must occur exactly once')
        self.used = True
        stream = kwargs['stdout']
        directory = deployment.private_directory(Path(stream.name).parent / 'native-capture')
        deployment.atomic_json(directory / 'expected.json', {'argv': args})
        environment = dict(kwargs['env'])
        environment['DEBUGINFOD_URLS'] = ''
        supervisor = self.original(['/usr/bin/python3', '-B', str(Path(__file__).resolve()),
                                    '_supervise', str(directory)], env=environment,
                                   stdin=subprocess.DEVNULL, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        deployment.atomic_json(directory / 'supervisor.json',
                               {'pid': supervisor.pid, 'identity': deployment.identity(supervisor.pid)})
        try:
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline and supervisor.poll() is None:
                record = read_receipt(directory / 'ready.json')
                if record and same_process(record) and record['identity']['argv'] == args:
                    self.child = CaptureChild(supervisor, record, directory)
                    return self.child
                time.sleep(0.05)
            raise ValueError('GDB inferior handoff failed; inspect ' + str(directory))
        except BaseException:
            if supervisor.poll() is None:
                supervisor.terminate()
                supervisor.wait(timeout=5)
            raise


@contextmanager
def adapted_spawn(manager, expected):
    # The short, single-threaded startup section delegates every other spawn,
    # including manager subprocess.run probes, to the original Popen.
    original = manager.subprocess.Popen
    adapter = SpawnAdapter(expected, original)
    manager.subprocess.Popen = adapter
    try:
        yield adapter
    finally:
        manager.subprocess.Popen = original


def load_manager(root):
    path = root / 'current/manager.py'
    spec = importlib.util.spec_from_file_location('installed_capture_manager', path)
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    return manager


def activate():
    """Explicitly approved stop/start; no install, wallpaper or autostart change."""
    os.umask(0o077)
    home = Path.home()
    root = home / '.local/share/omabuntu'
    state = home / '.local/state/omabuntu'
    manager = load_manager(root)
    app = manager.Installation(root, state, home / '.local/bin/omabuntu')
    fd = os.open(state / 'control.lock', os.O_RDWR | os.O_NOFOLLOW)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        app.require_settled()
        target = app.selected()
        if target is None:
            raise ValueError('No verified installed release')
        release = root / target
        expected = [str(release / 'runtime/bin/quickshell'), '--no-color', '--path',
                    str(release / 'shell/TrialShell.qml')]
        previous = app.running()
        if not previous:
            raise ValueError('Require the currently owned running shell before diagnostic restart')
        status = (Path('/proc') / str(previous['pid']) / 'status').read_text()
        if not any(line.split() == ['TracerPid:', '0'] for line in status.splitlines()):
            raise ValueError('The owned shell is already traced; do not stack diagnostic launchers')
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower().split(':')
        signature = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
        display = os.environ.get('WAYLAND_DISPLAY', '')
        if ('hyprland' not in desktop or not signature
                or not manager.re.fullmatch(r'wayland-\d+', display)
                or not (Path('/run/user') / str(os.getuid()) / display).is_socket()):
            raise ValueError('Require the unambiguous current Hyprland session before stopping')
        manager.read_hyprland_instances(signature, display)
        if not Path('/usr/bin/gdb').is_file():
            raise ValueError('GDB is unavailable; no stop performed')
        reportdir = deployment.private_directory(Path(__file__).resolve().parents[1] /
                                                'work/crash-capture-169' / deployment.stamp())
        import shutil
        for name in ('running.json', 'control.lock'):
            shutil.copy2(state / name, reportdir / name)
        shutil.copy2(previous['log'], reportdir / 'previous-output.log')
        deployment.atomic_json(reportdir / 'prestate.json',
                               {'selected': target, 'previous': previous, 'restore_background': False})
        app.stop()
        try:
            with adapted_spawn(manager, expected) as adapter:
                result = app.start(restore_background=False)
            if not adapter.child or app.running() is None:
                raise ValueError('Diagnostic child identity was not confirmed')
            result['native_capture'] = str(adapter.child.directory)
            deployment.atomic_json(reportdir / 'result.json', result)
        except BaseException:
            if 'adapter' in locals() and adapter.child:
                adapter.child.terminate()
            app.stop()
            recovery = app.start(restore_background=False)
            deployment.atomic_json(reportdir / 'recovery.json', recovery)
            raise
    print(json.dumps({'backup': str(reportdir), **result}, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', '_supervise'))
    parser.add_argument('directory', nargs='?', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    if args.action == '_supervise':
        if args.directory is None:
            parser.error('Supervisor requires its private receipt directory')
        return supervise(args.directory)
    if not args.apply:
        print('Plan only: owner-approved session diagnostic restart requires start --apply.')
        return 0
    if args.directory is not None:
        parser.error('Live start does not accept an arbitrary receipt directory')
    activate()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
