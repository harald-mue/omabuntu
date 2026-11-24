import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Bluetooth

// One nonvisual owner across outputs. Startup/panel opening never starts an agent.
QtObject {
  id: root
  property bool enabled: true
  property string helper: Quickshell.env("OMABUNTU_BLUETOOTH_HELPER")
  readonly property bool configured: helper.endsWith("/helpers/bluetooth-agent") && helper.indexOf(" ") < 0
  property string scope: freshToken()
  property bool ready: false
  property var pending: null
  property var prompt: null
  property var capturedDevice: null
  property var capturedAdapter: null
  property string errorText: ""
  property bool uncertain: false
  readonly property var adapter: Bluetooth.defaultAdapter
  readonly property var devices: adapter && adapter.devices ? adapter.devices.values : []
  signal completed(string address, string status)
  function freshToken() { return Date.now().toString(16) + Math.floor(Math.random()*0x1000000000000).toString(16).padStart(12,"0") }
  function current() {
    return pending && adapter === capturedAdapter && devices.indexOf(capturedDevice) >= 0
      && capturedDevice.address === pending.address && capturedDevice.dbusPath === pending.path
      && adapter.dbusPath === pending.adapter
  }
  function send(packet) { rpc.write(JSON.stringify(Object.assign({scope:scope},packet)) + "\n") }
  function begin(device, owner, action) {
    if (!enabled || !configured || pending || uncertain || (rpc.running && !ready) || !device || owner !== adapter
        || devices.indexOf(device) < 0 || ["connecting","disconnecting","forgetting"].indexOf(action) < 0) {
      errorText = uncertain ? "Previous Bluetooth outcome is uncertain; acknowledge after checking device state."
        : "Bluetooth helper unavailable or another operation is pending; no automatic installation or fallback."
      return false
    }
    capturedDevice=device;capturedAdapter=owner
    pending=Object.freeze({token:freshToken(),address:device.address,path:device.dbusPath,adapter:owner.dbusPath,
      action:action,label:String(device.name || "Bluetooth device"),sent:false})
    prompt=null;errorText=""
    if (ready && rpc.running) issue()
    else {
      ready=false;scope=freshToken();rpc.stdinEnabled=true
      startup.restart()
      rpc.exec([helper,"--allow-owned-agent","--allow-system-bus-connection-risk","--scope="+scope])
    }
    return true
  }
  function issue() {
    if (!pending || pending.sent || !ready) return
    if (!current()) { fail("Bluetooth device/adapter changed before issuance.",false);return }
    pending=Object.freeze(Object.assign({},pending,{sent:true}))
    watchdog.restart()
    send({op:pending.action==="connecting"?"connect":pending.action==="disconnecting"?"disconnect":"forget",
      token:pending.token,path:pending.path,adapter:pending.adapter,address:pending.address,
      paired:!!capturedDevice.paired,connected:!!capturedDevice.connected})
  }
  function fail(message,unknown) {
    startup.stop();watchdog.stop();prompt=null;ready=false
    var old=pending;pending=null;capturedDevice=null;capturedAdapter=null
    errorText=message;uncertain=!!unknown;scope=freshToken();rpc.running=false
    if (old) completed(old.address,unknown?"uncertain":"error")
  }
  function cancel() {
    if (!pending) return false
    prompt=null
    if (!pending.sent) { fail("Bluetooth request cancelled before issuance.",false);rpc.running=false;return true }
    send({op:"cancel",token:pending.token});return true
  }
  function answer(id,accept,value) {
    if (!pending || !prompt || prompt.id!==id || !current() || prompt.displayOnly) return false
    send({op:"answer",token:pending.token,prompt_id:id,accept:!!accept,value:typeof value==="string"?value:""})
    return true
  }
  function acknowledge() {
    if (pending) return false
    // Acknowledgement is not cancellation, retry, restoration or proof of success.
    uncertain=false;errorText="Previous uncertainty acknowledged; no operation replayed.";return true
  }
  function receive(line) {
    try {
      if (line.length>4096) throw new Error("frame-limit")
      var value=JSON.parse(line)
      if (value.scope!==scope || !enabled) return
      if (value.event==="ready") { startup.stop();ready=true;issue();return }
      if (value.event==="unavailable") { fail("Bluetooth agent became unavailable; reconnect explicitly.",!!pending);rpc.running=false;return }
      if (!pending || value.token!==pending.token) return
      if (value.event==="result") {
        if (["observed","error","cancelled","uncertain"].indexOf(value.status)<0) throw new Error("invalid-result")
        watchdog.stop();prompt=null
        var old=pending;pending=null;capturedDevice=null;capturedAdapter=null
        uncertain=value.status==="uncertain"
        errorText=value.status==="observed"?"":value.status==="cancelled"
          ? ((value.error||"").indexOf("timeout")>=0 ? "Bluetooth pairing timed out; cancellation was confirmed." : "Bluetooth pairing cancelled.")
          :"Bluetooth: "+(/^[A-Za-z0-9.-]{1,96}$/.test(value.error||"")?value.error:"request-refused-or-uncertain")
        completed(old.address,value.status);return
      }
      if (value.event==="prompt-cleared") { if(prompt&&prompt.id===value.prompt_id)prompt=null;return }
      if (value.event==="input-invalid") { errorText="Invalid Bluetooth PIN/passkey format; nothing submitted.";return }
      if (value.event!=="prompt" || !current() || !/^[a-f0-9]{1,16}$/.test(value.prompt_id)) throw new Error("invalid-prompt")
      var kinds=["RequestPinCode","RequestPasskey","RequestConfirmation","RequestAuthorization","AuthorizeService","DisplayPinCode","DisplayPasskey"]
      if (kinds.indexOf(value.kind)<0 || (value.code!==undefined&&!/^[0-9]{6}$/.test(value.code))
          || (value.entered!==undefined&&(!Number.isInteger(value.entered)||value.entered<0||value.entered>6))
          || (value.uuid!==undefined&&!/^0000[0-9a-f]{4}-0000-1000-8000-00805f9b34fb$/.test(value.uuid))) throw new Error("invalid-agent-data")
      var codeRequired=["RequestConfirmation","DisplayPinCode","DisplayPasskey"].indexOf(value.kind)>=0
      if ((codeRequired&&!/^[0-9]{6}$/.test(value.code||""))
          || (value.kind==="DisplayPasskey"&&value.entered===undefined)
          || (value.kind==="AuthorizeService"&&!/^0000(1108|110a|110b|110c|110e|110f|1112|111e|111f|1124|1812)-0000-1000-8000-00805f9b34fb$/.test(value.uuid||"")))
        throw new Error("missing-or-unadmitted-prompt-fields")
      if (prompt && !(value.kind==="DisplayPasskey" && prompt.kind===value.kind && prompt.id===value.prompt_id
          && prompt.code===value.code && value.entered>=prompt.entered)) throw new Error("overlapping-agent-prompts")
      prompt=Object.freeze({id:value.prompt_id,kind:value.kind,code:value.code||"",entered:value.entered||0,
        uuid:value.uuid||"",displayOnly:value.kind.indexOf("Display")===0})
    } catch(error) { fail("Invalid Bluetooth helper response; outcome uncertain, no replay.",!!pending);rpc.running=false }
  }
  onAdapterChanged: if(pending&&!current()) { cancel();fail("Bluetooth adapter changed; no request replayed.",true);rpc.running=false }
  onDevicesChanged: if(pending&&!current()) { cancel();fail("Bluetooth device disappeared; outcome uncertain.",true);rpc.running=false }
  onEnabledChanged: if(!enabled && (pending || rpc.running)) {
    var unknown=!!pending&&pending.sent
    if(pending)cancel()
    fail(unknown?"Bluetooth session hidden; check the pending outcome.":"Bluetooth managed session stopped.",unknown)
  }
  property Connections adapterChanges: Connections {
    target: root.adapter
    function onEnabledChanged() {
      if(root.pending && !root.adapter.enabled) {
        root.cancel();root.fail("Bluetooth adapter switched off; outcome uncertain, no replay.",true)
      }
    }
  }
  Component.onDestruction: { if(pending)cancel();rpc.running=false }
  property Timer startup: Timer { interval:5000;onTriggered:{root.fail("Bluetooth helper missing, refused or unavailable; no installation attempted.",false);rpc.running=false} }
  property Timer watchdog: Timer { interval:128000;onTriggered:{root.fail("Bluetooth action timed out; outcome uncertain. No automatic retry.",true);rpc.running=false} }
  property Process rpc: Process {
    stdinEnabled:true
    stdout:SplitParser { onRead:data=>root.receive(data) }
    onExited: { root.ready=false;if(root.pending)root.fail("Bluetooth helper ended; check device state before retry.",root.pending.sent) }
  }
}
