"""Original monitor controls with fake compositor/state; no live desktop writes."""
import copy
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import display_backend as backend
import display_profiles as profiles


def monitors():
    # An existing gap must not force profile adoption or layout normalization.
    return [dict(name=name, make='Fixture', model='Panel', serial=name,
                 width=1920, height=1080, refreshRate=60, scale=1, transform=0,
                 x=x, y=0, disabled=False, focused=index == 0)
            for index, (name, x) in enumerate((('DP-1', 0), ('DP-2', 3000)))]


class Native:
    def __init__(self):
        self.owner = dict(signature='fixture', pid=1, start='2', inode=3)
        self.monitors = monitors()
        self.calls = []
        self.ack = 'ok'
        self.observe = True
        self.fail_after_write = False

    def inventory(self):
        if self.calls and self.fail_after_write:
            raise ValueError('Compositor owner changed')
        return copy.deepcopy(self.monitors)

    def run(self, args):
        self.calls.append(args)
        match = re.fullmatch(r'hl.monitor\(\{ output = "(DP-[12])", disabled = (true|false) \}\); return "ok"', args[1])
        if not match:
            raise ValueError('Unexpected fake mutation')
        if self.observe:
            next(m for m in self.monitors if m['name'] == match[1])['disabled'] = match[2] == 'true'
        return self.ack


class DisplayControlsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.native = Native()
        self.profiles = profiles.Profiles(self.home, native=self.native)
        self.env = patch.dict(os.environ, {'OMABUNTU_STATE_HOME': str(self.home)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.light = patch.object(backend, 'backlight', return_value=None)
        self.light.start()
        self.addCleanup(self.light.stop)

    def key(self):
        return backend.status(self.native)['control_key']

    def switch(self, name='DP-2', enabled=True, key=None):
        return backend.toggle(self.native, self.profiles, name, enabled, key or self.key())

    def receipts(self):
        return sorted((self.home / 'desktop-actions').glob('*.json'))

    def test_gapped_status_is_read_only_without_profile_state(self):
        result = backend.status(self.native)
        self.assertEqual(result['displays'][1]['x'], 3000)
        self.assertRegex(result['control_key'], r'^[a-f0-9]{64}$')
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertEqual(self.native.calls, [])

    def test_switch_retains_gap_geometry_and_only_changes_disabled(self):
        before = copy.deepcopy(self.native.monitors)
        result = self.switch()
        self.assertTrue(result['displays'][1]['disabled'])
        before[1]['disabled'] = True
        self.assertEqual(self.native.monitors, before)
        self.assertEqual(len(self.native.calls), 1)
        self.assertFalse(self.profiles.path.exists())
        data = [json.loads(p.read_text()) for p in self.receipts()]
        self.assertEqual(len(data), 2)
        self.assertTrue(any(d.get('action') == 'toggle' and d['before']['displays'][1]['x'] == 3000 for d in data))
        self.assertTrue(any(d.get('status') == 'observed' for d in data))
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in self.receipts()))

    def test_backup_is_durable_before_the_only_native_write(self):
        original = self.native.run
        def write(args):
            backups = self.receipts()
            self.assertEqual(len(backups), 1)
            self.assertEqual(json.loads(backups[0].read_text())['owner'], self.native.owner)
            self.assertFalse(json.loads(backups[0].read_text())['before']['displays'][1]['disabled'])
            return original(args)
        with patch.object(self.native, 'run', side_effect=write):
            self.switch()

    def test_enable_uses_original_partial_rule_without_full_profile_validation(self):
        self.native.monitors[1]['disabled'] = True
        result = self.switch(enabled=False)
        self.assertFalse(result['displays'][1]['disabled'])
        self.assertIn('disabled = false', self.native.calls[0][1])
        for excluded in ('position =', 'scale =', 'mode =', 'reload'):
            self.assertNotIn(excluded, self.native.calls[0][1])

    def test_last_active_output_refuses_before_backup_and_write(self):
        self.native.monitors[0]['disabled'] = True
        with self.assertRaisesRegex(ValueError, 'last active'):
            self.switch()
        self.assertEqual(self.native.calls, [])
        self.assertEqual(self.receipts(), [])

    def test_stale_topology_geometry_identity_or_owner_refuses(self):
        for field, value in (('serial', 'replacement'), ('x', 4000), ('disabled', True)):
            with self.subTest(field=field):
                self.native.monitors = monitors()
                key = self.key()
                self.native.monitors[1][field] = value
                with self.assertRaisesRegex(ValueError, 'changed'):
                    self.switch(key=key)
        self.native.monitors = monitors()
        key = self.key()
        self.native.owner['inode'] += 1
        with self.assertRaisesRegex(ValueError, 'owner changed'):
            self.switch(key=key)
        self.assertEqual(self.native.calls, [])
        self.assertEqual(self.receipts(), [])

    def test_stale_row_enabled_state_and_duplicate_names_refuse(self):
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.switch(enabled=False)
        self.native.monitors.append(copy.deepcopy(self.native.monitors[1]))
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.switch()
        self.assertEqual(self.native.calls, [])

    def test_invalid_output_state_or_observation_refuses(self):
        for name, enabled in (('DP-2"});', True), ('missing', True), ('DP-2', 1)):
            with self.subTest(name=name, enabled=enabled), self.assertRaises(ValueError):
                backend.toggle_program(self.native.monitors, name, enabled)
        with self.assertRaisesRegex(ValueError, 'observation'):
            self.switch(key='bad')
        self.native.monitors[0]['disabled'] = 'false'
        with self.assertRaisesRegex(ValueError, 'Invalid output state'):
            self.switch()
        self.assertEqual(self.native.calls, [])

    def test_pending_profile_recovery_fences_normal_switches(self):
        profiles.put(self.profiles.pending_path, dict(token='a' * 32, status='prepared', deadline=100))
        with self.assertRaisesRegex(ValueError, 'Pending monitor transaction'):
            self.switch()
        self.assertEqual(self.native.calls, [])
        self.assertIsNotNone(self.profiles.pending())

    def test_missing_acknowledgement_retains_uncertainty_without_replay(self):
        self.native.ack = 'error'
        with self.assertRaisesRegex(ValueError, 'not acknowledged'):
            self.switch()
        self.assertEqual(len(self.native.calls), 1)
        outcomes = [json.loads(p.read_text()) for p in self.receipts() if p.name.endswith('.outcome.json')]
        self.assertEqual(outcomes[0]['status'], 'uncertain')

    def test_owner_loss_after_write_is_not_compensated_or_replayed(self):
        self.native.fail_after_write = True
        with self.assertRaisesRegex(ValueError, 'owner changed'):
            self.switch()
        self.assertEqual(len(self.native.calls), 1)
        self.assertEqual(len(self.receipts()), 2)

    def test_unobserved_result_times_out_without_second_setter(self):
        self.native.observe = False
        with patch.object(backend.time, 'monotonic', side_effect=[0, 4]):
            with self.assertRaisesRegex(ValueError, 'not observed'):
                self.switch()
        self.assertEqual(len(self.native.calls), 1)
        outcome = next(p for p in self.receipts() if p.name.endswith('.outcome.json'))
        self.assertEqual(json.loads(outcome.read_text())['status'], 'uncertain')

    def test_normal_text_control_needs_no_profile_or_native_write(self):
        current = self.home / 'current'
        current.mkdir(mode=0o775)
        current.chmod(0o775)
        with patch.object(profiles, 'Native', return_value=self.native), patch('builtins.print'):
            backend.main(['text', '14'])
        self.assertEqual(self.profiles.text_size(), 14)
        self.assertEqual(current.stat().st_mode & 0o777, 0o775)
        self.assertEqual(self.native.calls, [])
        self.assertFalse(self.profiles.path.exists())
        backup = next((self.profiles.directory / 'backups').glob('*.json'))
        self.assertFalse(json.loads(backup.read_text())['text']['existed'])

    def test_normal_text_control_preserves_previous_file_and_mode_in_backup(self):
        profiles.atomic(self.profiles.text_path, b'12\n')
        self.profiles.text_path.chmod(0o640)
        with patch.object(profiles, 'Native', return_value=self.native), patch('builtins.print'):
            backend.main(['text', '16'])
        self.assertEqual(self.profiles.text_size(), 16)
        backup = json.loads(next((self.profiles.directory / 'backups').glob('*.json')).read_text())
        self.assertEqual(backup['text']['mode'], 0o640)
        self.assertEqual(backup['text']['data'], 'MTIK')
        self.assertEqual(self.native.calls, [])

    def test_invalid_text_does_not_create_state_or_write(self):
        with patch.object(profiles, 'Native', return_value=self.native), patch('builtins.print'):
            for value in ('100', '13', 'NaN', '9;bad'):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    backend.main(['text', value])
        self.assertEqual(self.native.calls, [])
        self.assertEqual(list(self.home.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
