"""Actual QML request/registry functions with fake processes, never a desktop."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_widget_preferences import qml_function

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')


def functions(path, names, handler=False):
    text = (ROOT / path).read_text()
    if handler:
        text = text.replace('onExited: function(code)', 'function finished(code)')
    return '\n'.join(qml_function(text, name) for name in names + (['finished'] if handler else []))


@unittest.skipUnless(NODE, 'Node required for source JS regression checks')
class WidgetQueueNavigationTests(unittest.TestCase):
    def run_js(self, script):
        result = subprocess.run([NODE, '-e', "const assert=require('assert');\n" + script],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def adapter(self, path, names, setup, checks):
        code = functions(path, names, handler=True)
        self.run_js('''
let calls=[],scheduled=[],warnings=[];
const Qt={callLater:fn=>scheduled.push(fn)};
const output={text:''};
const backend={running:false,exec:args=>{calls.push(args);backend.running=true;}};
const console={warn:(...args)=>warnings.push(args)};
''' + setup + '''
with(root) {
''' + code + '\nObject.assign(root,{' + ','.join(names + ['finished']) + '});\n}\n' + checks)

    def test_dock_edits_during_load_coalesce_and_failed_write_is_visible(self):
        self.adapter('config/shell/preview/DockState.qml',
                     ['project', 'request', 'pump', 'applyPreferences', 'setPosition', 'setAutohide', 'setPinned'], '''
const root={confirmed:{position:'bottom',autohide:false,pinned:[]},queue:[],inFlight:[],
 finishing:false,loaded:false,errorText:'',helper:'/fixture/dock_state.py',changed:()=>{}};
for (const key of ['position','autohide','pinned']) Object.defineProperty(root,key,{get:()=>root.project()[key]});
''', '''
root.request('get',[]);
root.setPosition('left');root.setPosition('right');
root.setAutohide(true);root.setPinned(['one']);root.setPinned(['two','one']);
assert.equal(calls.length,1);
assert.equal(root.queue.length,3);
assert.equal(root.position,'right');assert.deepEqual(root.pinned,['two','one']);
output.text=JSON.stringify({position:'bottom',autohide:false,pinned:[]});
backend.running=false;root.finished(0);
assert.equal(root.position,'right');assert.equal(root.autohide,true);
scheduled.shift()();
assert.deepEqual(calls[1],['python3','/fixture/dock_state.py','set-position','right']);
output.text=JSON.stringify({error:'fixture'});backend.running=false;root.finished(1);
assert.ok(root.errorText);assert.equal(warnings.length,1);
assert.equal(root.position,'bottom'); // Failed optimistic edit is not confirmed.
assert.deepEqual(root.pinned,['two','one']); // Later independent edit survives.
scheduled.shift()();
assert.equal(calls[2][2],'set-autohide');
''')

    def test_display_mutations_survive_status_and_precede_next_poll(self):
        self.adapter('config/shell/preview/DisplayPanelController.qml',
                     ['request', 'pump', 'applyState', 'setBrightness', 'setScale'], '''
const root={profiles:null,helper:'/fixture/display_backend.py',queue:[],inFlight:[],lastState:null,finishing:false,
 displays:[],focusedMonitor:'fixture-a',monitorScale:'1',brightnessAvailable:true,brightnessPercent:10,errorText:''};
''', '''
root.request('status',[]);
root.setScale('1.25');root.request('status',[]);
root.setBrightness(55);root.setScale('1.5');root.request('status',[]);
assert.equal(calls.length,1);
assert.deepEqual(root.queue,[['brightness','55'],['scale','fixture-a','1.5'],['status']]);
output.text=JSON.stringify({displays:[{name:'fixture-a',focused:true,scale:1}],backlight:{percent:10}});
backend.running=false;root.finished(0);
assert.equal(root.brightnessPercent,55);assert.equal(root.monitorScale,'1.5');
scheduled.shift()();assert.equal(calls[1][2],'brightness');
output.text=JSON.stringify({error:'fixture failure'});backend.running=false;root.finished(1);
assert.equal(root.errorText,'fixture failure');assert.equal(root.brightnessPercent,10);
assert.equal(root.monitorScale,'1.5');
scheduled.shift()();assert.equal(calls[2][2],'scale');
assert.equal(root.queue[0][0],'status');
''')

    def test_display_scale_requests_keep_their_original_output(self):
        code = functions('config/shell/preview/DisplayPanelController.qml', ['request', 'pump', 'setScale'])
        self.run_js('''
let profiles=null,helper='/fixture/display_backend.py',queue=[],inFlight=[],finishing=false,errorText='';
let focusedMonitor='fixture-a',monitorScale='1',backend={running:true,exec:()=>{}};
''' + code + '''
setScale('1.25');focusedMonitor='fixture-b';setScale('2');
assert.deepEqual(queue,[['scale','fixture-a','1.25'],['scale','fixture-b','2']]);
''')

    def test_original_registry_switches_visible_panels_in_layout_order_per_output(self):
        code = functions('config/shell/preview/BarFrame.qml',
                         ['entryId', 'layoutEntries', 'panelNavigationSlots', 'switchPanelFrom', 'slotWindow', 'sameWindow'])
        model = str(ROOT / 'vendor/omarchy/shell/plugins/bar/BarModel.js')
        self.run_js("const BarModel=require(" + repr(model) + ");\n" + '''
function makeRegistry() {
 let moduleSlots=[],layoutConfig={left:[],centerBegin:[],center:['clock'],centerEnd:['elsewhen','weather'],right:['bluetooth','network','audio']};
''' + code + '''
 return {moduleSlots,layoutConfig,switchPanelFrom};
}
let opened=[];
function item(name,visible=true) {return {visible,enabled:true,width:26,height:26,opened:false,open:()=>opened.push(name),close:()=>{}};}
const a=makeRegistry(),b=makeRegistry();
const clock=item('clock'),weather=item('weather',false),elsewhen=item('elsewhen');
const bt=item('bluetooth'),net=item('network'),audio=item('audio');
function slot(id,region,activeItem){return {moduleName:id,region,activeItem,visible:true,width:26,height:26,window:null};}
for(const [key,region,value] of [['clock','center',clock],['elsewhen','centerEnd',elsewhen],
 ['weather','centerEnd',weather],['bluetooth','right',bt],['network','right',net],['audio','right',audio]])
 a.moduleSlots.push(slot(key,region,value));
b.moduleSlots.push(slot('network','right',item('other-output')));
assert.equal(a.switchPanelFrom(clock,1),true);assert.deepEqual(opened,['elsewhen']);
assert.equal(a.switchPanelFrom(elsewhen,1),true);assert.equal(opened.at(-1),'clock');
assert.equal(a.switchPanelFrom(bt,-1),true);assert.equal(opened.at(-1),'audio');
assert.equal(b.switchPanelFrom(net,1),false);
// Reordering persisted keys changes navigation, without rebuilding the registry.
a.layoutConfig.right=['bluetooth','audio','network'];
assert.equal(a.switchPanelFrom(bt,1),true);assert.equal(opened.at(-1),'audio');
audio.enabled=false;
assert.equal(a.switchPanelFrom(bt,1),true);assert.equal(opened.at(-1),'network');
audio.enabled=true;
a.moduleSlots.find(s=>s.activeItem===audio).width=0;
assert.equal(a.switchPanelFrom(bt,1),true);assert.equal(opened.at(-1),'network');
a.moduleSlots.find(s=>s.activeItem===net).visible=false;
assert.equal(a.switchPanelFrom(bt,1),false);
assert.equal(a.switchPanelFrom(item('unknown'),1),false);
''')

    def test_display_cursor_uses_original_section_navigation_without_text_size(self):
        code = functions('config/shell/preview/DisplayPanelController.qml',
                         ['sectionCount', 'sectionIsSingleRow', 'sectionFirstIndex', 'moveCursor', 'moveCursorH'])
        self.run_js('''
let visibleSections=['brightness','scale','monitors'],focusSection='brightness',selectedIndex=-1;
let scaleValues=['1','1.25','2'],displays=[{name:'a'},{name:'b'}];
''' + code + '''
moveCursor(1);assert.equal(focusSection,'scale');assert.equal(selectedIndex,0);
moveCursorH(1);assert.equal(selectedIndex,1);
moveCursor(1);assert.equal(focusSection,'monitors');assert.equal(selectedIndex,0);
moveCursor(1);assert.equal(selectedIndex,1);
moveCursor(-1);assert.equal(selectedIndex,0);
moveCursor(-1);assert.equal(focusSection,'scale');assert.equal(selectedIndex,0);
moveCursor(-1);assert.equal(focusSection,'brightness');assert.equal(selectedIndex,-1);
''')


if __name__ == '__main__':
    unittest.main()
