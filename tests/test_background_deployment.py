"""Upgrade refuses competing providers and unrelated recovery state."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import background_deployment as upgrade


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ops = upgrade.Upgrade.__new__(upgrade.Upgrade)
        self.ops.mask = self.root / 'mask'
        self.ops.unit = MagicMock(return_value={'ActiveState': 'inactive', 'UnitFileState': 'masked-runtime'})

    def test_default_is_plan_only_without_host_inspection(self):
        with patch.object(upgrade, 'Upgrade', side_effect=AssertionError('No live constructor')), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(upgrade.main(['--bundle', '/not-installed']), 0)

    def test_existing_runtime_fence_is_only_validated(self):
        self.ops.mask.symlink_to('/dev/null')
        with patch.object(upgrade.live, 'command', side_effect=AssertionError('No service command')):
            self.ops.fence_provider()
        self.assertEqual(os.readlink(self.ops.mask), '/dev/null')

    def test_missing_foreign_or_active_fence_refused(self):
        with self.assertRaises(ValueError): self.ops.fence_provider()
        self.ops.mask.symlink_to('/different-target')
        with self.assertRaises(ValueError): self.ops.fence_provider()
        self.ops.mask.unlink(); self.ops.mask.symlink_to('/dev/null')
        self.ops.unit.return_value['ActiveState'] = 'active'
        with self.assertRaises(ValueError): self.ops.fence_provider()

    def test_competing_owner_never_stopped_replaced_or_queued(self):
        with patch.object(upgrade.live, 'owner', return_value=':foreign'), patch.object(upgrade.live, 'command', side_effect=AssertionError('No activation/stop')):
            with self.assertRaises(ValueError): self.ops.stop_provider()
        with patch.object(upgrade.live, 'owner', return_value=None): self.ops.stop_provider()

    def test_role_requires_actual_admission_readiness_and_boolean_quiet(self):
        for row in ({'admitted': False, 'ready': True, 'quiet': False}, {'admitted': True, 'ready': False, 'quiet': False}, {'admitted': True, 'ready': True, 'quiet': 1}):
            with patch.object(upgrade.live, 'command', return_value=json.dumps(row)):
                with self.assertRaises(ValueError): self.ops.role(self.root)
        valid = {'admitted': True, 'ready': True, 'quiet': False}
        with patch.object(upgrade.live, 'command', return_value=json.dumps(valid)):
            self.assertEqual(self.ops.role(self.root), valid)

    def test_recovery_wrong_session_refuses_before_any_mutation(self):
        self.ops.data = {'session_sha256': 'previous-session'}
        self.ops.reload = MagicMock()
        with patch.dict(os.environ, {'XDG_RUNTIME_DIR': '/fixture'}), patch.object(upgrade.session, 'session_digest', return_value='different-session'):
            with self.assertRaisesRegex(ValueError, 'different compositor'): self.ops.recover()
        self.ops.reload.assert_not_called()

    def test_recovery_modified_backup_refuses_before_reload_or_stop(self):
        self.ops.directory = self.root
        p = self.root / 'saved'; p.write_text('changed'); p.chmod(0o600)
        self.ops.data = {'session_sha256': 'fixture', 'backups': [{'backup': 'saved', 'sha256': 'different', 'mode': 0o600}]}
        self.ops.reload = MagicMock()
        with patch.dict(os.environ, {'XDG_RUNTIME_DIR': '/fixture'}), patch.object(upgrade.session, 'session_digest', return_value='fixture'):
            with self.assertRaisesRegex(ValueError, 'backup integrity'): self.ops.recover()
        self.ops.reload.assert_not_called()

    def test_recovery_unrelated_same_release_pid_is_never_stopped(self):
        self.ops.data = {'session_sha256': 'fixture', 'backups': [], 'old': {'pid': 1}, 'attempt': {'pid': 2, 'identity': {'start_ticks': 'owned'}}}
        self.ops.adapter = None; self.ops.reload = MagicMock(); self.ops.app = MagicMock()
        self.ops.app.running.return_value = {'pid': 3, 'identity': {'start_ticks': 'unrelated'}}
        with patch.dict(os.environ, {'XDG_RUNTIME_DIR': '/fixture'}), patch.object(upgrade.session, 'session_digest', return_value='fixture'):
            with self.assertRaisesRegex(ValueError, 'Unrelated shell'): self.ops.recover()
        self.ops.app.stop.assert_not_called(); self.ops.app.restore.assert_not_called()

    def test_overlay_scope_excludes_notification_runtime_audio_and_monitors(self):
        self.assertEqual(len(upgrade.SOURCES), 8)
        for path in upgrade.SOURCES:
            self.assertFalse(any(word in path.lower() for word in ('notification', 'audio', 'display', 'runtime', 'manager.py')))


if __name__ == '__main__': unittest.main()
