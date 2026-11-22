import QtQuick
import qs.Commons
import qs.Ui

BarIndicator {
  id: root

  required property var backend
  enabled: !!backend && backend.known === true
  pressable: !!backend && backend.known === true && backend.writable === true
  onTooltipTextChanged: if (tooltipHovered) Qt.callLater(function() {
    if (root.tooltipHovered && root.bar) root.bar.showTooltip(root, root.tooltipText)
  })
  readonly property var notificationService: backend && backend.known === true ? backend : null
  readonly property bool dnd: notificationService ? notificationService.doNotDisturb : false

  active: dnd
  activeText: "󰂛"
  inactiveText: "󰂛"
  activeTooltipText: I18n.t("bar.allowNotifications")
  inactiveTooltipText: I18n.t("bar.silenceNotifications")

  onPressed: function() {
    if (root.notificationService) {
      root.notificationService.setDoNotDisturb(!root.notificationService.doNotDisturb)
    }
  }
}
