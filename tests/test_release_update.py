"""Prepared-release update tests: fixture files, mocked bar, no host changes."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import release_update as update
import user_install


class ReleaseUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.app = user_install.Installation(self.base / 'data/app', self.base / 'state/app', self.base / 'bin/omabuntu')
        self.live = None
        self.events = []
        patcher = patch.object(self.app, 'running', side_effect=lambda: self.live)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.a = self.bundle('v1')
        self.b = self.bundle('v2')

    def bundle(self, version):
        directory = self.base / 'bundles' / version
        directory.mkdir(parents=True)
        for name in user_install.INCOMING:
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture ' + version + ' ' + name)
            path.chmod(0o755 if name == 'runtime/bin/quickshell' else 0o444)
        meta = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': version,
                'autostart': False, 'lock_activation': False,
                'update_contract': update.contract(), 'files': user_install.file_manifest(directory)}
        (directory / 'release.json').write_text(json.dumps(meta))
        return directory

    def review(self, bundle=None, **kwargs):
        return update.review(self.app, self.b if bundle is None else bundle, **kwargs)

    def apply(self, plan, **kwargs):
        return update.apply(self.app, plan, update.approve_digest(plan),
                            check=lambda bundle: {'status': 'passed'}, check_locker=lambda: None, **kwargs)

    def start(self):
        self.events.append(('start', self.app.selected()))
        self.live = {'pid': 123, 'identity': {'fixture': True}}

    def stop(self):
        self.events.append(('stop', self.app.selected()))
        self.live = None

    def test_review_is_read_only(self):
        plan = self.review()
        self.assertFalse(self.app.root.exists())
        self.assertFalse(self.app.state.exists())
        self.assertEqual(plan['scope'], 'local-application-release-only')

    def test_bundled_activation_requires_explicit_hyprpm_migration(self):
        self.app.state.mkdir(parents=True)
        (self.app.state / 'session-activation.json').write_text(json.dumps({'library': '/immutable/old/hyprbars.so'}))
        with patch.object(update, 'candidate_plugin', return_value={'manager': 'hyprpm'}):
            with self.assertRaisesRegex(update.UpdateError, 'explicit migration'):
                self.review()
        self.assertFalse(self.app.root.exists())
        self.assertEqual(self.events, [])

    def test_bad_approval_has_no_writes(self):
        plan = self.review()
        with self.assertRaisesRegex(update.UpdateError, 'Approval'):
            update.apply(self.app, plan, 'wrong')
        self.assertFalse(self.app.state.exists())

    def test_fresh_bundle_install_does_not_start_bar(self):
        result = self.apply(self.review())
        self.assertEqual(result['status'], 'installed-not-started')
        self.assertEqual(self.app.selected(), 'releases/v2')
        self.assertIsNone(self.live)

    def test_update_preserves_preferences_and_previous_release(self):
        self.app.install(self.a)
        prefs = self.app.state / 'settings/weather.json'
        prefs.parent.mkdir()
        prefs.write_text('{"name":"Wien"}')
        self.live = {'pid': 11}
        plan = self.review(mode='update', restart=True)
        with patch.object(self.app, 'start', side_effect=self.start), patch.object(self.app, 'stop', side_effect=self.stop):
            result = self.apply(plan)
        self.assertEqual(result['status'], 'updated-and-started')
        self.assertEqual(self.app.selected('previous'), 'releases/v1')
        self.assertEqual(prefs.read_text(), '{"name":"Wien"}')
        self.assertEqual(self.events, [('stop', 'releases/v1'), ('start', 'releases/v2')])

    def test_update_requires_restart_permission_for_running_bar(self):
        self.app.install(self.a)
        self.live = {'pid': 11}
        with self.assertRaisesRegex(update.UpdateError, 'restart-bar'):
            self.review(mode='update')

    def test_failed_start_restores_exact_selectors_and_starts_previous(self):
        self.app.install(self.a)
        before_launcher = self.app.launcher.read_bytes()
        self.live = {'pid': 11}
        plan = self.review(mode='update', restart=True)
        def start():
            if self.app.selected() == 'releases/v2':
                raise ValueError('fixture startup failure')
            self.start()
        with patch.object(self.app, 'start', side_effect=start), patch.object(self.app, 'stop', side_effect=self.stop):
            with self.assertRaisesRegex(update.UpdateError, 'previous selection restored'):
                self.apply(plan)
        self.assertEqual(self.app.selected(), 'releases/v1')
        self.assertIsNone(self.app.selected('previous'))
        self.assertEqual(self.app.launcher.read_bytes(), before_launcher)
        self.assertIsNotNone(self.live)
        self.assertFalse(update.unresolved(self.app))
        self.assertTrue((self.app.root / 'releases/v2').exists())

    def test_failed_first_start_restores_preexisting_launcher(self):
        self.app.launcher.parent.mkdir()
        self.app.launcher.write_text('custom launcher')
        self.app.launcher.chmod(0o750)
        plan = self.review(restart=True)
        with patch.object(self.app, 'start', side_effect=ValueError('fixture failure')):
            with self.assertRaises(update.UpdateError):
                self.apply(plan)
        self.assertIsNone(self.app.selected())
        self.assertEqual(self.app.launcher.read_text(), 'custom launcher')
        self.assertEqual(self.app.launcher.stat().st_mode & 0o777, 0o750)

    def test_invalid_preflight_never_stops_old_bar(self):
        self.app.install(self.a)
        self.live = {'pid': 11}
        plan = self.review(restart=True)
        with patch.object(self.app, 'stop') as stop, self.assertRaisesRegex(update.UpdateError, 'preflight'):
            update.apply(self.app, plan, update.approve_digest(plan),
                         check=lambda bundle: {'status': 'blocked'}, check_locker=lambda: None)
        stop.assert_not_called()
        self.assertEqual(self.app.selected(), 'releases/v1')

    def test_staging_failure_does_not_stop_bar(self):
        self.app.install(self.a)
        self.live = {'pid': 11}
        plan = self.review(restart=True)
        with patch.object(update, 'stage', side_effect=OSError('disk full')), patch.object(self.app, 'stop') as stop:
            with self.assertRaises(update.UpdateError):
                self.apply(plan)
        stop.assert_not_called()
        self.assertEqual(self.app.selected(), 'releases/v1')
        self.assertFalse(update.unresolved(self.app))

    def test_identical_reinstall_is_noop_without_restart_or_preflight(self):
        self.app.install(self.b)
        self.live = {'pid': 11}
        plan = self.review(restart=True)
        with patch.object(update, 'preflight') as preflight, patch.object(self.app, 'stop') as stop:
            result = update.apply(self.app, plan, update.approve_digest(plan))
        self.assertEqual(result['status'], 'already-installed')
        preflight.assert_not_called()
        stop.assert_not_called()

    def test_changed_bundle_or_launcher_invalidates_plan(self):
        self.app.install(self.a)
        plan = self.review()
        self.app.launcher.write_text('edited by user')
        with self.assertRaisesRegex(update.UpdateError, 'Launcher changed'):
            self.apply(plan)
        self.assertEqual(self.app.selected(), 'releases/v1')

    def test_changed_bundle_invalidates_approval_before_stop(self):
        self.app.install(self.a)
        self.live = {'pid': 11}
        plan = self.review(restart=True)
        file = self.b / 'shell/TrialShell.qml'
        file.chmod(0o600)
        file.write_text('changed after review')
        with patch.object(self.app, 'stop') as stop, self.assertRaises(ValueError):
            self.apply(plan)
        stop.assert_not_called()

    def test_launcher_drift_during_staging_is_preserved_without_stopping(self):
        self.app.install(self.a)
        self.live = {'pid': 11}
        plan = self.review(restart=True)
        original = update.stage
        def stage(app, bundle):
            candidate = original(app, bundle)
            app.launcher.write_text('new user edit')
            return candidate
        with patch.object(update, 'stage', side_effect=stage), patch.object(self.app, 'stop') as stop:
            with self.assertRaises(update.UpdateError):
                self.apply(plan)
        stop.assert_not_called()
        self.assertEqual(self.app.launcher.read_text(), 'new user edit')
        self.assertEqual(self.app.selected(), 'releases/v1')

    def test_schema_and_native_mismatch_are_refused(self):
        for field, value in [('user_state_schema', 2), ('native_target', {'ubuntu': '26.04', 'hyprland': '0.99.0', 'qt': '6.10.2'})]:
            meta_path = self.b / 'release.json'
            original = meta_path.read_text()
            meta = json.loads(original)
            meta['update_contract'][field] = value
            meta_path.write_text(json.dumps(meta))
            with self.subTest(field=field), self.assertRaisesRegex(update.UpdateError, 'no state rewrite|session plan'):
                self.review()
            meta_path.write_text(original)

    def test_legacy_state_needs_explicit_acknowledgement(self):
        meta_path = self.a / 'release.json'
        meta = json.loads(meta_path.read_text())
        del meta['update_contract']
        meta_path.write_text(json.dumps(meta))
        self.app.install(self.a)
        with self.assertRaisesRegex(update.UpdateError, 'unversioned'):
            self.review()
        self.assertTrue(self.review(allow_legacy=True)['legacy_state'])

    def journal(self, status, current='releases/v1', previous=None, switched=False):
        self.app.install(self.a)
        directory = user_install.private_directory(self.app.state / 'updates' / 'interrupted')
        pre = {'operation': 'update', 'current': 'releases/v1', 'previous': None,
               'launcher_existed': True, 'launcher_mode': 0o755,
               'launcher_sha256': hashlib.sha256(self.app.launcher.read_bytes()).hexdigest()}
        (directory / 'launcher').write_bytes(self.app.launcher.read_bytes())
        plan = {'operation': 'update', 'version': 'v2', 'running': False, 'current': 'releases/v1', 'previous': None}
        user_install.atomic_json(directory / 'journal.json', {'schema_version': 1, 'status': status, 'plan': plan, 'prestate': pre})
        if switched:
            release = self.app.root / 'releases/v2'
            release.mkdir()
            for name in user_install.BASELINE:
                path = release / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture v2 ' + name)
            meta = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': 'v2',
                    'autostart': False, 'lock_activation': False, 'files': {}}
            (release / 'release.json').write_text(json.dumps(meta))
            meta['files'] = user_install.file_manifest(release)
            (release / 'release.json').write_text(json.dumps(meta))
            self.app.select('previous', 'releases/v1')
            self.app.select('current', 'releases/v2')
        return directory

    def test_interrupted_journal_can_be_marked_without_resuming(self):
        directory = self.journal('preparing')
        reviewed = update.recover_review(self.app)
        self.assertEqual(reviewed['action'], 'mark-unchanged')
        with patch.object(update, 'locker_absent'), patch.object(self.app, 'start') as start:
            result = update.recover(self.app, reviewed, update.guided.digest(reviewed))
        start.assert_not_called()
        self.assertEqual(result['status'], 'recovered-unchanged')
        self.assertFalse(result['resumed_new_release'])
        self.assertFalse(update.unresolved(self.app))
        self.assertEqual(json.loads((directory / 'journal.json').read_text())['status'], 'recovered-unchanged')

    def test_interrupted_switch_restores_prestate_without_starting_new_release(self):
        self.journal('switching', switched=True)
        reviewed = update.recover_review(self.app)
        self.assertEqual(reviewed['action'], 'restore-prestate')
        with patch.object(update, 'locker_absent'), patch.object(self.app, 'start') as start:
            result = update.recover(self.app, reviewed, update.guided.digest(reviewed), restart=False)
        start.assert_not_called()
        self.assertEqual(self.app.selected(), 'releases/v1')
        self.assertIsNone(self.app.selected('previous'))
        self.assertEqual(result['status'], 'recovered-to-prestate')
        self.assertFalse(result['bar_restarted'])

    def test_divergent_interruption_is_not_rewritten(self):
        directory = self.journal('starting')
        self.app.launcher.write_text('user changed launcher')
        reviewed = update.recover_review(self.app)
        self.assertEqual(reviewed['action'], 'manual')
        with self.assertRaises(update.UpdateError):
            update.recover(self.app, reviewed, update.guided.digest(reviewed))
        self.assertEqual(json.loads((directory / 'journal.json').read_text())['status'], 'starting')

    def test_running_bar_blocks_selector_recovery_without_a_forced_stop(self):
        self.journal('switching', switched=True)
        self.live = {'pid': 77}
        reviewed = update.recover_review(self.app)
        with patch.object(self.app, 'stop') as stop, patch.object(update, 'locker_absent'), self.assertRaisesRegex(update.UpdateError, 'no forced stop'):
            update.recover(self.app, reviewed, update.guided.digest(reviewed))
        stop.assert_not_called()

    def test_interrupted_outer_transaction_blocks_new_update(self):
        user_install.private_directory(self.app.state)
        path = self.app.state / 'updates' / 'interrupted'
        path.mkdir(parents=True)
        (path / 'journal.json').write_text('{"status":"starting"}')
        with self.assertRaisesRegex(update.UpdateError, 'Interrupted update'):
            self.review()

    def test_lock_probe_failure_leaves_bar_untouched(self):
        self.app.install(self.a)
        self.live = {'pid': 11}
        plan = self.review(restart=True)
        with patch.object(self.app, 'stop') as stop, self.assertRaises(update.UpdateError):
            update.apply(self.app, plan, update.approve_digest(plan),
                         check=lambda bundle: {'status': 'passed'},
                         check_locker=lambda: (_ for _ in ()).throw(update.UpdateError('locked')))
        stop.assert_not_called()

    def test_plugin_abi_drift_after_staging_never_stops_old_bar(self):
        self.app.install(self.a)
        def verify(bundle):
            if bundle == self.app.root / 'releases/v2':
                raise update.build_plugin.builder.BuildError('fixture ABI drift')
            return None
        with patch.object(update.build_plugin, 'verify_bundle_plugin', side_effect=verify):
            plan = self.review()
            with patch.object(self.app, 'stop') as stop, self.assertRaisesRegex(update.UpdateError, 'Update failed'):
                self.apply(plan)
        stop.assert_not_called()
        self.assertEqual(self.app.selected(), 'releases/v1')
        journal = json.loads(next((self.app.state / 'updates').glob('*/journal.json')).read_text())
        self.assertEqual(journal['status'], 'aborted-before-switch')

    def test_configured_session_blocks_candidates_missing_its_helpers(self):
        self.app.install(self.a)
        receipt = self.app.state / 'session-config.json'
        receipt.write_text(json.dumps({'schema_version': 1, 'helper_contract': 1, 'manual_lock': False}))
        with self.assertRaisesRegex(update.UpdateError, 'configured session'):
            self.review()
        self.assertEqual(self.app.selected(), 'releases/v1')
        for name in user_install.SESSION_HELPERS:
            file = self.b / name
            file.parent.mkdir(parents=True, exist_ok=True)
            if not file.exists():
                file.write_text('fixture ' + name)
            if name == 'runtime/bin/omasnap':
                file.chmod(0o755)
        meta = json.loads((self.b / 'release.json').read_text())
        meta['files'] = user_install.file_manifest(self.b)
        (self.b / 'release.json').write_text(json.dumps(meta))
        self.assertIsNotNone(self.review()['session_config_digest'])

    def test_existing_control_lock_refuses_concurrent_update(self):
        user_install.private_directory(self.app.state)
        plan = self.review()
        with (self.app.state / 'control.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.apply(plan)

    def test_explicit_rollback_can_restart_previous_release(self):
        self.app.install(self.a)
        self.app.install(self.b)
        plan = update.review(self.app, mode='rollback', restart=True)
        with patch.object(self.app, 'start', side_effect=self.start):
            self.apply(plan)
        self.assertEqual(self.app.selected(), 'releases/v1')
        self.assertEqual(self.app.selected('previous'), 'releases/v2')


if __name__ == '__main__':
    unittest.main()
