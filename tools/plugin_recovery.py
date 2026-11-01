"""Explicit continuation of only the reviewed PPA-header migration checkpoint.

The original journal stays immutable; a hash-bound resolution is written only
when the new backup, pinned build and inactive receipt are fully verified.
"""
import copy
import fcntl
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile
import tomllib

import plugin_migration as migration

manager = migration.manager
CONFIRMATION = 'resume hyprland-plugins'


def sha(path, limit=600 * 1024 * 1024):
    manager.user_install.safe_parents(path.parent)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Unsafe recovery evidence file')
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def plan(journal, root=manager.ROOT, home=None, inspect=manager.probe):
    home = Path.home() if home is None else Path(home)
    state = Path(os.environ.get('XDG_STATE_HOME') or home / '.local/state') / 'omabuntu'
    journal = Path(journal).absolute()
    if (journal != journal.resolve() or journal.name != 'transaction.json'
            or journal.parent.parent != state / 'plugin-transactions'):
        raise ValueError('Recovery needs a direct existing transaction in the current user state')
    original = manager.plugin_login.read_json(journal)
    old = original.get('plan', {})
    source = manager.policy(root)
    target = source['targets'][migration.TO_VERSION]
    commands = [['hyprpm', 'disable', 'hyprbars'], ['hyprpm', 'remove', source['repository']],
                ['hyprpm', 'update'], ['hyprpm', 'add', source['repository'], target['plugin_commit']]]
    steps = original.get('steps', [])
    if (original.get('status') != 'manual-review-required' or original.get('backup_verified') is not True
            or original.get('failure_detail') != 'Manager installed headers or pkg-config file are missing'
            or old.get('kind') != 'omabuntu-hyprpm-migration' or old.get('action') != 'migrate'
            or old.get('blockers') or old.get('receipt_before') is not None
            or old.get('root') != str(root) or old.get('home') != str(home) or old.get('state') != str(state)
            or old.get('native', {}).get('version') != migration.TO_VERSION
            or old.get('commands') != commands or len(steps) != 3
            or [step.get('command') for step in steps] != commands[:3]
            or [step.get('status') for step in steps] != ['verified', 'verified', 'failed-or-unverified']
            or steps[0].get('returncode') not in (0, 1) or steps[1].get('returncode') != 0
            or steps[2].get('returncode') != 1):
        raise ValueError('Not the supported interrupted PPA-header migration checkpoint')
    if journal.with_name('resolution.json').exists() or journal.with_name('resolution.json').is_symlink():
        raise ValueError('Existing recovery resolution requires review; no overwrite or repeated build')
    for other in (state / 'plugin-transactions').glob('*/transaction.json'):
        if other != journal and not manager.plugin_login.transaction_complete(other):
            raise ValueError('Another interrupted operation requires manual review')
    archive = journal.with_name('manager-before.tar')
    archive_sha = sha(archive)
    if archive_sha != original.get('backup_sha256'):
        raise ValueError('Original verified backup changed')
    with tarfile.open(archive, 'r') as backup:
        member = backup.getmember('state.toml')
        if not member.isreg() or member.size > 65536:
            raise ValueError('Invalid original global state backup')
        with backup.extractfile(member) as stream:
            previous = tomllib.loads(stream.read().decode())
    expected = copy.deepcopy(previous)
    expected['state']['hash'] = old['native']['abiHash']
    directory = Path(old['directory'])
    before = manager.manager_inventory(directory)
    if (set(before) != {'headersRoot', 'state.toml'}
            or before.get('headersRoot') != old['before'].get('headersRoot')
            or migration.read_toml(directory / 'state.toml') != expected):
        raise ValueError('Current manager is not the isolated empty-cache checkpoint; no automatic reconciliation')
    if {key: value for key, value in before['state.toml'].items() if key != 'sha256'} != {
            key: value for key, value in old['before']['state.toml'].items() if key != 'sha256'}:
        raise ValueError('Global state permissions/ownership changed')
    shared = Path(old['shared_pkgconfig'])
    if (manager.metadata_state(shared) != old['shared_pkgconfig_before']
            or original.get('shared_pkgconfig_after') != old['shared_pkgconfig_before']):
        raise ValueError('Shared pkg-config metadata changed; this recovery cannot restore it')
    if old['shared_pkgconfig_before']['existed']:
        if sha(journal.with_name('system-hyprland.pc.before'), 65536) != old['shared_pkgconfig_before']['sha256']:
            raise ValueError('Original shared pkg-config backup changed')
    reviewed = {**old, 'kind': 'omabuntu-hyprpm-recovery', 'action': 'migrate-recover',
                'before': before, 'commands': commands[3:], 'blockers': [], 'status': 'review-required',
                'ownership_blockers': [], 'prerequisite_blockers': [], 'replaces_repository': False,
                'recovery': {'journal': str(journal), 'sha256': sha(journal, 2 * 1024 * 1024),
                             'backup_sha256': archive_sha, 'confirmation': CONFIRMATION}}
    migration.assert_quiet(reviewed, inspect)
    reviewed['headers'] = migration.verify_headers(reviewed, inspect)
    if reviewed['headers']['layout'] != 'system-package':
        raise ValueError('Only the reviewed empty-cache/package-header recovery is supported')
    return reviewed


