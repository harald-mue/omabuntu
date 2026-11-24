"""Source fidelity is distinct from interactive and pixel/theme acceptance."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audio_frontend as frontend
import check_clock_preview as preview
import audio_port_fixtures as fixtures


class AudioFidelityTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "vendor/omarchy/shell/plugins/panels/audio/Panel.qml").read_bytes()
        self.output = frontend.derive_audio(self.source).decode()

    def test_frontend_is_generated_from_original_not_another_layout(self):
        self.assertEqual(self.output, (ROOT / "config/shell/preview/AudioOutputView.qml").read_text())
        files, meta = preview.verified_sources(ROOT)
        self.assertEqual(files["AudioOutputView.qml"].decode(), self.output)
        self.assertEqual(meta["upstream"]["AudioOutputView.qml"]["stage_transform"], "audio-native-input-frontend-v8")
        self.assertNotIn("AudioOutputView.qml", meta["authored"])

    def test_original_hero_is_byte_identical(self):
        start, end = "          // ---------- Hero:", "          // ---- Output devices ----"
        self.assertEqual(frontend.between(self.source.decode(), start, end), frontend.between(self.output, start, end))
        for token in ("ToggleSwitch {", "PanelToolTip {", "Style.font.display", "root.outputVolumeName("):
            self.assertIn(token, self.output)

    def test_original_output_geometry_is_preserved(self):
        start, end = "          // ---- Output devices ----", "          // ---- Input ----"
        original = frontend.between(self.source.decode(), start, end)
        # Only drag identity, admitted-route enablement and unknown percentage;
        # the original section geometry/content otherwise remains identical.
        original = original.replace("                onMoved: function(v)",
            "                onDraggingChanged: root.dragTarget = dragging ? root.current : null\n                onMoved: function(v)")
        original = frontend.replace(original, 'enabled: !!root.sink', 'enabled: root.outputControlAvailable')
        original = frontend.replace(original,
            'text: Commons.I18n.formatNumber(Math.round((outputSlider.dragging ? outputSlider.liveValue : root.outputVolume) * 100)) + "%"',
            'text: root.outputControlAvailable ? Commons.I18n.formatNumber(Math.round((outputSlider.dragging ? outputSlider.liveValue : root.outputVolume) * 100)) + "%" : "—"')
        self.assertIn(original, self.output)
        self.assertIn("panel.fittedContentWidth(Style.space(380))", self.output)

    def test_original_sink_row_has_only_identity_guard_change(self):
        row = frontend.between(self.source.decode(), "  component SinkRow: CursorSurface {\n", "  // Input device row")
        row = row.replace("root.sink.id === node.id", "root.sink.id === node.id && root.sink.name === node.name")
        self.assertIn(row, self.output)
        self.assertIn("current: isActive", row)
        self.assertIn("root.cursorActive", row)

    def test_original_input_geometry_is_preserved(self):
        start, end = "          // ---- Input ----\n", "          // ---- Per-app streams ----\n"
        original = frontend.between(self.source.decode(), start, end)
        # Same reviewed replacements the extraction makes: drag-identity guard,
        # Style.alpha for the upstream Util.alpha helper, provider-side peak.
        original = original.replace("                  onMoved: function(v) { root.setInputVolume(v) }",
            "                  onDraggingChanged: if (dragging) root.beginInputDrag()\n"
            "                  onMoved: function(v) { if (!dragging) root.inputDragCancelledState = false; root.setInputVolume(v) }\n"
            "                  onReleased: function(v) { root.finishInputDrag(v) }\n"
            "                  onEnabledChanged: if (!enabled) root.cancelInputDrag()\n"
            "                  Connections {\n"
            "                    target: root\n"
            "                    function onInputDragCancelled() { inputSlider.dragging = false; inputSlider.liveValue = inputSlider.value }\n"
            "                  }")
        original = original.replace("Util.alpha(root.bar.foreground, 0.18)",
                                     "Style.alpha(root.bar.foreground, 0.18)")
        original = original.replace("inputPeakMonitor.peak", "root.inputPeak")
        original = frontend.replace(original, "enabled: !!root.source", "enabled: root.inputWriteAvailable")
        self.assertIn(original, self.output)
        self.assertIn("root.inputPeak", self.output)
        self.assertIn("Style.alpha(root.bar.foreground, 0.18)", self.output)

    def test_original_source_row_has_only_identity_guard_change(self):
        start = "  // Input device row — sibling of SinkRow for the \"input\" section.\n"
        row = frontend.between(self.source.decode(), start, "  // Per-app stream row")
        row = row.replace("root.source.id === node.id",
                          "root.source.id === node.id && root.source.name === node.name")
        self.assertIn(row, self.output)
        self.assertIn("onClicked: root.setDefaultSource(sourceRow.node)", row)

    def test_helpers_and_untyped_routes_are_absent(self):
        # Original playback-stream controls use native typed actions; helpers,
        # IPC and untyped capture remain excluded.
        for forbidden in ("Process {", "FileView {", "Quickshell.Io", "UntypedInput", "Mpris",
                          "ipcTarget", "moduleName", "wpctl", "pactl"):
            self.assertNotIn(forbidden, self.output)
        self.assertIn("SourceRow", self.output)
        self.assertIn("onMoveRequested", self.output)
        self.assertIn("onActivateRequested", self.output)
        self.assertIn("onCloseRequested", self.output)

    def test_original_stream_section_and_controls_are_preserved(self):
        start = "          // ---- Per-app streams ----\n"
        end = "        }\n      }\n    }\n  }\n\n  // ---- Reusable inline components ----\n"
        self.assertIn(frontend.between(self.source.decode(), start, end), self.output)
        for token in ("component StreamRow: CursorSurface", "root.streamLabel(streamRow.node)",
                      'Commons.I18n.t("audio.sources")', "maximum: 1.5",
                      "root.toggleStreamMute(streamRow.node)",
                      "dragging ? streamRow.dragKey : streamRow.node"):
            self.assertIn(token, self.output)
        self.assertNotIn("streamRow.node.audio", self.output)
        self.assertIn("streamRow.dragKey = dragging ? streamRow.node : null", self.output)

    def test_extraction_fails_when_unique_witness_changes(self):
        with self.assertRaises(ValueError):
            frontend.derive_audio(self.source.replace(b"          // ---- Per-app streams ----", b"changed"))
        with self.assertRaises(ValueError):
            frontend.derive_audio(self.source.replace(b"  // Input device row", b"moved"))
        with self.assertRaises(ValueError):
            frontend.derive_audio(self.source + b"\n  KeyboardPanel {\n")
        with self.assertRaises(ValueError):
            frontend.derive_keyboard(b"not the pinned KeyboardPanel")

    def test_native_keyboard_never_uses_exclusive_focus(self):
        source = (ROOT / "vendor/omarchy/shell/Ui/KeyboardPanel.qml").read_bytes()
        text = frontend.derive_keyboard(source).decode()
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("//"))
        self.assertNotIn("WlrKeyboardFocus.Exclusive", code)
        self.assertIn("visible: open\n", text)
        self.assertIn("open ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None", text)
        self.assertIn("root.bar.itemContainsPoint", text)
        self.assertIn("active: !!root.content && (root.open || root.contentRequested)", text)

    def test_offscreen_surface_is_not_used_in_live_profile(self):
        files, _ = preview.verified_sources(ROOT)
        self.assertNotEqual(files["Ui/KeyboardPanel.qml"], fixtures.KEYBOARD_SURFACE.encode())
        self.assertIn(b"WlrLayershell.keyboardFocus", files["Ui/KeyboardPanel.qml"])
        self.assertNotIn("PanelWindow", fixtures.KEYBOARD_SURFACE)
        self.assertIn("original visual content loads", fixtures.fixture("navigation"))
        self.assertIn("device row does not adjust global volume", fixtures.fixture("navigation"))


if __name__ == "__main__":
    unittest.main()
