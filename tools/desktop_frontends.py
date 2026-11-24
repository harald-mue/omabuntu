"""Reviewed original panel/dock extractions; vendor parents remain unchanged.

Only visible surfaces and pure model/cursor logic are admitted. Backend actions
are implemented separately for Ubuntu. Every splice has a unique witness.
"""
from audio_frontend import between, replace
from network_frontend import block


def surface(data, name):
    text = data.decode()
    body = text[text.index("  BarIconButton {\n"):]
    if text.count("  BarIconButton {\n") != 1:
        raise ValueError("Desktop surface witness differs")
    if name == "Bluetooth":
        # Qt 6.10 Text implicitHeight can depend on the explicit height binding;
        # Column already omits invisible children, so no zero-height binding.
        body = replace(body, '        // ---------- Hero: Bluetooth icon · status ----------', '''        BluetoothPairingPrompt {
          width: parent.width
          session: root.session
          owner: root
          foreground: root.bar.foreground
          fontFamily: root.bar.fontFamily
        }
        // ---------- Hero: Bluetooth icon · status ----------''')
        body = replace(body, 'onActivateRequested: if (root.cursorActive) root.activateCursor()',
                       'onActivateRequested: if ((!root.session || !root.session.pending) && root.cursorActive) root.activateCursor()')
        body = replace(body, 'onDeleteRequested: if (root.cursorActive) root.deleteSelected()',
                       'onDeleteRequested: if ((!root.session || !root.session.pending) && root.cursorActive) root.deleteSelected()')
        body = replace(body, '              PanelSectionHeader {\n                visible: sectionTitle !== ""\n                height: visible ? implicitHeight : 0', '              PanelSectionHeader {\n                visible: sectionTitle !== ""')
        body = replace(body, 'visible: root.connectedDevices.length === 0 && root.scrollRows.length === 0', 'visible: root.errorText !== "" || (root.connectedDevices.length === 0 && root.scrollRows.length === 0)')
        body = replace(body, 'text: !root.adapter ? Commons.I18n.t("bluetooth.noBluetoothAdapter")', 'text: root.errorText !== "" ? root.errorText : !root.adapter ? Commons.I18n.t("bluetooth.noBluetoothAdapter")')
    if name == "Display":
        button = between(body, "  BarIconButton {\n", "  KeyboardPanel {\n")
        wheel = between(button, "    onWheelMoved: function(delta) {\n", "\n  }\n")
        body = replace(body, wheel, "    onWheelMoved: function(delta) { root.wheel(delta) }")
        body = replace(body, "                  brightnessDebounce.stop()\n", "")
        # Retain original text-size surface; the backend deliberately scopes it
        # to this shell rather than mutating GNOME/GTK/global font settings.
        body = replace(body, 'readonly property bool canToggle: display && (!display.enabled || root.enabledDisplayCount > 1)', 'readonly property bool canToggle: !!root.profiles // Opens reviewed profile editing; never a direct toggle.')
        body = replace(body, '          Item {\n            width: parent.width\n            height: Style.space(4)\n          }', '''          Text {
            width: parent.width
            visible: root.errorText !== ""
            text: root.errorText
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            color: root.bar.urgent
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.bodySmall
          }''')
        body = replace(body, '          // ---------- Hero: display icon · title/status ----------', '''          Button {
            width: parent.width
            text: root.profilePage ? "Back to display" : "Monitor profiles"
            iconText: root.profilePage ? "󰁍" : "󰍹"
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            focusable: true
            visible: !!root.profiles
            onClicked: { root.profilePage=!root.profilePage;if(root.profilePage)root.profiles.refresh() }
          }
          DisplayProfilesView {
            width: parent.width
            visible: root.profilePage
            owner: root.profiles
            bar: root.bar
            onBack: root.profilePage=false
          }
          Column {
            width: parent.width
            spacing: Style.space(14)
            visible: !root.profilePage
          // ---------- Hero: display icon · title/status ----------''')
        body = replace(body, '          PanelSeparator {\n            visible: root.displays.length > 1', '          PanelSeparator {\n            visible: root.displays.length > 1')
        end = "      }\n    }\n  }\n\n  component ScalePill: Button {"
        body = replace(body, end, "        } // Original normal-page column.\n"+end)
        body = replace(body, 'onActivateRequested: if (root.cursorActive)', 'onActivateRequested: if (!root.profilePage && root.cursorActive)')
        body = replace(body, '        if (!root.cursorActive) { root.cursorActive = true; return }', '        if (root.profilePage) return\n        if (!root.cursorActive) { root.cursorActive = true; return }')
        body = replace(body, 'contentHeight: panel.fittedContentHeight(panel.loadedContentHeight, Style.space(560))', 'contentHeight: panel.fittedContentHeight(panel.loadedContentHeight)')
        body = replace(body, '        clip: true', '        clip: true\n        contentHeight: panelColumn.implicitHeight\n        contentWidth: availableWidth')
    for forbidden in ("Process {", "execDetached", "ShellIpc", "omarchy-", "Util."):
        if forbidden in body:
            raise ValueError("Unsafe desktop surface: " + forbidden)
    # The static Ubuntu Row allocates the view's implicit size, unlike the
    # upstream module host. Reserve the original button slot and measured label
    # group, including three-digit percentages, instead of the base 26 px.
    dimensions = '''  implicitWidth: Math.max(button.implicitWidth, button.labelText !== ""
    ? Math.ceil(button.canvasSize + percentageMetrics.advanceWidth + Style.space(4)) : 0)
  implicitHeight: button.implicitHeight
  TextMetrics {
    id: percentageMetrics
    text: button.labelText
    font.family: button.fontFamily
    font.pixelSize: button.fontSize
  }
''' if name == "Power" else ""
    model = 'import "Port/' + name + 'Model.js" as Model\n'
    return ("// Derived from the pinned Omarchy Panel.qml, MIT; see LICENSE.\n"
            "// Original visible surface; Ubuntu actions and lifetime are separate.\n"
            "import QtQuick\nimport QtQuick.Controls\nimport Quickshell\n"
            "import qs.Ui\nimport qs.Commons\nimport qs.Commons as Commons\n" + model +
            name + "PanelController {\n  id: root\n  panelWindow: panel\n\n" + dimensions + body).encode()


