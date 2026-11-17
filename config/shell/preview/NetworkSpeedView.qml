// Derived original speedtest/Panel.qml overlay wiring (MIT).
// Bounded sequential Ubuntu measurements; no upstream shell/helper execution.
import QtQuick
import qs.Commons
import qs.Ui
NetworkSpeedController {
  id: root
  SpeedTestOverlay {
    fontFamily: Style.font.family
    targetScreen: root.targetScreen
    layerNamespace: "omarchy-network-speedtest"
    title: root.connectionName
    leftLabel: I18n.t("speedtest.download")
    rightLabel: I18n.t("speedtest.upload")
    runAgainTooltip: I18n.t("speedtest.measureAgainVia").arg("speed.cloudflare.com")
    running: root.running
    leftValue: root.downloadValue
    rightValue: root.uploadValue
    leftLive: root.running && root.phase === "down"
    rightLive: root.running && root.phase === "up"
    error: root.error
    open: root.opened
    onCloseRequested: root.dismiss()
    onRunAgainRequested: root.runSpeedTest()
  }
}
