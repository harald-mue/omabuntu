#!/usr/bin/env python3
"""Gated local-bundle installer. No automatic configuration or session changes."""
import argparse
import fcntl
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import subprocess
import sys

import check_runtime
import omabuntu
import package_plan
import user_install

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'packages/installer-runtime.json'
PROBE = '''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes
import QtQuick.Effects
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Networking
import Quickshell.Hyprland as WM
import Quickshell.Bluetooth as Blue
import Quickshell.Services.UPower as Power
import Quickshell.Services.Pipewire as Audio
import Quickshell.Services.SystemTray as Tray
ShellRoot {
  property Blue.BluetoothAdapter adapterType: null
  property Power.UPowerDevice batteryType: null
  property Audio.PwNode audioType: null
  property Tray.SystemTrayItem trayType: null
  Image {
    id: image
    source: "file:///probe/still.webp"
  }
  Timer {
    interval: 50; running: true; repeat: true
    onTriggered: {
      if (image.status === Image.Ready && image.sourceSize.width > 0 && image.sourceSize.height > 0) {
        console.log("OMABUNTU_INSTALL_WEBP_READY"); Qt.quit()
      } else if (image.status === Image.Error) Qt.exit(42)
    }
  }
}
'''


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def manifest(path=MANIFEST, wallpaper=False):
    value = json.loads(path.read_text())
    if (not isinstance(value, dict) or value.get('schema_version') != 1
            or value.get('name') != 'omabuntu-local-bundle'):
        raise ValueError('Unsupported runtime manifest')
    target = value.get('target')
    if (not isinstance(target, dict) or set(target) != {'ubuntu', 'hyprland', 'qt'}
            or any(not isinstance(v, str) or not re.fullmatch(r'\d+(?:\.\d+)+', v)
                   for v in target.values())):
        raise ValueError('Invalid supported-target specification')
    if not isinstance(value.get('groups'), dict):
        raise ValueError('Missing runtime package groups')
    names = []
    for group in ('runtime', 'wallpaper') if wallpaper else ('runtime',):
        entries = value.get('groups', {}).get(group)
        if not isinstance(entries, list) or not entries:
            raise ValueError('Missing runtime package group')
        for name in entries:
            if not isinstance(name, str) or not package_plan.PACKAGE_NAME.fullmatch(name):
                raise ValueError('Unsafe package name')
            if name not in names:
                names.append(name)
    return value, names


def checked(run, command, timeout=30):
    result = run(command, timeout=timeout)
    if result.get('status') != 'ok':
        raise ValueError('Probe failed (%s): %s' % (result.get('status'), ' '.join(command)))
    return result['stdout']


def package_state(run):
    text = checked(run, ['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\t${db:Status-Status}\n'])
    packages = {}
    for line in text.splitlines():
        fields = line.split('\t')
        if len(fields) != 3:
            raise ValueError('Unrecognized dpkg snapshot')
        if fields[2] == 'installed':
            packages[fields[0]] = fields[1]
    manual = sorted(checked(run, ['apt-mark', 'showmanual']).splitlines())
    held = sorted(checked(run, ['apt-mark', 'showhold']).splitlines())
    return {'installed': packages, 'manual': manual, 'held': held}


def package_version(state, name):
    packages = state['installed']
    return packages.get(name) or packages.get(name + ':amd64')


def host_blockers(spec, os_info=None):
    info = omabuntu.read_os_release() if os_info is None else os_info
    values = info.get('values', {})
    blockers = []
    if (info.get('status') != 'ok' or values.get('ID') != 'ubuntu'
            or values.get('VERSION_ID') != spec['target']['ubuntu']):
        blockers.append('Supported target requires Ubuntu ' + spec['target']['ubuntu'])
    if platform.machine() != 'x86_64':
        blockers.append('Only the reviewed x86_64 target is supported')
    return blockers


