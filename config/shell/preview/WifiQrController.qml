import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

// Matrix-only adapter for the original scrim. The matrix is credential-bearing:
// never log/cache it, reject late output, and clear it on every close/re-summon.
Item {
  id: root
  property bool opened: false
  property var targetScreen: null
  property string iface: ""
  property string ssid: ""
  property bool secured: false
  property var qrRows: []
  property int qrSize: 0
  property string error: ""
  property bool loading: false
  property int generation: 0
  property bool pendingShow: false
  readonly property string helper: Quickshell.env("OMABUNTU_NETWORK_HELPER") || ""
  readonly property bool showingQr: qrSize > 0 && !loading && error === ""
  readonly property color onScrim: "white"
  readonly property color onScrimDim: Qt.rgba(1, 1, 1, 0.55)
  readonly property color onScrimUrgent: "#ff6b6b"
  readonly property string fontFamily: Style.font.family

  function open(device, name, screen) {
    close()
    iface = String(device || "")
    ssid = String(name || "")
    targetScreen = screen
    opened = true
    loading = true
    pendingShow = true
    pump()
  }
  function close() {
    generation += 1
    opened = false
    pendingShow = false
    loading = false
    qrSize = 0
    qrRows = []
    ssid = ""
    iface = ""
    secured = false
    error = ""
    if (backend.running) backend.running = false
  }
  Component.onDestruction: close()
  function dismiss() { close() }
  function pump() {
    if (!opened || !pendingShow || backend.running) return
    pendingShow = false
    if (!/^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,14}$/.test(iface)
        || !helper.endsWith("/network_nm.py") || helper.indexOf(" ") >= 0) {
      loading = false
      error = I18n.t("wifiqr.generateFailed")
      return
    }
    backend.generation = generation
    backend.exec(["python3", helper, "qr", iface])
  }
  function applyResult(code, text, requestGeneration) {
    if (!opened || requestGeneration !== generation) return
    loading = false
    try {
      var data = JSON.parse(text)
      var size = Number(data.size)
      var modules = String(data.modules || "")
      if (code !== 0 || data.ok !== true || data.iface !== iface || size < 29 || size > 88
          || Math.floor(size) !== size || modules.length !== size * size || !/^[01]+$/.test(modules)) throw new Error("invalid matrix")
      var rows = []
      for (var i = 0; i < size; i++) {
        var row = modules.slice(i * size, (i + 1) * size)
        if (i < 4 || i >= size - 4) { if (/1/.test(row)) throw new Error("missing quiet zone") }
        else if (/1/.test(row.slice(0, 4) + row.slice(-4))) throw new Error("missing quiet zone")
        rows.push(row)
      }
      qrRows = rows
      qrSize = size
      ssid = String(data.ssid || ssid).slice(0, 128)
      secured = data.secured === true
      error = ""
    } catch (failure) {
      qrSize = 0
      qrRows = []
      error = I18n.t("wifiqr.generateFailed")
    }
  }
  Process {
    id: backend
    property int generation: -1
    stdout: StdioCollector { id: output; waitForEnd: true }
    onExited: function(code) {
      root.applyResult(code, output.text, generation)
      Qt.callLater(root.pump)
    }
  }
}
