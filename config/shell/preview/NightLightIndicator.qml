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
  readonly property var nightlightService: backend && backend.known === true ? backend : null

  active: nightlightService ? nightlightService.enabled : false
  activeText: "󰔎"
  inactiveText: "󰔎"
  activeTooltipText: I18n.t("bar.dayLight")
  inactiveTooltipText: I18n.t("bar.nightLight")

  function toggle() {
    if (root.nightlightService) root.nightlightService.setNightlight(!root.active)
  }

  onPressed: function() { root.toggle() }
}
