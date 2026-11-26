#!/usr/bin/env python3
"""Prepare only private Omabuntu notification state; never activate a service."""
import argparse
import json
import os
import math
import re
from pathlib import Path
import stat

LIMIT = 2_000_000
DEFAULTS = {'live.json': [], 'history.json': [], 'quiet.json': {'dnd': False}}
STRING_FIELDS = ('key', 'execArgv', 'execActions', 'glyph', 'app', 'appIcon',
                 'summary', 'body', 'rawBody', 'source', 'groupKey')
NUMBER_FIELDS = ('originalId', 'senderPid', 'urgency', 'expireTimeout', 'duration', 'ts')


def valid_row(row, history=False):
    strings = (*STRING_FIELDS, 'closed_reason') if history else STRING_FIELDS
    numbers = (*NUMBER_FIELDS, 'closed_ts') if history else NUMBER_FIELDS
    return (isinstance(row, dict) and set(row) == set(strings) | set(numbers)
            and all(isinstance(row[k], str) and len(row[k]) <= 32768 for k in strings)
            and all(type(row[k]) in (int, float) and math.isfinite(row[k]) for k in numbers)
            and re.fullmatch(r'[A-Za-z0-9_-]{1,120}', row['key']) is not None)


def owned(path, directory=False):
    info = path.lstat()
    mode = stat.S_IMODE(info.st_mode)
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if info.st_uid != os.getuid() or not kind(info.st_mode) or mode & 0o077:
        raise ValueError('Notification state must be owned, private and nonsymlinked')
    if not directory and (info.st_size > LIMIT or info.st_nlink != 1 or mode != 0o600):
        raise ValueError('Invalid bounded notification state file')


def prepare(home=None):
    home = Path(home or os.environ.get('OMABUNTU_STATE_HOME')
                or Path.home() / '.local/state/omabuntu').absolute()
    if '..' in home.parts or any(p.is_symlink() for p in (home, *home.parents)):
        raise ValueError('Symlinked/traversing notification state')
    # Missing state roots are created privately; existing modes are never fixed.
    missing = []
    for path in (home, *home.parents):
        if path.exists():
            break
        missing.append(path)
    for path in reversed(missing):
        path.mkdir(mode=0o700)
    owned(home, True)
    directory = home / 'notifications'
    if not directory.exists() and not directory.is_symlink():
        directory.mkdir(mode=0o700)
    owned(directory, True)
    # Validate all existing files before creating any missing file. Do not
    # replace malformed state, repair permissions, prune history or migrate it.
    for name in DEFAULTS:
        path = directory / name
        if path.exists() or path.is_symlink():
            owned(path)
            value = json.loads(path.read_bytes())
            if name == 'quiet.json':
                if not isinstance(value, dict) or set(value) != {'dnd'} or type(value['dnd']) is not bool:
                    raise ValueError('Invalid notification quiet state')
            elif not isinstance(value, list) or len(value) > 100 or any(not valid_row(row, name == 'history.json') for row in value):
                raise ValueError('Invalid notification entry state')
    for name, value in DEFAULTS.items():
        path = directory / name
        if not path.exists():
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write((json.dumps(value) + '\n').encode())
                stream.flush()
                os.fsync(stream.fileno())
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare',))
    parser.parse_args(argv)
    try:
        prepare()
        return 0
    except (OSError, ValueError):
        # Never echo notification text, file content or parser context.
        print('Notification state preparation refused', file=__import__('sys').stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
