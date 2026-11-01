#!/usr/bin/env python3
"""Local versioned Omabuntu deployment and session control; no service activation.

This file is also shipped as manager.py. All runtime operations use only the
Python standard library and the installed release, never the development tree.
"""
import argparse
import datetime
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
import sys
import time

VERSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z')
GRANT = {'schema_version': 1, 'scope': 'bar-session-v1', 'lifetime': 'session'}


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')


def safe_parents(path):
    """Reject symlinked deployment/state parents, including dangling links."""
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('Parent traversal is not allowed')
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise ValueError('Symlinked deployment path: ' + str(part))
        if part.exists() and not part.is_dir():
            raise ValueError('Not a directory: ' + str(part))
    return path


def private_directory(path):
    path = safe_parents(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError('Require an owned private directory: ' + str(path))
    return path


def read_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError('Expected a bounded regular JSON file: ' + str(path))
    return json.loads(path.read_text())


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.new-' + stamp())
    with temporary.open('x') as stream:
        os.chmod(temporary, 0o600)
        json.dump(value, stream, indent=2)
        stream.write('\n')
    temporary.replace(path)


def file_manifest(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        name = path.relative_to(directory).as_posix()
        if name == 'release.json':
            continue
        if path.is_symlink():
            # The verified stage has one absolute qs alias; packaging makes it relative.
            if name != 'runtime/bin/qs' or os.readlink(path) != 'quickshell':
                raise ValueError('Unapproved bundle symlink: ' + name)
            result[name] = {'link': 'quickshell'}
        elif path.is_file():
            result[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'mode': stat.S_IMODE(path.stat().st_mode)}
        elif not path.is_dir():
            raise ValueError('Special file in release: ' + name)
    return result


SESSION_HELPERS = ('runtime/bin/omasnap', 'helpers/capture_screenshot.py',
                   'helpers/omabuntu_hyprland_window_minimize.py')
SESSION_LOCK_HELPERS = ('helpers/lock_session.py', 'lock/hyprlock.conf')

BASELINE = ('manager.py', 'runtime/bin/quickshell', 'shell/TrialShell.qml',
            'helpers/network_nm.py', 'helpers/display_backend.py', 'helpers/qrcodegen.py',
            'licenses/Omarchy-MIT.txt', 'licenses/Omabuntu-MIT.txt',
            'licenses/Quickshell-LGPL.txt', 'licenses/Quickshell-GPL.txt', 'licenses/cpptrace-MIT.txt')
INCOMING = BASELINE + ('helpers/menu_model.py', 'helpers/menu_common.py', 'helpers/theme_backend.py',
                       'helpers/font_backend.py', 'helpers/background_backend.py', 'helpers/defaults_backend.py', 'helpers/power_actions.py',
                       'helpers/elsewhen_probe.py', 'helpers/capture_screenshot.py', 'helpers/weather_probe.py',
                       'shell/omabuntu-menu.jsonc', 'menu/themes.json')


def verify_bundle(bundle, *, installed=False):
    bundle = safe_parents(bundle)
    meta = read_json(bundle / 'release.json')
    if (not isinstance(meta, dict) or type(meta.get('schema_version')) is not int or meta.get('schema_version') != 1 or meta.get('scope') != 'omabuntu-user-release-v1'
            or not isinstance(meta.get('version'), str) or not VERSION.fullmatch(meta['version'])
            or meta['version'] in ('.', '..') or meta.get('autostart') is not False
            or meta.get('lock_activation') is not False
            or not isinstance(meta.get('files'), dict)):
        raise ValueError('Release identity, scope or integrity differs')
    actual = file_manifest(bundle)
    expected = meta['files']
    if actual != expected:
        differences = []
        for label, names in (
                ('added', actual.keys() - expected.keys()),
                ('missing', expected.keys() - actual.keys()),
                ('changed', {name for name in actual.keys() & expected.keys()
                             if actual[name] != expected[name]})):
            if names:
                # Bounded filenames only: never include file contents or hashes.
                shown = ', '.join(repr(name[:160]) for name in sorted(names)[:5])
                differences.append(label + ': ' + shown + (' ...' if len(names) > 5 else ''))
        raise ValueError('Release identity, scope or integrity differs (' + '; '.join(differences) + ')')
    # Selectors may point at a release packaged before the command menu.
    # A bundle being installed still has to carry the menu and its helpers.
    required = BASELINE if installed else INCOMING
    if any(name not in meta['files'] for name in required):
        raise ValueError('Incomplete release')
    return meta


def parse_hyprctl_instances(stdout):
    """Hyprland 0.56.2 prints a lone ']' when no instance lock is visible yet."""
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if type(parsed) is not list or any(type(item) is not dict for item in parsed):
        return None
    return parsed


def read_hyprland_instances(signature, display, *, attempts=40, pause=0.25, run=None):
    """Poll until the live Hyprland instance is listed.

    Login reaches graphical-session.target before hyprland.lock exists. A
    single parse then aborts autostart, and Option A does not restart it.
    The deadline waits for that lock only; it does not limit shell lifetime.
    """
    runner = run or (lambda: subprocess.run(['hyprctl', 'instances', '-j'], capture_output=True,
                                            text=True, timeout=2, check=False))
    last = None
    for attempt in range(attempts):
        query = runner()
        if query.returncode == 0:
            last = parse_hyprctl_instances(query.stdout)
            if last is not None and any(item.get('instance') == signature and item.get('wl_socket') == display
                                         for item in last):
                return last
        if attempt + 1 < attempts and pause:
            time.sleep(pause)
    if last is None:
        raise ValueError('Hyprland instance list was not ready')
    raise ValueError('Hyprland session environment does not match its live socket')


def identity(pid):
    if type(pid) is not int or pid <= 1:
        return None
    try:
        base = Path('/proc') / str(pid)
        if base.stat().st_uid != os.getuid():
            return None
        text = (base / 'stat').read_text()
        ticks = text[text.rfind(')') + 2:].split()[19]
        args = (base / 'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
        return {'start_ticks': ticks, 'argv': [arg.decode() for arg in args]}
    except (OSError, ValueError, IndexError, UnicodeError):
        return None


class Installation:
    def __init__(self, root, state, launcher):
        self.root = Path(root).absolute()
        self.state = Path(state).absolute()
        self.launcher = Path(launcher).absolute()
        if any(char.isspace() for char in str(self.root)):
            raise ValueError('The reviewed QML helper policy requires a release path without whitespace')
        if (self.root == self.state or self.root in self.state.parents or self.state in self.root.parents
                or self.root in self.launcher.parents or self.state in self.launcher.parents):
            raise ValueError('Release, state and launcher locations must be separate')

    def selected(self, name='current'):
        safe_parents(self.root)
        path = self.root / name
        if not path.is_symlink():
            if path.exists():
                raise ValueError('Release selector is not a symlink')
            return None
        return self.validated_target(os.readlink(path))

    def validated_target(self, target):
        if not isinstance(target, str):
            raise ValueError('Unsafe release selector')
        parts = Path(target).parts
        if len(parts) != 2 or parts[0] != 'releases' or not VERSION.fullmatch(parts[1]) or parts[1] in ('.', '..'):
            raise ValueError('Unsafe release selector')
        verify_bundle(self.root / target, installed=True)
        return target

    def select(self, name, target):
        self.validated_target(target)
        temporary = self.root / ('.' + name + '-' + stamp())
        temporary.symlink_to(target)
        temporary.replace(self.root / name)

    def process_record(self):
        path = self.state / 'running.json'
        return read_json(path) if path.exists() or path.is_symlink() else None

    def running(self):
        record = self.process_record()
        if not isinstance(record, dict) or not isinstance(record.get('identity'), dict):
            return None
        args = record['identity'].get('argv', [])
        try:
            if len(args) != 4 or args[1:3] != ['--no-color', '--path']:
                return None
            binary = Path(args[0]).relative_to(self.root / 'releases')
            shell = Path(args[3]).relative_to(self.root / 'releases')
            if ('..' in binary.parts or '..' in shell.parts or len(binary.parts) != 4 or len(shell.parts) != 3
                    or binary.parts[1:] != ('runtime', 'bin', 'quickshell')
                    or shell.parts[1:] != ('shell', 'TrialShell.qml') or binary.parts[0] != shell.parts[0]):
                return None
        except (TypeError, ValueError):
            return None
        return record if identity(record.get('pid')) == record['identity'] else None

    def bootstrap(self):
        # Paths are Python string literals, never interpolated into shell code.
        return ('#!/usr/bin/python3\nimport os,sys\nfrom pathlib import Path\n'
                'root=Path(' + repr(str(self.root)) + ')\n'
                'manager=root/"current"/"manager.py"\n'
                'if not manager.is_file(): raise SystemExit("No installed Omabuntu release")\n'
                'os.execv(sys.executable,[sys.executable,str(manager),"--root",str(root),"--state",'
                + repr(str(self.state)) + ',"--launcher",' + repr(str(self.launcher)) + ',*sys.argv[1:]])\n')

    def plan(self, bundle):
        meta = verify_bundle(bundle)
        safe_parents(self.root)
        safe_parents(self.state)
        safe_parents(self.launcher.parent)
        current = self.selected()
        if self.launcher.is_symlink() or (self.launcher.exists() and not self.launcher.is_file()):
            raise ValueError('Refusing a symlink/special launcher')
        prestate = {'root_existed': self.root.exists(), 'state_existed': self.state.exists(),
                    'releases_existed': (self.root / 'releases').exists(),
                    'launcher_parent_existed': self.launcher.parent.exists(),
                    'launcher_existed': self.launcher.exists(), 'previous': self.selected('previous')}
        if self.launcher.exists():
            prestate['launcher_mode'] = stat.S_IMODE(self.launcher.stat().st_mode)
            prestate['launcher_sha256'] = hashlib.sha256(self.launcher.read_bytes()).hexdigest()
        return {'version': meta['version'], 'current': current, 'prestate': prestate,
                'release_path': str(self.root / 'releases' / meta['version']),
                'launcher': str(self.launcher), 'state': str(self.state),
                'operations': ['verify and copy immutable version', 'back up selectors and launcher',
                               'switch current version', 'write standalone launcher'],
                'starts_process': False, 'autostart': False, 'lock_activation': False}

    def snapshot(self, operation):
        backup = private_directory(self.state / 'transactions' / stamp())
        launcher = self.launcher
        if launcher.is_symlink() or (launcher.exists() and not launcher.is_file()):
            raise ValueError('Refusing nonregular launcher backup')
        pre = {'operation': operation, 'current': self.selected(), 'previous': self.selected('previous'),
               'launcher_existed': launcher.exists(), 'launcher_mode': None, 'status': 'prepared'}
        if launcher.exists():
            pre['launcher_mode'] = stat.S_IMODE(launcher.stat().st_mode)
            data = launcher.read_bytes()
            pre['launcher_sha256'] = hashlib.sha256(data).hexdigest()
            (backup / 'launcher').write_bytes(data)
            os.chmod(backup / 'launcher', 0o600)
            if hashlib.sha256((backup / 'launcher').read_bytes()).digest() != hashlib.sha256(data).digest():
                raise ValueError('Launcher backup verification failed')
        atomic_json(backup / 'transaction.json', pre)
        return backup, pre

    def restore(self, backup, pre):
        if type(pre.get('launcher_existed')) is not bool or any(key not in pre for key in ('current', 'previous')):
            raise ValueError('Invalid deployment backup record')
        for key in ('current', 'previous'):
            if pre[key] is not None:
                self.validated_target(pre[key])
        if pre['launcher_existed']:
            saved = backup / 'launcher'
            if saved.is_symlink() or hashlib.sha256(saved.read_bytes()).hexdigest() != pre['launcher_sha256']:
                raise ValueError('Launcher backup integrity differs; no restore performed')
        for key in ('current', 'previous'):
            path = self.root / key
            if pre[key] is None:
                path.unlink(missing_ok=True)
            else:
                self.select(key, pre[key])
        if pre['launcher_existed']:
            temp = self.launcher.with_name('.omabuntu-restore-' + stamp())
            temp.write_bytes((backup / 'launcher').read_bytes())
            temp.chmod(pre['launcher_mode'])
            temp.replace(self.launcher)
        else:
            self.launcher.unlink(missing_ok=True)

    def pending(self):
        directory = self.state / 'transactions'
        safe_parents(directory)
        pending = []
        for path in sorted(directory.glob('*/transaction.json')):
            record = read_json(path)
            if not isinstance(record, dict):
                raise ValueError('Invalid transaction journal')
            if record.get('status') == 'prepared':
                pending.append((path, record))
        return pending

    def require_settled(self):
        if self.pending():
            raise ValueError('Interrupted deployment found; review its journal and use recover --apply first')

    def recover(self):
        if self.running():
            raise ValueError('Stop the installed bar before deployment recovery')
        pending = self.pending()
        if len(pending) != 1:
            raise ValueError('Recovery requires exactly one prepared transaction; review state manually')
        path, pre = pending[0]
        allowed = {None, pre.get('current'), pre.get('previous'), pre.get('installed_target')}
        if self.selected() not in allowed or self.selected('previous') not in allowed:
            raise ValueError('Selectors changed after the interruption; no automatic recovery')
        if self.launcher.exists():
            content = self.launcher.read_bytes()
            if (self.launcher.is_symlink() or (content != self.bootstrap().encode()
                    and hashlib.sha256(content).hexdigest() != pre.get('launcher_sha256'))):
                raise ValueError('Launcher changed after the interruption; no automatic recovery')
        self.restore(path.parent, pre)
        pre['status'] = 'recovered'
        atomic_json(path, pre)
        return {'status': 'prestate-restored', 'backup': str(path.parent), 'retained_releases': True}

    def install(self, bundle, state_preexisted=None):
        plan = self.plan(bundle)
        self.require_settled()
        if state_preexisted is not None:
            plan['prestate']['state_existed'] = state_preexisted
        if self.running():
            raise ValueError('Stop the installed bar before changing versions')
        private_directory(self.root)
        private_directory(self.state)
        (self.root / 'releases').mkdir(mode=0o700, exist_ok=True)
        safe_parents(self.root / 'releases')
        self.launcher.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        destination = Path(plan['release_path'])
        if destination.exists():
            if verify_bundle(destination) != verify_bundle(bundle):
                raise ValueError('Version already exists with different contents')
        else:
            temporary = self.root / ('releases/.incoming-' + stamp())
            try:
                shutil.copytree(bundle, temporary, symlinks=True)
                verify_bundle(temporary)
                temporary.rename(destination)
            except BaseException:
                if temporary.exists():
                    shutil.rmtree(temporary)  # Only this call's unselected staging tree.
                raise
        target = 'releases/' + plan['version']
        if plan['current'] == target and self.launcher.exists() and self.launcher.read_text() == self.bootstrap():
            return {'status': 'already-installed', **plan}
        backup, pre = self.snapshot('install')
        pre['installed_target'] = target
        pre['locations_before'] = plan['prestate']
        atomic_json(backup / 'transaction.json', pre)
        try:
            temp = self.launcher.with_name('.omabuntu-install-' + stamp())
            temp.write_text(self.bootstrap())
            temp.chmod(0o755)
            temp.replace(self.launcher)
            if pre['current'] and pre['current'] != target:
                self.select('previous', pre['current'])
            self.select('current', target)
            pre['status'] = 'completed'
            atomic_json(backup / 'transaction.json', pre)
        except BaseException:
            self.restore(backup, pre)
            pre['status'] = 'restored-after-failure'
            atomic_json(backup / 'transaction.json', pre)
            raise
        return {'status': 'installed-not-started', 'backup': str(backup), **plan,
                'previous_current': plan['current'], 'current': target}

    def rollback(self):
        self.require_settled()
        if self.running():
            raise ValueError('Stop the installed bar before rollback')
        if not self.launcher.is_file() or self.launcher.is_symlink() or self.launcher.read_text() != self.bootstrap():
            raise ValueError('Launcher changed outside this installer; refusing to overwrite it')
        target = self.selected('previous')
        if target is None:
            # First-install rollback restores the real launcher pre-state and
            # removes only selectors/launcher introduced by that installation.
            current = self.selected()
            transactions = sorted((self.state / 'transactions').glob('*/transaction.json'), reverse=True)
            for path in transactions:
                pre = read_json(path)
                if (pre.get('operation') == 'install' and pre.get('status') == 'completed'
                        and pre.get('current') is None and pre.get('installed_target') == current):
                    self.restore(path.parent, pre)
                    pre['status'] = 'rolled-back'
                    atomic_json(path, pre)
                    return {'status': 'first-install-restored', 'backup': str(path.parent), 'retained_releases': True}
            raise ValueError('No previous verified release or first-install backup')
        backup, pre = self.snapshot('rollback')
        try:
            self.select('current', target)
            if pre['current']:
                self.select('previous', pre['current'])
            pre['status'] = 'completed'
            atomic_json(backup / 'transaction.json', pre)
        except BaseException:
            self.restore(backup, pre)
            pre['status'] = 'restored-after-failure'
            atomic_json(backup / 'transaction.json', pre)
            raise
        return {'status': 'rolled-back-not-started', 'current': target, 'backup': str(backup)}

    def lock(self):
        """One explicit manual lock; never autostart, idle or a supervisor."""
        self.require_settled()
        target = self.selected()
        if target is None:
            raise ValueError('No installed release')
        release = self.root / target
        helper = release / 'helpers/lock_session.py'
        if helper.is_symlink() or not helper.is_file():
            raise ValueError('This release does not include the reviewed lock helper')
        result = subprocess.run([sys.executable, str(helper), '--release', str(release), '--apply'],
                                env={**os.environ, 'OMABUNTU_STATE_HOME': str(self.state),
                                     'PYTHONDONTWRITEBYTECODE': '1'}, check=False)
        if result.returncode:
            raise ValueError('Lock helper reported failure; see the private lock log')
        return {'status': 'lock-session-finished', 'release': target}

    def restore_wallpaper(self, release):
        """Best-effort recorded-background restore (plan 020); never blocks.

        The packaged helper applies the recorded still per connected monitor
        through the reviewed hyprpaper path. Any failure is a printed note,
        not a failed start."""
        helper = release / 'helpers' / 'background_backend.py'
        if helper.is_symlink() or not helper.is_file():
            return
        try:
            result = subprocess.run([sys.executable, str(helper), 'restore'],
                                    env={**os.environ, 'OMABUNTU_STATE_HOME': str(self.state),
                                         'PYTHONDONTWRITEBYTECODE': '1'},
                                    capture_output=True, text=True, timeout=20, check=False)
        except (OSError, subprocess.SubprocessError):
            print('Wallpaper restore: helper failed to run', flush=True)
            return
        summary = (result.stdout or result.stderr or '').strip().splitlines()
        print('Wallpaper restore: ' + (summary[-1] if summary else 'exit ' + str(result.returncode)), flush=True)

    def start(self, *, restore_background=True):
        self.require_settled()
        running = self.running()
        if running:
            return {'status': 'running', 'pid': running['pid']}
        target = self.selected()
        if target is None:
            raise ValueError('No installed release')
        release = self.root / target
        # Never select another compositor just because a GNOME process can see it.
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower().split(':')
        signature = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
        display = os.environ.get('WAYLAND_DISPLAY', '')
        runtime_dir = Path('/run/user') / str(os.getuid())
        if ('hyprland' not in desktop or not signature or not re.fullmatch(r'wayland-\d+', display)
                or not (runtime_dir / display).is_socket()):
            raise ValueError('Start from the existing Hyprland session, not GNOME or an ambiguous environment')
        read_hyprland_instances(signature, display)
        other = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'quickshell'], capture_output=True, timeout=5, check=False)
        if other.returncode != 1:
            raise ValueError('Another Quickshell exists or lookup failed; stop the trial explicitly first')
        # The private parent protects legacy current/ directories whose modes
        # were inherited from a menu backend. Do not chmod existing preferences.
        # New directories are private; symlinks and foreign ownership still fail.
        private_directory(self.state)
        current = safe_parents(self.state / 'current')
        current.mkdir(mode=0o700, exist_ok=True)
        if current.stat().st_uid != os.getuid():
            raise ValueError('Require an owned state directory: ' + str(current))
        if restore_background:
            self.restore_wallpaper(release)
        logdir = private_directory(self.state / 'runs' / stamp())
        env = {key: os.environ[key] for key in ('HOME', 'USER', 'LOGNAME', 'LANG', 'DBUS_SESSION_BUS_ADDRESS',
               'XDG_DATA_HOME', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_DIRS', 'XDG_STATE_HOME') if key in os.environ}
        env.update(PATH='/usr/local/bin:/usr/bin:/bin:/snap/bin', XDG_RUNTIME_DIR=str(runtime_dir),
                   XDG_CURRENT_DESKTOP='Hyprland', XDG_SESSION_TYPE='wayland', WAYLAND_DISPLAY=display,
                   HYPRLAND_INSTANCE_SIGNATURE=signature, QT_QPA_PLATFORM='wayland',
                   QML_IMPORT_PATH=str(release / 'runtime/lib/qt6/qml') + ':' + str(release / 'shell'),
                   OMABUNTU_CLOCK_TRIAL=json.dumps(GRANT), QS_DISABLE_CRASH_HANDLER='1',
                   OMABUNTU_NETWORK_HELPER=str(release / 'helpers/network_nm.py'),
                   OMABUNTU_DISPLAY_HELPER=str(release / 'helpers/display_backend.py'),
                   OMABUNTU_DOCK_HELPER=str(release / 'helpers/dock_state.py'),
                   OMABUNTU_KEYBINDINGS_HELPER=str(release / 'helpers/keybindings_menu.py'),
                   OMABUNTU_MENU_HELPER=str(release / 'helpers/menu_model.py'),
                   OMABUNTU_MENU_DEFINITIONS=str(release / 'shell/omabuntu-menu.jsonc'),
                   OMABUNTU_MENU_THEMES=str(release / 'menu/themes.json'),
                   OMABUNTU_ELSEWHEN_HELPER=str(release / 'helpers/elsewhen_probe.py'),
                   OMABUNTU_WEATHER_HELPER=str(release / 'helpers/weather_probe.py'),
                   OMABUNTU_ELSEWHEN_DIR=str(release / 'shell/Elsewhen'),
                   OMABUNTU_STATE_HOME=str(self.state), PYTHONDONTWRITEBYTECODE='1')
        bundled_capture = release / 'runtime/bin/omasnap'
        if bundled_capture.is_file() and not bundled_capture.is_symlink():
            env['OMABUNTU_OMASNAP'] = str(bundled_capture)
        env.setdefault('DBUS_SESSION_BUS_ADDRESS', 'unix:path=' + str(runtime_dir / 'bus'))
        args = [str(release / 'runtime/bin/quickshell'), '--no-color', '--path', str(release / 'shell/TrialShell.qml')]
        with (logdir / 'output.log').open('x') as stream:
            child = subprocess.Popen(args, env=env, stdin=subprocess.DEVNULL, stdout=stream,
                                     stderr=subprocess.STDOUT, start_new_session=True)
        record = {'pid': child.pid, 'identity': identity(child.pid), 'log': str(logdir / 'output.log'),
                  'release': target, 'lifetime': 'session', 'autostart': False}
        try:
            if record['identity'] is None:
                raise ValueError('Could not establish the new process identity')
            atomic_json(self.state / 'running.json', record)
        except BaseException:
            child.terminate()  # This Popen child only, never a discovered process.
            raise
        ready_since = None
        for _ in range(50):
            text = (logdir / 'output.log').read_text(errors='replace')
            bad = ('TypeError:', 'ReferenceError:', 'Binding loop', 'OMABUNTU_TRIAL_COMPONENT_FAILED',
                   'OMABUNTU_TRIAL_CREATE_FAILED', 'OMABUNTU_TRIAL_APPS_FAILED', 'OMABUNTU_TRIAL_DOCK_FAILED',
                   'OMABUNTU_TRIAL_KEYS_FAILED', 'OMABUNTU_TRIAL_KEYS_CREATE_FAILED',
                   'OMABUNTU_TRIAL_MENU_FAILED', 'OMABUNTU_TRIAL_MENU_CREATE_FAILED',
                   'OMABUNTU_TRIAL_PICKER_FAILED', 'OMABUNTU_TRIAL_PICKER_CREATE_FAILED',
                   'Unable to assign', 'Cannot assign')
            diagnostics = re.search(r'^\s*(?:ERROR|FATAL|CRITICAL)\b', text, re.MULTILINE)
            if child.poll() is not None or diagnostics or any(marker in text for marker in bad):
                if child.poll() is None:
                    child.terminate()
                raise ValueError('Installed bar startup failed; inspect ' + record['log'])
            if 'Configuration Loaded' in text and 'OMABUNTU_BAR_SESSION_NO_EXPIRY' in text:
                if ready_since is None:
                    ready_since = time.monotonic()
                if time.monotonic() - ready_since >= 0.5:
                    return {'status': 'running', **record}
            time.sleep(0.1)
        self.stop()
        raise ValueError('Startup was not confirmed; own process stopped, log: ' + record['log'])

    def stop(self):
        record = self.running()
        if record is None:
            return {'status': 'not-running'}
        os.kill(record['pid'], signal.SIGTERM)
        for _ in range(40):
            if self.running() is None:
                return {'status': 'stopped', 'applications_untouched': True}
            time.sleep(0.1)
        raise ValueError('Own bar did not stop; no forced kill or session stop performed')


def defaults():
    home = Path.home()
    data = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
    state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state'))
    if not data.is_absolute() or not state.is_absolute():
        raise ValueError('XDG directories must be absolute')
    return data / 'omabuntu', state / 'omabuntu', home / '.local/bin/omabuntu'


def main(argv=None):
    if os.getuid() == 0:
        raise ValueError('User installation must not be run as root or with sudo')
    root, state, launcher = defaults()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=root)
    parser.add_argument('--state', type=Path, default=state)
    parser.add_argument('--launcher', type=Path, default=launcher)
    parser.add_argument('action', choices=('plan', 'install', 'verify', 'rollback', 'recover', 'start', 'stop', 'status', 'lock'))
    parser.add_argument('bundle', type=Path, nargs='?')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    if args.action in ('plan', 'install') and args.bundle is None:
        parser.error('plan/install requires a bundle directory')
    if args.action not in ('plan', 'install') and args.bundle is not None:
        parser.error('This action takes no bundle')
    install = Installation(args.root, args.state, args.launcher)
    os.umask(0o077)
    if args.action == 'plan' or (args.action == 'install' and not args.apply):
        result = install.plan(args.bundle)
    elif args.action in ('status', 'verify'):
        safe_parents(install.state)
        target = install.selected()
        if args.action == 'verify' and target is None:
            raise ValueError('No installed release to verify')
        record = install.running()
        result = {'current': target, 'status': 'running' if record else 'not-running', 'pid': record['pid'] if record else None}
    else:
        if args.action in ('rollback', 'recover', 'lock') and not args.apply:
            raise ValueError('Rollback/recovery/lock requires --apply; no change made')
        state_preexisted = install.state.exists()
        private_directory(install.state)
        fd = os.open(install.state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if args.action == 'install':
                result = install.install(args.bundle, state_preexisted=state_preexisted)
            elif args.action == 'rollback':
                result = install.rollback()
            elif args.action == 'recover':
                result = install.recover()
            elif args.action == 'lock':
                result = install.lock()
            elif args.action == 'start':
                result = install.start()
            else:
                result = install.stop()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
