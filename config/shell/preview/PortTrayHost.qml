import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Commons as Commons
import "Port" as Port

// Original tray; live preferences belong to the shared transactional adapter.
// Isolated fixtures may omit it. This owner runs no commands or services.
Item {
  id: root
  implicitWidth: tray.implicitWidth
  implicitHeight: 26
  property var appearanceSettings: null
  property var fixturePreferences: ({ pinned: [], hidden: [] })
  readonly property var preferences: appearanceSettings ? appearanceSettings.bar.tray_settings : fixturePreferences
  // Null in isolated fixtures. The trial bar sets this so the clock, which
  // lives outside this host, shares one popout and one click-target list.
  property var popoutState: null
  readonly property int itemCount: tray.allItems.length
  readonly property alias widget: tray
  readonly property alias ownerApi: owner

  QtObject {
    id: owner
    readonly property bool vertical: false
    readonly property string position: "top"
    readonly property int barSize: 26
    readonly property color foreground: Commons.Color.bar.text
    readonly property color barForeground: foreground
    readonly property color background: Commons.Color.bar.background
    readonly property color urgent: Commons.Color.bar.active
    readonly property string fontFamily: Commons.Color.fontFamily
    readonly property bool foregroundAnimationEnabled: true
    readonly property var layoutConfig: ({ tray: [] })
    readonly property bool traySectionDragActive: false
    readonly property bool traySectionPopoutOpen: false
    property var _activePopout: null
    property var _clickTargets: []
    readonly property var activePopout: root.popoutState ? root.popoutState.activePopout : _activePopout
    readonly property var clickTargets: root.popoutState ? root.popoutState.clickTargets : _clickTargets
    // Narrow adaptations of original Bar.qml registration and Util.qml hit testing.
    function registerClickTarget(target) {
      var list = root.popoutState ? root.popoutState.clickTargets : _clickTargets
      if (target && list.indexOf(target) === -1) {
        list = list.concat([target])
        if (root.popoutState) root.popoutState.clickTargets = list
        else _clickTargets = list
      }
    }
    function unregisterClickTarget(target) {
      var list = root.popoutState ? root.popoutState.clickTargets : _clickTargets
      list = list.filter(function(item) { return item !== target; })
      if (root.popoutState) root.popoutState.clickTargets = list
      else _clickTargets = list
    }
    function itemContainsPoint(target, source, x, y) {
      if (!target || !target.contains(target.mapFromItem(source, x, y))) return false;
      for (var item = target; item; item = item.parent) {
        if (!item.visible || item.opacity === 0 || !item.enabled) return false;
        if (item.clip && !item.contains(item.mapFromItem(source, x, y))) return false;
      }
      return true;
    }
    readonly property QtObject shell: QtObject {
      function updateEntryInline(id, entry) {
        if (id !== "omarchy.tray" || !Array.isArray(entry.pinned) || !Array.isArray(entry.hidden)) return;
        var values = { pinned: entry.pinned.slice(), hidden: entry.hidden.slice() };
        if (root.appearanceSettings) root.appearanceSettings.setTray(values);
        else root.fixturePreferences = values;
      }
    }
    function switchPanelFrom(owner, direction) {
      return root.popoutState && typeof root.popoutState.switchPanelFrom === "function"
        ? root.popoutState.switchPanelFrom(owner, direction) : false;
    }
    function requestPopout(key) {
      var previous = root.popoutState ? root.popoutState.activePopout : _activePopout
      if (root.popoutState) root.popoutState.activePopout = key
      else _activePopout = key
      if (previous && previous !== key && typeof previous.close === "function") previous.close();
    }
    function releasePopout(key) {
      var current = root.popoutState ? root.popoutState.activePopout : _activePopout
      if (current !== key) return
      if (root.popoutState) root.popoutState.activePopout = null
      else _activePopout = null
    }
    // Only same-section handoff; a center popup must not fly to the tray.
    function notePopoutCard(card) {
      if (root.popoutState) root.popoutState.notePopoutCard(card, "right")
    }
    function popoutCardFor(owner) {
      return root.popoutState ? root.popoutState.popoutCardFor("right") : null
    }
    function showTooltip(item, text) {
      text = (root.appearanceSettings && root.appearanceSettings.errorText) || text;
      tooltipHost.showTooltip(item, text);
    }
    function hideTooltip(item) { tooltipHost.hideTooltip(item); }
  }

  Port.Tray {
    id: tray
    anchors.fill: parent
    bar: owner
    settings: root.preferences
    fixedEdge: "end"
  }

  BarTooltipHost {
    id: tooltipHost
    position: owner.position
    fontFamily: owner.fontFamily
  }
  BarTooltip { host: tooltipHost }
}
