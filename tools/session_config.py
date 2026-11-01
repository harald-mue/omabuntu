"""Generic source-reviewed Hyprland 0.56.2/0.57.0 profile: review, backed-up apply, no activation.

Refuse unowned profiles and changes to the owned module. Keep the main config
editable, preserve options, and never write while a user Hyprland is running.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

import bootstrap_sources
import build_hyprbars
import install as guided
import plugin_manager
import user_install

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = 'require("omabuntu-session")'
MANAGED_INCLUDE = 'require("omabuntu-managed")'
MANAGED_MARKER = '-- Omabuntu installer-managed settings (plan 018)'
ENTRY = ('-- Omabuntu fresh-session entry. This file is yours to extend.\n'
         '-- The installer updates only the owned module, not your additions.\n'
         + INCLUDE + '\n\n'
         '-- Theme selection updates only these border literals.\n'
         'hl.config({ general = { col = {\n'
         '  active_border = "rgba(caccccee)",\n'
         '  inactive_border = "rgba(404040aa)",\n'
         '} } })\n')


def state(path):
    user_install.safe_parents(path.parent)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('Unsafe session configuration file')
    if not path.exists():
        return {'existed': False}
    if path.stat().st_size > 65536 or path.stat().st_uid != os.getuid():
        raise ValueError('Session configuration must be owned and bounded')
    return {'existed': True, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'mode': path.stat().st_mode & 0o777}


def layouts(path=Path('/usr/share/X11/xkb/rules/evdev.lst')):
    result = set()
    section = ''
    for line in path.read_text().splitlines():
        if line.startswith('!'):
            section = line[1:].strip()
        elif section == 'layout' and line.strip():
            result.add(line.split()[0])
    if not result:
        raise ValueError('XKB layout catalog is empty')
    return result


def locations(home=None):
    home = Path.home() if home is None else Path(home).absolute()
    config = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
    data = Path(os.environ.get('XDG_DATA_HOME') or home / '.local/share')
    store = Path(os.environ.get('XDG_STATE_HOME') or home / '.local/state') / 'omabuntu'
    if any(not path.is_absolute() for path in (config, data, store)):
        raise ValueError('XDG session paths must be absolute')
    app = user_install.Installation(data / 'omabuntu', store, home / '.local/bin/omabuntu')
    paths = {'entry': config / 'hypr/hyprland.lua', 'module': config / 'hypr/omabuntu-session.lua',
             'receipt': store / 'session-config.json'}
    return home, app, paths


def render(root, app, keyboard, manual_lock, paths=None):
    path = root / 'config/hypr/session-template.lua.in'
    user_install.safe_parents(path.parent)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
        raise ValueError('Missing generic session template')
    text = path.read_text()
    if paths is None:
        paths = {'entry': Path('/fixture/config/hypr/hyprland.lua')}
    current = app.root / 'current'
    capture = shlex.join(['/usr/bin/env', 'PYTHONDONTWRITEBYTECODE=1',
                          'OMABUNTU_OMASNAP=' + str(current / 'runtime/bin/omasnap'),
                          '/usr/bin/python3', str(current / 'helpers/capture_screenshot.py')])
    minimize = shlex.join(['/usr/bin/env', 'PYTHONDONTWRITEBYTECODE=1', '/usr/bin/python3',
                           str(current / 'helpers/omabuntu_hyprland_window_minimize.py')])
    lock_command = shlex.join([str(app.launcher), 'lock', '--apply'])
    replacements = {
        '@KEYBOARD_LAYOUT@': (1, json.dumps(keyboard, ensure_ascii=False)),
        '@SCREENSHOT_COMMAND@': (2, json.dumps(capture, ensure_ascii=False)),
        '@MINIMIZE_COMMAND@': (1, json.dumps(minimize, ensure_ascii=False)),
        '@WORKSPACE_STATE@': (1, json.dumps(str(app.state / 'current/workspace-layouts.txt'), ensure_ascii=False)),
        '@ACTIVATION_PATH@': (2, json.dumps(str(paths['entry'].with_name('omabuntu-activation.lua')), ensure_ascii=False)),
        '@MANUAL_LOCK_BIND@': (1, 'bind("SUPER + CTRL + L", "Lock system", hl.dsp.exec_cmd('
                                + json.dumps(lock_command, ensure_ascii=False) + '), { release = true })'
                                if manual_lock else '-- No lock shortcut until explicit authentication/recovery approval.'),
    }
    for token, (count, replacement) in replacements.items():
        if text.count(token) != count:
            raise ValueError('Session template witness differs: ' + token)
        text = text.replace(token, replacement)
    if re.search(r'@[A-Z_]+@', text):
        raise ValueError('Unresolved session template token')
    return text


def pending(app):
    parent = user_install.safe_parents(app.state / 'session-transactions')
    result = []
    for path in parent.glob('*/transaction.json'):
        record = user_install.read_json(path)
        if not isinstance(record, dict) or record.get('schema_version') != 1:
            raise ValueError('Invalid session journal; manual review required')
        if record.get('status') not in ('completed', 'restored-after-failure'):
            result.append(str(path))
    return result


def adoptable(entry_text, managed_path, template):
    """Only the untouched installer-owned snippet can be replaced."""
    if managed_path.is_symlink() or not managed_path.is_file() or managed_path.read_bytes() != template:
        return False
    allowed = {'', MANAGED_MARKER, MANAGED_INCLUDE}
    lines = entry_text.splitlines()
    return sum(line.strip() == MANAGED_INCLUDE for line in lines) == 1 and all(line.strip() in allowed for line in lines)


def plan(root=ROOT, home=None, keyboard=None, manual_lock=None, native=None, known_layouts=None, adopt_managed=False):
    bootstrap_sources.host_check()
    home, app, paths = locations(home)
    before = {name: state(path) for name, path in paths.items()}
    previous = user_install.read_json(paths['receipt']) if before['receipt']['existed'] else None
    blockers = []
    adopt = False
    if pending(app):
        blockers.append('Interrupted session configuration transaction requires review')
    if before['receipt']['existed']:
        if (not isinstance(previous, dict) or previous.get('schema_version') != 1 or previous.get('entry_path') != str(paths['entry'])
                or previous.get('module_path') != str(paths['module'])
                or type(previous.get('helper_contract')) is not int or previous['helper_contract'] != 1
                or type(previous.get('manual_lock')) is not bool
                or not isinstance(previous.get('keyboard_layout'), str)):
            raise ValueError('Session ownership receipt differs; manual review required')
        if not before['module']['existed'] or before['module']['sha256'] != previous.get('module_sha256'):
            blockers.append('Owned session module was edited or removed; preserving user changes')
        if not before['entry']['existed']:
            blockers.append('Editable entry was removed; preserving user choice')
        else:
            lines = [line.split('--', 1)[0].strip() for line in paths['entry'].read_text().splitlines()]
            if lines.count(INCLUDE) != 1:
                blockers.append('Keep exactly one original session include in the editable entry')
    elif (any(before[name]['existed'] for name in ('entry', 'module'))
          or (paths['entry'].parent / 'hyprland.conf').exists()
          or (paths['entry'].parent / 'hyprland.conf').is_symlink()):
        template = (root / 'config/hypr/omabuntu-managed.lua').read_bytes()
        managed = paths['entry'].with_name('omabuntu-managed.lua')
        entry_text = paths['entry'].read_text() if before['entry']['existed'] and not paths['entry'].is_symlink() else ''
        if adopt_managed and adoptable(entry_text, managed, template):
            adopt = True
        else:
            blockers.append('Existing unowned Hyprland profile is not overwritten or merged automatically')
            if adoptable(entry_text, managed, template):
                blockers.append('The untouched managed snippet can be adopted with --adopt-managed')
    keyboard = keyboard if keyboard is not None else (previous or {}).get('keyboard_layout', 'us')
    manual_lock = manual_lock if manual_lock is not None else (previous or {}).get('manual_lock', False)
    if (not isinstance(keyboard, str) or len(keyboard) > 64
            or not re.fullmatch(r'[a-z0-9_]+(?:,[a-z0-9_]+)*', keyboard)):
        raise ValueError('Invalid XKB keyboard layout list')
    catalog = layouts() if known_layouts is None else known_layouts
    if any(name not in catalog for name in keyboard.split(',')):
        raise ValueError('Selected keyboard layout is not in the installed XKB catalog')
    if type(manual_lock) is not bool:
        raise ValueError('Manual lock shortcut choice must be boolean')
    native = build_hyprbars.installed_version() if native is None else native
    target = plugin_manager.policy(root)['targets'].get(native.get('version'))
    if (not target or not target['apply_reviewed'] or native.get('commit') != target['hyprland_commit']
            or native.get('dirty') is not False):
        blockers.append('Generic session requires a source-reviewed clean Hyprland version/commit')
    app.require_settled()
    selected = app.selected()
    release_digest = None
    if selected is None:
        blockers.append('Install a verified local release before preparing its session')
    else:
        release = app.root / selected
        meta = user_install.verify_bundle(release, installed=True)
        release_digest = guided.digest(meta)
        required = user_install.SESSION_HELPERS + (user_install.SESSION_LOCK_HELPERS if manual_lock else ())
        for name in required:
            if (name not in meta['files'] or not (release / name).is_file()
                    or (name == 'runtime/bin/omasnap' and not os.access(release / name, os.X_OK))):
                blockers.append('Release lacks session helper/artifact: ' + name)
    module = render(root, app, keyboard, manual_lock, paths)
    receipt = {'schema_version': 1, 'helper_contract': 1, 'entry_path': str(paths['entry']), 'module_path': str(paths['module']),
               'module_sha256': hashlib.sha256(module.encode()).hexdigest(),
               'keyboard_layout': keyboard, 'manual_lock': manual_lock}
    payload = {'module': module, 'receipt': json.dumps(receipt, indent=2) + '\n'}
    if not before['entry']['existed'] or adopt:
        payload['entry'] = ENTRY
    changes = [name for name, data in payload.items()
               if not before[name]['existed'] or before[name]['sha256'] != hashlib.sha256(data.encode()).hexdigest()]
    return {'schema_version': 1, 'kind': 'omabuntu-session-config', 'root': str(root.absolute()),
            'home': str(home), 'paths': {name: str(path) for name, path in paths.items()},
            'before': before, 'payload': payload, 'changes': changes, 'selected': selected,
            'release_digest': release_digest, 'native': native, 'keyboard_layout': keyboard,
            'manual_lock': manual_lock, 'adopt_managed': bool(adopt_managed and adopt),
            'blockers': blockers, 'status': 'blocked' if blockers else 'review-required'}


def require_stopped():
    if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE') or 'hyprland' in os.environ.get('XDG_CURRENT_DESKTOP', '').lower().split(':'):
        raise ValueError('Configure from GNOME/TTY after leaving Hyprland; live config writes are refused')
    result = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'Hyprland|hyprland'],
                            capture_output=True, timeout=5, check=False)
    if result.returncode != 1:
        raise ValueError('A user Hyprland is running or lookup failed; configuration is left alone')


def write(path, data, mode):
    user_install.safe_parents(path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name('.' + path.name + '-' + user_install.stamp())
    created = False
    try:
        with temp.open('xb') as stream:
            created = True
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temp.chmod(mode)
        temp.replace(path)
    finally:
        if created:
            temp.unlink(missing_ok=True)


def apply(reviewed, approval, check_stopped=require_stopped):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Session setup is per-user; do not use sudo')
    if guided.digest(reviewed) != approval or reviewed.get('kind') != 'omabuntu-session-config' or reviewed.get('blockers'):
        raise ValueError('Session approval differs or the profile is blocked')
    check_stopped()
    root, home = Path(reviewed['root']), Path(reviewed['home'])
    _, app, _ = locations(home)
    user_install.private_directory(app.state)
    fd = os.open(app.state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fresh = plan(root, home, reviewed['keyboard_layout'], reviewed['manual_lock'],
                     adopt_managed=reviewed.get('adopt_managed', False))
        if fresh != reviewed:
            raise ValueError('Session inputs/configuration changed; review again')
        if not reviewed['changes']:
            return {'status': 'already-current', 'desktop_started': False, 'reloaded': False}
        parent = user_install.private_directory(app.state / 'session-transactions' / user_install.stamp())
        paths = {name: Path(value) for name, value in reviewed['paths'].items()}
        journal = {'schema_version': 1, 'status': 'prepared', 'plan': reviewed}
        record = parent / 'transaction.json'
        for name, path in paths.items():
            if reviewed['before'][name]['existed']:
                shutil.copyfile(path, parent / name)
                (parent / name).chmod(0o600)
        user_install.atomic_json(record, journal)
        written = []
        try:
            check_stopped()
            for name in reviewed['changes']:
                check_stopped()
                if state(paths[name]) != reviewed['before'][name]:
                    raise ValueError('Configuration changed before write')
                data = reviewed['payload'][name].encode()
                written.append(name)
                write(paths[name], data, 0o600 if name == 'receipt' else 0o644)
            journal['status'] = 'completed'
            user_install.atomic_json(record, journal)
        except BaseException as error:
            try:
                check_stopped()
                for name in reversed(written):
                    current = state(paths[name])
                    if current == reviewed['before'][name]:
                        continue
                    expected = hashlib.sha256(reviewed['payload'][name].encode()).hexdigest()
                    if not current['existed'] or current['sha256'] != expected:
                        raise ValueError('Concurrent user edits require manual recovery')
                    before = reviewed['before'][name]
                    if before['existed']:
                        write(paths[name], (parent / name).read_bytes(), before['mode'])
                    else:
                        paths[name].unlink()  # Only the unchanged file this operation created.
                journal['status'] = 'restored-after-failure'
            except BaseException as recovery:
                journal.update(status='recovery-required', recovery_failure=type(recovery).__name__)
            journal['failure'] = type(error).__name__
            user_install.atomic_json(record, journal)
            raise ValueError('Session setup failed; inspect private journal ' + str(record)) from error
        return {'status': 'configured-not-activated', 'journal': str(record),
                'desktop_started': False, 'reloaded': False, 'lock_triggered': False, 'capture': False}
