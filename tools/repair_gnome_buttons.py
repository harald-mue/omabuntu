#!/usr/bin/python3
"""Restore the Ubuntu default GNOME window-button layout (plan 074).

Omabuntu never changes user-global GNOME settings, but a 2026-10-25 manual
change set org.gnome.desktop.wm.preferences button-layout to 'appmenu',
which strips minimize/maximize/close from every CSD app in GNOME sessions
too. review is read-only; apply restores the Ubuntu default
'appmenu:minimize,maximize,close' and records the previous value first;
rollback restores that recorded value. Only this one key is touched.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

SCHEMA = 'org.gnome.desktop.wm.preferences'
KEY = 'button-layout'
DAMAGE = 'appmenu'
DEFAULT = 'appmenu:minimize,maximize,close'
GSETTINGS = '/usr/bin/gsettings'
STATE_DIR = '.local/state/omabuntu/gnome-buttons'


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')


def state_dir(home):
    return Path(home) / STATE_DIR


def check_home(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('Parent traversal is not allowed')
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise ValueError('Symlinked path: ' + str(part))
        if part != path and part.exists() and not part.is_dir():
            raise ValueError('Not a directory: ' + str(part))
    if not path.is_dir():
        raise ValueError('Home directory does not exist: ' + str(path))
    return path


def gsettings(binary, *args):
    result = subprocess.run([binary, args[0], SCHEMA, *args[1:]],
                            capture_output=True, text=True, timeout=15, check=False)
    if result.returncode:
        raise ValueError('gsettings ' + ' '.join(args) + ' failed: '
                         + (result.stderr.strip() or str(result.returncode)))
    return result.stdout.strip()


def parse_value(raw):
    """gsettings prints the string quoted, e.g. 'appmenu'."""
    value = raw.strip()
    if len(value) >= 2 and value.startswith("'") and value.endswith("'"):
        value = value[1:-1]
    if not value:
        raise ValueError('Empty button-layout value')
    if any(character in value for character in '\'"'):
        raise ValueError('Unexpected characters in button-layout value')
    return value


def current_value(home=None, binary=GSETTINGS):
    return parse_value(gsettings(binary, 'get', KEY))


def record_paths(home):
    directory = state_dir(home)
    if not directory.is_dir():
        return []
    result = []
    for path in sorted(directory.glob('*/record.json')):
        try:
            record = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if (isinstance(record, dict) and record.get('schema') == SCHEMA
                and record.get('key') == KEY and isinstance(record.get('previous'), str)):
            result.append(path)
    return result


def write_record(home, previous):
    directory = state_dir(home)
    directory.mkdir(parents=True, exist_ok=True)
    record = {'schema_version': 1, 'changed_at': stamp(), 'schema': SCHEMA, 'key': KEY,
              'previous': previous, 'new': DEFAULT,
              'reason': 'Restore the Ubuntu default so GNOME sessions keep '
                         'min/max/close buttons; Omabuntu must not break GNOME (plan 074).',
              'restore_command': ['gsettings', 'set', SCHEMA, KEY, previous]}
    path = directory / record['changed_at'] / 'record.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + '\n')
    path.chmod(0o600)
    return path


def review(home=None, binary=GSETTINGS):
    """Read-only: current value, whether the documented repair is needed.

    The repair targets exactly the documented 2026-10-25 damage signature
    ('appmenu', no right-side buttons). Any other value, including a stock
    schema default or a user's own layout, is left alone and never offered.
    """
    home = check_home(home or os.path.expanduser('~'))
    value = current_value(home, binary)
    return {'home': home, 'schema': SCHEMA, 'key': KEY, 'current': value,
            'damage': DAMAGE, 'default': DEFAULT,
            'repair_needed': value == DAMAGE,
            'records': record_paths(home)}


def apply(home=None, binary=GSETTINGS):
    """Restore the Ubuntu default; record the previous value first."""
    info = review(home, binary)
    if not info['repair_needed']:
        return {'changed': False, 'record': None, 'current': info['current']}
    path = write_record(info['home'], info['current'])
    gsettings(binary, 'set', KEY, DEFAULT)
    return {'changed': True, 'record': path,
            'current': current_value(info['home'], binary)}


def rollback(home=None, binary=GSETTINGS):
    """Restore the most recent recorded previous value."""
    home = check_home(home or os.path.expanduser('~'))
    found = record_paths(home)
    if not found:
        return {'changed': False, 'record': None}
    path = found[-1]
    record = json.loads(path.read_text())
    gsettings(binary, 'set', KEY, record['previous'])
    record['restored_at'] = stamp()
    path.write_text(json.dumps(record, indent=2) + '\n')
    return {'changed': True, 'record': path,
            'current': current_value(home, binary)}


def plan(args):
    info = review(args.home, args.gsettings)
    print('Schema:   ' + SCHEMA)
    print('Key:      ' + KEY)
    print('Current:  ' + repr(info['current']))
    print('Damage:   ' + repr(info['damage']) + ' (the documented 2026-10-25 override)')
    print('Restore:  ' + repr(info['default']) + ' (the recorded pre-change value)')
    print('Repair needed: ' + ('yes' if info['repair_needed'] else 'no'))
    print('Records:  ' + (', '.join(str(path.parent.name) for path in info['records']) or 'none'))
    print('--- apply would run ---')
    if not info['repair_needed']:
        print('  nothing: the value is not the documented damage signature')
    else:
        print('  write a private record of ' + repr(info['current'])
              + ' under ' + str(state_dir(info['home'])))
        print('  gsettings set ' + SCHEMA + ' ' + KEY + ' ' + repr(DEFAULT))
    print('Apply changes the one GNOME key above; gsettings needs a running')
    print('desktop session bus. Nothing else is touched.')
    print('Rollback: ' + sys.argv[0] + ' rollback --home ' + str(info['home']))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', default=os.path.expanduser('~'),
                        help='Target home directory (default: the current user)')
    parser.add_argument('--gsettings', default=GSETTINGS,
                        help='gsettings binary override for isolated tests')
    sub = parser.add_subparsers(dest='mode', required=True)
    sub.add_parser('plan', help='Read-only plan: current/default and the exact change')
    sub.add_parser('apply', help='Record the current value, then restore the Ubuntu default')
    sub.add_parser('rollback', help='Restore the most recent recorded previous value')
    args = parser.parse_args()
    if args.mode == 'plan':
        return plan(args)
    if args.mode == 'apply':
        result = apply(args.home, args.gsettings)
    else:
        result = rollback(args.home, args.gsettings)
    if not result['changed']:
        print('Nothing to change.' if args.mode == 'apply'
              else 'No recorded change to roll back.')
    else:
        print('Set ' + SCHEMA + ' ' + KEY + ' to ' + repr(result['current']))
        print('Record: ' + str(result['record']))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        sys.exit(2)