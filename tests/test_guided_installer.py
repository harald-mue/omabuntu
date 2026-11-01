"""Guided installer safety contracts: private fixtures and injected commands only."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import install as guided
import user_install


class Host:
    def __init__(self):
        _, names = guided.manifest(wallpaper=True)
        self.installed = {n: '1.0' for n in names if n != 'hyprpaper'}
        self.installed['libqt6core6t64'] = '6.10.2+dfsg-3'
        self.manual = ['python3']
        self.held = []
        self.calls = []
        self.simulation = 'Inst hyprpaper (0.8.4 Ubuntu:26.04/resolute [amd64])\n'
        self.candidate = '0.8.4'
        self.hyprland = 'Hyprland 0.57.0'
        self.failure = None

    def run(self, command, timeout=30):
        self.calls.append(command)
        output = ''
        if self.failure == command[0]:
            return {'status': 'timeout', 'stdout': '', 'stderr': '', 'returncode': None}
        if command[0] == 'dpkg-query':
            output = ''.join(n + '\t' + v + '\tinstalled\n' for n, v in sorted(self.installed.items()))
        elif command[:2] == ['apt-mark', 'showmanual']:
            output = '\n'.join(self.manual)
        elif command[:2] == ['apt-mark', 'showhold']:
            output = '\n'.join(self.held)
        elif command[0] == 'apt-cache':
            output = ''.join(n + ':\n  Installed: ' + self.installed.get(n, '(none)')
                             + '\n  Candidate: ' + self.candidate + '\n' for n in command[2:])
        elif command[0] == 'apt-get':
            if '--simulate' not in command:
                raise AssertionError('No real APT execution in tests')
            output = self.simulation
        elif command[0] == 'Hyprland':
            output = self.hyprland
        elif command[0] == 'fc-match':
            output = 'JetBrainsMono Nerd Font\n'
        elif command[0] == 'pgrep':
            return {'status': 'failed', 'stdout': '', 'stderr': '', 'returncode': 1}
        elif command[0] == 'hyprctl':
            if command[1:] != ['hyprpaper', '--help']:
                raise AssertionError('No live compositor or wallpaper mutation in tests')
            output = 'requests: wallpaper'
        else:
            raise AssertionError('Unexpected host command: ' + repr(command))
        return {'status': 'ok', 'returncode': 0, 'stdout': output, 'stderr': ''}


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.addCleanup(patch.stopall)
        patch.object(guided, 'ROOT', self.base).start()
        patch.object(guided.platform, 'machine', return_value='x86_64').start()
        patch.object(guided.omabuntu, 'read_os_release', return_value={
            'status': 'ok', 'values': {'ID': 'ubuntu', 'VERSION_ID': '26.04'}}).start()
        self.host = Host()
        self.bundle = self.base / 'bundle'
        self.bundle.mkdir()
        for name in user_install.INCOMING:
            path = self.bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture ' + name)
            path.chmod(0o755 if name == 'runtime/bin/quickshell' else 0o444)
        (self.bundle / 'runtime/bin/qs').symlink_to('quickshell')
        image = self.bundle / 'config/menu/backgrounds/theme/still.webp'
        image.parent.mkdir(parents=True)
        image.write_bytes(b'fixture, never decoded by a host process')
        self.reseal()
        self.app = user_install.Installation(self.base / 'data/omabuntu',
                                            self.base / 'state/omabuntu', self.base / 'bin/omabuntu')

    def reseal(self):
        metadata = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1',
                    'version': 'fixture-v1', 'autostart': False, 'lock_activation': False,
                    'files': user_install.file_manifest(self.bundle)}
        (self.bundle / 'release.json').write_text(json.dumps(metadata))

    def plan_file(self, kind='omabuntu-package-plan', payload=None):
        if payload is None:
            payload = guided.package_review(True, run=self.host.run)
        sealed = guided.seal(kind, payload)
        path = guided.save(guided.private_case(), 'plan.json', sealed)
        return path, sealed['approval']

    def preflight(self, **kwargs):
        return guided.preflight(self.bundle, run=self.host.run,
                                runtime=lambda bundle, case: {'status': 'passed'}, **kwargs)

    def test_manifest_separates_wallpaper_and_has_no_build_toolchain(self):
        _, core = guided.manifest()
        _, full = guided.manifest(wallpaper=True)
        self.assertNotIn('hyprpaper', core)
        self.assertIn('hyprpaper', full)
        self.assertIn('qt6-image-formats-plugins', core)
        for name in ('g++', 'cmake', 'qt6-base-dev'):
            self.assertNotIn(name, full)

    def test_manifest_rejects_shell_or_apt_option_injection(self):
        value, _ = guided.manifest()
        value['groups']['runtime'] = ['--allow-unauthenticated']
        path = self.base / 'manifest.json'
        path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            guided.manifest(path)

    def test_package_plan_is_simulation_only_and_pins_candidates(self):
        value = guided.package_review(True, run=self.host.run)
        self.assertEqual(value['status'], 'review-required')
        self.assertEqual(value['pinned'], ['hyprpaper=0.8.4'])
        self.assertEqual(value['resolved'], {'hyprpaper': '0.8.4'})
        self.assertTrue(any('--simulate' in c for c in self.host.calls))
        self.assertFalse(any(c[0] in ('sudo', 'systemctl') for c in self.host.calls))
        self.assertFalse(any('update' in c for c in self.host.calls))

    def test_already_installed_packages_are_not_upgraded_to_candidates(self):
        value = guided.package_review(run=self.host.run)
        self.assertEqual(value['pinned'], [])
        self.assertFalse(any(c[0] == 'apt-get' for c in self.host.calls))

    def test_package_plan_blocks_removals_upgrades_and_unknown_lines(self):
        for text in ('Remv python3 [1.0]\n',
                     'Inst python3 [1.0] (2.0 Ubuntu [amd64])\n',
                     'Inst hyprpaper (bad;version Ubuntu [amd64])\n',
                     'nothing installed\n'):
            self.host.simulation = text
            self.assertEqual(guided.package_review(True, run=self.host.run)['status'], 'blocked')

    def test_valid_upgrade_lines_are_explained_not_misreported_as_parse_errors(self):
        self.host.simulation = 'Inst python3 [1.0] (2.0 Ubuntu [amd64])\n'
        reviewed = guided.package_review(True, run=self.host.run)
        self.assertEqual(reviewed['status'], 'blocked')
        self.assertIn('Removals or changes to installed packages are not permitted', reviewed['blockers'])
        self.assertNotIn('Unrecognized or unsafe APT install line', reviewed['blockers'])
        self.assertEqual(reviewed['resolved']['python3'], '2.0')

    def test_package_plan_blocks_missing_candidate_and_unsupported_host(self):
        self.host.candidate = '(none)'
        self.assertEqual(guided.package_review(True, run=self.host.run)['status'], 'blocked')
        with patch.object(guided.omabuntu, 'read_os_release', return_value={'status': 'error'}):
            self.assertEqual(guided.package_review(run=self.host.run)['status'], 'blocked')

    def test_probe_timeout_is_not_success(self):
        self.host.failure = 'apt-mark'
        with self.assertRaisesRegex(ValueError, 'timeout'):
            guided.package_review(True, run=self.host.run)

    def test_no_approval_or_tampered_plan_never_executes(self):
        path, approval = self.plan_file()
        with patch.object(guided, 'terminal_install') as execute:
            with self.assertRaises(ValueError):
                guided.apply_packages(path, 'wrong', run=self.host.run, execute=execute)
            value = json.loads(path.read_text())
            value['payload']['pinned'] = ['evil=1.0']
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                guided.apply_packages(path, approval, run=self.host.run, execute=execute)
            execute.assert_not_called()

    def test_drift_in_policy_package_marks_or_simulation_requires_new_approval(self):
        path, approval = self.plan_file()
        for attr, value in (('candidate', '0.8.5'), ('manual', ['python3', 'fontconfig']),
                            ('simulation', self.host.simulation + 'Conf hyprpaper (0.8.4 Ubuntu)\n')):
            old = getattr(self.host, attr)
            setattr(self.host, attr, value)
            with self.assertRaisesRegex(ValueError, 'changed'):
                guided.apply_packages(path, approval, run=self.host.run,
                                      execute=lambda c: self.fail('No transaction on drift'))
            setattr(self.host, attr, old)

    def test_explicit_package_apply_records_before_after_and_pins_transitives(self):
        self.host.simulation += 'Inst libfixture (2.0 Ubuntu:26.04/resolute [amd64])\n'
        path, approval = self.plan_file()
        calls = []

        def execute(command):
            calls.append(command)
            self.host.installed.update(hyprpaper='0.8.4', libfixture='2.0')
            return 0

        case = guided.apply_packages(path, approval, run=self.host.run, execute=execute)
        self.assertIn('hyprpaper=0.8.4', calls[0])
        self.assertIn('libfixture=2.0', calls[0])
        self.assertIn('--no-upgrade', calls[0])
        self.assertNotIn('-y', calls[0])
        self.assertEqual(json.loads((case / 'after.json').read_text())['status'], 'verified')
        self.assertEqual((case / 'before.json').stat().st_mode & 0o777, 0o600)

    def test_partial_package_failure_keeps_evidence_and_never_rolls_back_blindly(self):
        path, approval = self.plan_file()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            guided.apply_packages(path, approval, run=self.host.run, execute=lambda c: 100)
        evidence = list((self.base / 'work/installer').glob('*/after.json'))
        self.assertEqual(len(evidence), 1)
        self.assertEqual(json.loads(evidence[0].read_text())['status'], 'failed')
        self.assertFalse(any('autoremove' in c or 'purge' in c for c in self.host.calls))

    def test_interrupted_package_transaction_keeps_evidence(self):
        path, approval = self.plan_file()

        def interrupt(command):
            raise KeyboardInterrupt()

        with self.assertRaisesRegex(ValueError, 'incomplete'):
            guided.apply_packages(path, approval, run=self.host.run, execute=interrupt)
        evidence = next((self.base / 'work/installer').glob('*/after.json'))
        outcome = json.loads(evidence.read_text())
        self.assertEqual(outcome['status'], 'interrupted')
        self.assertIn('after', outcome)

    def test_unexpected_package_change_blocks_verification(self):
        path, approval = self.plan_file()

        def execute(command):
            self.host.installed.update(hyprpaper='0.8.4', python3='2.0')
            return 0

        with self.assertRaisesRegex(ValueError, 'unexpected'):
            guided.apply_packages(path, approval, run=self.host.run, execute=execute)

    def test_terminal_install_refuses_noninteractive_authentication(self):
        with patch.object(guided.sys.stdin, 'isatty', return_value=False), \
                patch.object(guided.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'interactive'):
                guided.terminal_install(['sudo', 'apt-get'])
            run.assert_not_called()

    def test_preflight_reports_missing_feature_and_wrong_target(self):
        report, path = self.preflight(wallpaper=True)
        self.assertEqual(report['status'], 'blocked')
        self.assertTrue(path.is_file())
        report, _ = self.preflight()
        self.assertEqual(report['status'], 'passed')
        self.host.hyprland = 'Hyprland 0.57.00'
        self.assertEqual(self.preflight()[0]['status'], 'blocked')
        self.host.hyprland = 'Hyprland 0.57.0'
        self.host.installed['libqt6core6t64'] = '6.11.0-1'
        self.assertEqual(self.preflight()[0]['status'], 'blocked')

    def test_wallpaper_is_reported_but_never_started_by_preflight(self):
        self.host.installed['hyprpaper'] = '0.8.4'
        report, _ = self.preflight(wallpaper=True)
        self.assertEqual(report['status'], 'passed')
        self.assertFalse(report['wallpaper_daemon']['running'])
        self.assertEqual(report['wallpaper_daemon']['ipc'], 'current')
        self.assertFalse(any(c[0] in ('hyprpaper', 'sudo', 'systemctl') for c in self.host.calls))
        self.assertEqual([c for c in self.host.calls if c[0] == 'hyprctl'],
                         [['hyprctl', 'hyprpaper', '--help']])

    def test_preflight_rejects_tampered_bundle_before_probes(self):
        (self.bundle / 'manager.py').chmod(0o600)
        (self.bundle / 'manager.py').write_text('changed')
        with self.assertRaises(ValueError):
            self.preflight()
        self.assertEqual(self.host.calls, [])

    def test_runtime_probe_is_sandboxed_and_requires_actual_decode_marker(self):
        calls = []

        def run(command, timeout):
            calls.append(command)
            output = ('libQt6Core libQt6Qml libQt6Quick' if 'ldd' in command
                      else 'Configuration Loaded\nOMABUNTU_INSTALL_WEBP_READY')
            return {'status': 'ok', 'stdout': output, 'stderr': ''}

        result = guided.runtime_probe(self.bundle, guided.private_case(), run=run)
        self.assertEqual(result['status'], 'passed')
        for c in calls:
            self.assertEqual(c[0], 'bwrap')
            self.assertIn('--unshare-all', c)
            self.assertIn('--clearenv', c)
            self.assertNotIn('HYPRLAND_INSTANCE_SIGNATURE', c)
        result = guided.runtime_probe(self.bundle, guided.private_case(),
                                     run=lambda c, timeout: {'status': 'ok', 'stdout': '', 'stderr': ''})
        self.assertEqual(result['status'], 'failed')

    def test_failed_decode_or_runtime_timeout_blocks_deployment(self):
        # Never launch the fixture binary, let alone a host service.
        report, path = guided.preflight(self.bundle, run=self.host.run,
                                       runtime=lambda b, c: {'status': 'timeout'})
        self.assertEqual(report['status'], 'blocked')
        with patch.object(guided, 'preflight', return_value=(report, path)):
            with self.assertRaisesRegex(ValueError, 'blocked'):
                guided.deployment_review(self.bundle, self.app)
        self.assertFalse(self.app.root.exists())

    def deployment(self):
        report, path = self.preflight()
        with patch.object(guided, 'preflight', return_value=(report, path)):
            payload = guided.deployment_review(self.bundle, self.app)
        return payload, report, path

    def test_deployment_reuses_transactional_installer_without_start(self):
        payload, report, report_path = self.deployment()
        path, approval = self.plan_file('omabuntu-deployment-plan', payload)
        with patch.object(guided, 'preflight', return_value=(report, report_path)), \
                patch.object(guided.subprocess, 'Popen') as popen:
            result = guided.apply_deployment(path, approval)
        self.assertEqual(result['status'], 'installed-not-started')
        self.assertEqual(self.app.selected(), 'releases/fixture-v1')
        self.assertTrue(Path(result['backup']).is_dir())
        popen.assert_not_called()
        self.assertEqual(self.app.rollback()['status'], 'first-install-restored')

    def test_reinstall_uses_existing_idempotent_deployment(self):
        self.app.install(self.bundle)
        payload, report, report_path = self.deployment()
        path, approval = self.plan_file('omabuntu-deployment-plan', payload)
        with patch.object(guided, 'preflight', return_value=(report, report_path)):
            result = guided.apply_deployment(path, approval)
        self.assertEqual(result['status'], 'already-installed')

    def test_deployment_refuses_later_launcher_edit(self):
        payload, report, report_path = self.deployment()
        path, approval = self.plan_file('omabuntu-deployment-plan', payload)
        self.app.launcher.parent.mkdir()
        self.app.launcher.write_text('user addition')
        with patch.object(guided, 'preflight', return_value=(report, report_path)):
            with self.assertRaisesRegex(ValueError, 'changed'):
                guided.apply_deployment(path, approval)
        self.assertEqual(self.app.launcher.read_text(), 'user addition')

    def test_bundle_is_rechecked_under_deployment_lock(self):
        payload, report, report_path = self.deployment()
        path, approval = self.plan_file('omabuntu-deployment-plan', payload)
        target = self.bundle / 'manager.py'
        target.chmod(0o600)
        target.write_text('changed while acquiring lock')
        target.chmod(0o444)
        self.reseal()
        # A stale preflight models a change after its successful check.
        with patch.object(guided, 'preflight', return_value=(report, report_path)):
            with self.assertRaisesRegex(ValueError, 'Bundle changed'):
                guided.apply_deployment(path, approval)
        self.assertFalse(self.app.launcher.exists())
        self.assertFalse(self.app.root.exists())

    def test_running_shell_blocks_plan_without_stopping_anything(self):
        report, path = self.preflight()
        with patch.object(guided, 'preflight', return_value=(report, path)), \
                patch.object(self.app, 'running', return_value={'pid': 123}), \
                patch.object(self.app, 'stop') as stop:
            with self.assertRaisesRegex(ValueError, 'running'):
                guided.deployment_review(self.bundle, self.app)
            stop.assert_not_called()

    def test_cli_no_apply_never_installs_or_starts(self):
        with patch.object(guided.os, 'geteuid', return_value=1000), \
                patch.dict(os.environ, {'SUDO_USER': ''}), \
                patch.object(guided, 'apply_packages') as packages, \
                patch.object(guided, 'apply_deployment') as deploy, \
                patch.object(guided.user_install, 'main') as manager, \
                contextlib.redirect_stdout(io.StringIO()):
            for args in (['packages', 'unused.json'], ['install', 'unused.json'], ['start']):
                self.assertEqual(guided.main(args), 0)
            packages.assert_not_called()
            deploy.assert_not_called()
            manager.assert_not_called()

    def test_candidate_solver_disagreement_blocks_apply(self):
        self.host.simulation = 'Inst hyprpaper (0.9.0 Ubuntu [amd64])\n'
        payload = guided.package_review(True, run=self.host.run)
        self.assertEqual(payload['status'], 'blocked')
        path, approval = self.plan_file(payload=payload)
        with self.assertRaisesRegex(ValueError, 'changed'):
            guided.apply_packages(path, approval, run=self.host.run,
                                  execute=lambda c: self.fail('Blocked plan must not run'))

    def test_noop_package_apply_does_not_invoke_sudo(self):
        self.host.installed['hyprpaper'] = '0.8.4'
        path, approval = self.plan_file()
        case = guided.apply_packages(path, approval, run=self.host.run,
                                     execute=lambda c: self.fail('Nothing to install'))
        self.assertEqual(json.loads((case / 'after.json').read_text())['status'], 'already-satisfied')

    def test_private_report_parent_symlink_is_refused(self):
        (self.base / 'work').mkdir(mode=0o700)
        (self.base / 'work/installer').symlink_to(self.base / 'unrelated')
        with self.assertRaises(ValueError):
            guided.private_case()
        self.assertFalse((self.base / 'unrelated').exists())

    def test_missing_probe_command_stays_explicit(self):
        self.host.failure = 'Hyprland'
        report, _ = self.preflight()
        result = next(c for c in report['checks'] if c['name'] == 'hyprland-target')
        self.assertFalse(result['ok'])
        self.assertEqual(result['probe']['status'], 'timeout')

    def test_cli_apply_without_digest_refuses_before_actions(self):
        with patch.object(guided.os, 'geteuid', return_value=1000), \
                patch.dict(os.environ, {'SUDO_USER': ''}), \
                patch.object(guided, 'apply_deployment') as deploy:
            with self.assertRaisesRegex(ValueError, 'Missing explicit'):
                guided.main(['install', 'unused.json', '--apply'])
            deploy.assert_not_called()

    def test_cli_rejects_root(self):
        with patch.object(guided.os, 'geteuid', return_value=0):
            with self.assertRaisesRegex(ValueError, 'normal user'):
                guided.main(['start', '--apply'])


if __name__ == '__main__':
    unittest.main()
