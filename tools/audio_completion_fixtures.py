"""Contained real-QML/real-Process audio probes, synthetic owners only."""
import hashlib
import json
from pathlib import Path
import struct
import zlib

CASES = ('native-query', 'native-profile', 'native-failure', 'native-unavailable',
         'native-timeout', 'native-scope', 'native-malformed', 'native-drag', 'native-layout', 'audio-osd', 'media-artwork')

OVERLAY = '''import QtQuick
Item {
  property bool shown:false
  property int shownKeyboardFocus:0
  property var mask:null
  width:800
  height:600
  visible:shown
}
'''


def overlay_surface(data):
    text = data.decode()
    old = '  property OverlayWindow surface: OverlayWindow {\n'
    namespace = '    WlrLayershell.namespace: "omarchy-osd"\n'
    if text.count(old) != 1 or text.count(namespace) != 1:
        raise ValueError('Original OSD surface witnesses changed')
    return text.replace(old, '  property FixtureAudioOverlay surface: FixtureAudioOverlay {\n').replace(namespace, '').encode()


RPC = '''import json,os,sys,time
from pathlib import Path
MODE=__MODE__
p=json.load(sys.stdin)
state=Path(os.environ['XDG_STATE_HOME'])/'synthetic-audio.json'
s=json.loads(state.read_text()) if state.exists() else {'profile':'analog','volume':.5,'pending':False,'history':[]}
op=p['op']
if MODE=='native-scope': time.sleep(.08)
if op=='review-profile':
 result={'review':{'profile':p['profile'],'digest':'d'*64,'notice':'May interrupt calls','before':{'card':{'name':p['card'],'index':7,'serial':'70'}}},'review_key':'e'*64}
elif op=='apply-profile':
 s['profile']=p['review']['profile'];s['history']=[{'id':'20260101T000000000000Z-0123456789ab','status':'applied','profile':s['profile']}]
 result={'status':'profile-observed'}
elif op=='restore-profile':
 s['profile']='analog';s['history'][0]['status']='restored';result={'status':'previous-profile-observed'}
elif op=='volume':
 s['volume']=p['value'];s['pending']=True;state.write_text(json.dumps(s))
 if MODE=='native-drag':
  s['pending']=False;result={'status':'observed'};time.sleep(.08)
 else:
  if MODE=='native-timeout': time.sleep(2)
  print(json.dumps({'ok':False,'error':'command-timeout'}));sys.exit(1)
elif op=='ack-control':
 s['pending']=False;result={'status':'acknowledged','restored':False}
elif op=='history':
 result={'profile_history':s['history'],'control_history':[{'id':'00000001','status':'prepared'}] if s['pending'] or MODE=='native-unavailable' else []}
elif op=='inspect':
 if MODE=='native-unavailable': print(json.dumps({'ok':False,'error':'pactl-unavailable-no-installation-attempted'}));sys.exit(1)
 source={'name':'virtual_input.fixture','serial':'153','volume':s['volume'],'muted':False}
 result={'key':'a'*64,'sources':[source],'sinks':[],'default_source':source['name'],'default_sink':'alsa_output.fixture',
 'cards':[{'index':7,'name':'alsa_card.fixture','serial':'70','active_profile':s['profile'],'profiles':{
 'analog':{'description':'Analog duplex','sinks':1,'sources':1,'priority':100,'available':True},
 'hdmi':{'description':'HDMI duplex','sinks':1,'sources':1,'priority':90,'available':True}}}],
 'partial':False,'blocked':s['pending'],'profile_blocked':False,'profile_history':s['history'],
 'control_history':[{'id':'00000001','status':'prepared'}] if s['pending'] else []}
else: raise SystemExit(2)
if MODE=='native-malformed' and op=='inspect': result['cards'][0]['profiles']['hdmi']['priority']='bad'
state.write_text(json.dumps(s))
print(json.dumps({'ok':True,'scope':p['scope'],'result':result}))
'''

