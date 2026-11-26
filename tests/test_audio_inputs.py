"""Microphone ownership probes use pure data and fake services, never host audio."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import audio_port_fixtures as fixtures
import check_clock_preview as preview


def js(path):
    return '\n'.join(line for line in path.read_text().splitlines()
                     if not line.startswith(('.pragma ', '.import ')))


@unittest.skipUnless(shutil.which('node'), 'Node required for pure input ownership probes')
class NativeInputTests(unittest.TestCase):
    def probe(self, body):
        directory = ROOT / 'config/shell/preview'
        sources = {'ACTIONS': js(directory / 'AudioActions.js'),
                   'ROUTING': js(directory / 'AudioRouting.js'),
                   'PRESENTATION': js(directory / 'AudioPresentation.js'),
                   'INPUT': js(directory / 'AudioInput.js'),
                   'MODEL': js(ROOT / 'vendor/omarchy/shell/plugins/panels/audio/Model.js')}
        program = '''const assert=require('assert'),vm=require('vm');
const Actions=vm.runInNewContext(ACTIONS+';({streamSerial})');
const Routing=vm.runInNewContext(ROUTING+';({createAuthority,currentNode,sameKey})',{Actions});
const Model=vm.runInNewContext(MODEL+';({nodeLabel,sourceGlyph})');
const Presentation=vm.runInNewContext(PRESENTATION+';({inputSnapshot})',{Actions,Model});
const Input=vm.runInNewContext(INPUT+';({eligible,snapshot,target})',{Routing,Presentation});
function node(id,name){return {id,name,ready:true,isSink:false,isStream:false,
  properties:{'object.serial':String(id+100)},audio:{volume:0.3,muted:true}};}
const mic=node(1,'mic'),other=node(2,'other'),nodes=[mic,other],owner=Routing.createAuthority();
const state=Input.snapshot(true,nodes,mic,owner),key=state.current;
BODY
console.log('input-ok');
'''
        for name, source in sources.items():
            program = program.replace(name, json.dumps(source), 1)
        result = subprocess.run(['node', '-e', program.replace('BODY', body)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'input-ok')

    def test_projection_is_detached_frozen_and_observation_only(self):
        self.probe('''
assert(Object.isFrozen(state)&&Object.isFrozen(state.inputs)&&Object.isFrozen(key)&&Object.isFrozen(key.control));
assert(state.defaultPresent&&key.controlAvailable);assert.strictEqual(key.id,mic.id);
assert.strictEqual(key.audio,undefined);assert.strictEqual(key.properties,undefined);
assert.strictEqual(key.control.audio,undefined);assert.strictEqual(key.control.properties,undefined);
assert.strictEqual(Input.target(true,nodes,mic,owner,key,true),mic);
assert.strictEqual(mic.audio.volume,0.3);assert.strictEqual(mic.audio.muted,true);
mic.audio.volume=0.8;assert.strictEqual(key.volume,0.3);
''')

    def test_gain_and_mute_require_same_actual_default_but_selection_can_choose_candidate(self):
        self.probe('''
assert.strictEqual(Input.target(true,nodes,other,owner,key,true),null);
assert.strictEqual(Input.target(true,nodes,other,owner,key,false),mic);
assert.strictEqual(Input.target(false,nodes,mic,owner,key,false),null);
assert.strictEqual(Input.target(false,nodes,mic,owner,key,true),null);
assert.strictEqual(mic.audio.volume,0.3);assert.strictEqual(other.audio.volume,0.3);
''')

    def test_serial_generation_provider_and_membership_churn_never_retarget(self):
        self.probe('''
const replaced={...mic,audio:{volume:0.9,muted:false}};
assert.strictEqual(Input.target(true,[replaced,other],replaced,owner,key,true),null);
assert.strictEqual(Input.target(true,nodes,mic,Routing.createAuthority(),key,true),null);
assert.strictEqual(Input.target(true,[other],mic,owner,key,true),null);
mic.properties['object.serial']='999';
assert.strictEqual(Input.target(true,nodes,mic,owner,key,true),null);
assert.strictEqual(Input.target(true,[mic,{...mic}],mic,owner,key,true),null);
''')

    def test_unsupported_unready_or_missing_defaults_never_become_writable_rows(self):
        self.probe('''
const virtual=node(3,'virtual');virtual.audio=null;
const unsupported=Input.snapshot(true,[...nodes,virtual],virtual,owner);
assert(unsupported.defaultPresent);assert.strictEqual(unsupported.current,null);
assert.strictEqual(unsupported.inputs.length,2);
const missing=Input.snapshot(true,nodes,null,owner);assert(!missing.defaultPresent);
assert.strictEqual(missing.current,null);
const stopped=Input.snapshot(false,nodes,mic,owner);assert(stopped.defaultPresent);
assert.strictEqual(stopped.inputs.length,0);assert.strictEqual(stopped.current,null);
const recreated={...mic};assert.strictEqual(Input.snapshot(true,[recreated],mic,owner).current,null);
''')

    def test_missing_serial_and_invalid_native_audio_disable_control_without_fabricating_gain(self):
        self.probe('''
for(const bad of ['', '0', 'not-a-serial']){
 mic.properties['object.serial']=bad;
 const unknown=Input.snapshot(true,nodes,mic,owner).current;
 assert(unknown&&!unknown.controlAvailable);assert.strictEqual(unknown.control,null);
 assert.strictEqual(Input.target(true,nodes,mic,owner,unknown,true),null);
}
mic.properties['object.serial']='101';
for(const value of [NaN,Infinity,'0.3']){
 mic.audio.volume=value;assert(!Input.snapshot(true,nodes,mic,owner).current.controlAvailable);
}
mic.audio.volume=0.3;mic.audio.muted='false';
assert(!Input.snapshot(true,nodes,mic,owner).current.controlAvailable);
''')

    def test_malformed_or_mismatched_visual_keys_are_not_authorities(self):
        self.probe('''
for(const bad of [null,{},false,{...key,control:null},{...key,controlAvailable:false},
 {...key,id:other.id},{...key,name:other.name},{...key,serial:'999'},
 {...key,control:{...key.control,generation:0}}])
 assert.strictEqual(Input.target(true,nodes,mic,owner,bad,true),null);
''')

    def test_forbidden_unbound_reads_and_ambiguous_rows_fail_closed(self):
        self.probe('''
mic.ready=false;Object.defineProperty(mic,'properties',{get(){throw Error('Unbound property read');}});
assert.strictEqual(Input.snapshot(true,nodes,mic,owner).current,null);
assert.strictEqual(Input.target(true,nodes,mic,owner,key,true),null);
const duplicate={...other};
const ambiguous=Input.snapshot(true,[other,duplicate,null],null,owner);
assert.strictEqual(ambiguous.current,null);assert(ambiguous.inputs.every(row=>!row.controlAvailable));
''')


class InputIntegrationContracts(unittest.TestCase):
    def test_actual_provider_has_no_legacy_projection_or_action_bypass(self):
        files, _ = preview.verified_sources(ROOT)
        provider = files['AudioOutputProvider.qml'].decode()
        self.assertIn('Input.snapshot(', provider)
        self.assertNotIn('Presentation.inputSnapshot(', provider)
        for witness in ('Input.target(Pipewire.ready,', 'sourceTarget(key, true)',
                        'sourceTarget(key, false)', 'sourceTarget(inputKey, true)',
                        'input ? [input] : []'):
            self.assertIn(witness, provider)
        master = provider.split('function toggleAllMuted(', 1)[1].split('\n  }', 1)[0]
        self.assertLess(master.index('sourceTarget(inputKey, true)'), master.index('Actions.toggleAllMuted'))
        for name in ('AudioInput.js', 'AudioOutputProvider.qml'):
            for forbidden in ('Process {', 'execDetached', 'wpctl', 'pactl', 'setTimeout'):
                self.assertNotIn(forbidden, files[name].decode())

    def test_original_slider_has_only_availability_seam_and_stale_row_resolver_is_guarded(self):
        files, meta = preview.verified_sources(ROOT)
        self.assertIn(b'enabled: root.inputWriteAvailable', files['AudioOutputView.qml'])
        self.assertIn(b'Routing.sameKey(inputs[j].control, key.control)', files['AudioPanelController.qml'])
        self.assertIn(b'Microphone controls unavailable', files['AudioPanelController.qml'])
        self.assertEqual(meta['upstream']['AudioOutputView.qml']['stage_transform'], 'audio-native-input-frontend-v9')

    def test_actual_provider_fixtures_reject_unexpected_warnings(self):
        for name in ('input-direct', 'input-churn', 'input-guards', 'input-uncertain'):
            source = fixtures.fixture(name)
            self.assertIn('actual provider exposes frozen microphone proof only', source)
            self.assertNotIn('Quickshell.Services.Pipewire', source)
            good = 'Configuration Loaded\n' + fixtures.MARKER + '::' + name + '\n'
            self.assertTrue(fixtures.classify(name, 0, good))
            self.assertFalse(fixtures.classify(name, 0, good+'WARN unexpected\n'))


if __name__ == '__main__':
    unittest.main()
