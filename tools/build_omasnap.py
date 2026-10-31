#!/usr/bin/env python3
"""Build pinned Omasnap in Bubblewrap, without installation or capture.

Sources/fonts/notices are verified before compilation. --version is the only
executable probe; the sandbox has no network, session bus or host display.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import build_runtime as builder
import user_install

ROOT = Path(__file__).resolve().parents[1]
PREFIX = '/opt/omabuntu-screenshot'
COMMIT = 'a432f40b14598a4a02b89fa0054f9a0ba3662dd4'


def inputs(root=ROOT):
    pin = json.loads((root / 'upstream/omasnap-source.json').read_text())
    if (pin.get('schema_version') != 1 or pin.get('repository') != 'https://github.com/omacom/omasnap'
            or pin.get('commit') != COMMIT or pin.get('version') != '1.24.0'
            or pin.get('archive_url') != 'https://codeload.github.com/omacom/omasnap/tar.gz/' + COMMIT
            or pin.get('archive_root') != 'omasnap-' + COMMIT
            or not re.fullmatch(r'[a-f0-9]{64}', pin.get('archive_sha256', ''))
            or type(pin.get('archive_bytes')) is not int or not 0 < pin['archive_bytes'] < builder.MAX_ARCHIVE_BYTES):
        raise builder.BuildError('Require the exact reviewed Omasnap source pin')
    fonts = pin.get('annotation_font_sha256')
    if not isinstance(fonts, dict) or set(fonts) != {'assets/Neucha.ttf', 'assets/JetBrainsMono-Regular.ttf', 'assets/InterDisplay-SemiBold.ttf'}:
        raise builder.BuildError('Omasnap annotation fonts must be pinned')
    for digest in fonts.values():
        if not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
            raise builder.BuildError('Invalid Omasnap annotation font hash')
    expected_notices = {'LICENSE', 'assets/OFL.txt', 'assets/JetBrainsMono-OFL.txt',
                        'assets/Inter-OFL.txt', 'assets/Lucide-ISC.txt', 'assets/FONTS.md'}
    records = notices(pin)
    if {relative for relative, _ in records} != expected_notices or len(records) != len(expected_notices):
        raise builder.BuildError('Omasnap notice set differs')
    for _, record in records:
        path = Path(record.get('notice_path', ''))
        if (path.parent != Path('licenses') or not path.name.startswith('Omasnap-')
                or not re.fullmatch(r'[a-f0-9]{64}', record.get('sha256', ''))):
            raise builder.BuildError('Invalid Omasnap notice path/hash')
    user_install.safe_parents(root / 'licenses')
    return pin


def notices(pin):
    return [('LICENSE', pin['license']), *[(item['upstream_path'], item) for item in pin['bundled_notices']],
            (pin['fonts_note']['upstream_path'], pin['fonts_note'])]


def validate_source(root, source, pin):
    for relative, record in notices(pin):
        expected = root / record['notice_path']
        path = source / relative
        if (path.is_symlink() or not path.is_file() or expected.is_symlink() or not expected.is_file()
                or builder.digest(path) != record['sha256'] or builder.digest(expected) != record['sha256']):
            raise builder.BuildError('Omasnap notice differs: ' + relative)
    for relative, digest in pin['annotation_font_sha256'].items():
        path = source / relative
        if path.is_symlink() or not path.is_file() or builder.digest(path) != digest:
            raise builder.BuildError('Omasnap annotation font differs: ' + relative)


def build(root=ROOT, jobs=4):
    if type(jobs) is not int or not 1 <= jobs <= 8:
        raise builder.BuildError('Build jobs must be 1..8')
    pin = inputs(root)
    for program in ('bwrap', 'cmake', 'ninja', 'g++', 'readelf', 'ldd'):
        if shutil.which(program) is None:
            raise builder.BuildError('Missing Omasnap build/probe tool: ' + program)
    work = user_install.private_directory(root / 'work')
    cache = user_install.private_directory(work / 'source-cache')
    parent = user_install.private_directory(work / 'omasnap-builds')
    workspace = user_install.private_directory(parent / user_install.stamp())
    for name in ('sources', 'build', 'stage', 'home', 'logs'):
        user_install.private_directory(workspace / name)
    report = {'schema_version': 1, 'status': 'building', 'source_pin': pin, 'jobs': jobs,
              'steps': [], 'prefix': PREFIX, 'capture': False, 'installed': False}
    report_path = workspace / 'report.json'
    def save():
        user_install.atomic_json(report_path, report)
    def step(name, command, timeout=900, env=None, expected=None):
        argv = builder.sandbox_command(workspace, command, workspace / 'sources', env)
        log = workspace / 'logs' / (name + '.log')
        item = {'name': name, 'status': 'running', 'command': argv, 'log': str(log.relative_to(workspace))}
        report['steps'].append(item)
        save()
        print('Building Omasnap: ' + name + '; log: ' + str(log), flush=True)
        with log.open('x') as stream:
            try:
                result = builder.run_with_heartbeat('Omasnap ' + name, lambda: subprocess.run(
                    argv, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                    timeout=timeout, check=False))
                item['status'] = 'passed' if result.returncode == 0 else 'failed'
                item['returncode'] = result.returncode
            except subprocess.TimeoutExpired:
                item['status'] = 'timeout'
        text = log.read_text(errors='replace')
        if item['status'] == 'passed' and expected and not expected(text):
            item['status'] = 'failed'
        save()
        if item['status'] != 'passed':
            raise builder.BuildError('Omasnap step failed: ' + name + '; inspect ' + str(log))
    save()
    try:
        step('sandbox-preflight', ['/usr/bin/true'], timeout=15)
        archive = builder.fetch_archive(dict(pin, name='omasnap'), cache)
        if archive.stat().st_size != pin['archive_bytes']:
            raise builder.BuildError('Omasnap archive length differs')
        source = builder.extract_source(archive, workspace / 'sources', pin)
        validate_source(root, source, pin)
        step('configure', ['cmake', '-S', '/source/' + pin['archive_root'], '-B', '/build/omasnap',
                           '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_TESTING=OFF',
                           '-DCMAKE_INSTALL_PREFIX=' + PREFIX,
                           '-DFETCHCONTENT_FULLY_DISCONNECTED=ON'], timeout=180)
        step('compile', ['cmake', '--build', '/build/omasnap', '--target', 'omasnap', '--parallel', str(jobs)])
        step('stage', ['cmake', '--install', '/build/omasnap'], timeout=120, env={'DESTDIR': '/stage'})
        binary = '/stage' + PREFIX + '/bin/omasnap'
        step('elf', ['readelf', '-d', binary], timeout=30,
             expected=lambda text: 'Shared library:' in text and '/home/' not in text)
        step('linkage', ['ldd', '-r', binary], timeout=30,
             expected=lambda text: 'not found' not in text and 'undefined symbol' not in text and 'libLayerShellQt' in text)
        step('version', [binary, '--version'], timeout=30,
             expected=lambda text: re.search(r'\b1\.24\.0\b', text) is not None)
        license_dir = workspace / 'stage' / PREFIX.lstrip('/') / 'share/licenses/omasnap'
        license_dir.mkdir(parents=True, exist_ok=True)
        # Upstream install omits its root MIT and fonts provenance note.
        for relative, record in notices(pin):
            target = license_dir / Path(record['notice_path']).name
            target.write_bytes((source / relative).read_bytes())
        report.update(status='staged-and-checked', artifacts=builder.artifact_manifest(workspace / 'stage'))
    except BaseException as error:
        report.update(status='failed', error=type(error).__name__)
        save()
        raise
    save()
    return report_path


def verify_stage(root, candidate):
    workspace = user_install.safe_parents(Path(candidate).absolute())
    if workspace.parent != (root / 'work/omasnap-builds').absolute():
        raise builder.BuildError('Choose a direct Omasnap build under work/omasnap-builds')
    report = user_install.read_json(workspace / 'report.json')
    pin = inputs(root)
    expected = {'sandbox-preflight', 'configure', 'compile', 'stage', 'elf', 'linkage', 'version'}
    if (report.get('schema_version') != 1 or report.get('source_pin') != pin
            or report.get('status') != 'staged-and-checked'
            or {step.get('name') for step in report.get('steps', [])} != expected
            or not all(step.get('status') == 'passed' for step in report['steps'])
            or report.get('capture') is not False or report.get('installed') is not False):
        raise builder.BuildError('Omasnap build/probe evidence differs')
    stage = workspace / 'stage'
    user_install.safe_parents(stage)
    if any(path.is_symlink() or not (path.is_file() or path.is_dir()) for path in stage.rglob('*')):
        raise builder.BuildError('Unexpected Omasnap stage link/special file')
    if builder.artifact_manifest(stage) != report.get('artifacts'):
        raise builder.BuildError('Omasnap artifacts changed')
    prefix = stage / PREFIX.lstrip('/')
    binary = prefix / 'bin/omasnap'
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise builder.BuildError('Omasnap executable missing')
    for _, record in notices(pin):
        path = prefix / 'share/licenses/omasnap' / Path(record['notice_path']).name
        if not path.is_file() or builder.digest(path) != record['sha256']:
            raise builder.BuildError('Omasnap stage notice differs')
    return workspace, prefix, report
