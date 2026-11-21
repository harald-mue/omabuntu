#!/usr/bin/env python3
"""Explicit user-wide window-button layout, including GNOME; one key only.

No launch wrappers, environment overrides, GTK CSS, browser profile changes,
login/logout toggling or application restarts. Custom controls may ignore it.
"""
import argparse
import ast
import contextlib
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess

import appearance_backend as files

SCHEMA = 'org.gnome.desktop.wm.preferences'
KEY = 'button-layout'
DCONF_KEY = '/org/gnome/desktop/wm/preferences/button-layout'
HIDE = 'appmenu'
SHOW = 'appmenu:minimize,maximize,close'
CHOICES = {'hide': HIDE, 'show': SHOW}
ACTIONS = {'omabuntu-window-controls:' + name: name for name in (*CHOICES, 'restore')}
SCOPE = 'user-wide-including-gnome'
NOTICE = ('Applies to this user across desktops, including GNOME and concurrent '
          'sessions. Applications with independent controls may ignore it. '
          'hyprbars is unchanged; no logout or automatic app restart is required.')
MAX_LAYOUT = 4096


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=10,
                                check=False, env={**os.environ, 'LC_ALL': 'C',
                                                  'PYTHONDONTWRITEBYTECODE': '1'})
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError('Window-button settings command missing or timed out') from error
    if result.returncode or len(result.stdout.encode()) > 16384:
        raise ValueError('Window-button settings command failed or returned oversized output')
    return result.stdout.strip()


def parse_value(raw):
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError, RecursionError) as error:
        raise ValueError('Invalid button-layout response') from error
    if (not isinstance(value, str) or len(value) > MAX_LAYOUT
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('Invalid button-layout value')
    return value


def read_state():
    if os.environ.get('GSETTINGS_BACKEND', '') not in ('', 'dconf'):
        raise ValueError('A persistent dconf settings backend is required')
    effective = parse_value(command(['/usr/bin/gsettings', 'get', SCHEMA, KEY]))
    raw = command(['/usr/bin/dconf', 'read', DCONF_KEY])
    user_value = parse_value(raw) if raw else None
    writable = command(['/usr/bin/gsettings', 'writable', SCHEMA, KEY])
    if writable not in ('true', 'false'):
        raise ValueError('Invalid writable response')
    if user_value is not None and user_value != effective:
        raise ValueError('Settings changed during inspection or backend differs; retry')
    return {'effective': effective, 'user_value': user_value, 'writable': writable == 'true'}


def validate_before(value):
    if (not isinstance(value, dict) or set(value) != {'effective', 'user_value', 'writable'}
            or type(value['writable']) is not bool):
        raise ValueError('Invalid window-control backup')
    for name in ('effective', 'user_value'):
        item = value[name]
        if name == 'user_value' and item is None:
            continue
        if not isinstance(item, str) or len(item) > MAX_LAYOUT or any(ord(c) < 32 or ord(c) == 127 for c in item):
            raise ValueError('Invalid window-control backup value')
    if value['user_value'] is not None and value['effective'] != value['user_value']:
        raise ValueError('Inconsistent window-control backup')
    return value


def transactions(root=None):
    return files.safe((files.state_root() if root is None else Path(root)) / 'global-window-control-transactions')


def history(root=None):
    parent = transactions(root)
    if parent.exists() and not parent.is_dir():
        raise ValueError('Invalid global window-control transaction directory')
    records = []
    for path in sorted(parent.glob('*/transaction.json')):
        files.safe(path)
        if not files.TOKEN.fullmatch(path.parent.name):
            raise ValueError('Invalid window-control transaction name')
        record = files.json_file(path)
        if (not record or type(record.get('schema_version')) is not int or record['schema_version'] != 1
                or record.get('scope') != SCOPE or record.get('choice') not in CHOICES
                or record.get('after') != CHOICES[record['choice']]
                or not isinstance(record.get('before_sha256'), str)
                or not re.fullmatch(r'[a-f0-9]{64}', record['before_sha256'])
                or record.get('status') not in ('prepared', 'applied', 'restored')):
            raise ValueError('Invalid global window-control journal')
        records.append((path.parent, record))
    return records


def owns_hidden_layout(root=None):
    """Recognize a deliberate hide so legacy installer repair cannot undo it."""
    records = history(root)
    if not records:
        return False
    if any(record['status'] == 'prepared' for _, record in records):
        raise ValueError('Interrupted global window-control change; defer legacy repair')
    case, record = records[-1]
    if record['status'] != 'applied' or record['choice'] != 'hide':
        return False
    raw = files.read_bytes(case / 'before.json')
    if raw is None or files.digest(raw) != record['before_sha256']:
        raise ValueError('Global window-control backup requires review before legacy repair')
    validate_before(json.loads(raw))
    return True


def snapshot():
    state = read_state()
    records = history()
    return {**state, 'scope': SCOPE, 'notice': NOTICE,
            'hidden': not bool(set(re.split(r'[:,]', state['effective'])) & {'minimize', 'maximize', 'close'}),
            'shown': state['effective'] == SHOW,
            'pending_recovery': any(record['status'] == 'prepared' for _, record in records),
            'can_restore': bool(records and records[-1][1]['status'] != 'restored')}


def require_write_context():
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Run as your normal user, not root or sudo')
    if not os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
        raise ValueError('A user desktop session bus is required')


@contextlib.contextmanager
def locked():
    parent = transactions()
    files.mkdirs(parent)
    if parent.stat().st_uid != os.getuid() or stat.S_IMODE(parent.stat().st_mode) & 0o077:
        raise ValueError('Window-control transactions must be private')
    path = files.safe(parent / 'operation.lock')
    if path.exists():
        files.read_bytes(path)
    with os.fdopen(os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600), 'w') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield parent


