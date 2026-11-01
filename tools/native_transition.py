"""Read-only evidence for one explicit application-contract handoff.

Never upgrade packages/compositor, load plugins, convert profiles or edit receipts.
A running 0.57 compositor and verified manager state must already exist.
"""
import hashlib
import json
import os
from pathlib import Path
import pwd
import stat
import tomllib

import plugin_manager as manager
import plugin_login
import user_install

FROM = {'ubuntu': '26.04', 'hyprland': '0.56.2', 'qt': '6.10.2'}
TO = {'ubuntu': '26.04', 'hyprland': '0.57.0', 'qt': '6.10.2'}


def profile_state(config):
    """Fingerprint the profile tree without following links or adopting it.

This is a preservation/drift snapshot, not arbitrary Lua dependency evaluation.
"""
    directory = config / 'hypr'
    user_install.safe_parents(directory)
    if not directory.exists():
        return {'existed': False}
    if not directory.is_dir():
        raise ValueError('Profile path is not a directory')
    files = {}
    total = 0
    for path in sorted(directory.rglob('*')):
        if len(files) >= 512:
            raise ValueError('Profile snapshot exceeds file limit')
        info = path.lstat()
        row = {'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid}
        if stat.S_ISLNK(info.st_mode):
            row['link'] = os.readlink(path)
        elif stat.S_ISREG(info.st_mode):
            total += info.st_size
            if total > 8 * 1024 * 1024:
                raise ValueError('Profile snapshot exceeds byte limit')
            row['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif stat.S_ISDIR(info.st_mode):
            row['directory'] = True
        else:
            raise ValueError('Special profile file requires separate review')
        files[path.relative_to(directory).as_posix()] = row
    info = directory.stat()
    return {'existed': True, 'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid,
            'gid': info.st_gid, 'files': files}


def manager_ready(policy, state, *, inspect=manager.probe, directory=None,
                  allow_unloaded=False, active_transaction=None):
    """Validate reusable manager state without reconciliation or activation."""
    state = Path(state)
    native = manager.build_hyprbars.installed_version()
    running = json.loads(inspect(['hyprctl', '-j', 'version']))
    target = policy['targets'].get('0.57.0', {})
    if (target.get('apply_reviewed') is not True or native.get('version') != '0.57.0'
            or native.get('commit') != target.get('hyprland_commit') or native.get('dirty') is not False
            or not native.get('abiHash') or running.get('commit') != native.get('commit')
            or running.get('abiHash') != native['abiHash']
            or not isinstance(running.get('flags', []), (list, str)) or 'dirty' in running.get('flags', [])):
        raise ValueError('Install and enter the reviewed clean matching 0.57.0 session separately first')
    for parent, allowed in (('plugin-transactions', ('completed',)),
                            ('session-transactions', ('completed', 'restored-after-failure')),
                            ('activation-transactions', ('completed', 'restored-after-failure'))):
        user_install.safe_parents(state / parent)
        for journal in (state / parent).glob('*/transaction.json'):
            if (parent == 'plugin-transactions' and active_transaction is not None
                    and str(journal) == active_transaction.get('path')):
                record = plugin_login.read_json(journal)
                if (record.get('status') not in ('prepared', 'running')
                        or record.get('backup_verified') is not True
                        or record.get('plan', {}).get('kind') != 'omabuntu-hyprbars-repair'
                        or manager.guided.digest(record['plan']) != active_transaction.get('digest')):
                    raise ValueError('Active repair transaction does not match its approved verified backup')
                continue
            if parent == 'plugin-transactions':
                complete = plugin_login.transaction_complete(journal)
            else:
                complete = plugin_login.read_json(journal).get('status') in allowed
            if not complete:
                raise ValueError('Unresolved manager/session operation blocks native handoff')
    receipt_path = state / 'hyprpm.json'
    if not receipt_path.exists():
        raise ValueError('Prepare/verify the current manager build separately before native handoff')
    receipt = plugin_login.read_json(receipt_path)
    directory = (Path('/var/cache/hyprpm') / pwd.getpwuid(os.getuid()).pw_name
                 if directory is None else Path(directory))
    library = directory / 'hyprland-plugins/hyprbars.so'
    if (receipt.get('policy_digest') != manager.guided.digest(policy) or receipt.get('native') != native
            or type(receipt.get('activated')) is not bool or receipt.get('library') != str(library)
            or hashlib.sha256(plugin_login.regular(library, 64 * 1024 * 1024)).hexdigest() != receipt.get('library_sha256')):
        raise ValueError('Prepare/verify the exact current manager build separately before native handoff')
    global_state = tomllib.loads(plugin_login.regular(directory / 'state.toml').decode())
    if global_state.get('state', {}).get('hash') != native['abiHash']:
        raise ValueError('Manager global ABI does not match the new compositor')
    headers = plugin_login.header_state(directory, native, inspect)
    if receipt.get('headers') is not None and receipt['headers'] != headers:
        raise ValueError('Manager header fingerprints changed')
    repositories = sorted(directory.glob('*/state.toml'))
    if repositories != [directory / 'hyprland-plugins/state.toml']:
        raise ValueError('Foreign manager repository prevents native handoff')
    repo = tomllib.loads(plugin_login.regular(repositories[0]).decode())
    metadata = repo.get('repository', {})
    if (metadata.get('name') != 'hyprland-plugins' or metadata.get('url') != policy['repository']
            or metadata.get('rev') != target['plugin_commit'] or metadata.get('hash') != target['plugin_commit']
            or repo.get('hyprbars', {}).get('filename') != 'hyprbars.so'
            or repo['hyprbars'].get('failed') is not False):
        raise ValueError('Manager repository/build is not the exact reviewed 0.57 pin')
    for name, row in repo.items():
        if name == 'repository':
            continue
        expected = receipt['activated'] if name == 'hyprbars' else False
        if not isinstance(row, dict) or type(row.get('enabled')) is not bool or row['enabled'] != expected:
            raise ValueError('Manager enablement differs or includes foreign plugins')
    loaded = manager.loaded_plugins(inspect)
    missing_enabled = allow_unloaded and receipt['activated'] is True and not loaded
    if (any(row.get('name') != 'hyprbars' for row in loaded)
            or (len(loaded) != int(receipt['activated']) and not missing_enabled)):
        raise ValueError('Live plugin list and explicit manager activation differ')
    return {'native': native, 'running': running,
            'manager_receipt': plugin_login.fingerprint(receipt_path, 2 * 1024 * 1024),
            'manager_inventory': manager.manager_inventory(directory), 'headers': headers, 'loaded': loaded}


def evidence(installation, bundle, *, inspect=manager.probe, directory=None, config=None):
    current = installation.selected()
    if current is None:
        raise ValueError('Native handoff requires an existing versioned application')
    old = user_install.verify_bundle(installation.root / current, installed=True)
    new = user_install.verify_bundle(bundle)
    before, after = old.get('update_contract', {}), new.get('update_contract', {})
    if (before.get('native_target') != FROM or after.get('native_target') != TO
            or before.get('user_state_schema') != 1 or after.get('user_state_schema') != 1):
        raise ValueError('Only the explicit versioned 0.56.2 to 0.57.0 application handoff is supported')
    policy = manager.bundle_policy(bundle)
    if policy is None:
        raise ValueError('Native handoff requires a manager-policy candidate, not a bundled plugin')
    activation = installation.state / 'session-activation.json'
    if activation.exists() or activation.is_symlink():
        raise ValueError('Existing next-login activation requires a separate owned-loader handoff')
    ready = manager_ready(policy, installation.state, inspect=inspect, directory=directory)
    config = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') if config is None else Path(config)
    if not config.is_absolute():
        raise ValueError('Profile root must be absolute')
    session = installation.state / 'session-config.json'
    if session.exists() or session.is_symlink():
        # Owned profiles need to already match the current reviewed renderer.
        # No automatic profile conversion or implicit adoption is performed.
        import session_config
        reviewed = session_config.plan()
        if (reviewed['blockers'] or reviewed['changes'] or reviewed['selected'] != current
                or reviewed['paths']['receipt'] != str(session)
                or reviewed['release_digest'] != manager.guided.digest(old)):
            raise ValueError('Owned session profile needs a separately approved configuration handoff')
    return {'kind': 'omabuntu-native-application-handoff', 'from': before, 'to': after,
            'old_bundle_digest': manager.guided.digest(old), **ready,
            'profile': profile_state(config), 'profile_root': str(config),
            'owned_session': plugin_login.fingerprint(session) if session.exists() else None,
            'profile_changed': False, 'system_packages_changed': False, 'plugins_changed': False}
