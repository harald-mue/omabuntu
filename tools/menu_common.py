#!/usr/bin/env python3
"""Shared state helpers for the Omabuntu menu backends.

State layout (all under the Omabuntu state home, default
~/.local/state/omabuntu, overridable with OMABUNTU_STATE_HOME):

  current/theme.json       applied theme name, palette, Hyprland colors
  current/font.txt         applied shell/GTK font family
  current/background.json  chosen background file
  current/power-gates.json approved session-ending actions
  backups/<stamp>/         copy of each state file before it changes
  operations.jsonl         one line per applied change

Every backend writes atomically, copies the previous state file into a
per-change backup directory first, and appends an operation record. Nothing
deletes user data. Backups are the rollback record; no rollback is automatic.
"""
import datetime
import json
import os
import shutil
from pathlib import Path


def state_home(root=None):
    """Omabuntu state directory; created on demand, never symlink-followed."""
    base = Path(root) if root is not None else Path(
        os.environ.get('OMABUNTU_STATE_HOME')
        or Path.home() / '.local' / 'state' / 'omabuntu')
    base = base.resolve() if base.exists() else base.absolute()
    if base.is_symlink() or not base.is_dir():
        if base.exists():
            raise ValueError('State home is not a real directory: %s' % base)
    (base / 'current').mkdir(parents=True, exist_ok=True)
    (base / 'backups').mkdir(parents=True, exist_ok=True)
    return base


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def read_json(path):
    """Parsed JSON state file or None; never follows a symlink."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        return None
    return _read_json(path)


def write_json(path, payload):
    """Atomic JSON write with 0600 permissions and fsync."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def write_text(path, text):
    """Atomic plain-text write."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def backup_and_write(path, writer):
    """Copy the previous state file aside, then write the new content.

    `writer` is called with the destination path. The backup keeps the exact
    previous bytes; a missing previous file records nothing to restore but is
    still logged. Returns the backup directory (or None when nothing existed).
    """
    path = Path(path)
    existed = path.exists() and not path.is_symlink()
    backup_dir = None
    if existed:
        backup_dir = state_home() / 'backups' / stamp()
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_dir / path.name)
    writer(path)
    return backup_dir


def record(action, target, backup_dir=None, detail=None):
    """Append one operation line to operations.jsonl."""
    entry = {'time': stamp(), 'action': action, 'target': str(target)}
    if backup_dir is not None:
        entry['backup'] = str(backup_dir)
    if detail is not None:
        entry['detail'] = detail
    log = state_home() / 'operations.jsonl'
    with log.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(entry, sort_keys=True) + '\n')
        stream.flush()
