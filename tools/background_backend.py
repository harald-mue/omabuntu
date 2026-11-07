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

Hyprlock reads one static path, ~/.local/state/omabuntu/current/lock-background.
set and restore point that symlink at the chosen still after the directory
allowlist has accepted it. They do not run a command at lock time.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import menu_common

ROOT = Path(__file__).resolve().parents[1]
THEME_BACKGROUNDS = ROOT / 'config' / 'menu' / 'backgrounds'
USER_BACKGROUNDS = (Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share')
                   / 'omabuntu' / 'artwork' / 'backgrounds')
USER_PREVIEWS = (Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share')
                 / 'omabuntu' / 'artwork' / 'themes-previews')
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


def _assets(assets=None):
    """Release-imported backgrounds, else the private downloaded artwork.

    Public releases ship artwork-free (redistribution is uncleared); the
    installer downloads the pinned upstream set into the private user
    directory, which the menus then fall back to."""
    if assets is not None:
        return Path(assets)
    release = THEME_BACKGROUNDS
    if release.is_dir() and not release.is_symlink() and any(
            entry.is_dir() and not entry.is_symlink() for entry in release.iterdir()):
        return release
    return USER_BACKGROUNDS


def theme_ids(assets=None):
    assets = _assets(assets)
    if assets.is_symlink() or not assets.is_dir():
        return []
    return sorted(entry.name for entry in assets.iterdir()
                  if entry.is_dir() and not entry.is_symlink())


def theme_backgrounds(theme_id, assets=None):
    """Imported still backgrounds of one theme, sorted like upstream."""
    if not theme_id or '/' in theme_id or theme_id.startswith('.'):
        return []
    return _images(_assets(assets) / theme_id)


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
    candidates = theme_backgrounds(theme_id, assets) if theme_id else all_theme_backgrounds(assets)
    for path in candidates:
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
    if not isinstance(argv, list) or not argv or argv[0] != 'hyprctl' or not 2 <= len(argv) <= 4:
        raise ValueError('Refused hyprctl command: %r' % (argv,))
    if argv[1:3] == ['monitors', '-j'] and len(argv) == 3:
        shape = True
    elif argv == ['hyprctl', 'hyprpaper', 'listactive']:
        shape = True
    elif len(argv) >= 3 and argv[1] == 'hyprpaper' and argv[2] in ('preload', 'wallpaper', 'unload'):
        value = argv[3] if len(argv) == 4 else ''
        shape = bool(value) and '\n' not in value and '\x00' not in value and len(value) <= 4096
    else:
        shape = False
    if not shape:
        raise ValueError('Refused hyprctl command: %r' % (argv,))
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    return completed.returncode, (completed.stdout or '') + (completed.stderr or '')


def _detail(text):
    return ' '.join(str(text).split())[:500]


def _failure(error, message, **extra):
    return {'ok': False, 'method': 'hyprpaper', 'error': error, 'message': message, **extra}


