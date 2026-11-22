// Derived from original Omarchy Bar.qml; full MIT notice is in LICENSE.
// Nonvisual fullscreen input ownership only, not visual fade/peek policy.
import QtQuick
import Quickshell.Hyprland
import "Port/BarModel.js" as BarModel

QtObject {
  id: root
  property var screen: null
  property var dragFrame: null
  property bool hidden: false
  property bool refreshEvents: false
  readonly property bool suppressed: hidden || underFullscreen
  // Suppression must win over drag input: never retain an invisible full grab.
  function maskFor(dragging, strip, empty) { return suppressed ? empty : (dragging ? null : strip) }
  function cancelSuppressedDrag() {
    if (suppressed && dragFrame && typeof dragFrame.clearBarDrag === "function") dragFrame.clearBarDrag()
  }
  onSuppressedChanged: cancelSuppressedDrag()
  onDragFrameChanged: cancelSuppressedDrag()
  Component.onCompleted: cancelSuppressedDrag()
    readonly property bool underFullscreen: {
      var monitor = screen ? Hyprland.monitorFor(screen) : null
      var workspace = monitor ? monitor.activeWorkspace : null
      return !!workspace && BarModel.fullscreenOn(Hyprland.toplevels.values, workspace.id)
    }

  // Hyprland's window list does not follow fullscreen on its own, and each
  // BarPanel reads it to drop its input under a fullscreen window.
  property Connections eventConnection: Connections {
    target: Hyprland
    enabled: root.refreshEvents
    function onRawEvent(event) {
      if (event && String(event.name) === "fullscreen") Hyprland.refreshToplevels()
    }
  }

}
