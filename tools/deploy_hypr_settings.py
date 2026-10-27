#!/usr/bin/env python3
"""Deploy the installer-managed Hyprland settings (plan 018).

Read-only plan by default. Apply writes the managed snippet and ensures exactly
one require line in the user's hyprland.lua, with a backup before any change.
Remove is the rollback. Never reloads Hyprland and never touches systemd.
Uses only the Python standard library.
"""
import argparse
import datetime
import difflib
import os
from pathlib import Path
import shutil
import sys

MANAGED_NAME = 'omabuntu-managed.lua'
REQUIRE_LINE = 'require("omabuntu-managed")'
MARKER = '-- Omabuntu installer-managed settings (plan 018)'
TEMPLATE = Path(__file__).resolve().parent.parent / 'config/hypr' / MANAGED_NAME


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')


def hypr_dir(home):
    return Path(home) / '.config/hypr'


def managed_target(home):
    return hypr_dir(home) / MANAGED_NAME


def config_target(home):
    return hypr_dir(home) / 'hyprland.lua'


def check_home(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('Parent traversal is not allowed')
    for part in [*reversed(path.parents), path, path / '.config', hypr_dir(path)]:
        if part.is_symlink() or (part.exists() and not part.is_dir()):
            raise ValueError('Unsafe configuration directory: ' + str(part))
    if not path.is_dir():
        raise ValueError('Home directory does not exist: ' + str(path))
    return path


def load_text(path, label):
    if path.is_symlink() or not path.is_file():
        raise ValueError(label + ' missing or not a regular file: ' + str(path))
    text = path.read_text()
    if not text.endswith('\n'):
        raise ValueError(label + ' must end with a newline')
    return text


def managed_names(text):
    """Lines that mention the managed snippet, exact or not."""
    return [line for line in text.splitlines() if 'omabuntu-managed' in line]


def include_lines(text):
    return [line for line in managed_names(text) if line.strip() == REQUIRE_LINE]


def verify_config(text, path):
    names = managed_names(text)
    includes = include_lines(text)
    if names and (not includes or len(names) != len(includes)):
        raise ValueError('A different omabuntu-managed reference exists in '
                         + str(path) + '; resolve it manually: ' + repr(names[0]))
    if len(includes) > 1:
        raise ValueError('More than one managed include line in ' + str(path))
    return includes


def backup(path):
    target = path.with_name(path.name + '.bak-' + stamp())
    shutil.copy2(path, target)
    print('Backed up ' + str(path) + ' to ' + str(target))
    return target


def write_managed(home, text, *, dry_run):
    target = managed_target(home)
    if target.is_symlink():
        raise ValueError('Refusing symlinked managed file: ' + str(target))
    existing = target.read_text() if target.is_file() else None
    if existing == text:
        print('Managed file already current: ' + str(target))
        return
    if dry_run:
        print('Dry run: would write ' + str(target))
        return
    if existing is not None:
        backup(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    print('Wrote ' + str(target))


def ensure_include(home, *, dry_run):
    target = config_target(home)
    text = load_text(target, 'Hyprland configuration')
    includes = verify_config(text, target)
    if includes:
        print('Include already present: ' + REQUIRE_LINE)
        return
    if dry_run:
        print('Dry run: would append ' + REQUIRE_LINE + ' to ' + str(target))
        return
    backup(target)
    addition = '\n' + MARKER + '\n' + REQUIRE_LINE + '\n'
    target.write_text(text + addition)
    print('Appended the managed include to ' + str(target))


def remove_include(home, *, dry_run):
    target = config_target(home)
    if not target.is_file() or target.is_symlink():
        print('No Hyprland configuration at ' + str(target) + '; nothing to remove.')
        return
    text = target.read_text()
    verify_config(text, target)
    if not include_lines(text):
        print('No managed include in ' + str(target) + '; nothing to remove.')
        return
    if dry_run:
        print('Dry run: would remove ' + REQUIRE_LINE + ' from ' + str(target))
        return
    backup(target)
    block = MARKER + '\n' + REQUIRE_LINE + '\n'
    if text.count(block) == 1:
        # Remove exactly the block this tool appended, including its separator.
        for separator in ('\n' + block, block):
            if text.endswith(separator):
                text = text[:-len(separator)]
                break
        else:
            text = text.replace(block, '', 1)
    else:
        text = ''.join(line for line in text.splitlines(keepends=True)
                       if line.strip() != REQUIRE_LINE)
    target.write_text(text)
    print('Removed the managed include from ' + str(target))


def validate(home):
    config = config_target(home)
    text = load_text(config, 'Hyprland configuration')
    verify_config(text, config)
    target = managed_target(home)
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError('Unsafe managed file: ' + str(target))
    return text


def show_diff(home):
    text = validate(home)
    managed = managed_target(home)
    before = managed.read_text() if managed.exists() else ''
    after = load_text(TEMPLATE, 'Managed template')
    changes = [(managed, before, after)]
    if not include_lines(text):
        addition = '\n' + MARKER + '\n' + REQUIRE_LINE + '\n'
        changes.append((config_target(home), text, text + addition))
    for path, old, new in changes:
        print(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                         fromfile=str(path), tofile=str(path) + ' (proposed)')), end='')