def apply_background(path_text, run=None, timeout=5, wait_seconds=0):
    """Apply to each active output, retaining failure evidence and target status.

    The overall deadline bounds IPC/readiness, never daemon lifetime. Only login
    restoration opts into readiness retries. No service activation or renderer
    replacement. An active-target report is not visual/rendering acceptance.
    """
    path = str(path_text)
    if not path.startswith('/') or any(c in path for c in ('\n', '\r', '\x00', ',')):
        return _failure('path', 'The wallpaper path must be absolute and contain no comma or control separator.')
    run = hyprctl_run if run is None else run
    deadline = time.monotonic() + timeout + wait_seconds

    def request(argv):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(argv, timeout + wait_seconds)
        return run(argv, min(timeout, remaining))

    def failed(code, output, stage):
        detail = _detail(output)
        unavailable = any(s in detail.lower() for s in (
            'failed to connect', "couldn't connect", 'connection refused', 'no such file or directory'))
        error = 'daemon-unavailable' if unavailable and stage != 'monitors' else stage
        return _failure(error, 'Wallpaper ' + stage + ' failed' +
                        (': ' + detail if detail else ' (exit %s).' % code))

    def accepted(argv):
        code, output = request(argv)
        # Modern Hyprwire returns no text; legacy successful replies are "ok".
        if code != 0 or str(output).strip().lower() not in ('', 'ok'):
            return failed(code, output, 'apply')
        return None

    def attempt():
        code, output = request(['hyprctl', 'monitors', '-j'])
        if code != 0:
            return failed(code, output, 'monitors')
        try:
            data = json.loads(output)
        except (ValueError, TypeError):
            return _failure('monitors', 'Hyprland returned an invalid monitor report.')
        if not isinstance(data, list):
            return _failure('monitors', 'Hyprland returned an invalid monitor report.')
        monitors = [m.get('name') for m in data if isinstance(m, dict) and not m.get('disabled')]
        if not monitors:
            return _failure('no-monitors', 'No active Hyprland output is ready for a wallpaper.')
        if any(not isinstance(m, str) or not m or any(c in m for c in ',\n\r\x00') for m in monitors):
            return _failure('monitors', 'Hyprland returned an invalid output name.')
        legacy = False
        for name in monitors:
            failure = accepted(['hyprctl', 'hyprpaper', 'wallpaper', name + ',' + path])
            if failure and not legacy and 'not preloaded' in failure['message'].lower():
                # A positive legacy preload requirement, not a connection,
                # file, handshake, rendering or generic invalid-request error.
                failure = accepted(['hyprctl', 'hyprpaper', 'preload', path])
                if not failure:
                    legacy = True
                    failure = accepted(['hyprctl', 'hyprpaper', 'wallpaper', name + ',' + path])
            if failure:
                return failure
        if legacy:
            # Do not unload all: that would discard other clients' preloads.
            request(['hyprctl', 'hyprpaper', 'unload', path])
        code, output = request(['hyprctl', 'hyprpaper', 'listactive'])
        detail = _detail(output).lower()
        if code != 0 or detail.startswith(('error:', 'err:', 'invalid ', 'unknown ')):
            if any(s in detail for s in ('invalid hyprpaper request', 'unknown request', 'protocol version too low')):
                return {'ok': True, 'method': 'hyprpaper', 'active_reported': None,
                        'message': 'Wallpaper accepted; this daemon cannot report active targets.'}
            return failed(code, output, 'status')
        active = dict(line.split(': ', 1) for line in str(output).splitlines() if ': ' in line)
        missing = [name for name in monitors if active.get(name) != path]
        if missing:
            return _failure('not-active', 'Wallpaper accepted, but hyprpaper did not report the selected image on: '
                            + ', '.join(missing) + '. Check wallpaper diagnostics.', accepted=True)
        return {'ok': True, 'method': 'hyprpaper', 'active_reported': True}

    while True:
        try:
            result = attempt()
        except subprocess.TimeoutExpired:
            return _failure('timeout', 'Wallpaper IPC/readiness timed out. Check hyprpaper and its session socket.')
        except OSError as error:
            return _failure('command', 'Wallpaper command could not run: ' + _detail(error))
        except ValueError as error:
            return _failure('command', 'Wallpaper command was refused: ' + _detail(error))
        if (result['ok'] or not wait_seconds or result.get('error') not in ('daemon-unavailable', 'no-monitors')
                or time.monotonic() + 0.25 >= deadline):
            return result
        time.sleep(0.25)


LOCK_BACKGROUND_NAME = 'lock-background'


def publish_lock_background(resolved, root=None):
    """Point Hyprlock's static symlink at this still.

    Hyprlock 0.9.6 loads one path and does not parse background.json. A
    regular file already at the link path is left untouched. Returns whether
    the symlink now points at the still.
    """
    target = Path(resolved)
    try:
        if target.is_symlink() or not target.is_file():
            return False
        destination = str(target.resolve())
    except OSError:
        return False
    link = menu_common.state_home(root) / 'current' / LOCK_BACKGROUND_NAME
    if not link.is_symlink() and link.exists():
        return False
    temporary = link.with_name(LOCK_BACKGROUND_NAME + '.tmp')
    try:
        if temporary.is_symlink() or temporary.exists():
            temporary.unlink()
        temporary.symlink_to(destination)
        os.replace(temporary, link)
    except OSError:
        return False
    return link.is_symlink() and os.readlink(link) == destination


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
    if any(c in resolved for c in (',', '\n', '\r', '\x00')):
        return {'ok': False, 'error': 'refused',
                'message': 'Wallpaper IPC does not support commas or control separators in file paths.'}
    published = publish_lock_background(resolved, root)
    applied = apply_background(resolved, run)
    payload = {'schema_version': 1, 'path': str(path), 'applied': applied['ok']}
    if not applied['ok']:
        payload['note'] = applied['message']
    target = menu_common.state_home(root) / 'current' / 'background.json'
    backup = menu_common.backup_and_write(
        target, lambda target_path: menu_common.write_json(target_path, payload))
    menu_common.record('background-set', str(path), backup, {'applied': applied['ok']})
    return {'ok': True, 'path': str(path), 'applied': applied['ok'], 'lock_background': published,
            'wallpaper': applied, 'message': applied.get('message', '')}


