"""Plugin artifact tests: fake compiler/probes, never load a real library."""
import copy
import hashlib
import io
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
import build_plugin as plugin
import build_runtime
import package_user

MODULES = dict(zip(plugin.MODULES, ('0.15.1', '0.14.3', '0.5.1', '0.1.13', '0.6.8')))
ABI = plugin.legacy.HYPRLAND_COMMIT + '_aq_0.15_hu_0.14_hg_0.5_hc_0.1_hlg_0.6'
TARGET = {'version': '0.56.2', 'commit': plugin.legacy.HYPRLAND_COMMIT, 'abi_hash': ABI,
          'modules': MODULES, 'requires': ['aquamarine >= 0.15.1'],
          'metadata': {'version': '0.56.2', 'commit': plugin.legacy.HYPRLAND_COMMIT,
                       'dirty': False, 'abiHash': ABI, 'commit_message': 'quote " and \\ newline\n'}}


class NativePluginTests(unittest.TestCase):
    def test_native_target_matches_official_client_hash_algorithm(self):
        def pkg(*args):
            return MODULES[args[1]] if args[0] == '--modversion' else 'aquamarine >= 0.15.1'
        with patch.object(plugin.legacy, 'installed_version', return_value=TARGET['metadata']), patch.object(plugin, 'pkg', side_effect=pkg):
            self.assertEqual(plugin.native_target()['abi_hash'], ABI)
        changed = dict(TARGET['metadata'], abiHash='different')
        with patch.object(plugin.legacy, 'installed_version', return_value=changed), patch.object(plugin, 'pkg', side_effect=pkg):
            with self.assertRaisesRegex(build_runtime.BuildError, 'compositor ABI'):
                plugin.native_target()

    def test_version_header_escapes_metadata_and_rejects_new_placeholders(self):
        text = plugin.version_header('#define MSG "@GIT_COMMIT_MESSAGE@"\n#define N @AQUAMARINE_VERSION_MAJOR@', TARGET)
        self.assertIn(r'quote \" and \\ newline\n', text)
        self.assertIn('#define N 0', text)
        with self.assertRaises(build_runtime.BuildError):
            plugin.version_header('@UNKNOWN@', TARGET)

    def test_export_probe_requires_defined_global_functions(self):
        text = '\n'.join('1: 00001 10 FUNC GLOBAL DEFAULT 12 ' + name for name in plugin.EXPORTS)
        self.assertTrue(plugin.exported(text))
        self.assertFalse(plugin.exported(text.replace('DEFAULT 12', 'DEFAULT UND')))


class PluginBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'upstream').mkdir()
        shutil.copyfile(ROOT / 'upstream/hyprbars-build.json', self.root / 'upstream/hyprbars-build.json')
        self.pin = plugin.inputs(ROOT)
        (self.root / 'licenses').mkdir()
        for item in self.pin['sources']:
            shutil.copyfile(ROOT / item['license']['notice_path'], self.root / item['license']['notice_path'])
        p = patch.object(plugin, 'native_target', return_value=copy.deepcopy(TARGET))
        p.start()
        self.addCleanup(p.stop)

    def stage(self):
        workspace = self.root / 'work/plugin-builds/fixture'
        prefix = workspace / 'stage' / plugin.PREFIX.lstrip('/')
        (prefix / 'lib').mkdir(parents=True)
        (prefix / 'lib/libhyprbars.so').write_bytes(b'fixture; never executed\n' * 1000)
        (prefix / 'licenses').mkdir()
        for item in self.pin['sources']:
            shutil.copyfile(self.root / item['license']['notice_path'], prefix / 'licenses' / Path(item['license']['notice_path']).name)
        (prefix / 'licenses/Protocol-notices.txt').write_text('Fixture protocol notices')
        report = {'schema_version': 1, 'status': 'staged-and-checked', 'source_pin': self.pin,
                  'native_target': TARGET, 'loaded': False, 'config_applied': False,
                  'protocols': ['/source/fixture.xml'],
                  'steps': [{'name': name, 'status': 'passed'} for name in sorted(plugin.BASE_STEPS | {'protocol-0'})],
                  'protocol_notices_sha256': build_runtime.digest(prefix / 'licenses/Protocol-notices.txt'),
                  'artifacts': build_runtime.artifact_manifest(workspace / 'stage')}
        (workspace / 'report.json').write_text(json.dumps(report))
        return workspace, prefix

    def test_pin_records_verified_archives_and_both_bsd_notices(self):
        self.assertEqual(sum(item['archive_bytes'] for item in self.pin['sources']), 50845475)
        for item in self.pin['sources']:
            self.assertEqual(len(item['archive_sha256']), 64)
        path = self.root / self.pin['sources'][0]['license']['notice_path']
        path.write_text('changed license')
        with self.assertRaises(build_runtime.BuildError):
            plugin.inputs(self.root)

    def test_packaging_copies_inert_library_descriptor_and_notices(self):
        workspace, prefix = self.stage()
        destination = self.root / 'bundle'
        package_user.stage_plugin(self.root, destination, workspace)
        self.assertEqual((destination / 'native/hyprbars.so').read_bytes(), (prefix / 'lib/libhyprbars.so').read_bytes())
        self.assertEqual((destination / 'native/hyprbars.so').stat().st_mode & 0o777, 0o444)
        descriptor = plugin.verify_bundle_plugin(destination)
        self.assertEqual(descriptor['activation'], 'not-configured')
        self.assertEqual(len(list((destination / 'licenses/hyprbars').iterdir())), 3)
        (destination / 'native/hyprbars.so').chmod(0o600)
        (destination / 'native/hyprbars.so').write_bytes(b'changed')
        with self.assertRaisesRegex(build_runtime.BuildError, 'ABI differ'):
            plugin.verify_bundle_plugin(destination)

    def test_stage_drift_missing_probe_and_extra_files_are_refused(self):
        workspace, prefix = self.stage()
        record = workspace / 'report.json'
        data = json.loads(record.read_text())
        data['steps'].pop()
        record.write_text(json.dumps(data))
        with self.assertRaises(build_runtime.BuildError):
            plugin.verify_stage(self.root, workspace)

    def test_native_abi_drift_refuses_staging(self):
        workspace, _ = self.stage()
        with patch.object(plugin, 'native_target', return_value=dict(TARGET, abi_hash='changed')):
            with self.assertRaises(build_runtime.BuildError):
                plugin.verify_stage(self.root, workspace)

    def test_sandbox_failure_is_journaled_before_any_download(self):
        with patch.object(plugin.shutil, 'which', return_value='/usr/bin/fixture'), \
             patch.object(plugin.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)), \
             patch.object(plugin, 'obtain') as obtain:
            with self.assertRaises(build_runtime.BuildError):
                plugin.build(self.root)
        obtain.assert_not_called()
        report = json.loads(next((self.root / 'work/plugin-builds').glob('*/report.json')).read_text())
        self.assertEqual(report['status'], 'failed')
        self.assertFalse(report['loaded'])

    def test_build_success_runs_only_sandbox_tools_and_preserves_pristine_sources(self):
        def extract(archive, destination, item):
            source = destination / item['archive_root']
            source.mkdir()
            shutil.copyfile(self.root / item['license']['notice_path'], source / 'LICENSE')
            if item['name'] == 'Hyprland':
                (source / 'src').mkdir()
                (source / 'src/version.h.in').write_text('#define HASH "@GIT_COMMIT_HASH@"\n')
                (source / 'protocols').mkdir()
                (source / 'protocols/fixture.xml').write_text('<protocol/>')
            return source
        commands = []
        def run(argv, **kwargs):
            self.assertIn('--unshare-all', argv)
            self.assertIn('--clearenv', argv)
            self.assertNotIn('/run/user', argv)
            command = argv[argv.index('--') + 1:]
            commands.append(command)
            self.assertIn(command[0], ('/usr/bin/true', 'hyprwayland-scanner', 'cmake', 'readelf', 'ldd'))
            if command[:2] == ['cmake', '--install']:
                workspace = next((self.root / 'work/plugin-builds').iterdir())
                file = workspace / 'stage' / plugin.PREFIX.lstrip('/') / 'lib/libhyprbars.so'
                file.parent.mkdir(parents=True)
                file.write_bytes(b'fixture never executed' * 1000)
            if command[0] == 'readelf':
                text = {'-h': 'DYN X86-64', '-l': 'DYNAMIC', '-d': 'Shared library: [libstdc++.so.6]',
                        '--dyn-syms': '\n'.join('1: 0001 10 FUNC GLOBAL DEFAULT 12 ' + name for name in plugin.EXPORTS)}[command[1]]
                kwargs['stdout'].write(text)
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(plugin.shutil, 'which', return_value='/usr/bin/fixture'), \
             patch.object(plugin, 'pkg', return_value='/usr/share/omabuntu-fixture-no-system-data'), \
             patch.object(plugin, 'protocol_notice', return_value='Fixture copyright\n'), \
             patch.object(plugin, 'obtain', return_value=self.root / 'fake-archive'), \
             patch.object(plugin.builder, 'extract_source', side_effect=extract), \
             patch.object(plugin.subprocess, 'run', side_effect=run):
            report = plugin.build(self.root, jobs=2, target=TARGET)
        workspace, _, record = plugin.verify_stage(self.root, report.parent)
        self.assertEqual(record['status'], 'staged-and-checked')
        self.assertFalse(record['loaded'])
        self.assertFalse((workspace / 'sources' / self.pin['sources'][1]['archive_root'] / 'src/version.h').exists())
        self.assertTrue((workspace / 'build/headers/hyprland/src/version.h').is_file())
        self.assertNotIn(['hyprctl', 'plugin', 'load'], commands)

    def test_approved_native_target_drift_stops_before_workspace_creation(self):
        with self.assertRaises(build_runtime.BuildError):
            plugin.build(self.root, target=dict(TARGET, abi_hash='old'))
        self.assertFalse((self.root / 'work').exists())

    def test_existing_build_output_and_temp_collision_are_preserved(self):
        work = plugin.user_install.private_directory(self.root / 'work')
        parent = plugin.user_install.private_directory(work / 'plugin-builds')
        existing = plugin.user_install.private_directory(parent / 'collision')
        (existing / 'keep').write_text('existing output')
        with patch.object(plugin.user_install, 'stamp', return_value='collision'), \
             patch.object(plugin.shutil, 'which', return_value='/usr/bin/fixture'), self.assertRaises(FileExistsError):
            plugin.build(self.root)
        self.assertEqual((existing / 'keep').read_text(), 'existing output')
        self.assertFalse((existing / 'report.json').exists())
        cache = work / 'source-cache'
        (cache / '.download-collision').write_text('existing temporary file')
        data = b'fixture archive'
        item = dict(self.pin['sources'][0], archive_bytes=len(data), archive_sha256=hashlib.sha256(data).hexdigest())
        with patch.object(plugin.user_install, 'stamp', return_value='collision'), \
             patch.object(plugin.urllib.request, 'build_opener') as opener, self.assertRaises(FileExistsError):
            opener.return_value.open.return_value = io.BytesIO(data)
            plugin.obtain(item, cache)
        self.assertEqual((cache / '.download-collision').read_text(), 'existing temporary file')

    def test_bad_cache_is_retained_without_download_or_reseal(self):
        cache = self.root / 'cache'
        cache.mkdir()
        item = self.pin['sources'][0]
        file = cache / (item['name'] + '-' + item['commit'] + '.tar.gz')
        file.write_bytes(b'user cache data')
        with patch.object(plugin.urllib.request, 'build_opener') as opener, self.assertRaises(build_runtime.BuildError):
            plugin.obtain(item, cache)
        opener.assert_not_called()
        self.assertEqual(file.read_bytes(), b'user cache data')

    def test_double_slash_pkgconfig_path_is_normalized_before_use(self):
        self.assertEqual(plugin.system_share('//usr/share/wayland-protocols'), Path('/usr/share/wayland-protocols'))
        with self.assertRaises(build_runtime.BuildError):
            plugin.system_share('/tmp')

    def test_protocol_copyright_is_preserved_and_missing_notice_blocks(self):
        path = self.root / 'protocol.xml'
        path.write_text('<protocol><copyright>Copyright fixture. Permission text.</copyright></protocol>')
        self.assertIn('Copyright fixture. Permission text.', plugin.protocol_notice(path))
        path.write_text('<protocol/>')
        with self.assertRaises(build_runtime.BuildError):
            plugin.protocol_notice(path)

    def test_library_symlink_and_unknown_stage_file_are_refused(self):
        workspace, prefix = self.stage()
        path = prefix / 'lib/libhyprbars.so'
        data = path.read_bytes()
        path.unlink()
        path.symlink_to(self.root / 'other')
        with self.assertRaises(build_runtime.BuildError):
            plugin.verify_stage(self.root, workspace)
        path.unlink()
        path.write_bytes(data)
        (prefix / 'unexpected').write_text('not part of the plugin')
        report_path = workspace / 'report.json'
        report = json.loads(report_path.read_text())
        report['artifacts'] = build_runtime.artifact_manifest(workspace / 'stage')
        report_path.write_text(json.dumps(report))
        with self.assertRaisesRegex(build_runtime.BuildError, 'Unexpected plugin stage files'):
            plugin.verify_stage(self.root, workspace)
