"""Original-panel navigation and explicitly expanded Ubuntu profile controls."""


def navigation(text):
    from network_frontend import between, replace
    keys = between(text, "      onMoveRequested: function(dx, dy) {\n", "    Column {\n      id: column\n")
    old = (
        "            } else if (root.wifiNetworks.length > 0) {\n"
        "              root.focusSection = \"wifi\"\n"
        "              if (root.selectedIndex < 0) root.selectedIndex = 0\n"
        "            }\n"
        "          } else {  // wifi\n"
        "            // k from the top row escapes back up to the DNS row rather than\n"
        "            // wrapping around to the bottom of the list.\n"
        "            if (dy < 0 && root.selectedIndex <= 0) {\n"
        "              root.focusSection = \"dns\"\n"
        "              root.wifiActionFocused = false\n"
        "            }\n"
    )
    new = (
        "            } else if (root.ethernetProfiles.length > 0) {\n"
        "              root.focusSection = \"ethernet\"\n"
        "              root.profileIndex = 0\n"
        "            } else if (root.vpnProfiles.length > 0) {\n"
        "              root.focusSection = \"vpn\"\n"
        "              root.profileIndex = 0\n"
        "            } else if (root.wifiNetworks.length > 0) {\n"
        "              root.focusSection = \"wifi\"\n"
        "              if (root.selectedIndex < 0) root.selectedIndex = 0\n"
        "            }\n"
        "          } else if (root.focusSection === \"ethernet\" || root.focusSection === \"vpn\") {\n"
        "            root.moveProfileCursor(dy)\n"
        "          } else {  // wifi\n"
        "            // k from the top row escapes back up to the DNS row rather than\n"
        "            // wrapping around to the bottom of the list.\n"
        "            if (dy < 0 && root.selectedIndex <= 0) {\n"
        "              if (root.vpnProfiles.length > 0) { root.focusSection = \"vpn\"; root.profileIndex = root.vpnProfiles.length - 1 }\n"
        "              else if (root.ethernetProfiles.length > 0) { root.focusSection = \"ethernet\"; root.profileIndex = root.ethernetProfiles.length - 1 }\n"
        "              else root.focusSection = \"dns\"\n"
        "              root.wifiActionFocused = false\n"
        "            }\n"
    )
    keys = replace(keys, old, new)
    keys = replace(
        keys,
        "          else if (root.focusSection === \"wifi\") root.selectWifiActionByDelta(dx)\n",
        "          else if (root.focusSection === \"ethernet\" || root.focusSection === \"vpn\") root.selectProfileByDelta(dx)\n"
        "          else if (root.focusSection === \"wifi\") root.selectWifiActionByDelta(dx)\n")
    keys = keys.replace("root.ethernetProfiles.length > 0", "(root.profilesOpen && root.ethernetProfiles.length > 0)")
    keys = keys.replace("root.vpnProfiles.length > 0", "(root.profilesOpen && root.vpnProfiles.length > 0)")
    keys = replace(keys, 'else if (t === "w" || t === "W") root.toggleNetwork()',
                   'else if (t === "w" || t === "W") root.toggleNetwork()\n        else if (t === "p" || t === "P") root.toggleProfiles()')
    return replace(
        keys,
        "          else root.activateSelected()\n",
        "          else if (root.focusSection === \"ethernet\") root.activateProfile(\"ethernet\")\n"
        "          else if (root.focusSection === \"vpn\") root.activateProfile(\"vpn\")\n"
        "          else root.activateSelected()\n")


def profile_section(kind, title_key, empty_key):
    # This is a secondary Ubuntu extension, never an original-panel replacement.
    return '''
      Column {
        visible: root.profilesOpen && root.__KIND__Profiles.length > 0
        width: parent.width
        spacing: Style.space(6)
        PanelSectionHeader {
          text: Commons.I18n.t("__TITLE__")
          foreground: root.bar.foreground
          fontFamily: root.bar.fontFamily
        }
        ListView {
          id: __KIND__ProfilesList
          width: parent.width
          height: Math.min(contentHeight, Style.space(144))
          model: root.__KIND__Profiles
          clip: true
          boundsBehavior: Flickable.StopAtBounds
          currentIndex: root.focusSection === "__KIND__" ? root.profileIndex : -1
          onCurrentIndexChanged: if (currentIndex >= 0) positionViewAtIndex(currentIndex, ListView.Contain)
          delegate: Button {
            required property var modelData
            required property int index
            width: ListView.view.width
            text: modelData.name
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            bordered: true
            active: !!modelData.active
            hasCursor: root.cursorActive && root.focusSection === "__KIND__" && root.profileIndex === index
            onHovered: function(on) {
              if (!on) return
              root.cursorActive = true
              root.focusSection = "__KIND__"
              root.profileIndex = index
            }
            onClicked: root.toggleProfile(modelData.uuid, !!modelData.active)
          }
        }
      }
'''.replace("__KIND__", kind).replace("__TITLE__", title_key)


def local_sections():
    return '''
      Column {
        visible: root.customDnsOpen
        width: parent.width
        spacing: Style.space(6)
        TextField {
          id: customDnsField
          width: parent.width
          placeholderText: Commons.I18n.t("network.customDnsPlaceholder")
          foreground: root.bar.foreground
          font.family: root.bar.fontFamily
          onAccepted: root.applyCustomDns(text)
          Keys.onEscapePressed: function(event) { root.customDnsOpen = false; event.accepted = true }
        }
        Button {
          width: parent.width
          text: Commons.I18n.t("network.setCustomDns")
          foreground: root.bar.foreground
          fontFamily: root.bar.fontFamily
          bordered: true
          onClicked: root.applyCustomDns(customDnsField.text)
        }
      }
      Button {
        visible: root.ethernetProfiles.length + root.vpnProfiles.length > 0
        width: parent.width
        text: Commons.I18n.t("network.savedProfiles") + (root.profilesOpen ? " −" : " +")
        tooltipText: Commons.I18n.t("network.savedProfilesHint")
        foreground: root.bar.foreground
        fontFamily: root.bar.fontFamily
        bordered: true
        onClicked: root.toggleProfiles()
      }
''' + profile_section("ethernet", "network.ethernetProfiles", "network.noEthernetProfiles") + profile_section("vpn", "network.vpnProfiles", "network.noVpnProfiles") + '''
      Text {
        visible: root.serviceNote !== ""
        width: parent.width
        text: root.serviceNote
        textFormat: Text.PlainText
        wrapMode: Text.WordWrap
        color: root.bar.foreground
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.bodySmall
      }
'''
