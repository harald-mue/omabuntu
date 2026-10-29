#!/usr/bin/env python3
"""Menu model and guarded dispatch for the Omabuntu command menu.

This is the Python port of the pure model functions in Omarchy's
shell/plugins/menu/MenuModel.js at commit 03ff1eff3812933f7088484533784d2f63eaf19a
(MIT, preserved in licenses/Omarchy-MIT.txt). The parser, merge, and route
functions keep the upstream behavior; the guard batching keeps the one
bash process with grouped subshells and `id:tag:0|1` result lines; the
provider contract keeps `label/value/current` rows. Ubuntu adaptations:
pacman/package presence is dropped (no apt equivalent is approved), the guard
helper vocabulary is omabuntu-*, actions use the reviewed omabuntu registry
instead of arbitrary shell commands, and session-ending actions go through
tools/power_actions.py gates. The dmenu select/input modes, translation
catalogs, and app rows stay excluded (see plans/002-command-menu.md).

CLI (one JSON result line on stdout):
  menu_model.py defs                 normalized merged items + order
  menu_model.py guards              batched guard evaluation results
  menu_model.py providers <menuId>  provider rows for one submenu
  menu_model.py run <id>             allowlisted, gated action dispatch
"""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

import background_backend
import defaults_backend
import font_backend
import menu_common
import power_actions
import theme_backend

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '03ff1eff3812933f7088484533784d2f63eaf19a'
MAX_DEFINITIONS = 262144
GUARD_GROUPS = 8


# ---------------------------------------------------------------- JSONC parse
# Port of MenuModel.js stripJsonc: whole-line // comments and trailing commas.

def strip_jsonc(raw):
    text = re.sub(r'^\s*//[^\n]*(\n|$)', '', str(raw or ''), flags=re.M)
    return re.sub(r',(\s*[}\]])', r'\1', text)


def normalize_aliases(value):
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)] if isinstance(value, str) and value else []


def normalize_item(item_id, raw):
    """Port of MenuModel.js normalizeItem: parent and kind inference."""
    value = raw if isinstance(raw, dict) else {}
    parent = value.get('parent')
    if parent is None:
        parent = '.'.join(item_id.split('.')[:-1]) if '.' in item_id else 'root'
    if item_id == 'root':
        parent = ''
    kind = 'action' if value.get('action') else ('link' if value.get('target') else 'menu')
    return {
        'id': item_id,
        'parent': parent,
        'kind': kind,
        'icon': str(value.get('icon') or ''),
        'iconFont': str(value.get('iconFont') or ''),
        'label': str(value.get('label') or item_id),
        'title': str(value.get('title') or ''),
        'target': str(value.get('target') or ''),
        'description': str(value.get('description') or ''),
        'action': str(value.get('action') or ''),
        'provider': str(value.get('provider') or ''),
        'aliases': normalize_aliases(value.get('aliases')),
        'searchTerms': normalize_aliases(value.get('searchTerms')),
        'when': str(value.get('when') or ''),
        'checked': str(value.get('checked') or ''),
        'disabled': str(value.get('disabled') or ''),
        'order': 0,
    }


def parse_menu_jsonc(raw):
    """Port of MenuModel.js parseMenuJsonc: broken file -> no entries."""
    stripped = strip_jsonc(raw)
    if not stripped.strip():
        return []
    try:
        parsed = json.loads(stripped)
    except ValueError:
        return []
    if not isinstance(parsed, dict):
        return []
    source = parsed.get('items') if isinstance(parsed.get('items'), dict) else parsed
    return [normalize_item(item_id, entry) for item_id, entry in source.items()
            if isinstance(entry, dict)]


