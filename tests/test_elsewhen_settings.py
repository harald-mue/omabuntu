"""Persistent Elsewhen preferences; all writes stay in workspace fixtures."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import elsewhen_settings as settings
import check_clock_preview as checker


class ElsewhenSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.env = patch.dict(os.environ, OMABUNTU_STATE_HOME=str(self.base))
        self.env.start()
        self.addCleanup(self.env.stop)
        self.payload = {'id': 'omarchy.elsewhen', 'cities': [
            {'name': 'Vienna', 'zone': 'Europe/Vienna', 'lat': 48.2, 'lon': 16.3,
             'people': ['Alice', '@bob'], 'region': 'Austria'},
            {'name': 'Tokyo', 'zone': 'Asia/Tokyo'}],
            'here': {'name': 'Vienna', 'zone': 'Europe/Vienna'},
            'hour24': True, 'offsetMode': 'utc', 'units': 'C',
            'globeEnabled': False, 'smoothMotion': True}

    def save(self, value):
        settings.save(json.dumps(value))

    def test_missing_load_is_read_only(self):
        self.assertEqual(settings.load(), {})
        self.assertEqual(list(self.base.iterdir()), [])

    def test_round_trip_across_process_restart(self):
        self.save(self.payload)
        result = subprocess.run([sys.executable, str(ROOT / 'tools/elsewhen_settings.py'), 'load'],
                                capture_output=True, text=True, timeout=5, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), self.payload)
        self.assertEqual(settings.settings_path().stat().st_mode & 0o777, 0o600)

    def test_order_removal_empty_and_preferences_survive(self):
        self.save(self.payload)
        changed = dict(self.payload, cities=list(reversed(self.payload['cities'])), hour24=False)
        self.save(changed)
        self.assertEqual(settings.load(), changed)
        changed['cities'] = changed['cities'][1:]
        self.save(changed)
        self.assertEqual(settings.load()['cities'], changed['cities'])
        changed['cities'] = []
        changed.pop('here')
        self.save(changed)
        self.assertEqual(settings.load(), changed)

    def test_exact_backup_prestate_and_noop(self):
        self.save(self.payload)
        previous = settings.settings_path().read_bytes()
        self.save({'cities': []})
        backups = list((self.base / 'backups').glob('*/elsewhen.json'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), previous)
        operations = (self.base / 'operations.jsonl').read_text()
        records = [json.loads(line) for line in operations.splitlines()]
        self.assertFalse(records[0]['detail']['existed'])
        self.assertEqual(Path(records[-1]['backup']) / 'elsewhen.json', backups[0])
        self.save({'cities': []})
        self.assertEqual((self.base / 'operations.jsonl').read_text(), operations)

    def test_rejects_invalid_payload_before_writing(self):
        for value in ([], {'unknown': 1}, {'cities': 'Tokyo'}, {'hour24': 1},
                      {'units': 'K'}, {'id': 'other'}, {'cities': [{'name': 'x', 'zone': ';id'}]},
                      {'cities': [{'name': 'x', 'zone': 'UTC', 'lat': 91, 'lon': 0}]},
                      {'cities': [{'name': 'x', 'zone': 'UTC', 'people': [False]}]}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.save(value)
        with self.assertRaises(ValueError):
            settings.save(' ' * (settings.MAX_BYTES + 1))
        self.assertEqual(list(self.base.iterdir()), [])

    def test_corrupt_and_oversize_state_are_not_overwritten(self):
        path = settings.settings_path()
        path.parent.mkdir()
        for data in (b'broken', b'[]', b'x' * (settings.MAX_BYTES + 1)):
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                settings.load()
            with self.assertRaises(ValueError):
                self.save({'cities': []})
            self.assertEqual(path.read_bytes(), data)

    def test_symlink_file_and_parent_are_rejected(self):
        target = self.base / 'other'
        target.mkdir()
        (self.base / 'settings').symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            settings.load()
        with self.assertRaises(ValueError):
            self.save({})
        (self.base / 'settings').unlink()
        (self.base / 'settings').mkdir()
        settings.settings_path().symlink_to(target / 'missing')
        with self.assertRaises(ValueError):
            settings.load()
        self.assertFalse((target / 'missing').exists())

    def test_failed_atomic_replace_preserves_original(self):
        self.save(self.payload)
        before = settings.settings_path().read_bytes()
        with patch.object(settings.os, 'replace', side_effect=OSError('fixture')):
            with self.assertRaises(OSError):
                self.save({'cities': []})
        self.assertEqual(settings.settings_path().read_bytes(), before)
        self.assertEqual(list(settings.settings_path().parent.glob('.elsewhen-*')), [])

    def test_cli_reports_failure_and_rejects_unknown_commands(self):
        self.assertEqual(settings.main(['other']), 2)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(settings.main(['save', 'bad']), 1)

    def test_shared_adapter_and_startup_order_are_staged(self):
        files, _ = checker.verified_sources(ROOT)
        panel = files['Elsewhen/ElsewhenPanel.qml'].decode()
        adapter = files['Commons/ElsewhenSettings.qml'].decode()
        self.assertIn('settings: Commons.ElsewhenSettings.settings', panel)
        self.assertNotIn('root.settings = entry', panel)
        self.assertIn('Commons.ElsewhenSettings.save(entry)', panel)
        self.assertIn('if (!settingsReady) return', panel)
        self.assertIn('setting("cities", null) === null && zones.length === 0', panel)
        self.assertIn('Commons.ElsewhenSettings.errorText ||', panel)
        self.assertIn('pragma Singleton', adapter)
        self.assertIn('singleton ElsewhenSettings 1.0 ElsewhenSettings.qml', files['Commons/qmldir'].decode())

    @unittest.skipUnless(shutil.which('node'), 'Node is required for QML adapter logic checks')
    def test_shared_adapter_serializes_and_coalesces_pending_writes(self):
        source = (ROOT / 'config/shell/preview/ElsewhenSettings.qml').read_text()
        # Run the actual adapter functions with a fake asynchronous process.
        functions = source[source.index('  function save('):source.index('  Component.onCompleted:')]
        script = '''
const assert = require('assert');
let ready = false, settings = {}, pending = '', helper = '/fixture/helper.py';
const calls = [];
const backend = {running: false, exec: args => {calls.push(args); backend.running = true;}};
''' + functions + '''
save({cities: ['ignored before load']});
assert.equal(calls.length, 0);
ready = true;
save({cities: ['Vienna']});
save({cities: ['Tokyo', 'Vienna']});
save({cities: []});
assert.equal(calls.length, 1);
assert.deepEqual(settings, {cities: []});
backend.running = false;
pump();
assert.equal(calls.length, 2);
assert.deepEqual(JSON.parse(calls[1][3]), {cities: []});
backend.running = false;
pump();
assert.equal(calls.length, 2);
'''
        result = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
