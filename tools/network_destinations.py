"""Narrow Ubuntu derivations of the pinned original Network destinations (MIT)."""


def derive_overlay(data):
    from network_frontend import replace
    text = data.decode()
    text = replace(text, 'property int shownKeyboardFocus: WlrKeyboardFocus.Exclusive',
                   'property int shownKeyboardFocus: WlrKeyboardFocus.OnDemand')
    text = replace(text, '  property var targetScreen: null',
                   '  property var preferredScreen: null\n  property var targetScreen: null')
    text = replace(text, 'targetScreen = shown ? focusedScreen() : null',
                   'targetScreen = shown ? (preferredScreen || focusedScreen()) : null')
    return ('// Ubuntu: OnDemand ownership; prefer the invoking output. Original MIT source.\n' + text).encode()


def derive_speed_overlay(data):
    from network_frontend import replace
    text = data.decode()
    text = replace(text, 'WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive',
                   'WlrLayershell.keyboardFocus: open ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None')
    text = replace(text, '  visible: open',
                   '  property var targetScreen: null\n  screen: targetScreen\n  visible: open')
    return ('// Ubuntu: OnDemand focus on the invoking output. Original gauge cluster retained.\n' + text).encode()


def derive_qr(data):
    from network_frontend import block, replace
    source = data.decode()
    overlay = block(source, '  OverlayWindow {\n')
    # Plaintext password retrieval/reveal is explicitly outside this admission.
    password_label = block(source, '          Text {\n            textFormat: Text.PlainText\n            visible: root.showingQr && root.secured\n')
    overlay = replace(overlay, password_label, '')
    overlay = replace(overlay, '    shown: root.opened',
                      '    shown: root.opened\n    preferredScreen: root.targetScreen')
    return ('''// Derived original wifiqr/Panel.qml scrim, title, canvas and states (MIT).
// Ubuntu matrix backend; no plaintext password reveal or upstream helper.
import QtQuick
import QtQuick.Layouts
import Quickshell.Wayland
import qs.Commons
import qs.Ui
WifiQrController {
  id: root
''' + overlay + '''
  Connections {
    target: root
    function onOpenedChanged() {
      if (root.opened) Qt.callLater(function() { if (root.opened) keyCatcher.forceActiveFocus() })
    }
  }
}
''').encode()


def derive_speed(data):
    from network_frontend import block, replace
    source = data.decode()
    overlay = block(source, '  SpeedTestOverlay {\n')
    overlay = replace(overlay, '    fontFamily: Style.font.family',
                      '    fontFamily: Style.font.family\n    targetScreen: root.targetScreen')
    overlay = replace(overlay, '.arg("speed.omarchy.org")', '.arg("speed.cloudflare.com")')
    return ('''// Derived original speedtest/Panel.qml overlay wiring (MIT).
// Bounded sequential Ubuntu measurements; no upstream shell/helper execution.
import QtQuick
import qs.Commons
import qs.Ui
NetworkSpeedController {
  id: root
''' + overlay + '\n}\n').encode()