def package_review(wallpaper=False, run=omabuntu.probe, manifest_path=MANIFEST):
    spec, names = manifest(manifest_path, wallpaper)
    before = package_state(run)
    policy = checked(run, ['apt-cache', 'policy', *names])
    candidates = package_plan.parse_policy(policy)
    missing = [name for name in names if not package_version(before, name)]
    blockers = host_blockers(spec)
    pinned = []
    for name in missing:
        version = candidates.get(name, {}).get('candidate')
        if not version:
            blockers.append('No APT candidate: ' + name)
        else:
            pinned.append(name + '=' + version)
    simulation = ''
    transaction = {'new': [], 'upgraded_or_changed': [], 'removed': []}
    resolved = {}
    if pinned and not blockers:
        simulation = checked(run, ['apt-get', '--simulate', '--no-remove',
                                  '--no-install-recommends', 'install', *pinned], timeout=90)
        transaction = package_plan.summarize_simulation(simulation)
        if transaction['removed'] or transaction['upgraded_or_changed']:
            blockers.append('Removals or changes to installed packages are not permitted')
        for line in simulation.splitlines():
            if line.startswith('Inst '):
                match = re.fullmatch(r'Inst ([a-z0-9][a-z0-9+.:-]*) \(([^\s]+) .*\)', line)
                if not match or not package_plan.VERSION.fullmatch(match.group(2)):
                    blockers.append('Unrecognized or unsafe APT install line')
                    continue
                resolved[match.group(1)] = match.group(2)
        if not transaction['new']:
            blockers.append('APT reported no additions for missing packages')
        planned = set(transaction['new'])
        if any(name not in planned and name + ':amd64' not in planned for name in missing):
            blockers.append('Simulation does not install every missing request')
        for request in pinned:
            name, expected = request.split('=', 1)
            if resolved.get(name, resolved.get(name + ':amd64')) != expected:
                blockers.append('Solver version differs from reviewed candidate: ' + name)
    return {'manifest_sha256': digest(spec), 'wallpaper': wallpaper,
            'packages': names, 'before': before, 'policy': policy,
            'pinned': pinned, 'resolved': resolved,
            'simulation': simulation, 'transaction': transaction,
            'blockers': blockers,
            'status': 'blocked' if blockers else 'review-required'}


def private_case():
    parent = user_install.private_directory(ROOT / 'work')
    parent = user_install.private_directory(parent / 'installer')
    case = parent / user_install.stamp()
    case.mkdir(mode=0o700)
    return case


def save(case, name, value):
    path = case / name
    omabuntu.save_json(path, value)
    return path


def runtime_probe(bundle, case, run=omabuntu.probe):
    """Only trusted, verified bundles, isolated from host services and display."""
    user_install.verify_bundle(bundle)
    # Authored 16x16 gradient, lossless WebP, generated for this codec check.
    # The native Qt reader rejected a valid but only 38-byte 1x1 fixture;
    # this fixture is exercised by the asset-free native preflight instead.
    # No imported wallpaper or local asset is needed in a public checkout.
    import base64
    probe_image = base64.b64decode('UklGRlwAAABXRUJQVlA4TFAAAAAvD8ADAH9AmG3067TOH+wYxIIp/pZOYsEUf0uv+a/CPlSgAucAqCLbhgoqqKCCCiqooIIKKqigggoqqOBrO0T0PwORRKZQaXQGk8XmcHl8AA==')
    for name in ('probe', 'home/runtime', 'home/config', 'home/cache', 'home/state', 'home/data'):
        (case / name).mkdir(mode=0o700, parents=True, exist_ok=True)
    (case / 'probe/shell.qml').write_text(PROBE)
    (case / 'probe/still.webp').write_bytes(probe_image)
    (case / 'probe/fonts.conf').write_text('<fontconfig><dir>/usr/share/fonts</dir></fontconfig>')
    binary = check_runtime.PREFIX + '/bin/quickshell'
    linkage = run(check_runtime.sandbox_command(bundle / 'runtime', case,
                  ['ldd', '-r', binary]), timeout=30)
    qml = run(check_runtime.sandbox_command(bundle / 'runtime', case,
              [binary, '--no-color', '--path', '/probe/shell.qml']), timeout=30)
    text = qml.get('stdout', '') + qml.get('stderr', '')
    libraries = linkage.get('stdout', '') + linkage.get('stderr', '')
    passed = (linkage.get('status') == 'ok' and qml.get('status') == 'ok'
              and not any(x in libraries for x in ('not found', 'undefined symbol'))
              and all(x in libraries for x in ('libQt6Core', 'libQt6Qml', 'libQt6Quick'))
              and 'Configuration Loaded' in text and 'OMABUNTU_INSTALL_WEBP_READY' in text
              and not re.search(r'^\s*(?:ERROR|FATAL|CRITICAL)\b', text, re.MULTILINE)
              and not any(x in text for x in ('ReferenceError:', 'TypeError:',
                          'is not installed', 'Cannot create', 'Required property',
                          'Failed to load configuration')))
    save(case, 'runtime-probe.json', {'linkage': linkage, 'qml': qml})
    user_install.verify_bundle(bundle)
    return {'status': 'passed' if passed else 'failed',
            'scope': 'Isolated linkage/imports and WebP decode, not native visual acceptance'}


