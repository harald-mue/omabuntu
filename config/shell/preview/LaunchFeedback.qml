import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland
import qs.Commons as Commons

// Delayed launch notice shared by the app grid and the floating dock.
// Omarchy's AppLibrary waits two seconds and then asks its OSD for glyph
// U+F14DE plus "Launching <name>…". A new toplevel or a changed active
// toplevel clears it, and it never stays longer than fifteen seconds.
// This surface draws only that message. It takes no keyboard or pointer
// input and starts no process.
PanelWindow {
  id: root
  property int launchSerial: 0
  property int launchToplevelCount: 0
  property var launchActiveToplevel: null
  property bool shown: false
  property string message: ""

  readonly property int pad: 16
  readonly property int bottomMargin: 67
  readonly property int messageGap: 11
  readonly property int maxMessageWidth: 190
  readonly property string launchGlyph: String.fromCodePoint(0xF14DE)
  readonly property color ink: Commons.Color.popups.text

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

  function toplevelCount() {
    try { return Hyprland.toplevels.values.length } catch (e) { return 0 }
  }

  function launchMessage(name) {
    var label = String(name || "")
    if (label.length === 0) return Commons.I18n.t("appLibrary.launchingApp")
    var template = Commons.I18n.t("appLibrary.launching")
    var at = template.indexOf("%1")
    if (at < 0) return template
    return template.slice(0, at) + label + template.slice(at + 2)
  }

  function windowArrived() {
    return root.toplevelCount() > root.launchToplevelCount
        || Hyprland.activeToplevel !== root.launchActiveToplevel
  }

  function begin(name) {
    root.launchSerial++
    root.launchToplevelCount = root.toplevelCount()
    root.launchActiveToplevel = Hyprland.activeToplevel
    root.message = root.launchMessage(name)
    var next = root.focusedScreen()
    if (next) root.screen = next
    launchDelay.restart()
    launchTimeout.restart()
  }

  function closeNotice(serial) {
    if (serial !== root.launchSerial) return
    launchDelay.stop()
    launchTimeout.stop()
    root.shown = false
  }

  function maybeFinish() {
    if (!launchDelay.running && !launchTimeout.running && !root.shown) return
    if (!root.windowArrived()) return
    root.closeNotice(root.launchSerial)
  }

  visible: shown
  color: "transparent"
  exclusionMode: ExclusionMode.Normal
  exclusiveZone: 0
  WlrLayershell.namespace: "omabuntu-launch"
  WlrLayershell.layer: WlrLayer.Overlay
  WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
  mask: Region {}

  anchors {
    left: true
    right: true
    bottom: true
  }
  implicitHeight: root.bottomMargin + card.implicitHeight

  Timer {
    id: launchDelay
    interval: 2000
    onTriggered: {
      if (root.windowArrived()) return
      root.shown = true
    }
  }

  Timer {
    id: launchTimeout
    interval: 15000
    onTriggered: root.closeNotice(root.launchSerial)
  }

  Connections {
    target: Hyprland.toplevels
    function onValuesChanged() { root.maybeFinish() }
  }

  Connections {
    target: Hyprland
    function onActiveToplevelChanged() { root.maybeFinish() }
  }

  Rectangle {
    id: card
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: parent.bottom
    anchors.bottomMargin: root.bottomMargin
    implicitWidth: iconBox.width + root.messageGap + messageLabel.width + root.pad * 2
    implicitHeight: root.pad * 2 + Commons.Style.font.displayLarge
    radius: Commons.Style.cornerRadius
    color: Commons.Style.alpha(Commons.Color.popups.background, 0.97)
    border.width: 2
    border.color: Commons.Color.popups.border

    Row {
      anchors.centerIn: parent
      spacing: root.messageGap

      Item {
        id: iconBox
        width: Math.ceil(Math.max(iconText.implicitWidth, iconMetrics.tightBoundingRect.width))
        height: Commons.Style.font.displayLarge

        Text {
          id: iconText
          anchors.verticalCenter: parent.verticalCenter
          text: root.launchGlyph
          textFormat: Text.PlainText
          font.family: Commons.Style.font.family
          font.pixelSize: Commons.Style.font.displayLarge
          color: root.ink
        }
      }

      Text {
        id: messageLabel
        width: Math.min(implicitWidth, root.maxMessageWidth)
        anchors.verticalCenter: parent.verticalCenter
        text: root.message
        textFormat: Text.PlainText
        elide: Text.ElideRight
        font.family: Commons.Style.font.family
        font.bold: true
        font.pixelSize: Commons.Style.font.title
        color: root.ink
      }
    }

    TextMetrics {
      id: iconMetrics
      font: iconText.font
      text: iconText.text
    }
  }
}
