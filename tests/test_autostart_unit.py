"""Plan 012 autostart unit template and deployment tool checks."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parent.parent / 'tools'
TEMPLATE = TOOLS.parent / 'config' / 'systemd' / 'omabuntu-shell.service'
DEPLOY = TOOLS / 'deploy_autostart.py'


def run_tool(args, *, expect=0):
    result = subprocess.run([sys.executable, str(DEPLOY), *args],
                            capture_output=True, text=True, timeout=60, check=False)
    if result.returncode != expect:
        raise AssertionError(f'exit {result.returncode} (want {expect}): {result.stderr}')
    return result


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.text = TEMPLATE.read_text()

    def contains(self, line):
        self.assertIn(line, self.text)

    def test_wiring_follows_the_hyprpaper_pattern(self):
        self.contains('PartOf=graphical-session.target')
        self.contains('Requires=graphical-session.target')
        self.contains('After=graphical-session.target')
        self.contains('ConditionEnvironment=WAYLAND_DISPLAY')
        self.contains('WantedBy=graphical-session.target')
        self.contains('Slice=session.slice')

    def test_pure_autostart_shape(self):
        self.contains('Type=oneshot')
        self.contains('ExecStart=%h/.local/bin/omabuntu start')
        self.assertNotIn('Restart=', self.text)
        self.assertNotIn('exec-once', self.text.lower())

    def test_launcher_exit_preserves_the_shell_control_group(self):
        # The manager backgrounds the shell and exits. Without this setting,
        # systemd deactivates the oneshot and cleans up its remaining children.
        directives = self.text.splitlines()
        self.assertIn('RemainAfterExit=yes', directives)
        self.assertNotIn('RemainAfterExit=no', directives)
        self.assertNotIn('KillMode=process', directives)
        self.assertNotIn('KillMode=none', directives)

    def test_waits_for_the_instance_without_starting_a_compositor(self):
        self.contains('ExecStartPre=/usr/bin/python3 %h/.config/systemd/user/omabuntu-shell-wait.py')
        self.assertEqual(self.text.count('ExecStartPre='), 1)
        self.assertNotIn('ExecStartPost', self.text)
        self.assertNotIn('hyprpaper', self.text)
        self.assertNotIn('hyprctl', self.text)
        self.assertNotIn('Restart=', self.text)


class DeployToolTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix='omabuntu-autostart-'))
        self.addCleanup(self.cleanup)
        self.bin = self.home / '.local/bin/omabuntu'
        self.bin.parent.mkdir(parents=True)
        self.bin.write_text('#!/bin/sh\nexit 0\n')
        self.bin.chmod(0o755)
        self.log = self.home / 'stub.log'
        self.stub = self.home / 'systemctl-stub'
        self.stub.write_text('#!/bin/sh\necho "$*" >> "' + str(self.log) + '"\nexit 0\n')
        self.stub.chmod(0o755)

    def cleanup(self):
        import shutil
        shutil.rmtree(self.home, ignore_errors=True)

    def base(self):
        return ['--home', str(self.home), '--systemctl', str(self.stub)]

    def commands(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_plan_is_read_only(self):
        result = run_tool([*self.base(), 'plan'])
        self.assertIn('ExecStart=%h/.local/bin/omabuntu start', result.stdout)
        self.assertIn('Target:   ' + str(self.home / '.config/systemd/user/omabuntu-shell.service'),
                      result.stdout)
        self.assertFalse((self.home / '.config/systemd/user/omabuntu-shell.service').exists())
        self.assertFalse((self.home / '.config/systemd/user/omabuntu-shell-wait.py').exists())
        self.assertEqual(self.commands(), [])

    def test_plan_reports_missing_launcher(self):
        self.bin.unlink()
        result = run_tool([*self.base(), 'plan'])
        self.assertIn('MISSING', result.stdout)

    def test_apply_writes_enables_and_never_starts(self):
        run_tool([*self.base(), 'apply'])
        unit_dir = self.home / '.config/systemd/user'
        unit = unit_dir / 'omabuntu-shell.service'
        wait = unit_dir / 'omabuntu-shell-wait.py'
        self.assertEqual(unit.read_text(), TEMPLATE.read_text())
        self.assertEqual(wait.read_text(), (TEMPLATE.parent / 'omabuntu-shell-wait.py').read_text())
        self.assertTrue(wait.stat().st_mode & 0o111)
        self.assertEqual(self.commands(), ['--user daemon-reload', '--user enable omabuntu-shell.service'])

    def test_apply_refuses_without_launcher(self):
        self.bin.unlink()
        run_tool([*self.base(), 'apply'], expect=2)
        self.assertFalse((self.home / '.config/systemd/user/omabuntu-shell.service').exists())
        self.assertFalse((self.home / '.config/systemd/user/omabuntu-shell-wait.py').exists())
        self.assertEqual(self.commands(), [])

    def test_apply_refuses_overwrite_without_replace(self):
        run_tool([*self.base(), 'apply'])
        run_tool([*self.base(), 'apply'], expect=2)
        run_tool([*self.base(), 'apply', '--replace'])
        backups = list((self.home / '.config/systemd/user').glob('omabuntu-shell.service.bak-*'))
        self.assertEqual(len(backups), 1)
        wait_backups = list((self.home / '.config/systemd/user').glob('omabuntu-shell-wait.py.bak-*'))
        self.assertEqual(len(wait_backups), 1)

    def test_apply_dry_run_touches_nothing(self):
        run_tool([*self.base(), 'apply', '--dry-run'])
        unit_dir = self.home / '.config/systemd/user'
        self.assertFalse((unit_dir / 'omabuntu-shell.service').exists())
        self.assertFalse((unit_dir / 'omabuntu-shell-wait.py').exists())
        self.assertEqual(self.commands(), [])

    def test_remove_disables_and_clears(self):
        run_tool([*self.base(), 'apply'])
        run_tool([*self.base(), 'remove'])
        unit_dir = self.home / '.config/systemd/user'
        self.assertFalse((unit_dir / 'omabuntu-shell.service').exists())
        self.assertFalse((unit_dir / 'omabuntu-shell-wait.py').exists())
        self.assertEqual(self.commands(),
                         ['--user daemon-reload', '--user enable omabuntu-shell.service',
                          '--user disable omabuntu-shell.service', '--user daemon-reload'])

    def test_remove_when_never_applied(self):
        run_tool([*self.base(), 'remove'])
        self.assertEqual(self.commands(), ['--user disable omabuntu-shell.service', '--user daemon-reload'])


def load_wait():
    path = TEMPLATE.parent / 'omabuntu-shell-wait.py'
    spec = importlib.util.spec_from_file_location('omabuntu_shell_wait', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstanceWaitTests(unittest.TestCase):
    def setUp(self):
        self.wait = load_wait()

    def test_lone_bracket_is_the_empty_instance_bug_not_a_list(self):
        self.assertIsNone(self.wait.parse_instances('\n]\n'))
        self.assertIsNone(self.wait.parse_instances(']'))
        self.assertEqual(self.wait.parse_instances('[]'), [])

    def test_poll_accepts_the_live_instance_after_invalid_json(self):
        payloads = ['\n]\n', '[{"instance": "sig", "time": 1, "pid": 2, "wl_socket": "wayland-1"}]\n']

        def run():
            return subprocess.CompletedProcess(['hyprctl'], 0, payloads.pop(0), '')

        found = self.wait.wait_for_instance('sig', 'wayland-1', run=run, attempts=2, pause=0)
        self.assertEqual(found[0]['instance'], 'sig')
        self.assertEqual(payloads, [])

    def test_poll_reports_not_ready_when_json_never_appears(self):
        def run():
            return subprocess.CompletedProcess(['hyprctl'], 0, '\n]\n', '')

        with self.assertRaisesRegex(ValueError, 'not ready'):
            self.wait.wait_for_instance('sig', 'wayland-1', run=run, attempts=2, pause=0)

    def test_missing_session_does_not_poll_or_start_a_shell(self):
        text = (TEMPLATE.parent / 'omabuntu-shell-wait.py').read_text()
        self.assertNotIn('quickshell', text)
        self.assertNotIn('omabuntu start', text)

        def run():
            raise AssertionError('poll should not start without a session')

        with self.assertRaisesRegex(ValueError, 'not ready'):
            self.wait.wait_for_instance('', 'wayland-1', run=run, attempts=3, pause=0)


if __name__ == '__main__':
    unittest.main()
