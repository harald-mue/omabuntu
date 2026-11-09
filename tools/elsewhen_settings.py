#!/usr/bin/env python3
"""Bounded, private Elsewhen preferences; no network or desktop actions."""
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile

import menu_common

MAX_BYTES = 65536
ZONE = re.compile(r'^[A-Za-z0-9_+\-/]{1,160}$')
KEYS = {'id', 'cities', 'zones', 'here', 'homeCity', 'hour24', 'offsetMode',
        'units', 'globeEnabled', 'smoothMotion'}


def text(value, maximum=256):
    if (not isinstance(value, str) or len(value) > maximum
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('Invalid Elsewhen text')


def place(value, people=False):
    allowed = {'name', 'zone', 'lat', 'lon', 'region'} | ({'people'} if people else set())
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError('Invalid Elsewhen city')
    text(value.get('name'))
    if not isinstance(value.get('zone'), str) or not ZONE.fullmatch(value['zone']):
        raise ValueError('Invalid Elsewhen zone')
    if ('lat' in value) != ('lon' in value):
        raise ValueError('Incomplete Elsewhen coordinates')
    for key, maximum in (('lat', 90), ('lon', 180)):
        if key in value and (type(value[key]) not in (int, float)
                             or not math.isfinite(value[key]) or abs(value[key]) > maximum):
            raise ValueError('Invalid Elsewhen coordinates')
    if 'region' in value:
        text(value['region'])
    if 'people' in value:
        if not isinstance(value['people'], list) or len(value['people']) > 12:
            raise ValueError('Invalid Elsewhen people')
        for person in value['people']:
            text(person)


def validate(value):
    if not isinstance(value, dict) or set(value) - KEYS:
        raise ValueError('Invalid Elsewhen settings')
    if 'id' in value and value['id'] != 'omarchy.elsewhen':
        raise ValueError('Invalid Elsewhen module')
    if 'cities' in value:
        if not isinstance(value['cities'], list) or len(value['cities']) > 200:
            raise ValueError('Invalid Elsewhen cities')
        for city in value['cities']:
            place(city, people=True)
    if 'here' in value and value['here'] is not None:
        place(value['here'])
    for key in ('homeCity', 'zones'):
        if key in value:
            text(value[key], 8192 if key == 'zones' else 256)
    for key in ('hour24', 'globeEnabled', 'smoothMotion'):
        if key in value and type(value[key]) is not bool:
            if key != 'hour24' or value[key] != '':
                raise ValueError('Invalid Elsewhen boolean')
    for key, options in (('offsetMode', ('home', 'utc')), ('units', ('', 'C', 'F'))):
        if key in value and value[key] not in options:
            raise ValueError('Invalid Elsewhen preference')
    if len(json.dumps(value, ensure_ascii=True, allow_nan=False).encode()) + 1 > MAX_BYTES:
        raise ValueError('Elsewhen settings exceed limit')
    return value


def settings_path():
    base = Path(os.environ.get('OMABUNTU_STATE_HOME') or Path.home() / '.local/state/omabuntu')
    path = base / 'settings/elsewhen.json'
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Unsafe Elsewhen state path')
    if path.exists() and not path.is_file():
        raise ValueError('Elsewhen state must be a regular file')
    return path


def load():
    path = settings_path()
    if not path.exists():
        return {}
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Elsewhen settings exceed limit')
    return validate(json.loads(data))


def save(payload):
    if len(payload.encode()) > MAX_BYTES:
        raise ValueError('Elsewhen settings exceed limit')
    value = validate(json.loads(payload))
    path = settings_path()
    # Refuse to replace corrupt or unsupported previous settings.
    previous = load()
    if path.exists() and previous == value:
        return
    existed = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    def write(target):
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                             prefix='.elsewhen-', delete=False) as stream:
                name = stream.name
                json.dump(value, stream, ensure_ascii=True, allow_nan=False)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, target)
        finally:
            if name and os.path.exists(name):
                os.unlink(name)

    # Record prestate before the write, including first creation.
    def recorded_write(target):
        menu_common.record('elsewhen-settings-prestate', target,
                           detail={'existed': existed})
        write(target)

    backup = menu_common.backup_and_write(path, recorded_write)
    menu_common.record('elsewhen-settings-save', path, backup, detail={'existed': existed})


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if args == ['load']:
            print(json.dumps(load(), allow_nan=False))
        elif len(args) == 2 and args[0] == 'save':
            save(args[1])
        else:
            return 2
    except (OSError, ValueError, TypeError, RecursionError):
        print('Elsewhen settings unavailable; existing state was not intentionally replaced.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
