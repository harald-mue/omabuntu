"""Additive bootstrap package tests with an in-memory APT fixture."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bootstrap_packages as packages
import install as guided
import setup as frontend


class FakeAPT:
    def __init__(self, names):
        self.versions = {name: '1.0-1' for name in names}
        self.versions.update(hyprland='0.57.0-1', libqt6core6t64='6.10.2-1', hyprlock='0.9.6-1')
        self.installed = dict(self.versions)
        self.installed.pop('libdeflate-dev')
        self.commands = []
        self.changes = False

    def run(self, command, timeout=30):
        self.commands.append(command)
        if command[0] == 'dpkg-query':
            output = ''.join('%s\t%s\tinstalled\n' % item for item in sorted(self.installed.items()))
        elif command == ['apt-mark', 'showmanual']:
            output = '\n'.join(sorted(self.installed)) + '\n'
        elif command == ['apt-mark', 'showhold']:
            output = ''
        elif command[:2] == ['apt-cache', 'policy']:
            output = ''.join('%s:\n  Installed: %s\n  Candidate: %s\n' %
                             (name, self.installed.get(name, '(none)'), self.versions[name]) for name in command[2:])
        elif command[0] == 'apt-get' and '--simulate' in command:
            output = ''.join('Inst %s (%s Ubuntu:26.04/resolute [amd64])\n' % tuple(request.split('=', 1))
                             for request in command if '=' in request)
            if self.changes:
                output += 'Inst libc6 [2.0-1] (3.0-1 Ubuntu:26.04/resolute [amd64])\n'
        else:
            raise AssertionError('Unexpected command: ' + repr(command))
        return {'status': 'ok', 'returncode': 0, 'stdout': output, 'stderr': ''}

    def execute(self, command):
        self.commands.append(command)
        for request in command[command.index('install') + 1:]:
            name, version = request.split('=', 1)
            self.installed[name] = version
        return 0


class MatchingHeaderAPT(FakeAPT):
    def __init__(self, names):
        plugin, _ = packages.request_manifest(plugin_build_only=True)
        super().__init__(set(names) | set(plugin['groups']['runtime']))
        self.versions['libudev-dev'] = '2.0-1'
        self.installed.pop('libudev-dev', None)
        self.installed.update(libudev1='1.0-1', systemd='1.0-1')
        self.metadata = ('Package: libudev-dev\nVersion: 1.0-1\nArchitecture: amd64\n'
                         'Depends: libudev1 (= 1.0-1)\nDescription: fixture\n')
        self.metadata_status = 'ok'
        self.retry_status = 'ok'
        self.residual_upgrade = False

    def run(self, command, timeout=30):
        if command[:3] == ['apt-cache', 'show', '--no-all-versions']:
            self.commands.append(command)
            return {'status': self.metadata_status, 'returncode': 0 if self.metadata_status == 'ok' else 1,
                    'stdout': self.metadata, 'stderr': ''}
        result = super().run(command, timeout)
        if command[0] == 'apt-get' and '--simulate' in command:
            if 'libudev-dev=2.0-1' in command:
                result['stdout'] += ('Inst libudev1 [1.0-1] (2.0-1 Ubuntu [amd64]) [systemd:amd64 ]\n'
                                     'Inst systemd [1.0-1] (2.0-1 Ubuntu [amd64]) []\n')
            elif 'libudev-dev=1.0-1' in command:
                result['status'] = self.retry_status
                if self.residual_upgrade:
                    result['stdout'] += 'Inst systemd [1.0-1] (2.0-1 Ubuntu [amd64])\n'
        return result


class BootstrapPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        for name, value in [('host_check', lambda: None)]:
            patcher = patch.object(packages.bootstrap_sources, name, side_effect=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(guided, 'host_blockers', return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)
        spec, _ = packages.request_manifest()
        self.apt = FakeAPT(spec['groups']['runtime'])
        evidence = self.base / 'evidence'
        evidence.mkdir()
        patcher = patch.object(guided, 'private_case', return_value=evidence)
        patcher.start()
        self.addCleanup(patcher.stop)

    def prepare(self):
        return packages.prepare(self.base / 'case', run=self.apt.run)

    def test_base_scope_can_install_tools_before_a_compositor_exists(self):
        self.apt.installed.pop('git')
        self.apt.installed.pop('hyprland')
        plan = packages.prepare(self.base / 'case', run=self.apt.run, base_only=True)
        self.assertTrue(plan['base_only'])
        self.assertFalse(plan['blockers'])
        self.assertEqual(plan['payload']['pinned'], ['git=1.0-1'])
        self.assertNotIn('hyprland', plan['payload']['packages'])
        result = packages.apply(plan, guided.digest(plan), run=self.apt.run, execute=self.apt.execute)
        self.assertEqual(result['status'], 'packages-verified')

    def test_inventory_includes_compositor_runtime_and_build_dependencies(self):
        spec, _ = packages.request_manifest()
        names = spec['groups']['runtime']
        for name in ('hyprland', 'hyprlock', 'hyprpaper', 'uwsm', 'gnupg', 'bubblewrap',
                     'liblayershellqtinterface-dev', 'libdeflate-dev', 'cmake', 'g++'):
            self.assertIn(name, names)
        self.assertEqual(len(names), len(set(names)))
        self.assertNotIn('ghostty', names)
        self.assertNotIn('google-chrome-stable', names)

    def test_published_runtime_scope_excludes_source_and_plugin_toolchains(self):
        spec, _ = packages.request_manifest(runtime_only=True)
        names = spec['groups']['runtime']
        for name in ('hyprland', 'hyprpaper', 'bubblewrap', 'python3', 'libqt6core6t64', 'libqt6widgets6',
                     'liblayershellqtinterface6', 'libdeflate0', 'libjemalloc2', 'libdwarf1', 'libunwind8'):
            self.assertIn(name, names)
        for name in ('cmake', 'g++', 'libdeflate-dev', 'qt6-base-dev', 'glslang-dev'):
            self.assertNotIn(name, names)
        self.assertFalse(any(name.endswith('-dev') for name in names))

    def test_plugin_build_scope_is_separate_from_quickshell_and_omasnap(self):
        spec, _ = packages.request_manifest(plugin_build_only=True)
        names = spec['groups']['runtime']
        for name in ('cmake', 'cpio', 'gcc', 'g++', 'liblua5.4-dev', 'glslang-dev',
                     'wayland-protocols', 'hyprland-protocols', 'libeis-dev', 'libcanberra-dev',
                     'libsdbus-c++-dev', 'libxcursor-dev', 'libxcb-render0-dev'):
            self.assertIn(name, names)
        for name in ('qt6-declarative-private-dev', 'libdeflate-dev', 'liblayershellqtinterface-dev'):
            self.assertNotIn(name, names)
        with self.assertRaises(ValueError):
            packages.request_manifest(runtime_only=True, plugin_build_only=True)

    def test_prepare_only_queries_and_simulates(self):
        plan = self.prepare()
        self.assertFalse(plan['blockers'])
        self.assertEqual(plan['payload']['pinned'], ['libdeflate-dev=1.0-1'])
        self.assertFalse(any(command[0] == 'sudo' for command in self.apt.commands))

    def test_changes_to_installed_packages_block_apply(self):
        self.apt.changes = True
        plan = self.prepare()
        self.assertTrue(plan['blockers'])
        with self.assertRaises(ValueError):
            packages.apply(plan, guided.digest(plan), run=self.apt.run,
                           execute=lambda _: self.fail('Unexpected sudo'))

    def test_native_target_mismatch_blocks(self):
        self.apt.installed['hyprland'] = '0.56.2-1'
        plan = self.prepare()
        self.assertIn('Native target differs: hyprland requires 0.57.0', plan['blockers'])

    def test_approved_apply_pins_dependencies_and_verifies_result(self):
        plan = self.prepare()
        result = packages.apply(plan, guided.digest(plan), run=self.apt.run, execute=self.apt.execute)
        self.assertEqual(result['status'], 'packages-verified')
        command = next(command for command in self.apt.commands if command[0] == 'sudo')
        self.assertEqual(command, ['sudo', 'apt-get', '--no-remove', '--no-upgrade',
                                  '--no-install-recommends', 'install', 'libdeflate-dev=1.0-1'])
        self.assertFalse(result['sources_changed'])
        self.assertFalse(result['desktop_started'])

    def test_candidate_drift_invalidates_approval(self):
        plan = self.prepare()
        self.apt.versions['libdeflate-dev'] = '1.0-2'
        with self.assertRaises(ValueError):
            packages.apply(plan, guided.digest(plan), run=self.apt.run,
                           execute=lambda _: self.fail('Unexpected sudo'))

    def matching_plan(self):
        return packages.prepare(self.base / 'matching', run=self.apt.run, plugin_build_only=True)

    def test_plugin_scope_can_pin_headers_matching_unchanged_runtime(self):
        self.apt = MatchingHeaderAPT(self.apt.versions)
        before = dict(self.apt.installed)
        plan = self.matching_plan()
        self.assertFalse(plan['blockers'])
        self.assertEqual(plan['payload']['pinned'], ['libudev-dev=1.0-1'])
        self.assertEqual(plan['payload']['transaction']['upgraded_or_changed'], [])
        evidence = plan['payload']['compatibility']
        self.assertIn('Inst systemd', evidence['candidate_simulation'])
        self.assertEqual(evidence['selections'][0]['candidate_version'], '2.0-1')
        self.assertEqual(evidence['selections'][0]['selected_version'], '1.0-1')
        self.assertEqual(self.apt.installed, before)
        result = packages.apply(plan, guided.digest(plan), run=self.apt.run, execute=self.apt.execute)
        self.assertEqual(result['status'], 'packages-verified')
        self.assertEqual(self.apt.installed['libudev-dev'], '1.0-1')
        self.assertTrue(all(self.apt.installed[name] == version for name, version in before.items()))

    def test_matching_header_selection_is_explicit_in_package_review_ui(self):
        self.apt = MatchingHeaderAPT(self.apt.versions)
        plan = self.matching_plan()
        output = io.StringIO()
        with patch.object(frontend, 'ROOT', self.base), contextlib.redirect_stdout(output):
            result = frontend.main(['--packages', '--plugin-build-only', '--plan',
                                    str(Path(plan['case']) / 'package-plan.json'), '--plain'])
        self.assertEqual(result, 0)
        self.assertIn('libudev-dev=1.0-1 (candidate 2.0-1)', output.getvalue())
        self.assertIn('preserves installed libudev1=1.0-1', output.getvalue())
        self.assertFalse(any(command[0] == 'sudo' for command in self.apt.commands))

    def test_arbitrary_compatibility_mappings_are_rejected(self):
        spec, _ = packages.request_manifest(plugin_build_only=True)
        spec['matching_development_versions'] = {'other-dev': 'libudev1'}
        path = self.base / 'unsupported-pair.json'
        guided.user_install.atomic_json(path, spec)
        with self.assertRaisesRegex(ValueError, 'Unsupported development/runtime'):
            guided.package_review(run=self.apt.run, manifest_path=path)

    def test_matching_headers_are_not_selected_for_other_package_scopes(self):
        self.apt = MatchingHeaderAPT(self.apt.versions)
        spec, _ = packages.request_manifest(plugin_build_only=True)
        spec.pop('matching_development_versions')
        path = self.base / 'without-compatibility.json'
        guided.user_install.atomic_json(path, spec)
        plan = guided.package_review(manifest_path=path, run=self.apt.run)
        self.assertTrue(plan['blockers'])
        self.assertIsNone(plan['compatibility'])
        self.assertNotIn('matching_development_versions', packages.request_manifest(runtime_only=True)[0])
        self.assertFalse(any(command[:2] == ['apt-cache', 'show'] for command in self.apt.commands))

    def test_unavailable_matching_header_preserves_the_upgrade_blocker(self):
        self.apt = MatchingHeaderAPT(self.apt.versions)
        self.apt.metadata_status = 'failed'
        plan = self.matching_plan()
        self.assertTrue(plan['blockers'])
        self.assertEqual(plan['payload']['compatibility']['selections'], [])
        self.assertFalse(any(command[0] == 'sudo' for command in self.apt.commands))

    def test_malformed_or_wrong_matching_metadata_is_not_accepted(self):
        original = MatchingHeaderAPT(self.apt.versions).metadata
        for metadata in (original.replace('Package: libudev-dev', 'Package: other'),
                         original.replace('Version: 1.0-1', 'Version: 2.0-1'),
                         original.replace('Architecture: amd64', 'Architecture: arm64'),
                         original.replace('libudev1 (= 1.0-1)', 'libudev1 (>= 1.0-1)'),
                         original.replace('libudev1 (= 1.0-1)', 'libudev1 (= 1.0-1) | other'),
                         original + '\n' + original):
            with self.subTest(metadata=metadata):
                self.apt = MatchingHeaderAPT(self.apt.versions)
                self.apt.metadata = metadata
                self.assertTrue(self.matching_plan()['blockers'])
                self.assertFalse(any(command[0] == 'sudo' for command in self.apt.commands))

    def test_held_matching_runtime_does_not_trigger_compatibility_selection(self):
        self.apt = MatchingHeaderAPT(self.apt.versions)
        original = self.apt.run
        def run(command, timeout=30):
            result = original(command, timeout)
            if command == ['apt-mark', 'showhold']:
                result['stdout'] = 'libudev1\n'
            return result
        plan = packages.prepare(self.base / 'held', run=run, plugin_build_only=True)
        self.assertTrue(plan['blockers'])
        self.assertEqual(plan['payload']['compatibility']['selections'], [])

    def test_failed_or_still_upgrading_matching_simulation_cannot_apply(self):
        for failed in (True, False):
            with self.subTest(failed=failed):
                self.apt = MatchingHeaderAPT(self.apt.versions)
                self.apt.retry_status = 'failed' if failed else 'ok'
                self.apt.residual_upgrade = not failed
                plan = self.matching_plan()
                self.assertTrue(plan['blockers'])
                with self.assertRaises(ValueError):
                    packages.apply(plan, guided.digest(plan), run=self.apt.run,
                                   execute=lambda _: self.fail('Unexpected package application'))

    def test_matching_metadata_or_runtime_drift_invalidates_approval(self):
        for metadata_drift in (True, False):
            with self.subTest(metadata_drift=metadata_drift):
                self.apt = MatchingHeaderAPT(self.apt.versions)
                plan = self.matching_plan()
                self.assertFalse(plan['blockers'])
                if metadata_drift:
                    self.apt.metadata += 'Source: changed\n'
                else:
                    self.apt.installed['libudev1'] = '1.0-2'
                with self.assertRaises(ValueError):
                    packages.apply(plan, guided.digest(plan), run=self.apt.run,
                                   execute=lambda _: self.fail('Unexpected package application'))

    def test_wrong_approval_cannot_execute(self):
        plan = self.prepare()
        with self.assertRaises(ValueError):
            packages.apply(plan, 'wrong', run=self.apt.run,
                           execute=lambda _: self.fail('Unexpected sudo'))


if __name__ == '__main__':
    unittest.main()
