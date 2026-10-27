"""Narrow tooltip extraction from pinned Bar.qml; no bar startup or helpers."""
from audio_frontend import between, replace


def derive_host(data):
    text = data.decode()
    checks = between(text, "  function targetTooltipHovered(target) {\n", "  function clearBarDrag() {\n")
    actions = between(text, "  function showTooltip(target, text) {\n", "  // Presence of the `bar-off` flag")
    return ('''// Derived from Omarchy Bar.qml; complete upstream MIT notice is in LICENSE.
// Only tooltip lifetime/state: no bar services, watchers or command runner.
import QtQuick
import Quickshell
Item {
  id: root
  property string position: "top"
  property string fontFamily: "JetBrainsMono Nerd Font"
  property Item tooltipTarget: null
  property string tooltipText: ""
  property bool tooltipShown: false
  property Item pendingTooltipTarget: null
  property string pendingTooltipText: ""
  property int tooltipRequest: 0
  function targetBelongsToWindow(target, window) {
    return !!target && !!window && target.QsWindow.window === window;
  }
''' + checks + actions + "}\n").encode()


def derive_window(data):
    text = data.decode()
    block = between(text, "    PopupWindow {\n      id: tooltipWindow\n", "    Component {\n      id: horizontalBar\n")
    block = "\n".join(line[4:] if line.startswith("    ") else line for line in block.splitlines()) + "\n"
    block = replace(block, "  id: tooltipWindow\n", "  id: tooltipWindow\n\n  required property QtObject host\n  readonly property var barWindow: host.tooltipTarget ? host.tooltipTarget.QsWindow.window : null\n")
    block = block.replace("root.", "host.")
    return ('''// Derived tooltip PopupWindow from Omarchy Bar.qml, not an in-bar Qt ToolTip.
// Original placement, border, plain text and screen-edge adjustment retained.
// Complete upstream MIT notice is in LICENSE.
import QtQuick
import Quickshell
import qs.Ui
import qs.Commons
import qs.Commons as Commons

''' + block).encode()
