#!/usr/bin/env python3
"""Deploy the Omabuntu shell login-autostart user unit (plan 012, Option A).

Read-only plan by default; apply writes the unit and enables it; remove is the
rollback. Never starts the service: the first automatic start happens at the
user's next login. Uses only the Python standard library.
"""
import argparse
import datetime
import os
from pathlib import Path
import shutil
import subprocess
import sys

UNIT_NAME = 'omabuntu-shell.service'
WAIT_NAME = 'omabuntu-shell-wait.py'
TEMPLATE = Path(__file__).resolve().parent.parent / 'config/systemd' / UNIT_NAME
WAIT_TEMPLATE = Path(__file__).resolve().parent.parent / 'config/systemd' / WAIT_NAME
SYSTEMCTL = '/usr/bin/systemctl'


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')


def target_path(home):
    return Path(home) / '.config/systemd/user' / UNIT_NAME


def wait_target_path(home):
    return Path(home) / '.config/systemd/user' / WAIT_NAME


def check_path(path):
    """Reject symlinked parents and traversal, mirroring the deployment rules."""
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('Parent traversal is not allowed')
    for part in [*reversed(path.parents), path]:
        if part.exists() and not part.is_dir() and part != path:
            raise ValueError('Not a directory: ' + str(part))
        if part.is_symlink():
            raise ValueError('Symlinked path: ' + str(part))
    return path


def load_text(path, label):
    if path.is_symlink() or not path.is_file():
        raise ValueError(label + ' missing: ' + str(path))
    text = path.read_text()
    if not text.endswith('\n'):
        raise ValueError(label + ' must end with a newline')
    return text


def load_template():
    return load_text(TEMPLATE, 'Unit template')


def load_wait():
    return load_text(WAIT_TEMPLATE, 'Instance wait helper')


def systemctl(binary, user_args, *, dry=False):
    command = [binary, '--user', *user_args]
    if dry:
        print('  would run: ' + ' '.join(command))
        return 0
    result = subprocess.run(command, check=False)
    if result.returncode:
        raise ValueError('systemctl --user ' + user_args[0] + ' failed with ' + str(result.returncode))


def plan(args):
    home = check_path(args.home)
    target = target_path(home)
    text = load_template()
    wait_text = load_wait()
    wait_target = wait_target_path(home)
    if Path(args.systemctl) != Path(SYSTEMCTL):
        print('Note: test systemctl stub in use: ' + args.systemctl)
    print('Template: ' + str(TEMPLATE))
    print('Wait:     ' + str(WAIT_TEMPLATE))
    print('Target:   ' + str(target))
    print('Wait file:' + str(wait_target))
    print('Existing: ' + ('yes' if target.exists() else 'no'))
    print('Wait present: ' + ('yes' if wait_target.exists() else 'no'))
    print('Launcher: ' + str(Path(home) / '.local/bin/omabuntu')
          + ' (' + ('present' if (Path(home) / '.local/bin/omabuntu').is_file() else 'MISSING') + ')')
    print('--- unit content ---')
    print(text, end='')
    print('--- wait helper ---')
    print(wait_text, end='')
    print('--- apply would run ---')
    print('  write the unit and wait helper above'
          + (' (after backing up existing files)' if target.exists() or wait_target.exists() else ''))
    systemctl(args.systemctl, ['daemon-reload'], dry=True)
    systemctl(args.systemctl, ['enable', UNIT_NAME], dry=True)
    print('Apply never starts the service; the shell starts at the next login.')
    print('Rollback: remove --home ' + str(home) + ' then daemon-reload.')
    return 0


def apply(args):
    home = check_path(args.home)
    target = target_path(home)
    text = load_template()
    wait_text = load_wait()
    wait_target = wait_target_path(home)
    if not (Path(home) / '.local/bin/omabuntu').is_file():
        raise ValueError('The omabuntu launcher is not installed; refusing to enable autostart')
    existing = [path for path in (target, wait_target) if path.exists() or path.is_symlink()]
    if existing and not args.replace:
        raise ValueError('Target already exists; pass --replace to back it up and redeploy')
    if not args.dry_run:
        for path in existing:
            backup = path.with_name(path.name + '.bak-' + stamp())
            shutil.copy2(path, backup)
            print('Backed up the previous file to ' + str(backup))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        wait_target.write_text(wait_text)
        wait_target.chmod(0o755)
        print('Wrote ' + str(target))
        print('Wrote ' + str(wait_target))
    else:
        print('Dry run: would write ' + str(target) + ' and ' + str(wait_target))
    systemctl(args.systemctl, ['daemon-reload'], dry=args.dry_run)
    systemctl(args.systemctl, ['enable', UNIT_NAME], dry=args.dry_run)
    print('Enabled. No start was performed; the shell starts at the next login.')
    print('Rollback: ' + sys.argv[0] + ' remove --home ' + str(home))
    return 0


def remove(args):
    home = check_path(args.home)
    target = target_path(home)
    systemctl(args.systemctl, ['disable', UNIT_NAME], dry=args.dry_run)
    removed = False
    for path in (target, wait_target_path(home)):
        if args.dry_run:
            print('Dry run: would remove ' + str(path))
            continue
        if path.is_symlink() or path.exists():
            path.unlink()
            print('Removed ' + str(path))
            removed = True
    if not removed and not args.dry_run:
        print('Nothing to remove at ' + str(target))
    systemctl(args.systemctl, ['daemon-reload'], dry=args.dry_run)
    print('Rollback complete; a running shell is unaffected until it is stopped or the session ends.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', default=os.path.expanduser('~'),
                        help='Target home directory (default: the current user)')
    parser.add_argument('--systemctl', default=SYSTEMCTL,
                        help='systemctl binary override for isolated tests')
    sub = parser.add_subparsers(dest='mode', required=True)
    sub.add_parser('plan', help='Read-only plan: paths, unit content, exact commands')
    apply_parser = sub.add_parser('apply', help='Write and enable the unit (never starts it)')
    apply_parser.add_argument('--replace', action='store_true',
                              help='Back up and replace an existing unit file')
    apply_parser.add_argument('--dry-run', action='store_true',
                              help='Write nothing; run no systemctl; print the commands')
    remove_parser = sub.add_parser('remove', help='Rollback: disable and delete the unit')
    remove_parser.add_argument('--dry-run', action='store_true',
                               help='Write nothing; run no systemctl; print the commands')
    args = parser.parse_args()
    args.dry_run = getattr(args, 'dry_run', False)
    {'plan': plan, 'apply': apply, 'remove': remove}[args.mode](args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        sys.exit(2)
