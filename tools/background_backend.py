#!/usr/bin/env python3
"""Background backend for the Omabuntu menu.

Upstream picks backgrounds through omarchy-theme-bg-switcher (the current
theme's `themes/<theme>/backgrounds/` set plus user extras in
`~/.config/omarchy/backgrounds/<theme>`), applies the choice with
omarchy-theme-bg-set, and repaints through the Omarchy shell's own
wallpaper engine. Ubuntu remains the managed operating system here and no
Omarchy wallpaper engine exists in this port: the recorded upstream stills
(imported under config/menu/backgrounds by tools/import_theme_backgrounds.py)
are listed for the current theme first, then Ubuntu's own
/usr/share/backgrounds images and files the user placed directly in
~/Pictures, in that order.

Applying stays reversible: the chosen file is recorded in the state
directory, and when a hyprpaper wallpaper daemon is running in the live
session the still is preloaded and set per monitor through
`hyprctl hyprpaper` (no service activation of its own, no daemon started
here). When no daemon answers, the choice is recorded and `applied` stays
false. Video wallpapers, intro videos, and transition caches are excluded.

CLI: background_backend.py list | current | set <file>
"""
import json
import os
from pathlib import Path
import subprocess
import sys

import menu_common

ROOT = Path(__file__).resolve().parents[1]
THEME_BACKGROUNDS = ROOT / 'config' / 'menu' / 'backgrounds'
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_FILES = 512
MAX_LABEL = 96