def apply(reviewed, approval, resume_approved=False, execute=migration.execute, inspect=manager.probe):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Run recovery as the ordinary user, never through sudo')
    if (reviewed.get('kind') != 'omabuntu-hyprpm-recovery' or reviewed.get('blockers')
            or manager.guided.digest(reviewed) != approval or resume_approved is not True):
        raise ValueError('Recovery requires the exact fresh plan and separate continuation approval')
    if execute is migration.DEFAULT_EXECUTE:
        expected = Path('/var/cache/hyprpm') / manager.pwd.getpwuid(os.getuid()).pw_name
        if (Path(reviewed['directory']) != expected
                or Path(reviewed['shared_pkgconfig']) != Path('/usr/share/pkgconfig/hyprland.pc')):
            raise ValueError('Real recovery execution requires canonical system paths')
    state = manager.user_install.private_directory(Path(reviewed['state']))
    fd = os.open(state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        origin = Path(reviewed['recovery']['journal'])
        if plan(origin, Path(reviewed['root']), Path(reviewed['home']), inspect) != reviewed:
            raise ValueError('Recovery inputs changed; no manager command executed')
        case, journal, record = manager.backup_state(reviewed, state)
        (case / 'original-journal.json').write_bytes(manager.plugin_login.regular(origin))
        (case / 'original-journal.json').chmod(0o600)
        record['steps'] = []
        directory = Path(reviewed['directory'])
        shared = Path(reviewed['shared_pkgconfig'])
        try:
            migration.assert_quiet(reviewed, inspect)
            if (manager.manager_inventory(directory) != reviewed['before']
                    or manager.metadata_state(shared) != reviewed['shared_pkgconfig_before']
                    or migration.verify_headers(reviewed, inspect) != reviewed['headers']
                    or sha(origin, 2 * 1024 * 1024) != reviewed['recovery']['sha256']):
                raise ValueError('Recovery checkpoint changed during backup')
            step = {'command': reviewed['commands'][0], 'status': 'started'}
            record['steps'].append(step)
            manager.user_install.atomic_json(journal, record)
            execute(step['command'])
            migration.assert_quiet(reviewed, inspect)
            after = manager.manager_inventory(directory)
            migration.verify_step(reviewed, 3, reviewed['before'], after, inspect)
            if (manager.metadata_state(shared) != reviewed['shared_pkgconfig_before']
                    or migration.verify_headers(reviewed, inspect) != reviewed['headers']
                    or sha(origin, 2 * 1024 * 1024) != reviewed['recovery']['sha256']):
                raise ValueError('Recovery shared/header/journal evidence changed')
            step.update(status='verified', returncode=0)
            receipt = {'schema_version': 1, 'policy_digest': reviewed['policy_digest'], 'native': reviewed['native'],
                       'library': reviewed['library'], 'library_sha256': after['hyprland-plugins/hyprbars.so']['sha256'],
                       'headers': reviewed['headers'], 'activated': False, 'migration_journal': str(journal)}
            manager.user_install.atomic_json(state / 'hyprpm.json', receipt)
            record.update(status='completed', shared_pkgconfig_after=manager.metadata_state(shared))
            manager.user_install.atomic_json(journal, record)
            resolution = {'schema_version': 1, 'kind': 'omabuntu-hyprpm-recovery-resolution',
                          'original_sha256': reviewed['recovery']['sha256'], 'recovery_journal': str(journal),
                          'recovery_sha256': sha(journal, 2 * 1024 * 1024)}
            manager.user_install.atomic_json(origin.with_name('resolution.json'), resolution)
            if not manager.plugin_login.transaction_complete(origin):
                raise ValueError('Recovery resolution did not verify')
        except BaseException as error:
            record.update(status='manual-review-required', failure=type(error).__name__)
            if record['steps'] and record['steps'][-1]['status'] == 'started':
                record['steps'][-1]['status'] = 'failed-or-unverified'
            manager.user_install.atomic_json(journal, record)
            raise ValueError('Recovery stopped; no restore or retry. Inspect ' + str(case)) from error
        return {'status': 'plugin-migrated-disabled', 'journal': str(journal), 'plugin_loaded': False,
                'configuration_reloaded': False, 'autostart_changed': False, 'activation_required': True}
