#!/usr/bin/env python3
"""Verify a Git candidate export without existing work inputs or local images.

Plan-only by default. --run writes only private files under work/, runs fixed
source/unit/CLI checks, and never builds, downloads, installs or activates a
service. This is not a secret scanner or fresh-machine desktop acceptance.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = ('work', 'target', 'target-backups', 'snapshot', 'inventory',
            'analysis', 'transfer', 'config/local', 'config/menu/backgrounds',
            'config/menu/themes-previews')


def candidate_files(root):
    result = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                            cwd=root, capture_output=True, timeout=15, check=True)
    files = []
    for name in sorted(set(os.fsdecode(item) for item in result.stdout.split(b'\0') if item)):
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe candidate filename')
        if any(path == Path(prefix) or Path(prefix) in path.parents for prefix in EXCLUDED):
            continue
        if '.git' in path.parts or '__pycache__' in path.parts or path.name.startswith('.env'):
            continue
        source = root / path
        if source.is_symlink() or any(parent.is_symlink() for parent in source.parents if parent != root.parent):
            raise ValueError('Symlinked candidate path: ' + name)
        if source.is_file():
            files.append(path)
        elif source.exists():
            raise ValueError('Candidate is not a regular file: ' + name)
    return files


def run(root):
    if any(path.is_symlink() for path in (root / 'work', root / 'work/clean-source')):
        raise ValueError('Refusing symlinked work directory')
    os.umask(0o077)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    case = root / 'work/clean-source' / stamp
    source = case / 'source'
    source.mkdir(parents=True)
    files = candidate_files(root)
    for path in files:
        target = source / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / path, target)
    for name in ('home', 'tmp'):
        (case / name).mkdir(mode=0o700)
    report = {'status': 'running', 'files': len(files), 'checks': [],
              'initial_work_present': (source / 'work').exists(),
              'local_images_present': any((source / path).exists() for path in EXCLUDED[-2:]),
              'limits': 'Source tests and fixed read-only CLIs only; same host dependencies, no fresh native runtime build or desktop/security acceptance.'}
    report_path = case / 'report.json'
    def save():
        report_path.write_text(json.dumps(report, indent=2) + '\n')
    save()
    # Tests create only new synthetic work fixtures, never use original work/.
    (source / 'work').mkdir(mode=0o700)
    env = {key: value for key, value in os.environ.items()
           if key in ('PATH', 'LANG', 'LC_ALL', 'USER', 'LOGNAME')}
    env.update(HOME=str(case / 'home'), TMPDIR=str(case / 'tmp'),
               PYTHONDONTWRITEBYTECODE='1', GIT_CEILING_DIRECTORIES=str(case),
               XDG_CONFIG_HOME=str(case / 'home/config'), XDG_DATA_HOME=str(case / 'home/data'),
               XDG_STATE_HOME=str(case / 'home/state'), XDG_CACHE_HOME=str(case / 'home/cache'))
    checks = [
        ('unit-tests', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], 0, None),
        ('make-help', ['make', '--no-print-directory', 'help'], 0, None),
        ('doctor-help', [sys.executable, '-B', 'tools/omabuntu.py', '--help'], 0, None),
        ('build-plan', [sys.executable, '-B', 'tools/build_runtime.py'], 0, 'Plan only'),
        ('runtime-plan', [sys.executable, '-B', 'tools/check_runtime.py'], 0, None),
        ('desktop-plan', [sys.executable, '-B', 'tools/check_desktop_panels.py'], 0, 'Plan only'),
        ('package-missing-build', [sys.executable, '-B', 'tools/package_user.py', '--version', 'clean-check'], 2, '--build-dir'),
        ('make-missing-build', ['make', '--no-print-directory', 'release', 'VERSION=clean-check'], 2, 'BUILD_DIR is required'),
        ('dev-update-missing-build', ['make', '--no-print-directory', 'dev-update'], 2, 'BUILD_DIR is required'),
    ]
    for name, command, expected, marker in checks:
        check = {'name': name, 'expected_exit': expected}
        try:
            result = subprocess.run(command, cwd=source, env=env, capture_output=True,
                                    text=True, timeout=120, check=False)
            output = result.stdout + result.stderr
            check.update(returncode=result.returncode,
                         status='passed' if result.returncode == expected and (marker is None or marker in output) else 'failed')
        except subprocess.TimeoutExpired as error:
            output = ((error.stdout or b'') + (error.stderr or b'')).decode(errors='replace')
            check.update(returncode=None, status='timeout')
        except OSError as error:
            output = str(error)
            check.update(returncode=None, status='missing-command' if isinstance(error, FileNotFoundError) else 'failed')
        (case / (name + '.log')).write_text(output)
        report['checks'].append(check)
        save()
        if check['status'] != 'passed':
            break
    report['status'] = 'passed' if len(report['checks']) == len(checks) and all(c['status'] == 'passed' for c in report['checks']) else 'failed'
    save()
    print(report_path)
    print(report['status'])
    return 0 if report['status'] == 'passed' else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    if not args.run:
        print('Plan only: export the Git candidate without private work/images and run unit/read-only CLI checks. Use --run to write a private report.')
        return 0
    try:
        return run(ROOT)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
