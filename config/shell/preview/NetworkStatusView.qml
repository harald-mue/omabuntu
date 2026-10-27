import QtQuick
import qs.Ui
import qs.Commons
import "Port/NetworkModel.js" as Model

// Restricted composition of original BarIconButton and PopupCard, with the
// original network icon model. This is not the complete original network
// configuration panel. It intentionally has no connection controls.
Item {
  id: root
  required property QtObject bar
  required property var state
  property bool opened: false
  readonly property string icon: state.kind === "unknown" ? "?"
    : Model.connectionIcon(state.kind, state.signal, state.connectivity)
  readonly property string statusText: {
    if (!state.available) return "NetworkManager unavailable";
    if (state.kind === "disconnected") return "Not connected";
    if (state.connectivity === "portal") return "Sign-in required";
    if (state.connectivity === "limited") return "Limited internet access";
    if (state.connectivity === "full") return "Connected";
    if (state.connectivity === "none") return "No internet access reported";
    return "Connected · internet status unknown";
  }
  implicitWidth: 26
  implicitHeight: 26
  function close() { opened = false; }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.icon
    active: root.state.connectivity === "portal" || root.state.connectivity === "limited"
    tooltipText: root.statusText
    onPressed: function(b) { if (b === Qt.LeftButton) root.opened = !root.opened; }
  }

  PopupCard {
    id: popup
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    contentWidth: fittedContentWidth(360)
    contentHeight: fittedContentHeight(content.implicitHeight, 500)
    Column {
      id: content
      width: parent.width
      spacing: 10
      Row {
        spacing: 12
        Text {
          text: root.icon
          color: root.bar.foreground
          font.family: Style.font.family
          font.pixelSize: 26
        }
        Column {
          width: content.width - 48
          spacing: 4
          Text {
            width: parent.width
            textFormat: Text.PlainText
            text: root.state.label || "Network"
            color: root.bar.foreground
            font.family: Style.font.family
            font.pixelSize: 16
            elide: Text.ElideRight
          }
          Text {
            width: parent.width
            textFormat: Text.PlainText
            text: root.statusText
            color: root.bar.foreground
            opacity: 0.7
            font.family: Style.font.family
            font.pixelSize: 11
            wrapMode: Text.Wrap
          }
        }
      }
      Repeater {
        model: root.state.devices
        delegate: Item {
          required property var modelData
          width: content.width
          implicitHeight: 32
          Text {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 98
            textFormat: Text.PlainText
            text: modelData.name + (modelData.label ? " · " + modelData.label : "")
            color: root.bar.foreground
            font.family: Style.font.family
            font.pixelSize: 12
            elide: Text.ElideRight
          }
          Text {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            textFormat: Text.PlainText
            text: modelData.connected ? (modelData.signal >= 0 ? modelData.signal + " %" : "Connected") : "Disconnected"
            color: root.bar.foreground
            opacity: 0.65
            font.family: Style.font.family
            font.pixelSize: 11
          }
        }
      }
      Text {
        width: parent.width
        textFormat: Text.PlainText
        text: "Status only · Connections cannot be changed here. VPN is neither read nor changed."
        color: root.bar.foreground
        opacity: 0.55
        font.family: Style.font.family
        font.pixelSize: 11
        wrapMode: Text.Wrap
      }
    }
  }
}
