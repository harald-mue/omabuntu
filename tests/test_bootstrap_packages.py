"""Additive bootstrap package tests with an in-memory APT fixture."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bootstrap_packages as packages
import install as guided


class FakeAPT:
    def __init__(self, names):
        self.versions = {name: '1.0-1' for name in names}
        self.versions.update(hyprland='0.56.2-1', libqt6core6t64='6.10.2-1', hyprlock='0.9.6-1')
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
                     'liblayershellqtinterface-dev', 'libdeflate-dev', 'glslang-dev', 'cmake', 'g++'):
            self.assertIn(name, names)
        self.assertEqual(len(names), len(set(names)))
        self.assertNotIn('ghostty', names)
        self.assertNotIn('google-chrome-stable', names)

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
        self.apt.installed['hyprland'] = '0.57.0-1'
        plan = self.prepare()
        self.assertIn('Native target differs: hyprland requires 0.56.2', plan['blockers'])

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

    def test_wrong_approval_cannot_execute(self):
        plan = self.prepare()
        with self.assertRaises(ValueError):
            packages.apply(plan, 'wrong', run=self.apt.run,
                           execute=lambda _: self.fail('Unexpected sudo'))


if __name__ == '__main__':
    unittest.main()
