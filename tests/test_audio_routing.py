"""Identity-bound native endpoint routing; no PipeWire server or host commands."""
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


@unittest.skipUnless(shutil.which('node'), 'Node required for native graph boundary tests')
class AudioRoutingTests(unittest.TestCase):
    def probe(self, body):
        paths = ROOT / 'config/shell/preview'
        sources = {
            'ACTIONS': js(paths / 'AudioActions.js'),
            'ROUTING': js(paths / 'AudioRouting.js'),
            'MODEL': js(ROOT / 'vendor/omarchy/shell/plugins/panels/audio/Model.js'),
            'PRESENTATION': js(paths / 'AudioPresentation.js'),
        }
        program = '''const assert=require('assert'),vm=require('vm');
const Actions=vm.runInNewContext(ACTIONS+';({streamSerial})');
const Routing=vm.runInNewContext(ROUTING+';({createAuthority,sources,sourceRank,resolve,target})',{Actions});
const Model=vm.runInNewContext(MODEL+';({nodeLabel,sinkGlyph,isHeadphones})');
const Presentation=vm.runInNewContext(PRESENTATION+';({snapshot,routedSnapshot})',{Actions,Model});
function node(id,name,isSink=true,isStream=false){return {id,name,isSink,isStream,ready:true,
 properties:{'object.serial':String(100+id)},audio:{volume:0.42,muted:false}}}
const a=node(1,'alsa_output.a'),b=node(2,'bluez_output.b'),dsp=node(3,'effect_input.dsp');
const output=node(4,'effect_output.dsp',true,true),link={source:output,target:a};
const nodes=[a,b,dsp,output],authority=Routing.createAuthority();
BODY
console.log('routing-ok');
'''
        for key, text in sources.items():
            program = program.replace(key, json.dumps(text), 1)
        program = program.replace('BODY', body)
        result = subprocess.run(['node', '-e', program], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'routing-ok')

    def test_direct_and_dsp_routes_are_frozen_data_and_never_mutate(self):
        self.probe('''
const direct=Routing.resolve(nodes,[],a,authority);assert.strictEqual(direct.status,'direct');
assert.strictEqual(Routing.target(nodes,[],a,authority,direct),a);
const control=Routing.resolve(nodes,[link],dsp,authority);assert.strictEqual(control.status,'resolved');
assert(Object.isFrozen(control)&&Object.isFrozen(control.selected)&&Object.isFrozen(control.target));
assert.strictEqual(control.selected.id,dsp.id);assert.strictEqual(control.target.id,a.id);
assert.strictEqual(control.target.audio,undefined);assert.strictEqual(control.target.properties,undefined);
assert.strictEqual(Routing.target(nodes,[link],dsp,authority,control),a);
const state=Presentation.routedSnapshot(true,nodes,dsp,control);
assert(Object.isFrozen(state)&&Object.isFrozen(state.current)&&Object.isFrozen(state.outputs));
assert.strictEqual(state.current.id,dsp.id);assert.strictEqual(state.current.volume,a.audio.volume);
assert.strictEqual(state.current.controlAvailable,true);
assert.strictEqual(a.audio.volume,0.42);assert.strictEqual(dsp.audio.volume,0.42);
assert.strictEqual(Routing.resolve(nodes,[],null,authority).status,'absent');
''')

    def test_original_source_name_priority_and_easyeffects_port_mapping(self):
        self.probe('''
assert.strictEqual(Routing.sourceRank(dsp.name,'effect_output.dsp'),2);
assert.strictEqual(Routing.sourceRank(dsp.name,'effect_input.dsp.fallback'),1);
assert.strictEqual(Routing.sourceRank(dsp.name,'unrelated'),0);
const fallback=node(5,'effect_input.dsp.fallback',true,true);nodes.push(fallback);
assert.strictEqual(Routing.resolve(nodes,[{source:fallback,target:b},link],dsp,authority).target.id,a.id);
const ee=node(6,'easyeffects_sink'),eeOut=node(7,'ee_output',false,false);eeOut.audio=null;
nodes.push(ee,eeOut);
assert.strictEqual(Routing.resolve(nodes,[{source:eeOut,target:b}],ee,authority).target.id,b.id);
const internal=node(12,'ee_internal');nodes.push(internal);
assert.strictEqual(Routing.resolve(nodes,[{source:eeOut,target:internal}],ee,authority).status,'unresolved');
assert.strictEqual(Routing.resolve(nodes,[{source:eeOut,target:internal},{source:eeOut,target:b}],ee,authority).target.id,b.id);
const tuning=node(8,'omarchy_speaker_tuning'),tuningOut=node(9,'omarchy_speaker_tuning.output',true,true);
nodes.push(tuning,tuningOut);
assert.strictEqual(Routing.resolve(nodes,[{source:tuningOut,target:a}],tuning,authority).target.id,a.id);
const custom=node(10,'custom'),customOut=node(11,'custom.output',true,true);
custom.properties['node.virtual']='true';nodes.push(custom,customOut);
assert.strictEqual(Routing.resolve(nodes,[{source:customOut,target:a}],custom,authority).target.id,a.id);
const tracked=Routing.sources(nodes,[a,b,dsp,ee,tuning,custom]);
assert(tracked.includes(output)&&tracked.includes(eeOut)&&tracked.includes(customOut));
''')

    def test_missing_ambiguous_cyclic_and_deep_routes_never_fall_back(self):
        self.probe('''
assert.strictEqual(Routing.resolve(nodes,[],dsp,authority).status,'unresolved');
const ambiguous=Routing.resolve(nodes,[link,{source:output,target:b}],dsp,authority);
assert.strictEqual(ambiguous.status,'ambiguous');assert.strictEqual(ambiguous.target,null);
assert.strictEqual(Routing.resolve(nodes,[{source:output,target:dsp}],dsp,authority).status,'cycle');
let chain=[],all=[],previous=null,first=null;
for(let i=0;i<10;i++){
 const sink=node(20+i*2,'effect_input.chain'+i),stream=node(21+i*2,'effect_output.chain'+i,true,true);
 all.push(sink,stream);if(!first)first=sink;if(previous)chain.push({source:previous,target:sink});previous=stream;
}
all.push(a);chain.push({source:previous,target:a});
assert.strictEqual(Routing.resolve(all,chain,first,authority).status,'limit');
const unknown=Presentation.routedSnapshot(true,nodes,dsp,ambiguous);
assert.strictEqual(unknown.current.controlAvailable,false);assert.strictEqual(unknown.current.volume,0);
assert.strictEqual(Routing.target(nodes,[],dsp,authority,unknown.current.control),null);
''')

    def test_chain_resolution_duplicate_channels_and_link_order_are_deterministic(self):
        self.probe('''
const second=node(5,'effect_input.second'),secondOut=node(6,'effect_output.second',true,true);
nodes.push(second,secondOut);
const edges=[{source:output,target:second},{source:secondOut,target:b}];
const proof=Routing.resolve(nodes,edges,dsp,authority);
assert.strictEqual(proof.target.id,b.id);
assert.strictEqual(Routing.resolve(nodes,edges.slice().reverse(),dsp,authority).proof,proof.proof);
assert.strictEqual(Routing.resolve(nodes,edges.concat(edges),dsp,authority).proof,proof.proof);
assert.strictEqual(Routing.target(nodes,edges,dsp,authority,proof),b);
''')

    def test_reroute_default_churn_serial_reuse_and_owner_scope_reject_capture(self):
        self.probe('''
const proof=Routing.resolve(nodes,[link],dsp,authority);
assert.strictEqual(Routing.target(nodes,[{source:output,target:b}],dsp,authority,proof),null);
assert.strictEqual(Routing.target(nodes,[link],a,authority,proof),null);
const replacement={...dsp,audio:{volume:0.9,muted:false}};
assert.strictEqual(Routing.target([a,b,replacement,output],[link],replacement,authority,proof),null);
assert.strictEqual(Routing.target(nodes,[link],dsp,Routing.createAuthority(),proof),null);
output.properties['object.serial']='999';assert.strictEqual(Routing.target(nodes,[link],dsp,authority,proof),null);
for(const bad of [null,undefined,false,{},[],{...proof,proof:''},{...proof,target:{...proof.target,generation:0}}])
 assert.strictEqual(Routing.target(nodes,[link],dsp,authority,bad),null);
''')

    def test_unready_nodes_stale_endpoints_and_unbound_state_are_not_dereferenced(self):
        self.probe('''
Object.defineProperty(link,'state',{get(){throw Error('unbound link state')}});
assert.strictEqual(Routing.resolve(nodes,[link],dsp,authority).target.id,a.id);
output.ready=false;Object.defineProperty(output,'properties',{get(){throw Error('unbound node properties')}});
assert.strictEqual(Routing.resolve(nodes,[link],dsp,authority).status,'unready');
assert(Routing.sources(nodes,[dsp]).includes(output));
assert.strictEqual(Routing.resolve([a,b,dsp],[link],dsp,authority).status,'unready');
const missing=node(15,'effect_output.dsp',true,true);missing.properties={};nodes.push(missing);
assert.strictEqual(Routing.resolve(nodes,[{source:missing,target:a}],dsp,authority).status,'unready');
const duplicate={...a};nodes.push(duplicate);
assert.strictEqual(Routing.resolve(nodes,[],a,authority).status,'unready');
''')


