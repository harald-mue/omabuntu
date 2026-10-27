import QtQuick
import qs.Commons
import qs.Commons as Commons
import qs.Ui

// Authored bar-slot wrapper for the Omarchy menu mark, mirroring upstream
// shell/plugins/menu/BarWidget.qml: left click opens the command menu's
// root route, right click opens a terminal. The upstream private-use mark
// rides the original BarIconButton through its iconComponent slot, drawn
// from the extracted outline (OmarchyMark.qml) because the binary icon font
// also carries third-party agent marks and is not imported.
Item {
  id: root
  property var bar: null
  property var openMenu: null
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    iconComponent: Component {
      OmarchyMark {
        color: root.bar && root.bar.barForeground ? root.bar.barForeground : Commons.Color.foreground
      }
    }
    onPressed: function(mouseButton) {
      if (!root.bar) return
      if (mouseButton === Qt.RightButton) {
        root.bar.run("xdg-terminal-exec")
      } else if (root.openMenu) {
        root.openMenu()
      }
    }
  }
}
