"""Original MPRIS selection remains read-only; no native bus or artwork fetch."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import audio_frontend
import audio_port_fixtures as fixtures
import check_clock_preview as preview
import media_frontend
from network_frontend import block


class MediaSelectionTests(unittest.TestCase):
    def source(self, name):
        return (ROOT / 'config/shell/preview' / name).read_text()

    def parent(self):
        return (ROOT / 'vendor/omarchy/shell/plugins/services/media/Service.qml').read_bytes()

    def test_original_selection_bodies_are_preserved(self):
        original = self.parent().decode()
        derived = media_frontend.derive_selection(self.parent()).decode()
        self.assertEqual(derived, self.source('MediaSelection.qml'))
        for name in media_frontend.FUNCTIONS:
            start = next(line for line in original.splitlines() if line.startswith('  function ' + name + '('))
            self.assertIn(block(original, start), derived)
        for witness in ('Component.onCompleted: root.syncPlayingOrder()',
                        'onPlayersChanged: root.syncPlayingOrder()', 'Instantiator {',
                        'function onIsPlayingChanged() { root.syncPlayingOrder() }'):
            self.assertIn(witness, derived)

    def test_original_pure_model_is_unchanged_and_licensed(self):
        data = (ROOT / 'vendor/omarchy/shell/plugins/services/media/MediaModel.js').read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         '566cc2c88196fedfd7b20a28e867c68efe519a65e250e4efb9946e77134654e6')
        files, meta = preview.verified_sources(ROOT)
        self.assertEqual(files['Port/MediaModel.js'], data)
        for target in ('Port/MediaModel.js', 'Commons/MediaSelection.qml'):
            self.assertEqual(meta['upstream'][target]['license'], 'MIT')
            self.assertEqual(meta['upstream'][target]['source_modifications'], [])
        self.assertEqual(meta['upstream']['Commons/MediaSelection.qml']['stage_transform'], 'guarded-media-owner-v3')

    def test_extraction_fails_closed_on_missing_or_duplicate_witnesses(self):
        original = self.parent()
        with self.assertRaises(ValueError):
            media_frontend.derive_selection(original.replace(b'  function selectActivePlayer()', b'  function otherPlayer()'))
        with self.assertRaises(ValueError):
            media_frontend.derive_selection(original + b'\n  function selectActivePlayer() { return null }\n')
        with self.assertRaises(ValueError):
            media_frontend.derive_selection(original.replace(b'  // Recompute play-order reactively', b'  // Removed play-order reactively'))

    def test_owner_excludes_external_helpers_volume_artwork_and_implicit_commands(self):
        derived = self.source('MediaSelection.qml')
        for forbidden in ('Quickshell.Io', 'ShellIpc', 'Process {', 'handleVolumeKey(',
                          'switchSource(', 'SizedImage', 'Image {', 'execDetached'):
            self.assertNotIn(forbidden, derived)
        projection = self.source('MediaPresentation.js')
        for forbidden in ('player.metadata', 'player.trackArtUrl', 'player.play(', 'player.pause('):
            self.assertNotIn(forbidden, projection)

    def test_audio_uses_original_matching_and_primitive_marks(self):
        provider = self.source('AudioOutputProvider.qml')
        self.assertIn('streamCandidates, Commons.MediaSelection.state)', provider)
        self.assertNotIn('MediaSelection {', provider)
        selection = self.source('MediaSelection.qml')
        self.assertIn('pragma Singleton', selection)
        self.assertIn('values.filter(Actions.playbackStream)', selection)
        self.assertIn('PwObjectTracker { objects: root.playbackStreams }', selection)
        snapshot = self.source('AudioPresentation.js')
        self.assertIn('Model.streamLabel(node, players, eligible)', snapshot)
        self.assertIn('active:!!Model.streamRepresentsPlayer(node, active, players, eligible)', snapshot)
        view = self.source('AudioOutputView.qml')
        self.assertIn('readonly property bool isActive: !!node && node.active', view)
        self.assertNotIn('Mpris.', view)
        self.assertNotIn('root.activeMediaPlayer', view)

    def test_isolated_cases_are_fixed_and_reject_warnings(self):
        for name in ('media-labels', 'media-selection', 'media-idle', 'media-churn'):
            text = fixtures.fixture(name)
            self.assertIn('import "FixtureMpris"', text)
            self.assertNotIn('Quickshell.Services.Mpris', text)
            self.assertIn('media discovery selection and churn never mutate audio or playback', text)
            good = 'Configuration Loaded\n' + fixtures.MARKER + '::' + name + '\n'
            self.assertTrue(fixtures.classify(name, 0, good))
            self.assertFalse(fixtures.classify(name, 0, good + 'WARN unexpected\n'))

    @unittest.skipUnless(shutil.which('node'), 'Node required for primitive projection checks')
    def test_projection_is_detached_frozen_and_has_no_methods_urls_or_raw_metadata(self):
        program = self.source('MediaPresentation.js').replace('.pragma library\n', '') + '''
const assert=require('assert');
const native={dbusName:'org.mpris.MediaPlayer2.fixture',identity:'Original',desktopEntry:'fixture',
  trackTitle:'Track',trackArtist:'Artist',trackAlbum:'Album',isPlaying:true,canPlay:true,
  metadata:{secret:'not admitted'},trackArtUrl:'https://invalid.example/no-fetch',play(){throw Error('no action')}};
const state=snapshot([native],native);
assert(Object.isFrozen(state)&&Object.isFrozen(state.players)&&Object.isFrozen(state.active));
assert.strictEqual(state.active.play,undefined);assert.strictEqual(state.active.metadata,undefined);
assert.strictEqual(state.active.trackArtUrl,undefined);
for(const row of state.players)for(const [key,value] of Object.entries(row))
  assert(key==='transportKey' ? value===null : ['string','boolean'].includes(typeof value));
native.identity='Replacement';native.trackTitle='Changed';
assert.strictEqual(state.active.identity,'Original');assert.strictEqual(state.players[0].trackTitle,'Track');
assert.deepStrictEqual(snapshot([],null),{players:[],active:null});
console.log(JSON.stringify({passed:true}));
'''
        result = subprocess.run(['node', '-e', program], text=True, capture_output=True, timeout=10, check=True)
        self.assertEqual(json.loads(result.stdout), {'passed': True})


if __name__ == '__main__':
    unittest.main()
