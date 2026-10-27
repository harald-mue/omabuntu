"""Fixed tooltip lifecycle probes; no real pointer or host session."""
import re

CASES = ("empty", "delayed", "stale-hide", "leave", "deleted-target", "geometry", "negative")
MARKER = "OMABUNTU_TOOLTIP_OK"


def bubble_fixture(window):
    """Execute the original bubble without an offscreen native popup backend."""
    text = window.decode().rstrip() + "\n"
    start = "  BorderSurface {\n    id: tooltipBubble\n"
    if text.count(start) != 1 or not text.endswith("}\n"):
        raise ValueError("Tooltip bubble witness differs")
    block = text[text.index(start):-2]
    block = block.replace("    id: tooltipBubble\n", "    id: tooltipBubble\n    required property QtObject host\n", 1)
    return ('import QtQuick\nimport qs.Ui\nimport qs.Commons\nimport qs.Commons as Commons\n' + block).encode()


def fixture(name):
    if name not in CASES:
        raise ValueError("Unknown tooltip fixture")
    return '''//@ pragma IgnoreSystemSettings
import QtQuick
import QtQuick.Window
import Quickshell
ShellRoot {
  id: test
  property var host: null
  property var first: null
  property var second: null
  property var bubble: null
  property string mode: "%s"
  Window { id: frame; visible: true; width: 320; height: 26 }
  function require(value,message) { if(!value)throw new Error(message); }
  function fail(error) { console.error("OMABUNTU_TOOLTIP_ASSERT",String(error));Qt.exit(42); }
  Timer { interval: 1; running: true; onTriggered: {
    try {
      var component=Qt.createComponent("BarTooltipHost.qml",Component.PreferSynchronous);
      require(component.status===Component.Ready,component.errorString());host=component.createObject(frame.contentItem);component.destroy();
      first=Qt.createQmlObject('import QtQuick; Item { width:26; height:26; property bool tooltipHovered:true }',frame.contentItem);
      second=Qt.createQmlObject('import QtQuick; Item { x:290; width:26; height:26; property bool tooltipHovered:true }',frame.contentItem);
      require(!host.tooltipShown && host.tooltipTarget===null,"no startup tooltip");
      if(mode==="empty") { host.showTooltip(first,""); require(host.pendingTooltipTarget===null,"empty text rejected"); }
      else if(mode==="geometry") {
        // The original bubble is measured independently of the 26px bar.
        // Native popup creation/anchoring cannot be tested by Qt offscreen.
        host.tooltipTarget=second;host.tooltipText="<b>Network status</b>";
        component=Qt.createComponent("TooltipBubbleFixture.qml",Component.PreferSynchronous);
        require(component.status===Component.Ready,component.errorString());
        bubble=component.createObject(null,{host:host});component.destroy();
        require(bubble!==null,"original bubble constructed");
        // Let text layout settle before measuring its implicit geometry.
      } else {
        host.showTooltip(first,"first");
        require(!host.tooltipShown,"not forced visible on enter");
        if(mode==="stale-hide") {host.showTooltip(second,"second");host.hideTooltip(first);}
        if(mode==="leave") {first.tooltipHovered=false;host.hideTooltip(first);}
        if(mode==="deleted-target") {first.destroy();}
      }
      early.start();late.start();
    } catch(error) {test.fail(error);}
  } }
  Timer { id:early; interval:150; onTriggered: {
    try {require(!host.tooltipShown,"400ms delay respected");}
    catch(error){test.fail(error);}
  } }
  Timer { id:late; interval:550; onTriggered: {
    try {
      if(mode==="geometry") require(bubble.implicitHeight>=24 && bubble.implicitWidth>26,
        "nonempty independent bubble dimensions "+bubble.implicitWidth+"x"+bubble.implicitHeight);
      if(mode==="delayed"||mode==="stale-hide"||mode==="negative") {
        require(host.tooltipShown,"delayed admission");
        require(host.tooltipTarget===(mode==="stale-hide"?second:first),"latest owner wins");
        require(host.tooltipText===(mode==="stale-hide"?"second":"first"),"latest text wins");
        host.hideTooltip(host.tooltipTarget);require(!host.tooltipShown && host.tooltipTarget===null,"exit closes tooltip");
      } else require(!host.tooltipShown,"empty/left/deleted targets never shown");
      if(mode==="negative")throw new Error("deliberate tooltip assertion");
      if(bubble)bubble.destroy();host.destroy();frame.visible=false;
      console.log("%s::"+mode);Qt.callLater(function(){Qt.quit();});
    } catch(error) {test.fail(error);}
  } }
}
''' % (name, MARKER)


def classify(name, code, text):
    if name not in CASES:
        return False
    errors = re.findall(r"^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b.*", text, re.M)
    if name == "negative":
        return code == 42 and len(errors) == 1 and "deliberate tooltip assertion" in errors[0] and MARKER not in text
    return code == 0 and not errors and text.count(MARKER + "::" + name) == 1 and "Configuration Loaded" in text
