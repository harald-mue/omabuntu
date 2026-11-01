"""Native application transition uses fixture processes/files only."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import native_transition as native
import release_update as update
import plugin_manager
import plugin_login
import user_install
import test_release_update as fixtures


class NativeTransactionTests(unittest.TestCase):
    bundle = fixtures.ReleaseUpdateTests.bundle
    review = fixtures.ReleaseUpdateTests.review
    apply = fixtures.ReleaseUpdateTests.apply
    stop = fixtures.ReleaseUpdateTests.stop

    def setUp(self):
        fixtures.ReleaseUpdateTests.setUp(self)
        meta_path = self.a / 'release.json'
        meta = json.loads(meta_path.read_text())
        meta['update_contract']['native_target'] = native.FROM.copy()
        meta_path.write_text(json.dumps(meta))
        self.app.install(self.a)
        self.config = self.base / 'config'
        (self.config / 'hypr').mkdir(parents=True)
        (self.config / 'hypr/hyprland.lua').write_text('-- private fixture')
        self.proof = {'kind': 'fixture-native-proof', 'profile_root': str(self.config),
                      'profile': native.profile_state(self.config)}
        mock = patch.object(native, 'evidence', side_effect=lambda *args: copy.deepcopy(self.proof))
        self.evidence = mock.start()
        self.addCleanup(mock.stop)

    def transition(self, **kwargs):
        return self.review(mode='update', migrate_native=True, **kwargs)

    def start(self, **kwargs):
        self.events.append(('start', self.app.selected(), kwargs))
        self.live = {'pid': 123, 'identity': {'fixture': True}}

    def test_normal_update_still_refuses_without_flag(self):
        with self.assertRaisesRegex(update.UpdateError, 'native target differs'):
            self.review(mode='update')
        self.evidence.assert_not_called()
        self.assertEqual(self.app.selected(), 'releases/v1')

    def test_explicit_handoff_does_not_rewrite_old_contract_or_profile(self):
        old = (self.app.root / 'releases/v1/release.json').read_bytes()
        profile = native.profile_state(self.config)
        result = self.apply(self.transition())
        self.assertEqual(result['status'], 'installed-not-started')
        self.assertEqual(self.app.selected(), 'releases/v2')
        self.assertEqual(self.app.selected('previous'), 'releases/v1')
        self.assertEqual((self.app.root / 'releases/v1/release.json').read_bytes(), old)
        self.assertEqual(native.profile_state(self.config), profile)

    def test_bar_restart_is_separate_and_preserves_wallpaper(self):
        self.live = {'pid': 11, 'identity': {'fixture': True}}
        with self.assertRaisesRegex(update.UpdateError, 'restart-bar'):
            self.transition()
        plan = self.transition(restart=True)
        with patch.object(self.app, 'start', side_effect=self.start) as start, \
             patch.object(self.app, 'stop', side_effect=self.stop):
            self.apply(plan)
        start.assert_called_once_with(restore_background=False)
        self.assertEqual(self.app.selected(), 'releases/v2')

    def test_evidence_drift_during_staging_never_stops_bar(self):
        self.live = {'pid': 11, 'identity': {'fixture': True}}
        plan = self.transition(restart=True)
        original = update.stage
        def stage(app, bundle):
            candidate = original(app, bundle)
            self.proof['changed'] = True
            return candidate
        with patch.object(update, 'stage', side_effect=stage), patch.object(self.app, 'stop') as stop:
            with self.assertRaisesRegex(update.UpdateError, 'Update failed'):
                self.apply(plan)
        stop.assert_not_called()
        self.assertEqual(self.app.selected(), 'releases/v1')

    def test_failed_new_start_restores_old_application_not_system_state(self):
        self.live = {'pid': 11, 'identity': {'fixture': True}}
        plan = self.transition(restart=True)
        def start(**kwargs):
            if self.app.selected() == 'releases/v2':
                raise ValueError('fixture new bar failed')
            self.start(**kwargs)
        with patch.object(self.app, 'start', side_effect=start), patch.object(self.app, 'stop', side_effect=self.stop):
            with self.assertRaisesRegex(update.UpdateError, 'previous selection restored'):
                self.apply(plan)
        self.assertEqual(self.app.selected(), 'releases/v1')
        self.assertEqual(self.events[-1][2], {'restore_background': False})
        self.assertFalse(update.unresolved(self.app))

    def test_same_target_update_and_rollback_after_handoff_need_no_flag(self):
        self.apply(self.transition())
        c = self.bundle('v3')
        self.apply(update.review(self.app, c, mode='update'))
        self.assertEqual(self.app.selected(), 'releases/v3')
        self.apply(update.review(self.app, mode='rollback'))
        self.assertEqual(self.app.selected(), 'releases/v2')
        with self.assertRaisesRegex(update.UpdateError, 'session plan'):
            # The legacy v1 target is not a supported native rollback.
            update.review(self.app, self.app.root / 'releases/v1', mode='update')

    def test_flag_cannot_be_reused_as_generic_native_bypass(self):
        self.apply(self.transition())
        with self.assertRaisesRegex(update.UpdateError, 'ordinary updates need no flag'):
            self.transition()
        with self.assertRaisesRegex(update.UpdateError, 'explicit versioned update'):
            self.review(migrate_native=True)

    def test_private_profile_change_after_review_is_preserved(self):
        plan = self.transition()
        (self.config / 'hypr/hyprland.lua').write_text('-- changed privately')
        self.proof['profile'] = native.profile_state(self.config)
        with patch.object(self.app, 'stop') as stop, self.assertRaisesRegex(update.UpdateError, 'state changed'):
            self.apply(plan)
        stop.assert_not_called()
        self.assertEqual((self.config / 'hypr/hyprland.lua').read_text(), '-- changed privately')

    def test_profile_edit_during_start_is_preserved_while_application_restores(self):
        self.live = {'pid': 11, 'identity': {'fixture': True}}
        plan = self.transition(restart=True)
        path = self.config / 'hypr/hyprland.lua'
        def start(**kwargs):
            self.start(**kwargs)
            if self.app.selected() == 'releases/v2':
                path.write_text('-- concurrent private edit')
        with patch.object(self.app, 'start', side_effect=start), patch.object(self.app, 'stop', side_effect=self.stop):
            with self.assertRaisesRegex(update.UpdateError, 'previous selection restored'):
                self.apply(plan)
        self.assertEqual(self.app.selected(), 'releases/v1')
        self.assertEqual(path.read_text(), '-- concurrent private edit')

    def test_recovery_accepts_real_process_record_instead_of_only_bool(self):
        directory = user_install.private_directory(self.app.state / 'updates/fixture')
        pre = {'current': 'releases/v1', 'previous': None, 'launcher_existed': True,
               'launcher_sha256': update.hashlib.sha256(self.app.launcher.read_bytes()).hexdigest()}
        (directory / 'launcher').write_bytes(self.app.launcher.read_bytes())
        plan = {'operation': 'update', 'version': 'v2', 'running': {'pid': 11, 'identity': {'fixture': True}}}
        user_install.atomic_json(directory / 'journal.json',
                                 {'schema_version': 1, 'status': 'preparing', 'plan': plan, 'prestate': pre})
        self.assertEqual(update.recover_review(self.app)['action'], 'mark-unchanged')


class NativeEvidenceTests(unittest.TestCase):
    bundle = fixtures.ReleaseUpdateTests.bundle

    def setUp(self):
        fixtures.ReleaseUpdateTests.setUp(self)
        old = json.loads((self.a / 'release.json').read_text())
        old['update_contract']['native_target'] = native.FROM.copy()
        (self.a / 'release.json').write_text(json.dumps(old))
        self.app.install(self.a)
        self.policy = plugin_manager.policy()
        target = self.policy['targets']['0.57.0']
        self.native = {'version': '0.57.0', 'commit': target['hyprland_commit'], 'abiHash': 'fixture-abi', 'dirty': False}
        self.running = {'commit': self.native['commit'], 'abiHash': 'fixture-abi', 'flags': []}
        self.loaded = []
        self.directory = self.base / 'cache'
        repo = self.directory / 'hyprland-plugins'
        repo.mkdir(parents=True)
        (repo / 'hyprbars.so').write_bytes(b'fixture plugin')
        (repo / 'state.toml').write_text('[repository]\nname="hyprland-plugins"\nurl=' + json.dumps(self.policy['repository'])
                                       + '\nrev=' + json.dumps(target['plugin_commit']) + '\nhash=' + json.dumps(target['plugin_commit'])
                                       + '\n[hyprbars]\nfilename="hyprbars.so"\nfailed=false\nenabled=false\n')
        (self.directory / 'state.toml').write_text('[state]\nhash="fixture-abi"\n')
        self.receipt = {'native': self.native, 'activated': False, 'policy_digest': plugin_login.digest(self.policy),
                        'library': str(repo / 'hyprbars.so'),
                        'library_sha256': update.hashlib.sha256(b'fixture plugin').hexdigest()}
        user_install.atomic_json(self.app.state / 'hyprpm.json', self.receipt)
        self.config = self.base / 'config'
        self.config.mkdir()
        for mock in (patch.object(plugin_manager, 'bundle_policy', return_value=self.policy),
                     patch.object(plugin_manager.build_hyprbars, 'installed_version', side_effect=lambda: self.native),
                     patch.object(plugin_login, 'header_state', return_value={'layout': 'fixture-headers'})):
            mock.start()
            self.addCleanup(mock.stop)

    def inspect(self, argv):
        if argv == ['hyprctl', '-j', 'version']:
            return json.dumps(self.running)
        if argv == ['hyprctl', '-j', 'plugin', 'list']:
            return json.dumps(self.loaded)
        raise AssertionError(argv)

    def evidence(self):
        return native.evidence(self.app, self.b, inspect=self.inspect, directory=self.directory, config=self.config)

    def test_valid_inactive_manager_handoff_is_read_only(self):
        before = (self.app.state / 'hyprpm.json').read_bytes()
        self.assertFalse(self.evidence()['plugins_changed'])
        self.assertEqual((self.app.state / 'hyprpm.json').read_bytes(), before)
        self.assertEqual(self.app.selected(), 'releases/v1')

    def test_valid_active_manager_is_preserved_without_enable_or_reload(self):
        self.receipt['activated'] = True
        user_install.atomic_json(self.app.state / 'hyprpm.json', self.receipt)
        repo = self.directory / 'hyprland-plugins/state.toml'
        repo.write_text(repo.read_text().replace('enabled=false', 'enabled=true'))
        self.loaded = [{'name': 'hyprbars'}]
        self.assertEqual(self.evidence()['loaded'], self.loaded)

    def test_stale_header_fingerprints_are_refused(self):
        self.receipt['headers'] = {'layout': 'old-headers'}
        user_install.atomic_json(self.app.state / 'hyprpm.json', self.receipt)
        with self.assertRaisesRegex(ValueError, 'fingerprints changed'):
            self.evidence()

    def test_foreign_manager_repository_is_refused(self):
        foreign = self.directory / 'foreign'
        foreign.mkdir()
        (foreign / 'state.toml').write_text('[repository]')
        with self.assertRaisesRegex(ValueError, 'Foreign manager repository'):
            self.evidence()

    def test_running_abi_dirty_or_foreign_plugin_is_refused(self):
        self.running['abiHash'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'clean matching'):
            self.evidence()
        self.running['abiHash'] = 'fixture-abi'
        self.loaded = [{'name': 'foreign'}]
        with self.assertRaisesRegex(ValueError, 'Live plugin'):
            self.evidence()

    def test_library_drift_is_not_adopted(self):
        Path(self.receipt['library']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'exact current manager build'):
            self.evidence()

    def test_old_activation_requires_separate_handoff(self):
        user_install.atomic_json(self.app.state / 'session-activation.json', {'library': '/legacy.so'})
        with self.assertRaisesRegex(ValueError, 'owned-loader handoff'):
            self.evidence()

    def test_unresolved_plugin_operation_blocks(self):
        path = self.app.state / 'plugin-transactions/failed'
        path.mkdir(parents=True)
        user_install.atomic_json(path / 'transaction.json', {'status': 'manual-review-required'})
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            self.evidence()

    def test_arbitrary_native_target_change_is_refused(self):
        meta = json.loads((self.b / 'release.json').read_text())
        meta['update_contract']['native_target']['qt'] = '6.11.0'
        (self.b / 'release.json').write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, 'Only the explicit'):
            self.evidence()
