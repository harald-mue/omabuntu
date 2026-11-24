"""Original audio/media OSD, no ShellIpc or arbitrary plugin startup."""
from audio_frontend import between, replace


def derive_osd(data):
    text = data.decode()
    text = replace(text, 'import Quickshell.Io\n', '')
    text = replace(text, 'import "OsdModel.js" as OsdModel', 'import "Port/OsdModel.js" as OsdModel')
    text = replace(text, between(text, '  function open(payloadJson) {\n', '  function close() {'), '')
    text = replace(text, between(text, '  ShellIpc {\n', '  OverlayWindow {\n'), '')
    text = replace(text, 'Item {\n  id: root', 'QtObject {\n  id: root')
    text = replace(text, '  Timer {\n    id: hideTimer', '  property Timer hideDelay: Timer {\n    id: hideTimer')
    for name in ('messageMetrics', 'valueMetrics', 'iconMetrics', 'widestIconMetrics'):
        text = replace(text, '  TextMetrics {\n    id: ' + name,
                       '  property TextMetrics ' + name + 'Object: TextMetrics {\n    id: ' + name)
    text = replace(text, '  OverlayWindow {\n', '  property OverlayWindow surface: OverlayWindow {\n')
    text = replace(text, '  property bool opened: false', '''  required property QtObject feedback
  property Connections feedbackConnections: Connections {
    target: root.feedback
    function onShowRequested(icon, message, value, maximum, progress) {
      root.show(icon, message, progress ? String(value) : "", String(maximum),
        progress ? Commons.I18n.formatNumber(value) + "%" : "", "1200")
    }
    function onCloseRequested() { root.close() }
  }
  property bool opened: false''')
    text = text.replace('Util.alpha(', 'Style.alpha(')
    if text.count('text: root.message') != 2 or text.count('textFormat: Text.PlainText') != 2:
        raise ValueError('Original plain-text OSD message witnesses changed')
    if any(w in text for w in ('ShellIpc', 'Process {', 'execDetached', 'function open(payloadJson)')):
        raise ValueError('Excluded OSD activation remains')
    return ('// Original measured OSD layout; narrow in-process audio-only dispatch.\n'
            '// Full upstream MIT notice in LICENSE. No native setter or IPC.\n' + text).encode()
