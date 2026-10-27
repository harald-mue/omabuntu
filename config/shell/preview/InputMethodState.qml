pragma Singleton
import QtQuick

// Restricted authored replacement for the upstream Commons/InputMethodState,
// which spawns Omarchy's fcitx/ibus indicator script (not ported). The seat
// reads xkb layouts only, so the state stays empty and cycle() always
// refuses; the keyboard-layout widget then shows the xkb layout alone.
QtObject {
  readonly property var state: ({})

  function cycle(back) {
    return false
  }
}
