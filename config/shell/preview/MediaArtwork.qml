import QtQuick
import Quickshell
import Quickshell.Io

// One local-cache artwork owner. No remote URLs ever reach a Qt image loader.
QtObject {
  id:root
  property bool enabled:false
  property string url:""
  property string identity:""
  property string source:""
  property string menuHelper:Quickshell.env("OMABUNTU_MENU_HELPER")
  readonly property string helper:menuHelper.endsWith("/menu_model.py") && menuHelper.indexOf(" ")<0
    ? menuHelper.slice(0,-"menu_model.py".length)+"audio_artwork.py" : ""
  readonly property string cacheRoot: Quickshell.env("XDG_CACHE_HOME") || (Quickshell.env("HOME") + "/.cache")
  readonly property string cachePrefix: cacheRoot.startsWith("/") && cacheRoot.split("/").indexOf("..") < 0
    ? "file://" + cacheRoot.split("/").map(function(part) {
        return encodeURIComponent(part).replace(/[!'()*]/g, function(c) { return "%" + c.charCodeAt(0).toString(16).toUpperCase() })
      }).join("/") + "/omabuntu/audio-art/" : ""
  property int generation:0
  property int issued:-1
  property bool again:false
  function refresh(){
    generation++;source=""
    if(rpc.running){again=true;return}
    if(!enabled || !helper || !url.startsWith("file:///"))return
    issued=generation;rpc.stdinEnabled=true;deadline.restart()
    rpc.exec(["/usr/bin/python3",helper,"--allow-local-artwork"])
  }
  onEnabledChanged:refresh()
  onUrlChanged:refresh()
  onIdentityChanged:refresh()
  property Timer deadline:Timer{interval:4000;onTriggered:{root.source="";rpc.running=false}}
  property Process rpc:Process{
    stdout:StdioCollector{id:reply}
    onStarted:{write(JSON.stringify({url:root.url,key:root.issued}));stdinEnabled=false}
    onExited:function(code){
      deadline.stop()
      if(root.enabled && root.issued===root.generation && code===0 && reply.text.length<16384){
        try{
          var data=JSON.parse(reply.text)
          if(data.ok===true && data.key===root.issued && typeof data.source==="string"
              && root.cachePrefix && data.source.startsWith(root.cachePrefix)
              && /^[a-f0-9]{64}\.(png|jpg)$/.test(data.source.slice(root.cachePrefix.length)))root.source=data.source
        }catch(error){root.source=""}
      }
      if(root.again){root.again=false;Qt.callLater(root.refresh)}
    }
  }
}
