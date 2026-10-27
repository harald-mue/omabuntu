#!/usr/bin/env python3
"""Theme backend for the Omabuntu menu.

Omarchy ships 23 theme palettes under themes/<name>/colors.toml (pinned
commit 03ff1eff) and applies each through omarchy-theme-set, which rewrites
the user's looknfeel configuration and restarts components. This Ubuntu port
keeps the recorded palette data (config/menu/themes.json, see the provenance
record there) and applies a theme in two reviewed steps:

  general:col.active_border   hyprland_active_border, or rgba(<accent>)
  general:col.inactive_border hyprland_inactive_border, or rgba(<muted>)

First the two live window-manager color keywords are applied through
hyprctl (immediate effect, no reload). Because a keyword is transient and
any later config reload falls the values back to whatever hyprland.lua
holds, the same two color literals in the user's ~/.config/hypr/hyprland.lua
are then updated to match the theme (only those two string literals; the
file is backed up first and never reloaded by this backend). A theme whose
palette carries upstream hyprland_active_border values uses those verbatim.
GTK, terminal, and editor color restyling is not attempted; the recorded
palette is read by the bar through its watched state file.

A theme apply also restores that theme's background: the per-theme choice
is kept in current/theme-backgrounds.json, defaulting to the first imported
still of the theme, and applied through background_backend's reviewed path.

CLI: theme_backend.py list [json]
      theme_backend.py current
      theme_backend.py set <theme-id>
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import background_backend
import menu_common

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PALETTES = ROOT / 'config' / 'menu' / 'themes.json'
PREVIEWS = ROOT / 'config' / 'menu' / 'themes-previews'


def palettes_path(explicit=None):
    return Path(explicit or os.environ.get('OMABUNTU_MENU_THEMES') or DEFAULT_PALETTES)


def load_palettes(path=None):
    """Recorded palette data with its provenance check intact."""
    path = palettes_path(path)
    if path.is_symlink() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get('schema_version') != 1 \
            or not isinstance(payload.get('themes'), dict) or not payload['themes']:
        return None
    return payload


def prettify(theme_id):
    """Port of upstream omarchy-theme-list display names (tokyo-night -> Tokyo Night)."""
    words = re.sub(r'(^|-)([a-z])', lambda match: match.group(1) + match.group(2).upper(), theme_id)
    return words.replace('-', ' ')


def _valid_hex(value):
    return bool(re.fullmatch(r'#[0-9A-Fa-f]{6}', str(value or '')))


def rgba(hex_value, alpha='ee'):
    return 'rgba(%s%s)' % (str(hex_value).lstrip('#'), alpha)


def hyprland_colors(palette):
    """The two live border colors for one palette, upstream order preferred."""
    active = palette.get('hyprland_active_border')
    if not active or not re.fullmatch(r'rgba\([0-9A-Fa-f]{6,8}\)(?: rgba\([0-9A-Fa-f]{6,8}\))?(?: \d+deg)?', str(active)):
        active = rgba(palette['accent']) if _valid_hex(palette.get('accent')) else None
    inactive = palette.get('hyprland_inactive_border')
    if not inactive or not re.fullmatch(r'rgba\([0-9A-Fa-f]{6,8}\)', str(inactive)):
        inactive = rgba(palette['muted'], 'aa') if _valid_hex(palette.get('muted')) else None
    return active, inactive


def themes(path=None):
    payload = load_palettes(path)
    return {} if payload is None else {name: data for name, data in payload['themes'].items()
                                       if isinstance(data, dict) and _valid_hex(data.get('accent'))
                                       and _valid_hex(data.get('background'))}


def current(root=None):
    payload = menu_common.read_json(menu_common.state_home(root) / 'current' / 'theme.json')
    return payload.get('name') if isinstance(payload, dict) else None


def preview_path(theme_id):
    """Imported picker preview for one theme, or ''."""
    if not theme_id or '/' in theme_id or theme_id.startswith('.') or theme_id.endswith('.png'):
        return ''
    candidate = PREVIEWS / ('%s.png' % theme_id)
    return str(candidate) if candidate.is_file() and not candidate.is_symlink() else ''


def hyprland_config_path(config_path=None):
    if config_path is not None:
        return Path(config_path)
    config_home = os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config'
    return Path(config_home) / 'hypr' / 'hyprland.lua'


ACTIVE_BORDER_PATTERN = re.compile(r'(active_border\s*=\s*)"[^"]*"')
INACTIVE_BORDER_PATTERN = re.compile(r'(inactive_border\s*=\s*)"[^"]*"')


def rewrite_border_colors(text, active, inactive):
    """Replace only the two border color literals; None when the shape misses."""
    if not ACTIVE_BORDER_PATTERN.search(text) or not INACTIVE_BORDER_PATTERN.search(text):
        return None
    text = ACTIVE_BORDER_PATTERN.sub(lambda match: match.group(1) + '"' + str(active) + '"', text, count=1)
    text = INACTIVE_BORDER_PATTERN.sub(lambda match: match.group(1) + '"' + str(inactive) + '"', text, count=1)
    return text


def persist_border_colors(active, inactive, config_path=None):
    """Update the two color literals in the user's hyprland.lua, backup first.

    Returns True when written, False when the file is missing or its shape
    is not recognized (nothing is written then; the live keyword apply still
    happened). Only the two literals change; the backend never reloads."""
    path = hyprland_config_path(config_path)
    if path.is_symlink() or not path.is_file():
        return False
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return False
    rewritten = rewrite_border_colors(text, active, inactive)
    if rewritten is None or rewritten == text:
        return False
    menu_common.backup_and_write(
        path, lambda target: target.write_text(rewritten, encoding='utf-8'))
    return True


def theme_background_choices(root=None):
    payload = menu_common.read_json(menu_common.state_home(root) / 'current' / 'theme-backgrounds.json')
    themes_map = payload.get('themes') if isinstance(payload, dict) else None
    return themes_map if isinstance(themes_map, dict) else None


def record_theme_background(theme_id, path_text, root=None):
    themes_map = theme_background_choices(root) or {}
    payload = {'schema_version': 1, 'themes': dict(themes_map)}
    payload['themes'][theme_id] = str(path_text)
    target = menu_common.state_home(root) / 'current' / 'theme-backgrounds.json'
    return menu_common.backup_and_write(
        target, lambda path: menu_common.write_json(path, payload))


def theme_background(theme_id, root=None, assets=None):
    """The theme's background: recorded choice, else its first imported still."""
    recorded = (theme_background_choices(root) or {}).get(theme_id)
    if recorded and Path(recorded).is_file():
        return str(recorded)
    images = background_backend.theme_backgrounds(theme_id, assets)
    return str(images[0]) if images else None


