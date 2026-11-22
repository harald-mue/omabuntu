"""Original shared hover policy; source contracts, never native input acceptance."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bar_frame
import bar_frame_fixtures
import check_clock_preview


class BarPeekTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / 'vendor/omarchy/shell/plugins/bar/Bar.qml').read_bytes()
        self.state = bar_frame.derive_peek(self.source).decode()
        self.frame = bar_frame.derive_frame(self.source).decode()

    def test_exact_sealed_nonvisual_original_derivation(self):
        files, meta = check_clock_preview.verified_sources(ROOT)
        self.assertEqual(files['BarPeekState.qml'].decode(), self.state)
        self.assertEqual((ROOT / 'config/shell/preview/BarPeekState.qml').read_text(), self.state)
        self.assertEqual(meta['upstream']['BarPeekState.qml']['stage_transform'], 'bar-peek-owner-v1')
        self.assertNotIn('BarPeekState.qml', meta['authored'])
        self.assertIn('QtObject {', self.state)
        for forbidden in ('PanelWindow', 'Process', 'FileView', 'Hyprland', 'exec', 'onCompleted'):
            self.assertNotIn(forbidden, self.state)

    def test_original_counter_and_hysteresis_bodies(self):
        source = self.source.decode()
        functions = source[source.index('  function setBarHovered(hovered) {'):source.index('  Timer {\n    id: centerSectionRevealTimer')]
        self.assertIn(functions, self.state)
        self.assertIn('interval: 120', self.state)
        self.assertIn('onTriggered: if (!root.barHovered) root.centerSectionRevealHeld = false', self.state)
        self.assertEqual(self.state.count('Timer {'), 1)
        self.assertIn('readonly property bool barHovered: barHoverCount > 0', self.state)

    def test_frame_restores_original_edge_and_ancestor_handler(self):
        self.assertIn('readonly property real boxStart: root.vertical ? y + centerBox.y : x + centerBox.x', self.frame)
        self.assertIn('root.peekEdge = BarModel.nextPeekEdge(root.peekEdge, boxStart, root.centerSectionRevealHeld)', self.frame)
        self.assertIn('onCenterSectionRevealHeldChanged() { sections.syncPeekEdge() }', self.frame)
        self.assertIn('peeking: !root.peekSuppressed && hovered && BarModel.peeksAt(point.position, root.peekEdge, root.vertical)', self.frame)
        self.assertIn('Component.onDestruction: root.setPeekHovered(false)', self.frame)
        self.assertIn('if (peekOwner === next) return', self.frame)
        self.assertIn('onPeekStateChanged: setPeekHovered(peekHovered)', self.frame)
        self.assertIn('peekHovered = !!hovered && !peekSuppressed', self.frame)
        self.assertNotIn('window.peekEdge =', self.frame)

    def test_production_shares_owner_and_separate_public_flag(self):
        panel = (ROOT / 'config/shell/preview/TrialPanel.qml').read_text()
        self.assertEqual(panel.count('property BarPeekState peekState: BarPeekState {}'), 1)
        for seam in ('peekState: bars.peekState', 'peekSuppressed: fullscreenState.suppressed',
                     'centerSectionRevealHeld: bars.peekState.centerSectionRevealHeld',
                     'centerHoverRevealSuppressed: bars.peekState.centerHoverRevealSuppressed',
                     'bars.peekState.setCenterHoverRevealSuppressed(value)'):
            self.assertIn(seam, panel)
        # Do not silently conflate consumer suppression with original hover state.
        self.assertNotIn('centerHoverRevealSuppressed', bar_frame.derive_hover(self.source.decode()))
        self.assertIn('peek-owner', bar_frame_fixtures.CASES)
        self.assertIn('peek-edge', bar_frame_fixtures.CASES)
        self.assertIn('peek-delay', bar_frame_fixtures.CASES)

    def test_unique_original_witnesses_fail_closed(self):
        for witness in (b'  property int barHoverCount: 0\n', b'  function setBarHovered(hovered) {\n'):
            with self.assertRaises(ValueError):
                bar_frame.derive_peek(self.source.replace(witness, witness + witness))
        with self.assertRaises(ValueError):
            witness = b'        HoverHandler {\n          readonly property bool peeking:'
            bar_frame.derive_frame(self.source.replace(witness, witness + witness))

    @unittest.skipUnless(shutil.which('node'), 'node unavailable for original pure model')
    def test_original_model_edge_freeze_and_strict_boundary(self):
        path = ROOT / 'vendor/omarchy/shell/plugins/bar/BarModel.js'
        code = 'const m=require(' + json.dumps(str(path)) + ''');
          const assert=require('assert');
          assert.strictEqual(m.peeksAt(null,100,false),false);
          assert.strictEqual(m.peeksAt({x:99,y:999},100,false),true);
          assert.strictEqual(m.peeksAt({x:100,y:0},100,false),false);
          assert.strictEqual(m.peeksAt({x:0,y:100},100,true),false);
          assert.strictEqual(m.nextPeekEdge(100,150,true),100);
          assert.strictEqual(m.nextPeekEdge(100,150,false),150);
        '''
        result = subprocess.run(['node', '-e', code], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
