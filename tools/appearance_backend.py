"""Allowlisted shell preferences; no compositor commands or global GTK settings.

Read operations never create state. Every change records exact prior bytes/mode
or absence before an atomic write. Rollback refuses unrelated later changes.
"""
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

import dock_state

CLOCKS = {
    'sunday-24h': 'dddd HH:mm', 'sunday-12h': 'dddd h:mm AP',
    'sunday-seconds-24h': 'dddd HH:mm:ss', 'sunday-seconds-12h': 'dddd h:mm:ss AP',
    'time-24h': 'HH:mm', 'time-12h': 'h:mm AP',
    'date-24h': 'ddd d MMM HH:mm', 'date-12h': 'ddd d MMM h:mm AP',
    'week': "d MMMM 'W'ww yyyy", 'iso': 'yyyy-MM-dd HH:mm',
}
DEFAULTS = {'schema_version': 1, 'background': 'opaque', 'hidden': False,
            'clock_format': 'dddd HH:mm', 'battery_percentage': False}
CHOICES = {'hidden': ('on', 'off'), 'background': ('opaque', 'glassy', 'none'),
           'clock': tuple(CLOCKS), 'battery-percentage': ('on', 'off'),
           'dock-position': dock_state.POSITIONS, 'dock-autohide': ('on', 'off')}
ACTIONS = {'omabuntu-appearance:%s:%s' % (key, value): (key, value)
           for key, values in CHOICES.items() for value in values}
TOKEN = re.compile(r'[0-9]{8}T[0-9]{12}Z-[0-9a-f]{12}\Z')
MAX_BYTES = 65536
WIDGET_KEYS = ('clock-settings', 'tray-settings')
CLOCK_FIELDS = {'weekStartDay', 'birthYear', 'lifeExpectancy', 'formatAlt',
                'verticalFormat', 'verticalFormatAlt'}
WEEKDAYS = ('sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday')


def widget_values(key, raw):
    """Validate bounded field patches, never commands or arbitrary widget ids."""
    if key not in WIDGET_KEYS or not isinstance(raw, str) or len(raw.encode()) > MAX_BYTES:
        raise ValueError('Invalid widget settings')
    values = json.loads(raw)
    if not isinstance(values, dict):
        raise ValueError('Invalid widget settings')
    if key == 'clock-settings':
        if set(values) - (CLOCK_FIELDS | {'format'}):
            raise ValueError('Unknown clock setting')
        for name, value in values.items():
            if name == 'format':
                if not isinstance(value, str) or value not in CLOCKS.values():
                    raise ValueError('Invalid clock format')
            elif name == 'weekStartDay':
                if not isinstance(value, str) or value not in WEEKDAYS:
                    raise ValueError('Invalid week start')
            elif name == 'birthYear':
                if type(value) is not int or not (value == 0 or 1000 <= value <= 9999):
                    raise ValueError('Invalid birth year')
            elif name == 'lifeExpectancy':
                if type(value) is not int or not 1 <= value <= 150:
                    raise ValueError('Invalid life expectancy')
            elif (not isinstance(value, str) or len(value) > 256
                  or any((ord(c) < 32 and c != '\n') or ord(c) == 127 for c in value)):
                raise ValueError('Invalid clock format text')
    else:
        if set(values) - {'pinned', 'hidden'}:
            raise ValueError('Unknown tray setting')
        for items in values.values():
            if (not isinstance(items, list) or len(items) > 128
                    or any(not isinstance(item, str) or not item or len(item) > 512
                           or any(ord(c) < 32 or ord(c) == 127 for c in item) for item in items)
                    or len(set(items)) != len(items)):
                raise ValueError('Invalid tray identifiers')
    return values


def valid_choice(key, value):
    if not isinstance(key, str) or not isinstance(value, str):
        return False
    if key in CHOICES:
        return value in CHOICES[key]
    try:
        widget_values(key, value)
        return True
    except (ValueError, TypeError, RecursionError):
        return False


def state_root():
    return Path(os.environ.get('OMABUNTU_STATE_HOME') or Path.home() / '.local/state/omabuntu')


