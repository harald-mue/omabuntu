"""Explicit source-to-bundle pipeline: runtime, screenshots, plugin and artwork.

No package install, source checkout mutation, selector switch or desktop start.
Plugin/font deployment and the complete stock-system setup remain separate.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path

import bootstrap_packages
import bootstrap_sources
import build_omasnap
import build_plugin
import build_runtime
import check_clock_preview
import check_runtime
import download_backgrounds
import install as guided
import omabuntu
import package_user
import user_install
import desktop_font
import release_update

ROOT = Path(__file__).resolve().parents[1]


def code_inputs(root):
    paths = [root / 'install.sh', *sorted((root / 'tools').glob('*.py')),
             *sorted((root / 'packages').glob('*.json')),
             root / 'upstream/source-lock.json', root / 'upstream/omasnap-source.json',
             root / 'upstream/clock-preview.json', root / 'upstream/theme-backgrounds.json',
             root / 'upstream/desktop-font.json', root / 'upstream/hyprbars-build.json']
    for prefix in ('config/hypr', 'config/systemd', 'config/lock'):
        paths.extend(path for path in sorted((root / prefix).rglob('*'))
                     if path.suffix in ('.lua', '.in', '.conf', '.service', '.py'))
    result = {}
    for path in paths:
        user_install.safe_parents(path.parent)
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing or linked build input: ' + str(path.relative_to(root)))
        result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    # Verify all source/mirror bytes, not just the profile JSON's own hash.
    files, _ = check_clock_preview.verified_sources(root)
    result['sealed_shell'] = guided.digest({name: hashlib.sha256(data).hexdigest() for name, data in files.items()})
    return result


def create_plan(root=ROOT, jobs=4, artwork=True, version=None, state=None):
    if type(jobs) is not int or not 1 <= jobs <= 8:
        raise ValueError('Build jobs must be 1..8')
    bootstrap_sources.host_check()
    _, runtime_sources = build_runtime.load_inputs(root)
    screenshot = build_omasnap.inputs(root)
    font_pin = desktop_font.inputs(root)
    plugin_pin = build_plugin.inputs(root)
    spec, _ = bootstrap_packages.request_manifest()
    state = guided.package_state(omabuntu.probe) if state is None else state
    versions = {name: guided.package_version(state, name) for name in spec['groups']['runtime']}
    blockers = ['Missing build/runtime package: ' + name for name, value in versions.items() if not value]
    for name, expected in bootstrap_packages.NATIVE_VERSIONS.items():
        actual = (versions.get(name) or '').split(':')[-1].split('+')[0].split('-')[0]
        if actual != expected:
            blockers.append('Native build target differs: ' + name)
    plugin_target = None
    if not blockers:
        try:
            plugin_target = build_plugin.native_target()
        except (OSError, ValueError, build_runtime.BuildError, build_plugin.subprocess.SubprocessError) as error:
            blockers.append('Plugin native target unavailable: ' + str(error))
    inputs = {'files': code_inputs(root), 'package_versions': versions, 'artwork': artwork,
              'update_contract': release_update.contract(), 'desktop_font': font_pin,
              'plugin_source': plugin_pin, 'plugin_target': plugin_target}
    digest = guided.digest(inputs)
    chosen = version or 'source-' + digest[:16]
    if not isinstance(chosen, str) or not user_install.VERSION.fullmatch(chosen):
        raise ValueError('Invalid release version')
    return {'schema_version': 1, 'kind': 'omabuntu-source-build', 'root': str(root.absolute()),
            'jobs': jobs, 'artwork': artwork, 'version': chosen, 'input_digest': digest,
            'inputs': inputs, 'runtime_commits': {name: data['commit'] for name, data in runtime_sources.items()},
            'omasnap_commit': screenshot['commit'], 'blockers': blockers,
            'status': 'blocked' if blockers else 'review-required',
            'scope': 'runtime/screenshot/plugin/font-assets bundle; no plugin/config deployment or font registration'}


def assert_same(plan):
    fresh = create_plan(Path(plan['root']), plan['jobs'], plan['artwork'], plan['version'])
    if fresh != plan:
        raise ValueError('Build inputs or installed dependencies changed; review a new plan')


def one_verified(parent, verify):
    """Reuse one exact verified stage. Never choose the newest of several."""
    if parent.is_symlink() or not parent.is_dir():
        return None
    matches = []
    for child in sorted(path for path in parent.iterdir() if path.is_dir() and not path.is_symlink()):
        if not (child / 'report.json').is_file():
            continue
        try:
            verify(child)
        except (OSError, ValueError, build_runtime.BuildError, json.JSONDecodeError):
            continue
        matches.append(child)
    return matches[0] if len(matches) == 1 else None


def collect_artwork(root):
    record = json.loads((root / 'upstream/theme-backgrounds.json').read_text())
    parent = user_install.private_directory(root / 'work/artwork-cache')
    destination = parent / guided.digest(record)[:16]
    caches = [path for path in sorted(parent.iterdir())
              if path != destination and path.is_dir() and not path.is_symlink()]
    # Each lock revision has an immutable namespace. Verified old assets are
    # reused without changing the old cache or removing a selected wallpaper.
    download_backgrounds.materialize(destination, record, download=True, cache_roots=caches)
    return destination


def apply(plan, approval):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Build as your normal user, never via sudo')
    if guided.digest(plan) != approval or plan.get('kind') != 'omabuntu-source-build' or plan.get('blockers'):
        raise ValueError('Build approval differs or required packages are missing')
    root = user_install.safe_parents(Path(plan['root']))
    if root != ROOT.absolute():
        raise ValueError('Build plan belongs to another checkout; run its own reviewed entry point')
    parent = user_install.private_directory(root / 'work/bootstrap')
    fd = os.open(parent / 'operation.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert_same(plan)
        case = user_install.private_directory(parent / ('build-' + user_install.stamp()))
        journal = {'status': 'preparing', 'plan': plan, 'bundle': None,
                   'desktop_started': False, 'packages_installed': False}
        path = case / 'build.json'
        def save():
            user_install.atomic_json(path, journal)
        save()
        try:
            output = root / 'work/user-releases' / plan['version']
            if output.exists():
                user_install.verify_bundle(output)
                provenance = user_install.read_json(output / 'PROVENANCE.json')
                if (provenance.get('bootstrap_input_sha256') != plan['input_digest']
                        or not (output / 'runtime/bin/omasnap').is_file()
                        or not (output / 'native/hyprbars.so').is_file()):
                    raise ValueError('Release version already exists with different build inputs')
                build_plugin.verify_bundle_plugin(output)
                report, _ = guided.preflight(output)
                if report['status'] != 'passed':
                    raise ValueError('Existing prepared bundle no longer passes native preflight')
                journal.update(status='verified-existing-bundle', bundle=str(output))
                save()
                return {'status': journal['status'], 'bundle': str(output), 'journal': str(path)}
            journal['status'] = 'artwork'
            save()
            print('  Downloading or reusing pinned artwork and the desktop font.', flush=True)
            assets = collect_artwork(root) if plan['artwork'] else user_install.private_directory(case / 'no-artwork')
            font_file = desktop_font.obtain(root)
            journal['status'] = 'runtime'
            save()
            runtime_dir = one_verified(root / 'work/builds', lambda path: check_runtime.verify_stage(root, path))
            journal['runtime_reused'] = runtime_dir is not None
            if runtime_dir is None:
                runtime_dir = build_runtime.build(root=root, jobs=plan['jobs']).parent
            journal['runtime_build'] = str(runtime_dir)
            save()
            checked = check_runtime.run_checks(root, runtime_dir)
            if checked.get('status') != 'isolated-imports-passed':
                raise ValueError('Runtime checks did not pass')
            journal['status'] = 'screenshots'
            save()
            screenshot_dir = one_verified(root / 'work/omasnap-builds', lambda path: build_omasnap.verify_stage(root, path))
            journal['screenshot_reused'] = screenshot_dir is not None
            if screenshot_dir is None:
                screenshot_dir = build_omasnap.build(root=root, jobs=plan['jobs']).parent
            journal['screenshot_build'] = str(screenshot_dir)
            save()
            build_omasnap.verify_stage(root, screenshot_dir)
            assert_same(plan)
            journal['status'] = 'plugin'
            save()
            plugin_dir = one_verified(root / 'work/plugin-builds', lambda path: build_plugin.verify_stage(root, path))
            journal['plugin_reused'] = plugin_dir is not None
            if plugin_dir is None:
                plugin_dir = build_plugin.build(root=root, jobs=plan['jobs'], target=plan['inputs']['plugin_target']).parent
            journal['plugin_build'] = str(plugin_dir)
            save()
            build_plugin.verify_stage(root, plugin_dir)
            assert_same(plan)
            journal['status'] = 'packaging'
            save()
            output = package_user.prepare(plan['version'], runtime_dir,
                                          screenshot_build=screenshot_dir,
                                          image_assets=assets, build_inputs=plan['input_digest'], font_file=font_file,
                                          plugin_build=plugin_dir)
            user_install.verify_bundle(output)
            build_plugin.verify_bundle_plugin(output)
            report, _ = guided.preflight(output)
            if report['status'] != 'passed':
                raise ValueError('Prepared bundle native preflight failed')
            assert_same(plan)
            journal.update(status='bundle-prepared-and-checked', bundle=str(output))
            save()
            return {'status': journal['status'], 'bundle': str(output), 'journal': str(path),
                    'installed': False, 'desktop_started': False, 'capture': False}
        except BaseException as error:
            journal.update(status='failed', error=type(error).__name__)
            save()
            raise
