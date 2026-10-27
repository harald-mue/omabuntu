import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland
import qs.Commons as Commons

// Visual layout follows Omarchy AppGrid.qml at the pinned 4.5 RC: a centered
// card, a search line, 56px icons, at most seven columns and four visible
// rows. It does not load that file. There is no drag-to-dock, uninstall,
// context menu, or helper. A selection starts DesktopEntry.execute().
PanelWindow {
  id: root
  property int selected: 0
  property bool shown: false
  property string filterText: ""
  // Set by TrialShell: the dock that previews an app dragged out of this panel.
  property var dock: null
  property bool dragging: false
  property var dragEntry: null
  property point dragPoint
  readonly property int iconSize: 56
  readonly property int labelHeight: Math.ceil(labelMetrics.height) * 2
  readonly property int cellGutter: 4
  readonly property int cellPadding: 8
  readonly property int cellWidth: Math.round(iconSize * 2.2)
  readonly property int cellHeight: cellPadding * 2 + iconSize + 6 + labelHeight
  readonly property int maxColumns: 7
  readonly property int visibleRows: 4
  readonly property int borderWidth: 2
  readonly property int contentMargin: 18
  readonly property int inset: contentMargin + borderWidth
  readonly property int headerHeight: 36
  readonly property int headerSpacing: 10
  readonly property int screenMargin: 40
  readonly property int cornerRadius: 8
  readonly property color menuText: "#cacccc"
  readonly property color menuBackground: "#101315"
  readonly property int cardWidth: Math.min(width - screenMargin * 2, maxColumns * cellWidth + inset * 2)
  readonly property int columns: Math.max(1, Math.floor((cardWidth - inset * 2) / cellWidth))
  readonly property int gridWidth: columns * cellWidth
  readonly property int cardHeight: Math.min(height - screenMargin * 2, inset * 2 + headerHeight + headerSpacing + visibleRows * cellHeight)

  visible: shown
  anchors { top: true; bottom: true; left: true; right: true }
  color: "transparent"
  exclusionMode: ExclusionMode.Normal
  exclusiveZone: 0
  WlrLayershell.namespace: "omabuntu-apps"
  WlrLayershell.layer: WlrLayer.Overlay
  WlrLayershell.keyboardFocus: shown ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

  TextMetrics {
    id: labelMetrics
    font.family: Commons.Color.fontFamily
    font.pixelSize: 12
    text: "Ag"
  }

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

  function iconSource(icon) {
    var value = String(icon || "")
    if (!value) return ""
    if (value.charAt(0) === "/") return "file://" + value
    return Quickshell.iconPath(value, true)
  }

  function rebuild() {
    var query = String(root.filterText || "").toLowerCase()
    var values = DesktopEntries.applications.values
    var rows = []
    for (var i = 0; i < values.length; ++i) {
      var app = values[i]
      if (!app || !app.command || app.command.length === 0) continue
      var name = String(app.name || app.id || "")
      var detail = String(app.genericName || app.comment || "")
      var haystack = (name + " " + detail + " " + String(app.id || "")).toLowerCase()
      if (query && haystack.indexOf(query) === -1) continue
      rows.push({ name: name, entryId: String(app.id || ""), icon: String(app.icon || "") })
    }
    rows.sort(function(left, right) { return left.name.localeCompare(right.name) })
    results.clear()
    for (var row = 0; row < rows.length; ++row) results.append(rows[row])
    root.selected = 0
    Qt.callLater(function() { if (results.count > 0) grid.positionViewAtBeginning() })
  }

  function launchSelected() {
    if (results.count === 0) return
    var index = Math.max(0, Math.min(root.selected, results.count - 1))
    var entry = DesktopEntries.byId(results.get(index).entryId)
    if (!entry) return
    entry.execute()
    root.close()
  }

  function moveSelection(delta) {
    if (results.count === 0) return
    var next = root.selected + delta
    if (next < 0 || next >= results.count) return
    root.selected = next
    grid.positionViewAtIndex(next, GridView.Contain)
  }

  function toggle() {
    if (root.shown) root.close()
    else root.open()
  }

  function open() {
    root.screen = root.focusedScreen()
    root.filterText = ""
    root.rebuild()
    root.shown = true
    Qt.callLater(function() { keyCatcher.forceActiveFocus() })
  }

  function close() {
    if (root.dragging && root.dock) root.dock.endExternalDrag()
    root.dragging = false
    root.dragEntry = null
    root.shown = false
    root.filterText = ""
  }
  // Mirrors the original AppGrid handshake: this panel reports the pointer to
  // the dock on the same screen, which shows where the app would land.
  function dragTo(entry, point) {
    if (!entry || !root.dock) return
    if (!root.dragging) { root.dragEntry = entry; root.dragging = true }
    root.dragPoint = point
    root.dock.moveExternalDrag(root.screen, point.x, point.y)
  }
  function dropDrag() {
    var entry = root.dragEntry
    var point = root.dragPoint
    root.dragging = false
    root.dragEntry = null
    if (entry && root.dock) root.dock.dropExternalDrag(root.screen, point.x, point.y, String(entry.id || ""))
    root.close()
  }

  ListModel { id: results }

  // DesktopEntryManager publishes the initial scan through a queued callback.
  // The first open may run before that callback; update the same visible panel
  // when the catalog arrives, rather than waiting for another open().
  Connections {
    target: DesktopEntries
    function onApplicationsChanged() { if (root.shown) root.rebuild() }
  }

  GlobalShortcut {
    appid: "omabuntu"
    name: "apps"
    description: "Open the application list"
    onPressed: {
      console.log("OMABUNTU_APPS_PRESSED")
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
        if (event.key === Qt.Key_Escape) {
          if (root.filterText) root.filterText = ""
          else root.close()
        } else if (event.key === Qt.Key_Backspace) {
          root.filterText = root.filterText.slice(0, -1)
        } else if (event.key === Qt.Key_Left) {
          root.moveSelection(-1)
        } else if (event.key === Qt.Key_Right) {
          root.moveSelection(1)
        } else if (event.key === Qt.Key_Up) {
          root.moveSelection(-root.columns)
        } else if (event.key === Qt.Key_Down) {
          root.moveSelection(root.columns)
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
          root.launchSelected()
        } else if (event.text && event.text.length === 1 && event.text.charCodeAt(0) >= 32) {
          root.filterText += event.text
        } else {
          return
        }
        event.accepted = true
      }
    }

    Column {
      width: root.gridWidth
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.top: parent.top
      anchors.bottom: parent.bottom
      anchors.margins: root.contentMargin
      spacing: root.headerSpacing

      Rectangle {
        x: root.cellGutter
        width: parent.width - root.cellGutter * 2
        height: root.headerHeight
        radius: root.cornerRadius
        color: Qt.rgba(0.792, 0.800, 0.800, 0.06)
        Text {
          anchors.left: parent.left
          anchors.right: parent.right
          anchors.leftMargin: 10
          anchors.rightMargin: 10
          anchors.verticalCenter: parent.verticalCenter
          text: root.filterText || "Search apps\u2026"
          color: root.menuText
          opacity: root.filterText ? 1 : 0.58
          font.family: Commons.Color.fontFamily
          font.pixelSize: 16
          elide: Text.ElideRight
        }
      }

      GridView {
        id: grid
        width: parent.width
        height: parent.height - root.headerHeight - parent.spacing
        model: results
        clip: true
        cellWidth: root.cellWidth
        cellHeight: root.cellHeight
        boundsBehavior: Flickable.StopAtBounds
        delegate: Item {
          id: cell
          required property int index
          required property string name
          required property string entryId
          required property string icon
          width: root.cellWidth
          height: root.cellHeight

          Image {
            id: iconImage
            anchors.horizontalCenter: parent.horizontalCenter
            y: root.cellPadding
            width: root.iconSize
            height: root.iconSize
            sourceSize: Qt.size(root.iconSize * 2, root.iconSize * 2)
            source: root.iconSource(cell.icon)
            fillMode: Image.PreserveAspectFit
            asynchronous: false
            smooth: true
            mipmap: true
          }

          Text {
            anchors.centerIn: iconImage
            visible: iconImage.status !== Image.Ready
            text: cell.name ? cell.name.charAt(0) : ""
            color: root.menuText
            font.family: Commons.Color.fontFamily
            font.pixelSize: 18
          }

          Rectangle {
            anchors.centerIn: label
            width: Math.min(cell.width - root.cellGutter * 2, label.contentWidth + 12)
            height: label.contentHeight + 4
            radius: root.cornerRadius
            color: cell.index === root.selected ? Qt.rgba(0.792, 0.800, 0.800, 0.08) : "transparent"
          }

          Text {
            id: label
            anchors.top: iconImage.bottom
            anchors.topMargin: 6
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - (root.cellGutter + 6) * 2
            text: cell.name
            color: root.menuText
            font.family: Commons.Color.fontFamily
            font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
          }

          MouseArea {
            id: cellMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            property point pressPoint
            property bool moved: false
            onContainsMouseChanged: if (containsMouse) root.selected = cell.index
            onPressed: function(event) {
              cellMouse.moved = false
              cellMouse.pressPoint = cellMouse.mapToItem(root.contentItem, event.x, event.y)
            }
            onPositionChanged: function(event) {
              if (!(cellMouse.pressedButtons & Qt.LeftButton)) return
              var point = cellMouse.mapToItem(root.contentItem, event.x, event.y)
              if (!cellMouse.moved && Math.hypot(point.x - cellMouse.pressPoint.x, point.y - cellMouse.pressPoint.y) < 8) return
              cellMouse.moved = true
              root.dragTo({ id: cell.entryId }, point)
            }
            onReleased: function(event) {
              if (!cellMouse.moved) return
              cellMouse.moved = false
              root.dragPoint = cellMouse.mapToItem(root.contentItem, event.x, event.y)
              root.dropDrag()
            }
            onCanceled: if (root.dragging) root.close()
            onClicked: {
              if (cellMouse.moved || root.dragging) return
              root.selected = cell.index
              root.launchSelected()
            }
          }
        }
      }
    }
  }

  onFilterTextChanged: if (root.shown) root.rebuild()
}