def merge_menu_sources(default_items, user_items=None, root_label='Go'):
    """Port of MenuModel.js mergeMenuSources: overlay by key, inject root.

    Upstream normalizes both sources before merging, so a user entry reuses
    the shipped id's position but replaces every normalized field it does
    not declare with the normalize defaults (the documented 'replaces only
    the fields you declare' holds for positions, not sparse fields)."""
    items = {}
    order = []
    for source in (default_items or [], user_items or []):
        for entry in source:
            if not entry or not entry.get('id'):
                continue
            if entry['id'] not in items:
                order.append(entry['id'])
            merged = dict(items.get(entry['id']) or {})
            merged.update(entry)
            merged['id'] = entry['id']
            items[entry['id']] = merged
    if 'root' not in items:
        items['root'] = normalize_item('root', {'label': root_label})
        order.insert(0, 'root')
    for position, item_id in enumerate(order):
        items[item_id]['order'] = position
    return items, order


# ---------------------------------------------------------------- Routes

def definitions_path(explicit=None):
    return Path(explicit or os.environ.get('OMABUNTU_MENU_DEFINITIONS')
                or ROOT / 'config' / 'shell' / 'omabuntu-menu.jsonc')


def user_overlay_path():
    config_home = os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config'
    return Path(config_home) / 'omabuntu' / 'menu.jsonc'


def load_definitions(explicit=None):
    """Merged definitions; a broken file contributes nothing (upstream rule)."""
    path = definitions_path(explicit)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_DEFINITIONS:
        return {}, []
    default_items = parse_menu_jsonc(path.read_text(encoding='utf-8'))
    user_items = []
    overlay = user_overlay_path()
    if overlay.is_file() and not overlay.is_symlink() and overlay.stat().st_size <= MAX_DEFINITIONS:
        user_items = parse_menu_jsonc(overlay.read_text(encoding='utf-8'))
    return merge_menu_sources(default_items, user_items)


def resolve_route(items, order, route):
    """Port of MenuModel.js resolveRoute: exact id beats alias; unknown strings
    fall through as literal ids so a misspelling still attempts that id."""
    raw = str(route or '').lower().replace('_', '-')
    if not raw or raw in ('go', 'menu'):
        return 'root'
    if raw in items:
        return raw
    for item_id in order:
        entry = items.get(item_id)
        if not entry:
            continue
        for alias in entry['aliases']:
            if str(alias).lower().replace('_', '-') == raw:
                return entry['id']
    return raw


def slugify(value):
    """Port of MenuModel.js slugify."""
    text = re.sub(r'[^a-z0-9]+', '-', str(value or '').lower())
    return text.strip('-') or 'item'


# ---------------------------------------------------------------- Guards

# Guard helper vocabulary. These functions are shadowed inside the one batch
# bash process (upstream guardHelpers shadows omarchy-pkg-present and
# friends); they are not installed commands. The state home is passed as $1.

GUARD_HELPERS = (
    'omabuntu-can-suspend() { case "$(cat /sys/power/state 2>/dev/null)" in *mem*|*freeze*) return 0 ;; esac; return 1; }\n'
    'omabuntu-can-hibernate() { case "$(cat /sys/power/state 2>/dev/null)" in *disk*) return 0 ;; esac; return 1; }\n'
    'omabuntu-theme-current() { sed -n \'s/.*"name": *"\\([^"]*\\)".*/\\1/p\' "$1/current/theme.json" 2>/dev/null; }\n'
    'omabuntu-font-current() { cat "$1/current/font.txt" 2>/dev/null; }\n'
    'omabuntu-background-current() { sed -n \'s/.*"path": *"\\([^"]*\\)".*/\\1/p\' "$1/current/background.json" 2>/dev/null; }\n'
)

# Commands a guard expression may read a value from. Rows in one submenu ask
# the same reader, so the batch runs it once and substitutes the captured
# answer (port of GUARD_READERS + substituteGuardReaders).

GUARD_READERS = ('omabuntu-theme-current', 'omabuntu-font-current', 'omabuntu-background-current')


def guard_reader_slot(index):
    return '${__omabuntu_read_%d}' % index


def substitute_guard_readers(expression):
    for index, reader in enumerate(GUARD_READERS):
        expression = expression.replace('$(%s)' % reader, guard_reader_slot(index))
    return expression


