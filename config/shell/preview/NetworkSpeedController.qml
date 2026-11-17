import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

// Original two-dial destination, bounded Ubuntu phases. Only open()/Run Again
// start traffic; closing invalidates results and terminates the owned curl group.
Item {
  id: root
  property bool opened: false
  property var targetScreen: null
  property string connectionName: ""
  property bool running: false
  property string phase: ""
  property string downloadMbps: ""
  property string uploadMbps: ""
  property string error: ""
  property int generation: 0
  property bool pendingRun: false
  readonly property string helper: Quickshell.env("OMABUNTU_NETWORK_HELPER") || ""
  readonly property real downloadValue: toMbps(downloadMbps)
  readonly property real uploadValue: toMbps(uploadMbps)
  function toMbps(raw) {
    var value = parseFloat(raw)
    return isFinite(value) && value > 0 ? value : 0
  }
  function open(name, screen) {
    close()
    targetScreen = screen
    connectionName = String(name || "")
    opened = true
    runSpeedTest()
  }
  function close() {
    generation += 1
    opened = false
    pendingRun = false
    running = false
    phase = ""
    if (backend.running) backend.running = false
  }
  Component.onDestruction: close()
  function dismiss() { close() }
  function runSpeedTest() {
    if (!opened || running) return
    downloadMbps = ""
    uploadMbps = ""
    error = ""
    running = true
    pendingRun = true
    phase = "down"
    pump()
  }
  function pump() {
    if (!opened || !pendingRun || backend.running) return
    pendingRun = false
    if (!helper.endsWith("/network_nm.py") || helper.indexOf(" ") >= 0) {
      running = false
      phase = ""
      error = I18n.t("speedtest.failed")
      return
    }
    backend.generation = generation
    backend.phase = phase
    backend.exec(["python3", helper, "speed-phase", phase])
  }
  function applyResult(code, text, requestGeneration, requestPhase) {
    if (!opened || generation !== requestGeneration || phase !== requestPhase) return
    try {
      var data = JSON.parse(text)
      var value = data.value
      if (code !== 0 || data.ok !== true || data.phase !== requestPhase
          || typeof value !== "number" || !isFinite(value) || value < 0) throw new Error("invalid measurement")
      if (requestPhase === "down") {
        downloadMbps = String(value)
        phase = "up"
        pendingRun = true
      } else {
        uploadMbps = String(value)
        phase = ""
        running = false
      }
    } catch (failure) {
      error = I18n.t("speedtest.failed")
      running = false
      pendingRun = false
      phase = ""
    }
  }
  Process {
    id: backend
    property int generation: -1
    property string phase: ""
    stdout: StdioCollector { id: output; waitForEnd: true }
    onExited: function(code) {
      root.applyResult(code, output.text, generation, phase)
      Qt.callLater(root.pump)
    }
  }
}
