"""Next-login activation files only: plugin, titlebar, wallpaper, optional unit.

Never starts Hyprland, hyprpaper, the shell, or a plugin. Login enablement is a
separate explicit choice and does not use systemctl start.
"""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

import build_plugin
import install as guided
import session_config
import user_install
import wallpaper_record

ROOT = Path(__file__).resolve().parents[1]
UNIT = 'omabuntu-shell.service'
WAIT = 'omabuntu-shell-wait.py'
SYSTEMCTL = '/usr/bin/systemctl'


def paths_for(home, app, config):
    user = config / 'systemd/user'
    hypr = config / 'hypr'
    return {
        'activation': hypr / 'omabuntu-activation.lua',
        'titlebars': hypr / 'omabuntu-titlebars.lua',
        'wallpaper': hypr / 'hyprpaper.conf',
        'unit': user / UNIT,
        'wait': user / WAIT,
        'receipt': app.state / 'session-activation.json',
    }


def render(root, app, selected, plugin):
    release = app.root / selected
    library = release / 'native/hyprbars.so'
    titlebar_path = plugin['titlebar_path']
    minimize = shlex.join(['/usr/bin/env', 'PYTHONDONTWRITEBYTECODE=1', '/usr/bin/python3',
                           str(release / 'helpers/omabuntu_hyprland_window_minimize.py')])
    template = root / 'config/hypr/titlebars.lua.in'
    user_install.safe_parents(template.parent)
    text = template.read_text()
    if text.count('@MINIMIZE_COMMAND@') != 1:
        raise ValueError('Titlebar template witness differs')
    titlebar = text.replace('@MINIMIZE_COMMAND@', json.dumps(minimize, ensure_ascii=False))
    activation_text = (
        '-- SPDX-License-Identifier: MIT\n'
        '-- Next-login activation. This file does not run during installer apply.\n'
        'local library = ' + json.dumps(str(library), ensure_ascii=False) + '\n'
        'local artifact = io.open(library, "r")\n'
        'if not artifact then return end\n'
        'artifact:close()\n'
        'hl.plugin.load(library)\n'
        'dofile(' + json.dumps(str(titlebar_path), ensure_ascii=False) + ')\n'
    )
    wallpaper = (root / 'config/hypr/hyprpaper.conf').read_text()
    if 'splash = false' not in wallpaper or 'preload' in wallpaper:
        raise ValueError('Wallpaper template must only disable the hyprpaper splash')
    unit = (root / 'config/systemd' / UNIT).read_text()
    wait = (root / 'config/systemd' / WAIT).read_text()
    if 'ExecStart=' not in unit or 'systemctl start' in unit or 'Restart=' in unit:
        raise ValueError('Autostart unit template differs')
    if not unit.endswith('\n') or not wait.endswith('\n') or not wallpaper.endswith('\n'):
        raise ValueError('Activation templates must end with a newline')
    return {'activation': activation_text, 'titlebars': titlebar, 'wallpaper': wallpaper,
            'unit': unit, 'wait': wait, 'library': str(library)}


def login_state(run):
    result = run([SYSTEMCTL, '--user', 'is-enabled', UNIT])
    if result.returncode == 0 and result.stdout.strip() == 'enabled':
        return True
    if result.returncode in (1, 4) or 'disabled' in result.stdout or 'not-found' in result.stdout:
        return False
    raise ValueError('Could not read login-unit state; no change made')


def daemons_stopped():
    session_config.require_stopped()
    result = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'hyprpaper'],
                            capture_output=True, timeout=5, check=False)
    if result.returncode != 1:
        raise ValueError('hyprpaper is running or its lookup failed; wallpaper config is left alone')


def pending(app):
    parent = app.state / 'activation-transactions'
    if not parent.exists():
        return []
    user_install.safe_parents(parent)
    result = []
    for path in parent.glob('*/transaction.json'):
        record = user_install.read_json(path)
        if not isinstance(record, dict) or record.get('schema_version') != 1:
            raise ValueError('Invalid activation journal; manual review required')
        if record.get('status') not in ('completed', 'restored-after-failure'):
            result.append(str(path))
    return result


