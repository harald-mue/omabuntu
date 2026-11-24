import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons as Commons

// One nonvisual owner across outputs. No mutation on construction or page open.
QtObject {
  id: root
  property bool enabled: true
  property string helper: Quickshell.env("OMABUNTU_DISPLAY_PROFILES_HELPER")
  property var data: ({profiles:[],pending:null,text_size:12,inventory:[]})
  property var draft: null
  property bool draftDirty: false
  property var review: null
  property string approval: ""
  property string errorText: ""
  property string automationStatus: ""
  property var packet: null
  property string watching: ""
  property string launchedWatch: ""
  readonly property bool busy: rpc.running || packet!==null
  readonly property bool configured: helper.endsWith("/display_profiles.py") && helper.indexOf(" ")<0
  function request(value) {
    if(!configured){errorText="Monitor profiles helper unavailable; no installation attempted";return false}
    if (!enabled || busy) return false
    packet=JSON.parse(JSON.stringify(value))
    rpc.stdinEnabled=true;rpc.exec(["python3","-B",helper,"rpc"])
    return true
  }
  function refresh() { request({op:"status"}) }
  function capture(name) { review=null;approval="";request({op:"capture",name:name}) }
  function save() { review=null;approval="";if(draft)request({op:"save",profile:draft,store_digest:data.store_digest}) }
  function select(profile) {
    if(busy||data.pending)return
    review=null;approval=""
    draftDirty=false
    draft=JSON.parse(JSON.stringify({schema_version:profile.schema_version,name:profile.name,outputs:profile.outputs,text_size:profile.text_size}))
  }
  function edit(index,key,value) {
    if(!draft||busy||data.pending)return
    var next=JSON.parse(JSON.stringify(draft));next.outputs[index][key]=value;draft=next;draftDirty=true;review=null;approval=""
  }
  function editText(value) {
    if(!draft||busy||data.pending)return
    var next=JSON.parse(JSON.stringify(draft));next.text_size=value;draft=next;draftDirty=true;review=null;approval=""
  }
  function inspect() { if(draft&&!draftDirty)request({op:"review",name:draft.name}) }
  function apply() { if(review&&approval)request({op:"apply",review:review,approval:approval}) }
  function terminal(op) { if(data.pending)request({op:op,token:data.pending.token}) }
  function automate(profile) { request({op:"automatic",name:profile.name,enabled:!profile.automatic,store_digest:data.store_digest}) }
  function remove(profile) { request({op:"delete",name:profile.name,store_digest:data.store_digest}) }
  function textSize(value) { request({op:"text",value:value}) }
  function watch() {
    var names=data.profiles.filter(function(p){return p.automatic}).map(function(p){return p.name}).sort().join("|")
    if(!enabled||!names){watching="";launchedWatch="";watcher.running=false;return}
    if(watching!==names){watcher.running=false;watching=names;Qt.callLater(startWatcher)}
  }
  function startWatcher() {
    if(enabled&&watching&&!watcher.running&&watching!==launchedWatch) {
      launchedWatch=watching;watcher.exec(["python3","-B",helper,"watch","--allow-session-automation"])
    }
  }
  onEnabledChanged: {
    if(enabled)refresh()
    else {watching="";launchedWatch="";watcher.running=false;review=null;approval=""}
  }
  Component.onCompleted: if(configured&&enabled)refresh()
  property Process rpc: Process {
    stdinEnabled:true
    onRunningChanged: if(running&&root.packet) { write(JSON.stringify(root.packet)+"\n");stdinEnabled=false }
    stdout: StdioCollector {id:output}
    onExited: function(code) {
      var op=root.packet?root.packet.op:"";root.packet=null
      try {
        if(output.text.length>2000000)throw Error("frame-limit")
        var value=JSON.parse(output.text)
        if(code!==0||value.error)throw Error(value.error||"Display operation failed")
        root.errorText=""
        if(value.profiles){root.data=value;Commons.Color.textSizeFile.reload();root.watch()}
        if(value.profile){root.draft=value.profile;root.draftDirty=true}
        if(op==="save")root.draftDirty=false
        if(value.review){root.review=value.review;root.approval=value.approval}
      }catch(error){root.errorText=String(error).slice(0,256);root.review=null;root.approval=""}
      if(["status","capture","review"].indexOf(op)<0)Qt.callLater(root.refresh)
    }
  }
  property Process watcher: Process {
    stdout: SplitParser { onRead:line=>{
      try{
        root.automationStatus=JSON.parse(line).status||""
        if(["kept","already-observed","automatic-refused-check-recovery"].indexOf(root.automationStatus)>=0)Qt.callLater(root.refresh)
      }catch(error){root.automationStatus="Invalid automation response"}
    }}
    onExited: {
      root.automationStatus="Automation stopped; no automatic crash restart"
      if(root.watching!==root.launchedWatch)Qt.callLater(root.startWatcher)
    }
  }
  // Observational refresh keeps confirmation/recovery controls accurate. It is
  // not a lifetime timer, native writer, automatic retry or crash supervisor.
  property Timer refreshTimer: Timer {interval:2000;repeat:true;running:root.enabled&&!!root.data.pending;onTriggered:root.refresh()}
}
