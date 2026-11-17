// Derived original wifiqr/Panel.qml scrim, title, canvas and states (MIT).
// Ubuntu matrix backend; no plaintext password reveal or upstream helper.
import QtQuick
import QtQuick.Layouts
import Quickshell.Wayland
import qs.Commons
import qs.Ui
WifiQrController {
  id: root
  OverlayWindow {
    shown: root.opened
    preferredScreen: root.targetScreen
    WlrLayershell.namespace: "omarchy-network-qr"

    // Deep scrim: the floating code needs the backdrop to carry the contrast
    // on any wallpaper.
    Rectangle {
      anchors.fill: parent
      color: Qt.rgba(0, 0, 0, 0.78)

      MouseArea {
        anchors.fill: parent
        onClicked: root.dismiss()
      }
    }

    Item {
      id: keyCatcher
      anchors.fill: parent
      focus: true

      Keys.onEscapePressed: root.dismiss()

      Item {
        anchors.centerIn: parent
        width: content.implicitWidth
        height: content.implicitHeight
        // Narrow or heavily scaled outputs: shrink the whole card rather than
        // clipping it at the screen edge.
        scale: Math.min(1,
          (keyCatcher.width - Style.space(32)) / Math.max(1, width),
          (keyCatcher.height - Style.space(32)) / Math.max(1, height))

        // Swallow clicks so only the scrim outside the content dismisses.
        MouseArea { anchors.fill: parent; onClicked: {} }

        ColumnLayout {
          id: content
          anchors.fill: parent
          spacing: Style.space(16)

          Text {
            textFormat: Text.PlainText
            text: (root.ssid || "Wi-Fi").toUpperCase()
            color: root.onScrimDim
            font.family: root.fontFamily
            font.pixelSize: Style.font.caption
            font.bold: true
            font.letterSpacing: 2
            elide: Text.ElideRight
            Layout.maximumWidth: Style.space(320)
            Layout.alignment: Qt.AlignHCenter
            horizontalAlignment: Text.AlignHCenter
          }

          // Render every QR module as an integer-sized native rectangle. This
          // stays crisp and avoids temporary images and file-cache races. Only
          // the dark modules paint, so the white canvas can keep its rounded
          // corners; the spec quiet zone baked into the matrix keeps the code
          // itself clear of them.
          Rectangle {
            id: qrCanvas
            readonly property int moduleSize: root.qrSize > 0
              ? Math.max(4, Math.floor(Style.space(240) / root.qrSize))
              : 0

            visible: root.showingQr
            width: root.qrSize * moduleSize
            height: width
            color: "white"
            radius: Style.cornerRadius
            Layout.alignment: Qt.AlignHCenter

            Grid {
              anchors.fill: parent
              columns: root.qrSize
              // A mirrored QR code does not scan: modules stay left to right
              // in right-to-left languages too.
              LayoutMirroring.enabled: false

              Repeater {
                model: root.qrSize * root.qrSize

                Rectangle {
                  required property int index
                  readonly property int matrixRow: Math.floor(index / root.qrSize)
                  readonly property int matrixColumn: index % root.qrSize

                  width: qrCanvas.moduleSize
                  height: qrCanvas.moduleSize
                  color: root.qrRows[matrixRow].charAt(matrixColumn) === "1" ? "#111111" : "transparent"
                }
              }
            }
          }

          Text {
            visible: root.loading
            text: I18n.t("wifiqr.generating")
            textFormat: Text.PlainText
            color: root.onScrimDim
            font.family: root.fontFamily
            font.pixelSize: Style.font.bodySmall
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
          }

          Text {
            textFormat: Text.PlainText
            visible: root.error !== ""
            text: root.error
            color: root.onScrimUrgent
            font.family: root.fontFamily
            font.pixelSize: Style.font.bodySmall
            wrapMode: Text.Wrap
            Layout.fillWidth: true
            Layout.maximumWidth: Style.space(320)
            horizontalAlignment: Text.AlignHCenter
          }

          Text {
            visible: root.showingQr
            text: I18n.t("wifiqr.scanToJoin")
            textFormat: Text.PlainText
            color: root.onScrimDim
            font.family: root.fontFamily
            font.pixelSize: Style.font.bodySmall
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
          }


        }
      }
    }
  }
  Connections {
    target: root
    function onOpenedChanged() {
      if (root.opened) Qt.callLater(function() { if (root.opened) keyCatcher.forceActiveFocus() })
    }
  }
}
