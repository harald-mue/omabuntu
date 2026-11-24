"""Source seals, graph/virtual-input identities and contained audio fixtures."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import audio_completion_fixtures as fixtures
import audio_feedback_frontend
import check_clock_preview as preview


def source(name):
    return re.sub(r'^\.(?:pragma|import).*\n', '', (ROOT / 'config/shell/preview' / name).read_text(), flags=re.M)


class AudioCompletionSourceTests(unittest.TestCase):
    def test_original_osd_image_and_model_are_unchanged_licensed_and_sealed(self):
        files, meta = preview.verified_sources(ROOT)
        for target in ('AudioOsdView.qml', 'Port/OsdModel.js', 'Ui/SizedImage.qml'):
            record = meta['upstream'][target]
            data = (ROOT / record['vendor_path']).read_bytes()
            self.assertEqual(record['license'], 'MIT'); self.assertEqual(record['source_modifications'], [])
            self.assertEqual(hashlib.sha256(data).hexdigest(), record['sha256'])
            self.assertEqual(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(), record['git_blob_sha1'])
        parent = (ROOT / meta['upstream']['AudioOsdView.qml']['vendor_path']).read_bytes()
        self.assertEqual(audio_feedback_frontend.derive_osd(parent), files['AudioOsdView.qml'])
        self.assertIn(b'QtObject {', files['AudioOsdView.qml'])
        self.assertIn(b'root.hasProgress', files['AudioOsdView.qml'])
        self.assertNotIn(b'ShellIpc', files['AudioOsdView.qml'])
        self.assertEqual(files['Port/OsdModel.js'], (ROOT / meta['upstream']['Port/OsdModel.js']['vendor_path']).read_bytes())

    def test_transform_and_fixture_surface_fail_closed_on_parent_changes(self):
        data = (ROOT / 'vendor/omarchy/shell/plugins/osd/Osd.qml').read_bytes()
        for old in (b'  function open(payloadJson) {\n', b'  OverlayWindow {\n', b'    text: root.message'):
            with self.subTest(old=old), self.assertRaises((ValueError, IndexError)):
                audio_feedback_frontend.derive_osd(data.replace(old, b'changed', 1))
        derived = audio_feedback_frontend.derive_osd(data)
        self.assertIn(b'FixtureAudioOverlay', fixtures.overlay_surface(derived))
        with self.assertRaises(ValueError): fixtures.overlay_surface(derived.replace(b'"omarchy-osd"', b'"changed"'))

    def test_shared_nonvisual_owner_and_packaged_dependencies_have_no_startup_grant(self):
        panel = (ROOT / 'config/shell/preview/TrialPanel.qml').read_text()
        self.assertEqual(panel.count('property AudioOutputProvider'), 1)
        self.assertIn('backend: bars.audioProvider', panel)
        self.assertNotIn('    AudioOutputProvider {', panel)
        provider = (ROOT / 'config/shell/preview/AudioOutputProvider.qml').read_text()
        self.assertIn('QtObject {', provider)
        state = (ROOT / 'config/shell/preview/AudioNativeState.qml').read_text()
        self.assertIn('property bool granted: false', state)
        self.assertIn('known && subscribing && !busy', state)
        package = (ROOT / 'tools/package_user.py').read_text()
        for name in ('audio_pactl.py', 'audio_profiles.py', 'audio_controls.py', 'audio_recovery.py', 'audio_events.py', 'audio_artwork.py'):
            self.assertIn(repr(name), package)
        for name in fixtures.CASES:
            text = fixtures.fixture(name)
            self.assertIn('OMABUNTU_AUDIO_FIXTURE_OK::', text)
            self.assertIn('bounded completion fixture', text)
            self.assertNotIn('Quickshell.Services.Pipewire', text)

    def test_advanced_audio_is_disabled_at_surface_cursor_and_invocation_boundaries(self):
        files, meta = preview.verified_sources(ROOT)
        output = files["AudioOutputView.qml"].decode()
        controls = files["AudioNativeControls.qml"].decode()
        controller = files["AudioPanelController.qml"].decode()
        self.assertIn("visible: !root.advancedAudio", output)
        self.assertIn("? ScrollBar.vertical.width + Style.space(10) : 0", output)
        self.assertIn("ScrollBar.horizontal.policy: ScrollBar.AlwaysOff", output)
        self.assertIn("if (root.advancedAudio) return", output)
        self.assertIn('readonly property bool advancedAudioAvailable: false', controller)
        self.assertIn('if (advancedAudio && !advancedAudioAvailable) { advancedAudio = false; return; }', controller)
        self.assertIn('visible: available && bridge !== null', controls)
        self.assertIn('enabled: available', controls)
        self.assertIn('if (!available || !bridge) return []', controls)
        self.assertIn('if (!available || !row || !row.enabled', controls)
        self.assertIn('return advancedAudioAvailable && !!profileControls', controller)
        self.assertIn('if (advancedAudioAvailable && profileControls)', controller)
        self.assertIn('if (advancedAudio && section !== "profiles") return false;', controller)
        self.assertIn('if (advancedAudio && focusSection !== "profiles") return;', controller)
        self.assertEqual(meta["upstream"]["AudioOutputView.qml"]["stage_transform"], "audio-native-input-frontend-v8")
        fixture = fixtures.fixture("native-layout")
        for witness in ("Advanced audio navigation is hidden and disabled", "forced legacy page selection is refused", "disabled actions and stale rows cannot invoke queries", "disabled page never grants or starts optional audio access", "measured content-to-scrollbar gap", "nonoverflow returns the full content width"):
            self.assertIn(witness, fixture)

    def test_disabling_advanced_preserves_accepted_normal_height_and_scroll_geometry(self):
        files, _ = preview.verified_sources(ROOT)
        output = files["AudioOutputView.qml"].decode()
        controls = files["AudioNativeControls.qml"].decode()
        self.assertIn("panel.fittedContentHeight(panel.loadedContentHeight)", output)
        self.assertNotIn("Style.space(560)", output)
        self.assertIn("contentHeight: panelColumn.implicitHeight", output)
        self.assertIn("contentWidth: availableWidth", output)
        self.assertIn("rightPadding: leftPadding", output)
        self.assertIn('objectName:"audioAdvancedNavigation"', controls)
        self.assertIn('iconText:root.expanded ?', controls)
        fixture = fixtures.fixture("native-layout")
        for witness in ("normal panel grows beyond the old cap", "constrained fallback scroll reaches the entire last original row", "nonoverflow content has no asymmetric reserved space", "reopen keeps Advanced audio disabled"):
            self.assertIn(witness, fixture)

    def test_artwork_slot_cannot_consume_native_remote_or_arbitrary_file_urls(self):
        widget = (ROOT / 'config/shell/preview/MediaControlView.qml').read_text()
        owner = (ROOT / 'config/shell/preview/MediaArtwork.qml').read_text()
        self.assertIn('SizedImage {', widget)
        self.assertIn('root.mediaService.artSource', widget)
        self.assertNotIn('trackArtUrl', widget)
        self.assertIn('data.source.startsWith(root.cachePrefix)', owner)
        self.assertIn('root.issued===root.generation', owner)
        self.assertIn('!url.startsWith("file:///")', owner)


@unittest.skipUnless(shutil.which('node'), 'Node needed for closed graph/identity probes')
class AudioCompletionIdentityTests(unittest.TestCase):
    def probe(self, body):
        model = re.sub(r'^\.pragma.*\n', '', (ROOT / 'vendor/omarchy/shell/plugins/panels/audio/Model.js').read_text(), flags=re.M)
        program = '''const assert=require('assert'),vm=require('vm');
const Actions=vm.runInNewContext(ACTIONS+';({streamSerial})');
const Routing=vm.runInNewContext(ROUTING+';({createAuthority,sources,resolve,target,currentNode,sameKey})',{Actions});
const Model=vm.runInNewContext(MODEL+';({nodeLabel,sourceGlyph})');
const Untyped=vm.runInNewContext(UNTYPED+';({merge,target})',{Actions,Routing,Model});
function node(id,name,sink=true,stream=false){return {id,name,isSink:sink,isStream:stream,ready:true,
 properties:{'object.serial':String(id+100)},audio:{volume:.5,muted:false}}}
BODY
console.log('completion-identity-ok');'''
        for token, value in (('ACTIONS', source('AudioActions.js')), ('ROUTING', source('AudioRouting.js')),
                             ('MODEL', model), ('UNTYPED', source('AudioUntyped.js'))):
            program = program.replace(token, json.dumps(value), 1)
        result = subprocess.run(['node', '-e', program.replace('BODY', body)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'completion-identity-ok')

    def test_custom_metadata_routes_track_before_ready_and_bind_association_proof(self):
        self.probe('''
const dsp=node(1,'studio_bus'),processor=node(2,'unrelated_processor',true,true),a=node(3,'alsa_output.a');
dsp.properties['node.link-group']='studio';processor.properties['node.link-group']='studio';
const authority=Routing.createAuthority(),nodes=[dsp,processor,a],links=[{source:processor,target:a}];
processor.ready=false;assert(Routing.sources(nodes,[dsp]).includes(processor));
assert.strictEqual(Routing.resolve(nodes,links,dsp,authority).status,'unresolved');
processor.ready=true;const route=Routing.resolve(nodes,links,dsp,authority);
assert.strictEqual(route.status,'resolved');assert.strictEqual(Routing.target(nodes,links,dsp,authority,route),a);
dsp.properties['node.link-group']='changed';processor.properties['node.link-group']='changed';
assert.strictEqual(Routing.target(nodes,links,dsp,authority,route),null);
''')

    def test_group_only_routes_are_supported_but_multiple_targets_stay_ambiguous(self):
        self.probe('''
const dsp=node(1,'custom_bus'),processor=node(2,'processor',true,true),a=node(3,'alsa_output.a'),b=node(4,'bluez_output.b');
dsp.properties['node.group']='custom';processor.properties['node.group']='custom';
const authority=Routing.createAuthority(),nodes=[dsp,processor,a,b],link={source:processor,target:a};
assert.strictEqual(Routing.resolve(nodes,[link],dsp,authority).target.id,a.id);
assert.strictEqual(Routing.resolve(nodes,[link,{source:processor,target:b}],dsp,authority).status,'ambiguous');
processor.properties['node.group']='different';assert.strictEqual(Routing.resolve(nodes,[link],dsp,authority).status,'unresolved');
''')

    def test_virtual_input_requires_native_generation_bridge_serial_and_default(self):
        self.probe('''
const input=node(1,'virtual_input.fixture',false,false);input.audio=null;
const authority=Routing.createAuthority(),nodes=[input],base={ready:true,current:null,inputs:[]};
const bridge={known:true,writable:true,snapshot:{key:'a'.repeat(64),default_source:input.name,
 sources:[{name:input.name,serial:'101',volume:.4,muted:true}]}};
let state=Untyped.merge(base,true,nodes,input,bridge,authority),row=state.current;
assert(Object.isFrozen(row)&&Object.isFrozen(state.inputs));assert(row.untyped&&row.controlAvailable);
assert.strictEqual(row.audio,undefined);assert.strictEqual(Untyped.target(true,nodes,input,bridge,authority,row,true),input);
bridge.writable=false;assert.strictEqual(Untyped.target(true,nodes,input,bridge,authority,row,true),null);bridge.writable=true;
bridge.snapshot.key='b'.repeat(64);assert.strictEqual(Untyped.target(true,nodes,input,bridge,authority,row,true),null);
bridge.snapshot.key='a'.repeat(64);bridge.snapshot.default_source='different';
assert.strictEqual(Untyped.target(true,nodes,input,bridge,authority,row,true),null);
bridge.snapshot.default_source=input.name;
const replacement={...input,properties:{...input.properties}};
assert.strictEqual(Untyped.target(true,[replacement],replacement,bridge,authority,row,true),null);
assert.strictEqual(Untyped.target(true,[input,{...input}],input,bridge,authority,row,true),null);
bridge.snapshot.sources[0].serial='999';assert.strictEqual(Untyped.merge(base,true,nodes,input,bridge,authority).current,null);
''')

    def test_unknown_or_typed_nodes_never_become_virtual_fallbacks(self):
        self.probe('''
const input=node(1,'virtual',false,false),base={ready:true,current:null,inputs:[]};
const authority=Routing.createAuthority(),bridge={known:false,writable:false,snapshot:null};
assert.strictEqual(Untyped.merge(base,true,[input],input,bridge,authority).current,null);
input.audio=null;assert.strictEqual(Untyped.merge(base,true,[input],input,bridge,authority).current,null);
assert.strictEqual(Untyped.target(true,[input],input,bridge,authority,{},true),null);
''')


if __name__ == '__main__': unittest.main()
