"""Original section geometry, keyed ownership and output-local navigation probes."""
import re
import indicator_feedback_fixtures

CASES = ('laptop', 'ultrawide', 'external', 'narrow', 'long-title', 'center-sides',
         'move', 'hide', 'navigation', 'outputs', 'empty', 'missing-component', 'trial-compile', 'guarded-edit', 'appearance-queue', 'drag-click', 'drag-move', 'drag-empty', 'drag-remove',
         'drag-cancel', 'drag-drift', 'drag-rejected', 'drag-output',
         'fullscreen-local', 'fullscreen-state', 'fullscreen-drag', 'fullscreen-refresh',
         'peek-owner', 'peek-edge', 'peek-delay',
         'indicators-reveal', 'indicators-order', 'indicators-missing',
         'native-indicators', 'indicator-owner', 'indicator-rpc') + indicator_feedback_fixtures.CASES + ('negative',)
MARKER = 'OMABUNTU_BAR_FRAME_OK'
INDICATOR_HELPER = '''import json,sys
from pathlib import Path
request=json.load(sys.stdin)
assert '--allow-existing-owner-queries' in sys.argv
assert '--allow-session-bus-connection-risk' in sys.argv
path=Path.home()/'indicator-fixture.json'
state=json.loads(path.read_text()) if path.exists() else {'dnd':False,'nightlight':True}
if sys.argv[1]=='inspect':
    result={'schema':1,'scope':request['scope'],'blocked':False,'states':{kind:{'known':True,'active':value,'key':('a' if kind=='dnd' else 'b')*64} for kind,value in state.items()}}
else:
    assert sys.argv[1]=='set' and '--apply-user-indicator' in sys.argv
    assert request['kind'] in state and type(request['desired']) is bool
    assert request['expected']==('a' if request['kind']=='dnd' else 'b')*64
    state[request['kind']]=request['desired']
    path.write_text(json.dumps(state))
    result={'status':'confirmed'}
print(json.dumps({'ok':True,**result}))
'''
HYPRLAND = '''pragma Singleton
import QtQml
QtObject {
  property var focusedWorkspace: ({id:3})
  property var workspaces: ({values:[]})
  signal rawEvent(var event)
  property var monitorMap: ({})
  property int refreshes: 0
  function monitorFor(screen) { return screen ? (monitorMap[screen.name] || null) : null; }
  function refreshToplevels() { refreshes++; }
  readonly property QtObject toplevels: QtObject { property var values: [] }
  property var activeToplevel: ({title:"Fixture title"})
  readonly property bool usingLua: true
  function dispatch(command) { throw new Error("No startup dispatch allowed"); }
}
'''


def trial_surface(data):
    """Compile the real registry wiring with only layer ownership substituted."""
    text = data.decode()
    edits = {
        '  PanelWindow {\n': '''  Item {
    property var screen
    property int exclusionMode
    property color color
    property int exclusiveZone
    property var mask
''',
        '    anchors { top: true; left: true; right: true }\n': '',
        '    margins { top: bars.barHidden ? -barPanel.implicitHeight : 0 }\n': '',
        '    surfaceFormat.opaque: false\n': '',
    }
    for old, new in edits.items():
        if text.count(old) != 1:
            raise ValueError('Trial layer fixture witness differs')
        text = text.replace(old, new)
    return ('\n'.join(line for line in text.splitlines()
                      if not line.strip().startswith('WlrLayershell.')) + '\n').encode()


def indicator_transport(data):
    """Exercise the actual shared owner, replacing only its OS process seam."""
    text = data.decode()
    start = '  property Process rpc: Process {\n'
    if text.count(start) != 1 or not text.endswith('  }\n}\n'):
        raise ValueError('Indicator RPC fixture witness changed')
    prefix = text[:text.index(start)]
    return (prefix + '''  property QtObject rpc: QtObject {
    id: rpc
    property bool running: false
    property bool stdinEnabled: false
    property var calls: []
    function exec(args) { calls = calls.concat([args]); }
  }
}
''').encode()


def ghost_surface(data):
    """Keep original ghost/poof markup, replacing only native layer ownership."""
    text = data.decode()
    edits = {
        '  component DragGhostPanel: PanelWindow {\n': '''  component DragGhostPanel: Item {
    property color color
    property var screen
    property int exclusionMode
    property var mask
    width: ghostScreen ? ghostScreen.width : 0
    height: ghostScreen ? ghostScreen.height : 0
''',
        '''    anchors {
      top: true
      bottom: true
      left: true
      right: true
    }
''': '',
    }
    for old, new in edits.items():
        if text.count(old) != 1:
            raise ValueError('Ghost layer fixture witness differs')
        text = text.replace(old, new)
    return ('\n'.join(line for line in text.splitlines()
                      if not line.strip().startswith('WlrLayershell.')) + '\n').encode()


