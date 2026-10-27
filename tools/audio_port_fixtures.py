"""Fixed audio-output probes with fake nodes, never native PipeWire."""
import re

CASES = ("no-output", "glyphs", "controls", "selection", "bounds", "churn", "navigation", "negative")

# offscreen has no PanelWindow backend. Replace only surface ownership in the
# fixture copy; the original visual content and controls still execute.
KEYBOARD_SURFACE = '''import QtQuick
Item {
  id: root
  property Item anchorItem: null
  property QtObject bar: null
  property var owner: null
  property bool open: false
  property bool centerOnBar: false
  property Item focusTarget: null
  property Component content: null
  property bool contentRequested: false
  property int contentWidth: 380
  property int contentHeight: 200
  readonly property Item loadedContent: loader.item
  readonly property real loadedContentHeight: loader.item ? loader.item.implicitHeight : 0
  width: contentWidth
  height: contentHeight
  visible: open
  function fittedContentWidth(value) { return Math.min(800,value); }
  function fittedContentHeight(value,cap) { return Math.min(cap,value+28); }
  function ensureContent() { contentRequested=true;return loader.item; }
  function close() { if(owner)owner.close(); }
  onOpenChanged: {
    if(open) {contentRequested=true;bar.requestPopout(owner);}
    else if(bar)bar.releasePopout(owner);
  }
  Loader {id:loader;anchors.fill:parent;anchors.margins:14;active:root.open||root.contentRequested;sourceComponent:root.content}
}
'''
MARKER = "OMABUNTU_AUDIO_FIXTURE_OK"