def guard_line(item_id, tag, expression):
    return ('if { %s; } >/dev/null 2>&1; then echo %s:%s:1; else echo %s:%s:0; fi\n'
            % (substitute_guard_readers(expression), item_id, tag, item_id, tag))


def guard_prelude(guards, state_home_text=None):
    """Start every wanted reader at once, then collect (port of guardPrelude)."""
    home = menu_common.state_home() if state_home_text is None else Path(state_home_text)
    state = shlex.quote(str(home))
    start = ''
    collect = ''
    for index, reader in enumerate(GUARD_READERS):
        if guard_reader_slot(index) not in guards:
            continue
        start += 'exec {__fd_%d}< <(%s %s 2>/dev/null)\n' % (index, reader, state)
        collect += 'IFS= read -r -d "" __omabuntu_read_%d <&$__fd_%d || :\n' % (index, index)
        collect += 'exec {__fd_%d}<&-\n' % index
        collect += '__omabuntu_read_%d=${__omabuntu_read_%d%%"${__omabuntu_read_%d##*[!$\'\\\\n\']}"}\n' % (index, index, index)
    return start + ''.join(GUARD_HELPERS) + collect


def guard_script(items, state_home_text=None):
    """One bash script for every when/checked/disabled (port of guardScript).

    Guards are dealt round-robin into GUARD_GROUPS background subshells; the
    batch exits nonzero if any group dies. Result lines are `id:tag:0|1`.
    """
    lines = []
    for item_id, entry in items.items():
        for tag, key in (('w', 'when'), ('c', 'checked'), ('d', 'disabled')):
            if entry.get(key):
                lines.append(guard_line(item_id, tag, entry[key]))
    if not lines:
        return ''
    prelude = guard_prelude(''.join(lines), state_home_text)
    groups = [[] for _ in range(GUARD_GROUPS)]
    for position, line in enumerate(lines):
        groups[position % GUARD_GROUPS].append(line)
    script = prelude + '__omabuntu_groups=()\n'
    for group in groups:
        script += '{\n' + ''.join(group) + '} &\n__omabuntu_groups+=($!)\n'
    script += ('__omabuntu_failed=0\n'
               'for __omabuntu_group in "${__omabuntu_groups[@]}"; do wait "$__omabuntu_group" || __omabuntu_failed=1; done\n'
               '((__omabuntu_failed == 0))\n')
    return script


def parse_guard_output(text):
    results = {'when': {}, 'checked': {}, 'disabled': {}}
    for line in str(text or '').splitlines():
        parts = line.split(':')
        if len(parts) != 3 or parts[2] not in ('0', '1'):
            continue
        if parts[1] == 'w':
            results['when'][parts[0]] = parts[2] == '1'
        elif parts[1] == 'c':
            results['checked'][parts[0]] = parts[2] == '1'
        elif parts[1] == 'd':
            results['disabled'][parts[0]] = parts[2] == '1'
    return results


def evaluate_guards(items, run=None):
    script = guard_script(items)
    if not script:
        return {'when': {}, 'checked': {}, 'disabled': {}}
    if run is None:
        run = guard_run
    code, output = run(script)
    if code != 0 and not output:
        return {'when': {}, 'checked': {}, 'disabled': {}}
    return parse_guard_output(output)


def guard_run(script, timeout=8):
    if not isinstance(script, str) or '\x00' in script or len(script) > MAX_DEFINITIONS * 4:
        raise ValueError('Refused guard script')
    completed = subprocess.run(['bash'], input=script, capture_output=True, text=True,
                               timeout=timeout, check=False)
    return completed.returncode, completed.stdout


# ---------------------------------------------------------------- Providers

PROVIDERS = {'themes', 'backgrounds', 'fonts', 'default-browsers', 'default-terminals'}


