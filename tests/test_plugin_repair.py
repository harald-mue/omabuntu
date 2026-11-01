"""Repair fixtures never load a compositor plugin or change the host."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import native_transition
import plugin_repair as repair
import setup as frontend
import user_install
import test_native_transition as evidence_fixtures


class PluginRepairTests(unittest.TestCase):
    bundle = evidence_fixtures.NativeEvidenceTests.bundle
    inspect = evidence_fixtures.NativeEvidenceTests.inspect

    def setUp(self):
        evidence_fixtures.NativeEvidenceTests.setUp(self)
        self.app.install(self.b)
        self.receipt.update(activated=True, schema_version=1, headers={'layout': 'fixture-headers'})
        user_install.atomic_json(self.app.state / 'hyprpm.json', self.receipt)
        self.repo = self.directory / 'hyprland-plugins/state.toml'
        self.repo.write_text(self.repo.read_text().replace('enabled=false', 'enabled=true'))
        self.calls = []
        self.backend = {'path': '/usr/bin/hyprpm', 'sha256': 'fixture'}
        patcher = patch.object(repair.plugin_migration, 'migration_backend', side_effect=lambda: dict(self.backend))
        patcher.start()
        self.addCleanup(patcher.stop)
        metadata = repair.manager.metadata_state
        patcher = patch.object(repair.manager, 'metadata_state', side_effect=lambda path:
                               {'existed': False} if Path(path) == Path('/usr/share/pkgconfig/hyprland.pc') else metadata(path))
        patcher.start()
        self.addCleanup(patcher.stop)

    def plan(self):
        return repair.plan(ROOT, self.app, self.directory, self.inspect)

    def execute(self, argv):
        self.calls.append(argv)
        self.loaded = [{'name': 'hyprbars'}]

    def apply(self, reviewed, execute=None):
        return repair.apply(reviewed, repair.manager.guided.digest(reviewed),
                            execute=execute or self.execute, inspect=self.inspect)

    def test_missing_plugin_is_repaired_with_backups_and_no_persistent_change(self):
        reviewed = self.plan()
        self.assertFalse(reviewed['blockers'])
        self.assertEqual(reviewed['changes'], ['load-hyprbars'])
        before = (self.app.state / 'hyprpm.json').read_bytes(), self.repo.read_bytes()
        result = self.apply(reviewed)
        self.assertEqual(result['status'], 'repaired-and-loaded')
        self.assertEqual(self.calls, [['hyprpm', 'reload']])
        self.assertEqual(before, ((self.app.state / 'hyprpm.json').read_bytes(), self.repo.read_bytes()))
        journal = Path(result['journal'])
        record = user_install.read_json(journal)
        self.assertTrue(record['backup_verified'])
        self.assertEqual(record['status'], 'completed')
        self.assertTrue((journal.parent / 'manager-before.tar').is_file())
        self.assertFalse(result['configuration_reloaded'])
        self.assertFalse(result['login_changed'])

    def test_strict_native_handoff_still_rejects_the_missing_plugin(self):
        with self.assertRaisesRegex(ValueError, 'Live plugin'):
            native_transition.manager_ready(self.policy, self.app.state, inspect=self.inspect, directory=self.directory)

    def test_loaded_plugin_needs_no_reload(self):
        self.loaded = [{'name': 'hyprbars'}]
        result = self.apply(self.plan())
        self.assertEqual(result['status'], 'already-loaded')
        self.assertEqual(self.calls, [])

    def test_unreceipted_foreign_or_failed_states_do_not_offer_repair(self):
        self.receipt['activated'] = False
        user_install.atomic_json(self.app.state / 'hyprpm.json', self.receipt)
        self.assertTrue(self.plan()['blockers'])
        self.receipt['activated'] = True
        user_install.atomic_json(self.app.state / 'hyprpm.json', self.receipt)
        self.loaded = [{'name': 'foreign'}]
        self.assertTrue(self.plan()['blockers'])
        self.loaded = []
        self.repo.write_text(self.repo.read_text().replace('failed=false', 'failed=true'))
        self.assertTrue(self.plan()['blockers'])
        self.assertEqual(self.calls, [])

    def test_unresolved_other_transaction_cannot_be_ignored(self):
        reviewed = self.plan()
        path = self.app.state / 'plugin-transactions/other/transaction.json'
        path.parent.mkdir(parents=True)
        user_install.atomic_json(path, {'status': 'manual-review-required'})
        with self.assertRaises(ValueError):
            self.apply(reviewed)
        self.assertEqual(self.calls, [])

    def test_library_or_backend_drift_prevents_execution(self):
        reviewed = self.plan()
        self.backend['sha256'] = 'changed'
        with self.assertRaises(ValueError):
            self.apply(reviewed)
        self.backend['sha256'] = 'fixture'
        Path(self.receipt['library']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            self.apply(reviewed)
        self.assertEqual(self.calls, [])

    def test_failed_or_nonconvergent_reload_retains_manual_review_journal(self):
        def execute(argv):
            self.calls.append(argv)
        with self.assertRaisesRegex(ValueError, 'no automatic unload/retry'):
            self.apply(self.plan(), execute)
        journal = next((self.app.state / 'plugin-transactions').glob('*/transaction.json'))
        self.assertEqual(user_install.read_json(journal)['status'], 'manual-review-required')
        self.assertEqual(self.calls, [['hyprpm', 'reload']])
        self.assertTrue(self.plan()['blockers'])

    def test_persistent_drift_after_load_does_not_trigger_unload(self):
        def execute(argv):
            self.execute(argv)
            self.repo.write_text(self.repo.read_text() + '\n# external edit\n')
        with self.assertRaisesRegex(ValueError, 'no automatic unload/retry'):
            self.apply(self.plan(), execute)
        self.assertEqual(self.calls, [['hyprpm', 'reload']])
        self.assertEqual(self.loaded, [{'name': 'hyprbars'}])

    def test_tampered_active_backup_journal_cannot_be_skipped(self):
        backup = repair.manager.backup_state
        def tamper(reviewed, state):
            case, journal, record = backup(reviewed, state)
            changed = dict(record, backup_verified=False)
            user_install.atomic_json(journal, changed)
            return case, journal, record
        with patch.object(repair.manager, 'backup_state', side_effect=tamper):
            with self.assertRaisesRegex(ValueError, 'no automatic unload/retry'):
                self.apply(self.plan())
        self.assertEqual(self.calls, [])

    def test_reload_exception_is_retained_without_retry_or_unload(self):
        def execute(argv):
            self.calls.append(argv)
            raise RuntimeError('fixture IPC failure')
        with self.assertRaisesRegex(ValueError, 'no automatic unload/retry'):
            self.apply(self.plan(), execute)
        self.assertEqual(self.calls, [['hyprpm', 'reload']])
        journal = next((self.app.state / 'plugin-transactions').glob('*/transaction.json'))
        self.assertEqual(user_install.read_json(journal)['failure'], 'RuntimeError')

    def test_real_executor_cannot_run_fixture_paths(self):
        reviewed = self.plan()
        with self.assertRaisesRegex(ValueError, 'canonical'):
            repair.apply(reviewed, repair.manager.guided.digest(reviewed), inspect=self.inspect)

    def test_json_or_digest_cannot_bypass_live_consent(self):
        reviewed = self.plan()
        with patch.object(frontend.plugin_repair, 'plan', return_value=reviewed), \
             patch.object(frontend.plugin_repair, 'apply') as apply, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = frontend.main(['--plugins-repair', '--apply', '--json', '--approve',
                                    repair.manager.guided.digest(reviewed)])
        self.assertEqual(result, 1)
        apply.assert_not_called()

    def test_declining_one_live_repair_prompt_never_loads(self):
        reviewed = self.plan()
        with patch.object(frontend.plugin_repair, 'plan', return_value=reviewed), \
             patch.object(frontend.plugin_repair, 'apply') as apply, \
             patch.object(frontend.sys.stdin, 'isatty', return_value=True), \
             patch.object(frontend.setup_ui, 'confirm', return_value=False) as confirm, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(frontend.main(['--plugins-repair', '--apply']), 0)
        confirm.assert_called_once()
        apply.assert_not_called()
