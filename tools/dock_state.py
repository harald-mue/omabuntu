#!/usr/bin/env python3
"""Session dock preferences (position, autohide, pins) in a private user file.

No shell helper, no Hyprland config write and no service. Every write is atomic,
keeps one previous copy and is restricted to installed desktop ids.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import sys
import tempfile

SCHEMA = 1
POSITIONS = ('top', 'bottom', 'left', 'right')
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,199}(?:\.desktop)?\Z')
MAX_PINS = 64


def config_path():
    override = os.environ.get('OMABUNTU_DOCK_CONFIG')
    if override:
        path = Path(override)
        if not path.is_absolute() or '..' in path.parts:
            raise ValueError('Invalid dock config path')
        return path
    base = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    return Path(base) / 'omabuntu/dock.json'


def safe(path):
    for part in (path.parent, path):
        if part.is_symlink():
            raise ValueError('Symlinked dock configuration path')
    return path


def read(path):
    if not path.exists():
        return {'schema_version': SCHEMA, 'position': 'bottom', 'autohide': False, 'pinned': []}
    data = json.loads(path.read_text())
    if (not isinstance(data, dict) or type(data.get('schema_version')) is not int
            or data['schema_version'] != SCHEMA or data.get('position') not in POSITIONS
            or type(data.get('autohide')) is not bool or not isinstance(data.get('pinned'), list)
            or not all(isinstance(item, str) and ID.fullmatch(item) for item in data['pinned'])):
        raise ValueError('Dock configuration is invalid')
    return data


def write(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.stat().st_mode & 0o077:
        raise ValueError('Dock configuration directory must be private')
    if path.exists():
        backup = path.with_name(path.name + '.previous')
        backup.write_bytes(path.read_bytes())
        os.chmod(backup, 0o600)
    fd, temporary = tempfile.mkstemp(dir=str(path.parent), prefix='.dock-')
    try:
        with os.fdopen(fd, 'w') as stream:
            os.chmod(temporary, 0o600)
            json.dump(data, stream, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('get', 'set-position', 'set-autohide', 'set-pinned'))
    parser.add_argument('values', nargs='*')
    args = parser.parse_args(argv)
    path = safe(config_path())
    data = read(path)
    if args.action == 'set-position':
        if len(args.values) != 1 or args.values[0] not in POSITIONS:
            raise ValueError('Position must be top, bottom, left or right')
        data['position'] = args.values[0]
    elif args.action == 'set-autohide':
        if len(args.values) != 1 or args.values[0] not in ('on', 'off'):
            raise ValueError('Autohide must be on or off')
        data['autohide'] = args.values[0] == 'on'
    elif args.action == 'set-pinned':
        pins = []
        for value in args.values:
            if not ID.fullmatch(value):
                raise ValueError('Pinned entries must be installed desktop ids')
            if value not in pins:
                pins.append(value)
        if len(pins) > MAX_PINS:
            raise ValueError('Too many pinned entries')
        data['pinned'] = pins
    elif args.values:
        raise ValueError('get takes no arguments')
    if args.action != 'get':
        data['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write(path, data)
    print(json.dumps({'position': data['position'], 'autohide': data['autohide'],
                      'pinned': data['pinned']}))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({'error': str(error)}))
        raise SystemExit(1)
