"""Update menu contracts: temporary bundles, synthetic network, no live actions."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import application_update as runner
import install as guided
import menu_model
import menu_update
import published_release as public
import release_update
import update_payload
import user_install


class MetadataTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.calls = []
        self.verified = False
        archive = 'omabuntu-0.3.0-ubuntu-26.04-x86_64.tar.gz'
        metadata = {'version': '0.3.0', 'target': public.TARGET, 'archive': archive,
                    'sha256': 'a' * 64, 'bytes': 10}
        raw = json.dumps(metadata).encode()
        self.data = {'github.json': json.dumps({'tag_name': 'v0.3.0'}).encode(),
                     'release.json': raw, 'SHA256SUMS.sig': b'synthetic',
                     'SHA256SUMS': (hashlib.sha256(raw).hexdigest() + '  release.json\n' + 'a' * 64 + '  ' + archive + '\n').encode()}

    def fetch(self, url, path, limit):
        name = 'github.json' if url.endswith('/latest') else url.rsplit('/', 1)[1]
        self.calls.append(name)
        if name == 'release.json':
            self.assertTrue(self.verified)
        path.write_bytes(self.data[name])

    def verify(self, *args):
        self.verified = True

    def test_signed_metadata_check_does_not_download_or_install_archive(self):
        info = public.discover(self.base / 'key', self.base, fetch=self.fetch, verify=self.verify)
        self.assertEqual(info['version'], '0.3.0')
        self.assertEqual(self.calls, ['github.json', 'SHA256SUMS', 'SHA256SUMS.sig', 'release.json'])

    def test_signature_failure_stops_before_metadata_or_archive(self):
        with self.assertRaisesRegex(ValueError, 'bad signature'):
            public.discover(self.base / 'key', self.base, fetch=self.fetch,
                            verify=Mock(side_effect=ValueError('bad signature')))
        self.assertNotIn('release.json', self.calls)

    def test_malformed_discovery_is_refused_before_signature_fetch(self):
        self.data['github.json'] = b'[]'
        with self.assertRaisesRegex(ValueError, 'discovery response'):
            public.discover(self.base / 'key', self.base, fetch=self.fetch, verify=self.verify)
        self.assertEqual(self.calls, ['github.json'])

    def test_tampered_metadata_is_refused(self):
        self.data['release.json'] += b' '
        with self.assertRaisesRegex(ValueError, 'checksum'):
            public.discover(self.base / 'key', self.base, fetch=self.fetch, verify=self.verify)

    def test_offline_propagates_without_installer(self):
        with self.assertRaises(OSError):
            public.discover(self.base / 'key', self.base, fetch=Mock(side_effect=OSError('offline')))

    def test_archive_mismatch_stops_before_extract(self):
        with patch.object(public.release_archive, 'extract') as extract:
            with self.assertRaisesRegex(ValueError, 'checksum'):
                public.download({'archive': 'file.tar.gz', 'url': 'https://github.com/fixture',
                                 'bytes': 3, 'sha256': 'a'*64}, self.base,
                                fetch=lambda url, path, limit: path.write_bytes(b'bad'))
            extract.assert_not_called()

    def test_version_and_local_provenance_policy(self):
        self.assertEqual(public.availability('0.2.0', '0.3.0', {'local_image_directories': []}), 'newer')
        self.assertEqual(public.availability('0.3.0', '0.3.0', {}), 'current')
        self.assertEqual(public.availability('0.4.0', '0.3.0', {}), 'downgrade-blocked')
        for version, provenance in [('battery-layout-097-local', {}), ('0.2.0', {'local_battery_layout_correction': {}}),
                                    ('0.2.0', None), ('0.2.0', {'local_unknown': True})]:
            self.assertEqual(public.availability(version, '0.3.0', provenance), 'local-release-blocked')
        for version in ('v0.3.0', '0.03.0', '0.3.0; reboot', '0.3.0-rc1'):
            with self.assertRaises(ValueError):
                public.version_tuple(version)


    def test_publisher_bundle_versions_preserve_local_and_downgrade_guards(self):
        for installed, incoming, status in (
                ('release-0.2.1', '0.2.2', 'newer'),
                ('release-0.2.1', '0.2.1', 'current'),
                ('release-0.2.1', '0.2.0', 'downgrade-blocked'),
                ('release-0.2.9', '0.2.10', 'newer')):
            self.assertEqual(public.availability(installed, incoming, {}), status)
        for installed in ('release-release-0.2.1', 'release-0.02.1', 'release-0.2.1-local'):
            self.assertEqual(public.availability(installed, '0.2.2', {}), 'local-release-blocked')
        self.assertEqual(public.availability('release-0.2.1', '0.2.2',
            {'local_correction': True}), 'local-release-blocked')
        with self.assertRaises(ValueError):
            public.availability('release-0.2.1', 'release-0.2.2', {})


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.app = runner.ApplicationInstallation(self.base/'app', self.base/'state', self.base/'bin/omabuntu')
        self.live = None
        running = patch.object(self.app, 'running', side_effect=lambda: self.live)
        running.start(); self.addCleanup(running.stop)
        self.a = self.bundle('release-0.2.0')
        self.b = self.bundle('release-0.3.0')
        self.app.install(self.a)
        self.live = {'pid': 10, 'release': self.app.selected()}
        self.directory = self.base/'reports'; self.directory.mkdir(mode=0o700)
        self.discover = Mock(return_value={'version': '0.3.0'})
        self.download = Mock(return_value=self.b)
        self.confirm = Mock(return_value=True)
        self.emit = Mock()

    def bundle(self, version):
        path = self.base/'bundles'/version; path.mkdir(parents=True)
        for name in user_install.INCOMING:
            target = path/name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('synthetic ' + name)
            target.chmod(0o755 if name == 'runtime/bin/quickshell' else 0o444)
        (path/'PROVENANCE.json').write_text('{}')
        meta = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': version,
                'autostart': False, 'lock_activation': False, 'update_contract': release_update.contract(),
                'files': user_install.file_manifest(path)}
        (path/'release.json').write_text(json.dumps(meta))
        return path

    def run_review(self, **kwargs):
        return runner.review_update(self.app, self.base/'resources', self.directory, self.confirm,
                                    emit=self.emit, discover=self.discover, download=self.download, **kwargs)

    def test_cancel_check_does_no_network_or_deployment(self):
        self.confirm.return_value = False
        result = self.run_review()
        self.assertEqual(result['status'], 'cancelled-before-check')
        self.discover.assert_not_called(); self.download.assert_not_called()
        self.assertEqual(self.app.selected(), 'releases/release-0.2.0')

    def test_cancel_download_has_no_candidate_or_deployment(self):
        self.confirm.side_effect = [True, False]
        self.assertEqual(self.run_review()['status'], 'cancelled-before-download')
        self.download.assert_not_called()

    def test_same_version_never_downloads(self):
        self.discover.return_value = {'version': '0.2.0'}
        self.assertEqual(self.run_review()['status'], 'current')
        self.download.assert_not_called()

    def test_public_downgrade_is_blocked_before_archive_download(self):
        self.discover.return_value = {'version': '0.1.0'}
        self.assertEqual(self.run_review()['status'], 'downgrade-blocked')
        self.download.assert_not_called()

    def test_bundle_version_mismatch_still_blocks_apply(self):
        self.download.return_value = self.bundle('release-0.4.0')
        apply = Mock()
        with self.assertRaisesRegex(ValueError, 'Bundle version differs'):
            self.run_review(apply=apply)
        apply.assert_not_called()

    def test_cancel_exact_plan_does_not_apply(self):
        self.confirm.side_effect = [True, True, False]
        apply = Mock()
        self.assertEqual(self.run_review(apply=apply)['status'], 'cancelled-before-apply')
        apply.assert_not_called()

    def test_selection_drift_after_download_is_refused(self):
        self.download.side_effect = lambda *args: (setattr(self, 'live', {'pid': 99}), self.b)[1]
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.run_review()
        self.assertEqual(self.app.selected(), 'releases/release-0.2.0')

    def test_stopped_shell_is_never_implicitly_started(self):
        self.live = None
        with self.assertRaisesRegex(ValueError, 'running'):
            self.run_review()
        self.discover.assert_not_called()

    def transaction(self, fail_start=False, preflight_status='passed'):
        events = []
        def start(*, restore_background=True):
            self.assertFalse(restore_background)
            events.append('start-' + self.app.selected())
            if fail_start and self.app.selected() == 'releases/release-0.3.0':
                raise ValueError('synthetic startup failure')
            self.live = {'pid': 11, 'release': self.app.selected()}
            return {'status': 'running'}
        def stop():
            events.append('stop'); self.live = None
        with patch.object(user_install.Installation, 'start', side_effect=start), \
             patch.object(self.app, 'stop', side_effect=stop), \
             patch.object(release_update, 'locker_absent'), \
             patch.object(guided, 'preflight', return_value=({'status': preflight_status}, self.directory/'fixture.json')) as preflight:
            result = self.run_review()
        self.assertEqual(preflight.call_args.kwargs['report_root'], self.directory)
        return result, events

    def test_actual_transaction_preserves_preferences_and_disables_wallpaper(self):
        prefs = self.app.state/'settings.json'; prefs.write_text('{"keep": true}')
        result, events = self.transaction()
        self.assertEqual(result['status'], 'updated-and-started')
        self.assertEqual(self.app.selected('previous'), 'releases/release-0.2.0')
        self.assertEqual(prefs.read_text(), '{"keep": true}')
        self.assertEqual(events, ['stop', 'start-releases/release-0.3.0'])

    def test_start_failure_restores_previous_selection_without_wallpaper(self):
        with self.assertRaises(release_update.UpdateError):
            self.transaction(fail_start=True)
        self.assertEqual(self.app.selected(), 'releases/release-0.2.0')
        self.assertEqual(self.live['release'], 'releases/release-0.2.0')

    def test_missing_prerequisites_block_before_stop(self):
        with self.assertRaisesRegex(release_update.UpdateError, 'preflight'):
            self.transaction(preflight_status='blocked')
        self.assertEqual(self.live['pid'], 10)
        self.assertEqual(self.app.selected(), 'releases/release-0.2.0')


class LauncherAndPayloadTests(unittest.TestCase):
    def test_closed_action_does_not_launch_on_definitions_or_guards(self):
        items, order = menu_model.merge_menu_sources(menu_model.parse_menu_jsonc(
            (ROOT/'config/shell/omabuntu-menu.jsonc').read_text()))
        # Definitions and guards must not start the updater or contact a service.
        self.assertEqual(items['update.omabuntu']['action'], 'omabuntu-update:review')
        with patch.object(menu_update, 'launch', return_value={'ok': True}) as launch:
            with patch.object(menu_model.appearance_backend, 'guards', return_value={'when': {}, 'checked': {}, 'disabled': {}}):
                menu_model.evaluate_guards(items, run=lambda _: (0, ''))
            launch.assert_not_called()
            result = menu_model.run_item('update.omabuntu', (items, order))
            self.assertTrue(result['ok']); launch.assert_called_once()
            items['update.omabuntu']['action'] = 'omabuntu-update:review; reboot'
            self.assertFalse(menu_model.run_item('update.omabuntu', (items, order))['ok'])
            self.assertEqual(launch.call_count, 1)

    def test_payload_imports_and_resources_work_without_checkout_or_reports(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as temporary:
            target = Path(temporary)
            update_payload.stage(ROOT, target)
            tools = target/'updater/tools'
            code = ('import sys;sys.path.insert(0,sys.argv[1]); import application_update, release_update, plugin_manager; '
                    'assert release_update.contract()["user_state_schema"] == 1; '
                    'assert plugin_manager.policy()["manager"] == "hyprpm"')
            completed = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(tools)],
                                       cwd=target, capture_output=True, text=True, timeout=15)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(list(target.rglob('__pycache__')))
            self.assertFalse((target/'updater/work').exists())
            self.assertEqual((target/'updater/config/release-signing-key.pub').read_bytes(),
                             (ROOT/'config/release-signing-key.pub').read_bytes())

    def test_reports_can_be_relocated_outside_immutable_payload(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as temporary:
            case = guided.private_case(Path(temporary)/'reports')
            self.assertTrue(case.is_relative_to(Path(temporary)/'reports'))

    def test_launcher_uses_fixed_argv_and_independent_session(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as temporary:
            root = Path(temporary)
            (root/'helpers').mkdir()
            helper = root/'helpers/menu_update.py'; helper.write_text('synthetic')
            runner_file = root/'updater/tools/application_update.py'
            runner_file.parent.mkdir(parents=True); runner_file.write_text('synthetic')
            (root/'release.json').write_text('{}')
            with patch.object(menu_update, '__file__', str(helper)), \
                 patch.object(menu_update.shutil, 'which', return_value='/usr/bin/xdg-terminal-exec'), \
                 patch.object(menu_update.subprocess, 'Popen') as popen:
                self.assertTrue(menu_update.launch()['ok'])
                args, kwargs = popen.call_args
                self.assertEqual(args[0][-3:], [sys.executable, '-B', str(runner_file)])
                self.assertTrue(kwargs['start_new_session'])
                self.assertNotIn('shell', kwargs)

    def test_noninteractive_runner_refuses_without_network_or_state(self):
        with patch.object(sys, 'argv', ['application_update.py']), \
             patch.object(sys, 'stdin', io.StringIO()), \
             patch.object(runner, 'cache_root') as cache:
            with self.assertRaisesRegex(ValueError, 'interactive terminal'):
                runner.main()
            cache.assert_not_called()

    def test_ambiguous_or_gnome_session_is_refused(self):
        for desktop in ('GNOME', 'Hyprland:GNOME', ''):
            self.assertFalse(runner.session_allowed({'XDG_CURRENT_DESKTOP': desktop}))


if __name__ == '__main__':
    unittest.main()
