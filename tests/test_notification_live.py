"""Recovery uses only synthetic files and injected host operations."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import notification_live as live
import notification_session as session
import notification_deployment as deploy


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.ops=live.Live.__new__(live.Live)
        o=self.ops;o.root=root/'install';o.state=root/'state';o.state.mkdir();o.bundle=root/'bundle';o.bundle.mkdir()
        (o.bundle/'release.json').write_text('{"version":"next"}')
        o.directory=root/'backup';o.directory.mkdir(mode=0o700)
        o.launcher=root/'launcher';o.launcher.write_text('original')
        o.pre={'current':'releases/base','previous':'releases/previous','launcher_sha256':hashlib.sha256(b'original').hexdigest()}
        o.data={'old':{'pid':123},'events':[],'quiet':True,'quiet_existed':False}
        o.mask=root/'runtime-mask';o.adapter=None;o.reload=MagicMock();o.save=MagicMock();o.manager=MagicMock()
        o.app=MagicMock();o.app.running.return_value=o.data['old'];o.app.bootstrap.return_value='original'
        o.app.selected.side_effect=lambda name='current':'releases/base' if name=='current' else 'releases/previous'
        o.unit=MagicMock(return_value={'MainPID':'7'})
        self.cmd=patch.object(live,'command',return_value='').start()
        self.owner=patch.object(live,'owner',return_value=':fixture').start()
        self.dbus=patch.object(live,'dbus',return_value=7).start()
        self.identity=patch.object(live.deployment,'identity',return_value={'argv':['/usr/bin/swaync']}).start()
        self.addCleanup(patch.stopall)

    def test_existing_provider_and_capture_are_not_restarted(self):
        self.ops.recover()
        self.ops.app.stop.assert_not_called();self.ops.app.start.assert_not_called()
        self.cmd.assert_not_called();self.assertEqual(self.ops.data['status'],'restored')

    def test_unrelated_shell_refuses_before_stop(self):
        self.ops.app.running.return_value={'release':'releases/unrelated'}
        with self.assertRaisesRegex(ValueError,'Unrelated shell'):self.ops.recover()
        self.ops.app.stop.assert_not_called();self.ops.app.restore.assert_not_called()

    def test_same_release_with_a_different_pid_is_not_owned(self):
        self.ops.app.running.return_value={'release':'releases/next','pid':456,'identity':{'start_ticks':'new'}}
        self.ops.data['attempt']={'pid':789,'identity':{'start_ticks':'previous'}}
        with self.assertRaisesRegex(ValueError,'Unrelated shell'):self.ops.recover()
        self.ops.app.stop.assert_not_called()

    def test_different_session_refuses_before_live_mutation(self):
        folder=self.ops.directory/'grant';folder.mkdir(mode=0o700);p=folder/'grant.json'
        session.exclusive_json(p,{'session_sha256':'previous-session'})
        self.ops.data['grant']=str(p)
        with patch.object(session,'session_digest',return_value='different-session'):
            with self.assertRaisesRegex(ValueError,'different compositor session'):self.ops.recover()
        self.ops.app.stop.assert_not_called();self.ops.app.restore.assert_not_called();self.cmd.assert_not_called()

    def test_external_selector_or_launcher_edit_refuses_restore(self):
        self.ops.app.selected.side_effect=None;self.ops.app.selected.return_value='releases/unrelated'
        with self.assertRaises(ValueError):self.ops.recover()
        self.ops.app.restore.assert_not_called()
        self.ops.app.selected.side_effect=lambda name='current':'releases/base' if name=='current' else 'releases/previous'
        self.ops.launcher.write_text('external edit')
        with self.assertRaisesRegex(ValueError,'Launcher changed'):self.ops.recover()
        self.ops.app.restore.assert_not_called()

    def test_changed_runtime_fence_is_not_removed(self):
        self.ops.data['events']=['mask-requested'];self.ops.mask.symlink_to('/not-our-fence')
        with self.assertRaisesRegex(ValueError,'fence changed'):self.ops.recover()
        self.cmd.assert_not_called()

    def test_owned_fence_removed_and_verified(self):
        self.ops.data['events']=['mask-requested'];self.ops.mask.symlink_to('/dev/null')
        self.cmd.side_effect=lambda args:self.ops.mask.unlink()
        self.ops.recover();self.assertFalse(self.ops.mask.is_symlink())
        self.cmd.assert_called_once_with(['systemctl','--user','unmask','--runtime','swaync.service'])

    def test_unknown_provider_never_starts_a_competing_fallback(self):
        self.identity.return_value={'argv':['/usr/bin/unrelated-provider']}
        with self.assertRaisesRegex(ValueError,'Unknown provider'):self.ops.recover()
        self.cmd.assert_not_called()

    def test_new_quiet_file_preserved_as_evidence_then_removed(self):
        q=self.ops.state/'notifications';q.mkdir(mode=0o700);p=q/'quiet.json';p.write_text('{"dnd":true}');p.chmod(0o600)
        self.ops.data['events']=['quiet-write-requested'];self.ops.recover()
        self.assertFalse(p.exists());self.assertEqual(json.loads((self.ops.directory/'quiet-after-attempt.json').read_text()),{'dnd':True})

    def test_grant_is_revoked_not_silently_reused(self):
        folder=self.ops.directory/'grant';folder.mkdir(mode=0o700);path=folder/'grant.json'
        session.exclusive_json(path,{'nonce':'fixture','bundle':'fixture-bundle'})
        self.ops.data.update(grant=str(path),grant_nonce='fixture',grant_bundle='fixture-bundle')
        self.ops.recover();self.assertTrue(session.private_json(path)['revoked'])

    def test_changed_backup_refuses_before_any_restore(self):
        p=self.ops.directory/'backup';p.write_text('before');p.chmod(0o600)
        self.ops.data['backups']=[{'backup':'backup','sha256':hashlib.sha256(b'before').hexdigest(),'mode':0o600}]
        p.write_text('changed')
        with self.assertRaisesRegex(ValueError,'backup integrity'):self.ops.recover()
        self.ops.app.restore.assert_not_called();self.cmd.assert_not_called()

    def test_absent_provider_and_shell_restore_in_order_with_capture(self):
        current={'shell':None,'owner':None};events=[]
        self.ops.app.running.side_effect=lambda:current['shell']
        self.owner.side_effect=lambda:current['owner']
        def command(args):
            events.append('provider-start');current['owner']=':restored';return ''
        self.cmd.side_effect=command
        def start(**kwargs):
            events.append('captured-shell-start');current['shell']=self.ops.data['old'];return current['shell']
        self.ops.app.start.side_effect=start
        with patch.object(live,'captured_start') as capture_start,patch.object(live,'capture_identity') as identity,patch.object(live.subprocess,'run',return_value=type('Result',(),{'returncode':1})()):
            self.ops.recover()
        self.assertEqual(events,['provider-start','captured-shell-start'])
        capture_start.assert_called_once();identity.assert_called_once()
        self.ops.app.start.assert_called_once_with(restore_background=False)

    def test_failed_journal_write_still_runs_recovery(self):
        class Ops:
            recovered=False
            def __getattr__(self,name):
                if name in ('install','record_failure'):raise OSError('fixture')
                return lambda *args:None
            def recover(self):self.recovered=True
        ops=Ops()
        with self.assertRaises(OSError):deploy.switch(ops)
        self.assertTrue(ops.recovered)


class CliTests(unittest.TestCase):
    def test_default_does_not_construct_live_operations(self):
        with patch.object(live,'Live') as cls,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(live.main(['--bundle','synthetic']),0)
        cls.assert_not_called()

    def test_overlay_write_preserves_frozen_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'frozen';p.write_text('before');p.chmod(0o444)
            deploy.write_preserved(p,'after')
            self.assertEqual(p.read_text(),'after');self.assertEqual(p.stat().st_mode&0o777,0o444)


if __name__=='__main__':unittest.main()
