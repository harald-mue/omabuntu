"""Fixed original-section geometry probes with synthetic Hyprland only."""
import re

CASES = ("laptop", "ultrawide", "external", "narrow", "long-title", "center-sides", "negative")
MARKER = "OMABUNTU_BAR_FRAME_OK"
HYPRLAND = '''pragma Singleton
import QtQml
QtObject {
  property var focusedWorkspace: ({id:3})
  property var workspaces: ({values:[]})
  property var activeToplevel: ({title:"Fixture title"})
  readonly property bool usingLua: true
  function dispatch(command) { throw new Error("No startup dispatch allowed"); }
}
'''


def fixture(name):
    if name not in CASES:
        raise ValueError("Unknown frame fixture")
    width = {"laptop":1280,"ultrawide":3440,"external":1920,"narrow":320}.get(name,1280)
    return '''//@ pragma IgnoreSystemSettings
import QtQuick
import QtQuick.Window
import Quickshell
import "FixtureHyprland"
ShellRoot {
  id: test
  property var layout: null
  property string mode: "%s"
  Window {id:host;visible:true;width:%d;height:26}
  Component {id:left; LiveStatus {maximumWidth:test.layout?Math.max(0,test.layout.centerStart-16):0}}
  Component {id:center; Item {implicitWidth:150;implicitHeight:26}}
  Component {id:right; Item {implicitWidth:130;implicitHeight:26}}
  Component {id:begin; Item {implicitWidth:40;implicitHeight:26}}
  Component {id:end; Item {implicitWidth:30;implicitHeight:26}}
  function require(value,message) {if(!value)throw new Error(message);}
  function section(item,region) {
    if(item.region===region && item.active)return item;
    for(var i=0;i<item.children.length;i++){var found=section(item.children[i],region);if(found)return found;}
    return null;
  }
  Timer {interval:1;running:true;onTriggered:{
    try {
      if(mode==="long-title")Hyprland.activeToplevel=({title:"<b>"+"Long title ".repeat(100)+"</b>"});
      var factory=Qt.createComponent("BarFrame.qml",Component.PreferSynchronous);
      require(factory.status===Component.Ready,factory.errorString());
      layout=factory.createObject(host.contentItem,{width:host.width,height:26,leftContent:left,centerContent:center,rightContent:right,
        centerBeginContent:mode==="center-sides"?begin:null,centerEndContent:mode==="center-sides"?end:null});
      factory.destroy();require(layout!==null,"frame construction");check.start();
    }catch(error){console.error("OMABUNTU_FRAME_ASSERT",String(error));Qt.exit(42);}
  }}
  Timer {id:check;interval:300;onTriggered:{
    try {
      var base=Math.round((host.width-150)/2);
      require(layout.centerStart===base-(mode==="center-sides"?40:0),"original center/begin positioning");
      require(layout.centerEnd===base+150+(mode==="center-sides"?30:0),"original center/end positioning");
      var l=section(layout,"left"),r=section(layout,"right"),c=section(layout,"center");
      require(l&&r&&c,"all three sections loaded");
      var lp=l.mapToItem(layout,0,0),rp=r.mapToItem(layout,0,0),cp=c.mapToItem(layout,0,0);
      require(lp.x===8 && rp.x+r.width===host.width-8,"original eight-pixel edge insets");
      require(cp.x===base && c.width===150,"clock stays centered independently of title length");
      require(lp.x+l.width<=layout.centerStart-8,"left section does not overlap center");
      require(rp.x>=layout.centerEnd+8,"right section does not overlap center");
      require(l.height===26&&r.height===26&&c.height===26,"bar height unchanged");
      require(l.item.maximumWidth===Math.max(0,layout.centerStart-16),"title gets live section budget");
      if(mode==="negative")throw new Error("deliberate frame assertion");
      console.log("%s::"+mode);layout.destroy();host.visible=false;Qt.callLater(function(){Qt.quit();});
    }catch(error){console.error("OMABUNTU_FRAME_ASSERT",String(error));Qt.exit(42);}
  }}
}
''' % (name,width,MARKER)


def classify(name, code, text):
    if name not in CASES:
        return False
    errors = re.findall(r"^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b.*", text, re.M)
    if name == "negative":
        return code == 42 and len(errors) == 1 and "deliberate frame assertion" in errors[0] and MARKER not in text
    return code == 0 and not errors and text.count(MARKER + "::" + name) == 1 and "Configuration Loaded" in text
