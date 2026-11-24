"""Actual original monitor popup/profile controls with a synthetic stdio backend."""
from pathlib import Path
import argparse
import check_desktop_panels as desktop

HELPER='''#!/usr/bin/python3
import json,sys,time
from pathlib import Path
if sys.argv[1]=='watch':
 while True:time.sleep(1)
p=Path('/home/probe/profiles-fixture.json')
profile=dict(schema_version=1,name='Fixture',text_size=12,outputs=[dict(identity=dict(connector='DP-1',make='Synthetic',model='Panel',serial='one'),enabled=True,width=1920,height=1080,refresh=60,scale=1,x=0,y=0,transform=0)])
s=json.loads(p.read_text()) if p.exists() else dict(profiles=[dict(profile,automatic=False,kept=False)],pending=None,text_size=12,inventory=[dict(name='DP-1',serial='one',availableModes=['1920x1080@60.00Hz'])],store_digest='fixture',writes=0)
v=json.loads(sys.stdin.readline());op=v['op'];result=None
if op=='capture':profile['name']=v['name'];result=dict(profile=profile)
if op=='save':s['profiles']=[dict(v['profile'],automatic=False,kept=False)]
if op=='review':
 profile=s['profiles'][0];result=dict(review=dict(name=profile['name'],target=profile['outputs'],text_size=profile['text_size']),approval='fixture-approval')
if op=='apply':s['pending']=dict(token='a'*32,status='awaiting-confirmation');s['writes']+=1
if op in ('keep','restore'):s['pending']=None;s['profiles'][0]['kept']=op=='keep'
if op=='automatic':s['profiles'][0]['automatic']=v['enabled']
if op=='text':
 s['text_size']=v['value'];text=Path('/home/probe/.local/state/omabuntu/current/text-size.txt');text.parent.mkdir(parents=True,exist_ok=True);text.write_text(str(v['value'])+'\\n')
p.write_text(json.dumps(s));print(json.dumps(dict(result or s,store_digest='fixture')))
'''
PROBE='''import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons as Commons
ShellRoot {
 id:test
 property var owner:null
 property var view:null
 property int phase:0
 property int ticks:0
 Window {id:surface;visible:true;width:700;height:900}
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
 function make(file,props){var c=Qt.createComponent(file,Component.PreferSynchronous);require(c.status===Component.Ready,c.errorString());var o=c.createObject(null,props);c.destroy();require(o!==null,'construct '+file);return o}
 function find(item,pred){if(pred(item))return item;var list=item.children||[];for(var i=0;i<list.length;i++){var o=find(list[i],pred);if(o)return o}return null}
 function click(text){var b=find(view,function(i){return i.text===text&&i.clicked!==undefined&&i.visible});require(b&&b.enabled,'visible enabled '+text);b.clicked()}
 Timer {interval:30;repeat:true;running:true;onTriggered:{try{
  require(++test.ticks<240,'bounded source QML fixture')
  if(test.phase===0){test.owner=make('DisplayProfilesState.qml',{helper:'/probe/helpers/display_profiles.py'});test.view=make('DisplayControlView.qml',{bar:bar,profiles:test.owner});test.view.parent=surface.contentItem;test.view.opened=true;test.view.panelWindow.ensureContent();test.phase=1;return}
  if(test.owner.busy)return
  if(test.phase===1){
   if(!test.owner.data.store_digest)return
   require(!test.owner.data.pending&&!test.owner.watcher.running,'startup is read-only without automatic consent')
   click('Monitor profiles');require(test.view.profilePage,'original popup opens separate capability page');test.phase=11;return
  }
  if(test.phase===11){click('Fixture');test.phase=2;return}
  if(test.phase===2){
   var input=find(test.view,function(i){return i.objectName==='displayProfile-scale-0'});require(input,'actual original toolkit editor constructed');input.text='1.5';input.editingFinished();require(test.owner.draftDirty&&test.owner.draft.outputs[0].scale===1.5,'editing is draft-only')
   click('Save draft');test.phase=3;return
  }
  if(test.phase===3){click('Review saved profile');test.phase=4;return}
  if(test.phase===4){require(test.owner.review&&!test.owner.data.pending,'review does not apply');click('Apply reviewed layout');test.phase=5;return}
  if(test.phase===5){if(!test.owner.data.pending)return;click('Keep');test.phase=6;return}
  if(test.phase===6){if(test.owner.data.pending)return;require(test.owner.data.profiles[0].kept,'readback-derived acceptance');click('Use at login/hotplug');test.phase=7;return}
  if(test.phase===7){
   require(test.owner.data.profiles[0].automatic,'explicit automation setting admitted');if(!test.owner.watcher.running)return
   click('Stop automatic');test.phase=8;return
  }
  if(test.phase===8){
   require(!test.owner.data.profiles[0].automatic,'explicit automation revocation');if(test.owner.watcher.running)return
   click('Use at login/hotplug');test.phase=10;return
  }
  if(test.phase===10){
   if(!test.owner.watcher.running)return
   require(test.owner.data.profiles[0].automatic,'explicit revocation and re-enable starts a fresh session watcher')
   click('Stop automatic');test.phase=12;return
  }
  if(test.phase===12){if(test.owner.watcher.running)return;test.owner.textSize(20);test.phase=9;return}
  if(test.phase===9){
   if(Commons.Style.font.baseSize!==20)return
   require(Commons.Style.font.body===20,'shell-local text size updates original style tokens by file readback')
   test.view.close();require(!test.view.profilePage,'reopening cannot retain advanced navigation');test.owner.enabled=false
   console.log('OMABUNTU_DISPLAY_PROFILES_OK');Qt.callLater(function(){Qt.quit()})
  }
 }catch(error){console.error('DESKTOP_COMPILE_FAILED: '+error);Qt.exit(42)}}}
}
'''


def run(build):
    return desktop.run(Path(__file__).resolve().parents[1],build,probe=PROBE,
                       extra_files={'helpers/display_profiles.py':(HELPER,0o500)},markers=('OMABUNTU_DISPLAY_PROFILES_OK',))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build-dir',type=Path,required=True);args=parser.parse_args();raise SystemExit(run(args.build_dir))
