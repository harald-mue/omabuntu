import QtQuick

// Shared observation feedback. Initial/default replacement is not a volume event.
QtObject {
  id:root
  property bool enabled:true
  property var previous:({})
  signal showRequested(string icon,string message,int value,int maximum,bool progress)
  signal closeRequested()
  function observe(kind,row){
    if(!row || row.controlAvailable===false || typeof row.volume !== "number"
        || !isFinite(row.volume) || row.volume < 0 || row.volume > 4)return
    var all=Object.assign({},previous)
    var identity=row.id+":"+row.serial+":"+JSON.stringify(row.control)
    var old=all[kind]
    all[kind]=identity ? {identity:identity,volume:row.volume,muted:row.muted} : null
    previous=all
    if(!enabled || !old || old.identity!==identity || !row)return
    if(old.volume===row.volume && old.muted===row.muted)return
    var mic=kind==="input"
    showRequested(mic?(row.muted?"microphone-muted":"microphone"):(row.muted?"volume-muted":"volume"),
      "",row.muted?0:Math.round(row.volume*100),100,true)
  }
  function media(action,title,icon){
    if(!enabled || ["play","pause","playPause","next","previous","stop"].indexOf(action)<0)return
    // Issuance is not playback acceptance; never announce a confirmed state.
    var icons=["media","media-play","media-pause","media-next","media-previous"]
    var chosen=icons.indexOf(icon)>=0 ? icon : action==="next" ? "media-next"
      : action==="previous" ? "media-previous" : action==="play" ? "media-play"
      : action==="pause" ? "media-pause" : "media"
    var label=chosen==="media-next" ? "Next track" : chosen==="media-previous" ? "Previous track"
      : chosen==="media-play" ? "Play" : chosen==="media-pause" ? "Pause" : action==="stop" ? "Stop" : "Play/pause"
    showRequested(chosen,String(label+" requested"+(title?" · "+String(title).slice(0,160):"")),0,100,false)
  }
  onEnabledChanged:{previous=({});if(!enabled)closeRequested()}
}
