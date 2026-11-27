"""Stopped restart is a separate, exact captured-session admission path."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import background_deployment as upgrade


class StoppedRestartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name); o = self.ops = upgrade.RestartCrashed.__new__(upgrade.RestartCrashed)
        o.root = root / 'install'; o.state = root / 'state'; o.target = 'releases/base'
        base = o.root / o.target; base.mkdir(parents=True); (base / 'release.json').write_text('sealed synthetic artifact')
        o.prior_journal = o.state / 'background-migrations/prior'; o.prior_journal.mkdir(parents=True, mode=0o700)
        grant_dir = o.prior_journal / 'grant'; grant_dir.mkdir(mode=0o700)
        capture = o.state / 'runs/old/native-capture'; capture.mkdir(parents=True)
        o.session_digest = 'same-session'; o.app = MagicMock(); o.app.running.return_value = None
        argv = upgrade.session.argv(base)
        self.record = {'pid': 1234, 'identity': {'start_ticks': '1', 'argv': argv}, 'release': o.target,
                       'log': str(capture.parent / 'output.log'), 'lifetime': 'session', 'autostart': False}
        self.proof = {'schema_version': 1, 'scope': upgrade.session.SCOPE, 'lifetime': 'session',
                      'bundle': str(base), 'release_sha256': upgrade.capability.digest(base / 'release.json'),
                      'capability_sha256': 'synthetic', 'session_sha256': o.session_digest, 'argv': argv, 'nonce': 'b' * 64}
        self.prior = {'scope': upgrade.SCOPE, 'status': 'completed', 'bundle_sha256': self.proof['release_sha256'],
                      'session_sha256': o.session_digest, 'grant_nonce': self.proof['nonce'],
                      'result': {'shell': self.record, 'capture': {'directory': str(capture),
                                  'debugger': {'pid': 456}, 'supervisor': {'pid': 789}}}}
        self.put(o.state / 'running.json', self.record)
        self.put(o.prior_journal / 'journal.json', self.prior)
        self.put(grant_dir / 'grant.json', self.proof)
        self.put(grant_dir / 'claim.json', {'nonce': self.proof['nonce'], 'pid': 1234, 'identity': self.record['identity']})
        self.put(capture / 'ready.json', {'pid': 1234, 'identity': self.record['identity']})
        self.put(capture / 'supervisor-finished.json', {'status': 'debugger-exited', 'debugger_returncode': 0})
        self.put(capture / 'gdb-finished.json', {'fatal_signal': 'SIGSEGV'})
        self.identity = patch.object(upgrade.deployment, 'identity', return_value=None)
        self.identity.start(); self.addCleanup(self.identity.stop)

    def put(self, path, data):
        path.write_text(json.dumps(data)); path.chmod(0o600)

    def test_exact_dead_session_and_completed_capture_are_admitted_without_starting(self):
        self.ops.validate_prior()
        self.assertEqual(self.ops.old, self.record)
        self.ops.app.start.assert_not_called(); self.ops.app.stop.assert_not_called()

    def test_other_session_is_refused(self):
        self.ops.session_digest = 'different-session'
        with self.assertRaisesRegex(ValueError, 'session/grant'): self.ops.validate_prior()

    def test_stale_record_change_is_refused(self):
        changed = dict(self.record, pid=9999); self.put(self.ops.state / 'running.json', changed)
        with self.assertRaisesRegex(ValueError, 'record/prior artifact'): self.ops.validate_prior()

    def test_changed_prior_artifact_is_refused(self):
        (self.ops.root / self.ops.target / 'release.json').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'artifact identity'): self.ops.validate_prior()

    def test_wrong_parent_claim_is_refused(self):
        path = self.ops.prior_journal / 'grant/claim.json'
        claim = json.loads(path.read_text()); claim['pid'] = 9999; self.put(path, claim)
        with self.assertRaisesRegex(ValueError, 'parent claim'): self.ops.validate_prior()

    def test_reused_pid_and_live_debugger_are_refused(self):
        for pid in (1234, 456, 789):
            with patch.object(upgrade.deployment, 'identity', side_effect=lambda p: {'occupied': True} if p == pid else None):
                with self.assertRaises(ValueError): self.ops.validate_prior()

    def test_nonfatal_or_incomplete_capture_is_refused(self):
        directory = Path(self.prior['result']['capture']['directory'])
        self.put(directory / 'gdb-finished.json', {'fatal_signal': None})
        with self.assertRaisesRegex(ValueError, 'completed fatal capture'): self.ops.validate_prior()

    def test_competing_shell_owner_or_lookup_failure_is_refused(self):
        with patch.object(upgrade.live, 'owner', return_value=':competing'):
            with self.assertRaises(ValueError): self.ops.require_absent()
        self.ops.app.running.return_value = {'pid': 7}
        with patch.object(upgrade.live, 'owner', return_value=None):
            with self.assertRaises(ValueError): self.ops.require_absent()
        self.ops.app.running.return_value = None
        with patch.object(upgrade.live, 'owner', return_value=None), patch.object(upgrade.live.subprocess, 'run') as run:
            for code in (0, 2):
                run.return_value.returncode = code
                with self.assertRaises(ValueError): self.ops.require_absent()
            run.return_value.returncode = 1; self.ops.require_absent()

    def test_restart_failure_does_not_restore_crashing_release_or_activate_provider(self):
        self.ops.adapter = None; self.ops.data = {}; self.ops.save = MagicMock()
        with patch.object(upgrade.live, 'command', side_effect=AssertionError('No service mutation')):
            self.ops.recover()
        self.ops.app.start.assert_not_called(); self.ops.app.restore.assert_not_called()
        self.assertEqual(self.ops.data['status'], 'failed-stopped-no-fallback')


if __name__ == '__main__': unittest.main()
