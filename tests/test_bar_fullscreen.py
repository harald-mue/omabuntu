"""Original fullscreen input policy with synthetic state, never a compositor."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import audio_frontend
import bar_frame
import bar_frame_fixtures as fixtures
import check_clock_preview as preview


class BarFullscreenTests(unittest.TestCase):
    def test_observer_is_derived_and_sealed_from_unchanged_original_parent(self):
        source = (ROOT / 'vendor/omarchy/shell/plugins/bar/Bar.qml').read_bytes()
        derived = bar_frame.derive_fullscreen(source)
        self.assertEqual(derived, (ROOT / 'config/shell/preview/BarFullscreenState.qml').read_bytes())
        files, meta = preview.verified_sources(ROOT)
        self.assertEqual(files['BarFullscreenState.qml'], derived)
        self.assertEqual(meta['upstream']['BarFullscreenState.qml']['stage_transform'], 'bar-fullscreen-input-v1')
        self.assertNotIn('BarFullscreenState.qml', meta['authored'])
        original = audio_frontend.between(source.decode(), '    readonly property bool underFullscreen: {\n',
            '    // Idle, only the strip takes input,')
        self.assertIn(original.replace('var monitor = Hyprland.monitorFor(screen)',
            'var monitor = screen ? Hyprland.monitorFor(screen) : null'), derived.decode())

    def test_only_original_fullscreen_event_refresh_is_admitted(self):
        text = (ROOT / 'config/shell/preview/BarFullscreenState.qml').read_text()
        self.assertIn('enabled: root.refreshEvents', text)
        self.assertIn('property bool refreshEvents: false', text)
        self.assertIn('String(event.name) === "fullscreen") Hyprland.refreshToplevels()', text)
        for forbidden in ('Timer {', 'Process {', 'FileView {', 'dispatch(', 'execDetached', 'opacity:', 'PanelWindow {'):
            self.assertNotIn(forbidden, text)
        self.assertNotIn('focusedMonitor', text)
        self.assertNotIn('focusedWorkspace', text)

    def test_real_surface_uses_empty_mask_with_fullscreen_and_hide_dominating_drag(self):
        text = (ROOT / 'config/shell/preview/TrialPanel.qml').read_text()
        self.assertEqual(text.count('refreshEvents: true'), 1)
        for witness in ('screen: barPanel.screen', 'hidden: bars.barHidden', 'dragFrame: frame',
                        'fullscreenState.maskFor(frame.barDragSource !== null, stripInputRegion, noInputRegion)',
                        'Region { id: noInputRegion }', 'exclusiveZone: 26', 'implicitHeight: screen ? screen.height : 26'):
            self.assertIn(witness, text)
        observer = (ROOT / 'config/shell/preview/BarFullscreenState.qml').read_text()
        self.assertIn('return suppressed ? empty : (dragging ? null : strip)', observer)
        self.assertIn('dragFrame.clearBarDrag()', observer)
        for forbidden in ('writeLayout(', 'editLayout(', 'removeWidget(', 'setLayout('):
            self.assertNotIn(forbidden, observer)

    def test_unique_extraction_witnesses_refuse_source_drift(self):
        source = (ROOT / 'vendor/omarchy/shell/plugins/bar/Bar.qml').read_bytes()
        for old in (b'    readonly property bool underFullscreen: {\n',
                    b'var monitor = Hyprland.monitorFor(screen)',
                    b'    // Idle, only the strip takes input,'):
            with self.subTest(old=old), self.assertRaises(ValueError):
                bar_frame.derive_fullscreen(source.replace(old, b'changed'))
        with self.assertRaises(ValueError):
            bar_frame.derive_fullscreen(source+b'\n    readonly property bool underFullscreen: {\n')

    def test_actual_observer_cases_and_fixture_substitution_have_closed_boundaries(self):
        source = (ROOT / 'tools/check_tray_port.py').read_text()
        self.assertIn('"WorkspaceSwitcher.qml", "BarFullscreenState.qml"', source)
        for case in ('fullscreen-local', 'fullscreen-state', 'fullscreen-drag', 'fullscreen-refresh'):
            text = fixtures.fixture(case)
            self.assertIn('actual source-derived fullscreen observers construct', text)
            self.assertNotIn('import Quickshell.Hyprland', text)
            good = 'Configuration Loaded\n'+fixtures.MARKER+'::'+case+'\n'
            self.assertTrue(fixtures.classify(case, 0, good))
            self.assertFalse(fixtures.classify(case, 0, good+'WARN unexpected\n'))

    @unittest.skipUnless(shutil.which('node'), 'Node required for original pure model test')
    def test_original_model_distinguishes_real_fullscreen_and_output_workspace(self):
        path = str(ROOT / 'vendor/omarchy/shell/plugins/bar/BarModel.js')
        program = 'const assert=require("assert"),model=require('+json.dumps(path)+');'+'''
function window(workspace,flag){return {workspace:{id:workspace},lastIpcObject:{fullscreen:flag}};}
for(const flag of [0,1]) assert.strictEqual(model.fullscreenOn([window(10,flag)],10),false);
for(const flag of [2,3]) assert.strictEqual(model.fullscreenOn([window(10,flag)],10),true);
assert.strictEqual(model.fullscreenOn([window(10,2)],20),false);
assert.strictEqual(model.fullscreenOn([window(-5,2)],-5),true);
assert.strictEqual(model.fullscreenOn([null,{},window(10,0)],10),false);
assert.strictEqual(model.fullscreenOn(null,10),false);
console.log('fullscreen-ok');
'''
        result = subprocess.run(['node', '-e', program], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'fullscreen-ok')


if __name__ == '__main__':
    unittest.main()