def preflight(bundle, wallpaper=False, run=omabuntu.probe, os_info=None, runtime=None):
    bundle = Path(bundle).absolute()
    meta = user_install.verify_bundle(bundle)
    spec, names = manifest(wallpaper=wallpaper)
    os_info = omabuntu.read_os_release() if os_info is None else os_info
    state = package_state(run)
    checks = []
    checks.append({'name': 'ubuntu-target', 'ok': not host_blockers(spec, os_info),
                   'blockers': host_blockers(spec, os_info)})
    version = run(['Hyprland', '--version'], timeout=15)
    checks.append({'name': 'hyprland-target', 'ok': version.get('status') == 'ok'
                   and re.search(r'(?<![\d.])' + re.escape(spec['target']['hyprland']) + r'(?![\d.])',
                                 version.get('stdout', '') + version.get('stderr', '')) is not None,
                   'probe': version})
    qt = package_version(state, 'libqt6core6t64') or ''
    checks.append({'name': 'qt-target', 'ok': qt.split('+')[0].split('-')[0] == spec['target']['qt']})
    missing = [name for name in names if not package_version(state, name)]
    checks.append({'name': 'runtime-packages', 'ok': not missing, 'missing': missing})
    font = run(['fc-match', '--format=%{family}\\n', 'monospace'], timeout=15)
    checks.append({'name': 'monospace-font', 'ok': font.get('status') == 'ok'
                   and bool(font.get('stdout', '').strip()),
                   'family': font.get('stdout', '').strip(), 'probe_status': font.get('status'),
                   'limit': 'Family resolution only; Nerd Font glyph acceptance remains separate'})
    wallpaper_info = {'status': 'not-requested'}
    if wallpaper:
        running = run(['pgrep', '-u', str(os.getuid()), '-x', 'hyprpaper'], timeout=10)
        help_result = run(['hyprctl', 'hyprpaper', '--help'], timeout=10)
        help_text = help_result.get('stdout', '') + help_result.get('stderr', '')
        ipc = ('legacy' if 'preload' in help_text else 'current' if 'wallpaper' in help_text else 'unknown')
        wallpaper_info = {'installed_version': package_version(state, 'hyprpaper'),
                          'process_probe': running, 'ipc_help_probe': help_result, 'ipc': ipc,
                          'running': True if running.get('status') == 'ok' else
                          False if running.get('returncode') == 1 else None,
                          'limit': 'Informational only: no process start, ownership grant or live apply'}
    case = private_case()
    runtime_result = (runtime or runtime_probe)(bundle, case)
    checks.append({'name': 'runtime-linkage-imports-webp', 'ok': runtime_result.get('status') == 'passed',
                   'result': runtime_result})
    report = {'kind': 'omabuntu-preflight', 'bundle': str(bundle), 'version': meta['version'],
              'bundle_sha256': digest(meta), 'manifest_sha256': digest(spec), 'wallpaper': wallpaper,
              'checks': checks, 'wallpaper_daemon': wallpaper_info,
              'status': 'passed' if all(c['ok'] for c in checks) else 'blocked',
              'limits': ['No session activation, configuration merge or native acceptance.',
                         'Existing compatible compositor and desktop services are required.',
                         'Wallpaper startup is separate; installation does not start a daemon.']}
    path = save(case, 'preflight.json', report)
    return report, path


