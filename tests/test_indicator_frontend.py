"""Original indicator rendering source, not fabricated live native statuses."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import indicator_frontend as frontend
import check_clock_preview as clock
import bar_frame_fixtures


class IndicatorFrontendTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / 'vendor/omarchy/shell/plugins/bar/widgets/Indicators.qml').read_bytes()
        self.base = (ROOT / 'vendor/omarchy/shell/Ui/BarIndicator.qml').read_bytes()
        self.view = frontend.derive_indicators(self.source).decode()
        self.indicator = frontend.derive_indicator(self.base).decode()

    def test_exact_original_mirrors_and_provenance(self):
        files, meta = clock.verified_sources(ROOT)
        for target, mirror, expected, transform in [
            ('IndicatorsView.qml', 'IndicatorsView.qml', self.view, 'original-indicators-ui-v2'),
            ('Ui/BarIndicator.qml', 'BarIndicator.qml', self.indicator, 'original-indicator-ui-v1')]:
            self.assertEqual(files[target].decode(), expected)
            self.assertEqual((ROOT / 'config/shell/preview' / mirror).read_text(), expected)
            self.assertEqual(meta['upstream'][target]['stage_transform'], transform)
            self.assertEqual(meta['upstream'][target]['license'], 'MIT')
            self.assertEqual(meta['upstream'][target]['source_modifications'], [])
        self.assertIn('BarIndicator 1.0 BarIndicator.qml\n', clock.MAPS['Ui/qmldir'])

    def test_original_active_inactive_geometry_and_hover_are_preserved(self):
        source = self.source.decode()
        for start, end in [('  function setIndicatorAreaHovered(hovered) {', '  function entryForId(id) {'),
                           ('  function activeModelIndex(id) {', '  function refresh() {'),
                           ('  Component {\n    id: horizontalIndicatorsTree', '  component IndicatorLoader: Item {')]:
            original = source[source.index(start):source.index(end)]
            # Only the explicitly reviewed opt-in policy seams may differ.
            original = original.replace('    if (inactiveIndicatorsMirrored === fixedAtStart) return',
                                        '    var mirror = !stableControls && fixedAtStart\n'
                                        '    if (inactiveIndicatorsMirrored === mirror) return')
            original = original.replace('    inactiveIndicatorsMirrored = fixedAtStart',
                                        '    inactiveIndicatorsMirrored = mirror')
            original = original.replace('          indicatorBlock: "inactive"',
                                        '          indicatorBlock: root.stableControls ? "single" : "inactive"')
            for orientation in ('!root.vertical', 'root.vertical'):
                witness = '          reportActiveState: ' + orientation
                original = original.replace(witness, witness + ' && !root.stableControls')
            self.assertIn(original, self.view)
        self.assertIn('interval: 120', self.view)
        self.assertIn('bar.centerSectionRevealHeld === true && bar.centerHoverRevealSuppressed !== true', self.view)
        self.assertIn('inactiveRevealed ? 0.45 : 0', self.indicator)
        self.assertIn('concealed: !effectiveActive && !inactiveRevealed', self.indicator)
        self.assertIn('maintainIndicatorReveal: indicatorBlock === "inactive"', self.indicator)

    def test_closed_components_no_commands_or_default_backends(self):
        self.assertIn('required property var indicatorComponents', self.view)
        self.assertIn('readonly property var defaultIndicatorEntries: []', self.view)
        self.assertIn('Object.prototype.hasOwnProperty.call(indicatorComponents, id)', self.view)
        self.assertIn('sourceComponent: root.indicatorComponentForId(indicatorSlot.indicatorId)', self.view)
        for forbidden in ('ShellIpc', 'Quickshell.Io', 'Process {', 'source:', 'Qt.resolvedUrl',
                          'execDetached', 'firstPartyServiceFor', 'PasswordlessSudo', 'parseModuleJson'):
            self.assertNotIn(forbidden, self.view + self.indicator)
        for mode in ('indicators-reveal', 'indicators-order', 'indicators-missing'):
            self.assertIn(mode, bar_frame_fixtures.CASES)

    def test_optional_shared_native_registry_never_fabricates_status_or_defaults(self):
        panel = (ROOT / 'config/shell/preview/TrialPanel.qml').read_text()
        self.assertIn('IndicatorsView', panel)
        self.assertIn('"omarchy.indicators": indicatorsComponent', panel)
        self.assertEqual(panel.count('property IndicatorState indicatorState:'), 1)
        import bar_layout
        self.assertNotIn('omarchy.indicators', json.dumps(bar_layout.defaults()))
        self.assertIn('bars.notificationHost.dnd && bars.notificationHost.dnd.known ? dndIndicatorComponent : null', panel)
        self.assertIn('bars.indicatorState.nightlight.known ? nightlightIndicatorComponent : null', panel)
        self.assertIn('legacyDnd: bars.indicatorState.dnd', panel)

    def test_original_native_parent_mirrors_and_narrow_provider_seams(self):
        files, meta = clock.verified_sources(ROOT)
        for kind, derive, transform in [('Dnd', frontend.derive_dnd, 'native-dnd-indicator-v2'),
                                         ('NightLight', frontend.derive_nightlight, 'native-nightlight-indicator-v2')]:
            source = (ROOT / 'vendor/omarchy/shell/plugins/bar/indicators' / (kind + '.qml')).read_bytes()
            target = kind + 'Indicator.qml'
            self.assertEqual(files[target], derive(source))
            self.assertEqual(files[target], (ROOT / 'config/shell/preview' / target).read_bytes())
            self.assertEqual(meta['upstream'][target]['stage_transform'], transform)
            view = files[target].decode()
            self.assertIn('required property var backend', view)
            self.assertIn('  enabled: !!backend && backend.known === true\n', view)
            self.assertIn('  pressable: !!backend && backend.known === true && backend.writable === true\n', view)
            self.assertIn('onTooltipTextChanged: if (tooltipHovered) Qt.callLater', view)
            self.assertNotIn('firstPartyServiceFor', view)
            self.assertIn(source.decode().split('  activeText:')[1], view)
            witness = next(line for line in source.splitlines(keepends=True) if b'firstPartyServiceFor' in line)
            with self.assertRaises(ValueError):
                derive(source.replace(witness, witness + witness))

    def test_original_extraction_witnesses_fail_closed(self):
        default = next(line for line in self.source.splitlines(keepends=True) if b'  readonly property var defaultIndicatorEntries:' in line)
        for witness in (b'  ShellIpc {\n', default):
            with self.assertRaises(ValueError):
                frontend.derive_indicators(self.source.replace(witness, witness + witness))
        witness = b'  function extractData(raw) {\n'
        with self.assertRaises(ValueError):
            frontend.derive_indicator(self.base.replace(witness, witness + witness))

    def test_new_vendor_blobs_match_pinned_tree_and_notice(self):
        import hashlib
        tree = json.loads((ROOT / 'upstream/clock-preview.json').read_text())
        for target, data in [('IndicatorsView.qml', self.source), ('Ui/BarIndicator.qml', self.base)]:
            record = tree['upstream'][target]
            self.assertEqual(record['git_blob_sha1'], hashlib.sha1(('blob ' + str(len(data)) + '\0').encode() + data).hexdigest())
            self.assertIn(clock.COMMIT, record['url'])
        self.assertIn('Permission is hereby granted', (ROOT / 'licenses/Omarchy-MIT.txt').read_text())


if __name__ == '__main__':
    unittest.main()