def plan(args):
    home = check_home(args.home)
    target = managed_target(home)
    config = config_target(home)
    print('Template: ' + str(TEMPLATE))
    print('Managed:  ' + str(target) + ' (' + ('present' if target.exists() else 'absent') + ')')
    print('Config:   ' + str(config) + ' (' + ('present' if config.is_file() else 'MISSING') + ')')
    if config.is_file():
        includes = verify_config(config.read_text(), config)
        print('Include:  ' + ('present' if includes else 'absent'))
    show_diff(home)
    print('--- managed content ---')
    print(load_text(TEMPLATE, 'Managed template'), end='')
    print('--- apply would ---')
    print('  write the managed snippet above (after backing up an existing file)')
    print('  ensure exactly one ' + REQUIRE_LINE + ' line in the config')
    print('  make no service, reload or session change')
    print('Rollback: ' + sys.argv[0] + ' remove --home ' + str(home))
    return 0


def apply(args):
    home = check_home(args.home)
    show_diff(home)  # Validate every destination before the first write.
    text = load_text(TEMPLATE, 'Managed template')
    write_managed(home, text, dry_run=args.dry_run)
    ensure_include(home, dry_run=args.dry_run)
    print('The next Hyprland start reads the managed settings; no reload was performed.')
    return 0


def remove(args):
    home = check_home(args.home)
    validate(home)
    remove_include(home, dry_run=args.dry_run)
    target = managed_target(home)
    if args.dry_run:
        print('Dry run: would remove ' + str(target))
    elif target.is_file():
        backup(target)
        target.unlink()
        print('Removed ' + str(target))
    else:
        print('No managed file at ' + str(target))
    print('Rollback complete; a running session is unaffected until it restarts.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', default=os.path.expanduser('~'),
                        help='Target home directory (default: the current user)')
    sub = parser.add_subparsers(dest='mode', required=True)
    sub.add_parser('plan', help='Read-only plan: paths, content, exact changes')
    apply_parser = sub.add_parser('apply', help='Write the managed snippet and include line')
    apply_parser.add_argument('--dry-run', action='store_true',
                              help='Write nothing; print what would change')
    remove_parser = sub.add_parser('remove', help='Rollback: remove include and snippet')
    remove_parser.add_argument('--dry-run', action='store_true',
                               help='Write nothing; print what would change')
    args = parser.parse_args()
    args.dry_run = getattr(args, 'dry_run', False)
    {'plan': plan, 'apply': apply, 'remove': remove}[args.mode](args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        sys.exit(2)
