"""Next-login activation contracts. No compositor, daemon or systemd start."""
import hashlib
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
import session_activation as activation
import session_config
import user_install

DESCRIPTOR = {'schema_version': 1, 'activation': 'not-configured', 'library_sha256': None}


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / 'home'
        self.home.mkdir()
        patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.base / 'config'),
                                'XDG_DATA_HOME': str(self.base / 'data'),
                                'XDG_STATE_HOME': str(self.base / 'state')}).start()
        self.addCleanup(patch.stopall)
        _, self.app, self.session_paths = session_config.locations(self.home)
        bundle = self.base / 'bundle'
        for name in (*user_install.INCOMING, 'native/hyprbars.so',
                     'helpers/omabuntu_hyprland_window_minimize.py'):
            path = bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture ' + name)
            path.chmod(0o755 if name.startswith('runtime/bin/') else 0o444)
        meta = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': 'test',
                'autostart': False, 'lock_activation': False,
                'files': user_install.file_manifest(bundle)}
        (bundle / 'release.json').write_text(json.dumps(meta))
        self.app.install(bundle)
        self.paths = activation.paths_for(self.home, self.app, self.base / 'config')
        module = session_config.render(ROOT, self.app, 'us', False, self.session_paths)
        self.session_paths['module'].parent.mkdir(parents=True)
        self.session_paths['module'].write_text(module)
        self.session_paths['receipt'].parent.mkdir(parents=True, exist_ok=True)
        self.session_paths['receipt'].write_text(json.dumps({
            'module_sha256': hashlib.sha256(module.encode()).hexdigest()}))
        self.descriptor = dict(DESCRIPTOR, library_sha256=hashlib.sha256(
            (self.app.root / 'releases/test/native/hyprbars.so').read_bytes()).hexdigest())

    def plan(self, **kwargs):
        kwargs.setdefault('plugin_check', lambda release: self.descriptor)
        kwargs.setdefault('login_probe', lambda: False)
        return activation.plan(ROOT, self.home, **kwargs)

    def apply(self, reviewed, run=None):
        return activation.apply(reviewed, activation.guided.digest(reviewed), check_stopped=lambda: None,
                                run=run or (lambda argv: subprocess.CompletedProcess(
                                    argv, 1 if 'is-enabled' in argv else 0, 'disabled' if 'is-enabled' in argv else '', '')),
                                plugin_check=lambda release: self.descriptor)

    def test_plan_writes_nothing_and_loads_nothing(self):
        reviewed = self.plan()
        self.assertFalse(reviewed['blockers'])
        self.assertFalse(reviewed['plugin_loaded'])
        self.assertFalse(self.paths['activation'].exists())
        self.assertNotIn('systemctl start', reviewed['payload']['unit'])
        self.assertIn('hl.plugin.load', reviewed['payload']['activation'])
        self.assertIn('releases/test/native/hyprbars.so', reviewed['payload']['activation'])
        self.assertNotIn('/.local/lib/', reviewed['payload']['activation'])
        self.assertIn('PYTHONDONTWRITEBYTECODE=1', reviewed['payload']['titlebars'])
        self.assertNotIn('preload', reviewed['payload']['wallpaper'])

    def test_manager_mode_never_loads_a_bundled_library_or_adds_autoreload(self):
        rendered = activation.render(ROOT, self.app, 'releases/test', {
            'manager': 'hyprpm', 'titlebar_path': self.paths['titlebars']})
        self.assertIsNone(rendered['library'])
        self.assertNotIn('hl.plugin.load', rendered['activation'])
        self.assertNotIn('hyprpm reload', rendered['activation'])
        self.assertIn('dofile(', rendered['activation'])
        self.assertIn('hyprbars', rendered['titlebars'])

    def test_persistent_plugin_grant_is_backed_up_preserved_and_removable_without_loading(self):
        release = self.app.root / 'releases/test'
        (release / 'native/hyprbars.so').unlink()
        (release / 'native/hyprpm.json').write_text(json.dumps(activation.plugin_manager.policy()))
        (release / 'helpers/plugin_login.py').write_text('# fixture')
        metadata = release / 'release.json'
        meta = json.loads(metadata.read_text())
        meta['files'] = user_install.file_manifest(release)
        metadata.chmod(0o644)
        metadata.write_text(json.dumps(meta))
        metadata.chmod(0o444)
        reviewed = self.plan(plugin_login=True)
        self.assertFalse(reviewed['blockers'])
        self.assertTrue(reviewed['receipt_payload']['plugin_login_enabled'])
        self.assertIn('hyprland.start', reviewed['payload']['activation'])
        self.assertNotIn('hl.plugin.load', reviewed['payload']['activation'])
        self.assertFalse(self.apply(reviewed)['plugin_loaded'])
        self.assertTrue(self.plan()['receipt_payload']['plugin_login_enabled'])
        disabled = self.plan(plugin_login=False)
        self.assertNotIn('hyprland.start', disabled['payload']['activation'])
        self.assertFalse(self.apply(disabled)['plugin_loaded'])
        self.assertFalse(self.plan()['receipt_payload']['plugin_login_enabled'])

    def test_apply_does_not_call_start_or_hyprctl(self):
        commands = []
        def run(argv):
            commands.append(argv)
            return subprocess.CompletedProcess(argv, 1 if 'is-enabled' in argv else 0,
                                               'disabled' if 'is-enabled' in argv else '', '')
        result = self.apply(self.plan(enable_login=True), run)
        self.assertEqual(result['status'], 'prepared-for-next-login')
        self.assertFalse(result['started'])
        self.assertFalse(result['plugin_loaded'])
        self.assertEqual([cmd for cmd in commands if 'is-enabled' not in cmd],
                         [[activation.SYSTEMCTL, '--user', 'daemon-reload'],
                          [activation.SYSTEMCTL, '--user', 'enable', activation.UNIT]])
        self.assertEqual(sum('is-enabled' in cmd for cmd in commands), 2)
        self.assertTrue(self.paths['activation'].is_file())
        self.assertEqual(self.paths['wait'].stat().st_mode & 0o111, 0o111)

    def test_default_apply_does_not_enable_or_disable(self):
        def run(argv):
            if 'is-enabled' in argv:
                return subprocess.CompletedProcess(argv, 1, 'disabled', '')
            raise AssertionError('Mutating systemctl command must not be called')
        result = self.apply(self.plan(), run)
        self.assertEqual(result['status'], 'prepared-for-next-login')
        self.assertIn('splash = false', self.paths['wallpaper'].read_text())

    def test_unowned_wallpaper_and_missing_plugin_block(self):
        self.paths['wallpaper'].parent.mkdir(parents=True, exist_ok=True)
        self.paths['wallpaper'].write_text('user wallpaper config\n')
        self.assertTrue(self.plan()['blockers'])
        self.descriptor['library_sha256'] = '0' * 64
        self.paths['wallpaper'].unlink()
        self.assertTrue(any('Plugin bytes' in item for item in self.plan()['blockers']))

    def test_failure_restores_created_files_without_start(self):
        original = session_config.write
        def write(path, data, mode):
            original(path, data, mode)
            if path == self.paths['titlebars']:
                raise OSError('fixture failure')
        with patch.object(session_config, 'write', side_effect=write), self.assertRaises(ValueError):
            self.apply(self.plan())
        self.assertFalse(self.paths['activation'].exists())
        self.assertFalse(self.paths['titlebars'].exists())
        self.assertFalse(activation.pending(self.app))

    def test_live_hyprland_is_refused_before_writes(self):
        reviewed = self.plan()
        with patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE': 'live'}), self.assertRaises(ValueError):
            activation.apply(reviewed, activation.guided.digest(reviewed), plugin_check=lambda release: self.descriptor)
        self.assertFalse(self.paths['activation'].exists())

    def test_default_wallpaper_is_recorded_without_starting_hyprpaper(self):
        image = self.app.root / 'releases/test/config/menu/backgrounds/tokyo/still.webp'
        image.parent.mkdir(parents=True)
        image.write_bytes(b'fixture-image')
        release = self.app.root / 'releases/test'
        meta_path = release / 'release.json'
        meta = json.loads(meta_path.read_text())
        meta['files'] = user_install.file_manifest(release)
        meta_path.write_text(json.dumps(meta))
        reviewed = self.plan()
        self.assertIn('wallpaper-record', reviewed['changes'])
        self.assertNotIn('hyprctl', reviewed['wallpaper_record']['bytes'])
        with patch.object(activation.subprocess, 'run', side_effect=AssertionError('hyprctl')):
            self.apply(reviewed)
        recorded = json.loads((self.app.state / 'current/background.json').read_text())
        self.assertFalse(recorded['applied'])
        self.assertEqual(recorded['path'], str(image))
        self.assertEqual(os.readlink(self.app.state / 'current/lock-background'), str(image))

    def test_existing_wallpaper_record_is_not_replaced(self):
        image = self.app.root / 'releases/test/config/menu/backgrounds/still.png'
        image.parent.mkdir(parents=True)
        image.write_bytes(b'fixture-image')
        release = self.app.root / 'releases/test'
        meta_path = release / 'release.json'
        meta = json.loads(meta_path.read_text())
        meta['files'] = user_install.file_manifest(release)
        meta_path.write_text(json.dumps(meta))
        target = self.app.state / 'current/background.json'
        target.parent.mkdir(parents=True)
        target.write_text('{"path":"user"}\n')
        reviewed = self.plan()
        self.assertNotIn('wallpaper-record', reviewed['changes'])
        self.apply(reviewed)
        self.assertEqual(target.read_text(), '{"path":"user"}\n')

    def test_service_state_drift_is_rechecked_before_file_writes(self):
        reviewed = self.plan(enable_login=True)
        commands = []
        def run(argv):
            commands.append(argv)
            return subprocess.CompletedProcess(argv, 0, 'enabled', '')
        with self.assertRaisesRegex(ValueError, 'inputs changed'):
            self.apply(reviewed, run)
        self.assertFalse(self.paths['activation'].exists())
        self.assertTrue(all('is-enabled' in cmd for cmd in commands))

    def test_failed_service_operation_is_not_claimed_fully_restored(self):
        def run(argv):
            return subprocess.CompletedProcess(argv, 1, 'disabled' if 'is-enabled' in argv else '', '')
        with self.assertRaises(ValueError):
            self.apply(self.plan(enable_login=True), run)
        self.assertFalse(self.paths['activation'].exists())
        self.assertTrue(activation.pending(self.app))
        journal = next((self.app.state / 'activation-transactions').glob('*/transaction.json'))
        self.assertEqual(user_install.read_json(journal)['status'], 'recovery-required')

    def test_failed_initial_wallpaper_publish_restores_the_created_record(self):
        release = self.app.root / 'releases/test'
        image = release / 'config/menu/backgrounds/tokyo/still.webp'
        image.parent.mkdir(parents=True)
        image.write_bytes(b'fixture-image')
        metadata = user_install.read_json(release / 'release.json')
        metadata['files'] = user_install.file_manifest(release)
        user_install.atomic_json(release / 'release.json', metadata)
        reviewed = self.plan()
        with patch.object(activation.wallpaper_record, 'publish_lock', return_value=False):
            with self.assertRaises(ValueError):
                self.apply(reviewed)
        self.assertFalse((self.app.state / 'current/background.json').exists())
        self.assertFalse(self.paths['activation'].exists())
        self.assertFalse(activation.pending(self.app))

    def test_service_start_command_is_refused(self):
        with self.assertRaises(ValueError):
            activation.systemctl([activation.SYSTEMCTL, '--user', 'start', activation.UNIT],
                                 lambda argv: subprocess.CompletedProcess(argv, 0))