EVENTS = '''import signal
print('ready',flush=True)
while True: signal.pause()
'''

ART = '''import json,os,sys,time
from pathlib import Path
p=json.load(sys.stdin);time.sleep(.04)
source=next((Path(os.environ['XDG_CACHE_HOME'])/'omabuntu/audio-art').glob('*.png'))
print(json.dumps({'ok':True,'key':p['key'],'source':source.as_uri()}))
'''


def prepare(case, name):
    """Write only into the already-created disposable fixture case."""
    case = Path(case)
    (case / 'probe/FixtureAudioOverlay.qml').write_text(OVERLAY)
    if name not in CASES:
        return
    (case / 'probe/FixtureUntypedInput.qml').write_text('''import QtQml
QtObject {
  property int id:4
  property string name:"virtual_input.fixture"
  property string description:"Virtual microphone"
  property bool ready:true
  property bool isSink:false
  property bool isStream:false
  property var audio:null
  property var properties:({"object.serial":"153"})
}
''')
    helper = case / 'probe/helpers'; helper.mkdir(mode=0o700)
    for filename, source in (('audio_controls.py', RPC.replace('__MODE__', json.dumps(name))),
                             ('audio_events.py', EVENTS), ('audio_artwork.py', ART)):
        (helper / filename).write_text(source)
    if name == 'media-artwork':
        def chunk(kind, data):
            return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
        data = (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))
                +chunk(b'IDAT',zlib.compress(b'\0\xff\xff\xff'))+chunk(b'IEND',b''))
        directory = case / 'home/cache/omabuntu/audio-art'; directory.mkdir(parents=True,mode=0o700)
        (directory / (hashlib.sha256(data).hexdigest()+'.png')).write_bytes(data)


