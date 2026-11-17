import QtQuick
import Quickshell.Hyprland
import qs.Commons

// Select the original monitor-local widget only after an approved coordinated
// policy deployment. Old installed profiles retain their global adapter.
Item {
  id: root
  property real maximumWidth: 100000
  property QtObject bar: null
  readonly property bool monitorLocal: TrialDesktopState.monitorLocalPolicy
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
    Loader {
      sourceComponent: root.monitorLocal ? monitorLocalWidget : globalWidget
    }
  }
  Component {
    id: monitorLocalWidget
    MonitorWorkspaces {
      bar: root.bar
      liveModes: root.liveModes
    }
  }
  Component {
    id: globalWidget
    WorkspaceSwitcher {
      activeId: root.activeId
      liveModes: root.liveModes
      onFocusRequested: function(workspaceId) { root.focusWorkspace(workspaceId) }
    }
  }
}
