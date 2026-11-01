"""Explicit, narrowly scoped migration of the reviewed mixed Hyprpm legacy state.

No implicit adoption, TOML rewriting, force, cache purge or live activation.
Application requires separate repository-replacement consent and verified backups.
"""
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tomllib

import plugin_manager as manager

FROM_VERSION = '0.56.2'
TO_VERSION = '0.57.0'
REPOSITORY = 'hyprland-plugins'
CONFIRMATION = 'replace hyprland-plugins'


def execute(argv):
    environment = manager.omabuntu_hyprpm.build_environment(os.environ)
    if argv == ['hyprpm', 'update']:
        # The official header refresh uses the installed binary, but its final
        # reconciliation would touch live plugins. A missing signature stops
        # that final phase before any IPC load/unload; validate the exit 1 and
        # complete header/global ABI postconditions in the parent instead.
        environment.pop('HYPRLAND_INSTANCE_SIGNATURE', None)
    subprocess.run(['/usr/bin/hyprpm', *argv[1:]], env=environment, check=True)


DEFAULT_EXECUTE = execute


def read_toml(path):
    if not manager.metadata_state(path)['existed']:
        raise ValueError('Missing manager TOML state')
    return tomllib.loads(path.read_text())


def migration_backend():
    path = Path('/usr/bin/hyprpm')
    manager.user_install.safe_parents(path.parent)
    info = path.stat()
    if (path.is_symlink() or not path.is_file() or info.st_size > 64 * 1024 * 1024
            or info.st_uid != 0 or info.st_mode & 0o022):
        raise ValueError('Migration requires the root-owned, non-writable system hyprpm binary')
    owner = manager.probe(['dpkg-query', '-S', str(path)]).strip()
    if not re.fullmatch(r'hyprland(?::amd64)?: /usr/bin/hyprpm', owner):
        raise ValueError('System hyprpm is not owned by the Hyprland package')
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'sha256': digest, 'uid': info.st_uid, 'gid': info.st_gid,
            'mode': info.st_mode & 0o7777, 'package': 'hyprland'}


def migration_packages():
    # Do not run APT or hyprpm just to determine installed prerequisites.
    import bootstrap_packages
    manifest, _ = bootstrap_packages.request_manifest(plugin_build_only=True)
    state = manager.guided.package_state(bootstrap_packages.omabuntu.probe)
    return {name: manager.guided.package_version(state, name)
            for name in dict.fromkeys([*manifest['groups']['runtime'], 'hyprland'])}


