"""Original notification contracts; never connect to a desktop or user bus."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import notification_frontend as frontend
import notification_state as state
import check_notifications as checks


class NotificationSourcesTests(unittest.TestCase):
    def test_original_card_and_models_are_not_reauthored(self):
        files = frontend.sources(ROOT)
        for name in frontend.NAMES:
            original = (ROOT / 'vendor/omarchy/shell/plugins/notifications' / name).read_bytes()
            if name != 'Service.qml':
                self.assertEqual(files['Notifications/' + name], original)
            else:
                self.assertEqual(files['Notifications/' + name], frontend.service(original))
        self.assertIn('Notifications/Omapager-MIT.txt', files)
        self.assertIn(b'Neil Jagdish Patel', files['Notifications/Service.qml'])

    def test_service_has_closed_actions_private_state_and_no_upstream_helper(self):
        service = frontend.sources(ROOT)['Notifications/Service.qml'].decode()
        for absent in ('Util.execArgv(', 'omarchy-hyprland-focus-app', '"bash", "-c"',
                       'ShellIpc {', '/.local/state/omarchy/notifications'):
            self.assertNotIn(absent, service)
        self.assertIn('Actions.runArgv', service)
        self.assertIn('active: service.storeReady', service)
        self.assertIn('target: "omabuntuNotifications"', service)
        self.assertIn('id: liveFile', service)
        self.assertIn('atomicWrites: true', service)

    def test_height_feedback_excludes_departing_and_unreserved_rows(self):
        service = frontend.sources(ROOT)['Notifications/Service.qml'].decode()
        method = service.split('  function noteHeight(key, h) {', 1)[1].split(
            '  // ------------------------------------------------------- the scene clock', 1)[0]
        self.assertTrue(method.lstrip().startswith('if (!liveKeys[key] || leaving[key]) return'))
        self.assertLess(method.index('if (!liveKeys[key] || leaving[key]) return'),
                        method.index('Math.abs'))
        self.assertIn('if (key === arriving)', method)
        self.assertIn('commit(function() { service.heights[key] = h })', method)

    def test_height_adaptation_does_not_reorder_close_or_change_surfaces(self):
        original = (ROOT / 'vendor/omarchy/shell/plugins/notifications/Service.qml').read_bytes()
        derived = frontend.service(original)
        self.assertNotIn(b'if (!liveKeys[key] || leaving[key]) return', original)
        for begin, end in ((b'  function finishClose(', b'  function clearAll('),
                           (b'  function layoutWith(', b'  // A leaving card')):
            self.assertEqual(original.split(begin, 1)[1].split(end, 1)[0],
                             derived.split(begin, 1)[1].split(end, 1)[0])
        self.assertIn(b'onTargetHeightChanged: if (surface.showingNotifications) service.noteHeight(model.key, targetHeight)', derived)

    def test_changed_height_witness_refuses_derivation(self):
        original = (ROOT / 'vendor/omarchy/shell/plugins/notifications/Service.qml').read_bytes()
        with self.assertRaisesRegex(ValueError, 'witness changed'):
            frontend.service(original.replace(b'function noteHeight(key, h)', b'function changedHeight(key, h)'))

    def test_unknown_source_witness_is_not_silently_removed(self):
        original = (ROOT / 'vendor/omarchy/shell/plugins/notifications/Service.qml').read_bytes()
        with self.assertRaisesRegex(ValueError, 'witness changed'):
            frontend.service(original.replace(b'  ShellIpc {', b'  ChangedIpc {'))

    def test_tampered_original_adapter_notice_and_staged_digest_refuse(self):
        for path in ('vendor/omarchy/shell/plugins/notifications/Toast.qml',
                     'config/shell/preview/NotificationHost.qml',
                     'licenses/Omapager-MIT.txt', 'upstream/notifications.json'):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for source in frontend.INPUTS:
                    target = root / source
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(ROOT / source, target)
                target = root / path
                if path.endswith('.json'):
                    meta = json.loads(target.read_text())
                    meta['staged']['Notifications/Toast.qml'] = '0' * 64
                    target.write_text(json.dumps(meta))
                else:
                    target.write_bytes(target.read_bytes() + b' ')
                with self.assertRaises(ValueError):
                    frontend.sources(root)

    def test_host_is_inert_without_two_explicit_deployment_proofs(self):
        source = (ROOT / 'config/shell/preview/NotificationHost.qml').read_text()
        self.assertIn('property bool deploymentApproved: false', source)
        self.assertIn('property bool exclusiveRuntimeVerified: false', source)
        self.assertIn('deploymentApproved && exclusiveRuntimeVerified', source)
        self.assertIn('requested ? originalDnd : legacyDnd', source)
        self.assertNotIn('OMABUNTU_NOTIFICATION_ROLE', source)
        manager = (ROOT / 'tools/user_install.py').read_text()
        self.assertNotIn('deploymentApproved', manager)
        self.assertNotIn('exclusiveRuntimeVerified', manager)

    def test_runtime_candidate_has_no_registration_retry_or_queue(self):
        patch_text = (ROOT / 'native/notification-exclusive.patch').read_text()
        added = '\n'.join(line[1:] for line in patch_text.splitlines() if line.startswith('+') and not line.startswith('+++'))
        self.assertIn('DontQueueService', added)
        self.assertIn('DontAllowReplacement', added)
        self.assertIn('qFatal(', added)
        self.assertNotIn('serviceWatcher.setConnection', added)
        meta = json.loads((ROOT / 'upstream/notification-runtime.json').read_text())
        self.assertEqual(meta['status'], 'candidate-not-built-or-runtime-accepted')

    def test_contained_probe_has_no_real_service_or_surface(self):
        derived = frontend.sources(ROOT)['Notifications/Service.qml']
        fixture = checks.fixture_service(derived).decode()
        self.assertNotIn('import Quickshell.Services.Notifications', fixture)
        self.assertNotIn('import Quickshell.Hyprland', fixture)
        self.assertNotIn('PanelWindow {', fixture)
        self.assertNotIn('IpcHandler {', fixture)
        self.assertIn('original verification-code DND exception', checks.FIXTURE)
        with patch.object(checks, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(checks.main([]), 0)
        run.assert_not_called()


class NotificationStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'state'

    def test_new_files_are_private_valid_and_idempotent(self):
        directory = state.prepare(self.home)
        self.assertEqual(self.home.stat().st_mode & 0o777, 0o700)
        for name, default in state.DEFAULTS.items():
            path = directory / name
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text()), default)
        before = {p.name: (p.read_bytes(), p.stat().st_ino) for p in directory.iterdir()}
        state.prepare(self.home)
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_ino) for p in directory.iterdir()})

    def test_existing_quiet_state_is_not_reset(self):
        directory = state.prepare(self.home)
        (directory / 'quiet.json').write_text('{"dnd": true}\n')
        state.prepare(self.home)
        self.assertTrue(json.loads((directory / 'quiet.json').read_text())['dnd'])

    def test_malformed_state_is_preserved_and_no_missing_file_created(self):
        directory = state.prepare(self.home)
        bad = directory / 'live.json'
        bad.write_text('private sentinel malformed state')
        (directory / 'history.json').unlink()
        with self.assertRaises(ValueError):
            state.prepare(self.home)
        self.assertEqual(bad.read_text(), 'private sentinel malformed state')
        self.assertFalse((directory / 'history.json').exists())

    def test_invalid_record_is_not_silently_replaced_by_an_empty_history(self):
        directory = state.prepare(self.home)
        bad = directory / 'history.json'
        bad.write_text('[{"unknown":"preserve"}]')
        with self.assertRaises(ValueError):
            state.prepare(self.home)
        self.assertEqual(bad.read_text(), '[{"unknown":"preserve"}]')

    def test_public_state_permissions_are_refused_not_repaired(self):
        directory = state.prepare(self.home)
        path = directory / 'quiet.json'
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            state.prepare(self.home)
        self.assertEqual(path.stat().st_mode & 0o777, 0o644)

    def test_symlink_file_directory_and_ancestor_refuse(self):
        directory = state.prepare(self.home)
        path = directory / 'quiet.json'
        path.unlink()
        outside = Path(self.temp.name) / 'outside'
        outside.write_text('untouched')
        path.symlink_to(outside)
        with self.assertRaises(ValueError):
            state.prepare(self.home)
        self.assertEqual(outside.read_text(), 'untouched')
        link = Path(self.temp.name) / 'link'
        link.symlink_to(self.home, target_is_directory=True)
        with self.assertRaises(ValueError):
            state.prepare(link)
        with self.assertRaises(ValueError):
            state.prepare(link / 'nested')

    def test_hardlinked_and_oversized_files_refuse(self):
        directory = state.prepare(self.home)
        source = directory / 'live.json'
        os.link(source, Path(self.temp.name) / 'copy')
        with self.assertRaises(ValueError):
            state.prepare(self.home)
        source.unlink()
        source.write_bytes(b' ' * (state.LIMIT + 1))
        source.chmod(0o600)
        with self.assertRaises(ValueError):
            state.prepare(self.home)

    def test_prepare_errors_never_print_notification_content(self):
        with patch.object(state, 'prepare', side_effect=ValueError('secret sentinel')):
            with contextlib.redirect_stderr(io.StringIO()) as output:
                self.assertEqual(state.main(['prepare']), 1)
        self.assertNotIn('secret sentinel', output.getvalue())


if __name__ == '__main__':
    unittest.main()
