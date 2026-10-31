"""Bootstrap-only hyprbars build: pinned archives, private headers, no loading.

Unlike the historical standalone maintainer builder, this never mutates shared
checkouts or runs CMake/scanners with access to the user's session or network.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request
import xml.etree.ElementTree as ET

import build_hyprbars as legacy
import build_runtime as builder
import user_install

ROOT = Path(__file__).resolve().parents[1]
PREFIX = '/opt/omabuntu-plugin'
MODULES = ('aquamarine', 'hyprutils', 'hyprgraphics', 'hyprcursor', 'hyprlang')
EXPORTS = {'pluginAPIVersion', 'pluginInit', 'pluginExit'}
BASE_STEPS = {'sandbox-preflight', 'wayland-enums', 'configure', 'compile', 'stage',
              'elf', 'segments', 'dynamic', 'linkage', 'exports'}


def inputs(root=ROOT):
    user_install.safe_parents(root / 'upstream')
    pin = user_install.read_json(root / 'upstream/hyprbars-build.json')
    if (pin.get('schema_version') != 1
            or pin.get('target') != {'version': '0.56.2', 'commit': legacy.HYPRLAND_COMMIT}
            or len(pin.get('sources', [])) != 2):
        raise builder.BuildError('Require the reviewed plugin/header source pins')
    expected = {'hyprland-plugins': (legacy.PLUGIN_COMMIT, 'Hyprland-plugins-BSD-3-Clause.txt'),
                'Hyprland': (legacy.HYPRLAND_COMMIT, 'Hyprland-BSD-3-Clause.txt')}
    if {item['name'] for item in pin['sources']} != set(expected):
        raise builder.BuildError('Plugin source set differs')
    for item in pin['sources']:
        name = item['name']
        commit, notice = expected[name]
        repo = 'https://github.com/hyprwm/' + name
        if (item.get('repository') != repo or item.get('commit') != commit
                or item.get('archive_root') != name + '-' + commit
                or item.get('archive_url') != 'https://codeload.github.com/hyprwm/' + name + '/tar.gz/' + commit
                or type(item.get('archive_bytes')) is not int or not 0 < item['archive_bytes'] < builder.MAX_ARCHIVE_BYTES
                or not re.fullmatch(r'[a-f0-9]{64}', item.get('archive_sha256', ''))):
            raise builder.BuildError('Plugin archive lock differs')
        record = item['license']
        path = root / 'licenses' / notice
        user_install.safe_parents(path.parent)
        if (record.get('upstream_path') != 'LICENSE' or record.get('notice_path') != 'licenses/' + notice
                or path.is_symlink() or not path.is_file() or builder.digest(path) != record.get('sha256')):
            raise builder.BuildError('Plugin/header notice differs')
    return pin


def pkg(*args):
    result = subprocess.run(['/usr/bin/pkg-config', *args], capture_output=True, text=True,
                            env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, timeout=15, check=False)
    if result.returncode:
        raise builder.BuildError('Required plugin pkg-config metadata unavailable: ' + ' '.join(args))
    return result.stdout.strip()


def native_target():
    data = legacy.installed_version()
    if (data.get('version') != '0.56.2' or data.get('commit') != legacy.HYPRLAND_COMMIT
            or data.get('dirty') is not False):
        raise builder.BuildError('Plugin requires the reviewed clean installed Hyprland')
    modules = {name: pkg('--modversion', name) for name in MODULES}
    if any(not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}', value) for value in modules.values()):
        raise builder.BuildError('Unreviewed native module version format')
    # Match the exact pinned PluginAPI.hpp client-hash algorithm, not a guessed ABI.
    expected = legacy.HYPRLAND_COMMIT
    for label, name in zip(('aq', 'hu', 'hg', 'hc', 'hlg'), MODULES):
        expected += '_' + label + '_' + modules[name].rsplit('.', 1)[0]
    if data.get('abiHash') != expected:
        raise builder.BuildError('Installed libraries differ from the compositor ABI; no plugin build')
    requires = pkg('--print-requires', 'hyprland').splitlines()
    if not requires or any(not re.fullmatch(r'[A-Za-z0-9_.-]+(?:\s+[<>=]+\s+[A-Za-z0-9_.+-]+)?', line) for line in requires):
        raise builder.BuildError('Unexpected installed Hyprland dependency metadata')
    return {'version': data['version'], 'commit': data['commit'], 'abi_hash': expected,
            'metadata': data, 'modules': modules, 'requires': requires}


def version_header(template, target):
    data = target['metadata']
    values = {key: str(data.get(field, '')) for key, field in {
        'GIT_COMMIT_HASH': 'commit', 'GIT_BRANCH': 'branch', 'GIT_COMMIT_MESSAGE': 'commit_message',
        'GIT_COMMIT_DATE': 'commit_date', 'GIT_TAG': 'tag', 'GIT_COMMITS': 'commits'}.items()}
    values['GIT_DIRTY'] = 'false'
    for key, name in zip(('AQUAMARINE', 'HYPRUTILS', 'HYPRGRAPHICS', 'HYPRCURSOR', 'HYPRLANG'), MODULES):
        values[key + '_VERSION'] = target['modules'][name]
    parts = (values['AQUAMARINE_VERSION'] + '.0.0').split('.')[:3]
    values.update(dict(zip(('AQUAMARINE_VERSION_MAJOR', 'AQUAMARINE_VERSION_MINOR', 'AQUAMARINE_VERSION_PATCH'), parts)))
    def replace(match):
        key = match.group(1)
        if key not in values:
            raise builder.BuildError('Unknown version-header placeholder')
        value = values[key]
        if key.endswith(('_MAJOR', '_MINOR', '_PATCH')):
            return value
        return json.dumps(value, ensure_ascii=True)[1:-1]
    return re.sub(r'@([A-Z_]+)@', replace, template)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def obtain(item, cache):
    path = cache / (item['name'] + '-' + item['commit'] + '.tar.gz')
    user_install.safe_parents(cache)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise builder.BuildError('Unsafe plugin archive cache')
    if not path.exists():
        request = urllib.request.Request(item['archive_url'], headers={'User-Agent': 'Omabuntu-pinned-plugin-build'})
        with urllib.request.build_opener(NoRedirect).open(request, timeout=60) as response:
            data = response.read(item['archive_bytes'] + 1)
        if len(data) != item['archive_bytes'] or hashlib.sha256(data).hexdigest() != item['archive_sha256']:
            raise builder.BuildError('Plugin archive download differs')
        # Atomic no-clobber publication; retain an existing user's cache on races.
        temp = cache / ('.download-' + user_install.stamp())
        created = False
        try:
            with temp.open('xb') as stream:
                created = True
                stream.write(data)
            os.link(temp, path)
        finally:
            if created:
                temp.unlink(missing_ok=True)
    if path.stat().st_size != item['archive_bytes'] or builder.digest(path) != item['archive_sha256']:
        raise builder.BuildError('Plugin archive cache differs; retained for review')
    return path


def system_share(path):
    """Normalize //usr/share from pkg-config before any relative-path check."""
    resolved = Path(path).resolve()
    if not resolved.is_relative_to('/usr/share'):
        raise builder.BuildError('Protocol data must be provided by system packages under /usr/share')
    return resolved


