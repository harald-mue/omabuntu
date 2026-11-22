import QtQuick
import Quickshell
import Quickshell.Io

// One session owner for every output; never claims notification/colour ownership.
QtObject {
  id: root
  property bool enabled: false
  property string menuHelper: Quickshell.env("OMABUNTU_MENU_HELPER")
  readonly property string helper: menuHelper.endsWith("/menu_model.py") && menuHelper.indexOf(" ") < 0
    ? menuHelper.slice(0, -"menu_model.py".length) + "indicator_state.py" : ""
  property string scope: newScope()
  property var states: ({})
  property bool blocked: false
  property string errorText: ""
  readonly property bool busy: inFlight !== null
  property var inFlight: null
  property bool actionInFlight: false
  property bool readbackPending: false
  readonly property var dnd: dndService
  readonly property var nightlight: nightlightService

  function newScope() {
    return Date.now().toString(16) + Math.floor(Math.random() * 0x100000000).toString(16).padStart(8, "0")
  }
  function known(kind) { return enabled && states[kind] && states[kind].known === true }
  function writable(kind) { return known(kind) && !busy && !readbackPending && !blocked && helper !== "" }
  function active(kind) { return known(kind) && states[kind].active === true }
  function request(operation, data) {
    if (!enabled || busy || rpc.running || !helper) return false
    // Explicit optional-widget consent includes canonical user-bus connection;
    // auto-start=no fences target apps, not transport socket activation.
    var args = ["/usr/bin/python3", helper, operation, "--allow-existing-owner-queries", "--allow-session-bus-connection-risk"]
    if (operation === "set") args.push("--apply-user-indicator")
    inFlight = data
    actionInFlight = operation === "set"
    rpc.stdinEnabled = true
    requestDeadline.restart()
    rpc.exec(args)
    return true
  }
  function refresh() { return request("inspect", {scope: scope}) }
  function change(kind, desired) {
    if (!writable(kind) || typeof desired !== "boolean") return false
    // Freeze primitive identity/state proof in this event, never queue a toggle.
    return request("set", {scope: scope, kind: kind, expected: states[kind].key, desired: desired})
  }
  function validStates(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false
    var names = ["dnd", "nightlight"]
    for (var i = 0; i < names.length; ++i) {
      var state = value[names[i]]
      if (!state || typeof state.known !== "boolean") return false
      if (state.known && (typeof state.active !== "boolean" || typeof state.key !== "string" || !/^[0-9a-f]{64}$/.test(state.key))) return false
    }
    return true
  }
  function finish(code, text) {
    if (!inFlight) return
    var previous = inFlight
    var action = actionInFlight
    if (action) readbackPending = true
    inFlight = null
    actionInFlight = false
    requestDeadline.stop()
    if (!enabled || previous.scope !== scope) return
    try {
      if (text.length > 16384) throw new Error("Bounded response required")
      var data = JSON.parse(text)
      if (code !== 0 || data.ok !== true) throw new Error("Request refused")
      if (action) {
        if (["confirmed", "unchanged", "uncertain"].indexOf(data.status) < 0) throw new Error("Unknown action result")
        blocked = data.status === "uncertain"
        if (blocked) states = ({})
        errorText = blocked ? "Indicator action uncertain; review its private receipt before another action." : ""
      } else {
        if (data.schema !== 1 || data.scope !== scope || typeof data.blocked !== "boolean" || !validStates(data.states)) throw new Error("Invalid owner response")
        blocked = data.blocked
        states = data.states
        readbackPending = false
        errorText = blocked ? "Indicator actions blocked; review private receipts." : ""
      }
    } catch (error) {
      states = ({})
      if (action) blocked = true
      errorText = action ? "Indicator action not confirmed; no retry was issued." : "Indicator status unavailable."
    }
    // A confirmed action keeps the last observed delegates until fresh readback.
    // It is not optimistic state: presses stay fenced, and unknown/uncertain
    // responses still revoke admission rather than becoming inactive buttons.
    if (action) Qt.callLater(root.refresh)
  }
  onEnabledChanged: {
    scope = newScope()
    readbackPending = false
    states = ({})
    if (enabled) Qt.callLater(root.refresh)
    // Do not replay or compensate an already-issued request on hide/re-enable.
  }
  Component.onCompleted: if (enabled) Qt.callLater(root.refresh)

  property QtObject dndService: QtObject {
    readonly property bool known: root.known("dnd") === true
    readonly property bool writable: root.writable("dnd") === true
    readonly property bool doNotDisturb: root.active("dnd") === true
    function setDoNotDisturb(value) { return root.change("dnd", value) }
  }
  property QtObject nightlightService: QtObject {
    readonly property bool known: root.known("nightlight") === true
    readonly property bool writable: root.writable("nightlight") === true
    readonly property bool enabled: root.active("nightlight") === true
    function setNightlight(value) { return root.change("nightlight", value) }
  }
  // Poll only fixed booleans/colour fields while explicitly visible. This is
  // status refresh, not a timed component lifetime or an action retry.
  property Timer refreshTimer: Timer {
    interval: 8000
    repeat: true
    running: root.enabled
    onTriggered: root.refresh()
  }
  property Timer requestDeadline: Timer {
    interval: 24000
    onTriggered: {
      if (!root.inFlight) return
      var action = root.actionInFlight
      root.inFlight = null
      root.actionInFlight = false
      root.states = ({})
      root.blocked = action || root.blocked
      root.errorText = action ? "Indicator action timed out; review private receipts." : "Indicator status timed out."
      rpc.running = false
    }
  }
  property Process rpc: Process {
    id: rpc
    stdout: StdioCollector { id: output }
    onStarted: {
      write(JSON.stringify(root.inFlight))
      stdinEnabled = false
    }
    onExited: function(code) { root.finish(code, output.text) }
  }
}