def _images(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        return []
    found = []
    for entry in sorted(directory.iterdir()):
        if entry.is_symlink() or not entry.is_file():
            continue
        if entry.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        try:
            if entry.stat().st_size == 0 or entry.stat().st_size > 64 * 1024 * 1024:
                continue
        except OSError:
            continue
        found.append(entry)
        if len(found) >= MAX_FILES:
            break
    return found


def theme_ids(assets=None):
    assets = Path(assets) if assets is not None else THEME_BACKGROUNDS
    if assets.is_symlink() or not assets.is_dir():
        return []
    return sorted(entry.name for entry in assets.iterdir()
                  if entry.is_dir() and not entry.is_symlink())


def theme_backgrounds(theme_id, assets=None):
    """Imported still backgrounds of one theme, sorted like upstream."""
    if not theme_id or '/' in theme_id or theme_id.startswith('.'):
        return []
    return _images((Path(assets) if assets is not None else THEME_BACKGROUNDS) / theme_id)


def all_theme_backgrounds(assets=None):
    files = []
    for theme_id in theme_ids(assets):
        files.extend(theme_backgrounds(theme_id, assets))
    return files


def current_theme(root=None):
    """Applied theme id from the state directory, or None.

    Imported lazily: theme_backend imports this module for the theme apply,
    so a top-level import would be circular."""
    import theme_backend
    return theme_backend.current(root)


def background_dirs(home=None):
    home = Path(home) if home is not None else Path.home()
    return [Path('/usr/share/backgrounds'), home / 'Pictures']


def backgrounds(dirs=None, root=None, assets=None):
    """Listed backgrounds: current theme's set first, then the Ubuntu dirs."""
    files = []
    seen = set()
    theme_id = current_theme(root)
    if theme_id:
        for path in theme_backgrounds(theme_id, assets):
            real = path.resolve()
            if real not in seen:
                seen.add(real)
                files.append(path)
    dirs = background_dirs() if dirs is None else [Path(d) for d in dirs]
    for directory in dirs:
        for path in _images(directory):
            real = path.resolve()
            if real in seen:
                continue
            seen.add(real)
            files.append(path)
    return files[:MAX_FILES]


def allowed_paths(dirs=None, root=None, assets=None):
    """Every settable background: all imported theme stills plus the dirs.

    All themes, not just the current one: a theme apply sets that theme's
    own background through the same reviewed path."""
    files = all_theme_backgrounds(assets) + backgrounds(dirs, root, assets)
    result = set()
    for path in files:
        try:
            result.add(str(path.resolve()))
        except OSError:
            result.add(str(path.absolute()))
    return result


def current(root=None):
    payload = menu_common.read_json(menu_common.state_home(root) / 'current' / 'background.json')
    return payload.get('path') if isinstance(payload, dict) else None


def rows(dirs=None, root=None, assets=None):
    name = current(root)
    return [{'label': path.name[:MAX_LABEL], 'value': str(path), 'current': str(path) == name}
            for path in backgrounds(dirs, root, assets)]


def hyprctl_run(argv, timeout=5):
    """One reviewed hyprctl hyprpaper or monitors command, list argv only."""
    if not isinstance(argv, list) or argv[0] != 'hyprctl' or len(argv) > 5:
        raise ValueError('Refused hyprctl command: %r' % (argv,))
    if argv[1:3] == ['monitors', '-j'] and len(argv) == 3:
        shape = True
    elif argv[1] == 'hyprpaper' and argv[2] in ('preload', 'wallpaper', 'unload'):
        value = argv[3] if len(argv) == 4 else ''
        shape = bool(value) and '\n' not in value and '\x00' not in value and len(value) <= 4096
    else:
        shape = False
    if not shape:
        raise ValueError('Refused hyprctl command: %r' % (argv,))
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    return completed.returncode, completed.stdout


def monitor_names(run=None, timeout=5):
    """Output names from `hyprctl monitors -j`, empty when Hyprland is away."""
    if run is None:
        run = hyprctl_run
    try:
        code, output = run(['hyprctl', 'monitors', '-j'])
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return []
    if code != 0:
        return []
    try:
        monitors = json.loads(str(output))
    except ValueError:
        return []
    if not isinstance(monitors, list):
        return []
    return [entry.get('name') for entry in monitors
            if isinstance(entry, dict) and isinstance(entry.get('name'), str) and entry.get('name')]


def _legacy_wallpaper(path, monitors, run, timeout):
    """Preload/wallpaper/unload sequence of hyprpaper before 0.8.4."""
    try:
        if run(['hyprctl', 'hyprpaper', 'preload', path], timeout)[0] != 0:
            return {'ok': False, 'method': 'hyprpaper'}
        for name in monitors:
            if run(['hyprctl', 'hyprpaper', 'wallpaper', '%s,%s' % (name, path)], timeout)[0] != 0:
                return {'ok': False, 'method': 'hyprpaper'}
        run(['hyprctl', 'hyprpaper', 'unload', 'all'], timeout)
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return {'ok': False, 'method': 'hyprpaper'}
    return {'ok': True, 'method': 'hyprpaper'}


def apply_background(path_text, run=None, timeout=5):
    """Set the still through a running hyprpaper daemon.

    hyprpaper 0.8.4 replaced the preload/wallpaper/unload requests with a
    single per-output `wallpaper <mon>,<path>` request; that shape is tried
    first and only an older daemon falls back to the legacy sequence.
    Returns {'ok': True/False, 'method': 'hyprpaper'}; any refused or failing
    step means not applied, never a crash."""
    path = str(path_text)
    if run is None:
        run = hyprctl_run
    monitors = monitor_names(run, timeout)
    if not monitors:
        return {'ok': False, 'method': 'hyprpaper'}
    accepted = True
    for name in monitors:
        try:
            code = run(['hyprctl', 'hyprpaper', 'wallpaper', '%s,%s' % (name, path)], timeout)[0]
        except (ValueError, OSError, subprocess.TimeoutExpired):
            return {'ok': False, 'method': 'hyprpaper'}
        if code != 0:
            accepted = False
            break
    if accepted:
        return {'ok': True, 'method': 'hyprpaper'}
    return _legacy_wallpaper(path, monitors, run, timeout)


def set_background(path_text, dirs=None, root=None, run=None, assets=None):
    path = Path(path_text)
    if path.is_symlink() or not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
        return {'ok': False, 'error': 'unknown', 'message': 'Unknown background file.'}
    allowed = allowed_paths(dirs, root, assets)
    try:
        resolved = str(path.resolve())
    except OSError:
        resolved = str(path.absolute())
    if resolved not in allowed:
        return {'ok': False, 'error': 'refused', 'message': 'Background is outside the listed directories.'}
    applied = apply_background(resolved, run)
    payload = {'schema_version': 1, 'path': str(path), 'applied': applied['ok']}
    if not applied['ok']:
        payload['note'] = 'Recorded; no wallpaper daemon answered (hyprpaper is not running).'
    target = menu_common.state_home(root) / 'current' / 'background.json'
    backup = menu_common.backup_and_write(
        target, lambda target_path: menu_common.write_json(target_path, payload))
    menu_common.record('background-set', str(path), backup, {'applied': applied['ok']})
    return {'ok': True, 'path': str(path), 'applied': applied['ok']}


def resolve_recorded(path_text, assets=None):
    """Recorded path, re-based onto this release when the release moved.

    A recorded still lives under a release's config/menu/backgrounds. After a
    release switch the recorded path names the old release; the same still in
    the selected release wins when it exists there (plan 020)."""
    text = str(path_text)
    marker = '/config/menu/backgrounds/'
    if marker in text:
        relative = text[text.rindex(marker) + len(marker):]
        candidate = (Path(assets) if assets is not None else THEME_BACKGROUNDS) / relative
        if (not candidate.is_symlink() and candidate.is_file()
                and candidate.suffix.lower() in IMAGE_SUFFIXES):
            return candidate
    return Path(text)


def restore_background(run=None, timeout=5, root=None, assets=None):
    """Apply the recorded background without re-recording it (plan 020).

    Best-effort login restore: a missing record, file, daemon or a refusal
    is reported, never raised."""
    path_text = current(root)
    if not path_text or not isinstance(path_text, str) or '\n' in path_text:
        return {'ok': False, 'error': 'unrecorded', 'message': 'No background is recorded.'}
    path = resolve_recorded(path_text, assets)
    if path.is_symlink() or not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
        return {'ok': False, 'error': 'missing', 'message': 'The recorded background is gone.'}
    allowed = allowed_paths(root=root, assets=assets)
    try:
        resolved = str(path.resolve())
    except OSError:
        resolved = str(path.absolute())
    if resolved not in allowed:
        return {'ok': False, 'error': 'refused',
                'message': 'The recorded background is outside the listed directories.'}
    applied = apply_background(resolved, run, timeout)
    return {'ok': applied['ok'], 'path': str(path), 'applied': applied['ok'], 'method': applied['method']}


def main(argv):
    if argv == ['list']:
        print(json.dumps({'ok': True, 'rows': rows()}))
        return 0
    if argv == ['current']:
        print(json.dumps({'ok': True, 'current': current()}))
        return 0
    if argv == ['restore']:
        print(json.dumps(restore_background()))
        return 0
    if len(argv) == 2 and argv[0] == 'set':
        print(json.dumps(set_background(argv[1])))
        return 0
    print(json.dumps({'ok': False, 'error': 'usage'}))
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
