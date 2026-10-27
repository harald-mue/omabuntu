import QtQuick
import Quickshell.Hyprland
import qs.Commons
import qs.Commons as Commons

// Existing global-workspace adapter, now sized by the original bar sections.
// Slots delegate to the derived Omarchy workspace switcher. Per-monitor blocks
// stay out because this session uses global workspace ids.
Item {
  id: root
  property var openApps: null
  property real maximumWidth: 100000
  readonly property color foreground: Commons.Color.bar.text
  readonly property int activeId: Hyprland.focusedWorkspace ? Hyprland.focusedWorkspace.id : -1
  readonly property string windowTitle: Hyprland.activeToplevel ? (Hyprland.activeToplevel.title || "") : ""
  property bool liveModes: false
  implicitWidth: Math.min(row.implicitWidth, Math.max(0, maximumWidth))
  implicitHeight: 26
  clip: true

  function focusWorkspace(id) {
    if (id < 1 || id > 6) return;
    if (Hyprland.usingLua)
      Hyprland.dispatch("hl.dsp.focus({ workspace = " + id + " })");
    else Hyprland.dispatch("workspace " + id);
  }

  Row {
    id: row
    height: 26
    spacing: 0
    WorkspaceSwitcher {
      id: workspaces
      activeId: root.activeId
      liveModes: root.liveModes
      onFocusRequested: function(workspaceId) { root.focusWorkspace(workspaceId) }
    }
    Item {
      id: appsButton
      width: appsLabel.implicitWidth + 16
      height: 26
      Text {
        id: appsLabel
        anchors.centerIn: parent
        text: "Apps"
        color: root.foreground
        font.family: Commons.Color.fontFamily
        font.pixelSize: 12
        renderType: Text.NativeRendering
      }
      MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: if (root.openApps) root.openApps()
      }
    }
    Item {
      width: Math.max(0, Math.min(Math.min(title.implicitWidth, 280) + 20, root.maximumWidth - workspaces.width - appsButton.width))
      height: 26
      clip: true
      Text {
        id: title
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 8
        anchors.verticalCenter: parent.verticalCenter
        textFormat: Text.PlainText
        text: root.windowTitle
        color: root.foreground
        font.family: Commons.Color.fontFamily
        font.pixelSize: 12
        renderType: Text.NativeRendering
        elide: Text.ElideRight
        opacity: 0.85
      }
    }
  }
}
