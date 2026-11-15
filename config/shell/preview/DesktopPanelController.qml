import QtQuick

// Shared trial lifetime/focus only. No registry, startup services or persistence.
Item {
  id: root
  required property QtObject bar
  property var panelWindow: null
  property bool opened: false
  property bool cursorActive: false
  implicitWidth: 26
  implicitHeight: 26
  function open() { opened = true; }
  function close() { opened = false; }
  function toggle() { opened = !opened; }
  function switchPanel(direction) {
    return bar && typeof bar.switchPanelFrom === "function" ? bar.switchPanelFrom(root, direction) : false;
  }
  function ensureCursorVisible(item) {
    var area = panelWindow && panelWindow.loadedContent ? panelWindow.loadedContent.scrollArea : null;
    var flick = area ? area.contentItem : null;
    if (!item || !flick || flick.contentY === undefined) return;
    var p = item.mapToItem(flick.contentItem || flick, 0, 0);
    var limit = Math.max(0, flick.contentHeight - flick.height);
    if (p.y < flick.contentY) flick.contentY = Math.max(0, p.y);
    else if (p.y + item.height > flick.contentY + flick.height)
      flick.contentY = Math.min(limit, p.y + item.height - flick.height);
  }
}