def provider_rows(provider, palettes_path=None, state_root=None, dirs=None, font_output=None):
    """Rows for one provider: label, value, current (upstream contract)."""
    if provider == 'themes':
        rows = theme_backend.rows(palettes_path, state_root)
        palettes = theme_backend.themes(palettes_path)
        for row in rows:
            palette = palettes.get(row['value']) or {}
            row['colors'] = {key: value for key, value in
                             ((key, palette.get(key)) for key in
                              ('background', 'foreground', 'accent', 'blue', 'green',
                               'yellow', 'red', 'magenta', 'cyan', 'mode'))
                             if isinstance(value, str) and value}
        return rows
    if provider == 'backgrounds':
        return background_backend.rows(dirs, state_root)
    if provider == 'fonts':
        available = font_backend.families(font_output)
        return font_backend.rows(state_root, available)
    if provider == 'default-browsers':
        return defaults_backend.browser_rows()
    if provider == 'default-terminals':
        return defaults_backend.terminal_rows()
    return None


def provider_row_ids(menu_id, rows):
    """Row ids are `<menuId>.<slug>` with a `-` appended on collision
    (upstream mergeProviderRows rule)."""
    ids = {}
    result = []
    for row in rows:
        row_id = '%s.%s' % (menu_id, slugify(row['value']))
        while row_id in ids:
            row_id += '-'
        ids[row_id] = True
        result.append(dict(row, id=row_id))
    return result


def provider_for_menu(items, menu_id):
    entry = items.get(menu_id)
    return entry.get('provider') if entry else ''


def provider_row_for(items, row_id):
    """Re-derive one provider row by its id, re-enumerating the provider.
    Dispatch never trusts a value the surface sent; it finds the row again."""
    if row_id.count('.') < 1:
        return None
    menu_id = row_id.rsplit('.', 1)[0]
    provider = provider_for_menu(items, menu_id)
    if provider not in PROVIDERS:
        return None
    for row in provider_row_ids(menu_id, provider_rows(provider) or []):
        if row['id'] == row_id:
            return provider, row
    return None


# ---------------------------------------------------------------- Dispatch

# The action registry. Upstream actions are arbitrary shell commands run
# detached; this Ubuntu adaptation maps a reviewed prefix per action family
# and refuses every other form. The allowlist is built from the definitions:
# an id absent from them, or a provider row that is no longer enumerated,
# is refused.

ACTION_RE = re.compile(r'^(omabuntu-open:(apps|keybindings|themes|backgrounds)|omabuntu-session:(lock|screenshot)|xdg-open:https://[A-Za-z0-9./_-]+/?|systemctl:(suspend|hibernate|reboot|poweroff)|uwsm:stop)$')


def launch_session_action(action):
    """Launch one reviewed action without a menu-process lifetime limit.

    No shell, captured credentials or inherited JSON stdout. These children
    survive the menu closing; only the existing lock manager owns locking.
    """
    if action == 'omabuntu-session:lock':
        executable = Path.home() / '.local/bin/omabuntu'
        if executable.is_symlink() or not executable.is_file() or not os.access(executable, os.X_OK):
            return {'ok': False, 'error': 'missing', 'message': 'Installed lock manager is missing.'}
        command = [str(executable), 'lock', '--apply']
    elif action == 'omabuntu-session:screenshot':
        helper = Path(__file__).resolve().parent / 'capture_screenshot.py'
        import capture_screenshot
        try:
            capture_screenshot.approved_binary(os.environ)
        except ValueError as error:
            return {'ok': False, 'error': 'missing', 'message': str(error)}
        if helper.is_symlink() or not helper.is_file():
            return {'ok': False, 'error': 'missing', 'message': 'Screenshot helper is missing.'}
        command = [sys.executable, str(helper)]
    else:
        return {'ok': False, 'error': 'refused'}
    try:
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return {'ok': False, 'error': 'failed', 'message': 'Could not start the requested action.'}
    return {'ok': True, 'status': 'started-not-accepted'}


