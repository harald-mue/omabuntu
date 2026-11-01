"""PPA header checkpoint recovery uses private fixtures, never sudo or hyprpm."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import plugin_recovery as recovery
import plugin_login
import test_plugin_migration as fixtures

manager = recovery.manager
migration = recovery.migration


class PluginRecoveryTests(unittest.TestCase):
    write_repository = fixtures.PluginMigrationTests.write_repository
    write_global = fixtures.PluginMigrationTests.write_global
    inspect = fixtures.PluginMigrationTests.inspect
    execute = fixtures.PluginMigrationTests.execute
    plan = fixtures.PluginMigrationTests.plan
    apply = fixtures.PluginMigrationTests.apply
    assert_no_receipt = fixtures.PluginMigrationTests.assert_no_receipt

    def setUp(self):
        fixtures.PluginMigrationTests.setUp(self)
        (self.directory / 'headersRoot').mkdir()

        def historical_execute(argv):
            if argv[1] == 'update':
                self.calls.append(argv)
                self.write_global(self.native['abiHash'])
                raise subprocess.CalledProcessError(1, argv)
            self.execute(argv)

        with patch.object(migration, 'verify_headers', side_effect=ValueError(
                'Manager installed headers or pkg-config file are missing')):
            with self.assertRaisesRegex(ValueError, 'Migration stopped'):
                self.apply(execute=historical_execute)
        self.journal = next((self.state / 'plugin-transactions').glob('*/transaction.json'))
        self.original = self.journal.read_bytes()
        self.calls.clear()
        self.system = {'layout': 'system-package', 'files': {'fixture-version': {'sha256': 'headers'}}}
        mock = patch.object(plugin_login, 'system_headers', return_value=self.system)
        self.system_mock = mock.start()
        self.addCleanup(mock.stop)

    def review(self):
        return recovery.plan(self.journal, ROOT, self.home, self.inspect)

    def recover(self, reviewed=None, execute=None):
        reviewed = self.review() if reviewed is None else reviewed
        return recovery.apply(reviewed, manager.guided.digest(reviewed), resume_approved=True,
                              execute=self.execute if execute is None else execute, inspect=self.inspect)

    def test_review_is_read_only_and_only_plans_missing_add(self):
        before = set((self.state / 'plugin-transactions').iterdir())
        reviewed = self.review()
        self.assertEqual([cmd[1] for cmd in reviewed['commands']], ['add'])
        self.assertEqual(reviewed['headers']['layout'], 'system-package')
        self.assertFalse(reviewed['loads_plugin'])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.journal.read_bytes(), self.original)
        self.assertEqual(set((self.state / 'plugin-transactions').iterdir()), before)

    def test_success_preserves_old_journal_and_links_verified_resolution(self):
        result = self.recover()
        self.assertEqual(result['status'], 'plugin-migrated-disabled')
        self.assertEqual([cmd[1] for cmd in self.calls], ['add'])
        self.assertEqual(self.journal.read_bytes(), self.original)
        self.assertTrue(plugin_login.transaction_complete(self.journal))
        new = Path(result['journal'])
        record = plugin_login.read_json(new)
        self.assertTrue(record['backup_verified'])
        self.assertEqual(record['status'], 'completed')
        self.assertEqual(new.with_name('original-journal.json').read_bytes(), self.original)
        receipt = plugin_login.read_json(self.state / 'hyprpm.json')
        self.assertFalse(receipt['activated'])
        self.assertEqual(receipt['headers'], self.system)
        activation = manager.plan(ROOT, self.home, 'activate', directory=self.directory,
                                  inspect=self.inspect, shared_pkgconfig=self.shared)
        self.assertFalse(activation['blockers'])

    def test_approval_and_extra_consent_are_required(self):
        reviewed = self.review()
        for digest, consent in ((manager.guided.digest(reviewed), False), ('wrong', True)):
            with self.assertRaisesRegex(ValueError, 'approval'):
                recovery.apply(reviewed, digest, resume_approved=consent, execute=self.execute, inspect=self.inspect)
        self.assertFalse(self.calls)

    def test_original_backup_drift_blocks(self):
        self.journal.with_name('manager-before.tar').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'backup changed'):
            self.review()
        self.assertFalse(self.calls)

    def test_unknown_cache_content_or_repository_blocks(self):
        (self.directory / 'foreign').write_text('unknown')
        with self.assertRaisesRegex(ValueError, 'empty-cache checkpoint'):
            self.review()
        self.assertFalse(self.calls)

    def test_foreign_loaded_plugin_blocks(self):
        self.loaded = [{'name': 'external'}]
        with self.assertRaisesRegex(ValueError, 'plugin loaded'):
            self.review()
        self.assertFalse(self.calls)

    def test_header_drift_after_review_has_no_command(self):
        reviewed = self.review()
        self.system_mock.return_value = {'layout': 'system-package', 'files': {'changed': 'headers'}}
        with self.assertRaisesRegex(ValueError, 'inputs changed'):
            self.recover(reviewed)
        self.assertFalse(self.calls)

    def test_other_pending_transaction_blocks(self):
        other = self.journal.parent.parent / 'other/transaction.json'
        other.parent.mkdir()
        other.write_text('{"status":"manual-review-required"}')
        with self.assertRaisesRegex(ValueError, 'Another interrupted'):
            self.review()

    def test_add_failure_has_no_receipt_resolution_or_retry(self):
        def fail(argv):
            self.calls.append(argv)
            raise subprocess.CalledProcessError(1, argv)
        with self.assertRaisesRegex(ValueError, 'Recovery stopped'):
            self.recover(execute=fail)
        self.assertEqual(len(self.calls), 1)
        self.assert_no_receipt()
        self.assertFalse(self.journal.with_name('resolution.json').exists())
        self.assertFalse(plugin_login.transaction_complete(self.journal))
        with self.assertRaisesRegex(ValueError, 'Another interrupted'):
            self.review()

    def test_enabled_build_never_gets_receipt(self):
        def enable(argv):
            self.execute(argv)
            self.write_repository(enabled=True)
        with self.assertRaisesRegex(ValueError, 'Recovery stopped'):
            self.recover(execute=enable)
        self.assert_no_receipt()
        self.assertFalse(self.journal.with_name('resolution.json').exists())

    def test_tampered_resolution_stays_blocked(self):
        self.recover()
        resolution = self.journal.with_name('resolution.json')
        data = plugin_login.read_json(resolution)
        data['original_sha256'] = 'changed'
        resolution.write_text(json.dumps(data))
        self.assertFalse(plugin_login.transaction_complete(self.journal))
        activation = manager.plan(ROOT, self.home, 'activate', directory=self.directory,
                                  inspect=self.inspect, shared_pkgconfig=self.shared)
        self.assertTrue(activation['prerequisite_blockers'])

    def test_changed_completed_recovery_journal_stays_blocked(self):
        result = self.recover()
        path = Path(result['journal'])
        record = plugin_login.read_json(path)
        record['extra'] = 'changed'
        path.write_text(json.dumps(record))
        self.assertFalse(plugin_login.transaction_complete(self.journal))

    def test_original_journal_cannot_be_outside_current_state(self):
        with self.assertRaisesRegex(ValueError, 'current user state'):
            recovery.plan(self.home / 'elsewhere/transaction.json', ROOT, self.home, self.inspect)

    def test_default_executor_refuses_fixture_paths(self):
        reviewed = self.review()
        with patch.object(subprocess, 'run') as run, self.assertRaisesRegex(ValueError, 'canonical system paths'):
            recovery.apply(reviewed, manager.guided.digest(reviewed), resume_approved=True, inspect=self.inspect)
        run.assert_not_called()


class PackagedHeaderTests(unittest.TestCase):
    def setUp(self):
        self.native = {'version': '0.57.0', 'commit': 'a' * 40, 'buildAquamarine': '0.15.1'}
        self.pc = b'prefix=/usr/include\nVersion: 0.57.0\n'
        self.header = ('#define GIT_COMMIT_HASH "' + self.native['commit'] + '"\n'
                       '#define GIT_DIRTY "clean"\n#define AQUAMARINE_VERSION "0.15.1"\n').encode()
        self.facts = {'sha256': 'fixture', 'uid': 0, 'gid': 0, 'mode': 0o644}

    def validate(self, owner='hyprland'):
        with patch.object(plugin_login, 'fingerprint', return_value=self.facts), \
             patch.object(plugin_login, 'regular', side_effect=lambda path, *args: self.pc if path.suffix == '.pc' else self.header):
            return plugin_login.system_headers(self.native, lambda argv: owner + ': ' + argv[-1])

    def test_package_owned_matching_headers_are_accepted(self):
        self.assertEqual(self.validate()['layout'], 'system-package')

    def test_wrong_package_or_writable_inputs_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'owned by'):
            self.validate('foreign-package')
        self.facts['mode'] = 0o666
        with self.assertRaisesRegex(ValueError, 'protected root-owned'):
            self.validate()

    def test_wrong_commit_dependency_and_pc_version_are_refused(self):
        for field, value in (('commit', 'b' * 40), ('buildAquamarine', '0.15.2'), ('version', '0.56.2')):
            with self.subTest(field=field):
                previous = copy.deepcopy(self.native)
                self.native[field] = value
                with self.assertRaises(ValueError):
                    self.validate()
                self.native = previous
