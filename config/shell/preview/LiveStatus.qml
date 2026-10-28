import QtQuick
import Quickshell.Hyprland

// Existing global-workspace adapter, sized by the original bar sections.
// Omarchy's left side is the menu plus workspaces. This row is only the
// workspace switcher. Per-monitor blocks stay out because this session uses
// global workspace ids.
Item {
  id: root
  property real maximumWidth: 100000
  readonly property int activeId: Hyprland.focusedWorkspace ? Hyprland.focusedWorkspace.id : -1
  property bool liveModes: false
  implicitWidth: Math.min(row.implicitWidth, Math.max(0, maximumWidth))
  implicitHeight: 26
  clip: true

  function focusWorkspace(id) {
    if (id < 1 || id > 6) return;
    if (Hyprland.usingLua)
      Hyprland.dispatch("hl.dsp.focus({ workspace = " + id + " })");
    else Hyprland.dispatch("workspace " + id);
  }

  Row {
    id: row
    height: 26
    spacing: 0
    WorkspaceSwitcher {
      id: workspaces
      activeId: root.activeId
      liveModes: root.liveModes
      onFocusRequested: function(workspaceId) { root.focusWorkspace(workspaceId) }
    }
  }
}
