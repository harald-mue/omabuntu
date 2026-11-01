"""Explicit repair of verified enabled-but-unloaded hyprbars; no rebuild/reset."""
import fcntl
import os
from pathlib import Path
import pwd
import subprocess

import native_transition
import plugin_manager as manager
import plugin_migration
import user_install

ROOT = Path(__file__).resolve().parents[1]


def execute(argv):
    if argv != ['hyprpm', 'reload']:
        raise ValueError('Repair permits only an unforced system hyprpm reload')
    subprocess.run(['/usr/bin/hyprpm', 'reload'], check=True, timeout=30)


DEFAULT_EXECUTE = execute


def plan(root=ROOT, installation=None, directory=None, inspect=manager.probe, active_transaction=None):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Plugin repair is normal-user only')
    root = Path(root).absolute()
    app = installation or user_install.Installation(*user_install.defaults())
    directory = (Path('/var/cache/hyprpm') / pwd.getpwuid(os.getuid()).pw_name
                 if directory is None else Path(directory))
    blockers, proof, receipt, backend, selected = [], None, None, None, None
    try:
        selected = app.selected()
        if selected is None:
            raise ValueError('Repair requires an installed verified application')
        selected_meta = user_install.verify_bundle(app.root / selected, installed=True)
        if selected_meta.get('update_contract', {}).get('native_target') != native_transition.TO:
            raise ValueError('Repair requires the current reviewed application native target')
        source = manager.policy(root)
        if manager.bundle_policy(app.root / selected) != source:
            raise ValueError('Selected application and repair policy differ')
        receipt = user_install.read_json(app.state / 'hyprpm.json')
        if (type(receipt.get('schema_version')) is not int or receipt['schema_version'] != 1
                or receipt.get('activated') is not True or not isinstance(receipt.get('headers'), dict)):
            raise ValueError('Repair requires an existing successful enabled receipt with verified header fingerprints')
        proof = native_transition.manager_ready(source, app.state, inspect=inspect, directory=directory,
                                                allow_unloaded=True, active_transaction=active_transaction)
        backend = plugin_migration.migration_backend()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        blockers.append(str(error))
    shared = Path('/usr/share/pkgconfig/hyprland.pc')
    return {'schema_version': 1, 'kind': 'omabuntu-hyprbars-repair', 'action': 'repair',
            'root': str(root), 'app_root': str(app.root), 'state': str(app.state), 'launcher': str(app.launcher),
            'selected': selected, 'directory': str(directory), 'proof': proof, 'backend': backend,
            'before': proof['manager_inventory'] if proof else {}, 'receipt_before': receipt,
            'shared_pkgconfig': str(shared), 'shared_pkgconfig_before': manager.metadata_state(shared),
            'commands': [['hyprpm', 'reload']], 'loads_plugin': True,
            'changes': ['load-hyprbars'] if proof and not proof['loaded'] else [], 'blockers': blockers,
            'exclusions': ['No build, sudo, enable/disable, unload, download, rules reload or login changes',
                           'Private Lua, wallpaper, preferences and services are not modified',
                           'Do not run other plugin/manager operations concurrently']}


def apply(reviewed, approval, execute=execute, inspect=manager.probe):
    if (os.getuid() == 0 or os.environ.get('SUDO_USER') or reviewed.get('kind') != 'omabuntu-hyprbars-repair'
            or manager.guided.digest(reviewed) != approval or reviewed.get('blockers')):
        raise ValueError('Repair approval differs or the plan is blocked')
    app = user_install.Installation(reviewed['app_root'], reviewed['state'], reviewed['launcher'])
    directory = Path(reviewed['directory'])
    if execute is DEFAULT_EXECUTE:
        canonical = Path('/var/cache/hyprpm') / pwd.getpwuid(os.getuid()).pw_name
        if directory != canonical or (app.root, app.state, app.launcher) != tuple(map(Path, user_install.defaults())):
            raise ValueError('Real repair requires canonical user/manager paths')
    user_install.private_directory(app.state)
    fd = os.open(app.state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        def fresh(active=None):
            return plan(Path(reviewed['root']), app, directory, inspect, active)
        if fresh() != reviewed:
            raise ValueError('Repair inputs changed; review again')
        if not reviewed['changes']:
            return {'status': 'already-loaded', 'plugin_loaded': True, 'configuration_reloaded': False}
        case, journal, record = manager.backup_state(reviewed, app.state)
        active = {'path': str(journal), 'digest': approval}
        try:
            if fresh(active) != reviewed:
                raise ValueError('Repair state changed during backup')
            record.update(status='running', command_started=True)
            user_install.atomic_json(journal, record)
            execute(['hyprpm', 'reload'])
            after = fresh(active)
            if after['blockers'] or not after['proof']['loaded']:
                raise ValueError('Repair did not load the verified plugin')
            before_static, after_static = dict(reviewed), dict(after)
            before_static['proof'] = dict(reviewed['proof'], loaded=[])
            after_static['proof'] = dict(after['proof'], loaded=[])
            before_static['changes'] = after_static['changes'] = []
            if before_static != after_static:
                raise ValueError('Persistent or native state drifted during repair')
            record.update(status='completed', plugin_loaded=True)
            user_install.atomic_json(journal, record)
        except BaseException as error:
            record.update(status='manual-review-required', failure=type(error).__name__, failure_detail=str(error))
            user_install.atomic_json(journal, record)
            raise ValueError('Repair stopped; no automatic unload/retry. Inspect ' + str(journal)) from error
        return {'status': 'repaired-and-loaded', 'plugin_loaded': True, 'journal': str(journal),
                'configuration_reloaded': False, 'login_changed': False, 'system_packages_changed': False}
