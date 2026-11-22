"""Playback-stream source contracts; actual JS/QML runs in isolated fixtures."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import audio_port_fixtures as fixtures
import check_clock_preview as preview


class AudioStreamTests(unittest.TestCase):
    def source(self, name):
        return (ROOT / 'config/shell/preview' / name).read_text()

    def test_streams_have_their_own_tracker_and_primitive_snapshot(self):
        provider = self.source('AudioOutputProvider.qml')
        self.assertIn('values.filter(Actions.playbackStream)', provider)
        self.assertIn('PwObjectTracker { objects: root.streamCandidates }', provider)
        self.assertIn('Presentation.streamSnapshot(Pipewire.ready, streamCandidates, Commons.MediaSelection.state)', provider)
        self.assertNotIn('Component.onCompleted', provider)

    def test_candidate_filter_never_reads_unbound_properties(self):
        actions = self.source('AudioActions.js')
        candidate = actions.split('function playbackStream(node) {', 1)[1].split('\n}', 1)[0]
        self.assertNotIn('properties', candidate)
        self.assertIn('node.isSink === true && node.isStream === true', candidate)
        self.assertIn('"quickshell"', candidate)
        serial = actions.split('function streamSerial(node) {', 1)[1].split('\n}', 1)[0]
        self.assertLess(serial.index('!node.ready'), serial.index('node.properties'))

    def test_serial_and_type_are_revalidated_before_every_stream_action(self):
        actions = self.source('AudioActions.js')
        self.assertIn('streamSerial(node) === key.serial', actions)
        for function in ('setStreamVolume', 'toggleStreamMute'):
            body = actions.split('function ' + function + '(', 1)[1].split('\n}', 1)[0]
            self.assertLess(body.index('resolveStream(nodes, key)'), body.index('node.audio.'))
        self.assertIn('Math.max(0, Math.min(1.5, value))', actions)
        self.assertIn('Math.max(0, Math.min(1, value))', actions)

    def test_delegates_do_not_get_native_stream_references(self):
        presentation = self.source('AudioPresentation.js')
        self.assertIn('serial:Actions.streamSerial(node)', presentation)
        self.assertIn('Object.freeze({ready:!!ready, streams:Object.freeze(rows)})', presentation)
        view = self.source('AudioOutputView.qml')
        self.assertIn('component StreamRow: CursorSurface', view)
        self.assertNotIn('streamRow.node.audio', view)
        self.assertIn('dragging ? streamRow.dragKey : streamRow.node', view)

    def test_stream_keyboard_actions_do_not_adjust_device_volume(self):
        controller = self.source('AudioPanelController.qml')
        self.assertIn('if (section === "streams") return displayAudioStreams.length;', controller)
        self.assertIn('setStreamVolume(row, row.volume + delta)', controller)
        self.assertIn('toggleStreamMute(displayAudioStreams[selectedIndex])', controller)
        self.assertIn('streams[k].serial === key.serial', controller)
        self.assertIn('onDisplayAudioStreamsChanged: clampCursor()', controller)

    def test_stream_fixture_coverage_is_contained_and_fixed(self):
        markers = {'streams': 'per-app volume only',
                   'stream-guards': 'same name and ID reused with new serial',
                   'stream-navigation': 'm mutes selected stream only',
                   'stream-drag': 'drag cannot retarget a replacement stream'}
        for name, marker in markers.items():
            text = fixtures.fixture(name)
            self.assertIn(marker, text)
            self.assertNotIn('Quickshell.Services.Pipewire', text)
            good = 'Configuration Loaded\n' + fixtures.MARKER + '::' + name + '\n'
            self.assertTrue(fixtures.classify(name, 0, good))
            self.assertFalse(fixtures.classify(name, 0, good + 'WARN unexpected\n'))

    def test_stream_source_is_sealed_and_vendor_parent_is_unchanged(self):
        files, meta = preview.verified_sources(ROOT)
        self.assertEqual(files['AudioOutputView.qml'].decode(), self.source('AudioOutputView.qml'))
        self.assertEqual(meta['upstream']['AudioOutputView.qml']['stage_transform'],
                         'audio-native-input-frontend-v5')
        self.assertEqual(meta['upstream']['AudioOutputView.qml']['source_modifications'], [])


if __name__ == '__main__':
    unittest.main()
