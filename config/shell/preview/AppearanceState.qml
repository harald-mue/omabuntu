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
  property string layoutErrorText: ""
  property var confirmedBar: ({background: "opaque", hidden: false, clock_format: "dddd HH:mm", battery_percentage: false, clock_settings: {}, tray_settings: {pinned: [], hidden: []}})
  // Pending field patches are shared too: an older helper response must not
  // erase a newer click, or make a second output toggle from stale arrays.
  readonly property var bar: projectBar()
  property var dock: ({position: "bottom", autohide: false, pinned: []})
  property var queue: []
  property var inFlight: []
  property bool finishing: false
  signal changed()

  function sameLayout(a, b) {
    var regions = ["left", "centerBegin", "center", "centerEnd", "right"]
    if (!a || !b || Object.keys(a).length !== regions.length || Object.keys(b).length !== regions.length) return false
    for (var i = 0; i < regions.length; i++) {
      var region = regions[i]
      if (!Array.isArray(a[region]) || !Array.isArray(b[region]) || JSON.stringify(a[region]) !== JSON.stringify(b[region])) return false
    }
    return true
  }
  function reportLayoutConflict() {
    layoutErrorText = "Bar layout changed; edit refused. Retry from the current layout."
    errorText = layoutErrorText
  }
  function projectBar() {
    var next = Object.assign({}, confirmedBar)
    next.clock_settings = Object.assign({}, confirmedBar.clock_settings || {})
    next.tray_settings = Object.assign({pinned: [], hidden: []}, confirmedBar.tray_settings || {})
    var requests = [inFlight].concat(queue)
    for (var i = 0; i < requests.length; i++) {
      var args = requests[i]
      if (args[0] !== "appearance-set") continue
      if (args[1] !== "clock-settings" && args[1] !== "tray-settings" && args[1] !== "bar-layout" && args[1] !== "bar-layout-edit") continue
      var patch = JSON.parse(args[2])
      if (args[1] === "bar-layout-edit") {
        if (sameLayout(next.bar_layout, patch.expected)) next.bar_layout = patch.layout
        continue
      }
      if (args[1] === "bar-layout") { next.bar_layout = patch; continue }
      if (args[1] === "tray-settings") next.tray_settings = Object.assign({}, next.tray_settings, patch)
      else {
        if (patch.format !== undefined) { next.clock_format = patch.format; delete patch.format }
        next.clock_settings = Object.assign({}, next.clock_settings, patch)
      }
    }
    return next
  }
  function apply(data) {
    if (!data || !data.bar || !data.dock) return false
    confirmedBar = data.bar
    dock = data.dock
    loaded = true
    errorText = layoutErrorText
    changed()
    return true
  }
  function request(args) {
    if (!helper || !helper.endsWith("/menu_model.py") || helper.indexOf(" ") >= 0) return false
    if (queue.length >= 32) { errorText = "Too many pending appearance requests."; return false }
    if (args[0] === "appearance-set" && (args[1] === "bar-layout" || args[1] === "bar-layout-edit")) {
      layoutErrorText = ""
      errorText = ""
    }
    queue = queue.concat([args])
    pump()
    return true
  }
  function pump() {
    if (backend.running || finishing || !queue.length) return
    while (queue.length) {
      var args = queue[0]
      if (args[0] === "appearance-set" && args[1] === "bar-layout-edit" && !sameLayout(confirmedBar.bar_layout, JSON.parse(args[2]).expected)) {
        queue = queue.slice(1)
        reportLayoutConflict()
        continue
      }
      inFlight = args
      queue = queue.slice(1)
      backend.exec(["python3", helper].concat(args))
      return
    }
  }
  function refresh() { request(["appearance-state"]) }
  function set(key, value) { request(["appearance-set", String(key), String(value)]) }
  function setClock(values) { if (loaded) request(["appearance-set", "clock-settings", JSON.stringify(values)]) }
  function setTray(values) { if (loaded) request(["appearance-set", "tray-settings", JSON.stringify(values)]) }
  function setLayout(values) { if (loaded) request(["appearance-set", "bar-layout", JSON.stringify(values)]) }
  function editLayout(expected, values) {
    if (!loaded || !sameLayout(values, values)) return false
    if (!sameLayout(projectBar().bar_layout, expected)) { reportLayoutConflict(); return false }
    if (sameLayout(expected, values)) return false
    return request(["appearance-set", "bar-layout-edit", JSON.stringify({expected: expected, layout: values})])
  }
  function finishResponse(code, text) {
    finishing = true
    var guarded = inFlight[0] === "appearance-set" && inFlight[1] === "bar-layout-edit"
    var success = false
    var refreshed = false
    try {
      var data = JSON.parse(text)
      if (code === 0 && data.ok === true) {
        if (!apply(data.appearance)) throw new Error("Missing appearance state")
        success = true
        refreshed = true
      } else {
        if (guarded && code === 0 && data.status === "conflict" && data.appearance) {
          if (!apply(data.appearance)) throw new Error("Missing conflict state")
          refreshed = true
        }
        errorText = data.message || "Appearance request failed."
      }
    } catch (error) { errorText = "Invalid appearance response." }
    if (!success && guarded) {
      layoutErrorText = errorText
      // Dependent expected layouts are no longer trustworthy. Independent
      // clock/tray requests remain queued; an unknown result gets one read.
      queue = queue.filter(function(args) { return !(args[0] === "appearance-set" && args[1] === "bar-layout-edit") })
      if (!refreshed) queue = [["appearance-state"]].concat(queue)
    }
    inFlight = []
    finishing = false
    if (errorText) console.warn("OMABUNTU_APPEARANCE_FAILED", errorText)
    Qt.callLater(root.pump)
  }

  property Process backend: Process {
    id: backend
    stdout: StdioCollector { id: output }
    onExited: function(code) { root.finishResponse(code, output.text) }
  }
}
