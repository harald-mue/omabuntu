"""Pinned manager plans and explicit activation using private fixtures only."""
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import plugin_manager as manager


class PluginManagerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.directory = self.home / 'manager'
        self.state = self.home / '.local/state/omabuntu'
        self.source = manager.policy()
        self.target = self.source['targets']['0.56.2']
        self.native = {'version': '0.56.2', 'commit': self.target['hyprland_commit'], 'dirty': False, 'abiHash': 'fixture-abi'}
        self.running = {'commit': self.native['commit'], 'flags': [], 'abiHash': 'fixture-abi'}
        include = self.home / 'include'
        include.mkdir()
        (include / 'lua.h').write_text('fixture')
        for mock in (patch.dict(os.environ, {'XDG_STATE_HOME': str(self.home / '.local/state')}, clear=False),
                     patch.object(manager.shutil, 'which', return_value='/fixture'),
                     patch.object(manager.omabuntu_hyprpm, 'LUA_INCLUDE', include),
                     patch.object(manager.build_hyprbars, 'installed_version', return_value=self.native),
                     patch.object(manager.os, 'getuid', return_value=self.home.stat().st_uid)):
            mock.start()
            self.addCleanup(mock.stop)
        self.loaded = []
        self.commands = []

    def inspect(self, argv):
        return json.dumps(self.running if 'version' in argv else self.loaded)

    def plan(self, action='prepare'):
        return manager.plan(ROOT, self.home, action, directory=self.directory, inspect=self.inspect,
                            shared_pkgconfig=self.home / 'shared-hyprland.pc')

    def write_repository(self, enabled=False, other=False):
        path = self.directory / ('other' if other else 'hyprland-plugins')
        path.mkdir(parents=True, exist_ok=True)
        (path / 'state.toml').write_text(
            '[repository]\nname = "hyprland-plugins"\nurl = ' + json.dumps(self.source['repository']) + '\n'
            'rev = ' + json.dumps(self.target['plugin_commit']) + '\n'
            'hash = ' + json.dumps(self.target['plugin_commit']) + '\n'
            '[hyprbars]\nfilename = "hyprbars.so"\nenabled = ' + str(enabled).lower() + '\nfailed = false\n')
        (path / 'hyprbars.so').write_bytes(b'fixture-built-library')

    def execute(self, argv):
        self.commands.append(argv)
        if argv[1] == 'update':
            pc = self.directory / 'headersRoot/share/pkgconfig/hyprland.pc'
            version = self.directory / 'headersRoot/include/hyprland/src/version.h'
            for path in (pc, version):
                path.parent.mkdir(parents=True, exist_ok=True)
            pc.write_text('prefix=' + str(self.directory / 'headersRoot/include') + '\nVersion: ' + self.native['version'] + '\n')
            version.write_text('#define GIT_COMMIT_HASH "' + self.native['commit'] + '"\n#define GIT_DIRTY "clean"\n')
            (self.directory / 'state.toml').write_text('[state]\nhash="fixture-abi"\n')
            raise subprocess.CalledProcessError(1, argv)
        elif argv[1] == 'add':
            self.write_repository()
        elif argv[1] == 'enable':
            self.write_repository(enabled=True)
            self.loaded = [{'name': 'hyprbars'}]

    def apply(self, reviewed):
        # Tests do not execute the root guard with the container's root identity.
        with patch.object(manager.os, 'getuid', return_value=self.home.stat().st_uid), \
             patch.dict(os.environ, {}, clear=False):
            return manager.apply(reviewed, manager.guided.digest(reviewed), execute=self.execute, inspect=self.inspect)

    def test_plan_is_read_only_and_uses_exact_revision(self):
        plan = self.plan()
        self.assertFalse(plan['blockers'])
        self.assertFalse(self.directory.exists())
        self.assertFalse(self.state.exists())
        self.assertEqual(plan['commands'][1], ['hyprpm', 'add', self.source['repository'], self.target['plugin_commit']])
        self.assertFalse(plan['loads_plugin'])

    def test_wrong_running_or_unreviewed_target_is_blocked(self):
        self.running['commit'] = 'f' * 40
        self.assertTrue(any('running Hyprland differ' in b for b in self.plan()['blockers']))
        new = self.source['targets']['0.57.0']
        self.native.update(version='0.57.0', commit=new['hyprland_commit'])
        self.running['commit'] = new['hyprland_commit']
        self.assertFalse(self.plan()['blockers'])
        self.native['version'] = '0.58.0'
        self.assertTrue(any('not approved' in b for b in self.plan()['blockers']))

    def test_current_target_prepares_and_activates_its_own_exact_revision(self):
        self.target = self.source['targets']['0.57.0']
        self.native.update(version='0.57.0', commit=self.target['hyprland_commit'])
        self.running['commit'] = self.native['commit']
        self.assertEqual(self.apply(self.plan())['status'], 'plugin-prepared')
        self.assertEqual(self.commands[-1][-1], self.target['plugin_commit'])
        self.assertEqual(self.apply(self.plan('activate'))['status'], 'plugin-loaded')

    def test_any_loaded_plugin_blocks_load_state_reconciliation(self):
        self.loaded = [{'name': 'unrelated-native-plugin'}]
        self.assertTrue(any('could be unloaded' in b for b in self.plan()['blockers']))

    def test_existing_unowned_or_enabled_repository_is_not_adopted(self):
        self.write_repository(enabled=True)
        blockers = self.plan()['blockers']
        self.assertTrue(any('Enabled manager plugins' in b for b in blockers))
        self.assertTrue(any('no matching Omabuntu receipt' in b for b in blockers))

    def test_unrelated_repository_and_symlinks_are_refused(self):
        self.write_repository(other=True)
        self.assertTrue(any('Unmanaged' in b for b in self.plan()['blockers']))
        (self.directory / 'escape').symlink_to(self.home / 'include', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            self.plan()

    def test_prepare_backs_up_and_never_enables_then_activation_is_separate(self):
        reviewed = self.plan()
        result = self.apply(reviewed)
        self.assertEqual(result['status'], 'plugin-prepared')
        self.assertFalse(result['plugin_loaded'])
        self.assertEqual([c[1] for c in self.commands], ['update', 'add'])
        self.assertTrue(Path(result['journal']).with_name('manager-before.tar').is_file())
        activate = self.plan('activate')
        self.assertFalse(activate['blockers'])
        self.assertEqual(activate['commands'], [['hyprpm', 'enable', 'hyprbars']])
        result = self.apply(activate)
        self.assertTrue(result['plugin_loaded'])
        self.assertFalse(result['configuration_reloaded'])
        self.assertFalse(result['autostart_changed'])

    def test_shared_system_metadata_is_backed_up_before_official_header_install(self):
        path = self.home / 'shared-hyprland.pc'
        path.write_text('original pkg-config metadata')
        reviewed = self.plan()
        def execute(argv):
            path.write_text('manager-generated metadata')
            self.execute(argv)
        result = manager.apply(reviewed, manager.guided.digest(reviewed), execute=execute, inspect=self.inspect)
        case = Path(result['journal']).parent
        self.assertEqual((case / 'system-hyprland.pc.before').read_text(), 'original pkg-config metadata')
        saved = json.loads(Path(result['journal']).read_text())
        self.assertNotEqual(saved['shared_pkgconfig_after'], reviewed['shared_pkgconfig_before'])
        self.assertFalse(saved['automatic_restore'])

    def test_update_child_cannot_reconcile_live_plugins(self):
        with patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE': 'fixture-session'}), \
             patch.object(manager.subprocess, 'run') as run:
            manager.execute(['hyprpm', 'update'])
            self.assertNotIn('HYPRLAND_INSTANCE_SIGNATURE', run.call_args.kwargs['env'])
            self.assertEqual(run.call_args.args[0], ['/usr/bin/hyprpm', 'update'])
            self.assertEqual(os.environ['HYPRLAND_INSTANCE_SIGNATURE'], 'fixture-session')

    def test_nonconvergent_update_exit_one_cannot_issue_a_receipt(self):
        reviewed = self.plan()
        def fail(argv):
            self.commands.append(argv)
            raise subprocess.CalledProcessError(1, argv)
        with self.assertRaisesRegex(ValueError, 'backup and journal'):
            manager.apply(reviewed, manager.guided.digest(reviewed), execute=fail, inspect=self.inspect)
        self.assertEqual(len(self.commands), 1)
        self.assertFalse((self.state / 'hyprpm.json').exists())

    def test_plugin_appearing_during_header_refresh_is_not_unloaded(self):
        reviewed = self.plan()
        def execute(argv):
            try:
                self.execute(argv)
            finally:
                self.loaded = [{'name': 'external'}]
        with self.assertRaisesRegex(ValueError, 'backup and journal'):
            manager.apply(reviewed, manager.guided.digest(reviewed), execute=execute, inspect=self.inspect)
        self.assertEqual([c[1] for c in self.commands], ['update'])
        self.assertEqual(self.loaded, [{'name': 'external'}])
        self.assertFalse((self.state / 'hyprpm.json').exists())

    def test_real_executor_refuses_fixture_paths_before_any_command(self):
        reviewed = self.plan()
        with patch.object(manager.subprocess, 'run') as run, self.assertRaisesRegex(ValueError, 'canonical system paths'):
            manager.apply(reviewed, manager.guided.digest(reviewed), inspect=self.inspect)
        run.assert_not_called()

    def test_preparation_always_records_verified_headers(self):
        self.apply(self.plan())
        receipt = json.loads((self.state / 'hyprpm.json').read_text())
        self.assertEqual(receipt['headers']['layout'], 'cache')
        header = self.directory / 'headersRoot/include/hyprland/src/version.h'
        header.write_text('#define GIT_COMMIT_HASH "wrong"\n')
        self.assertTrue(self.plan('activate')['blockers'])

    def test_malformed_enablement_is_rejected_before_activation(self):
        self.apply(self.plan())
        path = self.directory / 'hyprland-plugins/state.toml'
        path.write_text(path.read_text().replace('enabled = false', 'enabled = "false"'))
        self.assertTrue(any('Malformed' in item for item in self.plan('activate')['blockers']))

    def test_failed_new_plugin_output_cannot_issue_receipt(self):
        reviewed = self.plan()
        def execute(argv):
            self.execute(argv)
            if argv[1] == 'add':
                path = self.directory / 'hyprland-plugins/state.toml'
                path.write_text(path.read_text().replace('failed = false', 'failed = true'))
        with self.assertRaisesRegex(ValueError, 'backup and journal'):
            manager.apply(reviewed, manager.guided.digest(reviewed), execute=execute, inspect=self.inspect)
        self.assertFalse((self.state / 'hyprpm.json').exists())

    def test_bad_approval_or_manager_drift_cannot_execute(self):
        reviewed = self.plan()
        with self.assertRaises(ValueError):
            manager.apply(reviewed, 'wrong', execute=self.execute, inspect=self.inspect)
        self.write_repository()
        with self.assertRaisesRegex(ValueError, 'state changed'):
            self.apply(reviewed)
        self.assertEqual(self.commands, [])

    def test_failed_manager_operation_keeps_backup_and_blocks_retry(self):
        reviewed = self.plan()
        def fail(argv):
            raise ValueError('fixture failure')
        with self.assertRaisesRegex(ValueError, 'backup and journal'):
            manager.apply(reviewed, manager.guided.digest(reviewed), execute=fail, inspect=self.inspect)
        self.assertTrue(any('Interrupted' in b for b in self.plan()['blockers']))
        self.assertTrue(list((self.state / 'plugin-transactions').glob('*/manager-before.tar')))

    def test_activation_requires_successful_unchanged_manager_receipt(self):
        self.assertTrue(any('Prepare and verify' in b for b in self.plan('activate')['blockers']))
        self.apply(self.plan())
        (self.directory / 'hyprland-plugins/hyprbars.so').write_bytes(b'changed')
        self.assertTrue(any('Prepare and verify' in b for b in self.plan('activate')['blockers']))

    def test_packaging_stages_only_the_reviewed_manager_policy(self):
        import package_user
        bundle = self.home / 'bundle'
        bundle.mkdir()
        package_user.stage_manager_policy(ROOT, bundle)
        self.assertEqual(manager.bundle_policy(bundle), self.source)
        self.assertFalse((bundle / 'native/hyprbars.so').exists())
        self.assertFalse((bundle / 'native/hyprbars.json').exists())
        self.assertEqual((bundle / 'native/hyprpm.json').stat().st_mode & 0o777, 0o444)

    def test_bundle_cannot_mix_two_plugin_owners(self):
        bundle = self.home / 'bundle'
        native = bundle / 'native'
        native.mkdir(parents=True)
        (native / 'hyprpm.json').write_text(json.dumps(self.source))
        self.assertEqual(manager.bundle_policy(bundle), self.source)
        (native / 'hyprbars.so').write_bytes(b'legacy')
        with self.assertRaisesRegex(ValueError, 'mix'):
            manager.bundle_policy(bundle)


if __name__ == '__main__':
    unittest.main()
