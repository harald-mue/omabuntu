pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Shared across outputs. Loading must finish before any panel seeds defaults.
QtObject {
  id: root
  property var settings: ({})
  property bool ready: false
  property string errorText: ""
  property string pending: ""
  property bool loading: true
  readonly property string helper: Quickshell.env("OMABUNTU_ELSEWHEN_SETTINGS_HELPER")

  function save(entry) {
    if (!ready) return
    settings = entry
    pending = JSON.stringify(entry)
    pump()
  }

  function pump() {
    if (backend.running || !pending) return
    var snapshot = pending
    pending = ""
    backend.exec(["/usr/bin/python3", helper, "save", snapshot])
  }

  Component.onCompleted: {
    if (!helper) { errorText = "World Clock settings helper is missing."; console.warn(errorText); return }
    backend.exec(["/usr/bin/python3", helper, "load"])
  }

  property Process backend: Process {
    id: backend
    stdout: StdioCollector { id: output }
    onExited: function(code) {
      if (code !== 0) {
        root.errorText = "World Clock settings could not be " + (root.loading ? "loaded." : "saved.")
        console.warn(root.errorText)
      } else if (root.loading) {
        try {
          root.settings = JSON.parse(output.text)
          root.ready = true
          root.errorText = ""
        } catch (error) {
          root.errorText = "Invalid World Clock settings response."
          console.warn(root.errorText)
        }
      } else {
        root.errorText = ""
      }
      root.loading = false
      Qt.callLater(root.pump)
    }
  }
}