def bluetooth(data):
    return surface(data, "Bluetooth")


def bluetooth_controller(data):
    text = data.decode()
    logic = between(text, '  readonly property var deviceGroups:', '  function audioSinks() {')
    logic = replace(logic, '  readonly property var deviceGroups:', '  readonly property var deviceGroups:')
    logic = logic.replace('Model.deviceRow(', 'root.projectDevice(')
    resolver = block(logic, '  function deviceFor(row) {')
    logic = replace(logic, resolver, '  function deviceFor(row) { return root.resolveRow(row); }\n')
    cursor = between(text, '  function moveCursor(delta) {', '  onOpenedChanged: {')
    cursor = cursor.replace('  // \'x\' forgets remembered devices. For connected devices this first\n  // disconnects, then removes the BlueZ pairing record via omarchy-bluetooth-device.\n', '')
    return ('// Derived pure grouping/cursor logic from Omarchy Bluetooth Panel, MIT.\n'
            'import QtQuick\nimport qs.Commons\nimport qs.Commons as Commons\n'
            'import "Port/BluetoothModel.js" as Model\nBluetoothActions {\n  id: root\n'
            '  function deviceLabel(device) { return Model.deviceLabel(device); }\n'
            '  function deviceAt(section, index) { return devicesForSection(section)[index] || null; }\n'
            + logic + cursor + '}\n').encode()


def display(data):
    return surface(data, "Display")


def power(data):
    return surface(data, "Power")


def dock(data):
    text = data.decode()
    text = replace(text, 'import "DockModel.js" as DockModel', 'import "Port/DockModel.js" as DockModel')
    text = replace(text, '  visible: !remapGuard.remapping', '  visible: true')
    text = replace(text, '"omarchy-dock"', '"omabuntu-floating-dock"')
    # The focus grab is a pure Wayland protocol component: an outside click
    # clears it and closes the context menu, exactly as upstream. Only the
    # monitor-remap guard stays excluded; the derived surface stays mapped.
    text = replace(text, block(text, '  ScreenMoveRemap {'), '')
    text = replace(text, 'Util.execDetached("omarchy-dock position " + modelData[0])', 'window.dock.setPosition(modelData[0])')
    text = replace(text, 'Util.execDetached("omarchy-dock autohide " + (window.autohide ? "off" : "on"))', 'window.dock.setAutohide(!window.autohide)')
    # Ubuntu deviation: the original window buttons of a floating workspace come
    # from the hyprbars Hyprland plugin. Until that plugin is reviewed and built,
    # the same three actions are reachable from this context menu.
    text = replace(text, '''      MenuRow {
        visible: menu.running
        text: Commons.I18n.t("dock.quit")''', '''      MenuRow {
        visible: menu.running
        text: Commons.I18n.t("dock.minimize")
        onTriggered: window.dock.minimize(menu.item)
      }

      MenuRow {
        visible: menu.running
        text: Commons.I18n.t("dock.maximize")
        onTriggered: window.dock.toggleMaximized(menu.item)
      }

      MenuRow {
        visible: menu.running
        text: Commons.I18n.t("dock.quit")''')
    text = replace(text, '      Repeater {\n        model: [["top",', '''      Text {
        width: parent.width
        visible: !!window.dock && !!window.dock.prefs && window.dock.prefs.errorText !== ""
        text: window.dock && window.dock.prefs ? window.dock.prefs.errorText : ""
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
        color: Commons.Color.popups.text
        font.family: Style.font.family
        font.pixelSize: Style.font.body
      }

      Repeater {
        model: [["top",''')
    # Original menu's app-specific management helpers are not Ubuntu launchers.
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if 'Quickshell.execDetached' in line:
            lines[i] = line[:len(line)-len(line.lstrip())] + 'window.closeMenu() // Excluded upstream management action.\n'
    text = ''.join(lines)
    for forbidden in ('execDetached', 'Process {', 'ShellIpc', 'hyprctl', 'ScreenMoveRemap', 'omarchy-', 'Util.'):
        if forbidden in text:
            raise ValueError('Dock dependency still needs review: ' + forbidden)
    return ('// Source-derived Omarchy dock window, MIT; see LICENSE.\n' + text).encode()
