"""Fixed audio-output probes with fake nodes, never native PipeWire."""
import re

CASES = ("no-output", "glyphs", "controls", "selection", "bounds", "churn", "navigation",
         "streams", "stream-guards", "stream-navigation", "stream-drag",
         "master-mixed", "master-single", "master-guards", "master-partial",
         "media-labels", "media-selection", "media-idle", "media-churn",
         "media-transport", "media-guards", "media-widget", "media-widget-churn",
         "route-direct", "route-dsp", "route-churn", "route-unknown",
         "input-direct", "input-churn", "input-guards", "input-uncertain", "negative")

MPRIS_SINGLETON = '''pragma Singleton
import QtQml
QtObject { property var players: ({values:[]}) }
'''
PIPEWIRE_SINGLETON = '''pragma Singleton
import QtQml
QtObject {
  property var nodes: ({values:[]})
  property bool ready: true
  property var linkGroups: ({values:[]})
  property var defaultAudioSink: null
  property var defaultAudioSource: null
  property var preferredDefaultAudioSink: null
  property var preferredDefaultAudioSource: null
}
'''

MEDIA_PLAYER = '''import QtQml
QtObject {
  property string dbusName: ""
  property string identity: ""
  property string desktopEntry: ""
  property string trackTitle: "Fixture track"
  property string trackArtist: "Fixture artist"
  property string trackAlbum: "Fixture album"
  property string trackArtUrl: ""
  property bool isPlaying: false
  property bool canControl: true
  property bool canPlay: true
  property bool canPause: true
  property bool canTogglePlaying: true
  property bool canGoNext: true
  property bool canGoPrevious: true
  property bool allowCommands: false
  property bool failCommands: false
  property int attempts: 0
  property int plays: 0
  property int pauses: 0
  property int toggles: 0
  property int nexts: 0
  property int previouses: 0
  function send() {
    if (!allowCommands) throw new Error("Unexpected playback mutation");
    attempts++;
    if (failCommands) throw new Error("Fixture uncertain native request");
  }
  function play() {send();plays++;isPlaying=true;}
  function pause() {send();pauses++;isPlaying=false;}
  function togglePlaying() {send();toggles++;isPlaying=!isPlaying;}
  function next() {send();nexts++;}
  function previous() {send();previouses++;}
}
'''

