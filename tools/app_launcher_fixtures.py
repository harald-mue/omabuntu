"""Actual launcher UI with fake queued desktop-entry publication, no host apps."""
import re

CASES = ("cold", "filtered-cold", "warm", "closed-update", "removal", "native-cold", "negative")
MARKER = "OMABUNTU_APPS_FIXTURE_OK"
ENTRIES = '''pragma Singleton
import QtQml
QtObject {
  readonly property var applications: ({values:[]})
  function publish(rows) { applications.values=rows;applicationsChanged(); }
  function byId(id) { throw new Error("Application execution/lookup forbidden in fixture"); }
}
'''


def fixture_launcher(data, native=False):
    """Replace native window/shortcut ownership only in the isolated copy."""
    text = data.decode()
    def replace(old, new=""):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError("App launcher fixture witness differs")
        text = text.replace(old,new)
    replace("import QtQuick\n", 'import QtQuick\nimport QtQuick.Window\nimport "FixtureEntries" as FixtureEntries\n')
    replace("import Quickshell.Hyprland\n")
    replace("PanelWindow {\n", "Window {\n  width:1280\n  height:800\n")
    for line in ('  anchors { top: true; bottom: true; left: true; right: true }\n',
                 '  exclusionMode: ExclusionMode.Normal\n', '  exclusiveZone: 0\n',
                 '  WlrLayershell.namespace: "omabuntu-apps"\n',
                 '  WlrLayershell.layer: WlrLayer.Overlay\n',
                 '  WlrLayershell.keyboardFocus: shown ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None\n',
                 '    root.screen = root.focusedScreen()\n'):
        replace(line)
    start, end = "  GlobalShortcut {\n", "  Rectangle {\n    anchors.fill: parent\n"
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("Shortcut fixture boundary differs")
    text = text[:text.index(start)] + text[text.index(end):]
    return (text if native else text.replace("DesktopEntries", "FixtureEntries.DesktopEntries")).encode()


def fixture(name):
    if name not in CASES:
        raise ValueError("Unknown launcher fixture")
    return '''//@ pragma IgnoreSystemSettings
import QtQuick
import Quickshell
import "FixtureEntries" as F
ShellRoot {
  id:test
  property var launcher:null
  property var grid:null
  property string mode:"%s"
  property var rows:[{name:"Beta",id:"beta.desktop",command:["never-execute"],icon:""},
                     {name:"Alpha",id:"alpha.desktop",command:["never-execute"],icon:""}]
  function require(value,message){if(!value)throw new Error(message);}
  function findGrid(item){
    if(item.positionViewAtIndex && item.cellWidth)return item;
    for(var i=0;i<item.children.length;i++){var found=findGrid(item.children[i]);if(found)return found;}
    return null;
  }
  function fail(error){console.error("OMABUNTU_APPS_ASSERT",String(error));Qt.exit(42);}
  Timer {interval:1;running:true;onTriggered:{
    try {
      var factory=Qt.createComponent("AppLauncher.qml",Component.PreferSynchronous);
      require(factory.status===Component.Ready,factory.errorString());launcher=factory.createObject(null);factory.destroy();
      require(launcher!==null,"launcher construction");grid=findGrid(launcher.contentItem);require(grid!==null,"real grid loaded");
      if(mode==="warm"||mode==="removal")F.DesktopEntries.publish(rows);
      launcher.open();
      require(launcher.shown && grid.width>0 && grid.height>0,"first open has usable geometry");
      if(mode==="filtered-cold")launcher.filterText="be";
      if(mode!=="warm"&&mode!=="removal")require(grid.count===0,"initial cold list is empty");
      publish.start();
    }catch(error){test.fail(error);}
  }}
  Timer {id:publish;interval:50;onTriggered:{
    try {
      if(mode==="native-cold") {check.start();return;}
      if(mode==="closed-update")launcher.close();
      if(mode==="removal")F.DesktopEntries.publish([]);
      else F.DesktopEntries.publish(rows);
      if(mode==="closed-update") {require(!launcher.shown,"publication does not open hidden UI");launcher.open();}
      check.start();
    }catch(error){test.fail(error);}
  }}
  Timer {id:check;interval:150;onTriggered:{
    try {
      require(launcher.shown,"same opening remains shown");
      require(grid.count===(mode==="removal"?0:mode==="filtered-cold"?1:2),"first opening refreshes after publication");
      if(mode!=="removal") {
        var first=grid.itemAtIndex(0);
        require(first!==null && first.name===(mode==="filtered-cold"?"Beta":"Alpha"),"actual first delegate paints sorted/filtered app");
      } else launcher.launchSelected(); // Empty results must not attempt execution.
      if(mode==="filtered-cold")require(launcher.filterText==="be","late data preserves typed filter");
      if(mode==="negative")throw new Error("deliberate launcher assertion");
      launcher.close();launcher.destroy();console.log("%s::"+mode);Qt.callLater(function(){Qt.quit();});
    }catch(error){test.fail(error);}
  }}
}
''' % (name,MARKER)


def classify(name,code,text):
    if name not in CASES:
        return False
    diagnostics = re.findall(r"^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b.*",text,re.M)
    if name == "negative":
        return code==42 and len(diagnostics)==1 and "deliberate launcher assertion" in diagnostics[0] and MARKER not in text
    return code==0 and not diagnostics and text.count(MARKER+"::"+name)==1 and "Configuration Loaded" in text
