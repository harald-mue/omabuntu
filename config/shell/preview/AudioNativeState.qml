import QtQuick
import Quickshell
import Quickshell.Io

// Shared explicit-query owner. Native setters only follow an individual action.
QtObject {
  id: root
  property bool enabled: true
  property bool granted: false
  property string menuHelper: Quickshell.env("OMABUNTU_MENU_HELPER")
  readonly property string directory: menuHelper.endsWith("/menu_model.py") && menuHelper.indexOf(" ") < 0
    ? menuHelper.slice(0, -"menu_model.py".length) : ""
  property string scope: Date.now().toString(16) + Math.floor(Math.random()*0x100000000).toString(16).padStart(8,"0")
  property var snapshot: null
  property var recovery: ({profile_history:[],control_history:[]})
  property var pendingReview: null
  property string reviewKey: ""
  property var inFlight: null
  property bool readbackPending: false
  property bool dirty: false
  property bool subscribing: false
  property string errorText: ""
  readonly property bool busy: inFlight !== null || readbackPending
  readonly property bool known: enabled && granted && !!snapshot
  readonly property bool writable: known && subscribing && !busy && !snapshot.blocked && !snapshot.profile_blocked
  function grantQueries() {
    if (!directory) { errorText = "Optional audio helpers are not configured; no process started."; return false }
    granted = true; refresh(); startEvents(); return true
  }
  function revoke() {
    granted = false; scope = Date.now().toString(16) + Math.floor(Math.random()*0x100000000).toString(16).padStart(8,"0")
    snapshot = null; pendingReview = null; subscribing = false; events.running = false
  }
  function request(op, fields, write, ack) {
    if (!enabled || !granted || inFlight || rpc.running || !directory) return false
    var packet = Object.assign({scope:scope,op:op},fields || {})
    var args = ["/usr/bin/python3",directory+"audio_controls.py","--allow-existing-user-audio-queries","--allow-local-socket-activation-risk"]
    if (write) args.push("--apply-user-audio")
    if (ack) args.push("--acknowledge-unresolved")
    inFlight = JSON.parse(JSON.stringify(packet))
    if (write || ack) readbackPending = true
    rpc.stdinEnabled = true; deadline.restart(); rpc.exec(args)
    return true
  }
  function refresh() { return request("inspect",{},false,false) }
  function reviewProfile(card, profile) {
    if (!writable) return false
    pendingReview = null; reviewKey = ""
    var matches = snapshot.cards.filter(function(row) { return row.name === card })
    if (matches.length !== 1) return false
    return request("review-profile",{card:card,profile:profile,
      card_identity:{index:matches[0].index,serial:matches[0].serial},expected:snapshot.key},false,false)
  }
  function applyProfile() {
    if (!writable || !pendingReview || !reviewKey) return false
    return request("apply-profile",{review:pendingReview,review_key:reviewKey,digest:pendingReview.digest},true,false)
  }
  function restoreProfile(token) {
    if (!known || busy) return false
    return request("restore-profile",{transaction:token},true,false)
  }
  function acknowledgeProfile(token) {
    if (!enabled || !granted || busy) return false
    return request("ack-profile",{transaction:token},false,true)
  }
  function acknowledgeControl(token) {
    if (!enabled || !granted || busy) return false
    return request("ack-control",{transaction:token},false,true)
  }
  function change(op, target, value, expected, output) {
    if (!writable || expected !== snapshot.key) return false
    return request(op,{target:target,value:value,expected:expected,output:output || null},true,false)
  }
  function historyValid(rows, profile) {
    if (!Array.isArray(rows) || rows.length > 4096) return false
    var states = profile ? ["prepared","applied","restore-prepared","restored","cancelled","acknowledged"]
      : ["prepared","confirmed","acknowledged"]
    return rows.every(function(row) {
      return row && typeof row.id === "string" && (profile
        ? /^[0-9]{8}T[0-9]{12}Z-[a-f0-9]{12}$/.test(row.id) : /^[0-9]{8}$/.test(row.id))
        && states.indexOf(row.status) >= 0 && (!profile || (typeof row.profile === "string"
          && /^[A-Za-z0-9][A-Za-z0-9_.:+(), /-]{0,255}$/.test(row.profile)))
    })
  }
  function cardsValid(cards) {
    return cards.every(function(card) {
      if (!card || typeof card.name !== "string" || !/^alsa_card\.[A-Za-z0-9_.-]{1,240}$/.test(card.name)
          || !Number.isInteger(card.index) || card.index < 0 || card.index > 4294967295
          || typeof card.serial !== "string" || !/^[1-9][0-9]{0,19}$/.test(card.serial)
          || !card.profiles || typeof card.profiles !== "object" || Array.isArray(card.profiles)) return false
      var names = Object.keys(card.profiles)
      if (names.length < 1 || names.length > 128 || names.indexOf(card.active_profile) < 0) return false
      return names.every(function(name) {
        var p = card.profiles[name]
        return /^[A-Za-z0-9][A-Za-z0-9_.:+(), /-]{0,255}$/.test(name) && p
          && typeof p.description === "string" && p.description.length <= 512
          && !/[\x00-\x1f\x7f]/.test(p.description) && typeof p.available === "boolean"
          && Number.isInteger(p.sinks) && p.sinks >= 0 && p.sinks <= 64
          && Number.isInteger(p.sources) && p.sources >= 0 && p.sources <= 64
          && Number.isInteger(p.priority) && p.priority >= 0 && p.priority <= 4294967295
      })
    })
  }
  function valid(value) {
    if (!value || typeof value.key !== "string" || !/^[a-f0-9]{64}$/.test(value.key)
        || typeof value.blocked !== "boolean" || typeof value.profile_blocked !== "boolean"
        || typeof value.partial !== "boolean" || !Array.isArray(value.sources) || !Array.isArray(value.sinks)
        || !Array.isArray(value.cards) || !Array.isArray(value.profile_history) || !Array.isArray(value.control_history)
        || value.sources.length > 512 || value.sinks.length > 512 || value.cards.length > 128
        || typeof value.default_source !== "string" || typeof value.default_sink !== "string"
        || !/^[A-Za-z0-9_.:+-]{1,256}$/.test(value.default_source)
        || !/^[A-Za-z0-9_.:+-]{1,256}$/.test(value.default_sink)
        || !cardsValid(value.cards) || !historyValid(value.profile_history, true) || !historyValid(value.control_history, false)
        || value.blocked !== (value.partial || value.control_history.length >= 4096 || value.control_history.some(function(r) { return r.status === "prepared" }))
        || value.profile_blocked !== value.profile_history.some(function(r) { return r.status === "prepared" || r.status === "restore-prepared" })) return false
    return value.sources.concat(value.sinks).every(function(row) {
      return row && typeof row.name === "string" && /^[A-Za-z0-9_.:+-]{1,256}$/.test(row.name)
        && typeof row.serial === "string" && /^[1-9][0-9]*$/.test(row.serial)
        && typeof row.volume === "number" && isFinite(row.volume) && row.volume >= 0 && row.volume <= 4
        && typeof row.muted === "boolean"
    })
  }
  function finish(code,text) {
    var sent = inFlight
    if (!sent) return
    deadline.stop(); inFlight = null
    if (!enabled || !granted || sent.scope !== scope) return
    try {
      if (text.length > 262144) throw new Error("audio-result-limit")
      var packet = JSON.parse(text)
      if (code !== 0 || packet.ok !== true || packet.scope !== scope)
        throw new Error(typeof packet.error === "string" && /^[a-z0-9-]{1,96}$/.test(packet.error)
          ? packet.error : "audio-request-refused-or-uncertain")
      var data = packet.result
      if (sent.op === "inspect") {
        if (!valid(data)) throw new Error("invalid-audio-observation")
        snapshot = data; recovery = {profile_history:data.profile_history,control_history:data.control_history}
        pendingReview = null; reviewKey = ""
        readbackPending = false
        errorText = subscribing ? "" : "Audio events unavailable; writes stay disabled until an explicit reconnect."
      } else if (sent.op === "history") {
        if (!data || !historyValid(data.profile_history, true) || !historyValid(data.control_history, false)) throw new Error("invalid-audio-history")
        recovery = data; readbackPending = false
      } else if (sent.op === "review-profile") {
        if (!data.review || !/^[a-f0-9]{64}$/.test(data.review_key) || !/^[a-f0-9]{64}$/.test(data.review.digest)
            || typeof data.review.notice !== "string" || data.review.notice.length > 2048
            || data.review.profile !== sent.profile || !data.review.before || !data.review.before.card
            || data.review.before.card.name !== sent.card
            || data.review.before.card.index !== sent.card_identity.index
            || data.review.before.card.serial !== sent.card_identity.serial) throw new Error("invalid-profile-review")
        pendingReview = data.review; reviewKey = data.review_key; errorText = ""
      } else {
        pendingReview = null; reviewKey = ""
        errorText = "Request finished; awaiting observed audio state."
        dirty = true
      }
    } catch(error) {
      snapshot = null; pendingReview = null; reviewKey = ""
      errorText = "Audio backend: " + String(error.message || "unavailable")
        + ". Request refused or uncertain; no automatic retry or compensation. Check recovery below."
      if (sent.op !== "inspect" && sent.op !== "history") dirty = true
      if (sent.op === "inspect") Qt.callLater(function(){root.request("history",{},false,false)})
    }
    if (dirty) { dirty = false; Qt.callLater(root.refresh) }
  }
  function invalidate() {
    // Retain only last-observed presentation through local action readback;
    // readbackPending independently fences every subsequent write.
    if (!readbackPending) snapshot = null
    pendingReview = null; reviewKey = ""
    if (inFlight || rpc.running) dirty = true
    else refreshDelay.restart()
  }
  function startEvents() {
    if (!enabled || !granted || !directory || events.running) return
    subscribing = false; events.ownerScope = scope
    events.exec(["/usr/bin/python3",directory+"audio_events.py","--allow-existing-user-audio-queries","--allow-local-socket-activation-risk"])
  }
  onEnabledChanged: {
    scope = Date.now().toString(16) + Math.floor(Math.random()*0x100000000).toString(16).padStart(8,"0")
    snapshot = null; pendingReview = null; subscribing = false; events.running = false
    if (enabled && granted) { Qt.callLater(root.refresh); Qt.callLater(root.startEvents) }
  }
  property Timer refreshDelay: Timer { interval:100; onTriggered:root.refresh() }
  property Timer deadline: Timer {
    interval:75000
    onTriggered: {
      root.inFlight=null; root.snapshot=null; root.pendingReview=null
      root.errorText="Audio request timed out; review private recovery receipts before another action."
      rpc.running=false
    }
  }
  property Process rpc: Process {
    stdout:StdioCollector{id:reply}
    onStarted:{write(JSON.stringify(root.inFlight));stdinEnabled=false}
    onExited:function(code){root.finish(code,reply.text)}
  }
  property Process events: Process {
    property string ownerScope: ""
    stdout: SplitParser {
      onRead: function(line) {
        if (!root.enabled || !root.granted || events.ownerScope !== root.scope) return
        if (line === "ready") {
          root.subscribing = true
          if (root.known && !root.busy) root.errorText = ""
        } else if (line === "changed" && root.subscribing) root.invalidate()
        else {
          root.subscribing = false; events.running = false; root.snapshot = null
          root.errorText = "Invalid audio event stream. Refresh explicitly to reconnect."
        }
      }
    }
    onExited: {
      if (events.ownerScope !== root.scope) {
        if (root.enabled && root.granted) Qt.callLater(root.startEvents)
        return
      }
      root.subscribing = false
      if (root.enabled && root.granted) {
        root.snapshot = null
        root.errorText = "Audio subscription ended; refresh explicitly to reconnect."
      }
    }
  }
}