def rows(path=None, root=None):
    """Provider rows: label, value, current flag, picker preview, in order."""
    name = current(root)
    return [{'label': prettify(theme_id), 'value': theme_id, 'current': theme_id == name,
             'image': preview_path(theme_id)}
            for theme_id in sorted(themes(path))]


def set_theme(theme_id, path=None, root=None, run=None, config_path=None,
              background_run=None, assets=None):
    available = themes(path)
    if theme_id not in available:
        return {'ok': False, 'error': 'unknown', 'message': 'Unknown theme.'}
    palette = available[theme_id]
    active, inactive = hyprland_colors(palette)
    applied = {}
    if run is None:
        run = hyprctl_run
    if active:
        code, _ = run(['hyprctl', 'keyword', 'general:col.active_border', active])
        if code == 0:
            applied['general:col.active_border'] = active
    if inactive:
        code, _ = run(['hyprctl', 'keyword', 'general:col.inactive_border', inactive])
        if code == 0:
            applied['general:col.inactive_border'] = inactive
    persisted = persist_border_colors(active, inactive, config_path) \
        if active and inactive else False
    background_ok = False
    background_path = theme_background(theme_id, root, assets)
    if background_path:
        background_result = background_backend.set_background(
            background_path, root=root, run=background_run, assets=assets)
        background_ok = bool(background_result.get('ok'))
        if background_ok:
            record_theme_background(theme_id, background_path, root)
    payload = {'schema_version': 1, 'name': theme_id, 'palette': palette, 'hyprland': applied,
               'persisted': persisted, 'background': background_path}
    target = menu_common.state_home(root) / 'current' / 'theme.json'
    backup = menu_common.backup_and_write(
        target, lambda path: menu_common.write_json(path, payload))
    menu_common.record('theme-set', theme_id, backup,
                       {'applied': sorted(applied), 'persisted': persisted,
                        'background': background_path})
    return {'ok': True, 'name': theme_id, 'applied': sorted(applied),
            'persisted': persisted, 'background': background_ok}


def hyprctl_run(argv, timeout=5):
    """One hyprctl keyword command with a fixed, reviewed argument shape."""
    if not isinstance(argv, list) or len(argv) != 4 or argv[0] != 'hyprctl' \
            or argv[1] != 'keyword' or argv[2] not in ('general:col.active_border',
                                                       'general:col.inactive_border') \
            or '\n' in argv[3] or '\x00' in argv[3]:
        raise ValueError('Refused hyprctl command: %r' % (argv,))
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    return completed.returncode, completed.stdout


def main(argv):
    if argv == ['list']:
        print(json.dumps({'ok': True, 'rows': rows()}))
        return 0
    if argv == ['list', 'json']:
        print(json.dumps(themes(), indent=2, sort_keys=True))
        return 0
    if argv == ['current']:
        print(json.dumps({'ok': True, 'current': current()}))
        return 0
    if len(argv) == 2 and argv[0] == 'set':
        print(json.dumps(set_theme(argv[1])))
        return 0
    print(json.dumps({'ok': False, 'error': 'usage'}))
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
