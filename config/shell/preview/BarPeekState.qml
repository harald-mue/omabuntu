// Derived from pinned MIT Omarchy Bar.qml; full notice in licenses/Omarchy-MIT.txt.
import QtQuick

QtObject {
  id: root
  property int barHoverCount: 0
  // True while the pointer is over any bar, widgets included.
  readonly property bool barHovered: barHoverCount > 0
  // The indicator peek, open while the pointer is on any bar. Plugins read it
  // by this name through their bar API.
  property bool centerSectionRevealHeld: false
  property bool centerHoverRevealSuppressed: false
  function setBarHovered(hovered) {
    barHoverCount = Math.max(0, barHoverCount + (hovered ? 1 : -1))
    if (barHoverCount > 0) {
      centerSectionRevealTimer.stop()
      centerSectionRevealHeld = true
    } else {
      centerSectionRevealTimer.restart()
    }
  }

  function setCenterHoverRevealSuppressed(value) {
    centerHoverRevealSuppressed = !!value
  }

  property Timer leaveDelay: Timer {
    id: centerSectionRevealTimer
    interval: 120
    // A pointer that dips off the bar and straight back leaves the peek open.
    onTriggered: if (!root.barHovered) root.centerSectionRevealHeld = false
  }

}