def same_value(state, value):
    return state['effective'] == value and state['user_value'] == value


def same_before(state, before):
    return all(state[key] == before[key] for key in ('effective', 'user_value'))


def set_value(value):
    command(['/usr/bin/gsettings', 'set', SCHEMA, KEY, json.dumps(value)])
    if not same_value(read_state(), value):
        raise ValueError('Window-button change was not confirmed')


def restore_value(before):
    if before['user_value'] is None:
        command(['/usr/bin/gsettings', 'reset', SCHEMA, KEY])
    else:
        command(['/usr/bin/gsettings', 'set', SCHEMA, KEY, json.dumps(before['user_value'])])
    if not same_before(read_state(), before):
        raise ValueError('Previous window-button state could not be confirmed; review journal')


def response(status, token=None):
    result = {'ok': True, 'status': status, 'window_controls': snapshot(), 'message': NOTICE}
    if token:
        result['transaction'] = token
    return result


def review(choice):
    if choice not in CHOICES:
        raise ValueError('Unsupported window-control choice')
    state = snapshot()
    return {'scope': SCOPE, 'choice': choice, 'before': state['effective'],
            'after': CHOICES[choice], 'writable': state['writable'],
            'pending_recovery': state['pending_recovery'], 'notice': NOTICE}


def change(choice):
    if not isinstance(choice, str) or choice not in CHOICES:
        raise ValueError('Unsupported window-control choice')
    require_write_context()
    state = snapshot()
    if not state['writable'] or state['pending_recovery']:
        raise ValueError('Setting locked or interrupted change pending; restore/review first')
    if state['effective'] == CHOICES[choice]:
        return response('unchanged')
    with locked() as parent:
        state = snapshot()
        if not state['writable'] or state['pending_recovery']:
            raise ValueError('Setting locked or interrupted change pending; restore/review first')
        if state['effective'] == CHOICES[choice]:
            return response('unchanged')
        before = {name: state[name] for name in ('effective', 'user_value', 'writable')}
        raw = files.encode(before)
        token = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + os.urandom(6).hex()
        case = parent / token
        case.mkdir(mode=0o700)
        files.atomic(case / 'before.json', raw)
        record = {'schema_version': 1, 'scope': SCOPE, 'choice': choice, 'status': 'prepared',
                  'before_sha256': files.digest(raw), 'after': CHOICES[choice]}
        files.atomic(case / 'transaction.json', files.encode(record))
        # Refuse an intervening settings write before touching the live key.
        if not same_before(read_state(), before):
            record['status'] = 'restored'
            files.atomic(case / 'transaction.json', files.encode(record))
            raise ValueError('Window-button setting changed during review; no setting written')
        try:
            set_value(record['after'])
            record['status'] = 'applied'
            files.atomic(case / 'transaction.json', files.encode(record))
        except BaseException:
            # Do not undo an external change, even on a failure path.
            if same_value(read_state(), record['after']):
                restore_value(before)
            # Keep prepared journal until explicit recovery.
            raise
        return response('applied-user-wide', token)


def restore():
    require_write_context()
    if not history():
        raise ValueError('No global window-button change to restore')
    with locked():
        case, record = history()[-1]
        if record['status'] == 'restored':
            raise ValueError('Latest window-button change already restored')
        raw = files.read_bytes(case / 'before.json')
        if raw is None or files.digest(raw) != record['before_sha256']:
            raise ValueError('Window-control backup integrity differs')
        before = validate_before(json.loads(raw))
        current = read_state()
        if not current['writable']:
            raise ValueError('Window-button setting is locked')
        if not same_before(current, before):
            if not same_value(current, record['after']):
                raise ValueError('Window-button setting changed externally; restore refused')
            restore_value(before)
        record['status'] = 'restored'
        files.atomic(case / 'transaction.json', files.encode(record))
        return response('previous-user-state-restored', case.name)


def guards(items):
    result = {'when': {}, 'checked': {}, 'disabled': {}}
    try:
        state = snapshot()
    except (OSError, ValueError):
        state = None
    available = state is not None and state['writable']
    for item_id, entry in items.items():
        for field in result:
            expression = entry.get(field, '')
            if not expression.startswith('window-controls:'):
                continue
            token = expression[len('window-controls:'):]
            values = {'unavailable': not available or bool(state and state['pending_recovery']),
                      'cannot-restore': not available or not bool(state and state['can_restore']),
                      'hidden': bool(state and state['hidden']), 'shown': bool(state and state['shown'])}
            result[field][item_id] = values.get(token, False)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('status', help='Read the actual shared setting; no writes')
    plan = sub.add_parser('plan', help='Read-only user-wide show/hide plan')
    plan.add_argument('choice', choices=CHOICES)
    change_parser = sub.add_parser('set', help='Change this one key for all desktops')
    change_parser.add_argument('choice', choices=CHOICES)
    change_parser.add_argument('--apply-user-wide', action='store_true')
    recovery = sub.add_parser('restore', help='Restore/recover latest global transaction')
    recovery.add_argument('--apply-user-wide', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.action == 'status':
            result = {'ok': True, 'window_controls': snapshot()}
        elif args.action == 'plan':
            result = {'ok': True, 'plan': review(args.choice)}
        else:
            if not args.apply_user_wide:
                raise ValueError('This affects GNOME too; explicit --apply-user-wide is required')
            result = change(args.choice) if args.action == 'set' else restore()
    except (OSError, ValueError) as error:
        print(json.dumps({'ok': False, 'error': 'window-controls', 'message': str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