def fixture(name):
    if name in indicator_feedback_fixtures.CASES:
        return indicator_feedback_fixtures.fixture(name)
    if name not in CASES:
        raise ValueError('Unknown frame fixture')
    width = {'laptop':1280, 'ultrawide':3440, 'external':1920, 'narrow':320}.get(name, 1280)
    return '''//@ pragma IgnoreSystemSettings
import QtQuick
import QtQuick.Window
import Quickshell
import "FixtureHyprland"
import qs.Ui
ShellRoot {
  id: test
  property var layout: null
  property var appearance: null
  property var second: null
  property var kept: null
  property var keptOther: null
  property var oldParent: null
  property var peek: null
  property var alternatePeek: null
  property real oldPeekEdge: 0
  property int peekPhase: 0
  property var indicators: null
  property var nativeOwner: null
  property bool indicatorA: false
  property bool indicatorB: false
  property bool indicatorC: false
  property real fixedIndicatorX: 0
  property int indicatorPhase: 0
  property var observedDndDelegate: null
  readonly property bool gestureCase: mode.indexOf("drag-")===0
  property var dragged: null
  property var sharedLayout: ({left:["fixture.left"],centerBegin:[],center:["fixture.center"],centerEnd:[],right:["fixture.right"]})
  property string mode: "%s"
  readonly property bool sideCenters: mode==="center-sides" || mode==="navigation" || mode==="peek-edge"
  readonly property var components: ({"fixture.left":left,"fixture.center":center,"fixture.right":right,"fixture.begin":begin,"fixture.end":end})
  QtObject {
    id: editor
    property bool accept: false
    property bool loaded: true
    property int writes: 0
    function editLayout(expected,next) {
      if(!accept || JSON.stringify(expected)!==JSON.stringify(test.sharedLayout))return false;
      writes++;test.sharedLayout=next;return true;
    }
  }
  QtObject {
    id: api
    property bool transparentBar: false
    property bool vertical: false
    property int barSize: 26
    property string fontFamily: "monospace"
    property color urgent: "#ff5555"
    property bool centerSectionRevealHeld: false
    property bool centerHoverRevealSuppressed: false
    property bool foregroundAnimationEnabled: true
    function showTooltip(owner,text) {}
    property color background: "#101315"
    property color barForeground: "#cacccc"
    property var activePopout: null
    property var clickTargets: []
    property int hiddenTips: 0
    function hideTooltip(owner){hiddenTips++;}
    function itemContainsPoint(target,source,x,y){return target.contains(target.mapFromItem(source,x,y));}
  }
  Window {id:host;visible:true;width:%d;height:test.gestureCase?200:26}
  Window {id:other;visible:test.mode==="outputs";width:1280;height:26}
  component FixtureWidget: Item {
    implicitHeight:26
    property bool opened:false
    property int opens:0
    property int presses:0
    property int heldButtons: Qt.NoButton
    function triggerPress(button){presses++;}
    Rectangle {anchors.fill:parent;color:"#cacccc"}
    function open(){opened=true;opens++;}
    function close(){opened=false;}
  }
  Component {id:left; LiveStatus {maximumWidth:test.layout?Math.max(0,test.layout.centerStart-16):0}}
  Component {id:center; FixtureWidget {implicitWidth:150}}
  Component {id:right; FixtureWidget {implicitWidth:130}}
  Component {id:begin; FixtureWidget {implicitWidth:40}}
  Component {id:end; FixtureWidget {implicitWidth:30}}
  function require(value,message) {if(!value)throw new Error(message);}
  function section(item,region) {
    if(item.region===region && item.naturalWidth!==undefined)return item;
    for(var i=0;i<item.children.length;i++){var found=section(item.children[i],region);if(found)return found;}
    return null;
  }
  function makeFrame(parent) {
    var factory=Qt.createComponent("BarFrame.qml",Component.PreferSynchronous);
    require(factory.status===Component.Ready,factory.errorString());
    var admitted=mode==="missing-component"?Object.assign({},test.components,{"fixture.right":null}):test.components;
    var result=factory.createObject(parent,{width:host.width,height:26,widgetComponents:admitted,
      barWindow:test.gestureCase?({screen:{name:parent===other.contentItem?"fixture-b":"fixture-a",width:host.width,height:200},contentItem:parent,width:host.width,height:200}):(parent===other.contentItem?other:host),
      barApi:test.gestureCase?api:null,
      layoutEditor:(test.mode==="guarded-edit" || test.gestureCase)?editor:null,
      layoutConfig:Qt.binding(function(){return test.sharedLayout;})});
    factory.destroy();require(result!==null,"frame construction");return result;
  }
  Timer {interval:1;running:true;onTriggered:{
    try {
      if(mode==="long-title")Hyprland.activeToplevel=({title:"<b>"+"Long title ".repeat(100)+"</b>"});
      if(mode==="empty")sharedLayout=({left:[],centerBegin:[],center:[],centerEnd:[],right:[]});
      if(sideCenters) sharedLayout=Object.assign({},sharedLayout,{centerBegin:["fixture.begin"],centerEnd:["fixture.end"]});
      if(mode==="trial-compile") {
        var production=Qt.createComponent("TrialPanel.qml",Component.PreferSynchronous);
        require(production.status===Component.Ready,production.errorString());
        production.destroy();
      }
      if(mode==="appearance-queue") {
        var stateFactory=Qt.createComponent("AppearanceState.qml",Component.PreferSynchronous);
        require(stateFactory.status===Component.Ready,stateFactory.errorString());
        appearance=stateFactory.createObject(test,{helper:"/fixture/menu_model.py",finishing:true});stateFactory.destroy();
        require(appearance!==null,"real Appearance adapter construction");
        var a=JSON.parse(JSON.stringify(sharedLayout)),b=JSON.parse(JSON.stringify(a)),c=JSON.parse(JSON.stringify(a));
        b.center=[];b.centerEnd=["fixture.center"];
        c.center=[];c.left.push("fixture.center");
        appearance.apply({bar:{bar_layout:a,clock_settings:{},tray_settings:{pinned:[],hidden:[]}},dock:{}});
        require(appearance.editLayout(a,b) && appearance.editLayout(b,c),"real adapter queues a conditional chain");
        appearance.setClock({birthYear:1990});
        require(appearance.sameLayout(appearance.bar.bar_layout,c),"real binding projects newest layout");
        appearance.inFlight=appearance.queue[0];appearance.queue=appearance.queue.slice(1);
        appearance.finishResponse(0,JSON.stringify({ok:false,status:"conflict",message:"Bar layout changed; fixture conflict.",appearance:{bar:{bar_layout:a,clock_settings:{},tray_settings:{pinned:[],hidden:[]}},dock:{}}}));
        appearance.finishing=true;
        require(appearance.queue.length===1 && appearance.queue[0][1]==="clock-settings","real adapter retains unrelated edit only");
        require(appearance.sameLayout(appearance.bar.bar_layout,a) && appearance.layoutErrorText!=="","real bindings recover from conflict");
        require(!appearance.backend.running,"no fixture helper process starts");appearance.queue=[];
      }
      layout=makeFrame(host.contentItem);
      if(mode==="outputs" || mode==="drag-output")second=makeFrame(other.contentItem);
      check.start();
    }catch(error){console.error("OMABUNTU_FRAME_ASSERT",String(error));Qt.exit(42);}
  }}
  Timer {id:check;interval:300;onTriggered:{
    try {
      if(mode==="native-indicators" || mode==="indicator-owner" || mode==="indicator-rpc"){exerciseNativeIndicators();return;}
      if(mode.indexOf("indicators-")===0){exerciseIndicators();return;}
      if(mode.indexOf("peek-")===0){exercisePeek();return;}
      if(mode.indexOf("fullscreen-")===0){exerciseFullscreen();finish();return;}
      if(gestureCase){exercisePointer();return;}
      if(mode==="empty") {
        require(layout.widgetHosts.length===0 && layout.moduleSlots.length===0,"empty layout has no widget owners");
        require(layout.centerStart===Math.round(host.width/2) && layout.centerEnd===layout.centerStart,"empty center geometry");
        require(!layout.switchPanelFrom({},1),"empty layout has no navigation target");finish();return;
      }
      if(mode==="missing-component") {
        require(layout.widgetForId("fixture.right")===null,"missing admission never resolves custom QML");
        require(layout.widgetForId("fixture.left")!==null && layout.widgetForId("fixture.center")!==null,"missing Component does not break siblings");
        require(!layout.switchPanelFrom(layout.widgetForId("fixture.center"),1),"missing Component has no panel target");finish();return;
      }
      var base=Math.round((host.width-150)/2);
      require(layout.centerStart===base-(sideCenters?40:0),"original center/begin positioning");
      require(layout.centerEnd===base+150+(sideCenters?30:0),"original center/end positioning");
      var l=section(layout,"left"),r=section(layout,"right"),c=section(layout,"center");
      require(l&&r&&c,"all three sections loaded");
      var lp=l.mapToItem(layout,0,0),rp=r.mapToItem(layout,0,0),cp=c.mapToItem(layout,0,0);
      require(lp.x===8 && rp.x+r.width===host.width-8,"original eight-pixel edge insets");
      require(cp.x===base && c.width===150,"clock stays centered independently of title length");
      require(lp.x+l.width<=layout.centerStart-8,"left section does not overlap center");
      require(rp.x>=layout.centerEnd+8,"right section does not overlap center");
      require(l.height===26&&r.height===26&&c.height===26,"bar height unchanged");
      require(layout.widgetForId("fixture.left").maximumWidth===Math.max(0,layout.centerStart-16),"title gets live section budget");
      if(mode==="move" || mode==="outputs" || mode==="hide" || mode==="guarded-edit") {
        kept=layout.widgetForId("fixture.center");kept.opens=7;oldParent=kept.parent.parent.parent;
        if(second){keptOther=second.widgetForId("fixture.center");keptOther.opens=3;require(keptOther!==kept,"output pools are independent");}
        var next=JSON.parse(JSON.stringify(sharedLayout));
        if(mode==="hide")next.right=[];
        else {next.center=[];next.centerEnd=["fixture.center"];}
        if(mode==="guarded-edit") {
          var move={from:{region:"center",index:0,id:"fixture.center"},to:{region:"centerEnd",index:-1}};
          var stale={from:{region:"center",index:0,id:"other"},to:move.to};
          require(!layout.moveWidget(stale) && editor.writes===0,"original source-ID guard refuses stale move");
          require(!layout.moveWidget(move) && sharedLayout.center[0]==="fixture.center","rejected editor does not mutate source layout");
          editor.accept=true;
          require(layout.moveWidget(move) && editor.writes===1,"original move submits one guarded edit");
        } else sharedLayout=next;
        changed.start();return;
      }
      if(mode==="navigation") {
        var clock=layout.widgetForId("fixture.center"),first=layout.widgetForId("fixture.begin"),last=layout.widgetForId("fixture.end");
        require(layout.switchPanelFrom(first,1) && clock.opens===1,"original layout-order panel navigation");
        require(layout.switchPanelFrom(clock,1) && last.opens===1,"centerEnd follows center");
        last.visible=false;
        require(layout.switchPanelFrom(clock,1) && first.opens===1,"hidden widgets are skipped");
        require(!layout.switchPanelFrom(layout.widgetForId("fixture.right"),1),"single-panel region does not jump sections");
      }
      finish();
    }catch(error){console.error("OMABUNTU_FRAME_ASSERT",String(error));Qt.exit(42);}
  }}
  Timer {id:changed;interval:100;onTriggered:{
    try {
      require(layout.widgetForId("fixture.center")===kept && kept.opens===7,"moving keeps original widget instance and state");
      if(mode==="hide") {
        require(layout.widgetForId("fixture.right")===null,"removed widget unloads");
        require(kept.parent.parent.parent===oldParent,"unrelated widget is not reparented");
      } else {
        require(kept.parent.parent.parent!==oldParent,"pool hands widget to its new slot");
        require(layout.popoutSectionOf(kept)==="centerBegin center centerEnd","popout grouping follows layout");
      }
      if(second) {
        require(second.widgetForId("fixture.center")===keptOther && keptOther.opens===3,"shared layout preserves each output's own widget state");
        require(!second.switchPanelFrom(kept,1),"navigation never takes another output's owner");
      }
      if(mode==="guarded-edit") {
        require(!layout.removeWidget({region:"centerEnd",index:0,id:"other"}),"original removal identity guard");
        require(layout.removeWidget({region:"centerEnd",index:0,id:"fixture.center"}),"original remove submits guarded edit");
        removed.start();return;
      }
      finish();
    }catch(error){console.error("OMABUNTU_FRAME_ASSERT",String(error));Qt.exit(42);}
  }}
  Timer {id:removed;interval:100;onTriggered:{
    try {
      require(editor.writes===2 && layout.widgetForId("fixture.center")===null,"guarded removal unloads widget");
      require(layout.widgetForId("fixture.left")!==null && layout.widgetForId("fixture.right")!==null,"removal keeps sibling owners");
      finish();
    }catch(error){console.error("OMABUNTU_FRAME_ASSERT",String(error));Qt.exit(42);}
  }}
  function pointer(item) {
    if(item.objectName==="bar-module-pointer")return item;
    for(var i=0;i<item.children.length;i++){var found=pointer(item.children[i]);if(found)return found;}
    return null;
  }
  function exercisePointer() {
    editor.accept=mode!=="drag-rejected";
    var slot=layout.moduleSlots.find(function(s){return s.moduleName==="fixture.center";});
    dragged=slot.activeItem;dragged.opens=7;
    var p=pointer(slot);require(p!==null && p.enabled,"original pointer surface is ready");
    var event={x:75,y:13,button:Qt.LeftButton,buttons:Qt.LeftButton,accepted:true};
    p.pointerPressed(event);require(dragged.heldButtons===Qt.LeftButton,"original held feedback");
    p.pointerMoved({x:76,y:13,buttons:Qt.LeftButton});require(layout.barDragSource===null,"original four-pixel threshold");
    if(mode==="drag-click") {
      p.pointerReleased(event);p.pointerClicked(event);
      require(dragged.presses===1 && dragged.heldButtons===Qt.NoButton && editor.writes===0,"click routes once without a layout write");finish();return;
    }
    p.pointerMoved({x:83,y:13,buttons:Qt.LeftButton});
    require(layout.barDragSource===slot && dragged.heldButtons===Qt.NoButton && api.hiddenTips>0,"original drag starts and releases held feedback");
    if(mode==="drag-cancel" || mode==="drag-output") {
      if(second){second.beginBarDrag(slot,75,13);require(second.barDragSource===null,"another output cannot adopt this slot");}
      p.pointerCanceled();require(layout.barDragSource===null && Object.keys(layout.barDragShares).length===0,"cancellation clears room and grab state");
    } else if(mode==="drag-drift") {
      var changedLayout=JSON.parse(JSON.stringify(sharedLayout));changedLayout.right=[];sharedLayout=changedLayout;
      p.pointerReleased(event);
    } else {
      var origin=slot.mapToItem(null,0,0);
      var x=mode==="drag-empty"?origin.x-30:20;
      if(mode==="drag-remove") {
        x=origin.x+75;
        p.pointerMoved({x:x-origin.x,y:50,buttons:Qt.LeftButton});
        require(!layout.barDragRemoveArmed,"small off-strip overshoot does not arm removal");
      }
      p.pointerMoved({x:x-origin.x,y:mode==="drag-remove"?100:13,buttons:Qt.LeftButton});
      if(mode==="drag-remove")require(layout.barDragRemoveArmed,"original 48px off-strip removal threshold");
      else require(layout.barDragRoom && layout.barDragRoom.region===(mode==="drag-empty"?"centerBegin":"left"),"original drop resolution including empty sections: "+JSON.stringify({room:layout.barDragRoom,origin:origin,sceneX:layout.barDragSceneX,remove:layout.moduleRemoveDistance({x:layout.barDragSceneX,y:layout.barDragSceneY}),target:layout.barDragTarget?(layout.barDragTarget.slot?layout.barDragTarget.slot.region:layout.barDragTarget.region):null,slots:layout.moduleSlots.map(function(s){return {id:s.moduleName,x:s.mapToItem(null,0,0).x,width:s.width,widgetWidth:s.widgetWidth,visible:s.visible,same:layout.sameWindow(layout.slotWindow(s),layout.barDragWindow)};})}));
      p.pointerReleased(event);p.pointerClicked(event);
      require(dragged.presses===0,"drag suppresses composed click");
    }
    gestureDone.start();
  }
  Timer {id:gestureDone;interval:900;onTriggered:{
    try {
      require(layout.barDragSource===null && layout.barPoof===null && layout.barRemoval===null,"settle/poof completes without a gesture lifetime leak");
      if(mode==="drag-remove")require(editor.writes===1 && layout.widgetForId("fixture.center")===null,"original poof commits guarded removal");
      else {
        require(layout.widgetForId("fixture.center")===dragged && dragged.opens===7,"move/cancel retains widget state");
        var committed=mode==="drag-move" || mode==="drag-empty";
        require(editor.writes===(committed?1:0),"exactly one write only for an accepted drop");
        if(committed)require(sharedLayout[mode==="drag-empty"?"centerBegin":"left"].indexOf("fixture.center")!==-1,"drop reaches intended section");
        else require(sharedLayout.center[0]==="fixture.center","cancel/drift/rejection does not overwrite source order");
      }
      finish();
    }catch(error){console.error("OMABUNTU_FRAME_ASSERT",String(error));Qt.exit(42);}
  }}
  Component {id:indicatorAComponent;BarIndicator {active:test.indicatorA;activeText:"A";inactiveText:"a"}}
  Component {id:indicatorBComponent;BarIndicator {active:test.indicatorB;activeText:"B";inactiveText:"b"}}
  Component {id:indicatorCComponent;BarIndicator {active:test.indicatorC;activeText:"C";inactiveText:"c"}}
  function indicatorItem(item,id,block) {
    if(item.moduleName===id && item.indicatorBlock===block && item.activeOverride!==undefined)return item;
    for(var i=0;i<item.children.length;i++){var result=indicatorItem(item.children[i],id,block);if(result)return result;}
    return null;
  }
  function indicatorX(id) {
    var item=indicatorItem(indicators,id,"active");require(item!==null,"original active indicator exists");
    return item.mapToItem(host.contentItem,0,0).x;
  }
  Component {id:nativeDndComponent;DndIndicator {backend:test.nativeOwner.dnd}}
  Component {id:nativeNightComponent;NightLightIndicator {backend:test.nativeOwner.nightlight}}
  function ownerReply(blocked) {
    return JSON.stringify({ok:true,schema:1,scope:nativeOwner.scope,blocked:blocked,
      states:{dnd:{known:true,active:indicatorA,key:"a".repeat(64)},nightlight:{known:true,active:true,key:"b".repeat(64)}}});
  }
  function setterCount() {return nativeOwner.rpc.calls.filter(function(args){return args[2]==="set";}).length;}
  function exerciseNativeIndicators() {
    var factory=Qt.createComponent("IndicatorState.qml",Component.PreferSynchronous);
    require(factory.status===Component.Ready,factory.errorString());
    nativeOwner=factory.createObject(test,{menuHelper:mode==="indicator-rpc"?Qt.resolvedUrl("menu_model.py").toString().replace("file://",""):"/fixture/menu_model.py",enabled:true});factory.destroy();
    require(nativeOwner!==null,"actual shared native owner constructs");nativeWait.start();
  }
  property int rpcWaits: 0
  Timer {id:nativeWait;interval:200;onTriggered:{
    try {
      if(mode==="indicator-rpc") {
        if(nativeOwner.busy || !nativeOwner.dnd.known) {require(++rpcWaits<15,"bounded actual helper round trip");nativeWait.start();return;}
        rpcWaits=0;
        if(indicatorPhase===0) {
          require(!nativeOwner.dnd.doNotDisturb && nativeOwner.nightlight.enabled,"actual stdin/collector response supplies known typed states");
          require(nativeOwner.dnd.setDoNotDisturb(true),"actual RPC accepts one DND request");
        } else if(indicatorPhase===1) {
          require(nativeOwner.dnd.doNotDisturb,"actual helper setter/readback round trip");
          require(nativeOwner.nightlight.setNightlight(false),"actual RPC accepts one nightlight request");
        } else {
          require(!nativeOwner.nightlight.enabled,"actual native-owner facade consumes readback, not optimistic cache");
          nativeOwner.enabled=false;require(!nativeOwner.dnd.known,"disabling revokes known state without restoring native fields");finish();return;
        }
        indicatorPhase++;nativeWait.start();return;
      }
      if(indicatorPhase===0) {
        require(nativeOwner.busy && !nativeOwner.dnd.known,"initial read is not a fabricated inactive status");
        if(mode==="indicator-owner") {
          nativeOwner.finish(0,JSON.stringify({ok:true,schema:1,scope:nativeOwner.scope,blocked:false,states:{dnd:{known:true,active:"false",key:"a".repeat(64)},nightlight:{known:false}}}));
          require(!nativeOwner.dnd.known && !nativeOwner.dnd.writable,"malformed boolean fails closed");
          nativeOwner.refresh();
        }
        nativeOwner.finish(0,ownerReply(false));
        var factory=Qt.createComponent("IndicatorsView.qml",Component.PreferSynchronous);
        require(factory.status===Component.Ready,factory.errorString());
        indicators=factory.createObject(host.contentItem,{bar:api,indicatorComponents:({}),settings:({items:["NightLight","Dnd"]})});factory.destroy();
        indicators.indicatorComponents=Qt.binding(function(){return {Dnd:nativeOwner.dnd.known?nativeDndComponent:null,NightLight:nativeOwner.nightlight.known?nativeNightComponent:null};});
        indicators.width=Qt.binding(function(){return indicators.implicitWidth;});indicators.height=26;indicators.x=256;
        api.centerSectionRevealHeld=true;
      } else if(indicatorPhase===1) {
        require(indicators.activeIndicatorIds.indexOf("NightLight")!==-1 && indicators.activeIndicatorIds.indexOf("Dnd")===-1,"original icons consume actual known active/inactive booleans");
        var dnd=indicatorItem(indicators,"Dnd","inactive");require(dnd && dnd.enabled,"original inactive DND constructed and actionable");
        observedDndDelegate=dnd;
        dnd.pressed(Qt.LeftButton);
        require(nativeOwner.inFlight.kind==="dnd" && nativeOwner.inFlight.desired===true && nativeOwner.inFlight.expected==="a".repeat(64),"original DND dispatch freezes primitive state key");
        require(!nativeOwner.dnd.setDoNotDisturb(true) && setterCount()===1,"busy owner never queues duplicate setter");
        nativeOwner.finish(0,JSON.stringify({ok:true,status:"confirmed"}));
        require(nativeOwner.readbackPending && nativeOwner.dnd.known && !nativeOwner.dnd.writable && !nativeOwner.dnd.doNotDisturb,"confirmation retains observation without optimistic state or writable gap");
        require(dnd.enabled && !dnd.pressable,"confirmed readback gates presses, not hover");
      } else if(indicatorPhase===2) {
        require(nativeOwner.busy && setterCount()===1,"confirmation schedules only a read, never replay");
        require(nativeOwner.readbackPending && indicatorItem(indicators,"Dnd","inactive")===observedDndDelegate && nativeOwner.dnd.known && !nativeOwner.dnd.doNotDisturb,"confirmed pending read retains actual original delegate and last observed value");
        indicatorA=true;nativeOwner.finish(0,ownerReply(false));
      } else if(indicatorPhase===3) {
        require(indicators.activeIndicatorIds.indexOf("Dnd")!==-1,"known readback changes the original active block");
        var night=indicatorItem(indicators,"NightLight","active");require(night && night.enabled,"original nightlight is actionable");
        night.toggle();require(nativeOwner.inFlight.kind==="nightlight" && nativeOwner.inFlight.desired===false,"original nightlight dispatch requests identity off only");
        nativeOwner.finish(0,JSON.stringify({ok:true,status:"uncertain"}));
        require(!nativeOwner.nightlight.known && !nativeOwner.nightlight.writable,"uncertainty still revokes admission immediately");
      } else if(indicatorPhase===4) {
        nativeOwner.finish(0,ownerReply(true));
        require(nativeOwner.blocked && !nativeOwner.nightlight.writable && !nativeOwner.nightlight.setNightlight(false),"uncertain action blocks further writes");
        require(setterCount()===2,"no retry or compensating toggle");
        nativeOwner.refresh();var old=ownerReply(false);nativeOwner.enabled=false;nativeOwner.finish(0,old);
        require(!nativeOwner.dnd.known && Object.keys(nativeOwner.states).length===0,"late old-scope response cannot revive hidden owner");
      } else {
        require(indicators.indicatorEntries.length===0 && indicators.width===0,"unknown owner removes entries, never invents inactive icons");
        require(editor.writes===0,"native status/interaction never writes layout");finish();return;
      }
      indicatorPhase++;nativeWait.start();
    }catch(error){console.error("OMABUNTU_FRAME_ASSERT",String(error));Qt.exit(42);}
  }}
  function exerciseIndicators() {
    indicatorA=mode==="indicators-order";
    var factory=Qt.createComponent("IndicatorsView.qml",Component.PreferSynchronous);
    require(factory.status===Component.Ready,factory.errorString());
    indicators=factory.createObject(host.contentItem,{bar:api,indicatorComponents:({a:indicatorAComponent,b:indicatorBComponent,c:indicatorCComponent}),settings:({items:["a","b","c"]})});
    factory.destroy();require(indicators!==null,"actual original indicator layout constructs");
    indicators.width=Qt.binding(function(){return indicators.implicitWidth;});
    indicators.height=Qt.binding(function(){return indicators.implicitHeight;});
    // Keep the synthetic start-fixed sample away from the offscreen cursor at 0,0.
    indicators.x=Qt.binding(function(){return indicators.fixedEdge==="start"?256:host.width-indicators.width;});
    indicatorWait.start();
  }
  // Let the original 140ms WidgetButton opacity animation settle.
  Timer {id:indicatorWait;interval:200;onTriggered:{
    try {
      if(mode==="indicators-missing") {
        if(indicatorPhase===0) {
          indicators.settings={items:["missing","constructor","toString","../../unreviewed.qml"]};
          api.centerSectionRevealHeld=true;indicatorPhase++;indicatorWait.start();return;
        }
        require(indicators.indicatorEntries.length===0 && indicators.width===0,"unadmitted IDs cannot create loaders or fabricate inactive statuses");
        require(indicators.activeIndicatorIds.length===0,"no false active status");finish();return;
      }
      if(mode==="indicators-reveal") {
        if(indicatorPhase===0) {
          require(indicators.width===0,"inactive icons occupy no idle space");
          api.centerSectionRevealHeld=true;indicatorPhase++;indicatorWait.start();return;
        }
        if(indicatorPhase===1) {
          require(indicators.width>0 && indicators.revealInactiveIndicators,"shared peek reveals original inactive block");
          var item=indicatorItem(indicators,"a","inactive");
          require(item && Math.abs(item.opacity-0.45)<0.001 && !item.concealed,"original inactive dimming and concealment "+JSON.stringify(item?{opacity:item.opacity,concealed:item.concealed,active:item.effectiveActive,revealed:item.inactiveRevealed,block:item.indicatorBlock}:null));
          require(item.mapToItem(indicators,0,0).x<indicatorItem(indicators,"b","inactive").mapToItem(indicators,0,0).x,"original inactive end-fixed ordering");
          indicators.fixedEdge="start";api.centerHoverRevealSuppressed=true;indicatorPhase++;indicatorWait.start();return;
        }
        if(indicatorPhase===2) {
          require(indicators.width===0,"public suppression closes shared reveal");
          require(indicatorItem(indicators,"a","inactive").mapToItem(indicators,0,0).x>indicatorItem(indicators,"b","inactive").mapToItem(indicators,0,0).x,"original inactive block mirrors at fixed start");
          indicators.setIndicatorItemHovered(true);indicatorPhase++;indicatorWait.start();return;
        }
        if(indicatorPhase===3) {
          require(indicators.width>0,"original item hover keeps reveal independently");
          indicators.setIndicatorItemHovered(false);indicatorPhase++;indicatorWait.interval=180;indicatorWait.start();return;
        }
        require(indicators.width===0 && !indicators.indicatorItemHovered,"original leave timer closes item reveal "+JSON.stringify({width:indicators.width,item:indicators.indicatorItemHovered,area:indicators.indicatorAreaHovered}));finish();return;
      }
      if(indicatorPhase===0) {
        require(JSON.stringify(indicators.activeIndicatorIds)==='["a"]',"original active block always shown");
        fixedIndicatorX=indicatorX("a");indicatorB=true;indicatorPhase++;indicatorWait.start();return;
      }
      if(indicatorPhase===1) {
        require(JSON.stringify(indicators.activeIndicatorIds)==='["b","a"]' && indicatorX("a")===fixedIndicatorX,"new active status grows away from fixed end");
        indicators.fixedEdge="start";indicatorPhase++;indicatorWait.start();return;
      }
      if(indicatorPhase===2) {fixedIndicatorX=indicatorX("a");indicatorC=true;indicatorPhase++;indicatorWait.start();return;}
      require(JSON.stringify(indicators.activeIndicatorIds)==='["b","a","c"]' && indicatorX("a")===fixedIndicatorX,"new active status grows away from fixed start");
      require(editor.writes===0,"indicator projection never writes layout");finish();
    }catch(error){console.error("OMABUNTU_FRAME_ASSERT",String(error));Qt.exit(42);}
  }}
  function exercisePeek() {
    var factory=Qt.createComponent("BarPeekState.qml",Component.PreferSynchronous);
    require(factory.status===Component.Ready,factory.errorString());
    peek=factory.createObject(test);alternatePeek=factory.createObject(test);factory.destroy();
    require(peek && alternatePeek,"actual original shared state constructs without a scene");
    layout.setPeekHovered(true);require(layout.peekOwner===null,"late owner is not fabricated");
    layout.peekState=peek;
    require(peek.barHoverCount===1 && peek.centerSectionRevealHeld,"late binding attaches held hover");
    peek.setCenterHoverRevealSuppressed(true);
    require(peek.centerHoverRevealSuppressed && peek.barHovered && peek.centerSectionRevealHeld,"public suppression is independent of original tally");
    peek.setCenterHoverRevealSuppressed(false);
    if(mode==="peek-owner") {
      second=makeFrame(other.contentItem);second.peekState=peek;second.setPeekHovered(true);
      require(peek.barHoverCount===2,"two output owners counted");
      layout.setPeekHovered(false);require(peek.barHoverCount===1 && peek.centerSectionRevealHeld,"peer keeps reveal held");
      layout.setPeekHovered(true);layout.setPeekHovered(true);require(peek.barHoverCount===2,"same owner does not double enter");
      layout.peekState=alternatePeek;
      require(peek.barHoverCount===1 && alternatePeek.barHoverCount===1,"live owner replacement transfers exactly one hover");
      layout.peekSuppressed=true;
      require(alternatePeek.barHoverCount===0 && alternatePeek.leaveDelay.running,"hide or fullscreen releases tally");
      layout.setPeekHovered(true);require(alternatePeek.barHoverCount===0,"suppressed input cannot reacquire");
      layout.peekSuppressed=false;layout.setPeekHovered(true);
      require(alternatePeek.barHoverCount===1 && !alternatePeek.leaveDelay.running,"return cancels leave delay");
      layout.peekState=peek;require(peek.barHoverCount===2 && alternatePeek.barHoverCount===0,"return to shared owner");
      second.destroy();second=null;peekWait.start();return;
    }
    if(mode==="peek-edge") {
      oldPeekEdge=layout.peekEdge;
      require(oldPeekEdge===layout.centerStart+40,"edge is actual center box, not adjacent indicator boundary");
      layout.width+=200;peekWait.start();return;
    }
    layout.setPeekHovered(false);
    require(peek.barHoverCount===0 && peek.centerSectionRevealHeld && peek.leaveDelay.running,"leave uses original hysteresis, not immediate close");
    layout.setPeekHovered(true);
    require(!peek.leaveDelay.running && peek.centerSectionRevealHeld,"quick return stops pending close");
    layout.setPeekHovered(false);layout.setPeekHovered(false);
    require(peek.barHoverCount===0,"duplicate leave does not underflow");peekWait.start();
  }
  Timer {id:peekWait;interval:180;onTriggered:{
    try {
      if(mode==="peek-owner" && peekPhase===0) {
        require(peek.barHoverCount===1 && peek.centerSectionRevealHeld,"actual deferred peer destruction releases exactly its tally");
        peek.destroy();peekPhase=1;peekWait.start();return;
      } else if(mode==="peek-owner") {
        require(!layout.peekState && !layout.peekOwner,"destroyed shared owner leaves no stale object target");
        layout.peekState=alternatePeek;
        require(alternatePeek.barHoverCount===1,"replacement after owner destruction adopts held hover");
      } else if(mode==="peek-edge" && peekPhase===0) {
        require(layout.peekEdge===oldPeekEdge,"geometry cannot chase a held peek");
        layout.setPeekHovered(false);peekPhase=1;peekWait.start();return;
      } else if(mode==="peek-edge")require(!peek.centerSectionRevealHeld && layout.peekEdge===oldPeekEdge+100,"closed edge follows original center-box measurement");
      else require(!peek.centerSectionRevealHeld && !peek.leaveDelay.running && !peek.barHovered,"actual original timer closes after last leave");
      require(editor.writes===0,"peek lifecycle never persists a layout");finish();
    }catch(error){console.error("OMABUNTU_FRAME_ASSERT",String(error));Qt.exit(42);}
  }}
  function exerciseFullscreen() {
    var factory=Qt.createComponent("BarFullscreenState.qml",Component.PreferSynchronous);
    require(factory.status===Component.Ready,factory.errorString());
    var left=factory.createObject(test,{screen:{name:"fixture-a"},dragFrame:layout});
    var right=factory.createObject(test,{screen:{name:"fixture-b"}});
    var refresh=factory.createObject(test,{refreshEvents:true});factory.destroy();
    require(left && right && refresh,"actual source-derived fullscreen observers construct");
    var strip={kind:"strip"},empty={kind:"empty"};
    Hyprland.monitorMap={"fixture-a":{activeWorkspace:{id:10}},"fixture-b":{activeWorkspace:{id:20}}};
    Hyprland.toplevels.values=[{workspace:{id:10},lastIpcObject:{fullscreen:2}}];
    require(left.underFullscreen && !right.underFullscreen,"fullscreen belongs to active workspace on its own output");
    require(left.maskFor(false,strip,empty)===empty && left.maskFor(true,strip,empty)===empty,"fullscreen always drops even drag input");
    require(right.maskFor(false,strip,empty)===strip && right.maskFor(true,strip,empty)===null,"other output retains strip and active drag mask");
    if(mode==="fullscreen-local") {
      Hyprland.toplevels.values=[{workspace:{id:99},lastIpcObject:{fullscreen:2}}];
      require(!left.underFullscreen && !right.underFullscreen,"fullscreen on an inactive workspace never suppresses these outputs");
      Hyprland.monitorMap={};require(!left.underFullscreen,"missing output never borrows focused monitor");
      left.screen=null;require(!left.underFullscreen,"missing screen has no fullscreen owner");
    }
    if(mode==="fullscreen-state") {
      for(var flag of [0,1]) {
        Hyprland.toplevels.values=[{workspace:{id:10},lastIpcObject:{fullscreen:flag}}];
        require(!left.underFullscreen && left.maskFor(false,strip,empty)===strip,"normal/maximized keeps original input strip");
      }
      Hyprland.monitorMap={"fixture-a":{activeWorkspace:{id:-5}}};
      Hyprland.toplevels.values=[{workspace:{id:-5},lastIpcObject:{fullscreen:2}}];
      require(left.underFullscreen,"named negative workspace IDs retain original model semantics");
      Hyprland.toplevels.values=[];require(!left.underFullscreen,"toplevel disappearance restores idle strip");
      right.hidden=true;require(right.suppressed && right.maskFor(true,strip,empty)===empty,"explicit hide also dominates drag input");
      right.hidden=false;require(right.maskFor(false,strip,empty)===strip,"revealing does not retain suppressed state");
    }
    if(mode==="fullscreen-drag") {
      Hyprland.toplevels.values=[];
      var before=JSON.stringify(sharedLayout),count=editor.writes;
      layout.barDragSource=layout.moduleSlots[0];
      Hyprland.toplevels.values=[{workspace:{id:10},lastIpcObject:{fullscreen:2}}];
      require(layout.barDragSource===null && JSON.stringify(sharedLayout)===before && editor.writes===count,"fullscreen cancels owned drag without any layout write");
      Hyprland.toplevels.values=[];layout.barDragSource=layout.moduleSlots[0];
      left.hidden=true;require(layout.barDragSource===null && editor.writes===count,"hide cancels drag without persistence");
      left.dragFrame=null;layout.barDragSource=layout.moduleSlots[0];left.dragFrame=layout;
      require(layout.barDragSource===null,"late drag owner binding cannot bypass existing suppression");
    }
    if(mode==="fullscreen-refresh") {
      require(Hyprland.refreshes===0,"observer startup issues no refresh or dispatch");
      Hyprland.rawEvent({name:"workspace"});Hyprland.rawEvent(null);
      require(Hyprland.refreshes===0,"unrelated or malformed events never query");
      Hyprland.toplevels.values=[];Hyprland.rawEvent({name:"fullscreen"});
      require(Hyprland.refreshes===1 && !left.underFullscreen,"one shared read refresh, never optimistic fullscreen state");
      refresh.refreshEvents=false;refresh.destroy();refresh=null;Hyprland.rawEvent({name:"fullscreen"});
      require(Hyprland.refreshes===1,"disabled refresh owner and passive outputs never query");
    }
    left.destroy();right.destroy();if(refresh)refresh.destroy();
  }
  function finish() {
    if(mode==="negative")throw new Error("deliberate frame assertion");
    console.log("%s::"+mode);layout.destroy();if(second)second.destroy();if(appearance)appearance.destroy();host.visible=false;other.visible=false;
    Qt.callLater(function(){Qt.quit();});
  }
}
''' % (name, width, MARKER)


def classify(name, code, text):
    if name not in CASES:
        return False
    errors = re.findall(r'^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b.*', text, re.M)
    if name == 'negative':
        return code == 42 and len(errors) == 1 and 'deliberate frame assertion' in errors[0] and MARKER not in text
    if name == 'appearance-queue':
        if len(errors) != 1 or not re.fullmatch(
                r'WARN qml: OMABUNTU_APPEARANCE_FAILED Bar layout changed; fixture conflict\.', errors[0].strip()):
            return False
        errors = []
    return code == 0 and not errors and text.count(MARKER + '::' + name) == 1 and 'Configuration Loaded' in text