def protocol_notice(path):
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise builder.BuildError('Missing or oversized protocol XML')
    data = path.read_bytes()
    if b'<!DOCTYPE' in data or b'<!ENTITY' in data:
        raise builder.BuildError('Protocol XML declarations require manual review')
    try:
        element = ET.fromstring(data).find('copyright')
    except ET.ParseError as error:
        raise builder.BuildError('Malformed protocol XML') from error
    text = ''.join(element.itertext()).strip() if element is not None else ''
    if not text:
        raise builder.BuildError('Protocol copyright notice requires manual review')
    return path.name + '\n' + text + '\n\n'


def exported(text):
    found = set()
    for line in text.splitlines():
        columns = line.split()
        if len(columns) >= 8 and columns[3:6] == ['FUNC', 'GLOBAL', 'DEFAULT'] and columns[6] != 'UND':
            found.add(columns[7])
    return EXPORTS <= found


def build(root=ROOT, jobs=4, target=None):
    if type(jobs) is not int or not 1 <= jobs <= 8:
        raise builder.BuildError('Build jobs must be 1..8')
    pin = inputs(root)
    native = native_target()
    if target is not None and target != native:
        raise builder.BuildError('Plugin native target changed since approval')
    for tool in ('bwrap', 'cmake', 'ninja', 'g++', 'readelf', 'ldd', 'hyprwayland-scanner'):
        if shutil.which(tool) is None:
            raise builder.BuildError('Missing plugin build/probe tool: ' + tool)
    work = user_install.private_directory(root / 'work')
    cache = user_install.private_directory(work / 'source-cache')
    parent = user_install.private_directory(work / 'plugin-builds')
    workspace = parent / user_install.stamp()
    workspace.mkdir(mode=0o700)  # Exclusive: never reuse even a private existing output.
    for name in ('sources', 'build', 'stage', 'home', 'logs'):
        user_install.private_directory(workspace / name)
    report = {'schema_version': 1, 'status': 'building', 'source_pin': pin, 'native_target': native,
              'steps': [], 'protocols': [], 'jobs': jobs, 'loaded': False, 'config_applied': False}
    report_path = workspace / 'report.json'
    def save():
        user_install.atomic_json(report_path, report)
    def step(name, command, timeout=900, env=None, expected=None):
        argv = builder.sandbox_command(workspace, command, workspace / 'sources', env)
        log = workspace / 'logs' / (name + '.log')
        item = {'name': name, 'status': 'running', 'command': argv, 'log': str(log.relative_to(workspace))}
        report['steps'].append(item)
        save()
        print('Building hyprbars: ' + name + '; log: ' + str(log), flush=True)
        with log.open('x') as stream:
            try:
                result = builder.run_with_heartbeat('hyprbars ' + name, lambda: subprocess.run(
                    argv, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                    timeout=timeout, check=False))
                item.update(returncode=result.returncode, status='passed' if result.returncode == 0 else 'failed')
            except subprocess.TimeoutExpired:
                item['status'] = 'timeout'
        if item['status'] == 'passed' and expected and not expected(log.read_text(errors='replace')):
            item['status'] = 'failed'
        save()
        if item['status'] != 'passed':
            raise builder.BuildError('Plugin step failed: ' + name + '; inspect ' + str(log))
    save()
    try:
        step('sandbox-preflight', ['/usr/bin/true'], timeout=15)
        sources = {}
        for item in pin['sources']:
            source = builder.extract_source(obtain(item, cache), workspace / 'sources', item)
            if builder.digest(source / 'LICENSE') != item['license']['sha256']:
                raise builder.BuildError('Plugin source notice differs')
            sources[item['name']] = source
        # Only this private disposable header copy is writable; never the shared checkout.
        headers = workspace / 'build/headers/hyprland'
        headers.mkdir(parents=True)
        for name in ('src', 'protocols'):
            shutil.copytree(sources['Hyprland'] / name, headers / name)
        template = (headers / 'src/version.h.in').read_text()
        (headers / 'src/version.h').write_text(version_header(template, native))
        pc = workspace / 'build/pkgconfig'
        pc.mkdir()
        (pc / 'hyprland.pc').write_text(
            'prefix=/build/headers\nName: Hyprland\nDescription: Exact pinned source headers\nVersion: 0.56.2\n'
            'Requires: ' + ', '.join(native['requires']) + ', lua5.4\n'
            'Cflags: -I${prefix} -I${prefix}/hyprland/protocols -I${prefix}/hyprland/src -I${prefix}/hyprland\n')
        dest = '/build/headers/hyprland/protocols/'
        wayland = system_share(Path(pkg('--variable=pkgdatadir', 'wayland-scanner')) / 'wayland.xml')
        protocols = system_share(pkg('--variable=pkgdatadir', 'wayland-protocols'))
        protocol_notices = protocol_notice(wayland)
        step('wayland-enums', ['hyprwayland-scanner', '--wayland-enums', str(wayland), dest], timeout=30)
        xmls = [system_share(path) for group in ('stable', 'unstable', 'staging')
                for path in sorted((protocols / group).glob('*/*.xml'))]
        xmls += sorted((sources['Hyprland'] / 'protocols').glob('*.xml'))
        if not xmls:
            raise builder.BuildError('No protocol XML inputs')
        for index, path in enumerate(xmls):
            protocol_notices += protocol_notice(path)
            source = str(path) if str(path).startswith('/usr/share/') else '/source/' + str(path.relative_to(workspace / 'sources'))
            report['protocols'].append(source)
            step('protocol-' + str(index), ['hyprwayland-scanner', source, dest], timeout=30)
        env = {'PKG_CONFIG_PATH': '/build/pkgconfig'}
        source = '/source/' + sources['hyprland-plugins'].name + '/hyprbars'
        step('configure', ['cmake', '-S', source, '-B', '/build/plugin', '-G', 'Ninja',
                           '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_INSTALL_PREFIX=' + PREFIX,
                           '-DCMAKE_INSTALL_LIBDIR=lib', '-DFETCHCONTENT_FULLY_DISCONNECTED=ON'], timeout=180, env=env)
        step('compile', ['cmake', '--build', '/build/plugin', '--target', 'hyprbars', '--parallel', str(jobs)], env=env)
        step('stage', ['cmake', '--install', '/build/plugin'], timeout=120, env={**env, 'DESTDIR': '/stage'})
        library = '/stage' + PREFIX + '/lib/libhyprbars.so'
        step('elf', ['readelf', '-h', library], timeout=30,
             expected=lambda text: 'DYN' in text and 'X86-64' in text)
        step('segments', ['readelf', '-l', library], timeout=30, expected=lambda text: 'INTERP' not in text)
        step('dynamic', ['readelf', '-d', library], timeout=30,
             expected=lambda text: 'Shared library:' in text and not any(path in text for path in ('/home/', '/build/', '/source/', '/stage/')))
        # Unresolved compositor symbols are normal. Do not ldd -r or dlopen a plugin.
        step('linkage', ['ldd', library], timeout=30, expected=lambda text: 'not found' not in text)
        step('exports', ['readelf', '--dyn-syms', '--wide', library], timeout=30, expected=exported)
        if native_target() != native:
            raise builder.BuildError('Native target changed during plugin build')
        notices = workspace / 'stage' / PREFIX.lstrip('/') / 'licenses'
        notices.mkdir()
        (notices / 'Protocol-notices.txt').write_text(protocol_notices)
        report['protocol_notices_sha256'] = builder.digest(notices / 'Protocol-notices.txt')
        for item in pin['sources']:
            shutil.copyfile(sources[item['name']] / 'LICENSE', notices / Path(item['license']['notice_path']).name)
        report.update(status='staged-and-checked', artifacts=builder.artifact_manifest(workspace / 'stage'))
    except BaseException as error:
        report.update(status='failed', error=type(error).__name__)
        save()
        raise
    save()
    return report_path


