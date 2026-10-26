"""Plan 012 autostart unit template and deployment tool checks."""
import os
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

    def test_starts_neither_the_service_nor_a_compositor(self):
        self.assertNotIn('ExecStartPost', self.text)
        self.assertNotIn('ExecStartPre', self.text)
        self.assertNotIn('hyprpaper', self.text)
        self.assertNotIn('hyprctl', self.text)


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
        self.assertEqual(self.commands(), [])

    def test_plan_reports_missing_launcher(self):
        self.bin.unlink()
        result = run_tool([*self.base(), 'plan'])
        self.assertIn('MISSING', result.stdout)

    def test_apply_writes_enables_and_never_starts(self):
        run_tool([*self.base(), 'apply'])
        unit = self.home / '.config/systemd/user/omabuntu-shell.service'
        self.assertEqual(unit.read_text(), TEMPLATE.read_text())
        self.assertEqual(self.commands(), ['--user daemon-reload', '--user enable omabuntu-shell.service'])

    def test_apply_refuses_without_launcher(self):
        self.bin.unlink()
        run_tool([*self.base(), 'apply'], expect=2)
        self.assertFalse((self.home / '.config/systemd/user/omabuntu-shell.service').exists())
        self.assertEqual(self.commands(), [])

    def test_apply_refuses_overwrite_without_replace(self):
        run_tool([*self.base(), 'apply'])
        run_tool([*self.base(), 'apply'], expect=2)
        run_tool([*self.base(), 'apply', '--replace'])
        backups = list((self.home / '.config/systemd/user').glob('omabuntu-shell.service.bak-*'))
        self.assertEqual(len(backups), 1)

    def test_apply_dry_run_touches_nothing(self):
        run_tool([*self.base(), 'apply', '--dry-run'])
        self.assertFalse((self.home / '.config/systemd/user/omabuntu-shell.service').exists())
        self.assertEqual(self.commands(), [])

    def test_remove_disables_and_clears(self):
        run_tool([*self.base(), 'apply'])
        run_tool([*self.base(), 'remove'])
        self.assertFalse((self.home / '.config/systemd/user/omabuntu-shell.service').exists())
        self.assertEqual(self.commands(),
                         ['--user daemon-reload', '--user enable omabuntu-shell.service',
                          '--user disable omabuntu-shell.service', '--user daemon-reload'])

    def test_remove_when_never_applied(self):
        run_tool([*self.base(), 'remove'])
        self.assertEqual(self.commands(), ['--user disable omabuntu-shell.service', '--user daemon-reload'])


if __name__ == '__main__':
    unittest.main()
