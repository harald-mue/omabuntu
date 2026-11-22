"""Original gesture/feedback fidelity and detached conditional-write contracts."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_bar_layout as preference_fixtures

from test_widget_preferences import qml_function

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bar_drag
import bar_frame
import bar_frame_fixtures as fixtures
import bar_layout
import appearance_backend as backend
import menu_model
from audio_frontend import between

NODE = shutil.which('node')


class BarGestureTests(unittest.TestCase):
    def setUp(self):
        self.original = (ROOT / 'vendor/omarchy/shell/plugins/bar/Bar.qml').read_text()
        self.frame = bar_frame.derive_frame(self.original.encode()).decode()

    def test_pointer_handler_bodies_are_original_not_replacement_gestures(self):
        original = between(self.original, '  component ModuleSlot: Item {\n',
                           '  component CustomCommandModule: WidgetButton {\n')
        for signal, method in [('onPressed', 'pointerPressed'), ('onPositionChanged', 'pointerMoved'),
                               ('onReleased', 'pointerReleased'), ('onClicked', 'pointerClicked')]:
            with self.subTest(signal=signal):
                renamed = original.replace(signal + ': function(mouse)', 'function ' + method + '(mouse)')
                self.assertEqual(qml_function(renamed, method), qml_function(self.frame, method))
        renamed = original.replace('onCanceled: {', 'function pointerCanceled() {')
        self.assertEqual(qml_function(renamed, 'pointerCanceled'), qml_function(self.frame, 'pointerCanceled'))

    def test_ghost_poof_and_room_surfaces_are_original_with_only_reviewed_seams(self):
        ghost = between(self.original, '  component DragGhostPanel: PanelWindow {\n',
                        '  component BarMoveGhostPanel: PanelWindow {\n')
        expected = ghost.replace('"omarchy-bar-drag-ghost"', '"omabuntu-bar-drag-ghost"').replace('Util.clamp(', 'root.clamp(')
        self.assertIn(expected, self.frame)
        outlines = between(self.original, '  component RoomOutline: BorderSurface {\n',
                           '  component CenterGestureArea: MouseArea {\n')
        self.assertIn(outlines, self.frame)
        self.assertIn('mask: Region {}', ghost)
        self.assertIn('WlrKeyboardFocus.None', ghost)
        self.assertIn('readonly property real barDragRemoveDistance: Style.spaceReal(48)', self.frame)
        for duration in (120, 140, 180, 560, 620):
            self.assertIn('Style.duration(%s)' % duration, self.frame)
        self.assertNotIn('CenterGestureArea {', self.frame)
        self.assertNotIn('BarMoveGhostPanel', self.frame)
        self.assertNotIn('traySectionLoader', self.frame)

    def test_gestures_require_loaded_editor_and_local_slot_and_capture_source_state(self):
        self.assertIn('enabled: canReorder && slot.visible', self.frame)
        self.assertIn('root.layoutEditor.loaded === true', self.frame)
        self.assertIn('moduleSlots.indexOf(sourceSlot) === -1', self.frame)
        self.assertIn('barDragExpected = JSON.parse(JSON.stringify(layoutConfig))', self.frame)
        self.assertIn('keys: barDragKeys, expected: barDragExpected', self.frame)
        self.assertIn('id: entryId(sourceSlot.entry), expected: barDragExpected', self.frame)
        self.assertIn('JSON.stringify(layoutWidgets.sections) !== barDragKeys', self.frame)
        self.assertNotIn('mutateShellConfig', self.frame)
        self.assertNotIn('Util.execDetached', self.frame)

    def test_full_surface_reserves_only_strip_and_idle_input_is_masked(self):
        panel = (ROOT / 'config/shell/preview/TrialPanel.qml').read_text()
        self.assertIn('implicitHeight: screen ? screen.height : 26', panel)
        self.assertIn('exclusiveZone: 26', panel)
        self.assertIn('ExclusionMode.Ignore : ExclusionMode.Normal', panel)
        self.assertIn('mask: fullscreenState.maskFor(frame.barDragSource !== null, stripInputRegion, noInputRegion)', panel)
        self.assertIn('Region { id: noInputRegion }', panel)
        self.assertIn('Region { id: stripInputRegion; item: barStrip }', panel)
        self.assertIn('bars.barHidden ? -barPanel.implicitHeight : 0', panel)
        self.assertIn('barWindow: barPanel', panel)
        self.assertIn('barApi: clockBar', panel)
        self.assertIn('function onBarHiddenChanged() { frame.clearBarDrag() }', panel)

    def test_layer_fixture_replaces_no_pointer_or_visual_logic(self):
        staged = fixtures.ghost_surface(self.frame.encode()).decode()
        self.assertNotIn('component DragGhostPanel: PanelWindow', staged)
        self.assertIn('component DragGhostPanel: Item', staged)
        for name in ('pointerPressed', 'pointerMoved', 'pointerReleased', 'pointerCanceled',
                     'writeLayout', 'playPoof', 'moduleRemoveDistance'):
            self.assertEqual(qml_function(staged, name), qml_function(self.frame, name))
        with self.assertRaises(ValueError):
            fixtures.ghost_surface(self.frame.replace('component DragGhostPanel:', 'component Missing:').encode())
        with self.assertRaises(ValueError):
            bar_drag.derive_slot(self.original.replace('      onReleased: function(mouse) {', 'changed'))

    @unittest.skipUnless(NODE, 'Node required for actual gesture persistence functions')
    def js(self, names, script):
        functions = '\n'.join(qml_function(self.frame, name) for name in names)
        prefix = "const assert=require('assert');const BarModel=require(" + repr(str(
            ROOT / 'vendor/omarchy/shell/plugins/bar/BarModel.js')) + ');\n'
        prefix += 'const A=' + json.dumps(bar_layout.defaults()) + ';\n'
        result = subprocess.run([NODE, '-e', prefix + functions + '\n' + script],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_distinct_window_interfaces_match_only_the_same_output(self):
        self.js(['sameScreen', 'sameWindow'], '''
assert(sameWindow({screen:{name:'fixture-a'}},{screen:{name:'fixture-a'}}));
assert(!sameWindow({screen:{name:'fixture-a'}},{screen:{name:'fixture-b'}}));
assert(!sameWindow(null,null));
''')

    def test_conditional_write_is_detached_and_cleans_memo_on_rejection_or_exception(self):
        self.js(['writeLayout'], '''
let widgetMemo={},captured=[],layoutEditor=null;
const edit=config=>BarModel.removeEntry(config,{region:'center',index:0,id:'omarchy.clock'});
assert.equal(writeLayout({},edit,A),false);
layoutEditor={editLayout:(expected,next)=>{captured.push([expected,next]);return false;}};
const before=JSON.stringify(A);assert.equal(writeLayout({center:[]},edit,A),false);
assert.equal(JSON.stringify(A),before);assert.deepEqual(captured[0][1].center,[]);
assert.equal(widgetMemo.expected,null);
layoutEditor={editLayout:()=>{throw new Error('fixture failure');}};
assert.throws(()=>writeLayout({},edit,A),/fixture failure/);assert.equal(widgetMemo.expected,null);
''')

    def test_landing_uses_captured_layout_and_refuses_changed_key_order(self):
        self.js(['landBarDrag', 'writeLayout'], '''
let clears=0,captured=[],widgetMemo={};function clearBarDrag(){clears++;}
let layoutEditor={editLayout:(expected,next)=>{captured.push([expected,next]);return true;}};
const sections={left:['menu','workspaces'],centerBegin:[],center:['clock'],centerEnd:['elsewhen','weather'],right:['tray','keyboard','bt','net','audio','monitor','power'],tray:[]};
let layoutWidgets={sections};
const move={key:'clock',keys:JSON.stringify(sections),expected:A,
 from:{region:'center',index:0,id:'omarchy.clock'},to:{region:'left',index:-1}};
landBarDrag(move);assert.equal(clears,1);assert.equal(captured.length,1);
assert.deepEqual(captured[0][0],A);assert.equal(captured[0][1].left.at(-1),'omarchy.clock');
assert.deepEqual(captured[0][1].center,[]);assert.equal(A.center[0],'omarchy.clock');
layoutWidgets={sections:{...sections,left:['different']}};
landBarDrag(move);assert.equal(clears,2);assert.equal(captured.length,1);
''')

    def test_removal_uses_captured_expected_state_and_ignores_missing_key(self):
        self.js(['commitBarRemoval', 'writeLayout'], '''
let widgetMemo={},captured=[],layoutEditor={editLayout:(expected,next)=>{captured.push([expected,next]);return false;}};
let layoutWidgets={sections:{left:[],centerBegin:[],center:['clock'],centerEnd:[],right:[],tray:[]}};
let barRemoval={key:'clock',region:'center',id:'omarchy.clock',expected:A};
commitBarRemoval();assert.equal(barRemoval,null);assert.equal(captured.length,1);
assert.deepEqual(captured[0][0],A);assert.deepEqual(captured[0][1].center,[]);
barRemoval={key:'missing',region:'center',id:'omarchy.clock',expected:A};
commitBarRemoval();assert.equal(captured.length,1);assert.equal(widgetMemo.expected,null);
''')


class LayoutRecoveryTests(unittest.TestCase):
    setUp = preference_fixtures.BarLayoutTests.setUp

    def test_menu_restores_even_empty_layout_and_preserves_other_preferences(self):
        empty = {region: [] for region in bar_layout.REGIONS}
        backend.change('bar-layout', json.dumps(empty))
        backend.change('clock-settings', '{"birthYear":1990}')
        backend.change('tray-settings', '{"pinned":["fixture"]}')
        result = menu_model.run_item('appearance.top-bar.restore-layout')
        self.assertTrue(result['ok'], result)
        saved = backend.bar_state()
        self.assertEqual(saved['bar_layout'], bar_layout.defaults())
        self.assertEqual(saved['clock_settings']['birthYear'], 1990)
        self.assertEqual(saved['tray_settings']['pinned'], ['fixture'])
        backend.rollback(result['transaction'])
        self.assertEqual(backend.bar_state()['bar_layout'], empty)

    def test_recovery_action_retains_session_gate_and_closed_values(self):
        with patch.dict('os.environ', {'XDG_CURRENT_DESKTOP': 'GNOME'}):
            result = menu_model.run_item('appearance.top-bar.restore-layout')
        self.assertFalse(result['ok'])
        self.assertFalse(self.state.exists())
        for value in ('anything', 'restore; command', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                backend.change('bar-layout-default', value)


if __name__ == '__main__':
    unittest.main()
