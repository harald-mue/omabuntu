#!/usr/bin/env python3
"""Default browser and terminal for the Omabuntu Setup menu.

Omarchy lists fixed browser and terminal rows under Setup > Defaults and
applies choices through omarchy-default-browser and omarchy-default-terminal.
This Ubuntu adaptation discovers installed .desktop entries only, reads the
current choice through xdg-settings and xdg-terminal-exec, and applies a new
choice through those same mechanisms. Nothing is installed or removed.

Browsers: WebBrowser .desktop files with a working TryExec/Exec binary.
Duplicate vendor ids (com.google.Chrome vs google-chrome) collapse to one row.

Terminals: TerminalEmulator .desktop files with a working TryExec/Exec.
The preference is written to the Hyprland-specific xdg-terminals list under
XDG_CONFIG_HOME when XDG_CURRENT_DESKTOP names Hyprland, otherwise the generic
xdg-terminals.list. The xdg-terminal-exec cache file is removed after a change.

CLI: defaults_backend.py list-browsers | list-terminals | current-browser |
      current-terminal | set-browser <desktop-id> | set-terminal <desktop-id>
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import menu_common

DESKTOP_ID = re.compile(r'^[A-Za-z0-9._+-]+\.desktop$')
APPLICATION_DIRS = (
    Path('/usr/share/applications'),
    Path.home() / '.local' / 'share' / 'applications',
)


def _config_home(config=None):
    return Path(config) if config is not None else Path(
        os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')


def _parse_desktop_entry(path):
    """Return the main [Desktop Entry] section as a dict."""
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None
    section = None
    data = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            name = stripped[1:-1].strip()
            if name == 'Desktop Entry':
                section = 'main'
                data = {}
                continue
            if section == 'main':
                break
            section = None
            continue
        if section != 'main' or '=' not in line:
            continue
        key, value = line.split('=', 1)
        data[key.strip()] = value.strip()
    return data if data else None


def _truthy(value):
    return str(value or '').lower() in ('1', 'true', 'yes')


def _exec_binary(entry):
    candidate = entry.get('TryExec') or ''
    if not candidate:
        exec_line = entry.get('Exec') or ''
        candidate = exec_line.split()[0] if exec_line else ''
    candidate = candidate.replace('%u', '').replace('%U', '').replace('%f', '').strip()
    if not candidate:
        return None
    if candidate.startswith('/'):
        path = Path(candidate)
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    return shutil.which(candidate)


def _desktop_paths():
    seen = set()
    for directory in APPLICATION_DIRS:
        if directory.is_symlink() or not directory.is_dir():
            continue
        for path in sorted(directory.glob('*.desktop')):
            if path.is_symlink() or not path.is_file():
                continue
            real = str(path.resolve())
            if real in seen:
                continue
            seen.add(real)
            yield path


def _prefer_desktop_id(entries):
    """Pick one id when several .desktop files share the same binary."""
    return sorted(entries, key=lambda item: (item['id'].startswith('com.'),
                                             item['id'].startswith('org.'),
                                             len(item['id']),
                                             item['id']))[0]


def _collect(kind):
    grouped = {}
    for path in _desktop_paths():
        entry = _parse_desktop_entry(path)
        if not entry:
            continue
        if _truthy(entry.get('NoDisplay')) or _truthy(entry.get('Hidden')):
            continue
        categories = entry.get('Categories') or ''
        mime = entry.get('MimeType') or ''
        if kind == 'browser':
            if 'WebBrowser' not in categories and 'x-scheme-handler/https' not in mime:
                continue
        elif kind == 'terminal':
            if 'TerminalEmulator' not in categories:
                continue
        else:
            return []
        binary = _exec_binary(entry)
        if not binary:
            continue
        desktop_id = path.name
        if not DESKTOP_ID.fullmatch(desktop_id):
            continue
        label = entry.get('Name') or desktop_id
        grouped.setdefault(binary, []).append({'id': desktop_id, 'label': label, 'binary': binary})
    rows = [_prefer_desktop_id(group) for group in grouped.values()]
    rows.sort(key=lambda item: item['label'].lower())
    return rows


def browser_candidates():
    return _collect('browser')


def terminal_candidates():
    return _collect('terminal')


def xdg_settings_run(argv, timeout=8):
    if not isinstance(argv, list) or len(argv) < 3 or argv[0] != 'xdg-settings':
        raise ValueError('Refused xdg-settings command: %r' % (argv,))
    if argv == ['xdg-settings', 'get', 'default-web-browser']:
        pass
    elif (len(argv) == 4 and argv[1] == 'set' and argv[2] == 'default-web-browser'
          and DESKTOP_ID.fullmatch(argv[3])):
        pass
    else:
        raise ValueError('Refused xdg-settings command: %r' % (argv,))
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    return completed.returncode, completed.stdout


def current_browser(run=None):
    if run is None:
        run = xdg_settings_run
    code, output = run(['xdg-settings', 'get', 'default-web-browser'])
    if code != 0:
        return None
    desktop_id = output.strip()
    return desktop_id if DESKTOP_ID.fullmatch(desktop_id) else None


def current_terminal(run=None):
    try:
        completed = subprocess.run(['xdg-terminal-exec', '--print-id'],
                                   capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    desktop_id = completed.stdout.strip().split(':', 1)[0]
    return desktop_id if DESKTOP_ID.fullmatch(desktop_id) else None


def rows(kind, run=None):
    candidates = browser_candidates() if kind == 'browser' else terminal_candidates()
    current = current_browser(run) if kind == 'browser' else current_terminal(run)
    allowed = {item['id'] for item in candidates}
    if current not in allowed:
        current = None
    return [{'label': item['label'], 'value': item['id'], 'current': item['id'] == current}
            for item in candidates]


def browser_rows(run=None):
    return rows('browser', run)


def terminal_rows(run=None):
    return rows('terminal', run)


def terminals_list_path(config=None):
    base = _config_home(config)
    for name in (os.environ.get('XDG_CURRENT_DESKTOP') or '').split(':'):
        token = name.strip().lower()
        if token:
            return base / ('%s-xdg-terminals.list' % token)
    return base / 'xdg-terminals.list'


def _clear_terminal_cache():
    cache_root = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    cache = cache_root / 'xdg-terminal-exec'
    try:
        if cache.is_symlink() or cache.is_file():
            cache.unlink()
    except OSError:
        pass


def set_browser(desktop_id, run=None):
    if not DESKTOP_ID.fullmatch(str(desktop_id)):
        return {'ok': False, 'error': 'unknown', 'message': 'Unknown browser.'}
    allowed = {item['id'] for item in browser_candidates()}
    if desktop_id not in allowed:
        return {'ok': False, 'error': 'refused', 'message': 'That browser is not installed.'}
    if run is None:
        run = xdg_settings_run
    code, _ = run(['xdg-settings', 'set', 'default-web-browser', desktop_id])
    if code != 0:
        return {'ok': False, 'error': 'failed', 'message': 'Could not set the default browser.'}
    menu_common.record('default-browser-set', desktop_id, None)
    return {'ok': True, 'desktop': desktop_id}


def set_terminal(desktop_id, config=None):
    if not DESKTOP_ID.fullmatch(str(desktop_id)):
        return {'ok': False, 'error': 'unknown', 'message': 'Unknown terminal.'}
    allowed = {item['id'] for item in terminal_candidates()}
    if desktop_id not in allowed:
        return {'ok': False, 'error': 'refused', 'message': 'That terminal is not installed.'}
    target = terminals_list_path(config)
    payload = desktop_id + '\n'

    def writer(path):
        menu_common.write_text(path, payload)

    backup = menu_common.backup_and_write(target, writer)
    _clear_terminal_cache()
    applied = current_terminal()
    ok = applied == desktop_id
    menu_common.record('default-terminal-set', desktop_id, backup, {'applied': ok})
    if not ok:
        return {'ok': False, 'error': 'failed',
                'message': 'Recorded the terminal preference; xdg-terminal-exec did not switch yet.'}
    return {'ok': True, 'desktop': desktop_id}


def main(argv):
    if argv == ['list-browsers']:
        print(json.dumps({'ok': True, 'rows': browser_rows()}))
        return 0
    if argv == ['list-terminals']:
        print(json.dumps({'ok': True, 'rows': terminal_rows()}))
        return 0
    if argv == ['current-browser']:
        print(json.dumps({'ok': True, 'current': current_browser()}))
        return 0
    if argv == ['current-terminal']:
        print(json.dumps({'ok': True, 'current': current_terminal()}))
        return 0
    if len(argv) == 2 and argv[0] == 'set-browser':
        print(json.dumps(set_browser(argv[1])))
        return 0
    if len(argv) == 2 and argv[0] == 'set-terminal':
        print(json.dumps(set_terminal(argv[1])))
        return 0
    print(json.dumps({'ok': False, 'error': 'usage'}))
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
