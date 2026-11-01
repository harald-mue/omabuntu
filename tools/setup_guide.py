"""One-stage guide over the implemented installer steps.

Review is read-only. Apply performs only the next local stage and never starts
Hyprland, hyprpaper, the shell, a plugin or a package transaction.
"""
import json
import os
from pathlib import Path
import subprocess

import bootstrap_build
import bootstrap_packages
import bootstrap_sources
import build_runtime
import desktop_font
import install as guided
import release_update
import session_activation
import session_config
import user_install

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {'done', 'blocked', 'command', 'apply', 'manual'}


def stage(identifier, status, summary, command=''):
    if status not in STATUSES or not isinstance(summary, str) or not isinstance(command, str):
        raise ValueError('Invalid guide stage')
    return {'id': identifier, 'status': status, 'summary': summary, 'command': command}


def host_stage():
    try:
        bootstrap_sources.host_check()
    except (OSError, ValueError, bootstrap_sources.SourceError) as error:
        return stage('host', 'blocked', str(error))
    return stage('host', 'done', 'Ubuntu 26.04 x86_64. GNOME remains available.')


def ppa_stage(apt_root=Path('/etc/apt')):
    paths = bootstrap_sources.destinations(apt_root)
    if any(path.is_symlink() for path in paths.values()):
        return stage('ppa', 'blocked', 'A managed APT path is a symlink; review it manually.')
    try:
        duplicates = bootstrap_sources.conflicts(apt_root)
    except bootstrap_sources.SourceError as error:
        return stage('ppa', 'blocked', str(error))
    if duplicates:
        names = ', '.join(Path(path).name for path in duplicates)
        return stage('ppa', 'done', 'Hyprland PPA source already exists as ' + names + '. It will not be duplicated. This step did not recheck its signature.')
    if not paths['source'].exists() and not paths['key'].exists():
        return stage('ppa', 'command', 'The signed Hyprland PPA is not configured.', './install.sh --ppa')
    try:
        text = paths['source'].read_text()
    except OSError as error:
        return stage('ppa', 'blocked', 'PPA source is not readable: ' + type(error).__name__)
    if text != bootstrap_sources.source_text() or not paths['key'].is_file():
        return stage('ppa', 'blocked', 'Managed PPA source or key differs; no overwrite from the guide.')
    return stage('ppa', 'done', 'Managed signed PPA source is present.')


def packages_stage(installed, runtime_only=False, plugin_build_only=False):
    manifest, _ = bootstrap_packages.request_manifest(runtime_only=runtime_only, plugin_build_only=plugin_build_only)
    command = './install.sh --packages' + (' --runtime-only' if runtime_only else ' --plugin-build-only' if plugin_build_only else '')
    missing = [name for name in manifest['groups']['runtime'] if not installed(name)]
    if missing:
        count = len(missing)
        noun = 'package is' if count == 1 else 'packages are'
        shown = ', '.join(missing[:5])
        if count > 5:
            shown += ' and %d more' % (count - 5)
        return stage('packages', 'command',
                     str(count) + ' requested ' + noun + ' absent: ' + shown + '. Review the exact APT transaction separately.',
                     command)
    return stage('packages', 'done', 'Requested packages are installed. Upgrades still require --packages.')


def font_stage(root):
    reviewed = desktop_font.plan(root)
    if reviewed['blockers']:
        return stage('font', 'blocked', reviewed['blockers'][0])
    if all(item['existed'] for item in reviewed['before'].values()):
        return stage('font', 'done', 'Pinned desktop font and notices are already registered.')
    return stage('font', 'apply', 'Register the pinned Nerd Font without changing preferences.',
                 './install.sh --font --apply')


def build_stage(root, state=None, installation=None):
    reviewed = bootstrap_build.create_plan(root, state=state)
    if reviewed['blockers']:
        return stage('build', 'blocked', reviewed['blockers'][0], './install.sh --build-release')
    bundle = root / 'work/user-releases' / reviewed['version']
    if matching_bundle(bundle, reviewed['input_digest']):
        return stage('build', 'done', 'A verified local bundle matches the current inputs.', str(bundle))
    return stage('build', 'apply', 'Build the pinned runtime and screenshot tool; stage the hyprpm policy and artwork.',
                 './install.sh --build-release --apply')


