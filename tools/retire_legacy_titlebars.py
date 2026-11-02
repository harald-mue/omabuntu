#!/usr/bin/python3
"""Retire the legacy private hyprbars titlebar wiring (plan 075).

Since the installer-managed carrier owns the granted release titlebars
(plan 073), a private `require("hyprbars")` rules file and the dead
`hyprland.start` handler in the entry configuration duplicate the titlebar
buttons. review is read-only; apply removes the two exact matched blocks
from the entry (with a backup) and retires the private rules file by
renaming it; rollback restores both. Unknown shapes are refused, not
guessed. Nothing is ever reloaded or started here.
"""
import argparse
import datetime
import os
from pathlib import Path
import re
import shutil
import sys

REQUIRE_LINE = 'require("hyprbars")'
HANDLER_BEGIN = 'hl.on("hyprland.start", function()'
HANDLER_END = 'end)'
MANAGED_INCLUDE = 'require("omabuntu-managed")'
ACTIVATION_NAME = 'omabuntu-activation.lua'
RULES_NAME = 'hyprbars.lua'
HANDLER_BODY = [
    'local loaded = false',
    'for _, plugin in ipairs(hl.get_loaded_plugins() or {}) do',
    'if plugin.name == "hyprbars" then',
    'loaded = true',
    'end',
    'end',
    'if not loaded then',
    None,  # hl.plugin.load("<artifact>")
    'end',
]
LOAD_PATTERN = re.compile(r'hl\.plugin\.load\("[^"]+"\)')


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')


def hypr_dir(home):
    config = os.environ.get('XDG_CONFIG_HOME') or str(Path(home) / '.config')
    return Path(config) / 'hypr'


def entry_path(home):
    return hypr_dir(home) / 'hyprland.lua'


def rules_path(home):
    return hypr_dir(home) / RULES_NAME


def activation_path(home):
    return hypr_dir(home) / ACTIVATION_NAME


def check_file(path, label):
    if path.is_symlink() or not path.is_file():
        raise ValueError(label + ' missing or not a regular file: ' + str(path))
    return path


def handler_range(lines):
    """Return (first, last) inclusive indices of the matched handler block.

    None when no handler line exists; 'unknown' when a handler line exists
    but its body does not match the reviewed shape (refused, not guessed).
    """
    for index, line in enumerate(lines):
        if line.strip() != HANDLER_BEGIN:
            continue
        body = []
        cursor = index + 1
        while cursor < len(lines) and lines[cursor].strip() != HANDLER_END:
            body.append(lines[cursor].strip())
            cursor += 1
        if cursor >= len(lines):
            return 'unknown'
        if len(body) != len(HANDLER_BODY):
            return 'unknown'
        for expected, actual in zip(HANDLER_BODY, body):
            if expected is None:
                if not LOAD_PATTERN.fullmatch(actual):
                    return 'unknown'
            elif actual != expected:
                return 'unknown'
        return (index, cursor)
    return None


def comment_block_above(lines, index):
    start = index
    while start > 0 and lines[start - 1].lstrip().startswith('--'):
        start -= 1
    comments = ' '.join(line.strip().lstrip('-').strip() for line in lines[start:index])
    if not any(word in comments.lower() for word in ('hyprbars', 'plugin', 'hyprland.start')):
        return index
    return start


def removal_indices(text):
    lines = text.splitlines(keepends=True)
    remove = set()
    require_at = None
    for index, line in enumerate(lines):
        if line.strip() == REQUIRE_LINE:
            require_at = index
            remove.add(index)
    handler = handler_range(lines)
    handler_unknown = handler == 'unknown'
    if isinstance(handler, tuple):
        first, last = handler
        for index in range(comment_block_above(lines, first), last + 1):
            remove.add(index)
    if require_at is not None:
        for index in range(comment_block_above(lines, require_at), require_at + 1):
            remove.add(index)
    return lines, sorted(remove), require_at is not None, handler, handler_unknown


def review(home=None):
    """Read-only: what the retirement would remove; nothing is written."""
    home = Path(home or os.path.expanduser('~')).absolute()
    entry = entry_path(home)
    rules = rules_path(home)
    activation = activation_path(home)
    result = {'home': home, 'entry': entry, 'rules': rules,
              'entry_exists': entry.is_file() and not entry.is_symlink(),
              'rules_exist': rules.is_file() and not rules.is_symlink(),
              'activation_exist': activation.is_file() and not activation.is_symlink()}
    if result['entry_exists']:
        check_file(entry, 'Entry configuration')
        text = entry.read_text()
        lines, indices, has_require, handler, handler_unknown = removal_indices(text)
        result.update(require_line=has_require,
                       handler=isinstance(handler, tuple),
                       handler_unknown=handler_unknown,
                       managed_include=MANAGED_INCLUDE in text,
                       lines=len(indices))
    else:
        result.update(require_line=False, handler=False, handler_unknown=False,
                      managed_include=False, lines=0)
    return result