def resolve_recorded(path_text, assets=None):
    """Recorded path, re-based onto this release when the release moved.

    A recorded still lives under a release's config/menu/backgrounds. After a
    release switch the recorded path names the old release; the same still in
    the selected release wins when it exists there (plan 020)."""
    text = str(path_text)
    marker = '/config/menu/backgrounds/'
    if marker in text:
        relative = text[text.rindex(marker) + len(marker):]
        bases = ([THEME_BACKGROUNDS, USER_BACKGROUNDS] if assets is None
                 else [Path(assets), USER_BACKGROUNDS])
        for base in bases:
            candidate = base / relative
            if (not candidate.is_symlink() and candidate.is_file()
                    and candidate.suffix.lower() in IMAGE_SUFFIXES):
                return candidate
    return Path(text)


def restore_background(run=None, timeout=5, root=None, assets=None, wait_seconds=0):
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
    published = publish_lock_background(resolved, root)
    applied = apply_background(resolved, run, timeout, wait_seconds=wait_seconds)
    return {**applied, 'path': str(path), 'applied': applied['ok'], 'lock_background': published}


def diagnose(run=None, root=None):
    """Read-only bounded guest evidence; never set/restore/start/reload anything.

    Reports may contain private file/display names. Review before sharing.
    Neither active targets nor a healthy process establish rendered pixels.
    """
    commands = {
        'monitors': ['hyprctl', 'monitors', '-j'],
        'active': ['hyprctl', 'hyprpaper', 'listactive'],
        'hyprpaper_version': ['hyprpaper', '--version'],
        'service': ['systemctl', '--user', 'show', 'hyprpaper.service',
                    '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID',
                    '-p', 'ExecMainStatus', '-p', 'NRestarts'],
        'journal': ['journalctl', '--user', '-b', '-u', 'hyprpaper.service', '-n', '30', '--no-pager'],
    }
    if run is None:
        def run(argv, timeout):
            if argv not in commands.values():
                raise ValueError('Refused wallpaper diagnostic command')
            result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
            return result.returncode, (result.stdout or '') + (result.stderr or '')
    probes = {}
    for name, command in commands.items():
        try:
            code, output = run(command, 3)
            probes[name] = {'status': 'ok' if code == 0 else 'failed', 'exit': code,
                            'output': str(output)[:8000]}
        except subprocess.TimeoutExpired:
            probes[name] = {'status': 'timeout'}
        except (OSError, ValueError) as error:
            probes[name] = {'status': 'unavailable', 'message': _detail(error)}
    # menu_common.state_home() creates directories even for a normal reader;
    # diagnostics must not use it (nor rows/current_theme, which call it).
    state = Path(root) if root is not None else Path(os.environ.get('OMABUNTU_STATE_HOME')
                                                     or Path.home() / '.local/state/omabuntu')
    recorded = None
    theme = None
    if any(part.is_symlink() for part in (state, *state.parents, state / 'current')):
        probes['preferences'] = {'status': 'refused', 'message': 'Symlinked preference path was not read.'}
    else:
        record = menu_common.read_json(state / 'current/background.json')
        selection = menu_common.read_json(state / 'current/theme.json')
        recorded = record.get('path') if isinstance(record, dict) else None
        theme = selection.get('name') if isinstance(selection, dict) else None
    images = theme_backgrounds(theme) if isinstance(theme, str) and theme else all_theme_backgrounds()
    images += [image for directory in background_dirs() for image in _images(directory)]
    journal = probes['journal'].get('output', '').lower()
    rendering_errors = [word for word in ('egl_not_initialized', 'failed to create screen',
                        'create_dumb failed', 'gbm', 'segfault', 'status=11/segv') if word in journal]
    return {'ok': all(p['status'] == 'ok' for p in probes.values()),
            'read_only': True, 'rendering_verified': False,
            'environment': {key: os.environ.get(key, '') for key in (
                'XDG_CURRENT_DESKTOP', 'XDG_SESSION_TYPE', 'WAYLAND_DISPLAY',
                'HYPRLAND_INSTANCE_SIGNATURE', 'XDG_RUNTIME_DIR')},
            'recorded': recorded, 'recorded_file_exists': isinstance(recorded, str) and Path(recorded).is_file(),
            'listed_images': min(len(set(map(str, images))), MAX_FILES), 'rendering_error_hints': rendering_errors,
            'probes': probes}


def main(argv):
    if argv == ['diagnose']:
        print(json.dumps(diagnose(), indent=2))
        return 0
    if argv == ['list']:
        print(json.dumps({'ok': True, 'rows': rows()}))
        return 0
    if argv == ['current']:
        print(json.dumps({'ok': True, 'current': current()}))
        return 0
    if argv == ['restore']:
        print(json.dumps(restore_background(wait_seconds=8)))
        return 0
    if len(argv) == 2 and argv[0] == 'set':
        print(json.dumps(set_background(argv[1])))
        return 0
    print(json.dumps({'ok': False, 'error': 'usage'}))
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
