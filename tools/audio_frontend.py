"""Reviewed source extractions, not a second hand-maintained audio layout.

Vendor parents stay byte-identical; every splice requires unique witnesses.
The output slice preserves Omarchy's hero, output section and SinkRow markup.
The input slice preserves the separator, header, input slider, native peak
meter markup and SourceRow; per-app streams stay excluded.
"""


def between(text, start, end):
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("Audio frontend extraction witness differs")
    a, b = text.index(start), text.index(end)
    if a >= b:
        raise ValueError("Audio frontend extraction boundaries reversed")
    return text[a:b]


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Audio frontend replacement witness differs")
    return text.replace(old, new)


def derive_audio(data):
    text = data.decode()
    button = between(text, "  BarIconButton {\n", "  KeyboardPanel {\n")
    wheel = between(button, "    onWheelMoved: function(delta) {\n", "\n  }\n")
    button = replace(button, wheel, "    onWheelMoved: function(delta) { root.wheel(delta) }")
    # Hero, output and input sections; the per-app streams section is excluded.
    panel = between(text, "  KeyboardPanel {\n", "          // ---- Per-app streams ----\n")
    keys = between(panel, "      onTextKey: function(t) {\n", "      ScrollView {\n")
    panel = replace(panel, keys, '''      onTextKey: function(t) {
        // 'm' mutes whatever the cursor is on: the focused section's slider.
        if ((t === "m" || t === "M") && root.cursorActive) {
          if (root.focusSection === "input") root.toggleInputMute()
          else root.toggleOutputMute()
        }
      }

''')
    panel = replace(panel, "                onMoved: function(v) { root.setOutputVolume(v) }",
                    "                onDraggingChanged: root.dragTarget = dragging ? root.current : null\n"
                    "                onMoved: function(v) { root.setOutputVolume(v) }")
    # The input slider carries the same drag-identity guard as the output one.
    panel = replace(panel, "                  onMoved: function(v) { root.setInputVolume(v) }",
                    "                  onDraggingChanged: root.dragSourceTarget = dragging ? root.source : null\n"
                    "                  onMoved: function(v) { root.setInputVolume(v) }")
    # Upstream Commons/Util.alpha is the same helper as Style.alpha here, and
    # the peak monitor runs in the provider: the controller exposes its peak
    # as root.inputPeak, so the meter markup stays byte-identical otherwise.
    panel = replace(panel, "Util.alpha(root.bar.foreground, 0.18)",
                    "Style.alpha(root.bar.foreground, 0.18)")
    panel = replace(panel, "inputPeakMonitor.peak", "root.inputPeak")
    # Close the exact upstream Column, ScrollView, key catcher and panel.
    panel += '''          Text {
            visible: root.errorText !== ""
            width: parent.width
            textFormat: Text.PlainText
            text: root.errorText
            color: root.bar.urgent
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.bodySmall
            wrapMode: Text.Wrap
          }
        }
      }
    }
  }

'''
    row = between(text, "  component SinkRow: CursorSurface {\n", "  // Input device row")
    row = replace(row, "root.sink.id === node.id", "root.sink.id === node.id && root.sink.name === node.name")
    source_row = between(text, "  // Input device row — sibling of SinkRow for the \"input\" section.\n",
                         "  // Per-app stream row")
    source_row = replace(source_row, "root.source.id === node.id",
                          "root.source.id === node.id && root.source.name === node.name")
    return ('''// Derived from Omarchy audio/Panel.qml; upstream MIT notice is in LICENSE.
// Original hero, output and input layout/cursor controls; Ubuntu backend and
// focus are separate. Streams, helpers, IPC, OSD and untyped (virtual) sources
// are not admitted.
import QtQuick
import QtQuick.Controls
import qs.Ui
import qs.Commons
import qs.Commons as Commons

AudioPanelController {
  id: root
  panelWindow: panel

''' + button + panel + row + source_row + "}\n").encode()


def derive_keyboard(data):
    text = data.decode()
    text = replace(text, "  visible: open || card.opacity > 0 || popoutSwitching", "  visible: open")
    text = replace(text, "  WlrLayershell.keyboardFocus: open\n    ? (focusPrimed ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.Exclusive)\n    : WlrKeyboardFocus.None",
                   "  WlrLayershell.keyboardFocus: open ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None")
    text = replace(text, "Util.itemContainsPoint(target, root.anchorWindow.contentItem, p.x, p.y)",
                   "root.bar.itemContainsPoint(target, root.anchorWindow.contentItem, p.x, p.y)")
    return ("// Ubuntu derivation: never acquire Exclusive focus; unmap on logical close.\n"
            "// Original prime/fade commentary below describes upstream, not this policy.\n"
            "// The retained prime timer gates bar forwarding only, not keyboard ownership.\n" + text).encode()
