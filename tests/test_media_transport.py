"""Original guarded MPRIS dispatch and widget admission without host media IO."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check_clock_preview as preview
import media_frontend
import audio_port_fixtures as fixtures


class MediaTransportTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / 'config/shell/preview' / name).read_text()

    def parent(self, name):
        return (ROOT / 'vendor/omarchy/shell/plugins/services/media' / name).read_bytes()

    def test_widget_parent_is_unchanged_and_sealed_with_original_license(self):
        data = self.parent('BarWidget.qml')
        self.assertEqual(len(data), 12247)
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         'ce306a3b6d2308c948b0acf08fcf7fa651d69a6d8d5b672b3e004d1c165748a2')
        files, meta = preview.verified_sources(ROOT)
        record = meta['upstream']['MediaControlView.qml']
        self.assertEqual(record['git_blob_sha1'], 'b4c9a7d38690628eb47a9b5856a6ab23ce350a21')
        self.assertEqual(record['license'], 'MIT')
        self.assertEqual(record['source_modifications'], [])
        self.assertEqual(record['stage_transform'], 'original-media-widget-v2')
        self.assertEqual(files['MediaControlView.qml'].decode(), self.read('MediaControlView.qml'))
        self.assertEqual(files['MediaIdentity.js'].decode(), self.read('MediaIdentity.js'))

    def test_original_native_dispatch_conditions_and_calls_are_preserved(self):
        core = media_frontend.dispatch_branches(self.parent('Service.qml').decode())
        owner = self.read('MediaSelection.qml')
        self.assertIn(core, owner)
        for method in ('next', 'previous', 'play', 'pause', 'togglePlaying'):
            self.assertIn('player.' + method + '()', core)
        self.assertIn('transport.resolve(players, targetKey)', owner)
        self.assertIn('!player.canControl', owner)
        self.assertIn('!MediaModel.canHandleAction(player, action)', owner)
        self.assertIn('Request issued, not asynchronous server acceptance', owner)
        self.assertNotIn('playerForAction(', owner)

    def test_widget_preserves_original_layout_with_only_admitted_artwork(self):
        widget = self.read('MediaControlView.qml')
        self.assertEqual(media_frontend.derive_widget(self.parent('BarWidget.qml')).decode(), widget)
        for witness in ('Row {', 'NumberAnimation on x', 'PopupCard {', 'id: column',
                        'id: sourceList', 'id: sourceRow', 'iconText: "󰒭"',
                        'root.mediaService.sameTarget(', 'sourceRow.player.transportKey'):
            self.assertIn(witness, widget)
        self.assertIn('SizedImage {', widget)
        self.assertIn('url: root.mediaService ? root.mediaService.artSource : ""', widget)
        for excluded in ('trackArtUrl', 'firstPartyServiceFor(', 'Quickshell.Services.Mpris', 'Process {'):
            self.assertNotIn(excluded, widget)
        self.assertIn('onHasMediaChanged: if (!hasMedia) close()', widget)
        self.assertIn('function onBarHiddenChanged()', widget)
        self.assertIn('text: root.mediaService.errorText', widget)

    def test_transform_witnesses_fail_closed(self):
        parent = self.parent('BarWidget.qml')
        for bad in (parent.replace(b'firstPartyServiceFor("omarchy.media")', b'firstPartyServiceFor("other")'),
                    parent.replace(b'          SizedImage {', b'          Image {'),
                    parent + b'\n  MouseArea {\n  }\n'):
            with self.assertRaises(ValueError):
                media_frontend.derive_widget(bad)
        with self.assertRaises(ValueError):
            media_frontend.derive_selection(self.parent('Service.qml').replace(b'iconName = "media-next"', b'iconNameOther = "media-next"'))

    def test_isolated_transport_cases_have_closed_services_and_strict_classification(self):
        for name in ('media-transport', 'media-guards', 'media-widget', 'media-widget-churn'):
            text = fixtures.fixture(name)
            self.assertIn('import "FixtureMpris"', text)
            self.assertNotIn('Quickshell.Services.Mpris', text)
            self.assertIn('same-name replacement rejects stale command and preference', text)
            good = 'Configuration Loaded\n' + fixtures.MARKER + '::' + name + '\n'
            self.assertTrue(fixtures.classify(name, 0, good))
            self.assertFalse(fixtures.classify(name, 0, good + 'WARN unexpected\n'))
        self.assertIn('allowCommands: false', fixtures.MEDIA_PLAYER)

    @unittest.skipUnless(shutil.which('node'), 'Node required for closed dispatch probes')
    def test_generation_capability_and_dispatch_contract(self):
        model = self.parent('MediaModel.js').decode().replace('.pragma library\n', '')
        identity = self.read('MediaIdentity.js').replace('.pragma library\n', '')
        projection = self.read('MediaPresentation.js').replace('.pragma library\n', '')
        dispatch = media_frontend.derive_dispatch(self.parent('Service.qml').decode())
        program = '''const assert=require('assert');const vm=require('vm');
const MediaModel=vm.runInNewContext(MODEL+';({canHandleAction,playerKey,hasMetadata})');
IDENTITY
const Identity={same};const transport=createAuthority();let players=[],preferredPlayerKey='',errorText='';
function hasMetadata(p){return MediaModel.hasMetadata(p)}
function playerKey(p){return MediaModel.playerKey(p)}
DISPATCH
PROJECTION
let calls=[];
function native(name){return {dbusName:'org.mpris.MediaPlayer2.'+name,identity:name,trackTitle:'Track',
 canControl:true,canGoNext:true,canGoPrevious:true,canPlay:true,canPause:true,canTogglePlaying:true,isPlaying:true,
 next(){calls.push('next')},previous(){calls.push('previous')},play(){calls.push('play')},pause(){calls.push('pause')},togglePlaying(){calls.push('toggle')}}}
const a=native('a'),b=native('b');players=[a,b];
const view=snapshot(players,a,transport),key=view.active.transportKey;
assert(Object.isFrozen(key)&&Object.isFrozen(view.active));assert.strictEqual(key,view.players[0].transportKey);
assert.strictEqual(view.active.next,undefined);assert.strictEqual(view.active.trackArtUrl,undefined);
const invalid=snapshot([native('')],null,transport).players[0];
assert.strictEqual(invalid.transportKey,null);assert.strictEqual(invalid.canControl,false);
assert.deepStrictEqual(calls,[]);
for(const bad of [null,undefined,{},[],true,'a',{...key,generation:'1'},{...key,generation:NaN},
 {...key,generation:Infinity},{...key,generation:-1},{...key,name:'https://invalid.example/'},{...key,extra:true}])assert(!runAction('next',false,bad));
assert(!runAction('launch',false,key));assert(!runAction('next',true,key));assert.deepStrictEqual(calls,[]);
a.canControl=false;assert(!runAction('next',false,key));a.canControl=true;
a.canGoNext=false;assert(!runAction('next',false,key));a.canGoNext=true;
assert(runAction('next',false,key));assert.deepStrictEqual(calls,['next']);
assert(runAction('previous',false,key));assert(runAction('playPause',false,key));
a.isPlaying=false;assert(runAction('playPause',false,key));
a.canPlay=false;assert(runAction('playPause',false,key));
a.canTogglePlaying=false;assert(!runAction('play',false,key));
assert.deepStrictEqual(calls,['next','previous','pause','play','toggle']);
let tries=0;a.next=()=>{tries++;throw Error('unknown outcome')};
assert(!runAction('next',false,key));assert.strictEqual(tries,1);assert(errorText.includes('uncertain'));
players=[b];assert(!runAction('next',false,key));assert(!selectPlayer(key));
const replacement=native('a');players=[replacement];const fresh=snapshot(players,replacement,transport).active.transportKey;
assert(fresh.generation!==key.generation);assert(!runAction('next',false,key));assert(!selectPlayer(key));
assert(selectPlayer(fresh));assert.strictEqual(preferredPlayerKey,replacement.dbusName);
players=[a,replacement];assert(!runAction('next',false,fresh));
assert.strictEqual(tries,1);assert.deepStrictEqual(calls,['next','previous','pause','play','toggle']);
console.log('guarded-media-ok');
'''.replace('MODEL', json.dumps(model)).replace('IDENTITY', identity).replace('DISPATCH', dispatch).replace('PROJECTION', projection)
        result = subprocess.run(['node', '-e', program], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'guarded-media-ok')


if __name__ == '__main__':
    unittest.main()