def matching_bundle(bundle, digest):
    if bundle.is_symlink() or not bundle.is_dir():
        return False
    try:
        user_install.verify_bundle(bundle)
        provenance = user_install.read_json(bundle / 'PROVENANCE.json')
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return (provenance.get('bootstrap_input_sha256') == digest
            and (bundle / 'runtime/bin/omasnap').is_file()
            and (bundle / 'native/hyprpm.json').is_file())


def release_stage(installation, bundle, root=ROOT):
    try:
        current = installation.selected()
    except (OSError, ValueError) as error:
        return stage('release', 'blocked', str(error))
    # Only the bundle selected by the reviewed source build; never newest mtime.
    target = Path(bundle) if bundle else None
    if target is None:
        if current:
            return stage('release', 'done', 'Installed release contains the screenshot tool and plugin artifact.')
        return stage('release', 'blocked', 'Build a verified bundle before installing a release.')
    restart = installation.running() is not None
    try:
        release_update.review(installation, target, 'update' if current else 'install', restart, False)
    except release_update.UpdateError as error:
        return stage('release', 'blocked', str(error))
    command = './install.sh --bundle ' + str(target)
    if current:
        command += ' --update'
    if restart:
        command += ' --restart-bar'
    summary = 'Install ' + target.name + '.'
    if restart:
        summary = 'Install ' + target.name + ' and restart the recorded bar.'
    return stage('release', 'apply', summary, command)


def session_stage(root):
    reviewed = session_config.plan(root)
    if any('not overwritten' in item for item in reviewed['blockers']):
        return stage('session', 'manual', 'Your existing Hyprland configuration is kept. It is not replaced or merged.')
    if reviewed['blockers']:
        return stage('session', 'blocked', reviewed['blockers'][0], './install.sh --session-config')
    if not reviewed['changes']:
        return stage('session', 'done', 'Generic session profile is current.')
    return stage('session', 'apply', 'Write the generic profile only while Hyprland is stopped.',
                 './install.sh --session-config --apply')


def activation_stage(root):
    reviewed = session_activation.plan(root)
    if any('generic session' in item or 'not overwritten' in item for item in reviewed['blockers']):
        return stage('activation', 'manual', 'Next-login files are skipped while your personal Hyprland configuration is kept.')
    if reviewed['blockers']:
        return stage('activation', 'blocked', reviewed['blockers'][0], './install.sh --session-activate')
    if not reviewed['changes']:
        return stage('activation', 'done', 'Next-login files are current. Nothing has been started.')
    return stage('activation', 'apply', 'Write next-login files without loading the plugin or enabling login.',
                 './install.sh --session-activate --apply')


def login_stage():
    return stage('login', 'manual', 'Log in to Hyprland yourself. The guide does not start a session, plugin or daemon.',
                 'Select Hyprland at the Ubuntu login screen')


def default_installed(name):
    result = subprocess.run(['/usr/bin/dpkg-query', '-W', '-f', '${db:Status-Status}', name],
                            capture_output=True, text=True, timeout=15, check=False)
    return result.returncode == 0 and result.stdout.strip() == 'installed'


def promote_system(item, allow_system):
    if allow_system and item['id'] in ('ppa', 'packages') and item['status'] == 'command':
        return {**item, 'status': 'apply', 'summary': item['summary'] + ' Explicit system approval can run this stage.'}
    return item


def review(root=ROOT, installation=None, installed=None, state=None, apt_root=Path('/etc/apt'), allow_system=False):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Review the guide as your normal user')
    installation = user_install.Installation(*user_install.defaults()) if installation is None else installation
    installed = default_installed if installed is None else installed
    def guarded(identifier, function):
        try:
            item = function()
        except (OSError, ValueError, subprocess.SubprocessError, build_runtime.BuildError,
                release_update.UpdateError) as error:
            item = stage(identifier, 'blocked', str(error))
        if item['id'] != identifier:
            raise ValueError('Guide stage identity differs: ' + identifier)
        return item
    stages = [guarded('host', host_stage), promote_system(guarded('ppa', lambda: ppa_stage(apt_root)), allow_system),
              promote_system(guarded('packages', lambda: packages_stage(installed)), allow_system),
              guarded('font', lambda: font_stage(root)),
              guarded('build', lambda: build_stage(root, state, installation))]
    stages.append(guarded('release', lambda: release_stage(installation, bundle_from(stages), root)))
    stages.extend((guarded('session', lambda: session_stage(root)),
                   guarded('activation', lambda: activation_stage(root)), guarded('login', login_stage)))
    nxt = next((item for item in stages if item['status'] != 'done'), None)
    return {'schema_version': 1, 'kind': 'omabuntu-setup-guide', 'root': str(Path(root).absolute()),
            'stages': stages, 'next': None if nxt is None else nxt['id'],
            'allow_system': bool(allow_system), 'starts_desktop': False, 'installs_packages': False,
            'ready_to_apply': False}