def fixture(name):
    if name not in CASES:
        raise ValueError("Unknown audio fixture")
    return '''//@ pragma IgnoreSystemSettings
import QtQuick
import Quickshell
import "AudioActions.js" as Actions
import "AudioPresentation.js" as Presentation
import "Port/AudioModel.js" as Model
ShellRoot {
  id: test
  property var nodes: []
  property var owner: null
  property var view: null
  property int writes: 0
  property var current: null
  function require(value, message) { if (!value) throw new Error(message); }
  QtObject {
    id: backend
    property var state: Presentation.snapshot(false,[],null)
    function sync() { state = Presentation.snapshot(true,test.nodes,test.current); }
    function setVolume(key,value) { var ok=Actions.setVolume(test.nodes,key,value); if(ok) test.writes++; sync(); return ok; }
    function toggleMute(key) { var ok=Actions.toggleMute(test.nodes,key); if(ok) test.writes++; sync(); return ok; }
    function chooseOutput(key) { var node=Actions.resolve(test.nodes,key); if(!node)return false; test.current=node;test.writes++;sync();return true; }
  }
  Timer { interval: 200; running: true; onTriggered: {
    try {
      var mode="%s";
      var a={id:1,name:"fixture-a",description:"Built-in Audio Analog Stereo Output",ready:true,isSink:true,isStream:false,audio:{volume:0.42,muted:false}};
      var b={id:2,name:"fixture-b",description:"HDMI Display",ready:true,isSink:true,isStream:false,audio:{volume:0.6,muted:false}};
      test.nodes=mode === "no-output" ? [] : [a,b];test.current=mode === "no-output" ? null : a;backend.sync();
      var factory=Qt.createComponent("PortTrayHost.qml",Component.PreferSynchronous);
      require(factory.status===Component.Ready,factory.errorString());owner=factory.createObject(null);factory.destroy();
      factory=Qt.createComponent("AudioOutputView.qml",Component.PreferSynchronous);
      require(factory.status===Component.Ready,factory.errorString());
      view=factory.createObject(null,{bar:owner.ownerApi,backend:backend});factory.destroy();require(view!==null,"view construction");
      require(writes===0 && !view.opened,"no startup mutation or popup");
      require(view.panelWindow.loadedContent===null,"original lazy content stays unloaded");
      require(view.panelWindow.ensureContent()!==null,"original visual content loads");
      require(Object.isFrozen(backend.state) && Object.isFrozen(backend.state.outputs),"frozen snapshot");
      if(mode==="no-output") {
        view.toggleMute();view.wheel(120);require(writes===0,"no-output controls no-op");
      }
      if(mode==="glyphs") {
        require(Model.nodeLabel(a)==="Analog Stereo" && Model.sinkGlyph(b)==="󰍹","original labels and device glyphs");
        require(Presentation.icon({headphones:false,muted:false,volume:0.9})==="","high glyph");
        require(Presentation.icon({headphones:false,muted:true,volume:0.9})==="","muted glyph");
        require(Presentation.icon({headphones:false,muted:false,volume:0.1})==="","low glyph");
      }
      if(mode==="controls") {
        view.wheel(60);require(writes===0,"partial wheel delta");view.wheel(60);
        require(Math.abs(a.audio.volume-0.47)<0.0001 && writes===1,"five percent wheel");
        view.toggleMute();require(a.audio.muted && writes===2,"output mute");
        view.setVolume(view.current,0.2);require(a.audio.muted && a.audio.volume===0.2,"volume does not silently unmute");
      }
      if(mode==="selection") {
        require(backend.chooseOutput(backend.state.outputs[1]),"valid output request");
        require(backend.state.current.id===2 && test.writes===1,"selected output acknowledged");
      }
      if(mode==="bounds") {
        var key=backend.state.outputs[0];
        for(var v of [NaN,Infinity,"0.5",true,null]) require(!Actions.setVolume(nodes,key,v),"deny invalid volume");
        require(Actions.setVolume(nodes,key,7) && a.audio.volume===1,"upper bound");
        require(Actions.setVolume(nodes,key,-7) && a.audio.volume===0,"lower bound");
      }
      if(mode==="churn") {
        var stale=backend.state.outputs[0];
        a.name="reused-id";require(!Actions.toggleMute(nodes,stale),"ID reuse guard");
        test.nodes=[];require(!Actions.setVolume(nodes,stale,0.9),"removed device guard");
        require(stale.name==="fixture-a" && stale.audio===undefined,"no retained native wrapper");
        a.name="fixture-a";a.isStream=true;require(!Actions.resolve([a],stale),"no playback-stream mutation");
        a.isStream=false;a.isSink=false;require(!Actions.resolve([a],stale),"no microphone mutation");
        a.isSink=true;a.ready=false;require(!Actions.resolve([a],stale),"no unready-device mutation");
      }
      if(mode==="navigation") {
        view.opened=true;
        require(view.displayAudioSinks.length===2 && writes===0,"opening does not mutate audio");
        var catcher=view.panelWindow.loadedContent;
        catcher.moveRequested(0,1);require(view.cursorActive && view.selectedIndex===-1,"first key reveals cursor");
        catcher.moveRequested(0,1);require(view.selectedIndex===0,"next key selects first device");
        catcher.moveRequested(1,0);require(writes===0,"device row does not adjust global volume");
        catcher.moveRequested(0,-1);require(view.selectedIndex===-1,"back to slider");
        catcher.moveRequested(1,0);require(writes===1,"slider keyboard action");
        catcher.moveRequested(0,-1);require(view.headerHasCursor,"header cursor");
        catcher.activateRequested();require(writes===2 && a.audio.muted,"header output mute only");
        catcher.closeRequested();require(!view.opened && view.displayAudioSinks.length===0,"escape clears delegates");
      }
      if(mode==="negative") throw new Error("deliberate audio assertion");
      console.log("%s::"+mode);view.destroy();owner.destroy();Qt.callLater(function(){Qt.quit();});
    } catch(error) { console.error("OMABUNTU_AUDIO_ASSERT",String(error));Qt.callLater(function(){Qt.exit(42);}); }
  } }
}
''' % (name, MARKER)


def classify(name, code, text):
    if name not in CASES:
        return False
    errors = re.findall(r"^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b.*", text, re.M)
    if name == "negative":
        return code == 42 and len(errors) == 1 and "deliberate audio assertion" in errors[0] and MARKER not in text
    return code == 0 and not errors and text.count(MARKER + "::" + name) == 1 and "Configuration Loaded" in text
