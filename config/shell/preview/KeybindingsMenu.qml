import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons as Commons

// Searchable keybindings list. Omarchy opens this from Super+K through its
// menu selector at 800 by 500. The original menu plugin also runs the whole
// command catalog, so this card keeps that selector's size and the existing
// shell colors. Choosing a row runs the binding that is already set; it does
// not create or edit bindings. Nothing here closes the card on a timer.
PanelWindow {
  id: root
  property int selected: 0
  property int generation: 0
  property int matchCount: 0
  property bool shown: false
  property string filterText: ""
  property string note: ""
  property string selectedLabel: ""
  property string activatedDispatcher: ""
  property string activatedArg: ""
  property string pendingKind: ""
  property var pendingExtra: []
  property var entries: []
  property var visibleEntries: []
  readonly property int cardWidth: Math.min(800, width - 80)
  readonly property int cardHeight: Math.min(500, height - 80)
  readonly property int borderWidth: 2
  readonly property int contentMargin: 18
  readonly property int headerHeight: 36
  readonly property int headerSpacing: 10
  readonly property int rowHeight: 32
  readonly property int cornerRadius: 8
  readonly property color menuText: "#cacccc"
  readonly property color menuBackground: "#101315"
  readonly property string rowFont: Commons.Color.fontFamily

  visible: shown
  anchors { top: true; bottom: true; left: true; right: true }
  color: "transparent"
  exclusionMode: ExclusionMode.Normal
  exclusiveZone: 0
  WlrLayershell.namespace: "omabuntu-keybindings"
  WlrLayershell.layer: WlrLayer.Overlay
  WlrLayershell.keyboardFocus: shown ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

  function focusedScreen() {
    var monitor = Hyprland.focusedMonitor
    var screens = Quickshell.screens
    if (!monitor || !screens) return screens ? screens[0] : null
    for (var i = 0; i < screens.length; ++i) {
      var match = Hyprland.monitorFor(screens[i])
      if (match && match.name === monitor.name) return screens[i]
    }
    return screens[0]
  }

  function helperPath() {
    var value = Quickshell.env("OMABUNTU_KEYBINDINGS_HELPER")
    if (value === undefined || value === null) return ""
    var text = String(value)
    if (text.indexOf("/keybindings_menu.py") !== text.length - 20 || text.indexOf(" ") !== -1) return ""
    return text
  }

  function rebuild() {
    var query = root.filterText.toLowerCase()
    var next = []
    for (var i = 0; i < root.entries.length; ++i) {
      var row = root.entries[i]
      if (!row || query && String(row.label || "").toLowerCase().indexOf(query) < 0) continue
      var label = String(row.label || "")
      var chord = String(row.chord || "")
      var action = String(row.action || "")
      var cut = label.indexOf(" \u2192 ")
      if (!chord && cut >= 0) chord = label.slice(0, cut).trim()
      if (!action && cut >= 0) action = label.slice(cut + 3).trim()
      next.push({ label: label, chord: chord, action: action,
                  dispatcher: String(row.dispatcher || ""), arg: String(row.arg || "") })
    }
    root.visibleEntries = next
    root.matchCount = next.length
    root.selected = 0
    root.selectedLabel = next.length > 0 ? next[0].label : ""
    Qt.callLater(function() { if (root.visibleEntries.length > 0) resultList.positionViewAtBeginning() })
  }

  function moveSelection(delta) {
    if (root.visibleEntries.length === 0) return
    var next = Math.max(0, Math.min(root.visibleEntries.length - 1, root.selected + delta))
    root.selected = next
    root.selectedLabel = root.visibleEntries[next].label
    resultList.positionViewAtIndex(next, ListView.Contain)
  }

  function handleKey(event) {
    if (event.key === Qt.Key_Escape) {
      if (root.filterText) root.filterText = ""
      else root.close()
      return true
    }
    if (event.key === Qt.Key_Backspace) {
      root.filterText = root.filterText.slice(0, -1)
      return true
    }
    if (event.key === Qt.Key_Up) { root.moveSelection(-1); return true }
    if (event.key === Qt.Key_Down) { root.moveSelection(1); return true }
    if (event.key === Qt.Key_PageUp) { root.moveSelection(-6); return true }
    if (event.key === Qt.Key_PageDown) { root.moveSelection(6); return true }
    if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
      root.activate()
      return true
    }
    if (event.text && event.text.length === 1 && event.text.charCodeAt(0) >= 32) {
      root.filterText += event.text
      return true
    }
    return false
  }

  function activate() {
    if (root.visibleEntries.length === 0) return
    var row = root.visibleEntries[root.selected]
    if (!row || !row.dispatcher) { root.note = "This binding has no action."; return }
    root.activatedDispatcher = row.dispatcher
    root.activatedArg = row.arg
    root.queryHelper("dispatch", [row.dispatcher, row.arg])
  }

  function finishHelper(kind, generation, text) {
    var current = generation === root.generation && root.shown
    if (current) {
      var payload = null
      try { payload = JSON.parse(String(text || "")) } catch (error) { payload = null }
      var accepted = payload && payload.ok === true
      if (kind === "list") {
        root.entries = accepted && payload.rows ? payload.rows : []
        if (!accepted) root.note = "Keybindings could not be read."
        root.rebuild()
      } else if (accepted) {
        root.close()
      } else {
        root.note = payload && payload.error === "refused"
          ? "Session actions stay on their own keys."
          : "That binding did not run."
      }
    }
    root.pump()
  }

  function pump() {
    if (!root.shown || root.pendingKind === "" || proc.running) return
    var kind = root.pendingKind
    var extra = root.pendingExtra
    root.pendingKind = ""
    root.pendingExtra = []
    root.queryHelper(kind, extra)
  }

  function queryHelper(kind, extra) {
    var helper = helperPath()
    if (helper === "") { root.note = "Keybindings helper is not configured."; return }
    if (proc.running) { root.pendingKind = kind; root.pendingExtra = extra || []; return }
    var command = ["python3", helper, kind]
    var more = extra || []
    for (var i = 0; i < more.length; ++i) command.push(String(more[i]))
    proc.kind = kind
    proc.generation = root.generation
    proc.exec(command)
  }

  function toggle() {
    if (root.shown) root.close()
    else root.open()
  }

  function open() {
    root.generation += 1
    root.screen = root.focusedScreen()
    root.filterText = ""
    root.note = ""
    root.shown = true
    root.rebuild()
    root.queryHelper("list", [])
    Qt.callLater(function() { if (root.shown) keyCatcher.forceActiveFocus() })
  }

  function close() {
    root.generation += 1
    root.shown = false
    root.filterText = ""
    root.note = ""
  }

  onFilterTextChanged: if (root.shown) root.rebuild()

  GlobalShortcut {
    appid: "omabuntu"
    name: "keybindings"
    description: "Open the keybindings menu"
    onPressed: {
      console.log("OMABUNTU_KEYBINDINGS_PRESSED")
      root.toggle()
    }
  }

  Rectangle {
    anchors.fill: parent
    color: root.menuBackground
    opacity: 0.5
  }

  MouseArea {
    anchors.fill: parent
    onClicked: root.close()
  }

  Rectangle {
    id: card
    width: root.cardWidth
    height: root.cardHeight
    anchors.centerIn: parent
    radius: root.cornerRadius
    color: root.menuBackground
    border.width: root.borderWidth
    border.color: root.menuText

    MouseArea { anchors.fill: parent; onClicked: function() {} }

    Item {
      id: keyCatcher
      anchors.fill: parent
      focus: true
      Keys.onPressed: function(event) {
        if (root.handleKey(event)) event.accepted = true
      }
    }

    Column {
      anchors.fill: parent
      anchors.margins: root.contentMargin
      spacing: root.headerSpacing

      Rectangle {
        width: parent.width
        height: root.headerHeight
        radius: root.cornerRadius
        color: Qt.rgba(0.792, 0.800, 0.800, 0.06)
        Text {
          anchors.fill: parent
          anchors.leftMargin: 10
          anchors.rightMargin: 10
          verticalAlignment: Text.AlignVCenter
          text: root.note || root.filterText || "Search keybindings\u2026"
          color: root.note ? "#ee8888" : root.menuText
          opacity: root.filterText || root.note ? 1 : 0.58
          font.family: root.rowFont
          font.pixelSize: 18
          elide: Text.ElideRight
        }
      }

      ListView {
        id: resultList
        width: parent.width
        height: parent.height - root.headerHeight - parent.spacing
        model: root.visibleEntries
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        delegate: Rectangle {
          required property int index
          required property string label
          required property string chord
          required property string action
          required property string dispatcher
          required property string arg
          width: resultList.width
          height: root.rowHeight
          radius: root.cornerRadius
          color: index === root.selected ? Qt.rgba(0.792, 0.800, 0.800, 0.08) : "transparent"
          Row {
            x: 8
            width: parent.width - 16
            height: parent.height
            spacing: 16
            Text {
              width: Math.min(340, (parent.width - parent.spacing) * 0.46)
              height: parent.height
              verticalAlignment: Text.AlignVCenter
              text: chord
              color: root.menuText
              font.family: "JetBrainsMono Nerd Font"
              font.pixelSize: 15
              elide: Text.ElideRight
            }
            Text {
              width: parent.width - Math.min(340, (parent.width - parent.spacing) * 0.46) - parent.spacing
              height: parent.height
              verticalAlignment: Text.AlignVCenter
              text: action
              color: root.menuText
              font.family: root.rowFont
              font.pixelSize: 15
              elide: Text.ElideRight
            }
          }
          MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            onEntered: root.moveSelection(index - root.selected)
            onClicked: {
              root.selected = index
              root.activate()
            }
          }
        }
      }
    }
  }

  Process {
    id: proc
    property string kind: ""
    property int generation: -1
    stdout: StdioCollector { id: out }
    onExited: function(code) { root.finishHelper(kind, generation, out.text) }
  }
}
