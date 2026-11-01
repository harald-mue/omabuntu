"""Plan 068 hyprpaper Hyprland-only drop-in checks."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parent.parent / 'tools'
TEMPLATE = TOOLS.parent / 'config' / 'systemd' / 'hyprpaper-condition.conf'
DEPLOY = TOOLS / 'deploy_hyprpaper_condition.py'
sys.path.insert(0, str(TOOLS))
import deploy_hyprpaper_condition  # noqa: E402


def run_tool(args, *, expect=0):
    result = subprocess.run([sys.executable, str(DEPLOY), *args],
                            capture_output=True, text=True, timeout=60, check=False)
    if result.returncode != expect:
        raise AssertionError(f'exit {result.returncode} (want {expect}): {result.stdout}{result.stderr}')
    return result


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.text = TEMPLATE.read_text()

    def test_adds_only_the_hyprland_condition(self):
        self.assertIn('[Unit]', self.text)
        self.assertIn('ConditionEnvironment=HYPRLAND_INSTANCE_SIGNATURE', self.text)

    def test_never_changes_services_or_the_base_unit(self):
        for forbidden in ('[Service]', 'ExecStart', 'ExecStop', 'Restart=',
                          'WantedBy=', 'Requires=', 'PartOf=', 'ConditionEnvironment=WAYLAND'):
            self.assertNotIn(forbidden, self.text)

    def test_is_additive_and_reviewed(self):
        self.assertIn('systemd ANDs conditions', self.text)
        self.assertIn('hyprpaper.service.d/omabuntu.conf', self.text)


class DeployToolTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix='omabuntu-hyprpaper-'))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.log = self.home / 'stub.log'
        self.stub = self.home / 'systemctl-stub'
        self.stub.write_text('#!/bin/sh\necho "$*" >> "' + str(self.log) + '"\nexit 0\n')
        self.stub.chmod(0o755)

    def base(self):
        return ['--home', str(self.home), '--systemctl', str(self.stub)]

    def target(self):
        return self.home / '.config/systemd/user/hyprpaper.service.d/omabuntu.conf'

    def commands(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_plan_is_read_only(self):
        result = run_tool([*self.base(), 'plan'])
        self.assertIn('ConditionEnvironment=HYPRLAND_INSTANCE_SIGNATURE', result.stdout)
        self.assertIn('Target:   ' + str(self.target()), result.stdout)
        self.assertIn('Base unit:', result.stdout)
        self.assertIn('systemctl --user stop hyprpaper.service', result.stdout)
        self.assertFalse(self.target().exists())
        self.assertEqual(self.commands(), [])

    def test_apply_writes_the_drop_in_and_reloads_only(self):
        run_tool([*self.base(), 'apply'])
        self.assertEqual(self.target().read_text(), TEMPLATE.read_text())
        self.assertEqual(self.commands(), ['--user daemon-reload'])

    def test_apply_is_idempotent_and_reloads_nothing_twice(self):
        run_tool([*self.base(), 'apply'])
        run_tool([*self.base(), 'apply'])
        self.assertEqual(self.commands(), ['--user daemon-reload'])

    def test_apply_refuses_a_differing_file_without_replace(self):
        self.target().parent.mkdir(parents=True)
        self.target().write_text('# mine\n')
        run_tool([*self.base(), 'apply'], expect=2)
        self.assertEqual(self.target().read_text(), '# mine\n')
        self.assertEqual(self.commands(), [])
        run_tool([*self.base(), 'apply', '--replace'])
        backups = list(self.target().parent.glob('omabuntu.conf.bak-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(self.target().read_text(), TEMPLATE.read_text())
        self.assertEqual(self.commands(), ['--user daemon-reload'])

    def test_dry_run_writes_nothing_and_runs_no_systemctl(self):
        run_tool([*self.base(), 'apply', '--dry-run'])
        self.assertFalse(self.target().exists())
        self.assertEqual(self.commands(), [])

    def test_remove_deletes_the_drop_in_and_prunes_the_empty_dir(self):
        run_tool([*self.base(), 'apply'])
        run_tool([*self.base(), 'remove'])
        self.assertFalse(self.target().exists())
        self.assertFalse(self.target().parent.exists())
        self.assertEqual(self.commands(), ['--user daemon-reload', '--user daemon-reload'])

    def test_remove_is_safe_when_nothing_is_deployed(self):
        run_tool([*self.base(), 'remove'])
        self.assertEqual(self.commands(), ['--user daemon-reload'])


class ReviewDeployTests(unittest.TestCase):
    """Plan 069 helper API used by the published installer."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix='omabuntu-hyprpaper-api-'))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.log = self.home / 'stub.log'
        self.stub = self.home / 'systemctl-stub'
        self.stub.write_text('#!/bin/sh\necho "$*" >> "' + str(self.log) + '"\nexit 0\n')
        self.stub.chmod(0o755)

    def target(self):
        return self.home / '.config/systemd/user/hyprpaper.service.d/omabuntu.conf'

    def commands(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_review_reports_state_without_writing(self):
        info = deploy_hyprpaper_condition.review(self.home)
        self.assertEqual(info['target'], self.target())
        self.assertFalse(info['exists'])
        self.assertFalse(info['current'])
        self.assertFalse(self.target().exists())

    def test_deploy_writes_and_reloads_without_a_backup(self):
        result = deploy_hyprpaper_condition.deploy(self.home, systemctl_binary=str(self.stub))
        self.assertTrue(result['changed'])
        self.assertIsNone(result['backup'])
        self.assertEqual(self.target().read_text(), TEMPLATE.read_text())
        self.assertEqual(self.commands(), ['--user daemon-reload'])

    def test_deploy_is_idempotent_and_reloads_nothing_twice(self):
        deploy_hyprpaper_condition.deploy(self.home, systemctl_binary=str(self.stub))
        result = deploy_hyprpaper_condition.deploy(self.home, systemctl_binary=str(self.stub))
        self.assertFalse(result['changed'])
        self.assertEqual(self.commands(), ['--user daemon-reload'])

    def test_deploy_backs_up_a_differing_file(self):
        self.target().parent.mkdir(parents=True)
        self.target().write_text('# mine\n')
        result = deploy_hyprpaper_condition.deploy(self.home, systemctl_binary=str(self.stub))
        self.assertTrue(result['changed'])
        self.assertIsNotNone(result['backup'])
        self.assertEqual(result['backup'].read_text(), '# mine\n')
        self.assertEqual(self.target().read_text(), TEMPLATE.read_text())

    def test_deploy_dry_run_writes_nothing(self):
        result = deploy_hyprpaper_condition.deploy(self.home, systemctl_binary=str(self.stub), dry_run=True)
        self.assertTrue(result['changed'])
        self.assertFalse(self.target().exists())
        self.assertEqual(self.commands(), [])


if __name__ == '__main__':
    unittest.main()
