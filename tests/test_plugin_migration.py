"""Legacy migration uses fixture caches only; never runs a real manager/sudo."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import plugin_manager as manager
import plugin_migration as migration


class PluginMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.directory = self.home / 'manager'
        self.state = self.home / '.local/state/omabuntu'
        self.shared = self.home / 'shared-hyprland.pc'
        self.shared.write_text('original shared metadata')
        self.source = manager.policy()
        self.old = self.source['targets']['0.56.2']
        self.target = self.source['targets']['0.57.0']
        self.native = {'version': '0.57.0', 'commit': self.target['hyprland_commit'],
                       'dirty': False, 'abiHash': self.target['hyprland_commit'] + '_fixture'}
        self.running = {'commit': self.native['commit'], 'abiHash': self.native['abiHash'], 'flags': []}
        self.loaded = []
        self.calls = []
        self.packages = {'gcc': '1.0', 'libcanberra-dev': '1.0'}
        self.write_repository(enabled=True, legacy=True, library=b'old library')
        self.write_global(self.old['hyprland_commit'] + '_fixture')
        include = self.home / 'include'
        include.mkdir()
        (include / 'lua.h').write_text('fixture')
        for mock in (patch.dict(os.environ, {'XDG_STATE_HOME': str(self.home / '.local/state')}),
                     patch.object(manager.shutil, 'which', return_value='/fixture'),
                     patch.object(manager.omabuntu_hyprpm, 'LUA_INCLUDE', include),
                     patch.object(manager.build_hyprbars, 'installed_version', return_value=self.native),
                     patch.object(migration, 'migration_packages', side_effect=lambda: self.packages.copy()),
                     patch.object(migration, 'migration_backend', return_value={'path': '/usr/bin/hyprpm', 'sha256': 'fixture'})):
            mock.start()
            self.addCleanup(mock.stop)

    def write_repository(self, enabled=False, legacy=False, library=None):
        path = self.directory / 'hyprland-plugins'
        path.mkdir(parents=True, exist_ok=True)
        pin = self.old['plugin_commit'] if legacy else self.target['plugin_commit']
        (path / 'state.toml').write_text(
            '[repository]\nname = "hyprland-plugins"\nurl = ' + json.dumps(self.source['repository']) + '\n'
            'rev = ' + json.dumps(pin) + '\nhash = ' + json.dumps(self.target['plugin_commit']) + '\n'
            '[hyprbars]\nfilename = "hyprbars.so"\nfailed = false\nenabled = ' + str(enabled).lower() + '\n')
        if library is not None:
            (path / 'hyprbars.so').write_bytes(library)

    def write_global(self, abi):
        (self.directory / 'state.toml').write_text('[state]\nhash = ' + json.dumps(abi) + '\n')

    def inspect(self, argv):
        if argv == ['hyprctl', '-j', 'version']:
            return json.dumps(self.running)
        if argv == ['hyprctl', '-j', 'plugin', 'list']:
            return json.dumps(self.loaded)
        raise AssertionError(argv)

    def plan(self):
        return migration.plan(ROOT, self.home, self.directory, self.inspect, self.shared)

    def execute(self, argv):
        self.calls.append(argv)
        action = argv[1]
        if action == 'disable':
            (self.directory / 'headersRoot').mkdir(exist_ok=True)
            self.write_repository(enabled=False, legacy=True)
            # The official command writes enablement before returning 1 for
            # stale/missing headers. Prove that postcondition, do not ignore it.
            raise subprocess.CalledProcessError(1, argv)
        if action == 'remove':
            shutil.rmtree(self.directory / 'hyprland-plugins')
        elif action == 'update':
            pc = self.directory / 'headersRoot/share/pkgconfig/hyprland.pc'
            header = self.directory / 'headersRoot/include/hyprland/src/version.h'
            for path in (pc, header):
                path.parent.mkdir(parents=True, exist_ok=True)
            pc.write_text('prefix=' + str(self.directory / 'headersRoot/include') + '\nVersion: 0.57.0\n')
            header.write_text('#define GIT_COMMIT_HASH "' + self.native['commit'] + '"\n#define GIT_DIRTY "clean"\n')
            self.write_global(self.native['abiHash'])
            self.shared.write_text('new shared metadata')
            raise subprocess.CalledProcessError(1, argv)  # No live reconciliation without a socket.
        elif action == 'add':
            self.assertEqual(argv, ['hyprpm', 'add', self.source['repository'], self.target['plugin_commit']])
            self.write_repository(library=b'new rebuilt library')
        else:
            raise AssertionError(argv)

    def apply(self, reviewed=None, execute=None, **kwargs):
        reviewed = self.plan() if reviewed is None else reviewed
        return migration.apply(reviewed, manager.guided.digest(reviewed), replace_approved=True,
                               execute=self.execute if execute is None else execute, inspect=self.inspect, **kwargs)

    def assert_no_receipt(self):
        self.assertFalse((self.state / 'hyprpm.json').exists())

    def test_read_only_plan_recognizes_exact_mixed_state_without_adopting_it(self):
        reviewed = self.plan()
        self.assertFalse(reviewed['blockers'])
        self.assertTrue(reviewed['migration']['recognized'])
        self.assertEqual([c[1] for c in reviewed['commands']], ['disable', 'remove', 'update', 'add'])
        self.assertFalse(reviewed['loads_plugin'])
        self.assertFalse(self.state.exists())
        normal = manager.plan(ROOT, self.home, directory=self.directory, inspect=self.inspect, shared_pkgconfig=self.shared)
        self.assertTrue(normal['ownership_blockers'])
        self.assertEqual(self.calls, [])

    def test_success_has_verified_backups_new_build_and_disabled_receipt(self):
        (self.directory / 'hyprland-plugins').chmod(0o750)
        (self.directory / 'hyprland-plugins/hyprbars.so').chmod(0o550)
        self.shared.chmod(0o640)
        reviewed = self.plan()
        result = self.apply(reviewed)
        self.assertEqual(result['status'], 'plugin-migrated-disabled')
        self.assertFalse(result['plugin_loaded'])
        self.assertTrue(result['activation_required'])
        receipt = json.loads((self.state / 'hyprpm.json').read_text())
        self.assertFalse(receipt['activated'])
        self.assertEqual(receipt['native'], self.native)
        self.assertEqual(receipt['library_sha256'], hashlib.sha256(b'new rebuilt library').hexdigest())
        journal = Path(result['journal'])
        record = json.loads(journal.read_text())
        self.assertTrue(record['backup_verified'])
        self.assertFalse(record['automatic_restore'])
        self.assertEqual(record['status'], 'completed')
        self.assertEqual(record['steps'][0]['returncode'], 1)
        self.assertEqual(record['steps'][0]['outcome'], 'disabled-with-stale-headers')
        self.assertTrue(all(s['status'] == 'verified' for s in record['steps']))
        self.assertEqual(journal.with_name('system-hyprland.pc.before').read_text(), 'original shared metadata')
        with tarfile.open(journal.with_name('manager-before.tar')) as backup:
            self.assertEqual(backup.extractfile('hyprland-plugins/hyprbars.so').read(), b'old library')
            self.assertEqual(backup.getmember('state.toml').uid, reviewed['before']['state.toml']['uid'])
            self.assertEqual(backup.getmember('hyprland-plugins').mode, 0o750)
            self.assertEqual(backup.getmember('hyprland-plugins/hyprbars.so').mode, 0o550)
        self.assertEqual(record['plan']['shared_pkgconfig_before']['mode'], 0o640)
        activate = manager.plan(ROOT, self.home, action='activate', directory=self.directory,
                                inspect=self.inspect, shared_pkgconfig=self.shared)
        self.assertFalse(activate['blockers'])
        self.assertTrue(receipt['migration_journal'])
        self.assertEqual([c[1] for c in self.calls], ['disable', 'remove', 'update', 'add'])
        self.assertEqual(self.loaded, [])

    def test_header_refresh_removes_only_child_compositor_socket(self):
        environment = dict(os.environ, HYPRLAND_INSTANCE_SIGNATURE='fixture-session', CPLUS_INCLUDE_PATH='/existing')
        with patch.dict(os.environ, environment), patch.object(migration.subprocess, 'run') as run:
            migration.execute(['hyprpm', 'update'])
            self.assertEqual(run.call_args.args[0], ['/usr/bin/hyprpm', 'update'])
            child = run.call_args.kwargs['env']
            self.assertNotIn('HYPRLAND_INSTANCE_SIGNATURE', child)
            self.assertEqual(os.environ['HYPRLAND_INSTANCE_SIGNATURE'], 'fixture-session')
            self.assertIn('/existing', child['CPLUS_INCLUDE_PATH'])
            migration.execute(['hyprpm', 'add', self.source['repository'], self.target['plugin_commit']])
            self.assertEqual(run.call_args.kwargs['env']['HYPRLAND_INSTANCE_SIGNATURE'], 'fixture-session')

    def test_repository_replacement_needs_an_extra_approval(self):
        reviewed = self.plan()
        for approved in (False, 'yes', None):
            with self.subTest(approved=approved), self.assertRaises(ValueError):
                migration.apply(reviewed, manager.guided.digest(reviewed), replace_approved=approved,
                                execute=self.execute, inspect=self.inspect)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.state.exists())

    def test_bad_digest_cannot_create_a_transaction(self):
        with self.assertRaises(ValueError):
            migration.apply(self.plan(), 'wrong', replace_approved=True, execute=self.execute, inspect=self.inspect)
        self.assertFalse(self.state.exists())

    def test_unknown_origin_revision_or_build_is_not_replaced(self):
        path = self.directory / 'hyprland-plugins/state.toml'
        original = path.read_text()
        for before, after in ((self.source['repository'], 'https://example.invalid/other'),
                              (self.old['plugin_commit'], '0' * 40), (self.target['plugin_commit'], 'f' * 40)):
            with self.subTest(after=after):
                path.write_text(original.replace(before, after))
                self.assertTrue(self.plan()['blockers'])
                with self.assertRaises(ValueError):
                    self.apply()
        self.assertEqual(self.calls, [])

    def test_unrelated_enabled_plugin_is_preserved_and_blocks_migration(self):
        path = self.directory / 'hyprland-plugins/state.toml'
        path.write_text(path.read_text() + '[other]\nfilename = "other.so"\nenabled = true\nfailed = false\n')
        self.assertTrue(any('Other enabled' in b for b in self.plan()['blockers']))
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(self.calls, [])

    def test_unknown_cache_entry_blocks_migration(self):
        (self.directory / 'unrelated').mkdir()
        self.assertTrue(any('Unexpected manager cache' in b for b in self.plan()['blockers']))

    def test_existing_receipt_is_not_overwritten(self):
        self.state.mkdir(parents=True)
        (self.state / 'hyprpm.json').write_text('{}')
        self.assertTrue(any('Existing Omabuntu ownership' in b for b in self.plan()['blockers']))

    def test_loaded_plugin_and_running_abi_mismatch_block_before_commands(self):
        self.loaded = [{'name': 'hyprbars'}]
        self.assertTrue(self.plan()['blockers'])
        self.loaded = []
        self.running['abiHash'] = 'other'
        self.assertTrue(self.plan()['blockers'])
        self.assertEqual(self.calls, [])

    def test_manager_binary_drift_blocks_without_execution(self):
        reviewed = self.plan()
        with patch.object(migration, 'migration_backend', return_value={'path': '/usr/bin/hyprpm', 'sha256': 'changed'}):
            with self.assertRaisesRegex(ValueError, 'state changed'):
                self.apply(reviewed)
        self.assertEqual(self.calls, [])

    def test_missing_development_packages_block_before_manager_mutation(self):
        self.packages['libcanberra-dev'] = None
        reviewed = self.plan()
        self.assertTrue(any('Missing plugin-build packages' in b for b in reviewed['blockers']))
        with self.assertRaises(ValueError):
            self.apply(reviewed)
        self.assertFalse(self.state.exists())

    def test_already_current_global_abi_is_not_silently_adopted(self):
        self.write_global(self.native['abiHash'])
        self.assertTrue(any('reviewed stale' in b for b in self.plan()['blockers']))

    def test_preapply_drift_has_no_manager_command(self):
        reviewed = self.plan()
        (self.directory / 'hyprland-plugins/hyprbars.so').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'state changed'):
            self.apply(reviewed)
        self.assertEqual(self.calls, [])
        self.assert_no_receipt()

    def test_disable_exit_one_without_enablement_change_is_not_accepted(self):
        def execute(argv):
            self.calls.append(argv)
            raise subprocess.CalledProcessError(1, argv)
        with self.assertRaisesRegex(ValueError, 'Migration stopped'):
            self.apply(execute=execute)
        self.assertEqual(len(self.calls), 1)
        self.assert_no_receipt()
        self.assertTrue(any('Interrupted' in b for b in self.plan()['blockers']))

    def test_disable_other_error_is_not_ignored_even_if_it_changed_enablement(self):
        def execute(argv):
            self.calls.append(argv)
            self.write_repository(legacy=True)
            raise subprocess.CalledProcessError(2, argv)
        with self.assertRaisesRegex(ValueError, 'Migration stopped'):
            self.apply(execute=execute)
        self.assertEqual(len(self.calls), 1)
        self.assert_no_receipt()

    def test_disable_cannot_change_other_cache_bytes(self):
        def execute(argv):
            try:
                self.execute(argv)
            finally:
                (self.directory / 'hyprland-plugins/hyprbars.so').write_bytes(b'unexpected')
        with self.assertRaisesRegex(ValueError, 'Migration stopped'):
            self.apply(execute=execute)
        self.assertEqual(len(self.calls), 1)
        self.assert_no_receipt()

    def test_failed_remove_or_add_stops_without_reenable_restore_or_retry(self):
        def execute(argv):
            if argv[1] == 'remove':
                self.calls.append(argv)
                raise subprocess.CalledProcessError(1, argv)
            self.execute(argv)
        with self.assertRaisesRegex(ValueError, 'no automatic restore or retry'):
            self.apply(execute=execute)
        self.assertEqual([c[1] for c in self.calls], ['disable', 'remove'])
        self.assert_no_receipt()
        state = migration.read_toml(self.directory / 'hyprland-plugins/state.toml')
        self.assertFalse(state['hyprbars']['enabled'])

    def test_header_drift_during_add_cannot_get_a_receipt(self):
        def execute(argv):
            self.execute(argv)
            if argv[1] == 'add':
                (self.directory / 'headersRoot/include/hyprland/src/version.h').write_text('#define GIT_COMMIT_HASH "' + '0' * 40 + '"\n')
        with self.assertRaisesRegex(ValueError, 'Migration stopped'):
            self.apply(execute=execute)
        self.assertEqual([c[1] for c in self.calls], ['disable', 'remove', 'update', 'add'])
        self.assert_no_receipt()

    def test_incomplete_offline_header_exit_one_is_not_accepted(self):
        def execute(argv):
            if argv[1] == 'update':
                self.calls.append(argv)
                raise subprocess.CalledProcessError(1, argv)
            self.execute(argv)
        with self.assertRaisesRegex(ValueError, 'Migration stopped'):
            self.apply(execute=execute)
        self.assertEqual([c[1] for c in self.calls], ['disable', 'remove', 'update'])
        self.assert_no_receipt()

    def test_plugin_appearing_during_offline_refresh_is_left_alone(self):
        def execute(argv):
            try:
                self.execute(argv)
            finally:
                if argv[1] == 'update':
                    self.loaded = [{'name': 'external'}]
        with self.assertRaisesRegex(ValueError, 'Migration stopped'):
            self.apply(execute=execute)
        self.assertEqual([c[1] for c in self.calls], ['disable', 'remove', 'update'])
        self.assertEqual(self.loaded, [{'name': 'external'}])
        self.assert_no_receipt()

    def test_real_executor_cannot_apply_a_plan_for_fixture_paths(self):
        reviewed = self.plan()
        with patch.object(migration.subprocess, 'run') as run, self.assertRaisesRegex(ValueError, 'canonical system paths'):
            migration.apply(reviewed, manager.guided.digest(reviewed), replace_approved=True, inspect=self.inspect)
        run.assert_not_called()
        self.assertFalse(self.state.exists())

    def test_new_build_must_remain_disabled(self):
        def execute(argv):
            self.execute(argv)
            if argv[1] == 'add':
                self.write_repository(enabled=True)
        with self.assertRaisesRegex(ValueError, 'Migration stopped'):
            self.apply(execute=execute)
        self.assert_no_receipt()

    def test_plugin_appearing_after_a_command_stops_without_unloading_it(self):
        def execute(argv):
            try:
                self.execute(argv)
            finally:
                self.loaded = [{'name': 'external'}]
        with self.assertRaisesRegex(ValueError, 'Migration stopped'):
            self.apply(execute=execute)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.loaded, [{'name': 'external'}])
        self.assert_no_receipt()

    def test_packages_changing_during_authentication_stop_the_migration(self):
        def execute(argv):
            try:
                self.execute(argv)
            finally:
                self.packages['gcc'] = '2.0'
        with self.assertRaisesRegex(ValueError, 'Migration stopped'):
            self.apply(execute=execute)
        self.assertEqual(len(self.calls), 1)
        self.assert_no_receipt()

    def test_policy_change_during_authentication_stops_before_replacement(self):
        reviewed = self.plan()
        changed = json.loads(json.dumps(self.source))
        changed['evidence'].append('fixture policy change')
        with patch.object(manager, 'policy', return_value=self.source) as policy:
            def execute(argv):
                try:
                    self.execute(argv)
                finally:
                    policy.return_value = changed
            with self.assertRaisesRegex(ValueError, 'Migration stopped'):
                self.apply(reviewed, execute=execute)
        self.assertEqual(len(self.calls), 1)
        self.assert_no_receipt()

    def test_backup_verifies_archive_bytes_not_only_source_prestate(self):
        original = manager.tarfile.TarFile.add
        changed = False
        def add(archive, path, **kwargs):
            nonlocal changed
            if str(path).endswith('/hyprbars.so') and not changed:
                Path(path).write_bytes(b'raced during backup')
                changed = True
            return original(archive, path, **kwargs)
        with patch.object(manager.tarfile.TarFile, 'add', add), self.assertRaisesRegex(ValueError, 'backup failed'):
            self.apply()
        self.assertEqual(self.calls, [])
        self.assert_no_receipt()


if __name__ == '__main__':
    unittest.main()