def plan(root=ROOT, home=None, enable_login=None, plugin_check=None, login_probe=None):
    home, app, session_paths = session_config.locations(home)
    config = session_paths['entry'].parent.parent
    paths = paths_for(home, app, config)
    before = {name: session_config.state(path) for name, path in paths.items()}
    previous = user_install.read_json(paths['receipt']) if before['receipt']['existed'] else None
    blockers = []
    if session_config.pending(app) or pending(app):
        blockers.append('Interrupted session or activation transaction requires review')
    if not session_paths['receipt'].is_file():
        blockers.append('Prepare the generic session before activation')
    else:
        receipt = user_install.read_json(session_paths['receipt'])
        module = session_paths['module']
        guard = 'dofile(' + json.dumps(str(paths['activation']), ensure_ascii=False) + ')'
        if (not isinstance(receipt, dict) or not module.is_file()
                or session_config.state(module).get('sha256') != receipt.get('module_sha256')
                or guard not in module.read_text()):
            blockers.append('Session module has no current activation guard; reapply --session-config')
    app.require_settled()
    selected = app.selected()
    descriptor = None
    if selected is None:
        blockers.append('Install a verified release before activation')
    else:
        release = app.root / selected
        user_install.verify_bundle(release, installed=True)
        try:
            descriptor = (plugin_check or build_plugin.verify_bundle_plugin)(release)
        except (OSError, ValueError, build_plugin.builder.BuildError, subprocess.SubprocessError) as error:
            blockers.append('Plugin ABI/descriptor blocked activation: ' + str(error))
        if not descriptor:
            blockers.append('Selected release has no ABI-checked hyprbars artifact')
        helper = release / 'helpers/omabuntu_hyprland_window_minimize.py'
        if not helper.is_file():
            blockers.append('Release lacks the titlebar minimize helper')
    payload = None
    library = None
    wallpaper = None
    if descriptor and selected:
        rendered = render(root, app, selected, {
            'activation_path': paths['activation'], 'titlebar_path': paths['titlebars']})
        library = rendered.pop('library')
        payload = rendered
        try:
            actual = hashlib.sha256(Path(library).read_bytes()).hexdigest()
        except OSError as error:
            blockers.append('Plugin library is not readable: ' + type(error).__name__)
        else:
            if actual != descriptor.get('library_sha256'):
                blockers.append('Plugin bytes differ from the ABI descriptor')
        try:
            still = wallpaper_record.default_still(release)
        except (OSError, ValueError) as error:
            blockers.append(str(error))
            still = None
        recorded = app.state / 'current/background.json'
        recorded_state = session_config.state(recorded)
        if still is not None and not recorded_state['existed']:
            wallpaper = {'path': str(recorded), 'before': recorded_state,
                         'bytes': wallpaper_record.record(still), 'still': str(still)}
    if previous and (not isinstance(previous, dict) or previous.get('schema_version') != 1
                     or not isinstance(previous.get('files'), dict)):
        raise ValueError('Activation receipt differs; manual review required')
    owned = ('activation', 'titlebars', 'wallpaper', 'unit', 'wait')
    for name in owned:
        if before[name]['existed'] and (not previous or before[name]['sha256'] != previous.get('files', {}).get(name)):
            blockers.append('Existing ' + name + ' file is not installer-owned')
    enabled = False
    if login_probe is not None:
        enabled = login_probe()
    else:
        try:
            enabled = login_state(lambda argv: subprocess.run(argv, capture_output=True, text=True, timeout=15, check=False))
        except (OSError, subprocess.SubprocessError) as error:
            blockers.append('Login-unit probe failed: ' + str(error))
    if enable_login is not None and type(enable_login) is not bool:
        raise ValueError('Login enablement choice must be boolean')
    desired = previous.get('login_enabled') if previous and enable_login is None else enabled if enable_login is None else enable_login
    changes = []
    if payload:
        changes = [name for name, data in payload.items()
                   if not before[name]['existed'] or before[name]['sha256'] != hashlib.sha256(data.encode()).hexdigest()]
        if desired != enabled:
            changes.append('login-enablement')
        elif enabled and any(name in changes for name in ('unit', 'wait')):
            changes.append('user-systemd-reload')
        if wallpaper:
            changes.append('wallpaper-record')
    receipt = {'schema_version': 1, 'library': library, 'release': selected,
               'login_enabled': desired,
               'files': {name: hashlib.sha256(payload[name].encode()).hexdigest() for name in owned} if payload else {}}
    return {'schema_version': 1, 'kind': 'omabuntu-session-activation', 'root': str(root.absolute()),
            'home': str(home), 'paths': {name: str(path) for name, path in paths.items()},
            'before': before, 'payload': payload, 'receipt_payload': receipt, 'changes': changes,
            'wallpaper_record': wallpaper, 'enable_login': enable_login, 'login_enabled': enabled, 'blockers': blockers,
            'started': False, 'plugin_loaded': False,
            'status': 'blocked' if blockers else 'review-required'}


