"""Playback-stream source contracts; actual JS/QML runs in isolated fixtures."""
from pathlib import Path
import json
import re
import shutil
import subprocess
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

    @unittest.skipUnless(shutil.which('node'), 'Node needed for label projection checks')
    def test_duplicate_metadata_is_bounded_stable_and_never_participant_grouping(self):
        def js(path):
            return re.sub(r'^\.(?:pragma|import).*\n', '', path.read_text(), flags=re.M)
        program = '''const assert=require('assert'),vm=require('vm');
const Model=vm.runInNewContext(MODEL+';({streamLabel,streamRepresentsPlayer})');
const Actions=vm.runInNewContext(ACTIONS+';({playbackStream,streamSerial})');
const P=vm.runInNewContext(PRESENTATION+';({streamSnapshot})',{Model,Actions});
function stream(id,extra={}){return {id,name:'browser-'+id,ready:true,isSink:true,isStream:true,
 description:'Microsoft Edge',properties:Object.assign({'object.serial':String(100+id),'application.name':'Microsoft Edge'},extra),
 audio:{volume:.5,muted:false}}}
const a=stream(1,{'media.name':'WebRTC playback'}),b=stream(2,{'media.name':'WebRTC playback'});
let rows=P.streamSnapshot(true,[a,b]).streams;
assert.strictEqual(rows.length,2);assert.strictEqual(rows[0].label,'Microsoft Edge · Stream #101 · WebRTC playback');
assert.strictEqual(rows[1].label,'Microsoft Edge · Stream #102 · WebRTC playback');
assert.strictEqual(P.streamSnapshot(true,[b,a]).streams[1].label,rows[0].label);
assert.strictEqual(P.streamSnapshot(true,[a]).streams[0].label,'Microsoft Edge');
assert(Object.isFrozen(rows[0]));assert.strictEqual(rows[0].properties,undefined);
a.properties['media.name']='';b.properties['media.name']={secret:'never stringify'};
rows=P.streamSnapshot(true,[a,b]).streams;assert.strictEqual(rows[0].label,'Microsoft Edge · Stream #101');
assert.strictEqual(rows[1].label,'Microsoft Edge · Stream #102');
a.properties['media.name']='bad'+String.fromCharCode(10)+'title';a.properties['media.role']='Communication';
assert.strictEqual(P.streamSnapshot(true,[a,b]).streams[0].label,'Microsoft Edge · Stream #101 · Communication');
a.properties['media.name']='X'.repeat(513);
assert(!P.streamSnapshot(true,[a,b]).streams[0].label.includes('XXX'));
a.properties['media.name']='Z'.repeat(200);
assert(P.streamSnapshot(true,[a,b]).streams[0].label.endsWith('Z'.repeat(96)));
a.properties['media.name']='spoof'+String.fromCharCode(0x202e);
assert(!P.streamSnapshot(true,[a,b]).streams[0].label.includes('spoof'));
const unbound=stream(3);unbound.ready=false;Object.defineProperty(unbound,'properties',{get(){throw Error('unbound metadata read')}});
assert.strictEqual(P.streamSnapshot(true,[a,b,unbound]).streams.length,2);
b.properties['object.serial']='999';assert(P.streamSnapshot(true,[a,b]).streams[1].label.includes('Stream #999'));
console.log('stream-labels-ok');'''
        for token, data in (('MODEL', js(ROOT/'vendor/omarchy/shell/plugins/panels/audio/Model.js')),
                            ('ACTIONS', js(ROOT/'config/shell/preview/AudioActions.js')),
                            ('PRESENTATION', js(ROOT/'config/shell/preview/AudioPresentation.js'))):
            program = program.replace(token, json.dumps(data), 1)
        result = subprocess.run(['node', '-e', program], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'stream-labels-ok')

    def test_stream_heading_has_a_real_english_catalog_entry(self):
        self.assertIn('"audio.sources": "APPLICATION AUDIO"', self.source('I18n.qml'))
        self.assertIn('textFormat: Text.PlainText', self.source('AudioOutputView.qml'))

    def test_stream_source_is_sealed_and_vendor_parent_is_unchanged(self):
        files, meta = preview.verified_sources(ROOT)
        self.assertEqual(files['AudioOutputView.qml'].decode(), self.source('AudioOutputView.qml'))
        self.assertEqual(meta['upstream']['AudioOutputView.qml']['stage_transform'],
                         'audio-native-input-frontend-v9')
        self.assertEqual(meta['upstream']['AudioOutputView.qml']['source_modifications'], [])


if __name__ == '__main__':
    unittest.main()
