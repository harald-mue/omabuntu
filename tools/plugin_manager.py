"""Explicit pinned hyprpm preparation and separate live activation.

Planning is read-only. Applying can request sudo through hyprpm; never run this
module as root. Existing/unrelated manager state is not silently adopted.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import tarfile
import time
import tomllib

import build_hyprbars
import install as guided
import omabuntu_hyprpm
import plugin_login
import user_install

ROOT = Path(__file__).resolve().parents[1]


def policy(root=ROOT):
    data = user_install.read_json(root / 'upstream/hyprpm.json')
    if (not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1
            or data.get('manager') != 'hyprpm' or data.get('plugin') != 'hyprbars'
            or data.get('repository') != 'https://github.com/hyprwm/hyprland-plugins'
            or not isinstance(data.get('targets'), dict) or not data['targets']):
        raise ValueError('Invalid hyprpm source policy')
    for version, row in data['targets'].items():
        if (not isinstance(version, str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version)
                or not isinstance(row, dict) or type(row.get('apply_reviewed')) is not bool
                or any(not isinstance(row.get(key), str) or not re.fullmatch('[a-f0-9]{40}', row[key])
                       for key in ('hyprland_commit', 'plugin_commit'))):
            raise ValueError('Invalid hyprpm target pin')
    return data


def bundle_policy(bundle):
    path = bundle / 'native/hyprpm.json'
    user_install.safe_parents(path.parent)
    if path.is_symlink():
        raise ValueError('Linked bundle management policy')
    if not path.exists():
        return None
    if (bundle / 'native/hyprbars.so').exists() or (bundle / 'native/hyprbars.json').exists():
        raise ValueError('Bundle cannot mix hyprpm and native plugin ownership')
    data = user_install.read_json(path)
    if data != policy():
        raise ValueError('Bundle hyprpm policy differs from the reviewed installer')
    return data


def manager_inventory(directory):
    user_install.safe_parents(directory)
    result = {}
    total = 0
    start = time.monotonic()
    if not directory.exists():
        return result
    for path in sorted(directory.rglob('*')):
        if time.monotonic() - start > 30 or len(result) > 50000:
            raise ValueError('Manager inventory exceeded limits')
        name = path.relative_to(directory).as_posix()
        if path.is_symlink():
            raise ValueError('Manager symlinks require manual review: ' + name)
        info = path.stat()
        ownership = {'uid': info.st_uid, 'gid': info.st_gid}
        if path.is_file():
            size = info.st_size
            total += size
            if total > 512 * 1024 * 1024:
                raise ValueError('Manager inventory exceeds backup limit')
            result[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'mode': info.st_mode & 0o7777, **ownership}
        elif path.is_dir():
            result[name] = {'directory': True, 'mode': info.st_mode & 0o7777, **ownership}
        else:
            raise ValueError('Special file in manager state')
    return result


def metadata_state(path):
    user_install.safe_parents(path.parent)
    if path.is_symlink():
        raise ValueError('Linked system pkg-config metadata requires manual review')
    if not path.exists():
        return {'existed': False}
    info = path.stat()
    if not path.is_file() or info.st_size > 65536:
        raise ValueError('Unsafe system pkg-config metadata')
    return {'existed': True, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'mode': info.st_mode & 0o7777, 'uid': info.st_uid, 'gid': info.st_gid}


def directory_state(path):
    user_install.safe_parents(path)
    if not path.exists():
        return {'existed': False}
    info = path.stat()
    if not path.is_dir():
        raise ValueError('Manager cache parent is not a directory')
    return {'existed': True, 'mode': info.st_mode & 0o7777, 'uid': info.st_uid, 'gid': info.st_gid}


def probe(argv):
    return subprocess.run(argv, capture_output=True, text=True, check=True, timeout=15).stdout


def loaded_plugins(inspect=probe):
    data = json.loads(inspect(['hyprctl', '-j', 'plugin', 'list']))
    if not isinstance(data, list) or any(not isinstance(p, dict) for p in data):
        raise ValueError('Invalid running plugin list')
    return data


def plan(root=ROOT, home=None, action='prepare', native=None, running=None,
         directory=None, inspect=probe, shared_pkgconfig=Path('/usr/share/pkgconfig/hyprland.pc')):
    if action not in ('prepare', 'activate'):
        raise ValueError('Unknown plugin operation')
    home = Path.home() if home is None else Path(home)
    state = Path(os.environ.get('XDG_STATE_HOME') or home / '.local/state') / 'omabuntu'
    if not state.is_absolute():
        raise ValueError('XDG state path must be absolute')
    directory = Path('/var/cache/hyprpm') / pwd.getpwuid(os.getuid()).pw_name if directory is None else Path(directory)
    source = policy(root)
    native = build_hyprbars.installed_version() if native is None else native
    target = source['targets'].get(native.get('version'))
    blockers = []
    if (not target or not target['apply_reviewed'] or native.get('dirty') is not False
            or native.get('commit') != target['hyprland_commit']):
        blockers.append('Hyprland version/commit is not approved for hyprpm apply')
    required = ['hyprpm', 'hyprctl']
    if action == 'prepare':
        required.extend(('cmake', 'cpio', 'hyprwayland-scanner', 'pkg-config', 'g++', 'gcc', 'git', 'ninja', 'make'))
    for command in required:
        if not shutil.which(command):
            blockers.append('Missing plugin tool: ' + command)
    if action == 'prepare' and not (omabuntu_hyprpm.LUA_INCLUDE / 'lua.h').is_file():
        blockers.append('Missing Ubuntu Lua headers; review --packages --plugin-build-only')
    try:
        running = json.loads(inspect(['hyprctl', '-j', 'version'])) if running is None else running
        if (not isinstance(running, dict) or running.get('commit') != native.get('commit')
                or not isinstance(native.get('abiHash'), str) or not native['abiHash']
                or running.get('abiHash') != native['abiHash']
                or not isinstance(running.get('flags', []), (list, str))
                or 'dirty' in running.get('flags', [])):
            blockers.append('Installed and running Hyprland differ; no manager mutation')
        loaded = loaded_plugins(inspect)
        if loaded:
            blockers.append('Loaded compositor plugins could be unloaded by hyprpm; use a separately approved plugin-free session')
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        blockers.append('Running compositor probe failed: ' + type(error).__name__)
    before = manager_inventory(directory)
    shared_pkgconfig = Path(shared_pkgconfig)
    shared_before = metadata_state(shared_pkgconfig)
    cache_parent_before = directory_state(directory.parent)
    user_install.safe_parents(state)
    receipt_path = state / 'hyprpm.json'
    if receipt_path.is_symlink():
        raise ValueError('Unsafe plugin receipt')
    receipt = user_install.read_json(receipt_path) if receipt_path.exists() else None
    repositories = []
    enabled = []
    ownership_blockers = []
    for path in sorted(directory.glob('*/state.toml')):
        data = tomllib.loads(path.read_text())
        repository = data.get('repository', {})
        if not isinstance(repository, dict):
            raise ValueError('Invalid manager repository record')
        if (path.parent.name != 'hyprland-plugins' or repository.get('name') != 'hyprland-plugins'
                or repository.get('url') != source['repository']
                or not target or repository.get('rev') != target['plugin_commit']
                or repository.get('hash') != target['plugin_commit']):
            ownership_blockers.append('Unmanaged or differently pinned hyprpm repository requires manual migration')
        hyprbars = data.get('hyprbars', {})
        if not isinstance(hyprbars, dict):
            raise ValueError('Invalid manager hyprbars record')
        if hyprbars.get('filename') != 'hyprbars.so':
            ownership_blockers.append('Manager hyprbars filename requires manual review')
        repositories.append(path.parent.name)
        for name, item in data.items():
            if name == 'repository':
                continue
            if (not isinstance(item, dict) or type(item.get('enabled')) is not bool
                    or type(item.get('failed')) is not bool):
                ownership_blockers.append('Malformed manager plugin record requires manual review')
                continue
            if item['enabled']:
                enabled.append(name)
            if action == 'activate' and item['failed']:
                ownership_blockers.append('Failed manager plugin build must be repaired before activation')
    if enabled:
        ownership_blockers.append('Enabled manager plugins could be loaded by update/enable; automatic reconciliation refused')
    if repositories and (not isinstance(receipt, dict) or receipt.get('policy_digest') != guided.digest(source)):
        ownership_blockers.append('Existing manager repository has no matching Omabuntu receipt; no implicit adoption')
    library = directory / 'hyprland-plugins/hyprbars.so'
    library_digest = before.get('hyprland-plugins/hyprbars.so', {}).get('sha256')
    if action == 'activate':
        if (not isinstance(receipt, dict) or receipt.get('native') != native
                or receipt.get('library_sha256') != library_digest or not library_digest):
            blockers.append('Prepare and verify the manager plugin before live activation')
    headers_before = None
    if action == 'activate':
        try:
            headers_before = checked_headers(directory, native, inspect)
            if isinstance(receipt, dict) and receipt.get('headers') is not None and headers_before != receipt['headers']:
                blockers.append('Manager header inputs changed; preparation requires review')
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            blockers.append('Manager headers could not be verified: ' + str(error))
    pending = state / 'plugin-transactions'
    if pending.exists():
        user_install.safe_parents(pending)
        for journal in pending.glob('*/transaction.json'):
            user_install.safe_parents(journal.parent)
            record = user_install.read_json(journal)
            if not isinstance(record, dict) or not plugin_login.transaction_complete(journal):
                blockers.append('Interrupted plugin operation requires manual review')
    commands = ([['hyprpm', 'update'], ['hyprpm', 'add', source['repository'], target['plugin_commit']]]
                if target and not repositories else [['hyprpm', 'update']])
    if action == 'activate':
        commands = [['hyprpm', 'enable', 'hyprbars']]
    prerequisite_blockers = list(blockers)
    blockers.extend(ownership_blockers)
    return {'schema_version': 1, 'kind': 'omabuntu-hyprpm', 'action': action,
            'root': str(root), 'home': str(home), 'state': str(state), 'directory': str(directory),
            'policy_digest': guided.digest(source), 'native': native, 'running': running,
            'shared_pkgconfig': str(shared_pkgconfig), 'shared_pkgconfig_before': shared_before,
            'cache_parent_before': cache_parent_before, 'directory_before': directory_state(directory),
            'before': before, 'directory_existed': directory.exists(),
            'directory_mode': directory.stat().st_mode & 0o7777 if directory.exists() else None,
            'receipt_before': receipt, 'commands': commands, 'headers_before': headers_before,
            'library': str(library), 'blockers': blockers, 'prerequisite_blockers': prerequisite_blockers,
            'ownership_blockers': ownership_blockers, 'loads_plugin': action == 'activate',
            'may_request_sudo': True, 'status': 'blocked' if blockers else 'review-required'}


def backup_state(reviewed, state):
    """Verify private backups against the reviewed prestate before mutation."""
    case = user_install.private_directory(state / 'plugin-transactions' / user_install.stamp())
    journal = case / 'transaction.json'
    record = {'status': 'prepared', 'plan': reviewed, 'automatic_restore': False,
              'backup_verified': False}
    user_install.atomic_json(journal, record)
    try:
        archive = case / 'manager-before.tar'
        with tarfile.open(archive, 'w') as backup:
            for name in reviewed['before']:
                backup.add(Path(reviewed['directory']) / name, arcname=name, recursive=False)
        archive.chmod(0o600)
        with tarfile.open(archive, 'r') as backup:
            members = backup.getmembers()
            if len(members) != len(reviewed['before']):
                raise ValueError('Manager backup entry count differs')
            seen = set()
            for member in members:
                name = member.name.rstrip('/')
                expected = reviewed['before'].get(name)
                if (expected is None or name in seen or member.uid != expected['uid']
                        or member.gid != expected['gid'] or member.mode & 0o7777 != expected['mode']):
                    raise ValueError('Manager backup metadata differs')
                seen.add(name)
                if expected.get('directory'):
                    if not member.isdir():
                        raise ValueError('Manager backup directory differs')
                else:
                    if not member.isreg():
                        raise ValueError('Manager backup file is not regular')
                    with backup.extractfile(member) as stream:
                        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected['sha256']:
                            raise ValueError('Manager backup bytes differ')
        receipt_path = state / 'hyprpm.json'
        receipt = user_install.read_json(receipt_path) if receipt_path.exists() else None
        if receipt_path.is_symlink() or receipt != reviewed['receipt_before']:
            raise ValueError('Plugin receipt changed during backup')
        if receipt_path.exists():
            (case / 'receipt-before.json').write_bytes(receipt_path.read_bytes())
            (case / 'receipt-before.json').chmod(0o600)
        shared = Path(reviewed['shared_pkgconfig'])
        if metadata_state(shared) != reviewed['shared_pkgconfig_before']:
            raise ValueError('System pkg-config metadata changed during backup')
        if reviewed['shared_pkgconfig_before']['existed']:
            data = shared.read_bytes()
            if hashlib.sha256(data).hexdigest() != reviewed['shared_pkgconfig_before']['sha256']:
                raise ValueError('System pkg-config backup bytes differ')
            (case / 'system-hyprland.pc.before').write_bytes(data)
            (case / 'system-hyprland.pc.before').chmod(0o600)
        with archive.open('rb') as stream:
            record['backup_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        record['backup_verified'] = True
        user_install.atomic_json(journal, record)
    except BaseException as error:
        record.update(status='manual-review-required', failure=type(error).__name__)
        user_install.atomic_json(journal, record)
        raise ValueError('Plugin backup failed; inspect ' + str(case)) from error
    return case, journal, record


def checked_headers(directory, native, inspect=probe):
    global_state = tomllib.loads(plugin_login.regular(directory / 'state.toml', 65536).decode())
    if global_state.get('state', {}).get('hash') != native.get('abiHash'):
        raise ValueError('Manager header/global ABI differs from the installed compositor')
    return plugin_login.header_state(directory, native, inspect)


def checked_repository(directory, source, target, enabled=False):
    repositories = sorted(directory.glob('*/state.toml'))
    path = directory / 'hyprland-plugins/state.toml'
    if repositories != [path]:
        raise ValueError('Unexpected repository after manager operation')
    data = tomllib.loads(plugin_login.regular(path, 65536).decode())
    row = data.get('repository', {})
    if (row.get('rev') != target['plugin_commit'] or row.get('hash') != target['plugin_commit']
            or row.get('url') != source['repository'] or row.get('name') != 'hyprland-plugins'
            or data.get('hyprbars', {}).get('filename') != 'hyprbars.so'):
        raise ValueError('Manager output has no successful pinned hyprbars build')
    for name, item in data.items():
        if name == 'repository':
            continue
        expected = enabled if name == 'hyprbars' else False
        if (not isinstance(item, dict) or item.get('failed') is not False
                or type(item.get('enabled')) is not bool or item['enabled'] != expected):
            raise ValueError('Manager plugin output failed, enabled unexpectedly or malformed')
    return data


def execute(argv):
    # Authentication/builds are untimed; only the update child loses its socket.
    environment = omabuntu_hyprpm.build_environment(os.environ)
    if argv == ['hyprpm', 'update']:
        environment.pop('HYPRLAND_INSTANCE_SIGNATURE', None)
    subprocess.run(['/usr/bin/hyprpm', *argv[1:]], env=environment, check=True)


DEFAULT_EXECUTE = execute


def apply(reviewed, approval, execute=execute, inspect=probe):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Run hyprpm as the ordinary user, never through sudo')
    if guided.digest(reviewed) != approval or reviewed.get('blockers'):
        raise ValueError('Plugin plan is blocked or approval differs')
    root, home, directory = (Path(reviewed[key]) for key in ('root', 'home', 'directory'))
    if execute is DEFAULT_EXECUTE:
        expected = Path('/var/cache/hyprpm') / pwd.getpwuid(os.getuid()).pw_name
        if directory != expected or Path(reviewed['shared_pkgconfig']) != Path('/usr/share/pkgconfig/hyprland.pc'):
            raise ValueError('Real manager execution requires canonical system paths')
    state = user_install.private_directory(Path(reviewed['state']))
    fd = os.open(state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fresh = plan(root, home, reviewed['action'], directory=directory, inspect=inspect,
                     shared_pkgconfig=Path(reviewed['shared_pkgconfig']))
        if fresh != reviewed:
            raise ValueError('Manager/native/receipt state changed; review again')
        case, journal, record = backup_state(reviewed, state)
        shared = Path(reviewed['shared_pkgconfig'])
        try:
            if (manager_inventory(directory) != reviewed['before']
                    or metadata_state(shared) != reviewed['shared_pkgconfig_before']
                    or directory_state(directory.parent) != reviewed['cache_parent_before']
                    or directory_state(directory) != reviewed['directory_before']):
                raise ValueError('Manager changed during backup')
            checkpoint = reviewed['before']
            shared_checkpoint = reviewed['shared_pkgconfig_before']
            for command in reviewed['commands']:
                if (manager_inventory(directory) != checkpoint or metadata_state(shared) != shared_checkpoint
                        or guided.digest(policy(root)) != reviewed['policy_digest']):
                    raise ValueError('Manager/policy/system metadata changed between commands')
                if loaded_plugins(inspect):
                    raise ValueError('A compositor plugin loaded after review; manager reconciliation refused')
                step = {'command': command, 'status': 'started', 'returncode': None}
                record.setdefault('steps', []).append(step)
                user_install.atomic_json(journal, record)
                returncode = 0
                try:
                    execute(command)
                except subprocess.CalledProcessError as error:
                    if command != ['hyprpm', 'update'] or error.returncode != 1:
                        raise
                    returncode = 1  # Prove isolated-update convergence below, never ignore arbitrary failure.
                if (build_hyprbars.installed_version() != reviewed['native']
                        or json.loads(inspect(['hyprctl', '-j', 'version'])) != reviewed['running']):
                    raise ValueError('Compositor identity changed during manager operation')
                if reviewed['action'] == 'prepare':
                    if loaded_plugins(inspect):
                        raise ValueError('Plugin appeared during isolated preparation; no further commands')
                    checked_headers(directory, reviewed['native'], inspect)
                    if (directory / 'hyprland-plugins/state.toml').exists():
                        checked_repository(directory, policy(root), policy(root)['targets'][reviewed['native']['version']])
                    elif command != ['hyprpm', 'update'] or any(directory.glob('*/state.toml')):
                        raise ValueError('Unexpected repository after isolated header update')
                after_shared = metadata_state(shared)
                if command != ['hyprpm', 'update'] and after_shared != shared_checkpoint:
                    raise ValueError('System metadata changed outside header refresh')
                if guided.digest(policy(root)) != reviewed['policy_digest']:
                    raise ValueError('Manager policy changed during operation')
                current_receipt = user_install.read_json(state / 'hyprpm.json') if (state / 'hyprpm.json').exists() else None
                if (state / 'hyprpm.json').is_symlink() or current_receipt != reviewed['receipt_before']:
                    raise ValueError('Ownership receipt changed during operation')
                checkpoint, shared_checkpoint = manager_inventory(directory), after_shared
                step.update(status='verified', returncode=returncode)
                user_install.atomic_json(journal, record)
            if build_hyprbars.installed_version() != reviewed['native']:
                raise ValueError('Installed Hyprland changed during plugin operation')
            running = json.loads(inspect(['hyprctl', '-j', 'version']))
            if running != reviewed['running']:
                raise ValueError('Running Hyprland changed during plugin operation')
            data = tomllib.loads((directory / 'hyprland-plugins/state.toml').read_text())
            source = policy(root)
            target = source['targets'][reviewed['native']['version']]
            if (data.get('repository', {}).get('rev') != target['plugin_commit']
                    or data.get('repository', {}).get('hash') != target['plugin_commit']
                    or data.get('repository', {}).get('url') != source['repository']
                    or data.get('repository', {}).get('name') != 'hyprland-plugins'
                    or data.get('hyprbars', {}).get('filename') != 'hyprbars.so'
                    or data.get('hyprbars', {}).get('failed') is not False):
                raise ValueError('Manager output has no successful pinned hyprbars build')
            library = Path(reviewed['library'])
            user_install.safe_parents(library.parent)
            if library.is_symlink() or not library.is_file():
                raise ValueError('Missing regular manager-built plugin library')
            if reviewed['action'] == 'prepare' and any(
                    item.get('enabled') for name, item in data.items()
                    if name != 'repository' and isinstance(item, dict)):
                raise ValueError('Preparation unexpectedly enabled a plugin')
            if reviewed['action'] == 'prepare' and loaded_plugins(inspect):
                raise ValueError('A plugin was loaded during preparation; manual review required')
            if reviewed['action'] == 'activate' and not any(p.get('name') == 'hyprbars' for p in loaded_plugins(inspect)):
                raise ValueError('hyprpm returned but hyprbars is not reported loaded')
            receipt = {'schema_version': 1, 'policy_digest': reviewed['policy_digest'],
                       'native': reviewed['native'], 'library': str(library),
                       'library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
                       'activated': reviewed['action'] == 'activate'}
            if manager_inventory(directory) != checkpoint or metadata_state(shared) != shared_checkpoint:
                raise ValueError('Manager/system metadata changed before receipt creation')
            receipt['headers'] = checked_headers(directory, reviewed['native'], inspect)
            checked_repository(directory, source, target, enabled=reviewed['action'] == 'activate')
            if reviewed['action'] == 'activate' and receipt['headers'] != reviewed['headers_before']:
                raise ValueError('Manager header inputs changed during activation')
            user_install.atomic_json(state / 'hyprpm.json', receipt)
            record['shared_pkgconfig_after'] = metadata_state(shared)
            record['status'] = 'completed'
        except BaseException as error:
            record.update(status='manual-review-required', failure=type(error).__name__)
            if record.get('steps') and record['steps'][-1]['status'] == 'started':
                record['steps'][-1]['status'] = 'failed-or-unverified'
                if isinstance(error, subprocess.CalledProcessError):
                    record['steps'][-1]['returncode'] = error.returncode
            try:
                record['shared_pkgconfig_after'] = metadata_state(shared)
            except (OSError, ValueError):
                record['shared_pkgconfig_after'] = {'status': 'unreadable-requires-review'}
            user_install.atomic_json(journal, record)
            raise ValueError('Plugin operation failed; manager backup and journal: ' + str(case)) from error
        user_install.atomic_json(journal, record)
        return {'status': 'plugin-loaded' if receipt['activated'] else 'plugin-prepared',
                'journal': str(journal), 'plugin_loaded': receipt['activated'],
                'configuration_reloaded': False, 'autostart_changed': False}