def default_run(argv):
    return subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)


def systemctl(argv, run):
    if argv[0] != SYSTEMCTL or 'start' in argv or 'restart' in argv or '--now' in argv:
        raise ValueError('Refusing a service start or unexpected systemctl command')
    result = run(argv)
    if result.returncode:
        raise ValueError('systemctl failed: ' + ' '.join(argv[1:]))


def apply(reviewed, approval, check_stopped=daemons_stopped, run=None, plugin_check=None):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Activation is per-user; do not use sudo')
    if guided.digest(reviewed) != approval or reviewed.get('kind') != 'omabuntu-session-activation' or reviewed.get('blockers'):
        raise ValueError('Activation approval differs or the plan is blocked')
    check_stopped()
    root, home = Path(reviewed['root']), Path(reviewed['home'])
    _, app, _ = session_config.locations(home)
    user_install.private_directory(app.state)
    import fcntl
    fd = os.open(app.state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fresh = plan(root, home, reviewed['enable_login'], plugin_check=plugin_check,
                     login_probe=lambda: reviewed['login_enabled'])
        if fresh != reviewed:
            raise ValueError('Activation inputs changed; review again')
        if not reviewed['changes']:
            return {'status': 'already-current', 'started': False, 'plugin_loaded': False, 'reloaded': False}
        paths = {name: Path(value) for name, value in reviewed['paths'].items()}
        parent = user_install.private_directory(app.state / 'activation-transactions' / user_install.stamp())
        journal = {'schema_version': 1, 'status': 'prepared', 'plan': reviewed}
        record = parent / 'transaction.json'
        for name, path in paths.items():
            if reviewed['before'][name]['existed']:
                (parent / name).write_bytes(path.read_bytes())
                (parent / name).chmod(0o600)
        user_install.atomic_json(record, journal)
        written = []
        try:
            check_stopped()
            for name, data in reviewed['payload'].items():
                if name not in reviewed['changes']:
                    continue
                check_stopped()
                if session_config.state(paths[name]) != reviewed['before'][name]:
                    raise ValueError('Activation file changed before write')
                written.append(name)
                session_config.write(paths[name], data.encode(), 0o755 if name == 'wait' else 0o644)
            session_config.write(paths['receipt'], (json.dumps(reviewed['receipt_payload'], indent=2) + '\n').encode(), 0o600)
            written.append('receipt')
            if 'wallpaper-record' in reviewed['changes']:
                item = reviewed['wallpaper_record']
                target = Path(item['path'])
                if session_config.state(target) != item['before']:
                    raise ValueError('Wallpaper record changed before write')
                session_config.write(target, item['bytes'].encode(), 0o600)
                wallpaper_record.publish_lock(target.with_name('lock-background'), item['still'])
            if 'login-enablement' in reviewed['changes'] or 'user-systemd-reload' in reviewed['changes']:
                systemctl([SYSTEMCTL, '--user', 'daemon-reload'], run or default_run)
            if 'login-enablement' in reviewed['changes']:
                command = [SYSTEMCTL, '--user', 'enable' if reviewed['receipt_payload']['login_enabled'] else 'disable', UNIT]
                systemctl(command, run or default_run)
            journal['status'] = 'completed'
            user_install.atomic_json(record, journal)
        except BaseException as error:
            try:
                check_stopped()
                for name in reversed(written):
                    path = paths[name]
                    current = session_config.state(path)
                    expected_bytes = ((json.dumps(reviewed['receipt_payload'], indent=2) + '\n').encode()
                                      if name == 'receipt' else reviewed['payload'][name].encode())
                    if not current['existed'] or current['sha256'] != hashlib.sha256(expected_bytes).hexdigest():
                        raise ValueError('Concurrent edits require manual recovery')
                    before = reviewed['before'][name]
                    if before['existed']:
                        session_config.write(path, (parent / name).read_bytes(), before['mode'])
                    else:
                        path.unlink()
                journal['status'] = 'restored-after-failure'
            except BaseException as recovery:
                journal.update(status='recovery-required', recovery_failure=type(recovery).__name__)
            journal['failure'] = type(error).__name__
            user_install.atomic_json(record, journal)
            raise ValueError('Activation failed before any service start; inspect ' + str(record)) from error
        return {'status': 'prepared-for-next-login', 'journal': str(record),
                'started': False, 'plugin_loaded': False, 'reloaded': False, 'capture': False}
