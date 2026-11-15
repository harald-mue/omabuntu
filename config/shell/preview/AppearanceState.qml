import QtQuick
import Quickshell
import Quickshell.Io

// One serialized, read-only-on-start preference adapter shared by every output.
// All writes use the closed Python registry and its prestate transactions.
QtObject {
  id: root
  property string helper: Quickshell.env("OMABUNTU_MENU_HELPER")
  property bool loaded: false
  property string errorText: ""
  property var confirmedBar: ({background: "opaque", hidden: false, clock_format: "dddd HH:mm", battery_percentage: false, clock_settings: {}, tray_settings: {pinned: [], hidden: []}})
  // Pending field patches are shared too: an older helper response must not
  // erase a newer click, or make a second output toggle from stale arrays.
  readonly property var bar: projectBar()
  property var dock: ({position: "bottom", autohide: false, pinned: []})
  property var queue: []
  property var inFlight: []
  property bool finishing: false
  signal changed()

  function projectBar() {
    var next = Object.assign({}, confirmedBar)
    next.clock_settings = Object.assign({}, confirmedBar.clock_settings || {})
    next.tray_settings = Object.assign({pinned: [], hidden: []}, confirmedBar.tray_settings || {})
    var requests = [inFlight].concat(queue)
    for (var i = 0; i < requests.length; i++) {
      var args = requests[i]
      if (args[0] !== "appearance-set") continue
      if (args[1] !== "clock-settings" && args[1] !== "tray-settings") continue
      var patch = JSON.parse(args[2])
      if (args[1] === "tray-settings") next.tray_settings = Object.assign({}, next.tray_settings, patch)
      else {
        if (patch.format !== undefined) { next.clock_format = patch.format; delete patch.format }
        next.clock_settings = Object.assign({}, next.clock_settings, patch)
      }
    }
    return next
  }
  function apply(data) {
    if (!data || !data.bar || !data.dock) return
    confirmedBar = data.bar
    dock = data.dock
    loaded = true
    errorText = ""
    changed()
  }
  function request(args) {
    if (!helper || !helper.endsWith("/menu_model.py") || helper.indexOf(" ") >= 0) return
    if (queue.length >= 32) { errorText = "Too many pending appearance requests."; return }
    queue = queue.concat([args])
    pump()
  }
  function pump() {
    if (backend.running || finishing || !queue.length) return
    var args = queue[0]
    inFlight = args
    queue = queue.slice(1)
    backend.exec(["python3", helper].concat(args))
  }
  function refresh() { request(["appearance-state"]) }
  function set(key, value) { request(["appearance-set", String(key), String(value)]) }
  function setClock(values) { if (loaded) request(["appearance-set", "clock-settings", JSON.stringify(values)]) }
  function setTray(values) { if (loaded) request(["appearance-set", "tray-settings", JSON.stringify(values)]) }

  property Process backend: Process {
    id: backend
    stdout: StdioCollector { id: output }
    onExited: function(code) {
      root.finishing = true
      try {
        var data = JSON.parse(output.text)
        if (code === 0 && data.ok && data.appearance) root.apply(data.appearance)
        else root.errorText = data.message || "Appearance request failed."
      } catch (error) { root.errorText = "Invalid appearance response." }
      root.inFlight = []
      root.finishing = false
      if (root.errorText) console.warn("OMABUNTU_APPEARANCE_FAILED", root.errorText)
      Qt.callLater(root.pump)
    }
  }
}
