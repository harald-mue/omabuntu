"""Reviewed prepared-bundle installs/updates with bar-start rollback.

No packages, sources, config migrations or user preferences are changed here.
All deployment uses the existing manager's control lock. Interruption journals
are retained; unresolved operations block subsequent updates for manual review.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import install as guided
import user_install
import build_plugin
import state_schema


class UpdateError(ValueError):
    pass


RESOLVED = {'completed', 'restored-after-failure', 'aborted-before-switch',
            'recovered-unchanged', 'recovered-to-prestate'}


def contract():
    spec, _ = guided.manifest()
    return {'user_state_schema': 1, 'native_target': dict(spec['target'])}


def validate_contract(meta):
    value = meta.get('update_contract')
    if (not isinstance(value, dict) or set(value) != {'user_state_schema', 'native_target'}
            or type(value.get('user_state_schema')) is not int
            or value['user_state_schema'] < 1
            or not isinstance(value.get('native_target'), dict)
            or set(value['native_target']) != {'ubuntu', 'hyprland', 'qt'}
            or any(not isinstance(v, str) or not v for v in value['native_target'].values())):
        raise UpdateError('Release has no valid update/state contract; prepare a new bundle')
    return value


def unresolved(installation):
    directory = user_install.safe_parents(installation.state / 'updates')
    result = []
    for path in sorted(directory.glob('*/journal.json')):
        record = user_install.read_json(path)
        if not isinstance(record, dict):
            raise UpdateError('Invalid update journal; review private state')
        if record.get('status') not in RESOLVED:
            result.append(str(path))
    return result


def expected_after_switch(pre, plan):
    if plan.get('operation') == 'rollback':
        return plan.get('previous'), plan.get('current')
    target = 'releases/' + plan.get('version', '')
    previous = pre.get('current') if pre.get('current') not in (None, target) else pre.get('previous')
    return target, previous


def launcher_matches(installation, pre, directory):
    launcher = installation.launcher
    if launcher.is_symlink() or type(pre.get('launcher_existed')) is not bool:
        return False
    if not pre['launcher_existed']:
        return not launcher.exists()
    saved = directory / 'launcher'
    if (not launcher.is_file() or saved.is_symlink() or not saved.is_file()
            or not isinstance(pre.get('launcher_sha256'), str)):
        return False
    digest = hashlib.sha256(launcher.read_bytes()).hexdigest()
    return digest == pre['launcher_sha256'] == hashlib.sha256(saved.read_bytes()).hexdigest()


def recover_review(installation):
    """Review one interrupted update. Recovery restores prestate; it never resumes it."""
    found = unresolved(installation)
    if len(found) != 1:
        raise UpdateError('Recovery requires exactly one interrupted update journal')
    record_path = Path(found[0])
    record = user_install.read_json(record_path)
    pre = record.get('prestate')
    plan = record.get('plan')
    if (record.get('schema_version') != 1 or not isinstance(pre, dict) or not isinstance(plan, dict)
            or plan.get('operation') not in ('install', 'update', 'rollback')
            or not isinstance(plan.get('version'), str) or type(plan.get('running')) is not bool):
        raise UpdateError('Interrupted journal is incomplete; no recovery performed')
    current, previous = installation.selected(), installation.selected('previous')
    inner = installation.pending()
    pre_match = current == pre.get('current') and previous == pre.get('previous') and launcher_matches(installation, pre, record_path.parent)
    expected = expected_after_switch(pre, plan)
    switched = (current, previous) == expected
    if inner and not pre_match:
        action = 'restore-inner-then-prestate'
    elif pre_match and not inner:
        action = 'mark-unchanged'
    elif switched and not inner:
        action = 'restore-prestate'
    else:
        action = 'manual'
    running = installation.running()
    return {'schema_version': 1, 'kind': 'omabuntu-update-recovery', 'journal': str(record_path),
            'journal_status': record.get('status'), 'action': action, 'running': running,
            'prestate': {'current': pre.get('current'), 'previous': pre.get('previous'), 'running': plan['running']},
            'selectors': {'current': current, 'previous': previous}, 'inner_pending': bool(inner),
            'starts_by_default': False, 'system_packages_changed': False,
            'blockers': ['Selectors or launcher differ from both prestate and the interrupted switch; review manually'] if action == 'manual' else []}


def recover(installation, reviewed, approval, restart=False):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise UpdateError('Recover as your normal user, not via sudo')
    if guided.digest(reviewed) != approval or reviewed.get('kind') != 'omabuntu-update-recovery' or reviewed.get('blockers'):
        raise UpdateError('Recovery approval differs or needs manual review')
    if restart and (not reviewed['prestate']['running'] or reviewed['action'] == 'mark-unchanged'):
        raise UpdateError('Refusing to start a bar that was not stopped by this interrupted update')
    user_install.private_directory(installation.state)
    fd = os.open(installation.state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fresh = recover_review(installation)
        if fresh != reviewed:
            raise UpdateError('Interrupted update changed; review it again')
        if installation.running() and reviewed['action'] != 'mark-unchanged':
            raise UpdateError('Stop the recorded bar before selector recovery; no forced stop performed')
        locker_absent()
        record_path = Path(reviewed['journal'])
        record = user_install.read_json(record_path)
        if reviewed['action'] == 'restore-inner-then-prestate':
            installation.recover()
        if reviewed['action'] in ('restore-prestate', 'restore-inner-then-prestate'):
            installation.restore(record_path.parent, record['prestate'])
            status = 'recovered-to-prestate'
            restarted = False
            if restart:
                installation.start()
                restarted = True
        else:
            status = 'recovered-unchanged'
            restarted = False
        if (installation.selected(), installation.selected('previous')) != (record['prestate'].get('current'), record['prestate'].get('previous')):
            raise UpdateError('Recovery did not return to the recorded prestate')
        record['status'] = status
        record['recovery'] = {'restarted': restarted, 'resumed_new_release': False}
        user_install.atomic_json(record_path, record)
        return {'status': status, 'journal': str(record_path), 'bar_restarted': restarted,
                'resumed_new_release': False, 'system_packages_changed': False}


def locker_absent():
    try:
        result = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'hyprlock'],
                                capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise UpdateError('Could not check lock process; leaving desktop alone') from error
    if result.returncode != 1:
        raise UpdateError('Lock process present or lookup failed; leaving desktop alone')


def candidate_plugin(bundle):
    try:
        return build_plugin.verify_bundle_plugin(bundle)
    except (OSError, ValueError, build_plugin.builder.BuildError, subprocess.SubprocessError) as error:
        raise UpdateError('Native plugin candidate blocked: ' + str(error)) from error


def review(installation, bundle=None, mode='install', restart=False, allow_legacy=False):
    if mode not in ('install', 'update', 'rollback'):
        raise UpdateError('Unknown release operation')
    installation.require_settled()
    if unresolved(installation):
        raise UpdateError('Interrupted update found; review its private journal before retrying')
    current = installation.selected()
    previous = installation.selected('previous')
    if mode in ('update', 'rollback') and current is None:
        raise UpdateError('No installed release to update or roll back')
    if mode == 'rollback':
        if bundle is not None or previous is None:
            raise UpdateError('Rollback requires a verified previous release and no bundle argument')
        bundle = installation.root / previous
    elif bundle is None:
        raise UpdateError('Prepared release --bundle is required')
    bundle = user_install.safe_parents(Path(bundle).absolute())
    meta = user_install.verify_bundle(bundle)
    incoming = validate_contract(meta)
    native_plugin = candidate_plugin(bundle)
    session_digest = None
    receipt_path = installation.state / 'session-config.json'
    if receipt_path.exists() or receipt_path.is_symlink():
        receipt = user_install.read_json(receipt_path)
        if (not isinstance(receipt, dict) or receipt.get('schema_version') != 1
                or type(receipt.get('helper_contract')) is not int or receipt['helper_contract'] != 1):
            raise UpdateError('Session configuration contract needs manual review')
        required = user_install.SESSION_HELPERS + (user_install.SESSION_LOCK_HELPERS if receipt.get('manual_lock') else ())
        if (any(name not in meta['files'] for name in required)
                or not os.access(bundle / 'runtime/bin/omasnap', os.X_OK)):
            raise UpdateError('Candidate lacks helpers required by the configured session; no switch permitted')
        session_digest = guided.digest(receipt)
    if incoming['native_target'] != contract()['native_target']:
        raise UpdateError('Candidate native target requires a separate session plan; no live switch')
    legacy = False
    installed_schema = None
    if current:
        old = user_install.verify_bundle(installation.root / current, installed=True)
        if 'update_contract' not in old:
            legacy = True
            if not allow_legacy:
                raise UpdateError('Installed state is unversioned; review and explicitly allow legacy state')
        else:
            old_contract = validate_contract(old)
            if old_contract['native_target'] != incoming['native_target']:
                raise UpdateError('Installed native target differs; no live switch permitted')
            installed_schema = old_contract['user_state_schema']
    try:
        schema = state_schema.decision(installed_schema, incoming['user_state_schema'])
    except state_schema.SchemaError as error:
        raise UpdateError(str(error)) from error
    if schema['action'] != 'none' or schema['writes_state']:
        raise UpdateError('User-state migration is not approved for execution')
    destination = installation.root / 'releases' / meta['version']
    if destination.exists() and user_install.verify_bundle(destination) != meta:
        raise UpdateError('Version exists with different contents; use a new version name')
    launcher = installation.launcher
    launcher_state = {'existed': launcher.exists()}
    if launcher.is_symlink() or (launcher.exists() and not launcher.is_file()):
        raise UpdateError('Unsafe launcher')
    if launcher.exists():
        content = launcher.read_bytes()
        if current and content != installation.bootstrap().encode():
            raise UpdateError('Launcher changed outside the manager; leaving it untouched')
        launcher_state.update(sha256=hashlib.sha256(content).hexdigest(), mode=launcher.stat().st_mode & 0o777)
    running = installation.running()
    no_op = current == 'releases/' + meta['version'] and launcher.exists()
    if running and not restart and not no_op:
        raise UpdateError('Bar is running; explicit --restart-bar approval is required')
    return {'schema_version': 1, 'operation': mode, 'bundle': str(bundle),
            'bundle_digest': guided.digest(meta), 'version': meta['version'],
            'current': current, 'previous': previous, 'launcher': launcher_state,
            'running': running, 'restart_bar': restart, 'legacy_state': legacy,
            'allow_legacy_state': allow_legacy, 'no_op': no_op,
            'locations': {'root': str(installation.root), 'state': str(installation.state),
                          'launcher': str(installation.launcher)},
            'user_state_schema': incoming['user_state_schema'], 'schema_decision': schema,
            'session_config_digest': session_digest,
            'native_plugin': native_plugin, 'scope': 'local-application-release-only'}


def approve_digest(plan):
    return guided.digest(plan)


def stage(installation, bundle):
    """Copy and verify a complete immutable candidate before stopping the bar."""
    meta = user_install.verify_bundle(bundle)
    user_install.private_directory(installation.root)
    releases = user_install.private_directory(installation.root / 'releases')
    target = releases / meta['version']
    if target.exists():
        if user_install.verify_bundle(target) != meta:
            raise UpdateError('Candidate version collision')
        return target
    temporary = releases / ('.candidate-' + user_install.stamp())
    try:
        shutil.copytree(bundle, temporary, symlinks=True)
        if user_install.verify_bundle(temporary) != meta:
            raise UpdateError('Staged candidate differs')
        temporary.rename(target)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)  # Only this call's unselected temporary tree.
        raise
    return target


def preflight(bundle):
    report, path = guided.preflight(bundle)
    if report['status'] != 'passed':
        raise UpdateError('Runtime preflight blocked deployment; inspect ' + str(path))
    return report


def apply(installation, plan, approval, check=None, check_locker=None):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise UpdateError('Run as your normal user, not via sudo')
    if approve_digest(plan) != approval:
        raise UpdateError('Approval does not match the reviewed release plan')
    user_install.private_directory(installation.state)
    fd = os.open(installation.state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fresh = review(installation, None if plan['operation'] == 'rollback' else plan['bundle'],
                       plan['operation'], plan['restart_bar'], plan['allow_legacy_state'])
        if fresh != plan:
            raise UpdateError('Release or desktop state changed; review a new plan')
        if plan['no_op']:
            return {'status': 'already-installed', 'version': plan['version'], 'bar_restarted': False}
        probe = preflight if check is None else check
        report = probe(Path(plan['bundle']))
        if report.get('status') != 'passed':
            raise UpdateError('Runtime preflight did not pass')
        # Repeat after potentially long preflight. No mutation has happened yet
        # except creation of the private control lock/state directory.
        fresh = review(installation, None if plan['operation'] == 'rollback' else plan['bundle'],
                       plan['operation'], plan['restart_bar'], plan['allow_legacy_state'])
        if fresh != plan:
            raise UpdateError('Release or desktop changed during preflight')
        (locker_absent if check_locker is None else check_locker)()
        parent = user_install.private_directory(installation.state / 'updates')
        directory = user_install.private_directory(parent / user_install.stamp())
        pre = {'operation': plan['operation'], 'current': plan['current'], 'previous': plan['previous'],
               'launcher_existed': plan['launcher']['existed'],
               'launcher_mode': plan['launcher'].get('mode'),
               'launcher_sha256': plan['launcher'].get('sha256')}
        if pre['launcher_existed']:
            data = installation.launcher.read_bytes()
            if hashlib.sha256(data).hexdigest() != pre['launcher_sha256']:
                raise UpdateError('Launcher changed before backup')
            (directory / 'launcher').write_bytes(data)
            (directory / 'launcher').chmod(0o600)
        journal = {'schema_version': 1, 'status': 'preparing', 'plan': plan, 'prestate': pre}
        record = directory / 'journal.json'
        user_install.atomic_json(record, journal)
        stopped = False
        switched = False
        try:
            candidate = stage(installation, Path(plan['bundle']))
            if guided.digest(user_install.verify_bundle(candidate)) != plan['bundle_digest']:
                raise UpdateError('Candidate changed after staging')
            if candidate_plugin(candidate) != plan['native_plugin']:
                raise UpdateError('Native plugin changed during staging; no stop performed')
            if (installation.selected() != pre['current']
                    or installation.selected('previous') != pre['previous']
                    or installation.running() != plan['running']):
                raise UpdateError('Selectors or bar changed during staging; no stop performed')
            if pre['launcher_existed']:
                if (installation.launcher.is_symlink()
                        or hashlib.sha256(installation.launcher.read_bytes()).hexdigest() != pre['launcher_sha256']):
                    raise UpdateError('Launcher changed during staging; no stop performed')
            elif installation.launcher.exists() or installation.launcher.is_symlink():
                raise UpdateError('Launcher appeared during staging; no stop performed')
            (locker_absent if check_locker is None else check_locker)()
            journal['status'] = 'stopping'
            user_install.atomic_json(record, journal)
            if plan['running']:
                installation.stop()
            stopped = True
            journal['status'] = 'switching'
            user_install.atomic_json(record, journal)
            # The inner manager journals its own selector switch as before.
            if plan['operation'] == 'rollback':
                installation.rollback()
            else:
                installation.install(candidate)
            switched = True
            journal['status'] = 'starting' if plan['restart_bar'] else 'switched'
            user_install.atomic_json(record, journal)
            if plan['restart_bar']:
                installation.start()  # Bounded readiness, no component lifetime limit.
            journal['status'] = 'completed'
            user_install.atomic_json(record, journal)
            status = ('installed-and-started' if plan['operation'] == 'install' else 'updated-and-started') if plan['restart_bar'] else 'installed-not-started'
            return {'status': status,
                    'version': plan['version'], 'bar_restarted': plan['restart_bar'],
                    'journal': str(record), 'system_packages_changed': False}
        except BaseException as error:
            try:
                if stopped:
                    if installation.running():
                        installation.stop()
                    # Manager switch failures normally restore themselves. Never
                    # overwrite unrelated pending manager state or external edits.
                    installation.require_settled()
                    if installation.selected() not in (pre['current'], 'releases/' + plan['version']):
                        raise UpdateError('Selectors changed outside this operation; manual recovery required')
                    installation.restore(directory, pre)
                    if plan['running']:
                        installation.start()
                    journal['status'] = 'restored-after-failure'
                elif not switched:
                    journal['status'] = 'aborted-before-switch'
                journal['failure'] = type(error).__name__
                user_install.atomic_json(record, journal)
            except BaseException as recovery:
                journal.update(status='recovery-required', failure=type(error).__name__,
                               recovery_failure=type(recovery).__name__)
                user_install.atomic_json(record, journal)
                raise UpdateError('Update failed and needs manual recovery; inspect ' + str(record)) from error
            raise UpdateError('Update failed; previous selection restored or never changed. Inspect ' + str(record)) from error
