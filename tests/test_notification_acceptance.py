"""Artifact-bound native acceptance refusals, without native/host processes."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import notification_deployment as deploy


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.bundle=Path(self.tmp.name)
        self.path=self.bundle/'native/notification-acceptance';self.path.mkdir(parents=True)
        (self.bundle/'native/notification-runtime').mkdir()
        (self.bundle/'helpers').mkdir();(self.bundle/'helpers/notification_session.py').write_bytes(b'helper')
        (self.bundle/'runtime/bin').mkdir(parents=True);(self.bundle/'runtime/bin/quickshell').write_bytes(b'binary')
        self.sources={'NotificationHost.qml':'fixture-source'}
        (self.bundle/'native/notification-runtime/notifications.json').write_text(json.dumps({'staged':self.sources}))
        self.proof={'scope':'omabuntu-notification-live-prerequisites-v1','passed':True,'sources':self.sources,'reports':{}}
        for name in ('history','render','input','process','host'):
            checker=self.path/(name+'-checker.py');checker.write_text(name)
            row={'status':'native-original-notifications-passed' if name=='render' else 'passed','inputs_unchanged':True,
                 'notification_sources':self.sources,'runtime_sha256':hashlib.sha256(b'binary').hexdigest(),
                 'checker_sha256':hashlib.sha256(checker.read_bytes()).hexdigest(),
                 'returncode':0,'children_reaped':True,'checks':[{'passed':True}]}
            if name=='render':row['cases']=[{'status':'passed','returncode':0,'children_reaped':True,'inputs_unchanged':True,'checks':[{'passed':True}]} for _ in range(2)]
            if name=='host':row.update(fixture_kind='native-session-host-admission',claim_verified=True,
                admission_checker_sha256=row['checker_sha256'],session_helper_sha256=hashlib.sha256(b'helper').hexdigest(),checks=[{'passed':True} for _ in range(4)])
            self.save(name,row)
        self.save_proof()

    def save_proof(self):(self.bundle/'native/notification-acceptance.json').write_text(json.dumps(self.proof))
    def save(self,name,row):
        p=self.path/(name+'.json');p.write_text(json.dumps(row));self.proof['reports'][name]=hashlib.sha256(p.read_bytes()).hexdigest()
    def row(self,name):return json.loads((self.path/(name+'.json')).read_text())

    def test_complete_receipts_pass(self):self.assertTrue(deploy.validate_acceptance(self.bundle)['passed'])

    def test_missing_or_changed_receipt_refuses(self):
        p=self.path/'history.json';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(ValueError):deploy.validate_acceptance(self.bundle)
        p.unlink()
        with self.assertRaises(ValueError):deploy.validate_acceptance(self.bundle)

    def test_even_resealed_failed_foreign_or_variant_receipts_refuse(self):
        for field,value in [('status','failed'),('returncode',1),('children_reaped',False),('inputs_unchanged',False),('notification_sources',{}),('runtime_sha256','wrong'),('variant','diagnostic-only')]:
            original=self.row('history');row=dict(original);row[field]=value;self.save('history',row);self.save_proof()
            with self.assertRaises(ValueError):deploy.validate_acceptance(self.bundle)
            self.save('history',original);self.save_proof()

    def test_incomplete_host_or_wrong_helper_refuses(self):
        original=self.row('host')
        for field,value in [('claim_verified',False),('checks',[]),('session_helper_sha256','wrong'),('fixture_kind','minimal-control')]:
            row=dict(original);row[field]=value;self.save('host',row);self.save_proof()
            with self.assertRaises(ValueError):deploy.validate_acceptance(self.bundle)

    def test_changed_checker_refuses(self):
        (self.path/'input-checker.py').write_text('changed')
        with self.assertRaises(ValueError):deploy.validate_acceptance(self.bundle)

    def test_failed_render_case_refuses(self):
        row=self.row('render');row['cases'][0]['inputs_unchanged']=False;self.save('render',row);self.save_proof()
        with self.assertRaises(ValueError):deploy.validate_acceptance(self.bundle)


if __name__=='__main__':unittest.main()
