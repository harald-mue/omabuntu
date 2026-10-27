"""User deployment contracts, entirely in private workspace fixtures."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import user_install as deploy
import display_backend
import lock_readiness

REQUIRED = deploy.INCOMING


class UserInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.app = deploy.Installation(self.base / 'data/omabuntu', self.base / 'state/omabuntu', self.base / 'bin/omabuntu')
        self.a = self.bundle('v1')
        self.b = self.bundle('v2')

    def bundle(self, version):
        root = self.base / 'bundles' / version
        root.mkdir(parents=True)
        for name in REQUIRED:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture ' + name + ' ' + version)
            path.chmod(0o755 if name == 'runtime/bin/quickshell' else 0o444)
        (root / 'runtime/bin/qs').symlink_to('quickshell')
        meta = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': version,
                'autostart': False, 'lock_activation': False, 'files': deploy.file_manifest(root)}
        (root / 'release.json').write_text(json.dumps(meta))
        return root

    def test_plan_is_read_only_and_never_starts_services(self):
        with patch.object(deploy.subprocess, 'run') as run, patch.object(deploy.subprocess, 'Popen') as popen:
            plan = self.app.plan(self.a)
        self.assertFalse(self.app.root.exists())
        self.assertFalse(self.app.state.exists())
        self.assertFalse(self.app.launcher.exists())
        self.assertFalse(plan['autostart'])
        self.assertFalse(plan['lock_activation'])
        run.assert_not_called()
        popen.assert_not_called()

    def test_install_is_versioned_verified_and_not_started(self):
        with patch.object(deploy.subprocess, 'Popen') as popen:
            result = self.app.install(self.a)
        self.assertEqual(result['status'], 'installed-not-started')
        self.assertEqual(result['current'], 'releases/v1')
        self.assertEqual(self.app.selected(), 'releases/v1')
        deploy.verify_bundle(self.app.root / 'releases/v1')
        self.assertEqual(self.app.launcher.read_text(), self.app.bootstrap())
        compile(self.app.bootstrap(), '<bootstrap>', 'exec')
        self.assertTrue(self.app.launcher.stat().st_mode & stat.S_IXUSR)
        popen.assert_not_called()

    def test_install_is_idempotent(self):
        self.app.install(self.a)
        before = sorted((self.app.state / 'transactions').iterdir())
        self.assertEqual(self.app.install(self.a)['status'], 'already-installed')
        self.assertEqual(before, sorted((self.app.state / 'transactions').iterdir()))

    def test_update_preserves_previous_release(self):
        self.app.install(self.a)
        self.app.install(self.b)
        self.assertEqual(self.app.selected(), 'releases/v2')
        self.assertEqual(self.app.selected('previous'), 'releases/v1')
        self.assertTrue((self.app.root / 'releases/v1/manager.py').exists())

    def test_previous_release_may_predate_the_menu(self):
        older = self.base / 'bundles' / 'older'
        older.mkdir(parents=True)
        for name in deploy.BASELINE:
            path = older / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('older ' + name)
            path.chmod(0o755 if name == 'runtime/bin/quickshell' else 0o444)
        (older / 'runtime/bin/qs').symlink_to('quickshell')
        meta = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': 'older',
                'autostart': False, 'lock_activation': False, 'files': deploy.file_manifest(older)}
        (older / 'release.json').write_text(json.dumps(meta))
        with self.assertRaises(ValueError):
            deploy.verify_bundle(older)
        self.app.install(self.a)
        destination = self.app.root / 'releases' / 'older'
        shutil.copytree(older, destination, symlinks=True)
        self.app.select('previous', 'releases/older')
        plan = self.app.plan(self.b)
        self.assertEqual(plan['prestate']['previous'], 'releases/older')
        self.assertEqual(plan['current'], 'releases/v1')

    def test_rollback_switches_verified_versions_without_start(self):
        self.app.install(self.a)
        self.app.install(self.b)
        with patch.object(deploy.subprocess, 'Popen') as popen:
            result = self.app.rollback()
        self.assertEqual(result['status'], 'rolled-back-not-started')
        self.assertEqual(self.app.selected(), 'releases/v1')
        self.assertEqual(self.app.selected('previous'), 'releases/v2')
        popen.assert_not_called()

    def test_first_install_rollback_removes_only_own_activation(self):
        self.app.install(self.a)
        self.assertEqual(self.app.rollback()['status'], 'first-install-restored')
        self.assertIsNone(self.app.selected())
        self.assertFalse(self.app.launcher.exists())
        self.assertTrue((self.app.root / 'releases/v1').is_dir())

    def test_existing_launcher_is_backed_up_and_restored(self):
        self.app.launcher.parent.mkdir()
        self.app.launcher.write_text('original user launcher\n')
        self.app.launcher.chmod(0o750)
        result = self.app.install(self.a)
        backup = Path(result['backup'])
        self.assertEqual((backup / 'launcher').read_text(), 'original user launcher\n')
        self.app.rollback()
        self.assertEqual(self.app.launcher.read_text(), 'original user launcher\n')
        self.assertEqual(stat.S_IMODE(self.app.launcher.stat().st_mode), 0o750)

    def test_partial_switch_restores_real_prestate(self):
        self.app.launcher.parent.mkdir()
        self.app.launcher.write_text('existing')
        original = self.app.select
        def fail_current(name, target):
            if name == 'current':
                raise OSError('fixture atomic switch failure')
            original(name, target)
        with patch.object(self.app, 'select', side_effect=fail_current), self.assertRaises(OSError):
            self.app.install(self.a)
        self.assertFalse((self.app.root / 'current').exists())
        self.assertEqual(self.app.launcher.read_text(), 'existing')
        tx = next((self.app.state / 'transactions').glob('*/transaction.json'))
        self.assertEqual(json.loads(tx.read_text())['status'], 'restored-after-failure')

    def test_modified_launcher_blocks_rollback(self):
        self.app.install(self.a)
        self.app.launcher.write_text('new user changes')
        with self.assertRaisesRegex(ValueError, 'Launcher changed'):
            self.app.rollback()
        self.assertEqual(self.app.selected(), 'releases/v1')

    def test_same_version_cannot_be_replaced(self):
        self.app.install(self.a)
        changed = self.base / 'changed'
        import shutil
        shutil.copytree(self.a, changed, symlinks=True)
        path = changed / 'manager.py'
        path.chmod(0o644)
        path.write_text('different but self-consistent release')
        meta = json.loads((changed / 'release.json').read_text())
        meta['files'] = deploy.file_manifest(changed)
        (changed / 'release.json').write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, 'different contents'):
            self.app.install(changed)
        self.assertEqual(self.app.selected(), 'releases/v1')

    def test_changed_release_contents_modes_or_extra_files_are_rejected(self):
        path = self.a / 'helpers/network_nm.py'
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            deploy.verify_bundle(self.a)
        path.chmod(0o444)
        (self.a / 'unexpected').write_text('extra')
        with self.assertRaises(ValueError):
            deploy.verify_bundle(self.a)

    def test_absolute_runtime_alias_is_rejected(self):
        alias = self.a / 'runtime/bin/qs'
        alias.unlink()
        alias.symlink_to('/usr/bin/true')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            deploy.verify_bundle(self.a)

    def test_symlinked_bundle_and_install_parent_are_rejected(self):
        alias = self.base / 'alias'
        alias.symlink_to(self.a, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            deploy.verify_bundle(alias)
        self.app.root.parent.mkdir()
        self.app.root.symlink_to(self.base / 'elsewhere')
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            self.app.plan(self.a)

    def test_selector_traversal_is_rejected(self):
        self.app.root.mkdir(parents=True)
        (self.app.root / 'current').symlink_to('../../elsewhere')
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            self.app.selected()

    def test_symlinked_launcher_is_not_replaced(self):
        self.app.launcher.parent.mkdir()
        self.app.launcher.symlink_to(self.base / 'unrelated')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.app.plan(self.a)

    def test_installation_locations_must_not_overlap_or_contain_spaces(self):
        with self.assertRaises(ValueError):
            deploy.Installation(self.base / 'same', self.base / 'same/state', self.base / 'bin/omabuntu')
        with self.assertRaises(ValueError):
            deploy.Installation(self.base / 'space root', self.base / 'state', self.base / 'bin/omabuntu')

    def test_insecure_state_directory_is_refused(self):
        self.app.state.mkdir(mode=0o755, parents=True)
        self.app.state.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'private'):
            self.app.install(self.a)
        self.assertFalse(self.app.launcher.exists())

    def test_running_owned_process_prevents_update(self):
        self.app.install(self.a)
        with patch.object(self.app, 'running', return_value={'pid': 123}), self.assertRaisesRegex(ValueError, 'Stop'):
            self.app.install(self.b)
        self.assertEqual(self.app.selected(), 'releases/v1')

    def test_unrelated_or_reused_pid_is_not_stopped(self):
        self.app.state.mkdir(mode=0o700, parents=True)
        args = [str(self.app.root / 'releases/v1/runtime/bin/quickshell'), '--no-color', '--path',
                str(self.app.root / 'releases/v1/shell/TrialShell.qml')]
        record = {'pid': 123, 'identity': {'start_ticks': '1', 'argv': args}}
        deploy.atomic_json(self.app.state / 'running.json', record)
        with patch.object(deploy, 'identity', return_value={'start_ticks': '2', 'argv': args}), patch.object(deploy.os, 'kill') as kill:
            self.assertEqual(self.app.stop()['status'], 'not-running')
            kill.assert_not_called()
        record['identity']['argv'][0] = '/usr/bin/quickshell'
        deploy.atomic_json(self.app.state / 'running.json', record)
        with patch.object(deploy, 'identity', return_value=record['identity']), patch.object(deploy.os, 'kill') as kill:
            self.assertEqual(self.app.stop()['status'], 'not-running')
            kill.assert_not_called()

    def test_empty_hyprctl_instance_list_is_retried_before_start(self):
        self.assertIsNone(deploy.parse_hyprctl_instances('\n]\n'))
        payloads = ['\n]\n', '[{"instance": "sig", "wl_socket": "wayland-1"}]\n']

        def run():
            class Query:
                returncode = 0
                stdout = payloads.pop(0)
            return Query()

        found = deploy.read_hyprland_instances('sig', 'wayland-1', attempts=2, pause=0, run=run)
        self.assertEqual(found[0]['wl_socket'], 'wayland-1')

        def stuck():
            class Query:
                returncode = 0
                stdout = '\n]\n'
            return Query()

        with self.assertRaisesRegex(ValueError, 'not ready'):
            deploy.read_hyprland_instances('sig', 'wayland-1', attempts=2, pause=0, run=stuck)
        text = (ROOT / 'tools/user_install.py').read_text()
        self.assertIn('read_hyprland_instances(signature, display)', text)
        self.assertNotIn('json.loads(query.stdout)', text)

    def test_start_refuses_gnome_before_process_creation(self):
        self.app.install(self.a)
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'GNOME'}, clear=True), patch.object(deploy.subprocess, 'Popen') as popen:
            with self.assertRaisesRegex(ValueError, 'Hyprland session'):
                self.app.start()
            popen.assert_not_called()

    def test_status_does_not_create_installation_paths(self):
        with contextlib.redirect_stdout(io.StringIO()):
            deploy.main(['--root', str(self.app.root), '--state', str(self.app.state), '--launcher', str(self.app.launcher), 'status'])
        self.assertFalse(self.app.root.exists())
        self.assertFalse(self.app.state.exists())

    def test_installed_display_backup_uses_state_not_release_tree(self):
        directory = self.base / 'runtime-state'
        with patch.dict(os.environ, {'OMABUNTU_STATE_HOME': str(directory)}):
            display_backend.save_previous({'brightness': 70})
        path = next((directory / 'desktop-actions').glob('*.json'))
        self.assertEqual(json.loads(path.read_text()), {'brightness': 70})
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_lock_diagnostic_never_claims_authentication_or_recovery(self):
        with patch.object(lock_readiness, 'probe', return_value={'status': 'collected'}), patch.object(lock_readiness.shutil, 'which', return_value='/fixture/hyprlock'):
            result = lock_readiness.collect()
        self.assertFalse(result['authentication_verified'])
        self.assertFalse(result['recovery_verified'])
        self.assertFalse(result['activation_allowed'])
        for command in lock_readiness.COMMANDS.values():
            self.assertNotIn('lock-session', command)
            self.assertNotIn('sudo', command)
            self.assertNotIn('install', command)

    def test_boolean_schema_and_missing_notice_are_rejected(self):
        path = self.a / 'release.json'
        meta = json.loads(path.read_text())
        meta['schema_version'] = True
        path.write_text(json.dumps(meta))
        with self.assertRaises(ValueError):
            deploy.verify_bundle(self.a)
        meta['schema_version'] = 1
        notice = self.a / 'licenses/Omarchy-MIT.txt'
        notice.unlink()
        meta['files'] = deploy.file_manifest(self.a)
        path.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            deploy.verify_bundle(self.a)

    def test_changed_backup_blocks_restore_before_selectors_change(self):
        self.app.launcher.parent.mkdir()
        self.app.launcher.write_text('original')
        result = self.app.install(self.a)
        (Path(result['backup']) / 'launcher').write_text('corrupted backup')
        with self.assertRaisesRegex(ValueError, 'backup integrity'):
            self.app.rollback()
        self.assertEqual(self.app.selected(), 'releases/v1')
        self.assertEqual(self.app.launcher.read_text(), self.app.bootstrap())

    def test_only_exact_owned_process_receives_sigterm(self):
        record = {'pid': 456}
        with patch.object(self.app, 'running', side_effect=[record, None]), patch.object(deploy.os, 'kill') as kill:
            self.assertEqual(self.app.stop()['status'], 'stopped')
            kill.assert_called_once_with(456, deploy.signal.SIGTERM)

    def test_installed_helpers_cannot_write_bytecode_into_the_release(self):
        text = (ROOT / 'tools/user_install.py').read_text()
        self.assertIn("PYTHONDONTWRITEBYTECODE='1'", text)
        self.assertNotIn('import check_clock_preview', text)
        self.assertNotIn('import check_runtime', text)

    def test_prepared_transaction_blocks_activation_and_recovers_prestate(self):
        self.app.install(self.a)
        self.app.install(self.b)
        tx = sorted((self.app.state / 'transactions').glob('*/transaction.json'))[-1]
        pre = json.loads(tx.read_text())
        pre['status'] = 'prepared'
        deploy.atomic_json(tx, pre)
        with self.assertRaisesRegex(ValueError, 'Interrupted'):
            self.app.start()
        self.assertEqual(self.app.recover()['status'], 'prestate-restored')
        self.assertEqual(self.app.selected(), 'releases/v1')
        self.assertIsNone(self.app.selected('previous'))
        self.assertEqual(json.loads(tx.read_text())['status'], 'recovered')

    def test_corrupted_restore_selector_does_not_change_any_pointer(self):
        self.app.install(self.a)
        tx = next((self.app.state / 'transactions').glob('*/transaction.json'))
        pre = json.loads(tx.read_text())
        pre['previous'] = '../../unrelated'
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            self.app.restore(tx.parent, pre)
        self.assertEqual(self.app.selected(), 'releases/v1')

    def test_lock_probe_timeout_is_explicit(self):
        import subprocess
        with patch.object(lock_readiness.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['fixture'], 10)):
            self.assertEqual(lock_readiness.probe(['fixture'])['status'], 'timeout')


if __name__ == '__main__':
    unittest.main()


class WallpaperRestoreTests(unittest.TestCase):
    """Plan 020: start applies the recorded background, best-effort."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.app = deploy.Installation(self.base / 'data/omabuntu', self.base / 'state/omabuntu',
                                       self.base / 'bin/omabuntu')
        source = self.base / 'bundles/v1'
        for name in deploy.INCOMING:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture ' + name)
        marker = self.base / 'restore-marker'
        (source / 'helpers/background_backend.py').write_text(
            'import sys\n'
            'open(%r, "w").write(" ".join(sys.argv[1:]))\n'
            'print({"ok": True, "applied": True})\n' % str(marker))
        (source / 'release.json').write_text(json.dumps(
            {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': 'v1',
             'autostart': False, 'lock_activation': False,
             'files': deploy.file_manifest(source)}))
        self.app.install(source)
        self.release = self.app.root / 'releases/v1'

    def test_restore_runs_the_packaged_helper_and_never_fails_start(self):
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            self.app.restore_wallpaper(self.release)
        self.assertEqual((self.base / 'restore-marker').read_text(), 'restore')
        self.assertIn('Wallpaper restore:', captured.getvalue())

    def test_restore_keeps_the_sealed_release_valid_across_repeated_logins(self):
        # An imported sibling is enough to mutate a writable helper directory
        # unless the manager explicitly disables bytecode for this subprocess.
        helper = self.release / 'helpers/background_backend.py'
        helper.write_text('import menu_common\nprint("restored")\n')
        (self.release / 'helpers/menu_common.py').write_text('VALUE = 1\n')
        meta = json.loads((self.release / 'release.json').read_text())
        meta['files'] = deploy.file_manifest(self.release)
        (self.release / 'release.json').write_text(json.dumps(meta))
        with patch.dict(os.environ, {}, clear=True):
            self.app.restore_wallpaper(self.release)
            deploy.verify_bundle(self.release, installed=True)
            self.app.restore_wallpaper(self.release)
            deploy.verify_bundle(self.release, installed=True)
        self.assertFalse(list(self.release.rglob('__pycache__')))

    def test_restore_receives_the_actual_state_root(self):
        helper = self.release / 'helpers/background_backend.py'
        helper.write_text('import os\nprint(os.environ.get("OMABUNTU_STATE_HOME", "MISSING"))\n')
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            self.app.restore_wallpaper(self.release)
        self.assertIn(str(self.app.state), captured.getvalue())

    def attempt_start_until_process_creation(self, error='fixture stop'):
        import subprocess
        session = {'XDG_CURRENT_DESKTOP': 'Hyprland', 'HYPRLAND_INSTANCE_SIGNATURE': 'sig',
                   'WAYLAND_DISPLAY': 'wayland-1', 'XDG_STATE_HOME': str(self.base / 'xdg')}
        with patch.dict(os.environ, session, clear=True), \
                patch.object(Path, 'is_socket', return_value=True), \
                patch.object(deploy, 'read_hyprland_instances'), \
                patch.object(deploy.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)), \
                patch.object(self.app, 'restore_wallpaper') as restore, \
                patch.object(deploy.subprocess, 'Popen', side_effect=ValueError('fixture stop')) as popen:
            with self.assertRaisesRegex(ValueError, error):
                self.app.start()
        return restore, popen

    def test_start_prepares_workspace_state_before_any_optional_helper(self):
        restore, popen = self.attempt_start_until_process_creation()
        self.assertTrue((self.app.state / 'current').is_dir())
        self.assertEqual(stat.S_IMODE((self.app.state / 'current').stat().st_mode), 0o700)
        restore.assert_called_once_with(self.release)
        self.assertEqual(popen.call_args.kwargs['env']['XDG_STATE_HOME'], str(self.base / 'xdg'))

    def test_start_accepts_existing_current_directory_protected_by_private_state_parent(self):
        current = self.app.state / 'current'
        current.mkdir(mode=0o775)
        current.chmod(0o775)
        (current / 'font.txt').write_text('existing preference')
        restore, popen = self.attempt_start_until_process_creation()
        popen.assert_called_once()
        self.assertEqual(stat.S_IMODE(current.stat().st_mode), 0o775)
        self.assertEqual((current / 'font.txt').read_text(), 'existing preference')

    def test_start_still_rejects_symlinked_current_state(self):
        elsewhere = self.base / 'elsewhere'
        elsewhere.mkdir()
        (self.app.state / 'current').symlink_to(elsewhere)
        restore, popen = self.attempt_start_until_process_creation(error='Symlinked')
        restore.assert_not_called()
        popen.assert_not_called()

    def test_integrity_error_identifies_extra_files_without_their_contents(self):
        path = self.release / 'helpers/__pycache__/menu_common.pyc'
        path.parent.mkdir()
        path.write_text('private file contents')
        with self.assertRaisesRegex(ValueError, r'added.*helpers/__pycache__/menu_common.pyc') as error:
            deploy.verify_bundle(self.release, installed=True)
        self.assertNotIn('private file contents', str(error.exception))

    def test_missing_helper_is_a_silent_no_op(self):
        (self.release / 'helpers/background_backend.py').unlink()
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            self.app.restore_wallpaper(self.release)
        self.assertEqual(captured.getvalue(), '')

    def test_failing_helper_prints_a_note_and_does_not_raise(self):
        (self.release / 'helpers/background_backend.py').write_text('raise SystemExit(2)\n')
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            self.app.restore_wallpaper(self.release)
        self.assertIn('Wallpaper restore:', captured.getvalue())