def apply(home=None):
    """Remove the matched legacy wiring; back up both files first."""
    info = review(home)
    entry, rules = info['entry'], info['rules']
    if not info['entry_exists']:
        return {'changed': False, 'backup': None, 'retired': None, 'reason': 'no entry configuration'}
    if info['handler_unknown']:
        raise ValueError('Unknown hyprland.start handler shape; edit the entry manually')
    if not (info['require_line'] or info['handler']):
        return {'changed': False, 'backup': None, 'retired': None, 'reason': 'no legacy wiring'}
    if not info['managed_include']:
        raise ValueError('Entry has no managed include; removing the wiring would leave no titlebar rules')
    if not info['activation_exist']:
        raise ValueError('Granted activation file is absent; removing the wiring would leave no titlebar rules')
    backup = entry.with_name(entry.name + '.bak-' + stamp())
    shutil.copy2(entry, backup)
    text = entry.read_text()
    lines, indices, _, _, _ = removal_indices(text)
    kept = [line for index, line in enumerate(lines) if index not in set(indices)]
    entry.write_text(''.join(kept))
    retired = None
    if info['rules_exist']:
        retired = rules.with_name(rules.name + '.bak-' + stamp())
        rules.rename(retired)
    return {'changed': True, 'backup': backup, 'retired': retired, 'reason': 'retired'}


def rollback(home=None):
    """Restore the newest entry backup and rename the rules backup back."""
    home = Path(home or os.path.expanduser('~')).absolute()
    entry, rules = entry_path(home), rules_path(home)
    backups = sorted(entry.parent.glob(entry.name + '.bak-*'))
    restored = None
    if backups:
        entry.write_text(backups[-1].read_text())
        restored = backups[-1]
    retired = sorted(rules.parent.glob(rules.name + '.bak-*'))
    rules_restored = None
    if retired and not rules.exists() and not rules.is_symlink():
        retired[-1].rename(rules)
        rules_restored = rules
    return {'entry_backup': restored, 'rules': rules_restored}


def plan(args):
    info = review(args.home)
    print('Entry:    ' + str(info['entry']) + ' (' + ('present' if info['entry_exists'] else 'absent') + ')')
    print('Rules:    ' + str(info['rules']) + ' (' + ('present' if info['rules_exist'] else 'absent') + ')')
    print('Legacy require line: ' + ('yes' if info['require_line'] else 'no'))
    print('Dead handler block:  ' + ('yes' if info['handler'] else 'no')
          + (' UNKNOWN SHAPE' if info['handler_unknown'] else ''))
    print('Managed include:     ' + ('yes' if info['managed_include'] else 'no'))
    print('Activation file:     ' + ('yes' if info['activation_exist'] else 'no'))
    print('--- apply would ---')
    if not info['entry_exists'] or not (info['require_line'] or info['handler']):
        print('  nothing: no legacy wiring found')
    elif info['handler_unknown']:
        print('  REFUSED: the handler block does not match the reviewed shape')
    else:
        print('  back up the entry to ' + str(info['entry']) + '.bak-<stamp>')
        print('  remove ' + str(info['lines']) + ' matched lines from the entry')
        if info['rules_exist']:
            print('  retire ' + str(info['rules']) + ' by renaming it to .bak-<stamp>')
    print('Apply never reloads Hyprland and never touches anything else.')
    print('Rollback: ' + sys.argv[0] + ' rollback --home ' + str(info['home']))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', default=os.path.expanduser('~'),
                        help='Target home directory (default: the current user)')
    sub = parser.add_subparsers(dest='mode', required=True)
    sub.add_parser('plan', help='Read-only plan: matched lines and exact changes')
    sub.add_parser('apply', help='Back up and remove the legacy wiring; retire the rules file')
    sub.add_parser('rollback', help='Restore the newest backups')
    args = parser.parse_args()
    if args.mode == 'plan':
        return plan(args)
    if args.mode == 'apply':
        result = apply(args.home)
        if not result['changed']:
            print('Nothing to retire: ' + result['reason'])
        else:
            print('Removed the legacy wiring from the entry configuration.')
            print('Entry backup:  ' + str(result['backup']))
            print('Rules retired: ' + (str(result['retired']) if result['retired'] else 'none present'))
            print('A running Hyprland reads the change at its next config reload.')
        return 0
    result = rollback(args.home)
    print('Entry backup restored: ' + (str(result['entry_backup']) or 'none found'))
    print('Rules file restored:   ' + (str(result['rules']) or 'none found'))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        sys.exit(2)