"""Inactive package proof tests use synthetic bytes; never execute a runtime or a bus."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import notification_admission as admission
import notification_frontend
import package_user
import build_notification_runtime
import check_notification_runtime
import check_runtime


class NotificationAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bundle = self.root / 'bundle';self.bundle.mkdir()
        for name, data in notification_frontend.sources(ROOT).items():
            self.put('shell/' + name, data)
        self.put('helpers/notification_admission.py', Path(admission.__file__).read_bytes())
        self.binary = self.put('runtime/bin/quickshell', b'Synthetic executable, never run')
        self.binary.chmod(0o755)
        self.bundle.joinpath('runtime/bin/qs').symlink_to('quickshell')
        self.pin = json.loads((ROOT / 'upstream/notification-runtime.json').read_bytes())
        self.profile = json.loads((ROOT / 'upstream/notifications.json').read_bytes())
        self.put(admission.EVIDENCE['pin'], json.dumps(self.pin).encode())
        self.put(admission.EVIDENCE['profile'], json.dumps(self.profile).encode())
        self.put(admission.EVIDENCE['patch'], (ROOT / 'native/notification-exclusive.patch').read_bytes())
        self.build = {'schema_version':1,'status':'exclusive-notification-candidate-built',
                      'source_lock':{'quickshell':{'commit':admission.QUICKSHELL}},
                      'pin_sha256':admission.digest(self.bundle / admission.EVIDENCE['pin']),
                      'patch_sha256':self.pin['patch_sha256'],'native_source_sha256':self.pin['patched_source_sha256'],
                      'patched_source_sha256':self.pin['patched_source_sha256'],'baseline_unchanged':True,
                      'binary_sha256':admission.digest(self.binary),
                      'artifacts':[{'path':admission.PREFIX+'bin/quickshell','type':'file',
                                    'sha256':admission.digest(self.binary),'bytes':self.binary.stat().st_size},
                                   {'path':admission.PREFIX+'bin/qs','type':'symlink',
                                    'target':'/opt/omabuntu-runtime/bin/quickshell'}]}
        self.bus = {'status':'private-bus-checks-passed','returncode':0,'host_bus_exposed':False,
                    'artifacts_unchanged':True,'checker_sha256':'c'*64,
                    'checks':[{'name':name,'passed':True} for name in admission.CHECKS]}
        self.eligibility = {'schema_version':1,'status':'eligible-for-separate-deployment-review',
                            'binary_sha256':self.build['binary_sha256'],'patch_sha256':self.pin['patch_sha256'],
                            'checker_sha256':'c'*64,'live_deployment_authorized':False}
        self.proof = {'schema_version':1,'scope':'omabuntu-notification-runtime-capability-v1',
                      'role':admission.ROLE,'live_deployment_authorized':False,
                      'validator_sha256':admission.digest(Path(admission.__file__))}
        self.reseal()

    def put(self, relative, data):
        target = self.bundle / relative;target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def reseal(self):
        for key, obj in (('build',self.build),('bus',self.bus)):
            self.put(admission.EVIDENCE[key], json.dumps(obj).encode())
        self.eligibility['build_report_sha256']=admission.digest(self.bundle/admission.EVIDENCE['build'])
        self.eligibility['test_report_sha256']=admission.digest(self.bundle/admission.EVIDENCE['bus'])
        self.put(admission.EVIDENCE['eligibility'], json.dumps(self.eligibility).encode())
        self.proof['evidence']={key:admission.digest(self.bundle/name) for key,name in admission.EVIDENCE.items()}
        self.put(admission.DESCRIPTOR, json.dumps(self.proof).encode())

    def test_exact_relocated_fixture_is_capability_not_deployment_approval(self):
        result=admission.verify(self.bundle)
        self.assertTrue(result['runtime_verified']);self.assertFalse(result['deployment_approved'])
        self.assertEqual(result['role'],admission.ROLE)

    def test_offline_cli_does_not_spawn_or_touch_a_bus(self):
        with patch('subprocess.run',side_effect=AssertionError('No process allowed')):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(admission.main(['--bundle',str(self.bundle)]),0)
        self.assertIs(json.loads(out.getvalue())['deployment_approved'],False)

    def test_missing_proof_is_not_admission(self):
        empty=self.root/'ordinary';empty.mkdir()
        with self.assertRaises(ValueError):admission.verify(empty)

    def test_runtime_byte_change_extra_file_or_missing_execute_bit_refuses(self):
        data=self.binary.read_bytes()
        self.binary.write_bytes(b'changed')
        with self.assertRaises(ValueError):admission.verify(self.bundle)
        self.binary.write_bytes(data)
        extra=self.put('runtime/unreviewed',b'extra')
        with self.assertRaises(ValueError):admission.verify(self.bundle)
        extra.rename(self.root/'preserved-extra')
        self.binary.chmod(0o644)
        with self.assertRaises(ValueError):admission.verify(self.bundle)

    def test_source_and_packaged_verifier_tampering_refuse(self):
        for relative in ('shell/NotificationHost.qml','shell/Notifications/Toast.qml','helpers/notification_admission.py'):
            with self.subTest(relative=relative):
                path=self.bundle/relative;old=path.read_bytes();path.write_bytes(old+b'\n')
                with self.assertRaises(ValueError):admission.verify(self.bundle)
                path.write_bytes(old)

    def test_changed_patch_or_receipt_refuses(self):
        for key in ('patch','bus','eligibility','pin'):
            with self.subTest(key=key):
                path=self.bundle/admission.EVIDENCE[key];old=path.read_bytes();path.write_bytes(old+b'\n')
                with self.assertRaises(ValueError):admission.verify(self.bundle)
                path.write_bytes(old)

    def test_resealed_incomplete_or_failed_bus_results_are_not_capability(self):
        original=list(self.bus['checks'])
        for rows in (original[:-1],list(reversed(original)),[dict(row,passed=False) for row in original]):
            with self.subTest(rows=rows):
                self.bus['checks']=rows;self.reseal()
                with self.assertRaises(ValueError):admission.verify(self.bundle)

    def test_resealed_host_bus_exposure_or_initial_build_failure_refuses(self):
        for key, value in (('host_bus_exposed',True),('returncode',1),('artifacts_unchanged',False)):
            with self.subTest(key=key):
                old=self.bus[key];self.bus[key]=value;self.reseal()
                with self.assertRaises(ValueError):admission.verify(self.bundle)
                self.bus[key]=old
        self.build['baseline_unchanged']=False;self.reseal()
        with self.assertRaises(ValueError):admission.verify(self.bundle)

    def test_even_resealed_receipts_cannot_grant_live_role(self):
        self.eligibility['live_deployment_authorized']=True;self.reseal()
        with self.assertRaises(ValueError):admission.verify(self.bundle)
        self.eligibility['live_deployment_authorized']=False
        self.proof['live_deployment_authorized']=True;self.reseal()
        with self.assertRaises(ValueError):admission.verify(self.bundle)

    def test_resealed_missing_source_digest_is_not_complete_evidence(self):
        self.pin.pop('patched_source_sha256')
        self.build.pop('native_source_sha256');self.build.pop('patched_source_sha256')
        self.put(admission.EVIDENCE['pin'],json.dumps(self.pin).encode())
        self.build['pin_sha256']=admission.digest(self.bundle/admission.EVIDENCE['pin'])
        self.reseal()
        with self.assertRaisesRegex(ValueError,'complete notification'):
            admission.verify(self.bundle)

    def test_alias_tampering_refuses(self):
        alias=self.bundle/'runtime/bin/qs';alias.rename(self.root/'original-alias')
        alias.symlink_to('/opt/omabuntu-runtime/bin/quickshell')
        with self.assertRaises(ValueError):admission.verify(self.bundle)

    def test_symlinked_or_hardlinked_proof_input_refuses(self):
        path=self.bundle/admission.EVIDENCE['bus'];saved=self.root/'bus-evidence';path.rename(saved)
        path.symlink_to(saved)
        with self.assertRaises(ValueError):admission.verify(self.bundle)
        path.rename(self.root/'symlink-evidence');os.link(saved,path)
        with self.assertRaises(ValueError):admission.verify(self.bundle)

    def test_relocation_whitelist_refuses_path_escape_or_arbitrary_symlinks(self):
        for record in ({'path':'../elsewhere','type':'file'},
                       {'path':admission.PREFIX+'../elsewhere','type':'file'},
                       {'path':admission.PREFIX+'lib/foreign','type':'symlink','target':'/usr/lib/foreign'}):
            with self.subTest(record=record),self.assertRaises(ValueError):admission.relocated_artifacts([record])

    def test_normal_selection_does_not_consult_variant_or_enable_host(self):
        with patch.object(check_runtime,'verify_stage',return_value=(self.root,self.bundle,{})), \
             patch.object(build_notification_runtime,'verify') as verify:
            self.assertEqual(admission.select_runtime(ROOT,self.root),(self.root,self.bundle,None))
            verify.assert_not_called()
        host=(ROOT/'config/shell/preview/NotificationHost.qml').read_text()
        self.assertIn('property bool deploymentApproved: false',host)
        self.assertIn('property bool exclusiveRuntimeVerified: false',host)

    def test_variant_requires_successful_eligibility_and_matching_parent(self):
        (self.root/'report.json').write_text('{}')
        report={'baseline':str(self.root/'wrong-parent'),'baseline_report_sha256':'x','baseline_artifacts':[]}
        with patch.object(check_runtime,'verify_stage',return_value=(self.root,self.bundle,{'artifacts':[]})), \
             patch.object(build_notification_runtime,'verify',return_value=(self.root,self.bundle,report)), \
             patch.object(check_notification_runtime,'eligibility') as eligibility:
            with self.assertRaisesRegex(ValueError,'selected baseline'):
                admission.select_runtime(ROOT,self.root,self.root/'variant')
            eligibility.assert_called_once()
            report.update(baseline=str(self.root),baseline_report_sha256=admission.digest(self.root/'report.json'))
            self.assertEqual(admission.select_runtime(ROOT,self.root,self.root/'variant'),(self.root,self.bundle,self.root))
            eligibility.side_effect=ValueError('Unverified candidate')
            with self.assertRaisesRegex(ValueError,'Unverified candidate'):
                admission.select_runtime(ROOT,self.root,self.root/'variant')

    def test_packager_cli_requires_explicit_variant_selection(self):
        with patch.object(package_user,'prepare') as prepare,patch.object(package_user.os,'umask'):
            package_user.main(['--version','review-fixture','--build-dir','baseline'])
            self.assertIsNone(prepare.call_args.kwargs['notification_runtime'])
            package_user.main(['--version','review-fixture','--build-dir','baseline','--notification-runtime','variant'])
            self.assertEqual(prepare.call_args.kwargs['notification_runtime'],Path('variant'))


if __name__=='__main__':unittest.main()
