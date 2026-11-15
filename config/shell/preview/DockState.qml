import QtQuick
import Quickshell
import Quickshell.Io

// Shared dock preferences. Queue absolute edits and project them over confirmed
// state so a busy helper or an older response cannot erase the latest choice.
QtObject {
  id: root
  property string helper: Quickshell.env("OMABUNTU_DOCK_HELPER")
  property var confirmed: ({position: "bottom", autohide: false, pinned: []})
  readonly property var projected: project()
  readonly property string position: projected.position
  readonly property bool autohide: projected.autohide
  readonly property var pinned: projected.pinned
  property bool loaded: false
  property string errorText: ""
  property var queue: []
  property var inFlight: []
  property bool finishing: false
  signal changed()

  function project() {
    var next = Object.assign({}, confirmed)
    var requests = [inFlight].concat(queue)
    for (var i = 0; i < requests.length; i++) {
      var args = requests[i]
      if (args[0] === "set-position") next.position = args[1]
      else if (args[0] === "set-autohide") next.autohide = args[1] === "on"
      else if (args[0] === "set-pinned") next.pinned = args.slice(1)
    }
    return next
  }
  function request(kind, args) {
    if (!helper || !helper.endsWith("/dock_state.py") || helper.indexOf(" ") >= 0) {
      errorText = "Dock settings helper is unavailable."
      return
    }
    // Each verb sets an absolute value; the latest pending value supersedes
    // only the same verb. Distinct edits and the initial read are preserved.
    queue = queue.filter(function(item) { return item[0] !== kind }).concat([[kind].concat(args)])
    pump()
  }
  function pump() {
    if (backend.running || finishing || !queue.length) return
    inFlight = queue[0]
    queue = queue.slice(1)
    backend.exec(["python3", helper].concat(inFlight))
  }
  function applyPreferences(data) {
    if (!data || ["top", "bottom", "left", "right"].indexOf(data.position) < 0
        || typeof data.autohide !== "boolean" || !Array.isArray(data.pinned)) return false
    confirmed = {position: data.position, autohide: data.autohide,
      pinned: data.pinned.filter(function(id) { return typeof id === "string" })}
    if (!loaded) { loaded = true; changed() }
    return true
  }
  Component.onCompleted: request("get", [])
  function setPosition(value) {
    if (["top", "bottom", "left", "right"].indexOf(value) < 0 || value === position) return
    request("set-position", [value])
  }
  function setAutohide(value) {
    if (autohide === !!value) return
    request("set-autohide", [value ? "on" : "off"])
  }
  function setPinned(ids) {
    var next = []
    for (var i = 0; i < ids.length; i++) {
      var id = typeof ids[i] === "string" ? ids[i] : ""
      if (id.length > 0 && id.indexOf(" ") < 0 && next.indexOf(id) < 0) next.push(id)
    }
    request("set-pinned", next)
  }
  property Process backend: Process {
    id: backend
    stdout: StdioCollector { id: output }
    onExited: function(code) {
      root.finishing = true
      root.inFlight = []
      try {
        var data = JSON.parse(output.text)
        if (code !== 0 || data.error || !root.applyPreferences(data)) root.errorText = "Dock settings request failed."
        else root.errorText = ""
      } catch (error) { root.errorText = "Invalid dock settings response." }
      root.finishing = false
      if (root.errorText) console.warn("OMABUNTU_DOCK_SETTINGS_FAILED", root.errorText)
      Qt.callLater(root.pump)
    }
  }
}
