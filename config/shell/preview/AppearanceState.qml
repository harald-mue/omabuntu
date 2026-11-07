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
  property var bar: ({background: "opaque", hidden: false, clock_format: "dddd HH:mm", battery_percentage: false})
  property var dock: ({position: "bottom", autohide: false, pinned: []})
  property var queue: []
  signal changed()

  function apply(data) {
    if (!data || !data.bar || !data.dock) return
    bar = data.bar
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
    if (backend.running || !queue.length) return
    var args = queue[0]
    queue = queue.slice(1)
    backend.exec(["python3", helper].concat(args))
  }
  function refresh() { request(["appearance-state"]) }
  function set(key, value) { request(["appearance-set", String(key), String(value)]) }

  property Process backend: Process {
    id: backend
    stdout: StdioCollector { id: output }
    onExited: function(code) {
      try {
        var data = JSON.parse(output.text)
        if (code === 0 && data.ok && data.appearance) root.apply(data.appearance)
        else root.errorText = data.message || "Appearance request failed."
      } catch (error) { root.errorText = "Invalid appearance response." }
      if (root.errorText) console.warn("OMABUNTU_APPEARANCE_FAILED", root.errorText)
      Qt.callLater(root.pump)
    }
  }
}
