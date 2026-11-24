"""Actual original monitor controls; legacy fixture command name is retained.

The rejected profile page is no longer instantiated. All native actions below
use a contained fake CLI and private fixture state, never a real compositor.
"""
from pathlib import Path
import argparse
import check_desktop_panels as desktop

HELPER = '''#!/usr/bin/python3
import json,sys
from pathlib import Path
p=Path('/home/probe/display-controls-fixture.json')
s=json.loads(p.read_text()) if p.exists() else dict(displays=[dict(name='DP-1',width=1920,height=1080,x=0,y=0,scale=1,disabled=False,focused=True),dict(name='DP-2',width=1920,height=1080,x=3000,y=0,scale=1,disabled=False,focused=False)],backlight=dict(percent=70),fixture_writes=[])
a=sys.argv[1:];op=a[0]
key=str(len(s['fixture_writes'])).zfill(64)
if op=='toggle':
 if a[3]!=key:raise ValueError('stale observation')
 m=next(m for m in s['displays'] if m['name']==a[1]);enabled=not m['disabled']
 if enabled!=(a[2]=='true'):raise ValueError('stale row')
 if enabled and sum(not d['disabled'] for d in s['displays'])<=1:raise ValueError('last active')
 m['disabled']=enabled
elif op=='text':
 text=Path('/home/probe/.local/state/omabuntu/current/text-size.txt');text.parent.mkdir(parents=True,exist_ok=True);text.write_text(a[1]+'\\n')
elif op=='scale':next(m for m in s['displays'] if m['name']==a[1])['scale']=float(a[2])
elif op=='brightness':s['backlight']['percent']=int(a[1])
elif op!='status':raise ValueError('unknown action')
if op!='status':s['fixture_writes'].append(op);p.write_text(json.dumps(s))
s['control_key']=str(len(s['fixture_writes'])).zfill(64)
print(json.dumps(s))
'''

PROBE = '''import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons as Commons
ShellRoot {
 id:test
 property var view:null
 property int phase:0
 property int ticks:0
 Window {id:surface;visible:true;width:700;height:1200}
 QtObject {
  id:bar
  property bool vertical:false
  property string position:"top"
  property int barSize:26
  property color foreground:"#cccccc"
  property color barForeground:foreground
  property color background:"#101315"
  property color urgent:"#ee8888"
  property string fontFamily:"JetBrainsMono Nerd Font"
  property bool foregroundAnimationEnabled:false
  function registerClickTarget(target){}
  function unregisterClickTarget(target){}
  function showTooltip(item,text){}
  function hideTooltip(item){}
  function requestPopout(owner){}
  function releasePopout(owner){}
 }
 function require(ok,message){if(!ok)throw Error(message)}
 function find(item,pred){if(pred(item))return item;var list=item.children||[];for(var i=0;i<list.length;i++){var o=find(list[i],pred);if(o)return o}return null}
 function row(name){return find(view,function(i){return i.rowIndex!==undefined&&i.display&&i.display.name===name})}
 function writes(){return view.lastState.fixture_writes}
 Timer {interval:30;repeat:true;running:true;onTriggered:{try{
  require(++test.ticks<300,'bounded actual QML fixture')
  if(test.phase===0){
   var c=Qt.createComponent('DisplayControlView.qml',Component.PreferSynchronous);require(c.status===Component.Ready,c.errorString())
   test.view=c.createObject(surface.contentItem,{bar:bar,helper:'/probe/helpers/display_backend.py'});c.destroy();require(test.view,'original control view constructed')
   test.view.opened=true;require(test.view.panelWindow.ensureContent(),'original popup constructed');test.phase=1;return
  }
  if(test.view.controlsBusy||!test.view.lastState)return
  if(test.phase===1){
   require(writes().length===0,'opening and polling issue no setters')
   require(!find(view,function(i){return i.text==='Monitor profiles'||i.text==='Back to display'||i.text==='Back'||i.text==='MONITOR PROFILES'}),'no authored profile navigation or heading')
   require(view.visibleSections.join(',')==='brightness,textsize,scale,monitors','all original sections remain')
   require(view.lastState.displays[1].x===3000&&!view.errorText,'existing gap is not rejected')
   var r=row('DP-2');require(r&&r.canToggle,'original enabled monitor row is actionable')
   view.request('status',[]);require(!view.controlsBusy&&r.canToggle,'read-only refresh does not dim rows or consume the click')
   var area=find(r,function(i){return i.containsMouse!==undefined&&i.clicked!==undefined});require(area,'original monitor mouse surface');area.clicked(null);test.phase=2;return
  }
  if(test.phase===2){
   require(writes().join(',')==='toggle'&&!view.displays[1].enabled,'pointer routes to actual output toggle, not navigation')
   require(!row('DP-1').canToggle&&row('DP-2').canToggle,'last active output is dimmed, disabled output can be enabled')
   view.focusSection='monitors';view.selectedIndex=0;view.activateCursor();require(!view.controlsBusy,'last-output keyboard activation is a no-op')
   view.selectedIndex=1;view.activateCursor();test.phase=3;return
  }
  if(test.phase===3){
   require(writes().join(',')==='toggle,toggle'&&view.displays[1].enabled,'original keyboard activation restores disabled output')
   var slider=find(view,function(i){return i.maximum===6&&i.tickCount===7&&i.released!==undefined});require(slider,'original text-size slider');slider.released(6);test.phase=4;return
  }
  if(test.phase===4){
   if(Commons.Style.font.baseSize!==20)return
   require(writes().join(',')==='toggle,toggle,text','first file creation refreshes shell text without profiles')
   require(view.displayedTextPx()===20,'original header follows file readback')
   view.focusSection='textsize';view.adjustTextSize(-1);require(view.displayedTextPx()===16,'pending keyboard notch is stable while helper runs');test.phase=5;return
  }
  if(test.phase===5){
   if(Commons.Style.font.baseSize!==16)return
   var pill=find(view,function(i){return i.scaleValue==='2'&&i.clicked!==undefined});require(pill,'original scale pill');pill.clicked();test.phase=6;return
  }
  if(test.phase===6){
   require(view.monitorScale==='2','original scale action read back')
   view.wheel(120);test.phase=7;return
  }
  if(test.phase===7){
   require(view.brightnessPercent===75,'original wheel brightness control retained')
   require(writes().join(',')==='toggle,toggle,text,text,scale,brightness','only explicit fixture gestures mutated state')
   require(view.lastState.displays[1].x===3000,'no layout normalization or profile apply')
   view.toggleDisplay('DP-2',false);require(view.errorText!==''&&!view.controlsBusy,'stale row is refused locally')
   view.close();view.opened=true;test.phase=8;return
  }
  if(test.phase===8){
   if(view.errorText)return
   require(writes().length===6&&!view.errorText,'reopening refreshes without a native action')
   require(view.panelWindow.loadedContent.implicitHeight>0,'real-window popup content has measured extent')
   require(!find(view,function(i){return i.text==='Monitor profiles'||i.text==='Back'}),'reopening never restores the rejected page')
   console.log('OMABUNTU_ORIGINAL_MONITOR_CONTROLS_OK');Qt.callLater(function(){Qt.quit()})
  }
 }catch(error){console.error('DESKTOP_COMPILE_FAILED: '+error);Qt.exit(42)}}}
}
'''


def run(build):
    return desktop.run(Path(__file__).resolve().parents[1], build, probe=PROBE,
                       extra_files={'helpers/display_backend.py': (HELPER, 0o500)},
                       markers=('OMABUNTU_ORIGINAL_MONITOR_CONTROLS_OK',))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.build_dir))
