import QtQuick
import qs.Ui
import qs.Commons

// Authored trial frame, NOT the original Omarchy Bar.qml.
Item {
  id: root
  readonly property string labelText: label.displayText
  readonly property real labelWidth: label.implicitWidth
  readonly property int spacerWidth: spacer.implicitWidth
  readonly property bool actionsDisabled: !label.enabled
  readonly property QtObject passiveBar: QtObject {
    readonly property bool vertical: false
    readonly property int barSize: 32
    readonly property string fontFamily: "JetBrainsMono Nerd Font"
    readonly property color barForeground: "#cacccc"
    readonly property color urgent: "#ee8888"
    readonly property bool foregroundAnimationEnabled: false
    // Compatibility callbacks only: no popup, registration, command or IPC.
    function showTooltip(item, text) {}
    function hideTooltip(item) {}
  }
  implicitWidth: 960
  implicitHeight: 32
  Rectangle { anchors.fill: parent; color: "#101315" }
  Spacer {
    id: spacer
    bar: root.passiveBar
    settings: Object.freeze({size:12})
    height: parent.height
  }
  ClockLabel {
    id: label
    bar: root.passiveBar
    settings: Object.freeze({format:"dddd HH:mm"})
    enabled: false
    anchors.centerIn: parent
    width: implicitWidth
    height: parent.height
  }
}