def seal(kind, payload):
    return {'schema_version': 1, 'kind': kind, 'payload': payload,
            'approval': digest({'kind': kind, 'payload': payload})}


def read_plan(path, kind, approval):
    value = user_install.read_json(Path(path))
    if (not isinstance(value, dict) or value.get('schema_version') != 1 or value.get('kind') != kind
            or not isinstance(value.get('payload'), dict)
            or value.get('approval') != seal(kind, value['payload'])['approval']
            or approval != value.get('approval')):
        raise ValueError('Explicit approval must match the reviewed plan digest')
    return value['payload']


def terminal_install(command):
    """No credential capture, shell expansion, auto-yes or hook bypass."""
    if not sys.stdin.isatty():
        raise ValueError('Run the approved package step in your interactive terminal')
    return subprocess.run(command, check=False, timeout=1800).returncode


def apply_packages(plan_path, approval, run=omabuntu.probe, execute=terminal_install):
    reviewed = read_plan(plan_path, 'omabuntu-package-plan', approval)
    fresh = package_review(wallpaper=reviewed.get('wallpaper') is True, run=run)
    if fresh != reviewed or fresh['blockers']:
        raise ValueError('Package plan or host state changed; create and approve a new plan')
    case = private_case()
    record = {'status': 'prepared', 'reviewed_plan': seal('omabuntu-package-plan', fresh),
              'note': 'Package rollback is separate; no automatic purge or autoremove.'}
    save(case, 'before.json', record)
    if not fresh['pinned']:
        save(case, 'after.json', {'status': 'already-satisfied', 'after': fresh['before']})
        return case
    command = ['sudo', 'apt-get', '--no-remove', '--no-upgrade', '--no-install-recommends',
               'install', *[name + '=' + version for name, version in sorted(fresh['resolved'].items())]]
    outcome = {'status': 'failed', 'command': command}
    try:
        outcome['returncode'] = execute(command)
        after = package_state(run)
        outcome['after'] = after
        before_versions = fresh['before']['installed']
        changed = [n for n, v in before_versions.items() if after['installed'].get(n) != v]
        additions = set(after['installed']) - set(before_versions)
        allowed = {n.split(':')[0] for n in fresh['transaction']['new']}
        unexpected = sorted(n for n in additions if n.split(':')[0] not in allowed)
        wrong = [n for n, v in fresh['resolved'].items() if package_version(after, n) != v]
        changed_marks = (not set(fresh['before']['manual']).issubset(after['manual'])
                         or fresh['before']['held'] != after['held'])
        outcome.update(changed_existing=changed, unexpected_additions=unexpected,
                       wrong_versions=wrong, changed_existing_marks=changed_marks)
        if outcome['returncode'] == 0 and not (changed or unexpected or wrong or changed_marks):
            outcome['status'] = 'verified'
    except KeyboardInterrupt:
        outcome.update(status='interrupted', error='User interrupted the package transaction; inspect package state')
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        outcome['error'] = str(error)
    if 'after' not in outcome:
        try:
            outcome['after'] = package_state(run)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            outcome['snapshot_error'] = str(error)
    save(case, 'after.json', outcome)
    if outcome['status'] != 'verified':
        raise ValueError('Package transaction incomplete or unexpected; inspect ' + str(case))
    return case


def deployment_review(bundle, installation, wallpaper=False):
    report, path = preflight(bundle, wallpaper)
    if report['status'] != 'passed':
        raise ValueError('Preflight blocked deployment; inspect ' + str(path))
    if installation.running():
        raise ValueError('Managed shell is running; stop it explicitly before planning replacement')
    return {'bundle': str(Path(bundle).absolute()), 'bundle_sha256': report['bundle_sha256'],
            'manifest_sha256': report['manifest_sha256'], 'wallpaper': wallpaper,
            'root': str(installation.root), 'state': str(installation.state),
            'launcher': str(installation.launcher), 'deployment': installation.plan(bundle)}


