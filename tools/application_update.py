#!/usr/bin/env python3
"""Independent interactive application-only updater; no provisioning or auto-yes."""
import fcntl
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

import install as guided
import published_release
import release_update
import user_install


class ApplicationInstallation(user_install.Installation):
    def start(self, *, restore_background=False):
        return super().start(restore_background=False)


def session_allowed(env=None):
    env = os.environ if env is None else env
    return (env.get('XDG_CURRENT_DESKTOP', '').lower().split(':') == ['hyprland']
            and env.get('XDG_SESSION_TYPE') == 'wayland'
            and bool(env.get('HYPRLAND_INSTANCE_SIGNATURE')) and bool(env.get('WAYLAND_DISPLAY')))


def cache_root():
    cache = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    return user_install.private_directory(cache / 'omabuntu/menu-updates')


def review_update(installation, resources, directory, confirm, emit=print,
                  discover=published_release.discover, download=published_release.download,
                  apply=release_update.apply):
    """All download/deployment permissions come from this terminal, never a guard."""
    current = installation.selected()
    running = installation.running()
    if not current or not running or running.get('release') != current:
        raise ValueError('Require the selected running installed shell; no session will be started.')
    release = installation.root / current
    installed = user_install.verify_bundle(release, installed=True)
    provenance = user_install.read_json(release / 'PROVENANCE.json')
    emit('Omabuntu application update — no Ubuntu packages, plugin activation or configuration reset.')
    emit('Installed: ' + installed['version'])
    if not confirm('Check the signed public release metadata over the network?'):
        return {'status': 'cancelled-before-check'}
    info = discover(resources / 'config/release-signing-key.pub', directory)
    status = published_release.availability(installed['version'], info['version'], provenance)
    result = {'status': status, 'installed': installed['version'], 'published': info['version']}
    user_install.atomic_json(directory / 'availability.json', result)
    emit('Published: ' + info['version'])
    if status != 'newer':
        emit({'local-release-blocked': 'Local/adapted release: automatic replacement is blocked to preserve unpublished changes.',
              'downgrade-blocked': 'The public release is older; downgrade blocked.',
              'current': 'Public version matches; no deployment (archive byte identity was not compared).'}[status])
        return result
    if not confirm('Download and verify the candidate application bundle?'):
        return {'status': 'cancelled-before-download'}
    bundle = download(info, directory)
    incoming = user_install.verify_bundle(bundle)
    if published_release.bundle_public_version(incoming['version']) != info['version']:
        raise ValueError('Bundle version differs from signed metadata')
    if (installation.selected() != current or installation.running() != running
            or user_install.verify_bundle(release, installed=True) != installed):
        raise ValueError('Installed selection/process changed; reopen Update to review again.')
    plan = release_update.review(installation, bundle, mode='update', restart=True)
    # No legacy adoption, native handoff, source builds or prerequisite installs.
    if plan['schema_decision'].get('action') != 'none' or plan.get('native_transition'):
        raise ValueError('Application-only update cannot migrate state or native targets')
    user_install.atomic_json(directory / 'plan.json', plan)
    emit(json.dumps(plan, indent=2))
    emit('Preflight may refuse missing prerequisites; it will not install or repair them.')
    if not confirm('Apply this exact application plan, including the recorded shell-only restart?'):
        return {'status': 'cancelled-before-apply'}
    def preflight(candidate):
        report, path = guided.preflight(candidate, report_root=directory)
        emit('Private preflight report: ' + str(path))
        if report.get('status') != 'passed':
            emit(guided.preflight_failure(report, path))
        return report
    result = apply(installation, plan, release_update.approve_digest(plan), check=preflight)
    user_install.atomic_json(directory / 'result.json', result)
    return result


def confirm(message):
    return input(message + ' [y/N] ').strip().lower() in ('y', 'yes')


def main():
    if len(sys.argv) != 1 or not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('This updater requires an interactive terminal; no unattended options are supported.')
    if os.getuid() == 0 or os.environ.get('SUDO_USER') or not session_allowed():
        raise ValueError('Run as your normal user in the existing Hyprland Wayland session.')
    if platform.machine() != 'x86_64':
        raise ValueError('Published releases support x86_64 only.')
    os.umask(0o077)
    installation = ApplicationInstallation(*user_install.defaults())
    selected = installation.selected()
    resources = Path(__file__).resolve().parents[1]
    if selected is None or resources.parent != installation.root / selected:
        raise ValueError('This is not the selected installed update runner; reopen the menu.')
    if not (resources / 'config/release-signing-key.pub').is_file():
        raise ValueError('Installed publisher trust key is missing.')
    parent = cache_root()
    fd = os.open(parent / 'operation.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('Another update terminal is checking or updating; finish it first.') from error
        directory = user_install.private_directory(parent / user_install.stamp())
        print('Private update reports: ' + str(directory))
        try:
            result = review_update(installation, resources, directory, confirm)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            user_install.atomic_json(directory / 'failure.json', {'status': 'failed', 'message': str(error)})
            raise
        print('Update result: ' + result['status'])


if __name__ == '__main__':
    code = 0
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print('Update stopped: ' + str(error), file=sys.stderr)
        code = 1
    except KeyboardInterrupt:
        print('\nUpdate interrupted; review the retained transaction journal before retrying.', file=sys.stderr)
        code = 130
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            input('\nPress Enter to close this update terminal. ')
        except (EOFError, KeyboardInterrupt):
            pass
    raise SystemExit(code)
