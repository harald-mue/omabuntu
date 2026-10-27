"""Audio output contracts; unit tests never connect to PipeWire or play sound."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_clock_preview as preview
import audio_port_fixtures as fixtures


class AudioPortTests(unittest.TestCase):
    def test_original_model_and_slider_are_unchanged(self):
        files, meta = preview.verified_sources(ROOT)
        for target, source in {"Port/AudioModel.js": "shell/plugins/panels/audio/Model.js", "Ui/PanelSlider.qml": "shell/Ui/PanelSlider.qml"}.items():
            self.assertEqual(files[target], (ROOT / "vendor/omarchy" / source).read_bytes())
            self.assertEqual(meta["upstream"][target]["stage_transform"], "none")

    def test_typed_sources_admitted_without_helper_or_process_route(self):
        # Plan 001: typed capture devices are native PipeWire; the upstream
        # helper and the wpctl/pactl untyped route stay excluded everywhere.
        for name in ("AudioOutputProvider.qml", "AudioOutputView.qml", "AudioActions.js", "AudioPresentation.js"):
            text = (ROOT / "config/shell/preview" / name).read_text()
            for forbidden in ("Process {", "execDetached", "wpctl", "pactl", "Quickshell.Io", "UntypedInput", "omarchy-"):
                self.assertNotIn(forbidden, text)

    def test_provider_input_boundary_is_native_and_gated(self):
        text = (ROOT / "config/shell/preview/AudioOutputProvider.qml").read_text()
        self.assertIn("!node.isSink && !node.isStream && node.audio", text)
        self.assertIn('!== "quickshell"', text)
        self.assertEqual(text.count("Pipewire.preferredDefaultAudioSource = node"), 1)
        self.assertIn("function chooseInput(key)", text)
        self.assertIn("PwNodePeakMonitor {", text)
        # The peak monitor runs only while the panel is open, like upstream.
        self.assertIn("enabled: root.monitoring && !!Pipewire.defaultAudioSource", text)

    def test_control_resolves_identity_and_limits_volume(self):
        text = (ROOT / "config/shell/preview/AudioActions.js").read_text()
        self.assertIn("node.id === key.id && node.name === key.name", text)
        self.assertIn("node.isSink && !node.isStream", text)
        self.assertIn("node.ready", text)
        self.assertIn("Math.max(0, Math.min(1, value))", text)
        self.assertIn('typeof value !== "number"', text)
        # The source resolver keeps the typed-only contract: never a sink,
        # never a stream, never a node without PwNode.audio.
        self.assertIn("function resolveSource(nodes, key)", text)
        self.assertIn("!node.isSink && !node.isStream && node.audio", text)
        self.assertIn("function setSourceVolume(nodes, key, value)", text)
        self.assertIn("function toggleSourceMute(nodes, key)", text)

    def test_native_provider_has_no_startup_mutator(self):
        text = (ROOT / "config/shell/preview/AudioOutputProvider.qml").read_text()
        self.assertIn("PwObjectTracker", text)
        self.assertNotIn("Component.onCompleted", text)
        self.assertNotIn("onStateChanged", text)
        self.assertEqual(text.count("Pipewire.preferredDefaultAudioSink = node"), 1)
        self.assertIn("function chooseOutput(key)", text)
        self.assertEqual(text.count("Pipewire.preferredDefaultAudioSource = node"), 1)
        self.assertIn("function chooseInput(key)", text)

    def test_view_uses_original_controls_and_pins_drag_identity(self):
        text = (ROOT / "config/shell/preview/AudioOutputView.qml").read_text()
        for component in ("PanelSlider {", "BarIconButton {", "KeyboardPanel {", "ToggleSwitch {"):
            self.assertIn(component, text)
        self.assertIn("root.dragTarget = dragging ? root.current : null", text)
        self.assertIn("Text.PlainText", text)
        controller = (ROOT / "config/shell/preview/AudioPanelController.qml").read_text()
        self.assertIn("setVolume(dragTarget || current, value)", controller)
        self.assertIn("wheelRemainder / 120", controller)

    def test_fixed_fixtures_are_not_native_audio(self):
        self.assertEqual(len(fixtures.CASES), 8)
        with self.assertRaises(ValueError):
            fixtures.fixture("play-test-sound")
        text = fixtures.fixture("controls")
        self.assertNotIn("Quickshell.Services.Pipewire", text)
        self.assertIn("no startup mutation or popup", text)
        self.assertIn("five percent wheel", text)

    def test_classifier_rejects_errors_crashes_and_wrong_control(self):
        good = "Configuration Loaded\n" + fixtures.MARKER + "::controls\n"
        self.assertTrue(fixtures.classify("controls", 0, good))
        self.assertFalse(fixtures.classify("controls", -11, good))
        self.assertFalse(fixtures.classify("controls", 0, good + "WARN unexpected\n"))
        self.assertFalse(fixtures.classify("controls", 0, "Configuration Loaded\n"))
        self.assertFalse(fixtures.classify("negative", 42, "ERROR unrelated\n"))
        self.assertTrue(fixtures.classify("negative", 42, "ERROR deliberate audio assertion\n"))


if __name__ == "__main__":
    unittest.main()
