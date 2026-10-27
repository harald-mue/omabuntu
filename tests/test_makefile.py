"""The Makefile stays a thin, non-surprising wrapper around the reviewed tools."""
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / 'Makefile'


def target_body(name):
    text = MAKEFILE.read_text()
    match = re.search(r'^%s:(?:[^\n]*)\n((?:\t[^\n]*\n)+)' % re.escape(name), text, re.MULTILINE)
    if not match:
        raise AssertionError('target %s is missing' % name)
    return match.group(1)


class MakefileTests(unittest.TestCase):
    def test_help_is_the_default_and_has_no_side_effects(self):
        text = MAKEFILE.read_text()
        self.assertIn('.DEFAULT_GOAL := help', text)
        body = target_body('help')
        self.assertNotIn('$(PYTHON) tools/', body)
        self.assertNotIn('$(OMABUNTU)', body)

    def test_install_and_release_never_start_the_shell(self):
        for name in ('release', 'preflight', 'plan', 'install'):
            body = target_body(name)
            self.assertNotIn('$(OMABUNTU) start', body, name)
            self.assertNotIn('systemctl', body, name)
            self.assertNotIn('sudo', body, name)

    def test_update_prepares_stops_installs_then_starts(self):
        body = target_body('update')
        order = [body.index(marker) for marker in
                 ('release VERSION', 'stop', 'install', 'start')]
        self.assertEqual(order, sorted(order))
        self.assertEqual(body.count('$(OMABUNTU) start'), 1)

    def test_version_is_required_before_a_release_target_runs(self):
        self.assertIn('VERSION is required', target_body('check-version'))
        text = MAKEFILE.read_text()
        for name in ('release', 'preflight', 'plan', 'install', 'update'):
            self.assertRegex(text, r'(?m)^%s: check-version(?: check-build)?$' % name)

    def test_autostart_targets_only_use_the_deployer(self):
        self.assertIn('deploy_autostart.py apply --replace', target_body('autostart'))
        self.assertIn('deploy_autostart.py remove', target_body('autostart-remove'))
        for name in ('autostart', 'autostart-remove'):
            body = target_body(name)
            self.assertNotIn('systemctl', body)
            self.assertNotIn('omabuntu start', body)

    def test_development_update_always_builds_before_stopping(self):
        body = target_body('dev-update')
        markers = ('release VERSION', 'preflight VERSION', 'hypr-settings-plan',
                   'autostart-plan', '$(OMABUNTU) stop', 'tools/user_install.py install',
                   'directory hypr-settings\n', 'directory autostart\n',
                   'directory reload\n', '$(OMABUNTU) start')
        positions = [body.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn('test -d', body)
        self.assertNotIn('-$(OMABUNTU) stop', body)

    def test_dev_update_parallel_make_preserves_order_with_stub_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            stub = Path(directory) / 'tool'
            log = Path(directory) / 'calls'
            stub.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "' + str(log) + '"\n')
            stub.chmod(0o700)
            subprocess.run(['make', '--no-print-directory', '-j4', 'dev-update',
                            'VERSION=test-fresh', 'BUILD_DIR=work/builds/fixture', 'PYTHON=' + str(stub),
                            'OMABUNTU=' + str(stub)], cwd=ROOT, check=True,
                           capture_output=True, text=True, timeout=30)
            calls = log.read_text().splitlines()
            self.assertIn('tools/package_user.py --version test-fresh', calls[0])
            self.assertIn('tools/install.py preflight', calls[1])
            self.assertEqual(calls[4], 'stop')
            self.assertIn('tools/user_install.py install', calls[5])
            self.assertEqual(calls[-2:], ['tools/reload_hyprland.py', 'start'])

    def test_dev_update_stops_after_failed_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            stub = Path(directory) / 'tool'
            log = Path(directory) / 'calls'
            stub.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "' + str(log) +
                            '"\ncase "$*" in *reload_hyprland.py*) exit 2;; esac\n')
            stub.chmod(0o700)
            result = subprocess.run(['make', '--no-print-directory', 'dev-update',
                                     'VERSION=test-failure', 'BUILD_DIR=work/builds/fixture', 'PYTHON=' + str(stub),
                                     'OMABUNTU=' + str(stub)], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(log.read_text().splitlines()[-1], 'tools/reload_hyprland.py')
            self.assertNotIn('start', log.read_text().splitlines())

    def test_live_targets_do_not_exit_or_restart_hyprland(self):
        self.assertIn('tools/reload_hyprland.py', target_body('reload'))
        body = target_body('restart')
        self.assertLess(body.index(' stop'), body.index(' start'))
        for name in ('dev-update', 'reload', 'restart'):
            body = target_body(name)
            for forbidden in ('uwsm stop', 'dispatch exit', 'sudo', 'plugin load', 'git '):
                self.assertNotIn(forbidden, body)

    def test_help_lists_every_public_target(self):
        result = subprocess.run(['make', '--no-print-directory', 'help'], cwd=ROOT,
                                text=True, capture_output=True, check=True)
        for name in ('test', 'doctor', 'release', 'preflight', 'plan', 'install',
                     'update', 'start', 'stop', 'status', 'autostart',
                     'autostart-remove', 'dev-update', 'reload', 'restart',
                     'hypr-settings', 'hypr-settings-plan', 'autostart-plan'):
            self.assertIn('make %s' % name, result.stdout)


if __name__ == '__main__':
    unittest.main()
