"""GNOME button-layout repair contracts (plan 074). No live GNOME key is
changed by these tests: gsettings is a recording stub."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import repair_gnome_buttons as repair

DEFAULT = repair.DEFAULT


class StubGsettings:
    """A recording gsettings stub over a fixture settings file."""

    SCRIPT = '''#!/usr/bin/python3
import json
import sys
settings = SETTINGS_PATH
log = LOG_PATH
key = KEY_NAME
args = sys.argv[1:]
if args[0] == 'get':
    print("'" + json.load(open(settings))[key] + "'")
elif args[0] == 'set':
    data = json.load(open(settings))
    data[key] = args[3]
    open(settings, 'w').write(json.dumps(data))
    with open(log, 'a') as handle:
        handle.write(key + ' ' + args[3] + chr(10))
'''

    def __init__(self, home, value):
        self.home = Path(home)
        self.settings = self.home / 'gsettings' / 'settings.json'
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.write_text(json.dumps({repair.KEY: value}))
        self.log = self.home / 'gsettings' / 'calls.log'
        self.log.write_text('')
        self.binary = self.home / 'gsettings' / 'gsettings'
        script = (self.SCRIPT
                   .replace('SETTINGS_PATH', json.dumps(str(self.settings)))
                   .replace('LOG_PATH', json.dumps(str(self.log)))
                   .replace('KEY_NAME', json.dumps(repair.KEY)))
        self.binary.write_text(script)
        self.binary.chmod(0o755)

    def set_value(self, value):
        data = json.loads(self.settings.read_text())
        data[repair.KEY] = value
        self.settings.write_text(json.dumps(data))

    def calls(self):
        return self.log.read_text().splitlines()


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'home'
        self.home.mkdir()
        self.stub = StubGsettings(self.temp.name, 'appmenu')

    def test_review_is_read_only_and_detects_the_manual_change(self):
        before = self.stub.settings.read_text()
        reviewed = repair.review(self.home, str(self.stub.binary))
        self.assertEqual(reviewed['current'], 'appmenu')
        self.assertEqual(reviewed['damage'], 'appmenu')
        self.assertTrue(reviewed['repair_needed'])
        self.assertEqual(reviewed['default'], DEFAULT)
        self.assertEqual(reviewed['records'], [])
        self.assertEqual(self.stub.calls(), [])
        self.assertEqual(before, self.stub.settings.read_text())

    def test_review_reports_untouched_values_without_calls(self):
        # Only the exact documented damage signature is offered for repair;
        # the stock schema default and any user layout stay silent.
        for value in (DEFAULT, 'appmenu:close', 'close,minimize,maximize:'):
            self.stub.set_value(value)
            reviewed = repair.review(self.home, str(self.stub.binary))
            self.assertFalse(reviewed['repair_needed'], value)
        self.assertEqual(self.stub.calls(), [])

    def test_apply_records_previous_value_then_restores_the_default(self):
        result = repair.apply(self.home, str(self.stub.binary))
        self.assertTrue(result['changed'])
        self.assertEqual(result['current'], DEFAULT)
        self.assertEqual(self.stub.calls(), ['{0} {1}'.format(repair.KEY, DEFAULT)])
        records = repair.record_paths(self.home)
        self.assertEqual(len(records), 1)
        record = json.loads(records[0].read_text())
        self.assertEqual(record['previous'], 'appmenu')
        self.assertEqual(record['new'], DEFAULT)
        self.assertEqual(record['restore_command'],
                         ['gsettings', 'set', repair.SCHEMA, repair.KEY, 'appmenu'])
        self.assertEqual(records[0].stat().st_mode & 0o777, 0o600)

    def test_apply_is_a_noop_outside_the_damage_signature(self):
        self.stub.set_value('appmenu:close')
        result = repair.apply(self.home, str(self.stub.binary))
        self.assertFalse(result['changed'])
        self.assertEqual(self.stub.calls(), [])
        self.assertEqual(repair.record_paths(self.home), [])

    def test_rollback_restores_the_recorded_previous_value(self):
        repair.apply(self.home, str(self.stub.binary))
        self.stub.set_value(DEFAULT)
        result = repair.rollback(self.home, str(self.stub.binary))
        self.assertTrue(result['changed'])
        self.assertEqual(result['current'], 'appmenu')
        self.assertEqual(self.stub.calls(), ['{0} {1}'.format(repair.KEY, DEFAULT),
                                            '{0} {1}'.format(repair.KEY, 'appmenu')])
        record = json.loads(repair.record_paths(self.home)[-1].read_text())
        self.assertIn('restored_at', record)

    def test_rollback_without_a_record_changes_nothing(self):
        result = repair.rollback(self.home, str(self.stub.binary))
        self.assertFalse(result['changed'])
        self.assertEqual(self.stub.calls(), [])

    def test_rollback_uses_the_latest_record(self):
        for previous in ('appmenu', 'appmenu:close'):
            repair.review(self.home, str(self.stub.binary))
            repair.write_record(self.home, previous)
        self.stub.set_value(DEFAULT)
        result = repair.rollback(self.home, str(self.stub.binary))
        self.assertTrue(result['changed'])
        self.assertEqual(result['current'], 'appmenu:close')

    def test_failing_gsettings_is_refused_without_a_record(self):
        missing = str(self.home / 'missing-gsettings')
        with self.assertRaises((OSError, ValueError)):
            repair.review(self.home, missing)
        self.assertEqual(repair.record_paths(self.home), [])

    def test_unsafe_home_is_refused(self):
        linked = self.home / 'linked'
        linked.symlink_to(self.home)
        with self.assertRaises(ValueError):
            repair.check_home(linked)

    def test_quoted_values_are_parsed_and_weird_values_rejected(self):
        self.assertEqual(repair.parse_value("'appmenu'"), 'appmenu')
        self.assertEqual(repair.parse_value('appmenu:minimize,maximize,close'),
                         'appmenu:minimize,maximize,close')
        with self.assertRaises(ValueError):
            repair.parse_value("''")
        with self.assertRaises(ValueError):
            repair.parse_value("'weird'quote'")


if __name__ == '__main__':
    unittest.main()