def verify_stage(root, candidate):
    workspace = user_install.safe_parents(Path(candidate).absolute())
    if workspace.parent != (root / 'work/plugin-builds').absolute():
        raise builder.BuildError('Choose a direct plugin build under work/plugin-builds')
    report = user_install.read_json(workspace / 'report.json')
    expected = BASE_STEPS | {'protocol-' + str(i) for i in range(len(report.get('protocols', [])))}
    steps = report.get('steps', [])
    if (report.get('schema_version') != 1 or report.get('source_pin') != inputs(root)
            or report.get('native_target') != native_target() or not report.get('protocols')
            or report.get('status') != 'staged-and-checked'
            or len(steps) != len(expected) or {step.get('name') for step in steps} != expected
            or not all(step.get('status') == 'passed' for step in steps)
            or report.get('loaded') is not False or report.get('config_applied') is not False):
        raise builder.BuildError('Plugin build/probe/native evidence differs')
    stage = user_install.safe_parents(workspace / 'stage')
    if any(path.is_symlink() or not (path.is_file() or path.is_dir()) for path in stage.rglob('*')):
        raise builder.BuildError('Unexpected plugin stage link/special file')
    artifacts = builder.artifact_manifest(stage)
    if artifacts != report.get('artifacts'):
        raise builder.BuildError('Plugin artifacts changed')
    allowed = {PREFIX.lstrip('/') + '/lib/libhyprbars.so', PREFIX.lstrip('/') + '/licenses/Protocol-notices.txt'}
    allowed.update(PREFIX.lstrip('/') + '/licenses/' + Path(item['license']['notice_path']).name
                   for item in report['source_pin']['sources'])
    if {item['path'] for item in artifacts} != allowed:
        raise builder.BuildError('Unexpected plugin stage files')
    prefix = stage / PREFIX.lstrip('/')
    if builder.digest(prefix / 'licenses/Protocol-notices.txt') != report.get('protocol_notices_sha256'):
        raise builder.BuildError('Plugin protocol notices differ')
    library = prefix / 'lib/libhyprbars.so'
    if not library.is_file() or library.stat().st_size < 10000:
        raise builder.BuildError('Plugin library missing or implausible')
    for item in report['source_pin']['sources']:
        notice = prefix / 'licenses' / Path(item['license']['notice_path']).name
        if not notice.is_file() or builder.digest(notice) != item['license']['sha256']:
            raise builder.BuildError('Plugin stage notice differs')
    return workspace, prefix, report


def descriptor(report, library_sha256):
    target = report['native_target']
    return {'schema_version': 1, 'plugin_commit': legacy.PLUGIN_COMMIT,
            'hyprland_version': target['version'], 'hyprland_commit': target['commit'],
            'abi_hash': target['abi_hash'], 'library_sha256': library_sha256,
            'activation': 'not-configured'}


def verify_bundle_plugin(bundle):
    """Check a bundled plugin's bytes/installed ABI without invoking the plugin."""
    library = bundle / 'native/hyprbars.so'
    path = bundle / 'native/hyprbars.json'
    if not any(item.exists() or item.is_symlink() for item in (path, library)):
        return None  # Existing non-plugin bundles remain supported.
    user_install.safe_parents(path.parent)
    if any(item.is_symlink() or not item.is_file() for item in (path, library)):
        raise builder.BuildError('Incomplete or linked bundled plugin')
    data = user_install.read_json(path)
    target = native_target()
    expected = descriptor({'native_target': target}, builder.digest(library))
    if data != expected:
        raise builder.BuildError('Bundled plugin descriptor/bytes/native ABI differ')
    return data