def plan(root=manager.ROOT, home=None, directory=None, inspect=manager.probe,
         shared_pkgconfig=Path('/usr/share/pkgconfig/hyprland.pc')):
    base = manager.plan(root, home, directory=directory, inspect=inspect, shared_pkgconfig=shared_pkgconfig)
    # Normal ownership blockers remain intact. Migration independently validates
    # the legacy identity; it does not suppress blockers by matching their text.
    blockers = list(base['prerequisite_blockers'])
    source = manager.policy(root)
    old = source['targets'].get(FROM_VERSION, {})
    target = source['targets'].get(TO_VERSION, {})
    directory = Path(base['directory'])
    facts = {}
    old_abi = None
    recognized = False
    if base['native'].get('version') != TO_VERSION or not target.get('apply_reviewed'):
        blockers.append('Legacy migration requires the reviewed clean Hyprland 0.57.0 target')
    if base['receipt_before'] is not None:
        blockers.append('Existing Omabuntu ownership receipt requires a different migration; no overwrite')
    unknown = {name.split('/')[0] for name in base['before']} - {'state.toml', 'headersRoot', REPOSITORY}
    if unknown:
        blockers.append('Unexpected manager cache entries require manual review')
    try:
        repositories = sorted(directory.glob('*/state.toml'))
        if repositories != [directory / REPOSITORY / 'state.toml']:
            raise ValueError('Migration requires exactly one official legacy repository')
        facts = read_toml(repositories[0])
        repo = facts.get('repository', {})
        plugin = facts.get('hyprbars', {})
        if (repo.get('name') != REPOSITORY or repo.get('url') != source['repository']
                or repo.get('rev') != old.get('plugin_commit') or repo.get('hash') != target.get('plugin_commit')
                or plugin.get('filename') != 'hyprbars.so' or plugin.get('failed') is not False
                or type(plugin.get('enabled')) is not bool):
            raise ValueError('Only the reviewed mixed 0.56-pin/0.57-build legacy repository may be migrated')
        for name, row in facts.items():
            if name == 'repository':
                continue
            if not isinstance(row, dict) or type(row.get('enabled')) is not bool:
                raise ValueError('Malformed plugin enablement requires manual review')
            if name != 'hyprbars' and row['enabled']:
                raise ValueError('Other enabled plugins prevent legacy migration')
        old_abi = read_toml(directory / 'state.toml').get('state', {}).get('hash')
        if (not isinstance(old_abi, str) or not old_abi.startswith(old.get('hyprland_commit', 'INVALID') + '_')
                or old_abi == base['native'].get('abiHash')):
            raise ValueError('Global ABI is not the reviewed stale 0.56 manager state')
        recognized = True
    except (OSError, ValueError, TypeError, AttributeError) as error:
        blockers.append(str(error))
    backend = None
    try:
        backend = migration_backend()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        blockers.append('System manager backend verification failed: ' + str(error))
    packages = migration_packages()
    missing = [name for name, version in packages.items() if not version]
    if missing:
        blockers.append('Missing plugin-build packages: ' + ', '.join(missing))
    commands = ([['hyprpm', 'disable', 'hyprbars'], ['hyprpm', 'remove', source['repository']],
                 ['hyprpm', 'update'], ['hyprpm', 'add', source['repository'], target['plugin_commit']]]
                if recognized and base['native'].get('version') == TO_VERSION else [])
    return {**base, 'kind': 'omabuntu-hyprpm-migration', 'action': 'migrate', 'commands': commands,
            'migration': {'recognized': recognized, 'repository_before': facts,
                          'global_abi_before': old_abi, 'packages': packages, 'backend': backend,
                          'replacement_confirmation': CONFIRMATION, 'leaves_enabled': False,
                          'header_refresh_without_compositor': True},
            'blockers': blockers, 'status': 'blocked' if blockers else 'review-required',
            'loads_plugin': False, 'replaces_repository': True}


def assert_quiet(reviewed, inspect):
    if manager.guided.digest(manager.policy(Path(reviewed['root']))) != reviewed['policy_digest']:
        raise ValueError('Plugin policy changed during migration')
    if manager.build_hyprbars.installed_version() != reviewed['native']:
        raise ValueError('Installed Hyprland changed during migration')
    if json.loads(inspect(['hyprctl', '-j', 'version'])) != reviewed['running']:
        raise ValueError('Running Hyprland changed during migration')
    if manager.loaded_plugins(inspect):
        raise ValueError('A plugin loaded during migration; no further manager commands permitted')
    if migration_backend() != reviewed['migration']['backend']:
        raise ValueError('System hyprpm binary/package ownership changed during migration')
    if migration_packages() != reviewed['migration']['packages']:
        raise ValueError('Plugin-build packages changed during migration')
    receipt = Path(reviewed['state']) / 'hyprpm.json'
    if receipt.exists() or receipt.is_symlink():
        raise ValueError('An ownership receipt appeared during migration')
    directory = Path(reviewed['directory'])
    if (manager.directory_state(directory) != reviewed['directory_before']
            or manager.directory_state(directory.parent) != reviewed['cache_parent_before']):
        raise ValueError('Manager cache directory ownership/mode changed')


def unchanged_outside(before, after, allowed):
    for name in set(before) | set(after):
        if any(name == prefix or name.startswith(prefix + '/') for prefix in allowed):
            continue
        if before.get(name) != after.get(name):
            raise ValueError('Unexpected manager cache mutation: ' + name)