def apply_deployment(plan_path, approval):
    reviewed = read_plan(plan_path, 'omabuntu-deployment-plan', approval)
    installation = user_install.Installation(reviewed['root'], reviewed['state'], reviewed['launcher'])
    fresh = deployment_review(reviewed['bundle'], installation, reviewed['wallpaper'])
    if fresh != reviewed:
        raise ValueError('Deployment plan changed; create and approve a new plan')
    # Use the same transaction lock and prestate convention as the existing CLI.
    state_existed = installation.state.exists()
    user_install.private_directory(installation.state)
    fd = os.open(installation.state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Recheck the file/selector prestate and bundle after taking the manager's lock.
        if digest(user_install.verify_bundle(Path(fresh['bundle']))) != fresh['bundle_sha256']:
            raise ValueError('Bundle changed before deployment; review a new plan')
        locked_plan = installation.plan(Path(fresh['bundle']))
        locked_plan['prestate']['state_existed'] = state_existed
        if installation.running() or locked_plan != fresh['deployment']:
            raise ValueError('Deployment changed while waiting for its lock; review a new plan')
        return installation.install(Path(fresh['bundle']), state_preexisted=state_existed)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    for action in ('preflight', 'plan'):
        p = commands.add_parser(action)
        p.add_argument('bundle', type=Path)
        p.add_argument('--with-wallpaper', action='store_true')
    p = commands.add_parser('package-plan')
    p.add_argument('--with-wallpaper', action='store_true')
    for action in ('packages', 'install'):
        p = commands.add_parser(action)
        p.add_argument('plan', type=Path)
        p.add_argument('--approve')
        p.add_argument('--apply', action='store_true')
    p = commands.add_parser('start')
    p.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    if os.geteuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Run as your normal user, not via sudo; only the package subprocess uses sudo')
    os.umask(0o077)
    # Serialize guided operations; the existing manager also guards its own work.
    parent = user_install.private_directory(ROOT / 'work')
    parent = user_install.private_directory(parent / 'installer')
    fd = os.open(parent / 'operation.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == 'preflight':
            report, path = preflight(args.bundle, args.with_wallpaper)
            print(path)
            print(report['status'])
            return 0 if report['status'] == 'passed' else 1
        if args.action == 'package-plan':
            payload = package_review(args.with_wallpaper)
            value = seal('omabuntu-package-plan', payload)
            print(save(private_case(), 'package-plan.json', value))
            print('Approval digest:', value['approval'])
            print('Status:', payload['status'])
            print('Pinned requests:', ', '.join(payload['pinned']) or '(already installed)')
            print('Review the full private JSON, including origins, simulation and package prestate.')
            print('All new dependencies are version-pinned on apply and may receive manual APT marks.')
            return 1 if payload['blockers'] else 0
        if args.action == 'plan':
            installation = user_install.Installation(*user_install.defaults())
            value = seal('omabuntu-deployment-plan', deployment_review(args.bundle, installation, args.with_wallpaper))
            print(save(private_case(), 'deployment-plan.json', value))
            print('Approval digest:', value['approval'])
            print('Review the JSON; deployment does not start the shell or wallpaper daemon.')
            return 0
        if args.action == 'start':
            if not args.apply:
                print('No activation: pass --apply to grant the installed shell session lifetime. No wallpaper start.')
                return 0
            return user_install.main(['start'])
        if not args.apply:
            print('No changes: review the saved plan, then use --approve DIGEST --apply.')
            return 0
        if not args.approve:
            raise ValueError('Missing explicit --approve DIGEST')
        if args.action == 'packages':
            print('Package transaction evidence:', apply_packages(args.plan, args.approve))
        else:
            print(json.dumps(apply_deployment(args.plan, args.approve), indent=2))
        return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        message = str(error)
        if os.geteuid() != 0 and not os.environ.get('SUDO_USER'):
            try:
                path = save(private_case(), 'failure.json',
                            {'status': 'failed', 'error': message,
                             'note': 'No automatic rollback of package side effects.'})
                message += '\nPrivate failure report: ' + str(path)
            except (OSError, ValueError):
                pass
        raise SystemExit(message)
