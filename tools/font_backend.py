#!/usr/bin/env python3
"""Font backend for the Omabuntu menu.

Upstream opens a volatile `fonts` provider (Menu.qml providers map) that
lists families through omarchy-font-list and applies the choice with
omarchy-font-set, which rewrites the terminal font configuration, makes
fontconfig resolve `monospace` to the chosen family (the canonical source
for the shell, Qt, and anything resolving monospace), and restarts the
shell. This Ubuntu adaptation lists families through fontconfig (fc-list)
and applies the choice in the same reviewed three steps, each backed up:

  1. ~/.config/fontconfig/fonts.conf  monospace -> family prepend_first
     (the upstream mechanism, byte-for-byte its XML shape)
  2. the ghostty config's font-family lines, when a ghostty config file
     exists, plus a SIGUSR2 reload signal to running ghostty processes
  3. gsettings org.gnome.desktop.interface font-name for GTK apps
     (an Omabuntu extra; upstream does not set gsettings)

The applied family is recorded in the state directory; the bar reads it
from current/font.txt through its watched state file, so no restart is
needed for later changes. The size in the existing gsettings value is
preserved; the default is 11.

CLI: font_backend.py list | current | set <family>
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import menu_common

MAX_FAMILIES = 4096
DEFAULT_SIZE = 11
FONTCONFIG_MAX = 262144
QUOTED_FONT_FAMILY = re.compile(r'(^\s*font-family\s*=\s*)"[^"]*"', re.M)
BARE_FONT_FAMILY = re.compile(r'(^[ \t]*font-family[ \t]*=[ \t]*)[^\s"#][^\n]*', re.M)


def families(output=None):
    """Sorted unique family names from `fc-list --format %{family}` output."""
    if output is None:
        try:
            completed = subprocess.run(['fc-list', '--format', '%{family[0]}\n'],
                                       capture_output=True, text=True, timeout=8, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return []
        if completed.returncode != 0:
            return []
        output = completed.stdout
    names = set()
    for line in str(output).splitlines():
        name = line.strip()
        if name and len(name) <= 128 and '\x00' not in name:
            names.add(name)
    return sorted(names)[:MAX_FAMILIES]


def current(root=None):
    path = menu_common.state_home(root) / 'current' / 'font.txt'
    if path.is_symlink() or not path.is_file():
        return None
    try:
        text = path.read_text(encoding='utf-8').strip()
    except OSError:
        return None
    return text or None


def rows(root=None, available=None):
    """Provider rows. `font` renders each entry in its own family in the card."""
    name = current(root)
    available = families() if available is None else available
    return [{'label': family, 'value': family, 'current': family == name, 'font': family}
            for family in available]


def gsettings_font(family, previous=None, size_default=DEFAULT_SIZE):
    """GTK font-name value for a family, keeping a previous size when present."""
    size = size_default
    if previous:
        match = re.search(r'\s(\d{1,3})$', str(previous))
        if match:
            size = int(match.group(1))
    return '%s %d' % (family, size)


def xml_escape(value):
    return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def fontconfig_xml(family):
    """The upstream fonts.conf document, one family substituted."""
    return ('<?xml version="1.0"?>\n'
            '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
            '<fontconfig>\n'
            '  <match target="pattern">\n'
            '    <test name="family" qual="any">\n'
            '      <string>monospace</string>\n'
            '    </test>\n'
            '    <edit name="family" mode="prepend_first" binding="strong">\n'
            '      <string>%s</string>\n'
            '    </edit>\n'
            '  </match>\n'
            '</fontconfig>\n') % xml_escape(family)


def config_home(config=None):
    return Path(config) if config is not None else Path(
        os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')


def fontconfig_path(config=None):
    return config_home(config) / 'fontconfig' / 'fonts.conf'


def write_fontconfig(family, config=None):
    """Write the monospace prepend document, backup first. True when written."""
    target = fontconfig_path(config)
    if target.is_symlink() or (target.exists() and target.stat().st_size > FONTCONFIG_MAX):
        return False
    text = fontconfig_xml(family)
    menu_common.backup_and_write(
        target, lambda path: menu_common.write_text(path, text))
    return True


def ghostty_config_paths(config=None):
    """Existing ghostty config files, checked names only."""
    directory = config_home(config) / 'ghostty'
    if directory.is_symlink() or not directory.is_dir():
        return []
    return [path for path in (directory / 'config', directory / 'config.ghostty')
            if path.is_file() and not path.is_symlink()]


def rewrite_ghostty_font(text, family):
    """Replace font-family values (quoted or bare); None when none present."""
    if QUOTED_FONT_FAMILY.search(text):
        return QUOTED_FONT_FAMILY.sub(lambda match: match.group(1) + '"' + family + '"', text)
    if BARE_FONT_FAMILY.search(text):
        return BARE_FONT_FAMILY.sub(lambda match: match.group(1) + '"' + family + '"', text)
    return None


def write_ghostty(family, config=None):
    """Rewrite font-family in existing ghostty configs, backup first.

    Returns the list of written paths; a config without a font-family line
    stays untouched (upstream appends one; no new keys are invented here)."""
    written = []
    for path in ghostty_config_paths(config):
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            continue
        rewritten = rewrite_ghostty_font(text, family)
        if rewritten is None or rewritten == text:
            continue
        menu_common.backup_and_write(
            path, lambda target: target.write_text(rewritten, encoding='utf-8'))
        written.append(str(path))
    return written


def set_font(family, root=None, available=None, run=None, signal_run=None,
             config=None):
    available = families() if available is None else available
    if family not in available:
        return {'ok': False, 'error': 'unknown', 'message': 'Unknown font family.'}
    if run is None:
        run = gsettings_run
    if signal_run is None:
        signal_run = pkill_run
    previous = None
    read = run(['gsettings', 'get', 'org.gnome.desktop.interface', 'font-name'])
    if read[0] == 0:
        previous = str(read[1]).strip().strip("'")
    value = gsettings_font(family, previous)
    gtk = run(['gsettings', 'set', 'org.gnome.desktop.interface', 'font-name', value])[0] == 0
    fontconfig = write_fontconfig(family, config)
    ghostty = write_ghostty(family, config)
    if ghostty:
        signal_run(['pkill', '-SIGUSR2', '-x', 'ghostty'])
    target = menu_common.state_home(root) / 'current' / 'font.txt'
    backup = menu_common.backup_and_write(
        target, lambda path: menu_common.write_text(path, family + '\n'))
    menu_common.record('font-set', family, backup,
                       {'gtk': gtk, 'value': value, 'fontconfig': fontconfig,
                        'ghostty': ghostty})
    return {'ok': True, 'name': family, 'gtk': gtk, 'fontconfig': fontconfig,
            'ghostty': ghostty}


def gsettings_run(argv, timeout=5):
    """One reviewed gsettings read or write for the interface font."""
    if not isinstance(argv, list) or len(argv) not in (4, 5) or argv[0] != 'gsettings' \
            or argv[1] not in ('get', 'set') or argv[2:4] != ['org.gnome.desktop.interface', 'font-name']:
        raise ValueError('Refused gsettings command: %r' % (argv,))
    if len(argv) == 5 and ('\n' in argv[4] or '\x00' in argv[4] or len(argv[4]) > 128):
        raise ValueError('Refused gsettings value')
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    return completed.returncode, completed.stdout


def pkill_run(argv, timeout=5):
    """One reviewed reload signal; exactly ghostty SIGUSR2, nothing else."""
    if not isinstance(argv, list) or argv != ['pkill', '-SIGUSR2', '-x', 'ghostty']:
        raise ValueError('Refused signal command: %r' % (argv,))
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    return completed.returncode, completed.stdout


def main(argv):
    if argv == ['list']:
        print(json.dumps({'ok': True, 'rows': rows()}))
        return 0
    if argv == ['current']:
        print(json.dumps({'ok': True, 'current': current()}))
        return 0
    if len(argv) == 2 and argv[0] == 'set':
        print(json.dumps(set_font(argv[1])))
        return 0
    print(json.dumps({'ok': False, 'error': 'usage'}))
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
