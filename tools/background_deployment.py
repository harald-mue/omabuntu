#!/usr/bin/env python3
"""Scoped background overlay upgrade; preserve the exclusive notification role.

No package/service/wallpaper activation. Explicit --apply is required. Recovery
regrants the prior shell, never starts SwayNC or removes its existing fence.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import stat

import notification_admission as capability
import notification_deployment as transaction
import notification_live as live
import notification_session as session
import user_install as deployment

ROOT = Path(__file__).resolve().parents[1]
SCOPE = 'omabuntu-user-background-overlay-v1'
SOURCES = {
    'shell/TrialShell.qml': 'config/shell/preview/TrialShell.qml',
    'shell/CommandMenu.qml': 'config/shell/preview/CommandMenu.qml',
    'shell/ImagePicker.qml': 'config/shell/preview/ImagePicker.qml',
    'shell/omabuntu-menu.jsonc': 'config/shell/omabuntu-menu.jsonc',
    'helpers/menu_model.py': 'tools/menu_model.py',
    'helpers/background_backend.py': 'tools/background_backend.py',
    'helpers/theme_backend.py': 'tools/theme_backend.py',
    'helpers/user_backgrounds.py': 'tools/user_backgrounds.py',
}
EVIDENCE = {'picker.json': 'isolated-picker-fixtures-passed',
            'native.json': 'passed', 'clean-source.json': 'passed'}


def verify_evidence(bundle):
    proof = capability.load(bundle, 'native/background-overlay.json')
    if proof.get('scope') != SCOPE or proof.get('controller_sha256') != capability.digest(Path(__file__)):
        raise ValueError('Background overlay/controller differs')
    for target, source in SOURCES.items():
        digest = capability.digest(capability.regular(bundle, target))
        if proof.get('sources', {}).get(target) != digest or capability.digest(ROOT / source) != digest:
            raise ValueError('Background source witness differs')
    for name, status in EVIDENCE.items():
        path = capability.regular(bundle, 'native/background-tests/' + name)
        row = deployment.read_json(path)
        if capability.digest(path) != proof['evidence'][name] or row.get('status') != status:
            raise ValueError('Background test evidence differs')
        if name == 'native.json' and (row.get('inputs_unchanged') is not True or row.get('children_reaped') is not True
                                      or row.get('sources') != proof['sources'] or not row.get('checks')
                                      or any(c.get('passed') is not True for c in row['checks'])):
            raise ValueError('Native background cleanup/input evidence missing')
    log = capability.regular(bundle, 'native/background-tests/unit-tests.log')
    if capability.digest(log) != proof['evidence']['unit-tests.log'] or not log.read_text().endswith('\nOK\n'):
        raise ValueError('Background unit evidence failed')
    transaction.validate_acceptance(bundle)
    return proof


def prepare(base, output, version, evidence):
    base, output, evidence = (Path(p).absolute() for p in (base, output, evidence))
    before = deployment.verify_bundle(base, installed=True)
    capability.verify(base); transaction.validate_acceptance(base)
    if not deployment.VERSION.fullmatch(version) or output.exists():
        raise ValueError('Require a fresh overlay version/directory')
    shutil.copytree(base, output, symlinks=True)
    for target, source in SOURCES.items():
        transaction.copy_replacing(ROOT / source, output / target)
    proof = {'scope': SCOPE, 'base_release_sha256': capability.digest(base / 'release.json'),
             'controller_sha256': capability.digest(Path(__file__)),
             'sources': {p: capability.digest(output / p) for p in SOURCES}, 'evidence': {},
             'wallpaper_changed': False, 'fresh_session_grant_required': True,
             'notification_closure_unchanged': True}
    tests = output / 'native/background-tests'; tests.mkdir(mode=0o700, exist_ok=True)
    for name in (*EVIDENCE, 'unit-tests.log'):
        transaction.copy_replacing(evidence / name, tests / name)
        proof['evidence'][name] = capability.digest(tests / name)
    provenance = deployment.read_json(output / 'PROVENANCE.json')
    provenance['user_background_overlay'] = dict(proof)
    transaction.write_preserved(output / 'PROVENANCE.json', json.dumps(provenance, indent=2) + '\n')
    actual = deployment.file_manifest(output)
    changed = {p for p in set(actual) | set(before['files']) if actual.get(p) != before['files'].get(p)}
    allowed = set(SOURCES) | {'PROVENANCE.json'} | {'native/background-tests/' + n for n in (*EVIDENCE, 'unit-tests.log')}
    if not changed <= allowed or capability.runtime_manifest(output) != capability.runtime_manifest(base):
        raise ValueError('Unrelated overlay/runtime delta')
    proof['changed_paths'] = sorted(changed)
    (output / 'native/background-overlay.json').write_text(json.dumps(proof, indent=2) + '\n')
    meta = dict(before, version=version, files=deployment.file_manifest(output))
    transaction.write_preserved(output / 'release.json', json.dumps(meta, indent=2) + '\n')
    deployment.verify_bundle(output); capability.verify(output); verify_evidence(output)
    return proof


class Upgrade(live.Live):
    def role(self, release):
        raw = live.command([str(release / 'runtime/bin/quickshell'), 'ipc', '--path', str(release / 'shell/TrialShell.qml'),
                            'call', 'omabuntuNotificationRole', 'status'])
        row = json.loads(raw)
        if row.get('admitted') is not True or row.get('ready') is not True or type(row.get('quiet')) is not bool:
            raise ValueError('Prior notification role is not ready')
        return row

    def fence_provider(self):
        # Validate, never change, the already approved runtime-only fence.
        if not self.mask.is_symlink() or os.readlink(self.mask) != '/dev/null':
            raise ValueError('Existing notification activation fence differs')
        unit = self.unit()
        if unit.get('ActiveState') != 'inactive' or unit.get('UnitFileState') != 'masked-runtime':
            raise ValueError('Competing provider is not fenced/inactive')

    def stop_provider(self):
        if live.owner() is not None:
            raise ValueError('Notification owner remains; no takeover or competing fallback')

    def check_overlay(self):
        deployment.verify_bundle(self.bundle); capability.verify(self.bundle)
        proof = verify_evidence(self.bundle)
        self.target = self.app.selected(); base = self.root / self.target
        if proof['base_release_sha256'] != capability.digest(base / 'release.json'):
            raise ValueError('Background overlay belongs to a different installed base')
        capability.verify(base)
        if capability.runtime_manifest(base) != capability.runtime_manifest(self.bundle):
            raise ValueError('Runtime changed')
        for name in capability.SOURCE_NAMES:
            if capability.digest(base / 'shell' / name) != capability.digest(self.bundle / 'shell' / name):
                raise ValueError('Notification closure changed')
    def preflight(self):
        self.app.require_settled()
        self.check_overlay()
        self.old = self.app.running()
        if not self.old:
            raise ValueError('Require the currently owned captured shell')
        self.old_capture = live.capture_identity(self.old)
        owner = live.owner()
        if not owner or live.dbus('org.freedesktop.DBus.GetConnectionUnixProcessID', owner) != self.old['pid']:
            raise ValueError('Prior shell is not the exclusive notification owner')
        self.quiet = self.role(base)['quiet']
        self.mask = Path(os.environ['XDG_RUNTIME_DIR']) / 'systemd/user/swaync.service'
        self.fence_provider()
        self.env = dict(os.environ)
        self.env.setdefault('DBUS_SESSION_BUS_ADDRESS', 'unix:path=' + self.env['XDG_RUNTIME_DIR'] + '/bus')
        self.session_digest = session.session_digest(self.env)
        self.pre = {'current': self.target, 'previous': self.app.selected('previous'), 'launcher_existed': True,
                    'launcher_mode': stat.S_IMODE(self.launcher.stat().st_mode), 'launcher_sha256': capability.digest(self.launcher)}

    def snapshot(self):
        self.directory = deployment.private_directory(self.state / 'background-migrations' / deployment.stamp())
        self.data = {'scope': SCOPE, 'status': 'prepared', 'bundle': str(self.bundle),
                     'bundle_sha256': capability.digest(self.bundle / 'release.json'), 'pre': self.pre,
                     'old': self.old, 'old_capture': self.old_capture, 'quiet': self.quiet,
                     'session_sha256': self.session_digest, 'events': [], 'backups': []}
        for source, name in ((self.launcher, 'launcher'), (self.state / 'running.json', 'running-before.json'),
                             (Path(self.old['log']), 'previous-output.log')):
            shutil.copy2(source, self.directory / name)
            self.data['backups'].append({'source': str(source), 'backup': name, 'sha256': capability.digest(source),
                                         'mode': stat.S_IMODE(source.stat().st_mode)})
        shutil.copytree(self.old_capture['directory'], self.directory / 'previous-native-capture')
        self.save()

    def grant(self):
        release = self.root / self.app.selected()
        path = session.issue(release, self.directory / 'grant', self.env)
        self.data.update(grant=str(path), grant_nonce=session.private_json(path)['nonce'], grant_bundle=str(release)); self.save()

    def recover(self):
        env = dict(os.environ)
        env.setdefault('DBUS_SESSION_BUS_ADDRESS', 'unix:path=' + env['XDG_RUNTIME_DIR'] + '/bus')
        if session.session_digest(env) != self.data['session_sha256']:
            raise ValueError('Recovery belongs to a different compositor session')
        for row in self.data['backups']:
            path = self.directory / row['backup']
            if len(Path(row['backup']).parts) != 1 or path.is_symlink() or capability.digest(path) != row['sha256'] or stat.S_IMODE(path.stat().st_mode) != row['mode']:
                raise ValueError('Recovery backup integrity differs')
        self.reload(); running = self.app.running()
        if running and running != self.data['old']:
            attempt = self.data.get('attempt')
            if self.adapter and self.adapter.child:
                attempt = self.adapter.child.record
            if not attempt or running['pid'] != attempt['pid'] or running['identity'] != attempt['identity']:
                raise ValueError('Unrelated shell; no recovery stop')
            info = live.capture_identity(running)
            self.app.stop()
            live.wait(lambda: not live.capture.same_process(info['supervisor']), 'Attempt capture did not stop')
        if self.adapter and self.adapter.child and live.capture.same_process(self.adapter.child.record):
            self.adapter.child.terminate()
        self.fence_provider()
        if self.app.selected() not in {self.pre['current'], 'releases/' + deployment.read_json(self.bundle / 'release.json')['version']}:
            raise ValueError('Selector changed outside transaction')
        if self.app.selected('previous') not in {self.pre['previous'], self.pre['current']}:
            raise ValueError('Previous selector changed outside transaction')
        if self.launcher.is_symlink() or capability.digest(self.launcher) not in {self.pre['launcher_sha256'], live.hashlib.sha256(self.app.bootstrap().encode()).hexdigest()}:
            raise ValueError('Launcher changed outside transaction')
        grant = self.data.get('grant')
        if grant:
            if Path(grant) != self.directory / 'grant/grant.json':
                raise ValueError('Grant outside transaction')
            original = session.private_json(Path(grant))
            if original.get('nonce') != self.data['grant_nonce'] or original.get('bundle') != self.data['grant_bundle']:
                raise ValueError('Grant changed outside transaction')
            deployment.atomic_json(Path(grant), {**original, 'revoked': True})
        self.app.restore(self.directory, self.pre); self.reload()
        if not self.app.running():
            self.stop_provider()
            release = self.root / self.app.selected()
            recovery = session.issue(release, self.directory / ('recovery-grant-' + deployment.stamp()), env)
            self.data['recovery_grant'] = str(recovery); self.save()
            with live.captured_start(self.manager, session.argv(release), recovery):
                restored = self.app.start(restore_background=False)
            live.capture_identity(restored)
            if self.role(release)['quiet'] != self.data['quiet'] or live.dbus('org.freedesktop.DBus.GetConnectionUnixProcessID', live.owner()) != restored['pid']:
                raise ValueError('Recovered notification ownership/DND differs')
        self.data.update(status='restored', restored=self.app.running()); self.save()


class RestartCrashed(Upgrade):
    """Explicit stopped-session recovery; never revive the withdrawn dialog."""
    def __init__(self, bundle, prior_journal):
        super().__init__(bundle)
        self.prior_journal = Path(prior_journal).absolute()

    def require_absent(self):
        if self.app.running() or live.owner() is not None:
            raise ValueError('Shell or notification owner exists; no stopped-session restart')
        result = live.subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'quickshell'],
                                     capture_output=True, timeout=3, check=False)
        if result.returncode != 1:
            raise ValueError('Another Quickshell exists or process lookup failed')

    def validate_prior(self):
        prior_path = self.prior_journal
        if not prior_path.is_dir() or prior_path.parent != self.state / 'background-migrations':
            raise ValueError('Require the owned prior background transaction directory')
        deployment.private_directory(prior_path)
        prior = session.private_json(prior_path / 'journal.json')
        self.old = deployment.read_json(self.state / 'running.json')
        if (prior.get('scope') != SCOPE or prior.get('status') != 'completed'
                or prior.get('result', {}).get('shell') != self.old
                or self.old.get('release') != self.target
                or prior.get('bundle_sha256') != capability.digest(self.root / self.target / 'release.json')):
            raise ValueError('Stale shell record/prior artifact identity differs')
        if deployment.identity(self.old['pid']) is not None:
            raise ValueError('Prior shell PID is still occupied')
        proof = session.private_json(prior_path / 'grant/grant.json')
        claim = session.private_json(prior_path / 'grant/claim.json')
        if (set(proof) != session.KEYS or proof.get('argv') != session.argv(self.root / self.target)
                or self.old['identity'].get('argv') != proof.get('argv')
                or proof.get('session_sha256') != self.session_digest
                or prior.get('session_sha256') != self.session_digest
                or proof.get('nonce') != prior.get('grant_nonce')
                or proof.get('bundle') != str(self.root / self.target)
                or proof.get('release_sha256') != prior['bundle_sha256']
                or claim != {'nonce': proof['nonce'], 'pid': self.old['pid'], 'identity': self.old['identity']}):
            raise ValueError('Prior session/grant/parent claim differs')
        directory = Path(self.old['log']).parent / 'native-capture'
        if not directory.is_relative_to(self.state / 'runs'):
            raise ValueError('Prior capture is outside owned runs')
        deployment.safe_parents(directory)
        self.old_capture = prior['result']['capture']
        if Path(self.old_capture['directory']) != directory:
            raise ValueError('Prior capture directory differs')
        ready = deployment.read_json(directory / 'ready.json')
        done = deployment.read_json(directory / 'supervisor-finished.json')
        fatal = deployment.read_json(directory / 'gdb-finished.json')
        if (ready != {'pid': self.old['pid'], 'identity': self.old['identity']}
                or done != {'status': 'debugger-exited', 'debugger_returncode': 0}
                or fatal.get('fatal_signal') not in live.capture.FATAL_SIGNALS
                or any(deployment.identity(self.old_capture[k]['pid']) is not None for k in ('debugger', 'supervisor'))):
            raise ValueError('Require a completed fatal capture with no live debugger/supervisor')

    def preflight(self):
        self.app.require_settled(); self.check_overlay(); self.require_absent()
        self.env = dict(os.environ)
        self.env.setdefault('DBUS_SESSION_BUS_ADDRESS', 'unix:path=' + self.env['XDG_RUNTIME_DIR'] + '/bus')
        self.session_digest = session.session_digest(self.env)
        self.validate_prior()
        self.mask = Path(self.env['XDG_RUNTIME_DIR']) / 'systemd/user/swaync.service'
        self.fence_provider()
        # Quiet is non-message metadata. Never collect live/history contents.
        path = self.state / 'notifications/quiet.json'
        live.notification_state.owned(path)
        quiet = deployment.read_json(path)
        if set(quiet) != {'dnd'} or type(quiet['dnd']) is not bool:
            raise ValueError('Unknown current DND state')
        self.quiet = quiet['dnd']
        self.pre = {'current': self.target, 'previous': self.app.selected('previous'), 'launcher_existed': True,
                    'launcher_mode': stat.S_IMODE(self.launcher.stat().st_mode), 'launcher_sha256': capability.digest(self.launcher)}

    def stop_owned_shell(self):
        # The prior shell is dead; do not signal a stale PID or discard its log.
        self.require_absent()
        if deployment.read_json(self.state / 'running.json') != self.old or self.app.selected() != self.target:
            raise ValueError('Stopped session changed after preflight')
        self.event('completed-fatal-capture-preserved-no-stop-needed')

    def recover(self):
        # No fallback to a release containing the withdrawn crashing dialog.
        running = self.app.running()
        attempt = self.data.get('attempt')
        if self.adapter and self.adapter.child:
            attempt = self.adapter.child.record
        if running:
            if not attempt or running['pid'] != attempt['pid'] or running['identity'] != attempt['identity']:
                raise ValueError('Unrelated shell; failed restart refuses to stop it')
            self.app.stop()
        if self.adapter and self.adapter.child and live.capture.same_process(self.adapter.child.record):
            self.adapter.child.terminate()
        path = self.data.get('grant')
        if path:
            if Path(path) != self.directory / 'grant/grant.json':
                raise ValueError('Grant outside restart transaction')
            proof = session.private_json(Path(path))
            if proof.get('nonce') != self.data['grant_nonce'] or proof.get('bundle') != self.data['grant_bundle']:
                raise ValueError('Restart grant changed')
            deployment.atomic_json(Path(path), {**proof, 'revoked': True})
        self.data.update(status='failed-stopped-no-fallback'); self.save()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--apply', action='store_true'); parser.add_argument('--recover', type=Path)
    parser.add_argument('--resume-crashed', type=Path, help='Exact completed prior transaction; requires a dead captured shell')
    args = parser.parse_args(argv)
    if not args.apply:
        print('Plan only: scoped overlay and fresh exclusive notification grant; requires --apply.')
        return 0
    os.umask(0o077)
    if args.recover and args.resume_crashed:
        parser.error('--recover and --resume-crashed are separate operations')
    ops = RestartCrashed(args.bundle, args.resume_crashed) if args.resume_crashed else Upgrade(args.bundle)
    fd = os.open(ops.state / 'control.lock', os.O_RDWR | os.O_NOFOLLOW)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.recover:
            ops.directory = deployment.private_directory(args.recover)
            ops.data = session.private_json(ops.directory / 'journal.json')
            if ops.data.get('scope') != SCOPE or ops.data.get('bundle') != str(ops.bundle) or ops.data.get('bundle_sha256') != capability.digest(ops.bundle / 'release.json'):
                raise ValueError('Recovery journal/artifact differs')
            ops.pre = ops.data['pre']; ops.mask = Path(os.environ['XDG_RUNTIME_DIR']) / 'systemd/user/swaync.service'
            ops.recover(); result = {'status': ops.data['status']}
        else:
            result = transaction.switch(ops)
    print(json.dumps({'journal': str(ops.directory), **result}, indent=2)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
