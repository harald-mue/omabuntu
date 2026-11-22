"""Conditional original-model layout edits, without host QML or desktop writes."""
from concurrent.futures import ThreadPoolExecutor
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

import test_bar_layout as fixtures
from test_widget_preferences import qml_function

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import appearance_backend as backend
import bar_layout
import menu_model

NODE = shutil.which('node')


class ConditionalLayoutTests(unittest.TestCase):
    setUp = fixtures.BarLayoutTests.setUp
    moved = fixtures.BarLayoutTests.moved

    def edit(self, expected, layout):
        return backend.change('bar-layout-edit', json.dumps({'expected': expected, 'layout': layout}))

    def alternate(self):
        value = bar_layout.defaults()
        value['center'].clear()
        value['left'].append('omarchy.clock')
        return value

    def test_stale_and_noop_requests_do_not_allocate_state(self):
        result = self.edit(self.moved(), self.alternate())
        self.assertFalse(result['ok'])
        self.assertEqual(result['status'], 'conflict')
        self.assertEqual(result['appearance']['bar']['bar_layout'], bar_layout.defaults())
        self.assertFalse(self.state.exists())
        result = self.edit(bar_layout.defaults(), bar_layout.defaults())
        self.assertEqual(result['status'], 'unchanged')
        self.assertFalse(self.state.exists())

    def test_edit_payload_is_closed_and_validates_both_layouts(self):
        value = {'expected': bar_layout.defaults(), 'layout': self.moved()}
        bad = [None, [], {}, {**value, 'exec': 'anything'}, {'layout': self.moved()},
               {**value, 'expected': {}}, {**value, 'layout': {'left': []}}]
        unsafe = self.moved()
        unsafe['centerBegin'] = [{'id': 'omarchy.clock', 'source': '/tmp/custom.qml'}]
        bad.append({**value, 'layout': unsafe})
        for payload in bad:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                backend.change('bar-layout-edit', json.dumps(payload))
        self.assertFalse(self.state.exists())

    def test_unrelated_preference_changes_do_not_cause_false_conflicts(self):
        backend.change('clock-settings', '{"birthYear":1990}')
        backend.change('tray-settings', '{"pinned":["fixture"]}')
        result = self.edit(bar_layout.defaults(), self.moved())
        self.assertEqual(result['status'], 'applied')
        saved = backend.bar_state()
        self.assertEqual(saved['bar_layout'], self.moved())
        self.assertEqual(saved['clock_settings']['birthYear'], 1990)
        self.assertEqual(saved['tray_settings']['pinned'], ['fixture'])

    def test_expected_object_key_order_is_not_a_conflict(self):
        expected = dict(reversed(list(bar_layout.defaults().items())))
        self.assertEqual(self.edit(expected, self.moved())['status'], 'applied')

    def test_locked_recheck_catches_change_after_preflight(self):
        original = backend.transaction_directory
        pending = True
        def interleave():
            nonlocal pending
            if pending:
                pending = False
                backend.change('bar-layout', json.dumps(self.alternate()))
            return original()
        with patch.object(backend, 'transaction_directory', side_effect=interleave):
            result = self.edit(bar_layout.defaults(), self.moved())
        self.assertEqual(result['status'], 'conflict')
        self.assertEqual(backend.bar_state()['bar_layout'], self.alternate())
        receipts = list((self.state / 'appearance-transactions').glob('*/transaction.json'))
        self.assertEqual(len(receipts), 1)  # Only the independent writer committed.

    def test_two_writers_with_one_expected_layout_cannot_both_commit(self):
        original = backend.transaction_directory
        barrier = threading.Barrier(2)
        def together():
            value = original()
            barrier.wait(timeout=5)
            return value
        with patch.object(backend, 'transaction_directory', side_effect=together):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda layout: self.edit(bar_layout.defaults(), layout),
                                        [self.moved(), self.alternate()]))
        self.assertEqual(sorted(r['status'] for r in results), ['applied', 'conflict'])
        applied = next(r for r in results if r['ok'])
        self.assertEqual(backend.bar_state()['bar_layout'], applied['appearance']['bar']['bar_layout'])

    def test_guarded_edit_retains_exact_rollback_and_external_drift_refusal(self):
        path = self.state / 'current/bar.json'
        path.parent.mkdir(parents=True)
        before = b'{"schema_version":1,"future":{"keep":true}}\n'
        path.write_bytes(before)
        path.chmod(0o640)
        receipt = self.edit(bar_layout.defaults(), self.moved())
        self.assertTrue(backend.bar_state()['future']['keep'])
        backend.rollback(receipt['transaction'])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        receipt = self.edit(bar_layout.defaults(), self.moved())
        changed = path.read_bytes() + b' '
        path.write_bytes(changed)
        with self.assertRaises(ValueError):
            backend.rollback(receipt['transaction'])
        self.assertEqual(path.read_bytes(), changed)

    def test_failed_receipt_restores_absence(self):
        original = backend.atomic
        def fail_receipt(path, raw, mode=0o600):
            if path.name == 'transaction.json' and json.loads(raw).get('status') == 'applied':
                raise OSError('fixture receipt failure')
            return original(path, raw, mode)
        with patch.object(backend, 'atomic', side_effect=fail_receipt):
            with self.assertRaises(OSError):
                self.edit(bar_layout.defaults(), self.moved())
        self.assertFalse((self.state / 'current/bar.json').exists())

    def test_conditional_noop_does_not_bypass_the_existing_session_gate(self):
        with patch.dict('os.environ', {'XDG_CURRENT_DESKTOP': 'GNOME'}):
            with self.assertRaisesRegex(ValueError, 'Hyprland Wayland'):
                self.edit(bar_layout.defaults(), bar_layout.defaults())
        self.assertFalse(self.state.exists())

    def test_menu_conflict_is_a_failed_result_even_with_zero_cli_exit(self):
        output = io.StringIO()
        payload = json.dumps({'expected': self.moved(), 'layout': self.alternate()})
        with contextlib.redirect_stdout(output):
            code = menu_model.main(['appearance-set', 'bar-layout-edit', payload])
        self.assertEqual(code, 0)
        result = json.loads(output.getvalue())
        self.assertFalse(result['ok'])
        self.assertEqual(result['status'], 'conflict')
        self.assertIn('appearance', result)
        self.assertFalse(self.state.exists())

    @unittest.skipUnless(NODE, 'Node required for actual QML edit/queue regressions')
    def run_adapter(self, checks):
        source = (ROOT / 'config/shell/preview/AppearanceState.qml').read_text()
        names = ('sameLayout', 'reportLayoutConflict', 'projectBar', 'apply', 'request',
                 'pump', 'editLayout', 'setClock', 'finishResponse')
        functions = '\n'.join(qml_function(source, name) for name in names)
        script = "const assert=require('assert');\nconst A=" + json.dumps(bar_layout.defaults()) + ';\n'
        script += 'const B=' + json.dumps(self.moved()) + ';\nconst C=' + json.dumps(self.alternate()) + ';\n'
        script += '''
const copy=value=>JSON.parse(JSON.stringify(value));
let confirmedBar={bar_layout:copy(A),clock_settings:{},tray_settings:{pinned:[],hidden:[]}};
let queue=[],inFlight=[],finishing=false,loaded=true,errorText='',layoutErrorText='',dock={},helper='/fixture/menu_model.py';
let calls=[],scheduled=[],warnings=[];
const Qt={callLater:fn=>scheduled.push(fn)};
const console={warn:(...args)=>warnings.push(args)};
const changed=()=>{};
const root={pump:()=>pump()};
const backend={running:false,exec:args=>{calls.push(args);backend.running=true;}};
function state(layout){return {bar:{bar_layout:copy(layout),clock_settings:{},tray_settings:{pinned:[],hidden:[]}},dock:{}};}
function respond(data,code=0){backend.running=false;finishResponse(code,JSON.stringify(data));}
''' + functions + '\n' + checks
        result = subprocess.run([NODE, '-e', script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_pending_chain_tracks_both_outputs_and_acknowledges_in_order(self):
        self.run_adapter('''
assert(editLayout(A,B));assert(editLayout(B,C));setClock({birthYear:1990});
const first=()=>projectBar().bar_layout,second=()=>projectBar().bar_layout;
assert.deepEqual(first(),C);assert.deepEqual(first(),second());assert.equal(calls.length,1);
respond({ok:true,appearance:state(B)});assert.deepEqual(first(),C);
scheduled.shift()();assert.equal(calls.length,2);
assert.deepEqual(JSON.parse(calls[1][4]),{expected:B,layout:C});
respond({ok:true,appearance:state(C)});scheduled.shift()();
assert.equal(calls[2][3],'clock-settings');assert.deepEqual(second(),C);
''')

    def test_conflict_refreshes_shared_state_drops_dependents_and_keeps_notice(self):
        self.run_adapter('''
assert(editLayout(A,B));assert(editLayout(B,C));setClock({birthYear:1990});
respond({ok:false,status:'conflict',message:'Bar layout changed; fixture conflict.',appearance:state(C)});
assert.deepEqual(projectBar().bar_layout,C);assert.equal(queue.length,1);
assert.equal(queue[0][1],'clock-settings');assert(layoutErrorText.includes('conflict'));
scheduled.shift()();assert.equal(calls[1][3],'clock-settings');
respond({ok:true,appearance:state(C)});assert(errorText.includes('conflict'));
assert(editLayout(C,A));assert.equal(layoutErrorText,'');
''')

    def test_unknown_result_gets_one_read_and_never_replays_dependent_edit(self):
        self.run_adapter('''
assert(editLayout(A,B));assert(editLayout(B,C));setClock({birthYear:1990});
backend.running=false;finishResponse(0,'broken JSON');
assert.deepEqual(queue.map(a=>a[0]),['appearance-state','appearance-set']);
scheduled.shift()();assert.equal(calls[1][2],'appearance-state');
respond({ok:true,appearance:state(B)});assert.deepEqual(projectBar().bar_layout,B);
assert(layoutErrorText);scheduled.shift()();assert.equal(calls[2][3],'clock-settings');
assert.equal(calls.filter(a=>a[3]==='bar-layout-edit').length,1);
''')

    def test_failed_refresh_does_not_loop_or_drop_independent_edits(self):
        self.run_adapter('''
assert(editLayout(A,B));setClock({birthYear:1990});
backend.running=false;finishResponse(1,'');scheduled.shift()();
respond({ok:false,message:'Read failed.'},1);scheduled.shift()();
assert.equal(calls.length,3);assert.equal(calls[2][3],'clock-settings');
assert.equal(calls.filter(a=>a[2]==='appearance-state').length,1);
''')

    def test_stale_queued_edit_is_discarded_before_dispatch(self):
        self.run_adapter('''
backend.running=true;assert(editLayout(A,B));apply(state(C));
assert.deepEqual(projectBar().bar_layout,C);backend.running=false;pump();
assert.equal(queue.length,0);assert.equal(calls.length,0);assert(layoutErrorText);
''')

    def test_load_noop_shape_capacity_helper_and_stale_capture_guards(self):
        self.run_adapter('''
loaded=false;assert(!editLayout(A,B));loaded=true;
assert(!editLayout(A,A));assert(!editLayout(A,{left:[]}));
helper='/unreviewed/helper.py';assert(!editLayout(A,B));helper='/fixture/menu_model.py';
backend.running=true;queue=Array.from({length:32},()=>['appearance-state']);
assert(!editLayout(A,B));assert.equal(queue.length,32);queue=[];backend.running=false;
assert(editLayout(A,B));assert(!editLayout(A,C));assert.equal(calls.length,1);
const captured=JSON.parse(calls[0][4]);A.left=[];B.left=[];
assert(captured.expected.left.length>0 && captured.layout.left.length>0);
''')

    @unittest.skipUnless(NODE, 'Node required for original model invocation regression')
    def test_frame_uses_original_move_remove_without_mutating_rejected_source(self):
        source = (ROOT / 'config/shell/preview/BarFrame.qml').read_text()
        names = ('componentForId', 'applyLayoutEdit', 'layoutRegion', 'moveWidget', 'removeWidget')
        functions = '\n'.join(qml_function(source, name) for name in names)
        script = "const assert=require('assert');const BarModel=require(" + repr(str(
            ROOT / 'vendor/omarchy/shell/plugins/bar/BarModel.js')) + ');\n'
        script += 'let layoutConfig=' + json.dumps(bar_layout.defaults()) + ';\n'
        script += 'const widgetComponents=' + json.dumps({name: True for name in bar_layout.WIDGETS}) + ';\n'
        script += '''let layoutEditor=null,calls=[],accept=false;
''' + functions + '''
const original=JSON.stringify(layoutConfig);
const move={from:{region:'center',index:0,id:'omarchy.clock'},to:{region:'left',index:-1}};
assert(!moveWidget(move));
layoutEditor={editLayout:(expected,next)=>{calls.push([expected,next]);if(accept)layoutConfig=next;return accept;}};
assert(!moveWidget({from:{...move.from,id:'other'},to:move.to}));
assert(!moveWidget({...move,to:{region:'tray',index:-1}}));assert.equal(calls.length,0);
assert(!moveWidget({...move,to:{region:'center',index:0}}));
assert(!moveWidget(move));assert.equal(JSON.stringify(layoutConfig),original);
accept=true;assert(moveWidget(move));assert.deepEqual(layoutConfig.center,[]);
assert.equal(layoutConfig.left.at(-1),'omarchy.clock');
assert(!removeWidget({region:'left',index:0,id:'omarchy.clock'}));
assert(removeWidget({region:'left',index:2,id:'omarchy.clock'}));
assert.equal(layoutConfig.left.includes('omarchy.clock'),false);
'''
        result = subprocess.run([NODE, '-e', script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
