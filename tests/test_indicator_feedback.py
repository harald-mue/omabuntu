"""Stable native controls preserve the original UI and proof-bound action gates."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bar_frame_fixtures
import indicator_feedback_fixtures as fixtures
import indicator_frontend


class IndicatorFeedbackTests(unittest.TestCase):
    def test_stability_is_an_explicit_native_opt_in_not_a_new_panel(self):
        source = (ROOT / 'vendor/omarchy/shell/plugins/bar/widgets/Indicators.qml').read_bytes()
        view = indicator_frontend.derive_indicators(source).decode()
        self.assertIn('stableControls: setting("stableControls", false) === true', view)
        self.assertIn('indicatorBlock: root.stableControls ? "single" : "inactive"', view)
        self.assertIn('revealInactiveIndicators: stableControls || alwaysShowIndicators ||', view)
        self.assertIn('var mirror = !stableControls && fixedAtStart', view)
        self.assertEqual(view.count('&& !root.stableControls'), 2)
        self.assertEqual(view.count('component IndicatorBlock:'), 1)
        self.assertEqual(view.count('component ActiveIndicatorBlock:'), 1)
        self.assertIn('items: ["NightLight", "Dnd"], stableControls: true',
                      (ROOT / 'config/shell/preview/TrialPanel.qml').read_text())
        # No new visual component, direct setter, loader URL or default admission.
        for forbidden in ('StablePanel', 'NativeIndicatorRow', 'Process {', 'source:'):
            self.assertNotIn(forbidden, view)

    def test_four_tooltip_labels_match_the_reviewed_original_catalog(self):
        text = (ROOT / 'config/shell/preview/I18n.qml').read_text()
        for key, label in [('allowNotifications', 'Allow Notifications'),
                           ('silenceNotifications', 'Silence Notifications'),
                           ('dayLight', 'Day Light'), ('nightLight', 'Night Light')]:
            self.assertIn(json.dumps('bar.' + key) + ': ' + json.dumps(label), text)
        meta = json.loads((ROOT / 'upstream/clock-preview.json').read_text())
        self.assertIn('c34e291f8309073442ed9d2cfa971877b04c1bd4eaea9462f2f3906fce758584', json.dumps(meta))
        self.assertEqual(meta['authored']['Commons/I18n.qml']['sha256'], hashlib.sha256(text.encode()).hexdigest())

    def test_readback_fence_is_distinct_from_component_admission(self):
        text = (ROOT / 'config/shell/preview/IndicatorState.qml').read_text()
        self.assertIn('!busy && !readbackPending && !blocked', text)
        self.assertLess(text.index('if (action) readbackPending = true'), text.index('inFlight = null', text.index('function finish')))
        self.assertIn('if (blocked) states = ({})', text)
        self.assertIn('states = data.states\n        readbackPending = false', text)
        self.assertNotIn('if (action) { states = ({})', text)
        self.assertIn('if (action) Qt.callLater(root.refresh)', text)
        # Unknown, malformed, uncertain and stale-scope responses still revoke.
        self.assertIn('states = ({})', text)
        self.assertIn('scope = newScope()\n    readbackPending = false', text)

    def test_hover_is_not_disabled_by_the_write_fence(self):
        for name, derive in [('Dnd', indicator_frontend.derive_dnd),
                             ('NightLight', indicator_frontend.derive_nightlight)]:
            source = (ROOT / 'vendor/omarchy/shell/plugins/bar/indicators' / (name + '.qml')).read_bytes()
            text = derive(source).decode()
            self.assertIn('enabled: !!backend && backend.known === true\n', text)
            self.assertIn('pressable: !!backend && backend.known === true && backend.writable === true', text)
            self.assertIn('if (root.tooltipHovered && root.bar) root.bar.showTooltip(root, root.tooltipText)', text)
            # Native parent glyphs, texts and original click handlers remain exact.
            self.assertIn(source.decode().split('  activeText:')[1], text)

    def test_contained_input_uses_actual_original_controls_frame_and_tooltip_host(self):
        for mode in fixtures.CASES:
            self.assertIn(mode, bar_frame_fixtures.CASES)
            text = fixtures.fixture(mode)
            for witness in ('import QtTest', 'DndIndicator{backend:dndProvider}', 'NightLightIndicator{backend:night}',
                            'BarFrame {', 'IndicatorsView {', 'BarTooltipHost.qml',
                            'input.mouseMove(second', 'input.mouseClick(second', 'editor.writes===0'):
                self.assertIn(witness, text)
            for forbidden in ('busctl', 'hyprctl', '.hyprsunset.sock', 'Process {', 'execDetached'):
                self.assertNotIn(forbidden, text)
        with self.assertRaises(ValueError):
            fixtures.fixture('unreviewed')

    def test_actual_owner_fixture_covers_no_optimistic_state_or_writable_gap(self):
        text = bar_frame_fixtures.fixture('indicator-owner')
        for witness in ('observedDndDelegate=dnd', 'nativeOwner.readbackPending',
                        'indicatorItem(indicators,"Dnd","inactive")===observedDndDelegate',
                        'confirmation retains observation without optimistic state or writable gap',
                        'uncertainty still revokes admission immediately'):
            self.assertIn(witness, text)


if __name__ == '__main__':
    unittest.main()
