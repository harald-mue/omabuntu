#!/usr/bin/env python3
"""Deploy the Hyprland-only condition for Ubuntu's hyprpaper user unit (plan 068).

Read-only plan by default; apply writes an additive systemd user drop-in; remove
is the rollback. The tool never starts, stops or restarts hyprpaper.service and
never touches the package-owned unit. Uses only the Python standard library.
"""
import argparse
import datetime
import os
from pathlib import Path
import shutil
import subprocess
import sys

UNIT_NAME = 'hyprpaper.service'
DROPIN_DIR = UNIT_NAME + '.d'
DROPIN_NAME = 'omabuntu.conf'
TEMPLATE = Path(__file__).resolve().parent.parent / 'config/systemd' / 'hyprpaper-condition.conf'
SYSTEMCTL = '/usr/bin/systemctl'


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')


def dropin_dir(home):
    return Path(home) / '.config/systemd/user' / DROPIN_DIR


def target_path(home):
    return dropin_dir(home) / DROPIN_NAME


def check_path(path):
    """Reject symlinked parents and traversal, mirroring the deployment rules."""
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('Parent traversal is not allowed')
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise ValueError('Symlinked path: ' + str(part))
        if part != path and part.exists() and not part.is_dir():
            raise ValueError('Not a directory: ' + str(part))
    return path


def load_template():
    if TEMPLATE.is_symlink() or not TEMPLATE.is_file():
        raise ValueError('Drop-in template missing: ' + str(TEMPLATE))
    text = TEMPLATE.read_text()
    if not text.endswith('\n'):
        raise ValueError('Drop-in template must end with a newline')
    if 'ConditionEnvironment=HYPRLAND_INSTANCE_SIGNATURE' not in text:
        raise ValueError('Drop-in template lost the reviewed condition')
    if '[Unit]' not in text:
        raise ValueError('Drop-in template has no [Unit] section')
    return text


def base_unit_paths():
    return [Path('/usr/lib/systemd/user') / UNIT_NAME,
            Path('/lib/systemd/user') / UNIT_NAME]


def base_unit_present():
    for candidate in base_unit_paths():
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


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
    unit = base_unit_present()
    print('Template: ' + str(TEMPLATE))
    print('Target:   ' + str(target))
    print('Existing drop-in: ' + ('yes' if target.exists() else 'no'))
    print('Base unit: ' + (str(unit) if unit else 'NOT FOUND (Ubuntu hyprpaper package absent)'))
    print('--- drop-in content ---')
    print(text, end='')
    print('--- apply would run ---')
    print('  write the drop-in above'
          + (' (after backing up the existing file)' if target.exists() else ''))
    systemctl(args.systemctl, ['daemon-reload'], dry=True)
    print('Apply never starts, stops or restarts ' + UNIT_NAME + '.')
    print('An already running GNOME hyprpaper keeps running until it is stopped separately:')
    print('  systemctl --user stop ' + UNIT_NAME)
    print('Rollback: ' + sys.argv[0] + ' remove --home ' + str(home))
    return 0


def apply(args):
    home = check_path(args.home)
    target = target_path(home)
    text = load_template()
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file():
            raise ValueError('Unsafe existing drop-in: ' + str(target))
        if target.read_text() == text:
            print('Drop-in already current at ' + str(target))
            return 0
        if not args.replace:
            raise ValueError('Drop-in differs; pass --replace to back it up and redeploy')
        if not args.dry_run:
            backup = target.with_name(target.name + '.bak-' + stamp())
            shutil.copy2(target, backup)
            print('Backed up the previous drop-in to ' + str(backup))
    elif args.replace and not args.dry_run:
        print('No existing drop-in to replace.')
    if not args.dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        print('Wrote ' + str(target))
    else:
        print('Dry run: would write ' + str(target))
    systemctl(args.systemctl, ['daemon-reload'], dry=args.dry_run)
    print('Done. No service was started, stopped or restarted.')
    print('If a hyprpaper is running outside Hyprland, stop it once with: systemctl --user stop ' + UNIT_NAME)
    print('Rollback: ' + sys.argv[0] + ' remove --home ' + str(home))
    return 0


def remove(args):
    home = check_path(args.home)
    target = target_path(home)
    removed = False
    if args.dry_run:
        print('Dry run: would remove ' + str(target))
    elif target.is_symlink() or target.exists():
        target.unlink()
        print('Removed ' + str(target))
        removed = True
        directory = target.parent
        try:
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
                print('Removed the now-empty ' + str(directory))
        except OSError:
            pass
    else:
        print('Nothing to remove at ' + str(target))
    systemctl(args.systemctl, ['daemon-reload'], dry=args.dry_run)
    print('Rollback complete; a running hyprpaper is unaffected until it is stopped or the session ends.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', default=os.path.expanduser('~'),
                        help='Target home directory (default: the current user)')
    parser.add_argument('--systemctl', default=SYSTEMCTL,
                        help='systemctl binary override for isolated tests')
    sub = parser.add_subparsers(dest='mode', required=True)
    sub.add_parser('plan', help='Read-only plan: path, drop-in content, exact commands')
    apply_parser = sub.add_parser('apply', help='Write the drop-in (never starts or stops it)')
    apply_parser.add_argument('--replace', action='store_true',
                              help='Back up and replace a differing drop-in file')
    apply_parser.add_argument('--dry-run', action='store_true',
                              help='Write nothing; run no systemctl; print the commands')
    remove_parser = sub.add_parser('remove', help='Rollback: delete the drop-in and reload')
    remove_parser.add_argument('--dry-run', action='store_true',
                               help='Write nothing; run no systemctl; print the commands')
    args = parser.parse_args()
    args.dry_run = getattr(args, 'dry_run', False)
    return {'plan': plan, 'apply': apply, 'remove': remove}[args.mode](args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        sys.exit(2)