def bundle_from(stages):
    build = next(item for item in stages if item['id'] == 'build')
    if build['status'] != 'done':
        return None
    path = Path(build['command'])
    return path if path.is_dir() else None


def next_stage(reviewed):
    if reviewed.get('kind') != 'omabuntu-setup-guide' or reviewed.get('starts_desktop') is not False:
        raise ValueError('This is not a read-only setup guide')
    identifier = reviewed.get('next')
    return next(item for item in reviewed['stages'] if item['id'] == identifier)


def apply_next(reviewed, approval, confirm, runners):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Apply the guide as your normal user')
    if guided.digest(reviewed) != approval:
        raise ValueError('Guide approval differs')
    item = next_stage(reviewed)
    if item['status'] != 'apply':
        raise ValueError('Next step needs its own command or review: ' + (item['command'] or item['summary']))
    if not confirm(item):
        return {'status': 'cancelled', 'stage': item['id'], 'started': False, 'installs_packages': False}
    if item['id'] not in runners:
        raise ValueError('No local runner for ' + item['id'])
    result = runners[item['id']]()
    if not isinstance(result, dict) or result.get('started') is not False:
        raise ValueError('Guide runner must not start the desktop')
    return {'status': 'completed-one-stage', 'stage': item['id'], 'result': result,
            'started': False, 'installs_packages': bool(result.get('installs_packages')),
            'plugin_loaded': False}


def system_runners():
    """Call the existing PPA/package apply paths. Tests must inject fakes."""
    def ppa():
        parent = user_install.private_directory(ROOT / 'work/bootstrap')
        case = user_install.private_directory(parent / user_install.stamp())
        plan = bootstrap_sources.prepare(case)
        if plan.get('blockers'):
            raise ValueError(plan['blockers'][0])
        result = bootstrap_sources.apply(plan, guided.digest(plan))
        result.update(started=False, installs_packages=False)
        return result

    def packages():
        parent = user_install.private_directory(ROOT / 'work/bootstrap')
        case = user_install.private_directory(parent / user_install.stamp())
        plan = bootstrap_packages.prepare(case)
        if plan.get('blockers'):
            raise ValueError(plan['blockers'][0])
        result = bootstrap_packages.apply(plan, guided.digest(plan))
        result.update(started=False, installs_packages=True)
        return result

    return {'ppa': ppa, 'packages': packages}


def local_runners(root=ROOT):
    def font():
        reviewed = desktop_font.plan(root)
        result = desktop_font.apply(reviewed, guided.digest(reviewed))
        result['started'] = False
        return result

    def build():
        reviewed = bootstrap_build.create_plan(root)
        result = bootstrap_build.apply(reviewed, guided.digest(reviewed))
        result['started'] = False
        return result

    def release():
        installation = user_install.Installation(*user_install.defaults())
        guide = review(root, installation)
        item = next(stage for stage in guide['stages'] if stage['id'] == 'release')
        bundle = Path(item['command'].removeprefix('./install.sh --bundle '))
        mode = 'update' if installation.selected() else 'install'
        plan = release_update.review(installation, bundle, mode, False, False)
        result = release_update.apply(installation, plan, release_update.approve_digest(plan))
        result['started'] = False
        return result

    def session():
        reviewed = session_config.plan(root)
        result = session_config.apply(reviewed, guided.digest(reviewed))
        result.setdefault('started', False)
        return result

    def activation():
        reviewed = session_activation.plan(root)
        result = session_activation.apply(reviewed, guided.digest(reviewed))
        result['started'] = False
        return result

    return {'font': font, 'build': build, 'release': release, 'session': session, 'activation': activation}