class AudioRoutingIntegrationContracts(unittest.TestCase):
    def test_sealed_native_graph_adapter_and_actual_provider_boundary(self):
        files, _ = preview.verified_sources(ROOT)
        routing = files['AudioRouting.js'].decode()
        provider = files['AudioOutputProvider.qml'].decode()
        for forbidden in ('Process {', 'execDetached', 'pactl', 'wpctl', '.state ===', 'setDefault'):
            self.assertNotIn(forbidden, routing)
        for witness in ('PwObjectTracker { objects: root.routeSources }', 'Routing.target(',
                        'Presentation.routedSnapshot(', 'volumeTarget(outputKey)',
                        'target ? [target] : []', 'Actions.masterTarget(candidates, key, false)'):
            self.assertIn(witness, provider)

    def test_fixed_actual_provider_cases_reject_warnings(self):
        for name in ('route-direct', 'route-dsp', 'route-churn', 'route-unknown'):
            text = fixtures.fixture(name)
            self.assertIn('actual provider and original routed surface construct', text)
            self.assertNotIn('Quickshell.Services.Pipewire', text)
            good = 'Configuration Loaded\n' + fixtures.MARKER + '::' + name + '\n'
            self.assertTrue(fixtures.classify(name, 0, good))
            self.assertFalse(fixtures.classify(name, 0, good + 'WARN unexpected\n'))


if __name__ == '__main__':
    unittest.main()
