"""Variant/eligibility refusal tests; synthetic artifacts, no build or user bus."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_notification_runtime as variant
import check_notification_runtime as native
import build_runtime as builder


class NotificationRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('upstream/notification-runtime.json', 'upstream/source-lock.json',
                     'packages/quickshell-plan.json', 'native/notification-exclusive.patch'):
            target = self.root / name;target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        self.case = self.root / 'work/notification-runtime-builds/fixture'
        runtime = self.case / 'stage' / builder.PREFIX.lstrip('/')
        (runtime / 'bin').mkdir(parents=True)
        (runtime / 'bin/quickshell').write_bytes(b'synthetic artifact, never executed')
        pin, sources = variant.inputs(self.root)
        self.build = {'schema_version':1,'status':variant.STATUS,'source_lock':sources,
                      'patch_sha256':pin['patch_sha256'],'patched_source_sha256':pin['patched_source_sha256'],
                      'native_source_sha256':pin['patched_source_sha256'],
                      'pin_sha256':builder.digest(self.root / variant.PIN),
                      'builder_sha256':builder.digest(Path(variant.__file__)),
                      'baseline_unchanged':True,'shaders':[{'fixture':True}],
                      'steps':[{'name':n,'status':'passed'} for n in (
                          'sandbox-preflight','quickshell-configure','quickshell-build','quickshell-stage','quickshell-version')],
                      'artifacts':builder.artifact_manifest(self.case / 'stage'),
                      'binary_sha256':builder.digest(runtime / 'bin/quickshell')}
        self.save('report.json', self.build)
        self.test = {'status':'private-bus-checks-passed','host_bus_exposed':False,
                     'returncode':0,'artifacts_unchanged':True,
                     'checker_sha256':builder.digest(Path(native.__file__)),
                     'checks':[{'name':name,'passed':True} for name in native.CHECKS]}
        self.save('private-bus-report.json', self.test)
        self.receipt = {'schema_version':1,'status':'eligible-for-separate-deployment-review',
                        'build_report_sha256':builder.digest(self.case / 'report.json'),
                        'test_report_sha256':builder.digest(self.case / 'private-bus-report.json'),
                        'binary_sha256':self.build['binary_sha256'],'patch_sha256':pin['patch_sha256'],
                        'checker_sha256':builder.digest(Path(native.__file__)),
                        'live_deployment_authorized':False}
        self.save('eligibility.json', self.receipt)

    def save(self, name, value):
        (self.case / name).write_text(json.dumps(value) + '\n')

    def reseal_test(self):
        self.save('private-bus-report.json', self.test)
        self.receipt['test_report_sha256'] = builder.digest(self.case / 'private-bus-report.json')
        self.save('eligibility.json', self.receipt)

    def test_plan_defaults_do_not_build_start_bus_or_verify_host(self):
        with patch.object(variant, 'build') as build, patch.object(native, 'run') as run:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(variant.main([]), 0)
                self.assertEqual(native.main([]), 0)
            build.assert_not_called();run.assert_not_called()

    def test_synthetic_exact_receipt_verifies_but_never_authorizes_live(self):
        self.assertIs(native.eligibility(self.root, self.case)['live_deployment_authorized'], False)

    def test_binary_tampering_refuses(self):
        binary = self.case / 'stage' / builder.PREFIX.lstrip('/') / 'bin/quickshell'
        binary.write_bytes(b'changed')
        with self.assertRaisesRegex(builder.BuildError, 'artifacts changed'):
            native.eligibility(self.root, self.case)

    def test_patch_tampering_refuses_before_subprocess(self):
        path = self.root / 'native/notification-exclusive.patch'
        path.write_bytes(path.read_bytes() + b' ')
        with patch.object(variant.subprocess, 'run') as run:
            with self.assertRaises(builder.BuildError):
                variant.verify(self.root, self.case)
            run.assert_not_called()

    def test_inexact_source_refuses_without_patch_execution(self):
        pin, _ = variant.inputs(self.root)
        source = self.root / 'source'
        path = source / pin['source_path'];path.parent.mkdir(parents=True)
        path.write_bytes(b'unreviewed parent')
        with patch.object(variant.subprocess, 'run') as run:
            with self.assertRaisesRegex(builder.BuildError, 'exact pinned parent'):
                variant.patch_source(self.root, source, pin)
            run.assert_not_called()

    def test_incomplete_failed_or_reordered_native_checks_refuse(self):
        original = list(self.test['checks'])
        for rows in (original[:-1], list(reversed(original)),
                     [dict(row, passed=False) if index==2 else row for index,row in enumerate(original)]):
            with self.subTest(rows=rows):
                self.test['checks'] = rows;self.reseal_test()
                with self.assertRaises(builder.BuildError):
                    native.eligibility(self.root, self.case)

    def test_host_bus_exposure_or_changed_stage_refuses_even_with_matching_report_hash(self):
        for key, value in (('host_bus_exposed',True),('artifacts_unchanged',False),('returncode',134)):
            with self.subTest(key=key):
                original = self.test[key];self.test[key]=value;self.reseal_test()
                with self.assertRaises(builder.BuildError):native.eligibility(self.root,self.case)
                self.test[key]=original

    def test_receipt_cannot_grant_live_deployment(self):
        self.receipt['live_deployment_authorized']=True;self.save('eligibility.json',self.receipt)
        with self.assertRaises(builder.BuildError):native.eligibility(self.root,self.case)

    def test_stale_checker_or_test_digest_refuses(self):
        for key in ('checker_sha256','test_report_sha256','binary_sha256','build_report_sha256'):
            with self.subTest(key=key):
                old=self.receipt[key];self.receipt[key]='0'*64;self.save('eligibility.json',self.receipt)
                with self.assertRaises(builder.BuildError):native.eligibility(self.root,self.case)
                self.receipt[key]=old

    def test_symlink_and_out_of_tree_candidates_refuse(self):
        link=self.root/'candidate-link';link.symlink_to(self.case,target_is_directory=True)
        for path in (link,self.root):
            with self.subTest(path=path),self.assertRaises(builder.BuildError):variant.verify(self.root,path)

    def test_partial_build_refuses(self):
        self.build['steps'][2]['status']='timeout';self.save('report.json',self.build)
        with self.assertRaises(builder.BuildError):variant.verify(self.root,self.case)

    def test_driver_is_fixed_syntax_and_has_negative_control_and_no_activation_directories(self):
        compile(native.DRIVER,'private-native-driver','exec')
        self.assertIn('negative control reproduces original late takeover',native.DRIVER)
        self.assertNotIn('servicedir',native.BUS)
        self.assertIn('resource.RLIMIT_CORE',native.DRIVER)
        self.assertIn('missing-bus-fails-closed',native.CHECKS)
        self.assertIn('bus-loss-fails-closed',native.CHECKS)


if __name__=='__main__':unittest.main()