def fixture(name):
    if name not in CASES:
        raise ValueError('Unknown audio completion fixture')
    return '''//@ pragma IgnoreSystemSettings
import QtQuick
import QtQuick.Controls
import QtQuick.Window
import Quickshell
import "FixtureMpris"
import "FixturePipewire"
import qs.Commons as Commons
ShellRoot {
  id:test
  property string mode:__MODE__
  property var bridge:null
  property var host:null
  property var view:null
  property var feedback:null
  property var osd:null
  property var art:null
  property bool finished:false
  property int phase:0
  property int ticks:0
  property string oldScope:""
  Window { id:layoutWindow; visible:test.mode === "native-layout"; width:800; height:800 }
  function require(value,message){if(!value)throw new Error(message)}
  function make(file,properties){
    var c=Qt.createComponent(file,Component.PreferSynchronous)
    require(c.status===Component.Ready,c.errorString())
    var object=c.createObject(null,properties||{});c.destroy();require(object!==null,"create "+file);return object
  }
  function find(item,predicate){
    if(predicate(item))return item
    var children=item.children||[]
    for(var i=0;i<children.length;i++){var found=find(children[i],predicate);if(found)return found}
    return null
  }
  function done(){
    if(finished)return
    finished=true
    if(bridge)bridge.revoke()
    if(art)art.enabled=false
    console.log("OMABUNTU_AUDIO_FIXTURE_OK::"+mode);Qt.callLater(function(){Qt.quit()})
  }
  Timer {interval:25;repeat:true;running:true;onTriggered:{
    try {
      if(test.finished)return
      test.ticks++;require(test.ticks<160,"bounded completion fixture")
      if(test.phase===0){
        if(test.mode==="audio-osd"){
          test.feedback=make("AudioFeedback.qml")
          test.osd=make("AudioOsdView.qml",{feedback:test.feedback})
          var row={id:1,serial:"153",control:{generation:1},volume:.5,muted:false,controlAvailable:true}
          test.feedback.observe("output",row);require(!test.osd.opened,"initial observation has no OSD")
          test.feedback.observe("output",Object.assign({},row,{volume:.6}))
          require(test.osd.opened&&test.osd.value===60&&test.osd.hasProgress,"original observed-volume OSD")
          test.feedback.observe("output",Object.assign({},row,{volume:1.5}))
          require(test.osd.value===100&&test.osd.message==="150%","boosted observation keeps truthful readout and original bounded progress")
          test.feedback.observe("input",row)
          test.feedback.observe("input",Object.assign({},row,{muted:true}))
          require(test.osd.iconKey==="microphone-muted"&&test.osd.value===0,"observed microphone OSD")
          test.feedback.media("next","<b>Fixture</b>")
          require(test.osd.mediaOsd&&!test.osd.hasProgress&&test.osd.message.indexOf("requested")>=0,"media issuance is not acceptance")
          test.feedback.enabled=false;require(!test.osd.opened,"disable closes transient overlay");done();return
        }
        test.host=make("PortTrayHost.qml")
        if(test.mode==="media-artwork"){
          test.art=make("MediaArtwork.qml",{menuHelper:"/probe/helpers/menu_model.py",enabled:true,url:"file:///synthetic-cover.png",identity:"first"})
          Commons.MediaSelection.artwork=test.art
          var player=make("FixtureMediaPlayer.qml",{dbusName:"org.mpris.MediaPlayer2.fixture",identity:"Fixture",isPlaying:true})
          Mpris.players={values:[player]}
          test.view=make("MediaControlView.qml",{bar:test.host.ownerApi});test.view.popupOpen=true
          test.phase=1;return
        }
        test.bridge=make("AudioNativeState.qml",{enabled:false,menuHelper:"/probe/helpers/menu_model.py"})
        require(!test.bridge.granted&&!test.bridge.rpc.running&&!test.bridge.events.running,"no startup query, setter or subscription")
        test.bridge.enabled=true
        if(test.mode==="native-layout"){
          var nodes=[]
          for(var n=0;n<12;n++)nodes.push({id:n+1,name:"fixture_"+(n<8?"output_":"input_")+n,
            isSink:n<8,isStream:false,ready:true,properties:{"object.serial":String(n+100),"node.description":"Fixture device "+n},
            audio:{volume:.5,muted:false}})
          Pipewire.nodes={values:nodes};Pipewire.defaultAudioSink=nodes[0];Pipewire.defaultAudioSource=nodes[8]
          var provider=make("AudioOutputProvider.qml",{bridge:test.bridge})
          test.view=make("AudioOutputView.qml",{bar:test.host.ownerApi,backend:provider})
          test.view.parent=layoutWindow.contentItem
          test.view.open();test.view.panelWindow.ensureContent();test.phase=30;return
        }
        require(test.bridge.grantQueries(),"explicit query/risk grant")
        if(test.mode==="native-scope"){
          test.oldScope=test.bridge.scope;test.bridge.revoke();test.phase=10;return
        }
        test.phase=1;return
      }
      if(test.mode==="media-artwork"){
        if(test.phase===1){
          if(!test.art.source)return
          var image=find(test.view,function(item){return item.crop===true&&item.url!==undefined})
          require(image&&String(image.url)===test.art.source,"original SizedImage consumes admitted cache URL")
          if(image.status!==Image.Ready)return
          test.art.identity="replacement";test.art.url="file:///replacement.png"
          test.art.url="https://invalid.example/never-fetched.png";test.phase=2;return
        }
        if(test.art.rpc.running||test.art.again)return
        require(test.art.source==="","late old artwork and remote URL stay absent");done();return
      }
      if(test.mode==="native-layout"){
        var normal=find(test.view,function(item){return item.objectName==="audioNormalPage"})
        var scroll=test.view.panelWindow.loadedContent.scrollArea
        if(test.phase===30){
          require(normal&&normal.visible&&!test.view.advancedAudio,"normal original page is the default")
          require(test.view.displayAudioSinks.length===8&&test.view.displayAudioSources.length===4,"populated original device layout includes more rows than the reported setup")
          require(test.view.panelWindow.contentHeight>560&&scroll.contentHeight<=scroll.availableHeight+.5,"normal panel grows beyond the old cap and fits populated content: "+JSON.stringify({panel:test.view.panelWindow.contentHeight,normal:normal.height,content:scroll.contentHeight,height:scroll.height,available:scroll.availableHeight}))
          var nav=find(test.view,function(item){return item.objectName==="audioAdvancedNavigation"})
          require(nav&&!nav.visible&&!nav.enabled,"Advanced audio navigation is hidden and disabled")
          require(scroll.leftPadding===0&&scroll.rightPadding===0&&Math.abs(normal.width-scroll.width)<.5,"nonoverflow content has no asymmetric reserved space")
          require(!test.view.advancedAudioAvailable&&test.view.profileControls.actions.length===0,"disabled capability exposes no cursor or invocation rows")
          var title=find(test.view,function(item){return item.text==="DEVICE PROFILES AND VIRTUAL INPUTS"})
          require(title&&!title.visible,"technical block is hidden on ordinary page")
          test.view.focusSection="profiles";test.view.selectedIndex=0;test.view.cursorActive=true;test.view.activateCursor()
          require(!test.view.advancedAudio&&normal.visible&&test.view.visibleSections.indexOf("profiles")<0,"disabled page cannot be reached through the keyboard cursor")
          test.view.advancedAudio=true
          require(!test.view.advancedAudio&&normal.visible,"forced legacy page selection is refused")
          require(!test.view.profileControls.activate(0)&&!test.view.profileControls.invoke({enabled:true,op:"query"}),"disabled actions and stale rows cannot invoke queries")
          require(!test.bridge.granted&&!test.bridge.rpc.running&&!test.bridge.events.running,"disabled page never grants or starts optional audio access")
          test.view.clampCursor();require(test.view.focusSection!=="profiles","normal cursor excludes the disabled page")
          scroll.anchors.fill=null;scroll.width=340;scroll.height=120;test.phase=31;return
        }
        if(test.phase===31){
          var scrollbar=scroll.ScrollBar.vertical
          require(scrollbar.visible,"forced original overflow exposes vertical scrollbar: "+JSON.stringify({height:scroll.height,content:scroll.contentHeight,normal:normal.height,padding:scroll.rightPadding,size:scrollbar.size}))
          var right=normal.mapToItem(scroll,normal.width,0).x
          var left=scrollbar.mapToItem(scroll,0,0).x
          require(left-right>=Commons.Style.space(10)-.5,"measured content-to-scrollbar gap is theme-scaled, not an overlay")
          require(scroll.ScrollBar.horizontal.policy===ScrollBar.AlwaysOff,"horizontal bar remains disabled")
          require(scroll.leftPadding===scroll.rightPadding,"overflow clearance remains centered while scrollbar fades")
          require(scroll.contentHeight>scroll.height&&scroll.contentItem.contentHeight===scroll.contentHeight,"nested page declares a real flickable extent")
          scroll.contentItem.contentY=scroll.contentHeight-scroll.availableHeight
          test.phase=32;return
        }
        if(test.phase===32){
          var last=find(test.view,function(item){return item.node&&item.node.name==="fixture_input_11"&&item.rowIndex===3})
          require(last,"last original input row exists")
          var bottom=last.mapToItem(scroll,0,last.height).y
          require(bottom<=scroll.height+.5&&bottom-last.height>=-.5,"constrained fallback scroll reaches the entire last original row")
          scroll.height=2000;test.phase=33;return
        }
        require(!scroll.ScrollBar.vertical.visible&&scroll.leftPadding===0&&scroll.rightPadding===0,"nonoverflow returns the full content width")
        test.view.close();test.view.open()
        require(!test.view.advancedAudio&&!test.bridge.granted&&test.view.profileControls.actions.length===0,"reopen keeps Advanced audio disabled without granting backend access")
        done();return
      }
      if(test.mode==="native-scope"){
        if(test.phase===10){
          if(test.bridge.inFlight||test.bridge.rpc.running)return
          require(test.bridge.scope!==test.oldScope&&!test.bridge.granted&&!test.bridge.snapshot,"old-scope reply is rejected")
          test.bridge.grantQueries();test.phase=11;return
        }
        if(!test.bridge.writable)return
        require(test.bridge.scope!==test.oldScope,"new query gets current scope");done();return
      }
      if(test.mode==="native-malformed"){
        if(test.bridge.busy||test.bridge.errorText.indexOf("invalid-audio-observation")<0)return
        require(!test.bridge.known&&!test.bridge.writable,"malformed nested capabilities revoke instead of reaching delegates")
        done();return
      }
      if(test.mode==="native-unavailable"){
        if(test.bridge.busy||test.bridge.recovery.control_history.length!==1)return
        require(!test.bridge.known&&test.bridge.errorText.indexOf("pactl-unavailable")>=0,"missing dependency is reported and history remains readable")
        done();return
      }
      if(test.phase===1){
        if(!test.bridge.writable)return
        var input=make("FixtureUntypedInput.qml")
        Pipewire.nodes={values:[input]};Pipewire.defaultAudioSource=input
        var provider=make("AudioOutputProvider.qml",{bridge:test.bridge})
        test.view=make("AudioOutputView.qml",{bar:test.host.ownerApi,backend:provider})
        test.view.open();require(test.view.panelWindow.ensureContent()!==null,"actual original audio content loads")
        require(test.view.source&&test.view.source.untyped&&!test.view.inputLevelShown,"actual provider admits proved virtual input without inventing a peak meter")
        require(!provider.inputPeakMonitor.enabled,"untyped input never activates capture monitoring")
        require(test.view.profileControls&&test.view.profileControls.actions.length===0&&!test.view.profileControls.visible,"Advanced audio remains disabled even with a synthetic bridge grant")
        require(test.view.visibleSections.indexOf("profiles")<0,"disabled profiles never join the original cursor model")
        if(test.mode==="native-query"){
          var second=make("AudioPanelController.qml",{bar:test.host.ownerApi,backend:provider})
          second.open();test.view.close();require(provider.monitoring,"one closing panel cannot stop another panel's monitor")
          second.close();require(!provider.monitoring,"last owner releases monitoring")
          var oldInput=test.view.source
          var replacement=make("FixtureUntypedInput.qml")
          Pipewire.nodes={values:[replacement]};Pipewire.defaultAudioSource=replacement
          require(!provider.setSourceVolume(oldInput,.9)&&!test.bridge.inFlight,"recycled native node rejects stale virtual-source setter")
          test.view.focusSection="profiles";test.view.selectedIndex=0;test.view.cursorActive=true
          var before=JSON.stringify(test.bridge.snapshot.cards)
          test.view.adjustVolume(.05)
          require(JSON.stringify(test.bridge.snapshot.cards)===before,"h/l cannot switch profiles")
          test.bridge.revoke();require(!test.view.profileControls.invoke({enabled:true,op:"query"}),"disabled legacy scope action refused")
          done();return
        }
        if(test.mode==="native-drag"){
          var slider=find(test.view,function(item){return item.maximum===1&&item.enabled&&item.value===.5&&item.dragging!==undefined})
          require(slider,"original virtual-input slider exists")
          slider.dragging=true;slider.liveValue=.2;slider.moved(.2);slider.liveValue=.7;slider.moved(.7)
          require(!test.bridge.inFlight&&test.view.dragSourceTarget,"intermediate moves retain captured intent without RPCs")
          slider.dragging=false;slider.released(.7)
          require(test.bridge.inFlight&&test.bridge.inFlight.value===.7,"release issues only final captured value")
          require(test.view.source&&test.view.source.volume===.5&&!test.view.inputWriteAvailable,"pending keeps last observation and independently fences writes")
          test.bridge.invalidate()
          require(test.view.source&&test.view.source.volume===.5&&!provider.setSourceVolume(test.view.source,.9),"local event invalidation retains only observed presentation behind the write fence")
          test.phase=20;return
        }
        if(test.mode==="native-profile"){
          // Backend recovery coverage only; the deployed UI stays disabled.
          require(test.bridge.reviewProfile("alsa_card.fixture","hdmi"),"explicit synthetic backend-only profile review")
          test.phase=2;return
        }
        if(test.mode==="native-timeout")test.bridge.deadline.interval=200
        require(test.view.backend.setSourceVolume(test.view.source,.25),"original provider issues explicit proof-bound virtual gain request")
        test.phase=2;return
      }
      if(test.mode==="native-drag"){
        if(!test.bridge.writable)return
        require(test.view.source.volume===.7,"fresh observation confirms final drag value")
        var slider=find(test.view,function(item){return item.maximum===1&&item.enabled&&item.value===.7&&item.dragging!==undefined})
        require(slider,"same original slider readmits observed state")
        slider.dragging=true;slider.liveValue=.9;slider.moved(.9);test.view.close()
        require(!slider.dragging&&!test.view.dragSourceTarget&&!test.bridge.inFlight,"close cancels gesture without setter")
        slider.released(.9);require(!test.bridge.inFlight,"late release cannot retarget current source")
        test.view.open();slider.dragging=true;slider.liveValue=.8;slider.moved(.8)
        var replacement=make("FixtureUntypedInput.qml")
        Pipewire.nodes={values:[replacement]};Pipewire.defaultAudioSource=replacement
        require(!slider.dragging&&!test.view.dragSourceTarget,"replacement cancels captured gesture")
        slider.released(.8);require(!test.bridge.inFlight,"replacement receives no delayed gain request")
        done();return
      }
      if(test.mode==="native-profile"){
        if(test.phase===2){
          if(!test.bridge.pendingReview||test.bridge.busy)return
          require(test.bridge.snapshot.cards[0].active_profile==="analog","review does not change native profile")
          require(test.view.profileControls.actions.length===0,"backend approval cannot re-enable the disabled UI")
          require(test.bridge.applyProfile(),"explicit synthetic backend-only apply")
          test.phase=3;return
        }
        if(test.phase===3){
          if(!test.bridge.writable||test.bridge.snapshot.cards[0].active_profile!=="hdmi")return
          require(test.bridge.restoreProfile(test.bridge.recovery.profile_history[0].id),"explicit profile-only recovery")
          test.phase=4;return
        }
        if(!test.bridge.writable||test.bridge.snapshot.cards[0].active_profile!=="analog")return
        require(test.bridge.recovery.profile_history[0].status==="restored","observed profile recovery");done();return
      }
      if(test.mode==="native-timeout"&&test.phase===2){
        if(test.bridge.inFlight||test.bridge.rpc.running)return
        require(test.bridge.errorText.indexOf("timed out")>=0&&!test.bridge.snapshot,"watchdog revokes rather than fabricating success")
        test.bridge.deadline.interval=75000;test.bridge.grantQueries();test.phase=3;return
      }
      if(test.phase===2||test.phase===3){
        if(!test.bridge.known||test.bridge.busy)return
        require(!test.bridge.writable&&test.bridge.snapshot.blocked,"uncertainty fences writes")
        require(test.bridge.recovery.control_history[0].status==="prepared","prepared evidence survives")
        if(test.mode==="native-timeout"){done();return}
        require(test.bridge.acknowledgeControl("00000001"),"separate explicit acknowledgement")
        test.phase=4;return
      }
      if(test.phase===4){
        if(!test.bridge.writable)return
        require(test.bridge.snapshot.sources[0].volume===.25,"ack does not restore or replay gain")
        done();return
      }
    }catch(error){console.error("OMABUNTU_AUDIO_ASSERT "+error);Qt.exit(42)}
  }}
}
'''.replace('__MODE__',json.dumps(name))