def verify_headers(reviewed, inspect=manager.probe):
    directory = Path(reviewed['directory'])
    if read_toml(directory / 'state.toml').get('state', {}).get('hash') != reviewed['native']['abiHash']:
        raise ValueError('Manager global ABI does not match the running/built compositor')
    return manager.plugin_login.header_state(directory, reviewed['native'], inspect)


def verify_step(reviewed, index, before, after, inspect=manager.probe):
    directory = Path(reviewed['directory'])
    repository = directory / REPOSITORY
    if index == 0:
        expected = copy.deepcopy(reviewed['migration']['repository_before'])
        expected['hyprbars']['enabled'] = False
        if read_toml(repository / 'state.toml') != expected:
            raise ValueError('Disable did not produce exactly the reviewed enablement change')
        allowed = [REPOSITORY + '/state.toml']
        if 'headersRoot' not in before and 'headersRoot' in after:
            if not after['headersRoot'].get('directory') or any(n.startswith('headersRoot/') for n in after):
                raise ValueError('Disable created unexpected header cache content')
            allowed.append('headersRoot')  # DataState may initialize this empty directory.
        unchanged_outside(before, after, allowed)
    elif index == 1:
        if repository.exists() or repository.is_symlink():
            raise ValueError('Official repository removal did not complete')
        unchanged_outside(before, after, [REPOSITORY])
    elif index == 2:
        if list(directory.glob('*/state.toml')):
            raise ValueError('A repository appeared during header-only refresh')
        unchanged_outside(before, after, ['headersRoot', 'state.toml'])
        verify_headers(reviewed, inspect)
    elif index == 3:
        unchanged_outside(before, after, [REPOSITORY, 'state.toml'])
        verify_headers(reviewed, inspect)
        if sorted(directory.glob('*/state.toml')) != [repository / 'state.toml']:
            raise ValueError('Unexpected repository after pinned add')
        data = read_toml(repository / 'state.toml')
        source = manager.policy(Path(reviewed['root']))
        target = source['targets'][TO_VERSION]
        row = data.get('repository', {})
        plugin = data.get('hyprbars', {})
        if (row.get('name') != REPOSITORY or row.get('url') != source['repository']
                or row.get('rev') != target['plugin_commit'] or row.get('hash') != target['plugin_commit']
                or plugin.get('failed') is not False or plugin.get('filename') != 'hyprbars.so'):
            raise ValueError('New manager repository has no successful exact pinned hyprbars build')
        for name, item in data.items():
            if name != 'repository' and (not isinstance(item, dict) or item.get('enabled') is not False):
                raise ValueError('A newly registered plugin is enabled or malformed')
        if not after.get(REPOSITORY + '/hyprbars.so', {}).get('sha256'):
            raise ValueError('New manager library is not a regular built file')
    if index < 2 and read_toml(directory / 'state.toml').get('state', {}).get('hash') != reviewed['migration']['global_abi_before']:
        raise ValueError('Stale global ABI changed before the isolated header refresh')