def safe(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Expected an absolute preference path')
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise ValueError('Symlinked preference path')
        if part.exists() and part.stat().st_uid != os.getuid() and part not in path.parents:
            raise ValueError('Preference file is not owned by this user')
    return path


def read_bytes(path):
    path = safe(path)
    if not path.exists():
        return None
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > MAX_BYTES or info.st_mode & 0o7000:
        raise ValueError('Expected a bounded owned preference file')
    return path.read_bytes()


def json_file(path):
    raw = read_bytes(path)
    if raw is None:
        return None
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Invalid preference object')
    return value


def session_allowed(environ=None):
    env = os.environ if environ is None else environ
    desktops = re.split(r'[:;]', env.get('XDG_CURRENT_DESKTOP', '').lower())
    return (bool(desktops) and all(d == 'hyprland' for d in desktops)
            and env.get('XDG_SESSION_TYPE') == 'wayland'
            and bool(env.get('HYPRLAND_INSTANCE_SIGNATURE'))
            and bool(env.get('WAYLAND_DISPLAY')))


def bar_state():
    root = state_root()
    data = json_file(root / 'current/bar.json')
    result = dict(DEFAULTS, clock_settings={}, tray_settings={'pinned': [], 'hidden': []})
    flag = root / 'toggles/bar-off'
    safe(flag)
    result['hidden'] = flag.is_file()
    if data is not None:
        if type(data.get('schema_version')) is not int or data['schema_version'] != 1:
            raise ValueError('Unsupported bar preferences')
        result.update(data)
    if (result['background'] not in CHOICES['background']
            or type(result['hidden']) is not bool
            or type(result['battery_percentage']) is not bool
            or result['clock_format'] not in CLOCKS.values()):
        raise ValueError('Invalid bar preferences')
    clock = widget_values('clock-settings', json.dumps(result['clock_settings']))
    if 'format' in clock:
        raise ValueError('Clock format must have one authoritative field')
    widget_values('tray-settings', json.dumps(result['tray_settings']))
    if set(result['tray_settings']) != {'pinned', 'hidden'}:
        raise ValueError('Incomplete tray preferences')
    return result


def battery_present(directory=Path('/sys/class/power_supply')):
    try:
        return any((p / 'type').read_text().strip() == 'Battery'
                   and (not (p / 'present').exists() or (p / 'present').read_text().strip() == '1')
                   for p in directory.iterdir())
    except OSError:
        return False


def floating_workspace(workspace):
    if not isinstance(workspace, str) or not re.fullmatch(r'[1-9][0-9]{0,8}', workspace):
        return False
    raw = read_bytes(state_root() / 'current/workspace-layouts.txt')
    return raw is not None and (workspace + ' floating') in raw.decode().splitlines()


def snapshot(workspace=None):
    path = safe(dock_state.config_path())
    read_bytes(path)
    return {'bar': bar_state(), 'dock': dock_state.read(path),
            'available': session_allowed(), 'battery_present': battery_present(),
            'floating_workspace': floating_workspace(workspace)}


def guards(items, workspace=None):
    result = {'when': {}, 'checked': {}, 'disabled': {}}
    try:
        current = snapshot(workspace)
    except (OSError, ValueError):
        current = None
    for item_id, entry in items.items():
        for field in result:
            expression = entry.get(field, '')
            if not expression.startswith('appearance:'):
                continue
            token = expression[len('appearance:'):]
            value = False
            if current is not None and current['available']:
                if token == 'available':
                    value = True
                elif token == 'battery':
                    value = current['battery_present']
                elif token in ('battery-show', 'battery-hide'):
                    value = current['battery_present'] and current['bar']['battery_percentage'] == (token == 'battery-hide')
                elif token == 'floating':
                    value = current['floating_workspace']
                elif ':' in token:
                    key, wanted = token.split(':', 1)
                    if key == 'hidden':
                        value = current['bar']['hidden'] == (wanted == 'on')
                    elif key == 'background':
                        value = current['bar']['background'] == wanted
                    elif key == 'clock':
                        value = current['bar']['clock_format'] == CLOCKS.get(wanted)
                    elif key == 'battery-percentage':
                        value = current['bar']['battery_percentage'] == (wanted == 'on')
                    elif key == 'dock-position':
                        value = current['dock']['position'] == wanted
                    elif key == 'dock-autohide':
                        value = current['dock']['autohide'] == (wanted == 'on')
            result[field][item_id] = value
    return result


def mkdirs(path):
    safe(path)
    for directory in [*reversed(path.parents), path]:
        if not directory.exists():
            directory.mkdir(mode=0o700, exist_ok=True)
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('Preference parent is not a directory')


def atomic(path, raw, mode=0o600):
    safe(path)
    fd, name = tempfile.mkstemp(prefix='.appearance-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest() if raw is not None else None


def transaction_directory():
    path = safe(state_root() / 'appearance-transactions')
    mkdirs(path)
    if path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError('Appearance transactions must be private')
    return path


def change(key, value):
    if not valid_choice(key, value):
        raise ValueError('Unsupported appearance choice')
    if not session_allowed():
        raise ValueError('Appearance changes require a Hyprland Wayland session')
    # Validate both preference stores before any write or transaction allocation.
    snapshot()
    parent = transaction_directory()
    lock = parent / 'operation.lock'
    safe(lock)
    with contextlib.ExitStack() as locks, os.fdopen(os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600), 'w') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        if key.startswith('dock-'):
            target = safe(dock_state.config_path())
            locks.enter_context(dock_state.preference_lock(target))
            read_bytes(target)
            data = dock_state.read(target)
            data['position' if key == 'dock-position' else 'autohide'] = value if key == 'dock-position' else value == 'on'
        else:
            target = safe(state_root() / 'current/bar.json')
            data = bar_state()
            if key in WIDGET_KEYS:
                patch = widget_values(key, value)
                if key == 'clock-settings':
                    if 'format' in patch:
                        data['clock_format'] = patch.pop('format')
                    data['clock_settings'] = {**data['clock_settings'], **patch}
                else:
                    data['tray_settings'] = {**data['tray_settings'], **patch}
            else:
                field = {'hidden': 'hidden', 'background': 'background', 'clock': 'clock_format',
                         'battery-percentage': 'battery_percentage'}[key]
                data[field] = CLOCKS[value] if key == 'clock' else (value == 'on' if key in ('hidden', 'battery-percentage') else value)
        before = read_bytes(target)
        after = encode(data)
        if len(after) > MAX_BYTES:
            raise ValueError('Preference state exceeds limit')
        if before == after:
            return {'ok': True, 'status': 'unchanged', 'appearance': snapshot()}
        token = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + os.urandom(6).hex()
        case = parent / token
        case.mkdir(mode=0o700)
        record = {'schema_version': 1, 'status': 'prepared', 'target': str(target),
                  'before_sha256': digest(before), 'before_mode': stat.S_IMODE(target.stat().st_mode) if before is not None else None,
                  'after_sha256': digest(after), 'key': key, 'value': value,
                  'parent_existed': target.parent.exists()}
        if before is not None:
            atomic(case / 'before', before)
        atomic(case / 'transaction.json', encode(record))
        mkdirs(target.parent)
        try:
            atomic(target, after)
            record['status'] = 'applied'
            atomic(case / 'transaction.json', encode(record))
        except BaseException:
            # A failed final receipt must not leave an unacknowledged change.
            if digest(read_bytes(target)) == record['after_sha256']:
                if before is None:
                    target.unlink()
                else:
                    atomic(target, before, record['before_mode'])
            raise
        return {'ok': True, 'status': 'applied', 'transaction': token, 'appearance': snapshot()}


def rollback(token):
    if not session_allowed() or not TOKEN.fullmatch(token):
        raise ValueError('Invalid rollback request/session')
    parent = safe(state_root() / 'appearance-transactions')
    if not parent.is_dir():
        raise ValueError('No appearance transactions')
    lock = safe(parent / 'operation.lock')
    with contextlib.ExitStack() as locks, os.fdopen(os.open(lock, os.O_RDWR | os.O_NOFOLLOW), 'w') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        case = safe(parent / token)
        record = json_file(case / 'transaction.json')
        if not record or record.get('status') not in ('applied', 'prepared'):
            raise ValueError('Transaction is not reversible')
        key = record.get('key')
        before_hash = record.get('before_sha256')
        after_hash = record.get('after_sha256')
        if (type(record.get('schema_version')) is not int or record['schema_version'] != 1
                or not valid_choice(key, record.get('value'))
                or not isinstance(record.get('target'), str)
                or (before_hash is not None and (not isinstance(before_hash, str)
                    or not re.fullmatch(r'[0-9a-f]{64}', before_hash)))
                or not isinstance(after_hash, str) or not re.fullmatch(r'[0-9a-f]{64}', after_hash)):
            raise ValueError('Invalid preference transaction')
        target = safe(Path(record['target']))
        expected = safe(dock_state.config_path() if record.get('key', '').startswith('dock-') else state_root() / 'current/bar.json')
        if record.get('key', '').startswith('dock-'):
            locks.enter_context(dock_state.preference_lock(expected))
        if target != expected or digest(read_bytes(target)) != record['after_sha256']:
            raise ValueError('Preference changed since this transaction; rollback refused')
        before = read_bytes(case / 'before')
        if digest(before) != record['before_sha256']:
            raise ValueError('Preference backup differs')
        if before is None:
            target.unlink()
        else:
            mode = record['before_mode']
            if type(mode) is not int or not 0 <= mode <= 0o777:
                raise ValueError('Invalid recorded preference mode')
            atomic(target, before, mode)
        record['status'] = 'rolled-back'
        atomic(case / 'transaction.json', encode(record))
        return {'ok': True, 'status': 'rolled-back', 'appearance': snapshot()}
