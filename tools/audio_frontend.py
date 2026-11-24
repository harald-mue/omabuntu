"""Reviewed source extractions, not a second hand-maintained audio layout.

Vendor parents stay byte-identical; every splice requires unique witnesses.
The output slice preserves Omarchy's hero, output section and SinkRow markup.
The input slice preserves the separator, header, input slider, native peak
meter markup and SourceRow. Playback stream sections/rows retain the original
layout with primitive snapshots and identity-checked native actions.
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
    # Preserve hero, output/input sections and the original per-app stream grid.
    panel = between(text, "  KeyboardPanel {\n", "          // ---- Per-app streams ----\n")
    keys = between(panel, "      onTextKey: function(t) {\n", "      ScrollView {\n")
    panel = replace(panel, keys, '''      onTextKey: function(t) {
        // Hidden normal-page controls cannot acquire advanced-page keys.
        if (root.advancedAudio) return
        // 'm' operates on the current section or that individual stream only.
        if ((t === "m" || t === "M") && root.cursorActive) {
          if (root.focusSection === "streams") {
            if (root.selectedIndex >= 0) root.toggleStreamMute(root.displayAudioStreams[root.selectedIndex])
          } else if (root.focusSection === "input") root.toggleInputMute()
          else root.toggleOutputMute()
        }
      }

''')
    panel = replace(panel, "                onMoved: function(v) { root.setOutputVolume(v) }",
                    "                onDraggingChanged: root.dragTarget = dragging ? root.current : null\n"
                    "                onMoved: function(v) { root.setOutputVolume(v) }")
    panel = replace(panel, '                enabled: !!root.sink',
                    '                enabled: root.outputControlAvailable')
    panel = replace(panel, 'text: Commons.I18n.formatNumber(Math.round((outputSlider.dragging ? outputSlider.liveValue : root.outputVolume) * 100)) + "%"',
                    'text: root.outputControlAvailable ? Commons.I18n.formatNumber(Math.round((outputSlider.dragging ? outputSlider.liveValue : root.outputVolume) * 100)) + "%" : "—"')
    # The original input slider needs both a captured target and live authority.
    panel = replace(panel, '                  enabled: !!root.source',
                    '                  enabled: root.inputWriteAvailable')
    panel = replace(panel, "                  onMoved: function(v) { root.setInputVolume(v) }",
                    "                  onDraggingChanged: if (dragging) root.beginInputDrag()\n"
                    "                  onMoved: function(v) { if (!dragging) root.inputDragCancelledState = false; root.setInputVolume(v) }\n"
                    "                  onReleased: function(v) { root.finishInputDrag(v) }\n"
                    "                  onEnabledChanged: if (!enabled) root.cancelInputDrag()\n"
                    "                  Connections {\n"
                    "                    target: root\n"
                    "                    function onInputDragCancelled() { inputSlider.dragging = false; inputSlider.liveValue = inputSlider.value }\n"
                    "                  }")
    # Upstream Commons/Util.alpha is the same helper as Style.alpha here, and
    # the peak monitor runs in the provider: the controller exposes its peak
    # as root.inputPeak, so the meter markup stays byte-identical otherwise.
    panel = replace(panel, "Util.alpha(root.bar.foreground, 0.18)",
                    "Style.alpha(root.bar.foreground, 0.18)")
    panel = replace(panel, "inputPeakMonitor.peak", "root.inputPeak")
    panel += between(text, "          // ---- Per-app streams ----\n",
                     "        }\n      }\n    }\n  }\n\n  // ---- Reusable inline components ----\n")
    # New capability rows join the existing cursor; m must not act on an
    # unrelated output while the cursor is on profile/recovery actions.
    panel = replace(panel, 'else root.toggleOutputMute()',
                    'else if (root.focusSection === "output" || root.focusSection === "header") root.toggleOutputMute()')
    panel = replace(panel, "panel.fittedContentHeight(panel.loadedContentHeight, Style.space(560))",
                    "panel.fittedContentHeight(panel.loadedContentHeight)")
    panel = replace(panel, "panelColumn.implicitHeight > height ? ScrollBar.AsNeeded",
                    "panelColumn.implicitHeight > availableHeight ? ScrollBar.AsNeeded")
    panel = replace(panel, "value: panelColumn.implicitHeight > scrollArea.height",
                    "value: panelColumn.implicitHeight > scrollArea.availableHeight")
    # Preserve the original normal-page markup inside one visibility wrapper.
    panel = replace(panel, "          // ---------- Hero: speaker icon · title/status ----------",
                    "          Column {\n"
                    "            id: normalAudioColumn\n"
                    "            objectName: \"audioNormalPage\"\n"
                    "            visible: !root.advancedAudio\n"
                    "            width: parent.width\n"
                    "            spacing: Style.space(14)\n"
                    "          // ---------- Hero: speaker icon · title/status ----------")
    panel = replace(panel, "        clip: true\n",
                    "        clip: true\n"
                    "        // Declare the extent of the nested pages; keep fallback scrolling reachable.\n"
                    "        contentHeight: panelColumn.implicitHeight\n"
                    "        contentWidth: availableWidth\n"
                    "        // Balanced clearance keeps content centered even while the bar fades.\n"
                    "        leftPadding: contentHeight > availableHeight\n"
                    "          ? ScrollBar.vertical.width + Style.space(10) : 0\n"
                    "        rightPadding: leftPadding\n")
    # Close the original normal-page wrapper before the advanced-page entry.
    panel += '          }\n'
    # Close the exact upstream Column, ScrollView, key catcher and panel.
    panel += '''          AudioNativeControls {
            width: parent.width
            bridge: "bridge" in root.backend ? root.backend.bridge : null
            controller: root
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
          }
          Text {
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
    stream_row = between(text, "  // Per-app stream row", "\n}\n")
    stream_row = replace(stream_row, '    required property int rowIndex\n',
                         '    required property int rowIndex\n    property var dragKey: null\n')
    stream_row = replace(stream_row, 'node && node.audio ? node.audio.volume : 0',
                         'node ? node.volume : 0')
    stream_row = replace(stream_row, 'node && node.audio ? node.audio.muted : false',
                         'node ? node.muted : false')
    # Preserve the original active-row visual; compute matching in the provider
    # with the original model and project only a frozen primitive boolean.
    stream_row = replace(stream_row, 'root.streamRepresentsPlayer(node, root.activeMediaPlayer)',
                         '!!node && node.active')
    stream_row = replace(stream_row, '''              if (streamRow.node && streamRow.node.audio)
                streamRow.node.audio.muted = !streamRow.node.audio.muted''',
                         '              root.toggleStreamMute(streamRow.node)')
    stream_row = replace(stream_row, '''        onMoved: function(v) {
          if (streamRow.node && streamRow.node.audio) streamRow.node.audio.volume = v
        }
        onRightClicked: {
          if (streamRow.node && streamRow.node.audio)
            streamRow.node.audio.muted = !streamRow.node.audio.muted
        }''', '''        onDraggingChanged: streamRow.dragKey = dragging ? streamRow.node : null
        onMoved: function(v) {
          root.setStreamVolume(dragging ? streamRow.dragKey : streamRow.node, v)
        }
        onRightClicked: root.toggleStreamMute(streamRow.node)''')
    return ('''// Derived from Omarchy audio/Panel.qml; upstream MIT notice is in LICENSE.
// Original hero, output/input and playback-stream layout/cursor controls.
// Ubuntu backend and focus are separate. MPRIS labels/active marks are read-only.
// Helpers, IPC, OSD, transport and untyped capture sources are not admitted.
import QtQuick
import QtQuick.Controls
import qs.Ui
import qs.Commons
import qs.Commons as Commons

AudioPanelController {
  id: root
  panelWindow: panel

''' + button + panel + row + source_row + stream_row + "}\n").encode()


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
