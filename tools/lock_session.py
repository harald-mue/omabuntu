#!/usr/bin/env python3
"""Explicit, single-shot screen lock for the installed Omabuntu release.

This is not autostart, not an idle timer and not a daemon. It requires --apply,
a matching live Hyprland session, the packaged static configuration and the
reviewed Hyprlock version. It never reads credentials and never runs commands
from configuration.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

EXPECTED = re.compile(r'Hyprlock version v0\.9\.6\b')
FORBIDDEN = ('cmd[', 'onclick', 'exec', 'source', 'script', 'sleep')


def helper_config(release):
    path = Path(release) / 'lock/hyprlock.conf'
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16384:
        raise ValueError('Reviewed lock configuration is missing')
    text = path.read_text()
    # Comments may describe the exclusions; only active directives are scanned.
    active = '\n'.join(line.split('#', 1)[0] for line in text.splitlines()).lower()
    for word in FORBIDDEN:
        if word in active:
            raise ValueError('Lock configuration contains an execution directive: ' + word)
    if re.search(r'(?m)^\s*auth\s*\{', active) or 'pam' in active:
        raise ValueError('Lock configuration must not override the PAM service')
    return path


def state_directory():
    base = os.environ.get('OMABUNTU_STATE_HOME')
    if not base:
        raise ValueError('Run this through the installed Omabuntu manager')
    directory = Path(base) / 'locks' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    if any(part.is_symlink() for part in (directory, *directory.parents)):
        raise ValueError('Symlinked lock state directory')
    directory.mkdir(mode=0o700, parents=True)
    if directory.stat().st_uid != os.getuid() or directory.stat().st_mode & 0o077:
        raise ValueError('Lock state directory must be owned and private')
    return directory


def preflight(release):
    lock = shutil.which('hyprlock')
    if not lock or lock != '/usr/bin/hyprlock':
        raise ValueError('Reviewed Hyprlock binary is not installed at /usr/bin/hyprlock')
    version = subprocess.run([lock, '--version'], capture_output=True, text=True, timeout=10, check=False)
    if version.returncode or not EXPECTED.search(version.stdout + version.stderr):
        raise ValueError('Hyprlock version differs from the reviewed v0.9.6')
    if 'hyprland' not in os.environ.get('XDG_CURRENT_DESKTOP', '').lower().split(':'):
        raise ValueError('Lock only from the Hyprland session')
    signature = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
    display = os.environ.get('WAYLAND_DISPLAY', '')
    runtime_dir = Path('/run/user') / str(os.getuid())
    if not signature or not re.fullmatch(r'wayland-\d+', display) or not (runtime_dir / display).is_socket():
        raise ValueError('No matching live Wayland/Hyprland session')
    instances = json.loads(subprocess.check_output(['hyprctl', 'instances', '-j'], timeout=8))
    if not any(i.get('instance') == signature and i.get('wl_socket') == display for i in instances):
        raise ValueError('Hyprland environment does not match a live instance')
    others = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'hyprlock'], capture_output=True, timeout=5, check=False)
    if others.returncode != 1:
        raise ValueError('A Hyprlock process already exists or lookup failed')
    return {'binary': lock, 'config': str(helper_config(release)), 'display': display}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    if os.getuid() == 0:
        raise ValueError('Never run the session lock as root')
    info = preflight(args.release)
    if not args.apply:
        print(json.dumps({**info, 'status': 'planned-not-locked'}, indent=2))
        return 0
    directory = state_directory()
    command = [info['binary'], '--config', info['config']]
    (directory / 'command.json').write_text(json.dumps({'command': command, 'expected': 'v0.9.6',
                                                        'recovery': 'local TTY login, verified by the user'}, indent=2) + '\n')
    with (directory / 'output.log').open('x') as log:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                timeout=1800, check=False)
    (directory / 'result.json').write_text(json.dumps({
        'returncode': result.returncode,
        'status': 'exited' if result.returncode == 0 else 'failed'}, indent=2) + '\n')
    print('Hyprlock exited with status', result.returncode, '- log:', directory / 'output.log')
    return 0 if result.returncode == 0 else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('Lock not started:', error)
        raise SystemExit(1)
