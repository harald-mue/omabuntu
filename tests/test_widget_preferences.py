"""Calendar/tray persistence and shared QML patches; no desktop actions."""
import contextlib
from concurrent.futures import ThreadPoolExecutor
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
import appearance_backend as backend
import check_clock_preview as preview
import menu_model

NODE = shutil.which('node')


def qml_function(source, name):
    start = source.index('function ' + name + '(')
    opened = source.index('{', start)
    depth = 0
    for end in range(opened, len(source)):
        depth += (source[end] == '{') - (source[end] == '}')
        if depth == 0:
            return source[start:end + 1]
    raise AssertionError('Unbalanced function: ' + name)


class WidgetPreferenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.state = self.home / 'state'
        self.env = {'HOME': str(self.home), 'OMABUNTU_STATE_HOME': str(self.state),
                    'XDG_CONFIG_HOME': str(self.home / 'config'),
                    'XDG_CURRENT_DESKTOP': 'Hyprland', 'XDG_SESSION_TYPE': 'wayland',
                    'HYPRLAND_INSTANCE_SIGNATURE': 'fixture', 'WAYLAND_DISPLAY': 'wayland-fixture'}
        environment = patch.dict(os.environ, self.env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        battery = patch.object(backend, 'battery_present', return_value=False)
        battery.start()
        self.addCleanup(battery.stop)

    def change(self, kind, values):
        return backend.change(kind + '-settings', json.dumps(values))

    def test_missing_state_is_read_only_with_complete_defaults(self):
        bar = backend.snapshot()['bar']
        self.assertEqual(bar['clock_settings'], {})
        self.assertEqual(bar['tray_settings'], {'pinned': [], 'hidden': []})
        self.assertFalse(self.state.exists())

    def test_calendar_and_format_survive_fresh_python_process(self):
        fields = {'weekStartDay': 'saturday', 'birthYear': 1990, 'lifeExpectancy': 90,
                  'formatAlt': 'yyyy-MM-dd', 'verticalFormat': 'HH\nmm', 'verticalFormatAlt': 'dd\nMMM'}
        self.change('clock', fields)
        self.change('clock', {'format': 'HH:mm'})
        backend.change('background', 'glassy')
        backend.change('clock', 'time-12h')
        script = 'import sys,json;sys.path.insert(0,sys.argv[1]);import appearance_backend as b;print(json.dumps(b.bar_state()))'
        result = subprocess.run([sys.executable, '-c', script, str(ROOT / 'tools')],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads(result.stdout)
        self.assertEqual(saved['clock_settings'], fields)
        self.assertEqual(saved['clock_format'], 'h:mm AP')
        self.assertNotIn('format', saved['clock_settings'])
        self.assertEqual((self.state / 'current/bar.json').stat().st_mode & 0o777, 0o600)

    def test_tray_pin_hide_unhide_and_explicit_clear(self):
        self.change('tray', {'pinned': ['org.example.One'], 'hidden': ['org.example.Two']})
        self.change('clock', {'weekStartDay': 'monday'})
        self.assertEqual(backend.bar_state()['tray_settings'],
                         {'pinned': ['org.example.One'], 'hidden': ['org.example.Two']})
        self.change('tray', {'hidden': []})
        self.assertEqual(backend.bar_state()['tray_settings']['pinned'], ['org.example.One'])
        self.change('tray', {'pinned': [], 'hidden': []})
        self.assertEqual(backend.bar_state()['tray_settings'], {'pinned': [], 'hidden': []})

    def test_field_patches_do_not_erase_concurrent_edits(self):
        edits = [('clock', {'weekStartDay': 'monday'}), ('clock', {'birthYear': 1991}),
                 ('clock', {'lifeExpectancy': 92}), ('tray', {'pinned': ['fixture']})]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda args: self.change(*args), edits))
        self.assertTrue(all(result['ok'] for result in results))
        saved = backend.bar_state()
        self.assertEqual(saved['clock_settings'], {'weekStartDay': 'monday', 'birthYear': 1991, 'lifeExpectancy': 92})
        self.assertEqual(saved['tray_settings']['pinned'], ['fixture'])

    def test_legacy_state_unknown_fields_and_exact_rollback(self):
        path = self.state / 'current/bar.json'
        path.parent.mkdir(parents=True)
        before = b'{"schema_version":1,"clock_format":"HH:mm","future":{"keep":true}}\n'
        path.write_bytes(before)
        path.chmod(0o640)
        first = self.change('clock', {'birthYear': 1990})
        second = self.change('tray', {'pinned': ['fixture']})
        self.assertTrue(backend.bar_state()['future']['keep'])
        backend.rollback(second['transaction'])
        backend.rollback(first['transaction'])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_first_creation_rollback_and_clear_birth_year(self):
        first = self.change('clock', {'birthYear': 1990, 'lifeExpectancy': 85})
        second = self.change('clock', {'birthYear': 0})
        self.assertEqual(backend.bar_state()['clock_settings'], {'birthYear': 0, 'lifeExpectancy': 85})
        backend.rollback(second['transaction'])
        backend.rollback(first['transaction'])
        self.assertFalse((self.state / 'current/bar.json').exists())

    def test_invalid_widget_values_are_rejected_before_mutation(self):
        cases = [('clock', {'command': 'anything'}), ('clock', {'birthYear': True}),
                 ('clock', {'weekStartDay': 'not-a-day'}), ('clock', {'lifeExpectancy': 151}),
                 ('clock', {'format': 'not-a-preset'}), ('clock', {'verticalFormat': '\0'}),
                 ('tray', {'pinned': 'fixture'}), ('tray', {'hidden': ['same', 'same']}),
                 ('tray', {'pinned': ['bad\nidentifier']}), ('tray', {'id': 'other'})]
        for kind, values in cases:
            with self.subTest(kind=kind, values=values), self.assertRaises(ValueError):
                self.change(kind, values)
        self.assertFalse(self.state.exists())

    def test_invalid_existing_widget_state_is_not_overwritten(self):
        path = self.state / 'current/bar.json'
        path.parent.mkdir(parents=True)
        for field, value in [('clock_settings', {'birthYear': True}),
                             ('tray_settings', {'hidden': []}),
                             ('clock_settings', {'format': 'HH:mm'})]:
            raw = json.dumps({'schema_version': 1, field: value}).encode()
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                self.change('clock', {'weekStartDay': 'monday'})
            self.assertEqual(path.read_bytes(), raw)
        self.assertFalse((self.state / 'appearance-transactions').exists())

    def test_failed_widget_receipt_restores_exact_previous_bytes_and_mode(self):
        path = self.state / 'current/bar.json'
        path.parent.mkdir(parents=True)
        before = b'{"schema_version":1,"clock_format":"HH:mm"}\n'
        path.write_bytes(before)
        path.chmod(0o640)
        original = backend.atomic

        def fail_receipt(target, raw, mode=0o600):
            if target.name == 'transaction.json' and json.loads(raw).get('status') == 'applied':
                raise OSError('fixture receipt failure')
            original(target, raw, mode)

        for kind, values in [('clock', {'birthYear': 1990}), ('tray', {'pinned': ['fixture']})]:
            with self.subTest(kind=kind), patch.object(backend, 'atomic', side_effect=fail_receipt):
                with self.assertRaises(OSError):
                    self.change(kind, values)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_merged_state_size_is_bounded_without_corrupting_previous_state(self):
        self.change('tray', {'pinned': [str(i) + 'p' * 505 for i in range(64)]})
        path = self.state / 'current/bar.json'
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'exceeds limit'):
            self.change('tray', {'hidden': [str(i) + 'h' * 505 for i in range(64)]})
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(backend.bar_state()['tray_settings']['hidden'], [])

    def test_widget_changes_still_require_the_existing_session_gate(self):
        with patch.dict(os.environ, XDG_CURRENT_DESKTOP='GNOME'):
            with self.assertRaisesRegex(ValueError, 'Hyprland Wayland'):
                self.change('tray', {'pinned': []})
        self.assertFalse(self.state.exists())

    def test_menu_helper_routes_only_validated_widget_requests(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(menu_model.main(['appearance-set', 'clock-settings', '{"weekStartDay":"monday"}']), 0)
        self.assertTrue(json.loads(output.getvalue())['ok'])
        self.assertEqual(backend.bar_state()['clock_settings']['weekStartDay'], 'monday')

    def test_shared_wiring_and_binding_preserving_early_routes(self):
        files, _ = preview.verified_sources(ROOT)
        panel = files['TrialPanel.qml'].decode()
        self.assertIn('appearance.bar.clock_settings', panel)
        self.assertIn('appearanceSettings: bars.appearance', panel)
        self.assertIn('popoutState: barBus', panel)
        self.assertIn('barOverride: clockBar', panel)
        self.assertIn('bars.appearance.setClock(values)', panel)
        self.assertIn('root.appearanceSettings.setTray(values)', files['PortTrayHost.qml'].decode())
        for name in ('CalendarPanel.qml', 'ClockControlView.qml'):
            text = files[name].decode()
            self.assertLess(text.index('root.bar.shell.updateClockSettings('), text.index('root.settings = entry'))

    @unittest.skipUnless(NODE, 'Node required for source JS adapter regressions')
    def test_actual_js_functions_share_pending_state_and_preserve_bindings(self):
        source = (ROOT / 'config/shell/preview/AppearanceState.qml').read_text()
        functions = '\n'.join(qml_function(source, name) for name in
                              ('sameLayout', 'reportLayoutConflict', 'projectBar', 'apply', 'request', 'pump', 'setClock', 'setTray'))
        calendar = (ROOT / 'config/shell/preview/CalendarPanel.qml').read_text()
        script = '''
const assert = require('assert');
let confirmedBar={clock_format:'dddd HH:mm',clock_settings:{},tray_settings:{pinned:[],hidden:[]}};
let queue=[],inFlight=[],finishing=false,loaded=false,errorText='',layoutErrorText='',dock={},helper='/fixture/menu_model.py';
let calls=[],changed=()=>{},backend={running:false,exec:args=>{calls.push(args);backend.running=true;}};
''' + functions + '''
setClock({birthYear:1990});setTray({pinned:['ignored']});assert.equal(calls.length,0);
loaded=true;
finishing=true;
setClock({weekStartDay:'monday'});
assert.equal(calls.length,0); // Requests from change signals wait for the response handler.
finishing=false;pump();
setClock({birthYear:1990,lifeExpectancy:90});
setTray({pinned:['one'],hidden:[]});
// All consumers see the same optimistic projection, even while a write is busy.
const firstOutput=()=>projectBar(),secondOutput=()=>projectBar();
assert.deepEqual(firstOutput(),secondOutput());
assert.equal(secondOutput().clock_settings.birthYear,1990);
// A response to the first edit must not erase the remaining field patches.
apply({bar:{clock_format:'dddd HH:mm',clock_settings:{weekStartDay:'monday'},tray_settings:{pinned:[],hidden:[]}},dock:{}});
inFlight=[];
assert.equal(projectBar().clock_settings.birthYear,1990);
assert.deepEqual(projectBar().tray_settings.pinned,['one']);
backend.running=false;pump();assert.equal(calls.length,2);
// A failed in-flight calendar write must roll back only its unconfirmed fields.
inFlight=[];
assert.equal(projectBar().clock_settings.birthYear,undefined);
assert.deepEqual(projectBar().tray_settings.pinned,['one']);
let hostAssignments=0;
let root={settings:{format:'dddd HH:mm'},moduleName:'omarchy.clock',
  hostWidget:{set settings(value){hostAssignments++;}},bar:{shell:{updateClockSettings:values=>setClock(values)}}};
''' + qml_function(calendar, 'persistSettings') + '''
persistSettings({lifeExpectancy:95});
assert.equal(hostAssignments,0);
assert.deepEqual(root.settings,{format:'dddd HH:mm'});
assert.equal(projectBar().clock_settings.lifeExpectancy,95);
'''
        result = subprocess.run([NODE, '-e', script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
