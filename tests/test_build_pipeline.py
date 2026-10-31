"""Source-to-release contracts: no real compiler, capture, network or desktop."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bootstrap_build as pipeline
import bootstrap_packages
import build_omasnap
import build_runtime
import user_install
import package_user


class OmasnapBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'upstream').mkdir()
        (self.root / 'upstream/omasnap-source.json').write_bytes((ROOT / 'upstream/omasnap-source.json').read_bytes())
        self.pin = build_omasnap.inputs(ROOT)
        (self.root / 'licenses').mkdir()
        for _, record in build_omasnap.notices(self.pin):
            shutil.copyfile(ROOT / record['notice_path'], self.root / record['notice_path'])

    def stage(self):
        workspace = self.root / 'work/omasnap-builds/test'
        prefix = workspace / 'stage' / build_omasnap.PREFIX.lstrip('/')
        (prefix / 'bin').mkdir(parents=True)
        binary = prefix / 'bin/omasnap'
        binary.write_bytes(b'fixture binary; never executed')
        binary.chmod(0o755)
        notices = prefix / 'share/licenses/omasnap'
        notices.mkdir(parents=True)
        for _, record in build_omasnap.notices(self.pin):
            shutil.copyfile(ROOT / record['notice_path'], notices / Path(record['notice_path']).name)
        report = {'schema_version': 1, 'source_pin': self.pin, 'status': 'staged-and-checked',
                  'capture': False, 'installed': False,
                  'steps': [{'name': name, 'status': 'passed'} for name in
                            ('sandbox-preflight', 'configure', 'compile', 'stage', 'elf', 'linkage', 'version')],
                  'artifacts': build_runtime.artifact_manifest(workspace / 'stage')}
        (workspace / 'report.json').write_text(json.dumps(report))
        return workspace, binary

    def test_pin_has_verified_archive_and_annotation_fonts(self):
        self.assertEqual(self.pin['archive_bytes'], 6050541)
        self.assertEqual(len(self.pin['annotation_font_sha256']), 3)
        self.assertEqual(len(self.pin['archive_sha256']), 64)

    def test_verify_stage_checks_pinned_evidence_and_notice_bytes(self):
        workspace, binary = self.stage()
        _, prefix, report = build_omasnap.verify_stage(self.root, workspace)
        self.assertEqual(prefix / 'bin/omasnap', binary)
        self.assertFalse(report['capture'])
        binary.write_bytes(b'changed')
        with self.assertRaisesRegex(build_runtime.BuildError, 'artifacts changed'):
            build_omasnap.verify_stage(self.root, workspace)

    def test_packaging_embeds_verified_binary_and_all_notices(self):
        workspace, binary = self.stage()
        output = self.root / 'bundle'
        package_user.stage_screenshot(self.root, output, workspace)
        copied = output / 'runtime/bin/omasnap'
        self.assertEqual(copied.read_bytes(), binary.read_bytes())
        self.assertEqual(copied.stat().st_mode & 0o777, 0o755)
        for _, record in build_omasnap.notices(self.pin):
            notice = output / 'licenses/omasnap' / Path(record['notice_path']).name
            self.assertEqual(hashlib.sha256(notice.read_bytes()).hexdigest(), record['sha256'])

    def test_missing_probe_or_linked_stage_is_refused(self):
        workspace, binary = self.stage()
        record = workspace / 'report.json'
        data = json.loads(record.read_text())
        data['steps'].pop()
        record.write_text(json.dumps(data))
        with self.assertRaises(build_runtime.BuildError):
            build_omasnap.verify_stage(self.root, workspace)

    def test_source_notices_and_fonts_must_match_before_build(self):
        source = self.root / 'source'
        source.mkdir()
        pin = copy.deepcopy(self.pin)
        for relative, record in build_omasnap.notices(pin):
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / record['notice_path'], target)
        for relative in pin['annotation_font_sha256']:
            target = source / relative
            target.write_bytes(b'font fixture')
            pin['annotation_font_sha256'][relative] = hashlib.sha256(b'font fixture').hexdigest()
        build_omasnap.validate_source(self.root, source, pin)
        (source / 'assets/Neucha.ttf').write_bytes(b'tampered')
        with self.assertRaisesRegex(build_runtime.BuildError, 'annotation font differs'):
            build_omasnap.validate_source(self.root, source, pin)

    def test_sandbox_failure_is_recorded_before_download(self):
        with patch.object(build_omasnap.shutil, 'which', return_value='/usr/bin/fixture'), \
             patch.object(build_omasnap.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)), \
             patch.object(build_runtime, 'fetch_archive') as fetch:
            with self.assertRaises(build_runtime.BuildError):
                build_omasnap.build(self.root)
        fetch.assert_not_called()
        reports = list((self.root / 'work/omasnap-builds').glob('*/report.json'))
        self.assertEqual(len(reports), 1)
        self.assertEqual(json.loads(reports[0].read_text())['status'], 'failed')

    def test_invalid_jobs_never_start_a_build(self):
        with self.assertRaises(build_runtime.BuildError):
            build_omasnap.build(self.root, jobs=0)
        self.assertFalse((self.root / 'work').exists())

    def test_heartbeat_returns_the_command_result_without_waiting(self):
        result = build_runtime.run_with_heartbeat('fixture', lambda: 'done', interval=30)
        self.assertEqual(result, 'done')

    def test_isolation_has_no_session_or_network_access(self):
        workspace = self.root / 'example'
        command = build_runtime.sandbox_command(workspace, ['/usr/bin/true'], workspace / 'sources')
        self.assertIn('--unshare-all', command)
        self.assertIn('--clearenv', command)
        self.assertNotIn('/run/user', command)
        self.assertNotIn('--share-net', command)
        self.assertIn('offscreen', command)


class BuildPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = {'schema_version': 1, 'kind': 'omabuntu-source-build', 'root': str(self.root),
                     'jobs': 2, 'artwork': False, 'version': 'fixture', 'input_digest': 'a' * 64,
                     'blockers': [], 'status': 'review-required', 'inputs': {'plugin_target': {'abi_hash': 'fixture'}}}
        self.output = self.root / 'work/user-releases/fixture'
        self.runtime = self.root / 'work/builds/runtime/report.json'
        self.capture = self.root / 'work/omasnap-builds/capture/report.json'
        self.plugin = self.root / 'work/plugin-builds/plugin/report.json'
        patches = [patch.object(pipeline, 'ROOT', self.root),
                   patch.object(pipeline, 'create_plan', return_value=self.plan),
                   patch.object(pipeline.build_runtime, 'build', return_value=self.runtime),
                   patch.object(pipeline.check_runtime, 'run_checks', return_value={'status': 'isolated-imports-passed'}),
                   patch.object(pipeline.build_omasnap, 'build', return_value=self.capture),
                   patch.object(pipeline.build_omasnap, 'verify_stage'),
                   patch.object(pipeline.package_user, 'prepare', side_effect=self.package),
                   patch.object(pipeline.user_install, 'verify_bundle', return_value={'version': 'fixture'}),
                   patch.object(pipeline.guided, 'preflight', return_value=({'status': 'passed'}, self.root / 'probe')),
                   patch.object(pipeline.desktop_font, 'obtain', return_value=self.root / 'cached-font.ttf'),
                   patch.object(pipeline.build_plugin, 'build', return_value=self.plugin),
                   patch.object(pipeline.build_plugin, 'verify_stage'),
                   patch.object(pipeline.build_plugin, 'verify_bundle_plugin')]
        self.mocks = [item.start() for item in patches]
        for item in patches:
            self.addCleanup(item.stop)

    def package(self, *args, **kwargs):
        self.output.mkdir(parents=True)
        return self.output

    def apply(self):
        return pipeline.apply(self.plan, pipeline.guided.digest(self.plan))

    def test_one_verified_stage_is_reused_and_several_are_not(self):
        runtime = self.root / 'work/builds/only'
        (runtime / 'logs').mkdir(parents=True)
        (runtime / 'report.json').write_text('{}')
        calls = []
        def verify(path):
            calls.append(path.name)
        self.assertEqual(pipeline.one_verified(runtime.parent, verify), runtime)
        second = self.root / 'work/builds/also'
        second.mkdir()
        (second / 'report.json').write_text('{}')
        self.assertIsNone(pipeline.one_verified(runtime.parent, verify))
        parent = self.root / 'work/plugin-builds'
        parent.mkdir()
        (parent / 'linked').symlink_to(runtime)
        self.assertIsNone(pipeline.one_verified(parent, verify))
        self.assertNotIn('linked', calls)

    def test_pipeline_uses_exact_returned_builds_and_never_deploys(self):
        result = self.apply()
        self.assertEqual(result['status'], 'bundle-prepared-and-checked')
        self.assertFalse(result['installed'])
        self.assertFalse(result['desktop_started'])
        packager = self.mocks[6]
        self.assertEqual(packager.call_args.args, ('fixture', self.runtime.parent))
        self.assertEqual(packager.call_args.kwargs['screenshot_build'], self.capture.parent)
        self.assertEqual(packager.call_args.kwargs['plugin_build'], self.plugin.parent)
        self.assertEqual(packager.call_args.kwargs['build_inputs'], 'a' * 64)

    def test_runtime_failure_never_builds_capture_or_packages(self):
        self.mocks[3].return_value = {'status': 'failed'}
        with self.assertRaisesRegex(ValueError, 'Runtime checks'):
            self.apply()
        self.mocks[4].assert_not_called()
        self.mocks[6].assert_not_called()
        self.assertEqual(json.loads(next((self.root / 'work/bootstrap').glob('build-*/build.json')).read_text())['status'], 'failed')

    def test_source_input_drift_stops_packaging(self):
        changed = dict(self.plan, input_digest='b' * 64)
        self.mocks[1].side_effect = [self.plan, changed]
        with self.assertRaisesRegex(ValueError, 'inputs or installed dependencies changed'):
            self.apply()
        self.mocks[6].assert_not_called()

    def test_plugin_failure_never_packages_or_deploys(self):
        self.mocks[10].side_effect = build_runtime.BuildError('fixture plugin failure')
        with self.assertRaises(build_runtime.BuildError):
            self.apply()
        self.mocks[6].assert_not_called()
        self.assertFalse(self.output.exists())

    def test_approval_is_checked_before_any_build(self):
        with self.assertRaises(ValueError):
            pipeline.apply(self.plan, 'wrong')
        self.mocks[2].assert_not_called()
        self.assertFalse((self.root / 'work').exists())

    def test_existing_matching_bundle_is_verified_not_rebuilt(self):
        (self.output / 'runtime/bin').mkdir(parents=True)
        (self.output / 'runtime/bin/omasnap').write_bytes(b'fixture')
        (self.output / 'native').mkdir()
        (self.output / 'native/hyprbars.so').write_bytes(b'fixture')
        (self.output / 'PROVENANCE.json').write_text(json.dumps({'bootstrap_input_sha256': 'a' * 64}))
        self.assertEqual(self.apply()['status'], 'verified-existing-bundle')
        self.mocks[2].assert_not_called()
        self.mocks[4].assert_not_called()

    def test_existing_version_collision_does_not_rebuild_or_overwrite(self):
        self.output.mkdir(parents=True)
        (self.output / 'PROVENANCE.json').write_text('{"bootstrap_input_sha256":"different"}')
        with self.assertRaisesRegex(ValueError, 'different build inputs'):
            self.apply()
        self.mocks[2].assert_not_called()


class BuildPlanTests(unittest.TestCase):
    def test_plan_is_repeatable_and_missing_dependencies_block(self):
        state = {'installed': {}, 'manual': [], 'held': []}
        with patch.object(pipeline.bootstrap_sources, 'host_check'):
            first = pipeline.create_plan(state=state)
            second = pipeline.create_plan(state=state)
        self.assertEqual(first, second)
        self.assertTrue(first['blockers'])
        self.assertTrue(first['version'].startswith('source-'))
        self.assertIn('no plugin/config deployment', first['scope'])