def apply(reviewed, approval, replace_approved=False, execute=execute, inspect=manager.probe):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Run migration as the ordinary user, never through sudo')
    if (reviewed.get('kind') != 'omabuntu-hyprpm-migration' or reviewed.get('action') != 'migrate'
            or manager.guided.digest(reviewed) != approval or reviewed.get('blockers')
            or replace_approved is not True):
        raise ValueError('Migration blocked, approval differs or repository replacement is not approved')
    if execute is DEFAULT_EXECUTE:
        expected = Path('/var/cache/hyprpm') / manager.pwd.getpwuid(os.getuid()).pw_name
        if (Path(reviewed['directory']) != expected
                or Path(reviewed['shared_pkgconfig']) != Path('/usr/share/pkgconfig/hyprland.pc')):
            raise ValueError('Real manager execution requires canonical system paths, not fixture overrides')
    state = manager.user_install.private_directory(Path(reviewed['state']))
    fd = os.open(state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fresh = plan(Path(reviewed['root']), Path(reviewed['home']), Path(reviewed['directory']), inspect,
                     Path(reviewed['shared_pkgconfig']))
        if fresh != reviewed:
            raise ValueError('Migration state changed; review again before any manager mutation')
        case, journal, record = manager.backup_state(reviewed, state)
        record['steps'] = []
        directory = Path(reviewed['directory'])
        shared = Path(reviewed['shared_pkgconfig'])
        checkpoint = reviewed['before']
        shared_checkpoint = reviewed['shared_pkgconfig_before']
        try:
            for index, command in enumerate(reviewed['commands']):
                assert_quiet(reviewed, inspect)
                if manager.manager_inventory(directory) != checkpoint or manager.metadata_state(shared) != shared_checkpoint:
                    raise ValueError('Manager/system metadata changed between migration steps')
                step = {'command': command, 'status': 'started', 'returncode': None}
                record['steps'].append(step)
                manager.user_install.atomic_json(journal, record)
                result_code = 0
                try:
                    execute(command)
                except subprocess.CalledProcessError as error:
                    step['returncode'] = error.returncode
                    if index not in (0, 2) or error.returncode != 1:
                        raise
                    # Only stale-ABI disable and explicitly socket-disconnected
                    # header refresh can converge despite exit 1. Prove the
                    # complete step postconditions before continuing.
                    result_code = 1
                assert_quiet(reviewed, inspect)
                after = manager.manager_inventory(directory)
                shared_after = manager.metadata_state(shared)
                if index != 2 and shared_after != shared_checkpoint:
                    raise ValueError('System pkg-config metadata changed outside header refresh')
                verify_step(reviewed, index, checkpoint, after, inspect)
                outcome = ('disabled-with-stale-headers' if index == 0 else
                           'headers-refreshed-without-live-reconciliation') if result_code else 'success'
                step.update(status='verified', returncode=result_code, outcome=outcome)
                checkpoint, shared_checkpoint = after, shared_after
                manager.user_install.atomic_json(journal, record)
            assert_quiet(reviewed, inspect)
            if manager.manager_inventory(directory) != checkpoint or manager.metadata_state(shared) != shared_checkpoint:
                raise ValueError('Manager changed before receipt creation')
            receipt = {'schema_version': 1, 'policy_digest': reviewed['policy_digest'], 'native': reviewed['native'],
                       'library': reviewed['library'],
                       'library_sha256': checkpoint[REPOSITORY + '/hyprbars.so']['sha256'],
                       'activated': False, 'migration_journal': str(journal),
                       'headers': verify_headers(reviewed, inspect)}
            manager.user_install.atomic_json(state / 'hyprpm.json', receipt)
            record.update(status='completed', shared_pkgconfig_after=shared_checkpoint)
            manager.user_install.atomic_json(journal, record)
        except BaseException as error:
            detail = str(error) if isinstance(error, ValueError) else type(error).__name__
            record.update(status='manual-review-required', failure=type(error).__name__, failure_detail=detail)
            if record['steps'] and record['steps'][-1]['status'] == 'started':
                record['steps'][-1]['status'] = 'failed-or-unverified'
            try:
                record['shared_pkgconfig_after'] = manager.metadata_state(shared)
            except (OSError, ValueError):
                record['shared_pkgconfig_after'] = {'status': 'unreadable-requires-review'}
            manager.user_install.atomic_json(journal, record)
            raise ValueError('Migration stopped (' + detail + '); no automatic restore or retry. Inspect backup and journal: ' + str(case)) from error
        return {'status': 'plugin-migrated-disabled', 'journal': str(journal), 'plugin_loaded': False,
                'configuration_reloaded': False, 'autostart_changed': False,
                'repository_replaced': True, 'activation_required': True}
