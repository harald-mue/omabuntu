"""Reviewed extraction of Omarchy's network connection surface.

The vendor panel stays byte-identical. The staged view keeps the original
icon, hero, connection grid, captive-portal prompt, band/DNS and Wi-Fi rows.
Ubuntu profiles are secondary, and QR/speed use source-derived destinations.
Helper processes and upstream portal/provider commands stay out.
"""


def between(text, start, end):
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("Network frontend extraction witness differs")
    a, b = text.index(start), text.index(end)
    if a >= b:
        raise ValueError("Network frontend extraction boundaries reversed")
    return text[a:b]


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Network frontend replacement witness differs")
    return text.replace(old, new)


def block(text, start):
    if text.count(start) != 1:
        raise ValueError("Network frontend block witness differs")
    index = text.index(start)
    opened = text.find("{", index)
    if opened < 0 or opened > index + len(start):
        raise ValueError("Network frontend block has no opening brace")
    depth = 0
    for cursor in range(opened, len(text)):
        depth += (text[cursor] == "{") - (text[cursor] == "}")
        if depth == 0:
            return text[index:cursor + 1]
    raise ValueError("Network frontend block is not closed")


def derive_network(data):
    text = data.decode()
    button = between(text, "  BarIconButton {\n    id: button\n",
                     "  // Keyboard-driven popup anchored to the bar widget icon.")
    hero = between(text, "      // ---------- Hero:",
                   "      Button {\n        id: portalAction\n")
    station = between(text, "      // Wi-Fi networks (only if a Wi-Fi station is available).\n",
                      "      ListView {\n        id: networkList\n")
    listing = block(text, "      ListView {\n        id: networkList\n")
    # Text.height bound to its own implicitHeight loops in Qt 6.10. Visibility
    # already removes these labels from their Columns, so those bindings are omitted.
    listing = replace(listing, "              height: visible ? implicitHeight : 0\n", "")
    row = between(text, "  component NetworkRow: CursorSurface {\n",
                  "  component DetailValue: InfoValue {\n")
    row = replace(row, "          height: visible ? implicitHeight : 0\n", "")
    row = replace(
        row,
        "        if (row.requiresCredentials && !row.isKnown) {\n"
        "          root.openPasswordPrompt(row.net.ssid)\n"
        "          return\n"
        "        }\n",
        "        if (row.isEnterprise && !row.isKnown) {\n"
        "          root.refuseEnterprise(row.net.ssid)\n"
        "          return\n"
        "        }\n"
        "        if (row.requiresCredentials && !row.isKnown) {\n"
        "          root.openPasswordPrompt(row.net.ssid)\n"
        "          return\n"
        "        }\n")
    row = replace(
        row,
        "      if (!isEnterprise) return root.connectWithPassphrase(net.ssid, root.passwordText)\n"
        "      if (root.identityText.length > 0) root.connectEnterprise(net.ssid, root.identityText, root.passwordText)\n",
        "      if (isEnterprise) {\n"
        "        root.passwordText = \"\"\n"
        "        root.identityText = \"\"\n"
        "        root.refuseEnterprise(net.ssid)\n"
        "        return\n"
        "      }\n"
        "      root.connectWithPassphrase(net.ssid, root.passwordText)\n")
    from network_sections import local_sections, navigation
    portal = between(text, "      Button {\n        id: portalAction\n",
                     "      // Connection details:")
    band = between(text, "      // Wi-Fi band selection.", "      // DNS provider selection.\n")
    dns = between(text, "      // DNS provider selection.\n",
                  "      // Wi-Fi networks (only if a Wi-Fi station is available).\n")
    details = between(text, "      // Connection details:", "      // Wi-Fi band selection.")
    info_components = text[text.index("  component DetailValue: InfoValue {\n"):text.rfind("}\n")]
    phrases = between(text, "  Timer {\n    id: connectionPhraseTimer\n", "  Timer {\n    id: actionTimeout\n")
    pills = between(text, "  component BandPill: Button {\n", "  component NetworkRow: CursorSurface {\n")
    keys = navigation(text)
    extra = local_sections()
    output = (
        "// Derived from Omarchy network/Panel.qml; upstream MIT notice is in LICENSE.\n"
        "// Original hero, connection grid, phrase transitions, band/DNS and Wi-Fi rows.\n"
        "// Ethernet and VPN profile rows are Ubuntu additions. The portal opens\n"
        "// Ubuntu's connectivity check. Two Text height bindings are omitted.\n"
        "import QtQuick\n"
        "import QtQuick.Controls\n"
        "import QtQuick.Layouts\n"
        "import Quickshell\n"
        "import Quickshell.Networking\n"
        "import qs.Ui\n"
        "import qs.Commons\n"
        "import qs.Commons as Commons\n"
        "import \"Port/NetworkModel.js\" as Model\n"
        "\n"
        "NetworkPanelController {\n"
        "  id: root\n"
        "\n"
        + button
        + "  KeyboardPanel {\n"
        "    id: panel\n"
        "    anchorItem: button\n"
        "    owner: root\n"
        "    bar: root.bar\n"
        "    open: root.opened\n"
        "    focusTarget: panel.loadedContent\n"
        "    contentWidth: panel.fittedContentWidth(Style.space(380))\n"
        "    contentHeight: panel.fittedContentHeight(panel.loadedContentHeight)\n"
        "\n"
        "    content: PanelKeyCatcher {\n"
        "      id: keyCatcher\n"
        "      property alias heroMeta: heroMeta\n"
        "      property alias customDnsField: customDnsField\n"
        "      implicitHeight: column.implicitHeight\n"
        "      anchors.fill: parent\n"
        "      blocked: root.passwordSsid !== \"\" || root.customDnsOpen\n"
        "\n"
        + keys
        + "      Column {\n"
        "        id: column\n"
        "        anchors.left: parent.left\n"
        "        anchors.right: parent.right\n"
        "        anchors.top: parent.top\n"
        "        spacing: Style.space(12)\n"
        "\n"
        + hero + portal + details + band + dns + extra + station + listing + "\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "\n"
        + "  Connections {\n"
        "    target: root\n"
        "    function onPasswordSsidChanged() {\n"
        "      if (root.passwordSsid === \"\" && root.opened) {\n"
        "        root.passwordText = \"\"\n"
        "        Qt.callLater(function() { if (panel.loadedContent) panel.loadedContent.forceActiveFocus() })\n"
        "      }\n"
        "    }\n"
        "    function onCustomDnsOpenChanged() {\n"
        "      Qt.callLater(function() {\n"
        "        if (!root.opened || !panel.loadedContent) return\n"
        "        if (root.customDnsOpen) panel.loadedContent.customDnsField.forceActiveFocus()\n"
        "        else panel.loadedContent.forceActiveFocus()\n"
        "      })\n"
        "    }\n"
        "    function onShareRequested(iface, ssid) {\n"
        "      wifiQr.active = true\n"
        "      if (wifiQr.item) wifiQr.item.open(iface, ssid, root.QsWindow.window ? root.QsWindow.window.screen : null)\n"
        "    }\n"
        "    function onSpeedRequested(connection) {\n"
        "      speedTest.active = true\n"
        "      if (speedTest.item) speedTest.item.open(connection, root.QsWindow.window ? root.QsWindow.window.screen : null)\n"
        "    }\n"
        "    function onPortalRequestChanged() {\n"
        "      if (root.portalRequest === 0 || !root.hasCaptivePortal) return\n"
        "      Quickshell.execDetached([\"xdg-open\", \"http://connectivity-check.ubuntu.com/\"])\n"
        "      root.close()\n"
        "    }\n"
        "  }\n"
        "\n"
        + phrases
        + "  Loader { id: wifiQr; active: false; source: \"WifiQrView.qml\"; onStatusChanged: if (status === Loader.Error) console.warn(\"OMABUNTU_NETWORK_QR_LOAD_FAILED\") }\n"
        + "  Loader { id: speedTest; active: false; source: \"NetworkSpeedView.qml\"; onStatusChanged: if (status === Loader.Error) console.warn(\"OMABUNTU_NETWORK_SPEED_LOAD_FAILED\") }\n"
        + pills + row + info_components + "}\n"
    )
    launch = 'Quickshell.execDetached(["xdg-open", "http://connectivity-check.ubuntu.com/"])'
    if output.count(launch) != 1:
        raise ValueError("Captive portal launch differs")
    scrubbed = output.replace(launch, "", 1)
    for forbidden in ("Process {", "Quickshell.Io", "execDetached", "nmcli", "enterpriseConnect",
                      "captivePortalUrl", "omarchy-", "ShellIpc", "bash", "FileView", "ping.archlinux",
                      "sudo", "--show-secrets"):
        if forbidden in scrubbed:
            raise ValueError("Excluded network path remains in extraction")
    return output.encode()