def _run_action(action, run=None, palettes_path=None, state_root=None, dirs=None, font_output=None):
    """Execute one registry action; session-ending verbs go through gates."""
    if action.startswith('omabuntu-session:'):
        return launch_session_action(action)
    if action.startswith('omabuntu-open:'):
        # Surface-side routes; the helper never receives them. Refuse here so
        # a forged request cannot relaunch or focus anything.
        return {'ok': False, 'error': 'refused', 'message': 'That route is menu-internal.'}
    if action.startswith('xdg-open:'):
        url = action[len('xdg-open:'):]
        if run is None:
            run = open_run
        code, _ = run(['xdg-open', url])
        return {'ok': code == 0} if code == 0 else {'ok': False, 'error': 'failed'}
    if action.startswith('systemctl:'):
        verb = action.split(':', 1)[1]
        return power_actions.perform(verb, run=run)
    if action == 'uwsm:stop':
        return power_actions.perform('logout', run=run)
    return {'ok': False, 'error': 'refused'}


def run_item(row_id, definitions=None, run=None):
    """Allowlisted dispatch for one row id. Returns a JSON-serializable dict."""
    items, order = definitions if definitions is not None else load_definitions()
    entry = items.get(row_id)
    if entry is None:
        found = provider_row_for(items, row_id)
        if found is None:
            return {'ok': False, 'error': 'unknown', 'message': 'That row is not in the menu.'}
        provider, row = found
        if provider == 'themes':
            return theme_backend.set_theme(row['value'])
        if provider == 'fonts':
            return font_backend.set_font(row['value'])
        if provider == 'backgrounds':
            return background_backend.set_background(row['value'])
        if provider == 'default-browsers':
            return defaults_backend.set_browser(row['value'])
        if provider == 'default-terminals':
            return defaults_backend.set_terminal(row['value'])
        return {'ok': False, 'error': 'refused'}
    action = entry.get('action')
    if not action or not ACTION_RE.fullmatch(action):
        return {'ok': False, 'error': 'refused', 'message': 'That action is not allowed here.'}
    return _run_action(action, run=run)


def open_run(argv, timeout=6):
    if not isinstance(argv, list) or len(argv) != 2 or argv[0] != 'xdg-open' \
            or not argv[1].startswith('https://') or len(argv[1]) > 512:
        raise ValueError('Refused open command: %r' % (argv,))
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    return completed.returncode, completed.stdout


# ---------------------------------------------------------------- CLI

def menu_palette(root=None):
    """Background, text, and accent for the open card.

    Omarchy reads these from the theme's menu section. This bar has the
    recorded palette only, so the card uses that palette's background,
    foreground, and accent. Missing state keeps the bar colors.
    """
    fallback = {'background': '#101315', 'foreground': '#cacccc', 'accent': '#cacccc'}
    name = theme_backend.current(root)
    palette = theme_backend.themes().get(name) if isinstance(name, str) else None
    if not isinstance(palette, dict):
        return fallback
    result = {}
    for key, default in fallback.items():
        value = palette.get(key)
        result[key] = value if theme_backend._valid_hex(value) else default
    return result


def main(argv):
    if argv == ['defs']:
        items, order = load_definitions()
        print(json.dumps({'ok': True, 'items': items, 'itemOrder': order,
                          'palette': menu_palette()}))
        return 0
    if argv == ['guards']:
        items, _ = load_definitions()
        print(json.dumps({'ok': True, 'results': evaluate_guards(items)}))
        return 0
    if len(argv) == 2 and argv[0] == 'providers':
        items, _ = load_definitions()
        provider = provider_for_menu(items, argv[1])
        if provider not in PROVIDERS:
            print(json.dumps({'ok': False, 'error': 'unknown'}))
            return 0
        rows = provider_row_ids(argv[1], provider_rows(provider) or [])
        print(json.dumps({'ok': True, 'rows': rows}))
        return 0
    if len(argv) == 2 and argv[0] == 'run':
        print(json.dumps(run_item(argv[1])))
        return 0
    print(json.dumps({'ok': False, 'error': 'usage'}))
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
