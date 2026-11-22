"""Actual original controls, frame and synthetic Qt input; never native setters."""
CASES = ('indicator-stable-controls', 'indicator-tooltip-controls')


def fixture(name):
    if name not in CASES:
        raise ValueError('Unknown indicator feedback fixture')
    return '''//@ pragma IgnoreSystemSettings
import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
ShellRoot {
  id:test
  property string mode:"%s"
  property var view:null
  property var tips:null
  QtObject {
    id:dndProvider
    property bool known:true
    property bool writable:true
    property bool doNotDisturb:false
    property int writes:0
    function setDoNotDisturb(value){if(!writable)return false;writes++;doNotDisturb=value;return true;}
  }
  QtObject {
    id:night
    property bool known:true
    property bool writable:true
    property bool active:true
    readonly property bool enabled:active
    property int writes:0
    function setNightlight(value){if(!writable)return false;writes++;active=value;return true;}
  }
  QtObject {
    id:api
    property bool transparentBar:false
    property bool vertical:false
    property int barSize:26
    property string fontFamily:"monospace"
    property color urgent:"#ff5555"
    property color background:"#101315"
    property color barForeground:"#cacccc"
    property var activePopout:null
    property var clickTargets:[]
    property bool centerSectionRevealHeld:false
    property bool centerHoverRevealSuppressed:false
    property bool foregroundAnimationEnabled:true
    function showTooltip(owner,text){if(test.tips)test.tips.showTooltip(owner,text);}
    function hideTooltip(owner){if(test.tips)test.tips.hideTooltip(owner);}
    function registerClickTarget(target){if(clickTargets.indexOf(target)<0)clickTargets=clickTargets.concat([target]);}
    function unregisterClickTarget(target){clickTargets=clickTargets.filter(function(item){return item!==target;});}
    function itemContainsPoint(target,source,x,y){return target.contains(target.mapFromItem(source,x,y));}
  }
  QtObject {id:editor;property bool loaded:true;property int writes:0;function editLayout(before,after){writes++;return false;}}
  Component {id:dndComponent;DndIndicator{backend:dndProvider}}
  Component {id:nightComponent;NightLightIndicator{backend:night}}
  Component {
    id:indicators
    IndicatorsView {
      bar:api
      settings:({items:["NightLight","Dnd"],stableControls:true})
      indicatorComponents:({Dnd:dndProvider.known?dndComponent:null,NightLight:night.known?nightComponent:null})
      Component.onCompleted:test.view=this
    }
  }
  Window {
    id:surface;visible:true;width:800;height:80
    BarFrame {
      id:frame;width:800;height:26;barApi:api;layoutEditor:editor
      widgetComponents:({"omarchy.indicators":indicators})
      layoutConfig:({left:[],centerBegin:["omarchy.indicators"],center:[],centerEnd:[],right:[]})
    }
    TestCase {id:input;name:"NativeIndicatorFeedback";when:false}
  }
  function require(value,message){if(!value)throw new Error(message);}
  function collect(item,result){
    if(!item)return;
    if((item.moduleName==="Dnd"||item.moduleName==="NightLight") && "indicatorBlock" in item)result.push(item);
    for(var i=0;i<item.children.length;i++)collect(item.children[i],result);
  }
  function buttons(){var result=[];collect(test.view,result);return result;}
  function button(name){var result=buttons();for(var i=0;i<result.length;i++)if(result[i].moduleName===name)return result[i];return null;}
  function point(item){return item.mapToItem(frame,0,0);}
  Timer {interval:100;running:true;onTriggered:{try{test.run();}catch(error){console.error("OMABUNTU_FRAME_ASSERT",String(error));Qt.exit(42);}}}
  function run(){
    var component=Qt.createComponent("BarTooltipHost.qml",Component.PreferSynchronous);
    require(component.status===Component.Ready,component.errorString());tips=component.createObject(surface.contentItem);component.destroy();
    input.wait(200);require(view!==null,"actual original frame hosts original indicator view");
    var first=button("NightLight"),second=button("Dnd");
    require(first&&second&&buttons().length===2,"one original control per known provider");
    require(first.indicatorBlock==="single"&&second.indicatorBlock==="single","existing original single-block semantics");
    require(first.tooltipText==="Day Light"&&second.tooltipText==="Silence Notifications","pinned original English labels");
    var p=point(first),q=point(second);
    require(p.x<q.x && Math.abs(first.width-second.width)<0.01,"configured original equal-slot order");
    input.mouseMove(surface.contentItem,760,60);input.wait(30);
    if(mode==="indicator-stable-controls"){
      var states=[[true,true],[false,true],[false,false],[true,false],[true,true]];
      for(var i=0;i<states.length;i++){
        night.active=states[i][0];dndProvider.doNotDisturb=states[i][1];input.wait(200);
        require(button("NightLight")===first&&button("Dnd")===second,"native changes retain original delegates");
        require(buttons().length===2&&view.activeIndicatorIds.length===0,"no duplicate active projection");
        require(Math.abs(point(first).x-p.x)<0.01&&Math.abs(point(second).x-q.x)<0.01,"native states never exchange targets");
        require(Math.abs(first.opacity-(night.active?1:0.45))<0.01&&Math.abs(second.opacity-(dndProvider.doNotDisturb?1:0.45))<0.01,"original active/inactive dimming retained "+JSON.stringify({phase:i,night:[first.opacity,first.active,first.effectiveActive,first.inactiveRevealed],dndProvider:[second.opacity,second.active,second.effectiveActive,second.inactiveRevealed]}));
      }
      view.fixedEdge="start";input.wait(30);
      require(button("NightLight")===first&&button("Dnd")===second&&point(first).x<point(second).x,"fixed-edge change does not reverse stable controls");
      dndProvider.known=false;input.wait(200);require(button("Dnd")===null&&buttons().length===1,"unknown provider is absent, never false/inactive");
      dndProvider.known=true;input.wait(200);require(buttons().length===2&&button("NightLight").active===night.active,"provider readmission preserves the other observed native state");
    }else{
      input.mouseMove(second,second.width/2,second.height/2);input.wait(550);
      require(second.tooltipHovered&&tips.tooltipShown&&tips.tooltipTarget===second&&tips.tooltipText==="Silence Notifications","actual MouseArea and original 400ms tooltip host");
      dndProvider.writable=false;input.wait(150);
      require(second.enabled&&!second.pressable&&second.tooltipHovered&&tips.tooltipShown,"busy/blocked fences presses, not hover descriptions");
      input.mouseClick(second,second.width/2,second.height/2,Qt.LeftButton);input.wait(30);
      require(dndProvider.writes===0,"busy/blocked input never issues or queues action");
      dndProvider.writable=true;input.mouseClick(second,second.width/2,second.height/2,Qt.LeftButton);input.wait(200);
      require(dndProvider.writes===1&&dndProvider.doNotDisturb,"actual frame click dispatches original handler once to synthetic provider");
      require(point(second).x===q.x&&button("Dnd")===second,"click does not retarget the pointer");
      // Original press hides its tooltip. Re-enter, then change observed state
      // without moving the pointer to prove description updates on the same item.
      input.mouseMove(surface.contentItem,760,60);input.wait(30);
      input.mouseMove(second,second.width/2,second.height/2);input.wait(550);
      require(tips.tooltipShown&&tips.tooltipText==="Allow Notifications","active original DND action description");
      dndProvider.doNotDisturb=false;input.wait(50);
      require(tips.tooltipShown&&tips.tooltipText==="Silence Notifications","hovered description follows observed state without another enter");
      input.mouseMove(first,first.width/2,first.height/2);input.wait(50);
      require(tips.tooltipShown&&tips.tooltipTarget===first&&tips.tooltipText==="Day Light","original warm cross-control handoff");
      night.active=false;input.wait(50);require(tips.tooltipText==="Night Light","both original nightlight descriptions admitted");
      input.mouseMove(surface.contentItem,760,60);input.wait(150);require(!tips.tooltipShown,"pointer leave closes original tooltip");
    }
    require(editor.writes===0,"interaction never changes persisted layout");
    console.log("OMABUNTU_BAR_FRAME_OK::"+mode);Qt.callLater(function(){Qt.quit();});
  }
}
''' % name