# Only popup ownership is synthetic; the original media widget/popup content runs.
MEDIA_POPUP_SURFACE = '''import QtQuick
Item {
  id: root
  default property alias contentItem: contentHolder.children
  property Item anchorItem: null
  property QtObject bar: null
  property var owner: null
  property bool open: false
  property bool centerOnBar: false
  property int contentWidth: 320
  property int contentHeight: 200
  width: contentWidth
  height: contentHeight
  visible: open
  function fittedContentWidth(value) {return Math.min(800,value);}
  function fittedContentHeight(value,cap) {return Math.min(cap,value+28);}
  onOpenChanged: {
    if (open) bar.requestPopout(owner);
    else if (bar) bar.releasePopout(owner);
  }
  property Item holder: Item {id:contentHolder;parent:root;anchors.fill:parent;anchors.margins:14}
}
'''

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
import "FixtureMpris"
import "FixturePipewire"
import qs.Commons as Commons
ShellRoot {
  id: test
  property var nodes: []
  property var owner: null
  property var view: null
  property int writes: 0
  property var current: null
  property var currentSource: null
  property var mediaOwner: null
  function require(value, message) { if (!value) throw new Error(message); }
  function makePlayer(key, label, playing) {
    var component=Qt.createComponent("FixtureMediaPlayer.qml",Component.PreferSynchronous);
    require(component.status===Component.Ready,component.errorString());
    var player=component.createObject(test);component.destroy();
    player.dbusName=key;player.identity=label;player.desktopEntry=label.toLowerCase();player.isPlaying=playing;
    return player;
  }
  function graph(nodes, links, selected, source) {
    Pipewire.nodes={values:nodes};Pipewire.linkGroups={values:links};
    Pipewire.defaultAudioSink=selected;Pipewire.defaultAudioSource=source;
  }
  function findItem(item, test) {
    if (test(item)) return item;
    var children = item.children || [];
    for (var i = 0; i < children.length; i++) {
      var found = findItem(children[i], test);
      if (found) return found;
    }
    return null;
  }
  QtObject {
    id: backend
    property var state: Presentation.snapshot(false,[],null)
    property var streamState: Presentation.streamSnapshot(false,[])
    readonly property var mediaState: test.mediaOwner ? test.mediaOwner.state : null
    property var inputState: Presentation.inputSnapshot(false,[],null)
    property real peak: 0
    property bool monitoring: false
    function sync() {
      state = Presentation.snapshot(true,test.nodes,test.current);
      inputState = Presentation.inputSnapshot(true,test.nodes,test.currentSource);
      streamState = Presentation.streamSnapshot(true,test.nodes,mediaState);
    }
    function setStreamVolume(key,value) { var ok=Actions.setStreamVolume(test.nodes,key,value); if(ok)test.writes++;sync();return ok; }
    function toggleStreamMute(key) { var ok=Actions.toggleStreamMute(test.nodes,key); if(ok)test.writes++;sync();return ok; }
    function setVolume(key,value) { var ok=Actions.setVolume(test.nodes,key,value); if(ok) test.writes++; sync(); return ok; }
    function toggleMute(key) { var ok=Actions.toggleMute(test.nodes,key); if(ok) test.writes++; sync(); return ok; }
    function toggleAllMuted(outputKey,inputKey) {
      if(!Actions.masterDefaultMatches(outputKey,test.current) || !Actions.masterDefaultMatches(inputKey,test.currentSource))return false;
      var ok=Actions.toggleAllMuted(test.nodes,test.nodes,outputKey,inputKey);if(ok)test.writes++;sync();return ok;
    }
    function toggleSourceMute(key) {var ok=Actions.toggleSourceMute(test.nodes,key);if(ok)test.writes++;sync();return ok;}
    function chooseOutput(key) { var node=Actions.resolve(test.nodes,key); if(!node)return false; test.current=node;test.writes++;sync();return true; }
  }
  Timer { interval: 200; running: true; onTriggered: {
    try {
      var mode="%s";
      var a={id:1,name:"fixture-a",description:"Built-in Audio Analog Stereo Output",ready:true,isSink:true,isStream:false,audio:{volume:0.42,muted:false}};
      var b={id:2,name:"fixture-b",description:"HDMI Display",ready:true,isSink:true,isStream:false,audio:{volume:0.6,muted:false}};
      a.properties={"object.serial":"11"};b.properties={"object.serial":"12"};
      var mic={id:4,name:"fixture-microphone",ready:true,isSink:false,isStream:false,
        properties:{"object.serial":"14"},audio:{volume:0.3,muted:true}};
      var stream={id:3,name:"fixture-player",description:"Fixture Player",ready:true,isSink:true,isStream:true,
        properties:{"object.serial":"1001","application.name":"Fixture Player"},audio:{volume:0.4,muted:false}};
      test.nodes=mode === "no-output" ? [] : [a,b];
      if(mode.indexOf("stream")===0 || mode.indexOf("media-")===0)test.nodes=test.nodes.concat([stream]);
      if(mode.indexOf("master-")===0){test.nodes=test.nodes.concat([mic,stream]);test.currentSource=mic;}
      test.current=mode === "no-output" ? null : a;backend.sync();
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
        catcher.activateRequested();require(writes===2 && a.audio.muted,"header master mute with only output present");
        catcher.closeRequested();require(!view.opened && view.displayAudioSinks.length===0,"escape clears delegates");
      }
      if(mode.indexOf("media-")===0) {
        mediaOwner=Commons.MediaSelection;
        require(mediaOwner!==null,"original read-only shared media owner constructs");
        Pipewire.nodes={values:test.nodes};Pipewire.defaultAudioSink=a;
        var spotify=makePlayer("org.mpris.MediaPlayer2.spotify","Spotify",true);
        var browser=makePlayer("org.mpris.MediaPlayer2.browser","Browser",true);
        var proxy=makePlayer("org.mpris.MediaPlayer2.playerctld","Proxy",true);
        stream.properties["application.name"]="Spotify";
        Mpris.players={values:[browser,spotify,proxy]};backend.sync();view.opened=true;
        require(mediaOwner.activePlayer===spotify,"matching playback stream wins before older unrelated player " + JSON.stringify({active:mediaOwner.activePlayer ? mediaOwner.activePlayer.identity : "",count:mediaOwner.players.length,match:mediaOwner.playerHasPlaybackStream(spotify),array:Array.isArray(mediaOwner.playbackStreams),props:mediaOwner.playbackStreams.length ? mediaOwner.playbackStreams[0].properties : {},order:mediaOwner.playerStartedAt}));
        require(Object.isFrozen(mediaOwner.state) && Object.isFrozen(mediaOwner.state.players) && Object.isFrozen(mediaOwner.state.active),"frozen media projection");
        require(mediaOwner.state.active.play===undefined && mediaOwner.state.active.metadata===undefined && mediaOwner.state.active.trackArtUrl===undefined,"no QObject methods metadata or URLs in projection");
        if(mode==="media-labels") {
          stream.properties["application.name"]="audio-src";
          browser.isPlaying=false;proxy.isPlaying=false;backend.sync();
          require(backend.streamState.streams[0].label==="Spotify" && backend.streamState.streams[0].active,"original unambiguous generic MPRIS label and active mark");
          var streamItem=findItem(view.panelWindow.loadedContent,function(item){return item.streamMuted!==undefined && item.rowIndex===0;});
          require(streamItem!==null && streamItem.isActive,"original StreamRow active visual is wired");
          browser.isPlaying=true;backend.sync();
          require(backend.streamState.streams[0].label==="audio-src" && !backend.streamState.streams[0].active,"ambiguous generic stream is not relabeled or highlighted");
        }
        if(mode==="media-selection") {
          Pipewire.nodes={values:[]};
          require(mediaOwner.activePlayer===browser,"oldest nonproxy playing selection retained");
          browser.isPlaying=false;
          require(mediaOwner.activePlayer===spotify,"stopped player loses selection");
          browser.isPlaying=true;
          require(mediaOwner.activePlayer===spotify,"reactive playing order retains older active player");
          mediaOwner.preferredPlayerKey=browser.dbusName;
          require(mediaOwner.activePlayer===browser,"explicit playing preference wins");
          Pipewire.nodes={values:test.nodes};
          var providerFactory=Qt.createComponent("AudioOutputProvider.qml",Component.PreferSynchronous);
          require(providerFactory.status===Component.Ready,providerFactory.errorString());
          var firstOutput=providerFactory.createObject(view), secondOutput=providerFactory.createObject(view);providerFactory.destroy();
          require(firstOutput && secondOutput,"two actual provider owners construct with fake native services");
          require(firstOutput.streamState.streams[0].active===secondOutput.streamState.streams[0].active,"providers observe one shared media preference");
          mediaOwner.preferredPlayerKey=spotify.dbusName;
          require(firstOutput.streamState.streams[0].active && secondOutput.streamState.streams[0].active,"shared player selection updates both outputs");
          mediaOwner.preferredPlayerKey=browser.dbusName;
          browser.isPlaying=false;
          require(mediaOwner.activePlayer===spotify,"paused preference does not override playing player");
          spotify.isPlaying=false;
          require(mediaOwner.activePlayer===proxy,"proxy is a fallback not a preferred duplicate");
        }
        if(mode==="media-idle") {
          browser.isPlaying=false;spotify.isPlaying=false;proxy.isPlaying=false;
          browser.trackTitle="";browser.trackArtist="";browser.trackArtUrl="https://invalid.example/no-fetch.png";
          Pipewire.nodes={values:[]};Mpris.players={values:[browser,spotify]};
          require(mediaOwner.activePlayer===spotify,"idle shown-track player beats art-only metadata");
          mediaOwner.preferredPlayerKey=browser.dbusName;
          require(mediaOwner.activePlayer===browser,"explicit idle preference retains original exception");
          Mpris.players={values:[spotify]};
          require(mediaOwner.preferredPlayerKey==="" && mediaOwner.activePlayer===spotify,"vanished preference is removed");
        }
        if(mode==="media-churn") {
          var captured=mediaOwner.state.active;
          spotify.identity="Renamed player";
          require(captured.identity==="Spotify" && mediaOwner.state.active.identity==="Renamed player","published metadata remains detached from player churn");
          Mpris.players={values:[]};backend.sync();
          require(mediaOwner.state.active===null && mediaOwner.state.players.length===0 && !backend.streamState.streams[0].active,"player disappearance clears active marks");
          var replacement=makePlayer(spotify.dbusName,"Replacement",true);
          Mpris.players={values:[replacement]};backend.sync();
          require(mediaOwner.state.active.identity==="Replacement" && captured.identity==="Spotify","same-name player recreation never retains native row references");
          test.nodes=[];Pipewire.nodes={values:[]};backend.sync();require(backend.streamState.streams.length===0,"stream disappearance clears rows");
        }
        require(writes===0 && a.audio.volume===0.42 && !a.audio.muted && stream.audio.volume===0.4 && !stream.audio.muted,"media discovery selection and churn never mutate audio or playback");
      }
      if(["media-transport","media-guards","media-widget","media-widget-churn"].indexOf(mode)!==-1) {
        Mpris.players={values:[spotify]};spotify.allowCommands=true;
        var target=mediaOwner.state.active.transportKey;
        require(Object.isFrozen(target) && target.name===spotify.dbusName && target.generation>0,"frozen primitive identity target");
        require(spotify.attempts===0 && mediaOwner.state.active.canControl,"discovery never sends transport");
        if(mode==="media-transport") {
          require(mediaOwner.runAction("playPause",false,target) && spotify.pauses===1,"original playing toggle pauses");
          require(mediaOwner.runAction("playPause",false,target) && spotify.plays===1,"original paused toggle plays");
          require(mediaOwner.runAction("next",false,target) && spotify.nexts===1,"next targets bound player");
          require(mediaOwner.runAction("previous",false,target) && spotify.previouses===1,"previous targets bound player");
          require(mediaOwner.runAction("pause",false,target) && mediaOwner.runAction("play",false,target),"explicit play and pause");
          spotify.canPause=false;spotify.canPlay=false;
          require(mediaOwner.runAction("playPause",false,target) && spotify.toggles===1,"original advertised toggle fallback");
          spotify.canTogglePlaying=false;
          require(!mediaOwner.runAction("playPause",false,target) && spotify.attempts===7,"all unavailable capabilities refuse");
          spotify.failCommands=true;
          require(!mediaOwner.runAction("next",false,target) && spotify.attempts===8 && spotify.nexts===1,"synchronous exception never retries");
          require(mediaOwner.errorText.indexOf("uncertain")!==-1,"exception is uncertainty not false success");
        }
        if(mode==="media-guards") {
          for(var badKey of [undefined,null,false,3,"spotify",{},Object.assign({},target,{generation:"1"}),Object.assign({},target,{generation:0}),Object.assign({},target,{extra:1})])
            require(!mediaOwner.runAction("next",false,badKey),"missing/malformed target never falls back");
          require(!mediaOwner.runAction("launch",false,target) && !mediaOwner.runAction("next",true,target),"unknown/feedback paths excluded");
          spotify.canControl=false;
          require(!mediaOwner.runAction("next",false,target),"fresh canControl gates advertised capability");
          spotify.canControl=true;spotify.canGoNext=false;
          require(!mediaOwner.runAction("next",false,target),"capability changed after capture rejects");
          spotify.canGoNext=true;Mpris.players={values:[browser]};browser.allowCommands=true;
          require(!mediaOwner.runAction("next",false,target) && browser.attempts===0,"vanished target cannot command selected replacement");
          var recycled=makePlayer(spotify.dbusName,"Recycled",true);recycled.allowCommands=true;
          Mpris.players={values:[recycled]};
          require(!mediaOwner.runAction("next",false,target) && !mediaOwner.selectPlayer(target) && recycled.attempts===0,"same-name replacement rejects stale command and preference");
          var currentKey=mediaOwner.state.active.transportKey;
          require(currentKey.generation!==target.generation && mediaOwner.selectPlayer(currentKey) && recycled.attempts===0,"fresh source preference never transfers playback");
          Mpris.players={values:[spotify,recycled]};
          require(!mediaOwner.runAction("next",false,currentKey) && spotify.attempts===0,"ambiguous native names refuse");
        }
        if(mode==="media-widget" || mode==="media-widget-churn") {
          view.close();
          var widgetComponent=Qt.createComponent("MediaControlView.qml",Component.PreferSynchronous);
          require(widgetComponent.status===Component.Ready,widgetComponent.errorString());
          var mediaWidget=widgetComponent.createObject(view,{bar:owner.ownerApi});widgetComponent.destroy();
          require(mediaWidget && mediaWidget.hasMedia && mediaWidget.activePlayer.play===undefined,"original widget reads primitive active row");
          mediaWidget.popupOpen=true;
          require(spotify.attempts===0 && owner.ownerApi.activePopout===mediaWidget,"popup ownership/readback sends no transport");
          if(mode==="media-widget") {
            mediaWidget.pointerClicked({button:Qt.MiddleButton});
            require(spotify.nexts===1,"original middle click advances track");
            mediaWidget.pointerWheel({angleDelta:{y:120}});
            require(spotify.previouses===1,"original up wheel goes previous");
            mediaWidget.pointerClicked({button:Qt.LeftButton});
            require(spotify.pauses===1,"original left click play/pause");
            var nextButton=findItem(mediaWidget,function(item){return item.iconText==="󰒭" && item.clicked!==undefined;});
            require(nextButton!==null && nextButton.enabled,"original popup next button exists");
            nextButton.clicked();require(spotify.nexts===2,"original popup button submits primitive bound target");
            spotify.canControl=false;
            require(!nextButton.enabled,"live capability disables original button");
            var attempts=spotify.attempts;nextButton.clicked();
            require(spotify.attempts===attempts && mediaOwner.errorText!=="","even programmatic disabled-button signal cannot bypass native guard");
          } else {
            spotify.identity="<b>Not rich text</b>";
            require(mediaWidget.activePlayer.identity===spotify.identity && spotify.attempts===0,"live metadata is presentation only");
            Mpris.players={values:[]};
            require(!mediaWidget.hasMedia && !mediaWidget.popupOpen && owner.ownerApi.activePopout===null,"last-player loss releases popup ownership");
            var returned=makePlayer(spotify.dbusName,"Returned",true);returned.allowCommands=true;
            Mpris.players={values:[returned]};
            require(mediaWidget.hasMedia && !mediaWidget.popupOpen && returned.attempts===0,"same-name reappearance never opens or plays automatically");
            require(!mediaOwner.runAction("next",false,target) && returned.attempts===0,"widget lifetime cannot retain old native command target");
          }
          mediaWidget.close();require(owner.ownerApi.activePopout===null,"explicit close releases original popup owner");mediaWidget.destroy();
        }
        require(writes===0 && a.audio.volume===0.42 && !a.audio.muted && stream.audio.volume===0.4 && !stream.audio.muted,"transport/source controls never change device or stream gain/mute");
      }
      if(mode.indexOf("route-")===0 || mode.indexOf("input-")===0) {
        a.name="alsa_output.fixture";b.name="bluez_output.fixture";
        var dsp={id:8,name:"effect_input.fixture",ready:true,isSink:true,isStream:false,
          properties:{"object.serial":"18"},audio:{volume:0.91,muted:false}};
        var dspSource={id:9,name:"effect_output.fixture",ready:true,isSink:true,isStream:true,
          properties:{"object.serial":"19"},audio:{volume:0.99,muted:false}};
        var edge={source:dspSource,target:a};
        Object.defineProperty(edge,"state",{get:function(){throw new Error("Unbound link-state read");}});
        var graphNodes=[a,b,dsp,dspSource,mic];
        graph(graphNodes,[edge],mode==="route-direct" || mode.indexOf("input-")===0 ? a : dsp,mic);
        var routeFactory=Qt.createComponent("AudioOutputProvider.qml",Component.PreferSynchronous);
        require(routeFactory.status===Component.Ready,routeFactory.errorString());
        var routedProvider=routeFactory.createObject(view);routeFactory.destroy();
        routeFactory=Qt.createComponent("AudioOutputView.qml",Component.PreferSynchronous);
        var routedView=routeFactory.createObject(view,{bar:owner.ownerApi,backend:routedProvider});routeFactory.destroy();
        require(routedView && routedProvider,"actual provider and original routed surface construct");
        require(a.audio.volume===0.42 && dsp.audio.volume===0.91 && mic.audio.muted && Pipewire.preferredDefaultAudioSink===null,"routing startup is observation only");
        routedView.opened=true;
        var capturedRoute=routedProvider.state.current;
        require(Object.isFrozen(capturedRoute.control) && Object.isFrozen(capturedRoute.control.target),"frozen primitive route proof");
        require(capturedRoute.control.target.audio===undefined && capturedRoute.control.target.properties===undefined,"no native route target in delegate state");
        if(mode==="route-direct") {
          require(capturedRoute.control.status==="direct" && capturedRoute.id===a.id,"direct default targets itself");
          routedView.setOutputVolume(0.62);require(a.audio.volume===0.62,"direct gain through actual provider");
          for(var invalidVolume of [NaN,Infinity,"0.5",null])require(!routedProvider.setVolume(capturedRoute,invalidVolume),"invalid routed gain refuses");
          routedProvider.setVolume(capturedRoute,2);require(a.audio.volume===1,"routed device upper clamp");
          routedProvider.toggleMute(capturedRoute);require(a.audio.muted,"direct mute");
          routedProvider.setVolume(capturedRoute,-1);require(a.audio.volume===0 && a.audio.muted,"lower clamp never unmutes");
          var gainAttempts=0;
          Object.defineProperty(a.audio,"volume",{get:function(){return 0;},set:function(value){gainAttempts++;throw new Error("Fixture native gain outcome uncertain");}});
          routedView.setOutputVolume(0.4);
          require(gainAttempts===1 && routedView.errorText.indexOf("uncertain")!==-1,"routed setter exception reports uncertainty without retry");
        }
        if(mode==="route-dsp") {
          require(capturedRoute.id===dsp.id && capturedRoute.control.target.id===a.id && routedView.outputVolume===0.42,"selected DSP differs from loudness target");
          routedView.setOutputVolume(0.7);require(a.audio.volume===0.7 && dsp.audio.volume===0.91 && dspSource.audio.volume===0.99,"original slider controls downstream only");
          routedView.toggleOutputMute();require(a.audio.muted && !dsp.audio.muted && mic.audio.muted,"local output mute targets physical sink only");
          graph(graphNodes,[edge],dsp,mic);
          routedView.toggleAllMuted();require(!a.audio.muted && !mic.audio.muted && !dsp.audio.muted,"both-muted explicit master unmutes physical output and microphone");
          graph(graphNodes,[edge],dsp,mic);
          routedView.toggleAllMuted();require(a.audio.muted && mic.audio.muted && !dsp.audio.muted,"master mutes physical output without altering DSP gain/mute");
          var rowB=routedProvider.state.outputs.filter(function(row){return row.id===b.id;})[0];
          require(routedProvider.chooseOutput(rowB) && Pipewire.preferredDefaultAudioSink===b && Pipewire.defaultAudioSink===dsp,"selection stays a server preference, not optimistic route mutation");
          a.audio.muted=false;graph(graphNodes,[edge],dsp,mic);
          var micAttempts=0;
          Object.defineProperty(mic.audio,"muted",{get:function(){return true;},set:function(value){micAttempts++;throw new Error("Fixture native microphone outcome uncertain");}});
          require(!routedProvider.toggleAllMuted(routedProvider.state.current,routedProvider.inputState.current)
            && micAttempts===1 && a.audio.muted && !dsp.audio.muted,"partial master failure never compensates by unmuting the physical output");
        }
        if(mode==="route-churn") {
          routedView.dragTarget=capturedRoute;routedView.wheel(60);require(routedView.wheelRemainder===60,"partial wheel before reroute");
          var edgeB={source:dspSource,target:b};graph(graphNodes,[edgeB],dsp,mic);
          require(routedView.wheelRemainder===0,"route proof change resets partial wheel input");
          routedView.setOutputVolume(0.9);
          require(a.audio.volume===0.42 && b.audio.volume===0.6 && routedView.errorText!=="","captured slider cannot retarget after graph reroute");
          require(!routedProvider.toggleAllMuted(capturedRoute,routedProvider.inputState.current) && !a.audio.muted && !b.audio.muted && mic.audio.muted,"stale master route preflights before either channel");
          routedView.dragTarget=null;routedView.setOutputVolume(0.8);require(b.audio.volume===0.8 && dsp.audio.volume===0.91,"fresh routed request targets new hardware");
          var previous=routedProvider.state.current;
          var replaced=Object.assign({},dsp,{audio:{volume:0.55,muted:false}});
          graph([a,b,replaced,dspSource,mic],[edgeB],replaced,mic);
          require(!routedProvider.setVolume(previous,0.3) && b.audio.volume===0.8,"same ID/name/serial recreated default rejects old object generation");
          Pipewire.ready=false;
          require(!routedProvider.toggleMute(routedProvider.state.current) && !b.audio.muted,"server unready blocks routed requests");Pipewire.ready=true;
        }
        if(mode==="route-unknown") {
          graph(graphNodes,[],dsp,mic);
          require(!routedView.outputControlAvailable && routedView.outputVolumeName(0,true)==="Output route unavailable","missing route reports unknown, not DSP gain");
          var outputSlider=findItem(routedView.panelWindow.loadedContent,function(item){return item.maximum===1 && item.moved!==undefined;});
          require(outputSlider && !outputSlider.enabled,"original output slider disables for unknown route");
          routedView.setOutputVolume(0.3);routedView.toggleAllMuted();
          require(a.audio.volume===0.42 && dsp.audio.volume===0.91 && mic.audio.muted,"unknown route never falls back or partially changes microphone");
          graph(graphNodes,[edge,{source:dspSource,target:b}],dsp,mic);
          require(routedProvider.volumeRoute.status==="ambiguous" && !routedProvider.toggleMute(capturedRoute),"two physical outputs do not select the first");
          graph(graphNodes,[{source:dspSource,target:dsp}],dsp,mic);
          require(routedProvider.volumeRoute.status==="cycle" && !routedView.outputControlAvailable,"cycle never controls virtual gain");
          routedView.toggleInputMute();require(!mic.audio.muted,"independent input row still works while output route is unknown");
        }
        if(mode.indexOf("input-")===0) {
          var inputKey=routedProvider.inputState.current;
          require(inputKey && inputKey.controlAvailable && Object.isFrozen(inputKey.control)
            && inputKey.control.audio===undefined,"actual provider exposes frozen microphone proof only");
          require(Pipewire.preferredDefaultAudioSource===null && mic.audio.volume===0.3 && mic.audio.muted,"microphone construction and opening never mutate");
          if(mode==="input-direct") {
            routedView.setInputVolume(0.64);require(mic.audio.volume===0.64 && mic.audio.muted && a.audio.volume===0.42,"input gain remains channel-local and does not unmute");
            routedView.toggleInputMute();require(!mic.audio.muted && !a.audio.muted,"local microphone mute");
            for(var invalidInput of [NaN,Infinity,"0.4",true,null])require(!routedProvider.setSourceVolume(inputKey,invalidInput),"invalid microphone gain refuses");
            require(routedProvider.setSourceVolume(inputKey,2) && mic.audio.volume===1,"input upper clamp");
            require(routedProvider.setSourceVolume(inputKey,-1) && mic.audio.volume===0,"input lower clamp");
            var otherMic={id:5,name:"fixture-other-mic",ready:true,isSink:false,isStream:false,
              properties:{"object.serial":"15"},audio:{volume:0.7,muted:true}};
            graph(graphNodes.concat([otherMic]),[edge],a,mic);
            var otherKey=routedProvider.inputState.inputs.filter(function(row){return row.id===5;})[0];
            require(routedProvider.chooseInput(otherKey) && Pipewire.preferredDefaultAudioSource===otherMic
              && Pipewire.defaultAudioSource===mic,"input selection is a preference hint, never optimistic default rewrite");
            require(!routedProvider.setSourceVolume(otherKey,0.1) && otherMic.audio.volume===0.7,"local input gain never controls a nondefault candidate");
          }
          if(mode==="input-churn") {
            routedView.dragSourceTarget=inputKey;
            var changedMic={id:5,name:"fixture-other-mic",ready:true,isSink:false,isStream:false,
              properties:{"object.serial":"15"},audio:{volume:0.7,muted:false}};
            graph(graphNodes.concat([changedMic]),[edge],a,changedMic);
            routedView.setInputVolume(0.9);
            require(mic.audio.volume===0.3 && changedMic.audio.volume===0.7 && routedView.errorText!=="","held drag cannot follow changed actual default");
            var changedKey=routedProvider.inputState.current;
            var replacedMic=Object.assign({},changedMic,{audio:{volume:0.2,muted:false}});
            graph(graphNodes.concat([replacedMic]),[edge],a,replacedMic);
            require(!routedProvider.toggleSourceMute(changedKey) && !routedProvider.chooseInput(changedKey)
              && routedView.nodeFor(changedKey)===null,"recreated ID/name/serial cannot acquire old row actions");
            require(!routedProvider.toggleAllMuted(routedProvider.state.current,changedKey)
              && !a.audio.muted && !replacedMic.audio.muted,"stale microphone proof blocks both master setters");
            var freshMic=routedProvider.inputState.current;
            var secondFactory=Qt.createComponent("AudioOutputProvider.qml",Component.PreferSynchronous);
            var secondProvider=secondFactory.createObject(view);secondFactory.destroy();
            require(secondProvider && !secondProvider.setSourceVolume(freshMic,0.8),"microphone owner replacement rejects foreign provider proof");
            secondProvider.destroy();
            replacedMic.properties={"object.serial":"99"};graph(graphNodes.concat([replacedMic]),[edge],a,replacedMic);
            require(!routedProvider.setSourceVolume(freshMic,0.9) && replacedMic.audio.volume===0.2,"serial churn blocks captured microphone action");
          }
          if(mode==="input-guards") {
            Pipewire.ready=false;
            require(!routedProvider.setSourceVolume(inputKey,0.8) && !routedProvider.toggleSourceMute(inputKey)
              && !routedProvider.chooseInput(inputKey),"server readiness gates every input mutation");Pipewire.ready=true;
            var virtualMic={id:6,name:"fixture-virtual-mic",ready:true,isSink:false,isStream:false,
              properties:{"object.serial":"16","media.class":"Audio/Source/Virtual"},audio:null};
            graph(graphNodes.concat([virtualMic]),[edge],a,virtualMic);
            require(routedProvider.inputState.defaultPresent && !routedProvider.inputState.current
              && routedView.inputUnavailable && routedView.toggleHint==="Microphone controls unavailable","present unsupported default is explicit, never fabricated absent/muted state");
            routedView.toggleAllMuted();require(!a.audio.muted && mic.audio.muted,"unsupported microphone never turns master into output-only action");
            var duplicate=Object.assign({},mic);
            graph(graphNodes.concat([duplicate]),[edge],a,mic);
            require(!routedProvider.toggleSourceMute(inputKey),"ambiguous input ID never selects first match");
            routedView.cursorActive=true;routedView.focusSection="input";routedView.selectedIndex=-1;
            mic.properties={};graph(graphNodes,[edge],a,mic);
            require(!routedView.inputControlAvailable && !routedView.inputLevelKnown,"missing serial disables input control and known percentage");
            require(!routedView.sectionHasSlider("input") && routedView.selectedIndex===0,"input keyboard cursor skips disabled slider");
            var disabledInput=findItem(routedView.panelWindow.loadedContent,function(item){return item.maximum===1 && item.moved!==undefined && item.value===routedView.inputVolume;});
            require(disabledInput && !disabledInput.enabled,"original microphone slider disables without control authority");
          }
          if(mode==="input-uncertain") {
            var inputGainAttempts=0,inputMuteAttempts=0;
            Object.defineProperty(mic.audio,"volume",{get:function(){return 0.3;},set:function(value){inputGainAttempts++;throw new Error("Fixture uncertain microphone gain");}});
            routedView.setInputVolume(0.8);
            require(inputGainAttempts===1 && routedView.errorText.indexOf("uncertain")!==-1,"input gain exception reports uncertainty with no replay");
            Object.defineProperty(mic.audio,"muted",{get:function(){return true;},set:function(value){inputMuteAttempts++;throw new Error("Fixture uncertain microphone mute");}});
            routedView.toggleInputMute();require(inputMuteAttempts===1 && routedView.errorText.indexOf("uncertain")!==-1,"local input mute exception never retries");
            require(!routedProvider.toggleAllMuted(routedProvider.state.current,inputKey)
              && a.audio.muted && inputMuteAttempts===2,"partial native master never compensates by unmuting output");
          }
        }
        require(dsp.audio.volume===0.91 && dspSource.audio.volume===0.99 && !dsp.audio.muted,"DSP processing level preserved across every routed action");
        routedView.close();routedView.destroy();routedProvider.destroy();
      }
      if(mode.indexOf("master-")===0) {
        var outputKey=backend.state.current,inputKey=backend.inputState.current;
        require(writes===0 && view.anyAudible,"master construction reads only");
        require(view.toggleHint==="Mute output and microphone","explicit two-channel scope");
        if(mode==="master-mixed") {
          view.opened=true;require(writes===0,"opening never unmutes microphone");
          view.toggleAllMuted();require(a.audio.muted && mic.audio.muted && !view.anyAudible,"mixed channels both mute");
          require(a.audio.volume===0.42 && mic.audio.volume===0.3,"master preserves gain");
          view.toggleAllMuted();require(!a.audio.muted && !mic.audio.muted && view.anyAudible,"both-muted master explicitly unmutes both");
          view.toggleOutputMute();require(a.audio.muted && !mic.audio.muted && view.anyAudible,"output row stays local");
          view.toggleInputMute();require(a.audio.muted && mic.audio.muted && !view.anyAudible,"input row stays local");
          mic.audio.muted=false;backend.sync();view.toggleAllMuted();
          require(a.audio.muted && mic.audio.muted,"input-only audibility mutes both instead of toggling independently");
          require(b.audio.muted===false && stream.audio.muted===false,"nondefault and streams unchanged");
        }
        if(mode==="master-single") {
          test.nodes=[mic];test.current=null;backend.sync();
          view.toggleAllMuted();require(!mic.audio.muted,"microphone-only explicit unmute");
          view.toggleAllMuted();require(mic.audio.muted,"microphone-only mute");
          test.nodes=[a];test.current=a;test.currentSource=null;backend.sync();
          view.toggleAllMuted();require(a.audio.muted,"output-only mute");
          test.nodes=[];test.current=null;backend.sync();var before=writes;
          view.toggleAllMuted();require(writes===before && view.errorText!=="","empty master fails closed");
        }
        if(mode==="master-guards") {
          mic.properties={"object.serial":"99"};
          require(!Actions.toggleAllMuted(nodes,nodes,outputKey,inputKey) && !a.audio.muted,"reused microphone serial blocks all writes");
          mic.properties={"object.serial":"14"};
          require(!Actions.toggleAllMuted(nodes,[a],outputKey,inputKey) && !a.audio.muted,"missing microphone blocks output mutation");
          mic.ready=false;require(!Actions.toggleAllMuted(nodes,nodes,outputKey,inputKey),"unready input blocks master");mic.ready=true;
          for(var invalid of [undefined,false,0,"",{},Object.assign({},inputKey,{serial:""}),Object.assign({},inputKey,{serial:14})])
            require(!Actions.toggleAllMuted(nodes,nodes,outputKey,invalid) && !a.audio.muted,"malformed or missing serial fails closed");
          test.current=b;
          require(!backend.toggleAllMuted(outputKey,inputKey) && !a.audio.muted && !b.audio.muted,"default change rejects stale capture");
          require(!Actions.masterDefaultMatches(null,mic) && Actions.masterDefaultMatches(null,null),"new default cannot be silently omitted");
          test.current=a;test.currentSource=null;
          require(!backend.toggleAllMuted(outputKey,inputKey),"vanished default rejects stale capture");
        }
        if(mode==="master-partial") {
          Object.defineProperty(mic.audio,"muted",{get:function(){return true;},set:function(v){throw new Error("fixture native setter failure");}});
          require(!Actions.toggleAllMuted(nodes,nodes,outputKey,inputKey),"setter failure reported without retry");
          require(a.audio.muted,"no unsafe compensating unmute after partial setter failure");
        }
      }
      if(mode.indexOf("stream")===0) {
        require(view.displayAudioStreams.length===0 && writes===0,"closed stream delegates and no startup write");
        view.opened=true;
        require(view.displayAudioStreams.length===1,"playback stream visible on open");
        var key=backend.streamState.streams[0];
        require(Object.isFrozen(key) && Object.isFrozen(backend.streamState.streams),"frozen stream primitives");
        require(key.audio===undefined && key.properties===undefined && key.serial==="1001","no native object in stream row");
        require(key.label==="Fixture Player","original application label");
        if(mode==="streams") {
          view.setStreamVolume(key,0.7);require(stream.audio.volume===0.7 && a.audio.volume===0.42,"per-app volume only");
          view.toggleStreamMute(key);require(stream.audio.muted && !a.audio.muted,"per-app mute only");
          view.setStreamVolume(key,8);require(stream.audio.volume===1.5 && stream.audio.muted,"original stream amplification limit; no unmute");
          view.setStreamVolume(key,-8);require(stream.audio.volume===0,"stream lower bound");
          for(var bad of [NaN,Infinity,"0.5",true,null])require(!Actions.setStreamVolume(nodes,key,bad),"invalid stream gain refused");
        }
        if(mode==="stream-guards") {
          var capture=Object.assign({},stream,{isSink:false});
          var shell=Object.assign({},stream,{name:"quickshell"});
          var processing=Object.assign({},stream,{name:"omarchy_speaker_tuning.output"});
          var unready=Object.assign({},stream,{ready:false});
          Object.defineProperty(unready,"properties",{get:function(){throw new Error("unbound property read");}});
          require(!Actions.playbackStream(capture) && !Actions.playbackStream(shell) && !Actions.playbackStream(processing),"capture/shell/processing excluded");
          require(Presentation.streamSnapshot(true,[capture,shell,processing,unready,a]).streams.length===0,"wrong directions and unbound streams omitted");
          require(Actions.playbackStream(unready),"tracker eligibility does not access unbound properties");
          var missing=Object.assign({},stream,{properties:{}});
          require(!Actions.resolveStream([missing],key) && Presentation.streamSnapshot(true,[missing]).streams.length===0,"missing serial fails closed");
          stream.properties["object.serial"]="1002";
          require(!Actions.setStreamVolume(nodes,key,0.9) && !Actions.toggleStreamMute(nodes,key),"same name and ID reused with new serial");
          require(!Actions.setStreamVolume([],key,0.9),"removed stream refused");
          require(!Actions.resolveStream([capture],key) && !Actions.resolveStream([a],key),"never mutate capture or device with stream action");
        }
        if(mode==="stream-navigation") {
          view.cursorActive=true;view.focusSection="streams";view.selectedIndex=0;
          var catcher=view.panelWindow.loadedContent;
          catcher.moveRequested(1,0);require(Math.abs(stream.audio.volume-0.45)<0.0001 && a.audio.volume===0.42,"stream keyboard gain is local");
          catcher.textKey("m",0);require(stream.audio.muted && !a.audio.muted,"m mutes selected stream only");
          catcher.activateRequested();require(!stream.audio.muted,"enter unmutes selected stream");
          test.nodes=[a,b];backend.sync();
          require(view.focusSection==="output" && view.selectedIndex===-1,"cursor recovers when last stream disappears");
        }
        if(mode==="stream-drag") {
          var row=findItem(view.panelWindow.loadedContent,function(item){return item.streamVolume!==undefined;});
          require(row!==null,"original stream row constructed");
          var slider=findItem(row,function(item){return item.maximum===1.5 && item.moved!==undefined;});
          require(slider!==null,"original stream slider constructed");
          slider.dragging=true;
          require(row.dragKey.serial==="1001","drag pins stream serial");
          var replacement=Object.assign({},stream,{properties:{"object.serial":"2002"},audio:{volume:0.2,muted:false}});
          test.nodes=[a,b,replacement];
          row.node=Presentation.streamSnapshot(true,[replacement]).streams[0];
          slider.moved(0.9);
          require(writes===0 && replacement.audio.volume===0.2 && view.errorText!=="","drag cannot retarget a replacement stream");
        }
        view.close();require(view.displayAudioStreams.length===0,"stream delegates cleared on close");
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
