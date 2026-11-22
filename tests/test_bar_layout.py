"""Closed original-layout persistence and ownership tests, never a host desktop."""
from concurrent.futures import ThreadPoolExecutor
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import appearance_backend as backend
import bar_layout
import check_clock_preview as preview
import menu_model
from test_widget_preferences import qml_function

NODE = shutil.which('node')


class BarLayoutTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.state = self.home / 'state'
        environment = patch.dict(os.environ, {
            'HOME': str(self.home), 'XDG_CONFIG_HOME': str(self.home / 'config'),
            'OMABUNTU_STATE_HOME': str(self.state), 'XDG_CURRENT_DESKTOP': 'Hyprland',
            'XDG_SESSION_TYPE': 'wayland', 'WAYLAND_DISPLAY': 'wayland-fixture',
            'HYPRLAND_INSTANCE_SIGNATURE': 'fixture'}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def moved(self):
        value = bar_layout.defaults()
        value['right'].remove('omarchy.audio')
        value['centerEnd'].insert(0, 'omarchy.audio')
        return value

    def change(self, value):
        return backend.change('bar-layout', json.dumps(value))

    def test_default_reads_create_no_state_and_return_detached_lists(self):
        first = backend.bar_state()['bar_layout']
        first['left'].clear()
        self.assertEqual(backend.bar_state()['bar_layout'], bar_layout.DEFAULT)
        self.assertFalse(self.state.exists())

    def test_only_known_unique_string_widgets_and_five_sections_are_admitted(self):
        values = [None, [], True, {}, {**bar_layout.defaults(), 'tray': []}]
        for entry in ('unknown', '/tmp/custom.qml', 'constructor', {'id': 'omarchy.audio'},
                      {'exec': 'anything'}, None, True, 5, ['omarchy.audio']):
            value = bar_layout.defaults()
            value['centerBegin'] = [entry]
            values.append(value)
        value = bar_layout.defaults()
        value['left'] += ['omarchy.audio']
        values.append(value)
        value = bar_layout.defaults()
        value['centerBegin'] = 'omarchy.audio'
        values.append(value)
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.change(value)
        self.assertFalse(self.state.exists())

    def test_layout_round_trip_fresh_process_and_independent_widget_edits(self):
        value = self.moved()
        self.change(value)
        backend.change('clock-settings', '{"weekStartDay":"monday"}')
        backend.change('tray-settings', '{"pinned":["fixture"]}')
        script = 'import sys,json;sys.path.insert(0,sys.argv[1]);import appearance_backend as b;print(json.dumps(b.bar_state()))'
        result = subprocess.run([sys.executable, '-B', '-c', script, str(ROOT / 'tools')],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads(result.stdout)
        self.assertEqual(saved['bar_layout'], value)
        self.assertEqual(saved['clock_settings']['weekStartDay'], 'monday')
        self.assertEqual(saved['tray_settings']['pinned'], ['fixture'])
        self.assertEqual((self.state / 'current/bar.json').stat().st_mode & 0o777, 0o600)

    def test_empty_sections_are_valid_and_first_creation_rolls_back_to_absence(self):
        empty = {region: [] for region in bar_layout.REGIONS}
        receipt = self.change(empty)
        self.assertEqual(backend.bar_state()['bar_layout'], empty)
        backend.rollback(receipt['transaction'])
        self.assertFalse((self.state / 'current/bar.json').exists())

    def test_unknown_fields_and_exact_previous_bytes_and_mode_survive(self):
        path = self.state / 'current/bar.json'
        path.parent.mkdir(parents=True)
        before = b'{"schema_version":1,"future":{"keep":true},"clock_format":"HH:mm"}\n'
        path.write_bytes(before)
        path.chmod(0o640)
        receipt = self.change(self.moved())
        self.assertTrue(backend.bar_state()['future']['keep'])
        backend.rollback(receipt['transaction'])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_external_drift_prevents_rollback_overwrite(self):
        receipt = self.change(self.moved())
        path = self.state / 'current/bar.json'
        changed = path.read_bytes() + b' '
        path.write_bytes(changed)
        with self.assertRaises(ValueError):
            backend.rollback(receipt['transaction'])
        self.assertEqual(path.read_bytes(), changed)

    def test_malformed_existing_layout_is_not_overwritten(self):
        path = self.state / 'current/bar.json'
        path.parent.mkdir(parents=True)
        raw = b'{"schema_version":1,"bar_layout":{"left":["unknown"]}}'
        path.write_bytes(raw)
        with self.assertRaises(ValueError):
            self.change(self.moved())
        self.assertEqual(path.read_bytes(), raw)
        self.assertFalse((self.state / 'appearance-transactions').exists())

    def test_failed_final_receipt_restores_exact_prestate(self):
        self.change(bar_layout.defaults())
        path = self.state / 'current/bar.json'
        before = path.read_bytes()
        path.chmod(0o640)
        original = backend.atomic
        def fail_receipt(target, raw, mode=0o600):
            if target.name == 'transaction.json' and json.loads(raw).get('status') == 'applied':
                raise OSError('fixture receipt failure')
            return original(target, raw, mode)
        with patch.object(backend, 'atomic', side_effect=fail_receipt):
            with self.assertRaises(OSError):
                self.change(self.moved())
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_layout_writes_keep_the_existing_session_gate(self):
        with patch.dict(os.environ, XDG_CURRENT_DESKTOP='GNOME'):
            with self.assertRaisesRegex(ValueError, 'Hyprland Wayland'):
                self.change(self.moved())
        self.assertFalse(self.state.exists())

    def test_concurrent_layout_clock_tray_edits_preserve_independent_fields(self):
        edits = [('bar-layout', json.dumps(self.moved())), ('clock-settings', '{"birthYear":1990}'),
                 ('tray-settings', '{"hidden":["fixture"]}')]
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda args: backend.change(*args), edits))
        self.assertTrue(all(result['ok'] for result in results))
        saved = backend.bar_state()
        self.assertEqual(saved['bar_layout'], self.moved())
        self.assertEqual(saved['clock_settings']['birthYear'], 1990)
        self.assertEqual(saved['tray_settings']['hidden'], ['fixture'])

    def test_menu_helper_uses_validated_layout_route(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = menu_model.main(['appearance-set', 'bar-layout', json.dumps(self.moved())])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output.getvalue())['ok'])
        self.assertEqual(backend.bar_state()['bar_layout'], self.moved())

    def test_bar_model_is_unchanged_reviewed_source_and_pool_is_original(self):
        files, meta = preview.verified_sources(ROOT)
        model = files['Port/BarModel.js']
        self.assertEqual(hashlib.sha256(model).hexdigest(),
                         '9394b2ca8256518bbe04a8b11f4b740e20c2d9c0859372eda475dc33200471b8')
        self.assertEqual(meta['upstream']['Port/BarModel.js']['stage_transform'], 'none')
        original = (ROOT / 'vendor/omarchy/shell/plugins/bar/Bar.qml').read_text()
        pool = original.split('  component WidgetPool: Item {', 1)[1].split(
            '  // One widget on a bar surface, loaded from its entry,', 1)[0]
        frame = files['BarFrame.qml'].decode()
        self.assertIn(pool, frame)
        for forbidden in ('CustomCommandModule {', 'qmlLoader', 'customModuleSource', 'execDetached', 'Process {'):
            self.assertNotIn(forbidden, frame)
        self.assertNotIn('target.settings =', frame)
        self.assertNotIn('target.bar =', frame)

    def test_python_and_live_component_registry_have_the_same_closed_ids(self):
        panel = (ROOT / 'config/shell/preview/TrialPanel.qml').read_text()
        components = panel.split('      widgetComponents: ({', 1)[1].split('      })', 1)[0]
        names = re.findall(r'"([a-z.-]+)":', components)
        self.assertEqual(set(names), bar_layout.WIDGETS)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn('return frame.switchPanelFrom(owner, direction)', panel)
        self.assertIn('barOverride: clockBar', panel)
        self.assertNotIn('trayHost.ownerApi', panel)

    def test_qml_startup_fallback_matches_the_python_default_order(self):
        panel = (ROOT / 'config/shell/preview/TrialPanel.qml').read_text()
        raw = '{left:' + panel.split(': ({left:', 1)[1].split('})\n      widgetComponents:', 1)[0] + '}'
        raw = re.sub(r'([{,])\s*([A-Za-z]+)\s*:', r'\1"\2":', raw)
        self.assertEqual(json.loads(raw), bar_layout.defaults())

    @unittest.skipUnless(NODE, 'Node required for actual QML projection regression')
    def test_shared_pending_layout_does_not_revert_on_older_response(self):
        source = (ROOT / 'config/shell/preview/AppearanceState.qml').read_text()
        functions = '\n'.join(qml_function(source, name) for name in
                              ('sameLayout', 'reportLayoutConflict', 'projectBar', 'apply', 'request', 'pump', 'setLayout', 'setClock'))
        script = '''const assert=require('assert');
let confirmedBar={clock_settings:{},tray_settings:{pinned:[],hidden:[]},bar_layout:{left:['one']}};
let queue=[],inFlight=[],finishing=false,loaded=false,errorText='',layoutErrorText='',dock={},helper='/fixture/menu_model.py';
let calls=[],changed=()=>{},backend={running:false,exec:args=>{calls.push(args);backend.running=true;}};
''' + functions + '''
setLayout({left:['ignored']});assert.equal(calls.length,0);
loaded=true;setLayout({left:['first']});setLayout({left:['latest']});setClock({weekStartDay:'monday'});
const firstOutput=()=>projectBar(),secondOutput=()=>projectBar();
assert.deepEqual(firstOutput(),secondOutput());assert.deepEqual(secondOutput().bar_layout,{left:['latest']});
assert.deepEqual(confirmedBar.bar_layout,{left:['one']});
apply({bar:{clock_settings:{},tray_settings:{pinned:[],hidden:[]},bar_layout:{left:['first']}},dock:{}});inFlight=[];
assert.deepEqual(projectBar().bar_layout,{left:['latest']});
backend.running=false;pump();assert.equal(calls.length,2);
// A failed pending layout is dropped; later independent clock edit survives.
inFlight=[];
assert.deepEqual(projectBar().bar_layout,{left:['first']});
assert.equal(projectBar().clock_settings.weekStartDay,'monday');
'''
        result = subprocess.run([NODE, '-e', script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
