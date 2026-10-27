#!/usr/bin/env python3
"""Read-only Hyprland screen-lock prerequisites; never authenticates or locks.

Package presence, a PAM filename or a successful probe cannot establish secure
locking, authentication, corporate-policy compatibility or recoverability.
"""
import datetime
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = {
    'packages': ['dpkg-query', '-W', '-f=${binary:Package}\t${db:Status-Abbrev}\t${Version}\n',
                 'hyprlock', 'swaylock', 'gnome-shell', 'libpam-gnome-keyring'],
    'hyprlock_candidates': ['apt-cache', 'policy', 'hyprlock'],
    'session_units': ['systemctl', '--user', 'list-units', 'wayland-session@*', 'wayland-wm@*',
                      '--no-legend', '--no-pager'],
}


def probe(argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=10, check=False)
        return {'status': 'collected' if result.returncode == 0 else 'partial-or-failed',
                'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
    except FileNotFoundError:
        return {'status': 'missing-command'}
    except subprocess.TimeoutExpired:
        return {'status': 'timeout'}
    except OSError as error:
        return {'status': 'error', 'error': str(error)}


def collect():
    return {
        'schema_version': 1, 'collected_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'binaries': {name: shutil.which(name) for name in ('hyprlock', 'swaylock', 'loginctl', 'uwsm')},
        'probes': {name: probe(argv) for name, argv in COMMANDS.items()},
        'authentication_verified': False, 'recovery_verified': False,
        'activation_allowed': False,
        'limits': 'No PAM conversation, credentials, configuration changes, package install, lock, idle, suspend or session transition. GNOME lock state is not proof of a Hyprland session lock.',
    }


def main():
    report = collect()
    directory = ROOT / 'work/lock-readiness' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    directory.mkdir(mode=0o700, parents=True)
    path = directory / 'report.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    path.chmod(0o600)
    print('Private lock readiness report:', path)
    print('Hyprlock executable:', 'available' if report['binaries']['hyprlock'] else 'missing')
    print('Authentication and recovery are NOT verified; no lock activation permitted.')


if __name__ == '__main__':
    main()
