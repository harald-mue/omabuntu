// Derived from Omarchy network/Panel.qml; upstream MIT notice is in LICENSE.
// Original hero, captive-portal prompt, band row, DNS row, Wi-Fi list and row.
// Ethernet and VPN profile rows are Ubuntu additions. The portal opens
// Ubuntu's connectivity check. Two Text height bindings are omitted.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Networking
import qs.Ui
import qs.Commons
import qs.Commons as Commons
import "Port/NetworkModel.js" as Model

NetworkPanelController {
  id: root

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.icon
    active: root.restricted
    tooltipText: root.hasCaptivePortal ? Commons.I18n.t("network.signInToNetwork")
      : (root.restricted ? Commons.I18n.t("network.limitedAccess") : "")

    onPressed: function(b) {
      if (root.opened) root.close()
      // open() is enough: onOpenedChanged runs refresh(true), which defers the
      // PHY scan past the first frame. The bare refresh() that used to follow
      // took the no-scan branch and set scannerEnabled synchronously, undoing
      // that deferral and stalling the open on NetworkManager's AP flood.
      else root.open()
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: panel.loadedContent
    contentWidth: panel.fittedContentWidth(Style.space(380))
    contentHeight: panel.fittedContentHeight(panel.loadedContentHeight)

    content: PanelKeyCatcher {
      id: keyCatcher
      property alias heroMeta: heroMeta
      implicitHeight: column.implicitHeight
      anchors.fill: parent
      blocked: root.passwordSsid !== ""

      onMoveRequested: function(dx, dy) {
        if (!root.cursorActive) {
          root.cursorActive = true
          if (dy >= 0) return
        }
        if (dy !== 0) {
          // Hidden sections drop out of the keyboard chain entirely.
          if (root.focusSection === "header") {
            if (dy > 0) {
              if (root.hasCaptivePortal) {
                root.focusSection = "portal"
              } else if (root.canSelectBand) {
                root.focusSection = "band"
                root.bandAutoFocused = true
              } else {
                root.focusSection = "dns"
              }
            }
          } else if (root.focusSection === "portal") {
            if (dy < 0 && root.headerActionCount > 0) {
              root.focusSection = "header"
              root.headerIndex = 0
            } else if (dy > 0) {
              root.focusSection = root.canSelectBand ? "band" : "dns"
              root.bandAutoFocused = true
            }
          } else if (root.focusSection === "band") {
            // Automatic on the header line, then the pills -- which collapse
            // away under Automatic, leaving a single row to walk.
            if (dy < 0) {
              if (!root.bandAutoFocused) {
                root.bandAutoFocused = true
              } else if (root.hasCaptivePortal) {
                root.focusSection = "portal"
              } else if (root.headerActionCount > 0) {
                root.focusSection = "header"
                root.headerIndex = 0
              }
            } else if (root.bandAutoFocused && root.bandPillsVisible) {
              root.bandAutoFocused = false
            } else {
              root.focusSection = "dns"
            }
          } else if (root.focusSection === "dns") {
            // k from DNS moves up into the band section when it's on screen,
            // then the disconnect button; otherwise stays put. j drops into the
            // wifi list if there's anywhere to land.
            if (dy < 0) {
              if (root.canSelectBand) {
                root.focusSection = "band"
                root.bandAutoFocused = !root.bandPillsVisible
              } else if (root.hasCaptivePortal) {
                root.focusSection = "portal"
              } else if (root.headerActionCount > 0) {
                root.focusSection = "header"
                root.headerIndex = 0
              }
            } else if (root.ethernetProfiles.length > 0) {
              root.focusSection = "ethernet"
              root.profileIndex = 0
            } else if (root.vpnProfiles.length > 0) {
              root.focusSection = "vpn"
              root.profileIndex = 0
            } else if (root.wifiNetworks.length > 0) {
              root.focusSection = "wifi"
              if (root.selectedIndex < 0) root.selectedIndex = 0
            }
          } else if (root.focusSection === "ethernet" || root.focusSection === "vpn") {
            if (dy < 0) {
              if (root.focusSection === "vpn" && root.ethernetProfiles.length > 0) root.focusSection = "ethernet"
              else root.focusSection = "dns"
            } else if (root.focusSection === "ethernet" && root.vpnProfiles.length > 0) {
              root.focusSection = "vpn"
              root.profileIndex = 0
            } else if (root.wifiNetworks.length > 0) {
              root.focusSection = "wifi"
              if (root.selectedIndex < 0) root.selectedIndex = 0
            }
          } else {  // wifi
            // k from the top row escapes back up to the DNS row rather than
            // wrapping around to the bottom of the list.
            if (dy < 0 && root.selectedIndex <= 0) {
              if (root.vpnProfiles.length > 0) root.focusSection = "vpn"
              else if (root.ethernetProfiles.length > 0) root.focusSection = "ethernet"
              else root.focusSection = "dns"
              root.wifiActionFocused = false
            }
            else root.selectByDelta(dy)
          }
        }
        if (dx !== 0) {
          if (root.focusSection === "header") root.selectHeaderByDelta(dx)
          else if (root.focusSection === "band") { if (!root.bandAutoFocused) root.selectBandByDelta(dx) }
          else if (root.focusSection === "dns") root.selectDnsByDelta(dx)
          else if (root.focusSection === "ethernet" || root.focusSection === "vpn") root.selectProfileByDelta(dx)
          else if (root.focusSection === "wifi") root.selectWifiActionByDelta(dx)
        }
      }
      onActivateRequested: {
        if (root.cursorActive) {
          if (root.focusSection === "header") root.activateHeader()
          else if (root.focusSection === "portal") root.openCaptivePortal()
          else if (root.focusSection === "band") root.activateBand()
          else if (root.focusSection === "dns") root.activateDns()
          else if (root.focusSection === "ethernet") root.activateProfile("ethernet")
          else if (root.focusSection === "vpn") root.activateProfile("vpn")
          else root.activateSelected()
        }
      }
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }
      onTextKey: function(t) {
        if (t === "r" || t === "R") root.refresh()
        else if (t === "w" || t === "W") root.toggleNetwork()
      }

      Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Style.space(12)

      // ---------- Hero: network icon · SSID + state · actions ----------
      Item {
        width: parent.width
        implicitHeight: Math.max(heroIcon.implicitHeight, heroLabels.implicitHeight, heroActions.implicitHeight)

        // Status only — the switch owns toggling, mouse and keyboard alike.
        Text {
          id: heroIcon
          textFormat: Text.PlainText
          text: root.icon
          color: root.restricted ? root.bar.urgent : root.bar.foreground
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.display
          opacity: root.networkManagerAvailable ? 1.0 : 0.5
          anchors.left: parent.left
          anchors.verticalCenter: parent.verticalCenter
        }

        // Sharing belongs to the connected-network hero rather than the scan
        // result row. The radio switch remains beside it as the other hero action.
        RowLayout {
          id: heroActions
          spacing: Style.space(8)
          anchors.right: parent.right
          anchors.verticalCenter: parent.verticalCenter

          PanelActionButton {
            id: qrAction
            visible: root.canShareWifi
            iconText: "󰐲"
            tooltipText: Commons.I18n.t("network.showQrCode")
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            fontSize: Style.font.subtitle * 1.5
            hasCursor: root.qrHeaderHasCursor
            Layout.alignment: Qt.AlignVCenter
            onHovered: function(on) { if (on) root.setHeaderCursor(root.qrHeaderIndex) }
            onClicked: root.summonWifiQr()
          }

          PanelActionButton {
            id: speedAction
            visible: root.canRunSpeedTest
            iconText: "󰓅"
            tooltipText: Commons.I18n.t("network.runSpeedTest")
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            fontSize: Style.font.subtitle * 1.5
            hasCursor: root.speedHeaderHasCursor
            Layout.alignment: Qt.AlignVCenter
            onHovered: function(on) { if (on) root.setHeaderCursor(root.speedHeaderIndex) }
            onClicked: root.summonSpeedTest()
          }

          ToggleSwitch {
            id: powerSwitch
            visible: root.canToggleWifi
            checked: Networking.wifiEnabled
            hasCursor: root.toggleHeaderHasCursor
            foreground: root.bar.foreground
            Layout.alignment: Qt.AlignVCenter
            onHovered: function(on) { if (on) root.setHeaderCursor(root.toggleHeaderIndex) }
            onToggled: root.toggleNetwork()

            PanelToolTip {
              visible: powerSwitch.containsMouse
              text: root.toggleHint
              fontFamily: root.bar.fontFamily
            }
          }
        }

        Column {
          id: heroLabels
          anchors.left: heroIcon.right
          anchors.leftMargin: Style.space(14)
          anchors.right: parent.right
          anchors.rightMargin: heroActions.width > 0 ? heroActions.width + Style.space(12) : 0
          anchors.verticalCenter: parent.verticalCenter
          spacing: Style.space(2)

          // Link detail rides inline after the name — "Ethernet (2.5gbit)" —
          // rather than in a pill, which crowded the on/off switch.
          Text {
            id: heroSsid
            textFormat: Text.PlainText
            width: parent.width

            readonly property string title: {
              // The HTTP restriction does not undo association. Show the live
              // SSID even before route/details polling has returned anything.
              if (root.kind === "wifi" && root.connectedWifiNetwork) return root.connectedWifiNetwork.name || "Wi-Fi"
              if (root.info.type === "wifi") return root.info.ssid || "Wi-Fi"
              if (root.info.type === "ethernet") return Commons.I18n.t("network.ethernet")
              return root.info.iface || (root.kind === "disconnected" ? Commons.I18n.t("network.disconnected") : Commons.I18n.t("network.noConnection"))
            }
            readonly property string detail: root.headerDetail()

            text: heroSsid.detail !== "" ? heroSsid.title + " (" + heroSsid.detail + ")" : heroSsid.title
            color: root.bar.foreground
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.title
            font.bold: true
            elide: Text.ElideRight
          }

          Text {
            id: heroMeta
            textFormat: Text.PlainText
            width: parent.width
            text: {
              if (root.hasCaptivePortal) return Commons.I18n.t("network.signInRequiredHeader")
              if (root.restricted) return Commons.I18n.t("network.limitedAccessHeader")
              if (root.info.type === "wifi") {
                if (root.canDisconnect) return root.connectionPhrase.toUpperCase()
                if (root.kind === "disconnected") return Commons.I18n.t("network.notConnected")
                return ""
              }
              if (root.info.type === "ethernet") return root.connectionPhrase.toUpperCase()
              if (root.kind === "disconnected") return Commons.I18n.t("network.notConnected")
              return ""
            }
            visible: text !== ""
            color: root.restricted ? root.bar.urgent : Qt.darker(root.bar.foreground, 1.4)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.caption
            font.bold: true
            font.letterSpacing: 1.2
            elide: Text.ElideRight
          }
        }

      }

      Column {
        visible: root.hasCaptivePortal
        width: parent.width
        spacing: Style.space(6)

        Button {
          id: portalAction
          width: parent.width
          text: Commons.I18n.t("network.openCaptivePortal")
          iconText: "󰏌"
          foreground: root.bar.urgent
          accent: root.bar.urgent
          fontFamily: root.bar.fontFamily
          verticalPadding: Style.space(10)
          bordered: true
          active: true
          hasCursor: root.cursorActive && root.focusSection === "portal"
          onHovered: function(on) {
            if (!on) return
            root.cursorActive = true
            root.focusSection = "portal"
          }
          onClicked: root.openCaptivePortal()
        }

        Text {
          width: parent.width
          text: Commons.I18n.t("network.captivePortalHelp")
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          color: root.bar.foreground
          opacity: 0.7
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.bodySmall
        }
      }

      // Wi-Fi band selection. Only on Wi-Fi, and only when the network answers
      // on more than one band -- a single-band AP has nothing to toggle.
      PanelSeparator {
        visible: root.canSelectBand
        foreground: root.bar.foreground
      }

      Column {
        visible: root.canSelectBand
        width: parent.width
        spacing: Style.space(10)

        // "Automatic" rides on the header line rather than under the pills: it
        // qualifies the whole row, and at header scale it reads as a modifier
        // instead of competing with the band choices for attention.
        Item {
          width: parent.width
          implicitHeight: Math.max(bandHeader.implicitHeight, bandAutoRow.implicitHeight)

          PanelSectionHeader {
            id: bandHeader
            text: root.bandSectionTitle
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
          }

          Row {
            id: bandAutoRow
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.space(6)

            PanelSectionHeader {
              id: bandAutoLabel
              text: Commons.I18n.t("network.automatic")
              foreground: root.bar.foreground
              fontFamily: root.bar.fontFamily
              anchors.verticalCenter: parent.verticalCenter
            }

            // Sized off the label rather than the theme's control height so it
            // reads as part of the header, and centred on the label's *glyphs*:
            // PanelSectionHeader carries topPadding to protect Nerd Font
            // overshoot, which pushes its text below its own box centre, so a
            // plain verticalCenter would sit the switch visibly high.
            ToggleSwitch {
              id: bandAutoSwitch
              trackHeight: Math.round(bandAutoLabel.font.pixelSize * 1.2)
              cursorPad: Style.space(3)
              anchors.verticalCenter: bandAutoLabel.verticalCenter
              anchors.verticalCenterOffset: Math.round(bandAutoLabel.topPadding / 2)
              checked: !root.bandPinned
              busy: root.bandBusy
              hasCursor: root.cursorActive && root.focusSection === "band" && root.bandAutoFocused
              foreground: root.bar.foreground
              onToggled: root.toggleBandAuto()

              onHovered: function(isHovered) {
                if (!isHovered) return
                root.cursorActive = true
                root.focusSection = "band"
                root.bandAutoFocused = true
              }

              PanelToolTip {
                visible: bandAutoSwitch.containsMouse
                text: root.bandPinned
                  ? Commons.I18n.t("network.bandAutoTooltip")
                  : Commons.I18n.t("network.stayOnBand").arg(root.bandLabel(root.bandCurrent))
                fontFamily: root.bar.fontFamily
              }
            }
          }
        }

        // Collapsing container: the pills animate their height so toggling
        // Automatic slides the sections below into place instead of snapping.
        // `visible` only drops at a real zero, which keeps the row rendered for
        // the whole animation and takes it out of the Column's spacing once
        // it's actually gone.
        Item {
          id: bandPillsClip
          width: parent.width
          clip: true
          visible: height > 0
          height: root.bandPillsVisible ? bandRow.implicitHeight : 0
          opacity: root.bandPillsVisible ? 1 : 0

          Behavior on height {
            NumberAnimation { duration: Style.duration(140); easing.type: Easing.OutCubic }
          }
          Behavior on opacity {
            NumberAnimation { duration: Style.duration(140); easing.type: Easing.OutCubic }
          }

          Row {
            id: bandRow
            width: parent.width
            spacing: Style.space(6)

            readonly property int count: Math.max(1, root.bandAvailable.length)
            readonly property real cellWidth: (width - spacing * (count - 1)) / count

            // Wrapper takes modelData/index from the Repeater's delegate
            // context, which doesn't bind into nested `component` declarations,
            // and passes them down explicitly -- same shape as the network
            // list delegate.
            Repeater {
              model: root.bandAvailable

              delegate: Item {
                required property var modelData
                required property int index
                width: bandRow.cellWidth
                height: bandPill.implicitHeight

                BandPill {
                  id: bandPill
                  band: modelData
                  slot: index
                  width: parent.width
                }
              }
            }
          }
        }

      }

      // DNS provider selection.
      PanelSeparator {
        foreground: root.bar.foreground
      }

      Column {
        width: parent.width
        spacing: Style.space(10)

        PanelSectionHeader {
          text: Commons.I18n.t("network.dnsProvider")
          foreground: root.bar.foreground
          fontFamily: root.bar.fontFamily
        }

        Row {
          id: dnsRow
          width: parent.width
          spacing: Style.space(6)

          readonly property int count: 4
          readonly property real cellWidth: (width - spacing * (count - 1)) / count

          DnsProviderPill {
            provider: "DHCP"
            index: 0
            tooltipText: Commons.I18n.t("network.dnsFromDhcp")
            width: dnsRow.cellWidth
            onClicked: root.setDns(provider)
          }

          DnsProviderPill {
            provider: "Cloudflare"
            index: 1
            tooltipText: Commons.I18n.t("network.setDnsTo").arg("Cloudflare")
            width: dnsRow.cellWidth
            onClicked: root.setDns(provider)
          }

          DnsProviderPill {
            provider: "Google"
            index: 2
            tooltipText: Commons.I18n.t("network.setDnsTo").arg("Google")
            width: dnsRow.cellWidth
            onClicked: root.setDns(provider)
          }

          DnsProviderPill {
            provider: "Custom"
            index: 3
            tooltipText: Commons.I18n.t("network.setCustomDns")
            width: dnsRow.cellWidth
            onClicked: root.setDns(provider)
          }
        }
      }


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
      Column {
        width: parent.width
        spacing: Style.space(6)
        PanelSectionHeader {
          text: Commons.I18n.t("network.ethernetProfiles")
          foreground: root.bar.foreground
          fontFamily: root.bar.fontFamily
        }
        Repeater {
          model: root.ethernetProfiles
          delegate: Button {
            required property var modelData
            required property int index
            width: parent.width
            text: modelData.name
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            bordered: true
            active: !!modelData.active
            hasCursor: root.cursorActive && root.focusSection === "ethernet" && root.profileIndex === index
            onHovered: function(on) {
              if (!on) return
              root.cursorActive = true
              root.focusSection = "ethernet"
              root.profileIndex = index
            }
            onClicked: root.toggleProfile(modelData.uuid, !!modelData.active)
          }
        }
        Text {
          visible: root.ethernetProfiles.length === 0
          width: parent.width
          text: Commons.I18n.t("network.noEthernetProfiles")
          textFormat: Text.PlainText
          color: root.bar.foreground
          opacity: 0.7
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.bodySmall
        }
      }
      Column {
        width: parent.width
        spacing: Style.space(6)
        PanelSectionHeader {
          text: Commons.I18n.t("network.vpnProfiles")
          foreground: root.bar.foreground
          fontFamily: root.bar.fontFamily
        }
        Repeater {
          model: root.vpnProfiles
          delegate: Button {
            required property var modelData
            required property int index
            width: parent.width
            text: modelData.name
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            bordered: true
            active: !!modelData.active
            hasCursor: root.cursorActive && root.focusSection === "vpn" && root.profileIndex === index
            onHovered: function(on) {
              if (!on) return
              root.cursorActive = true
              root.focusSection = "vpn"
              root.profileIndex = index
            }
            onClicked: root.toggleProfile(modelData.uuid, !!modelData.active)
          }
        }
        Text {
          visible: root.vpnProfiles.length === 0
          width: parent.width
          text: Commons.I18n.t("network.noVpnProfiles")
          textFormat: Text.PlainText
          color: root.bar.foreground
          opacity: 0.7
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.bodySmall
        }
      }
      Column {
        visible: root.qrOpen && root.qrSize > 0
        width: parent.width
        spacing: Style.space(6)
        PanelSectionHeader {
          text: Commons.I18n.t("network.showQrCode")
          foreground: root.bar.foreground
          fontFamily: root.bar.fontFamily
        }
        Grid {
          columns: root.qrSize
          Repeater {
            model: root.qrModules.length
            delegate: Rectangle {
              required property int index
              width: 4
              height: 4
              color: root.qrModules.charAt(index) === "1" ? root.bar.foreground : "transparent"
            }
          }
        }
      }
      Column {
        visible: root.speedOpen
        width: parent.width
        spacing: Style.space(6)
        PanelSectionHeader {
          text: Commons.I18n.t("network.runSpeedTest")
          foreground: root.bar.foreground
          fontFamily: root.bar.fontFamily
        }
        Text {
          text: Commons.I18n.t("network.speedDown") + " " + (root.speedDown || "--")
          textFormat: Text.PlainText
          color: root.bar.foreground
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.bodySmall
        }
        Text {
          text: Commons.I18n.t("network.speedUp") + " " + (root.speedUp || "--")
          textFormat: Text.PlainText
          color: root.bar.foreground
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.bodySmall
        }
      }
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
      // Wi-Fi networks (only if a Wi-Fi station is available).
      PanelSeparator {
        visible: root.wifiStationAvailable
        foreground: root.bar.foreground
      }

      PanelSectionHeader {
        visible: root.wifiStationAvailable && root.scanning
        text: Commons.I18n.t("network.scanningWifi")
        foreground: root.bar.foreground
        fontFamily: root.bar.fontFamily
      }

      // Scrollable network list — cap the height so a busy neighbourhood
      // doesn't push the popup off-screen. ListView (vs Repeater+Column)
      // gives us positionViewAtIndex for free, which is what keeps the
      // keyboard-selected row scrolled into view as j/k walk past the
      // visible window.
      ListView {
        id: networkList
        visible: root.wifiStationAvailable
        width: parent.width
        height: Math.min(contentHeight, Style.space(240))
        spacing: Style.space(4)
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height

        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        model: root.wifiStationAvailable ? root.wifiNetworks : []
        currentIndex: root.selectedIndex
        onCurrentIndexChanged: if (currentIndex >= 0) positionViewAtIndex(currentIndex, ListView.Contain)

        // Wrapper takes the required props from ListView's delegate context
        // (which doesn't bind into nested `component` declarations like
        // NetworkRow) and passes them down explicitly.
        delegate: Item {
          required property var modelData
          required property int index
          readonly property string sectionTitle: root.wifiSectionTitle(index)
          width: ListView.view.width
          height: delegateColumn.implicitHeight

          Column {
            id: delegateColumn
            width: parent.width
            spacing: Style.space(4)

            PanelSectionHeader {
              visible: sectionTitle !== ""
              text: sectionTitle
              foreground: root.bar.foreground
              fontFamily: root.bar.fontFamily
            }

            NetworkRow {
              id: row
              width: parent.width
              net: modelData
              index: parent.parent.index
            }
          }
        }
      }
      }
    }
  }

  Connections {
    target: root
    function onPasswordSsidChanged() {
      if (root.passwordSsid === "" && root.opened) {
        root.passwordText = ""
        Qt.callLater(function() { if (panel.loadedContent) panel.loadedContent.forceActiveFocus() })
      }
    }
    function onPortalRequestChanged() {
      if (root.portalRequest === 0 || !root.hasCaptivePortal) return
      Quickshell.execDetached(["xdg-open", "http://connectivity-check.ubuntu.com/"])
      root.close()
    }
  }

  component BandPill: Button {
    id: pill
    required property string band
    required property int slot

    text: root.bandLabel(band)
    tooltipText: root.bandTooltip(band)
    fontSize: Style.font.bodySmall
    foreground: root.bar.foreground
    fontFamily: root.bar.fontFamily
    horizontalPadding: Style.spacing.controlPaddingX
    verticalPadding: Style.spacing.controlPaddingY + Style.space(2)
    bordered: true

    active: root.bandCurrent === band
    selected: root.bandEffective === band
    hasCursor: root.cursorActive && root.focusSection === "band"
      && !root.bandAutoFocused && root.bandIndex === slot

    onClicked: root.setBand(band)

    onHovered: function(isHovered) {
      if (!isHovered) return
      root.cursorActive = true
      root.focusSection = "band"
      root.bandIndex = pill.slot
    }
  }

  // One DNS provider pill. The cursor + current visuals come entirely from
  // CursorSurface; this component just binds them to the panel's cursor
  // state and renders the label/tooltip/click target.
  component DnsProviderPill: Button {
    id: pill
    required property string provider
    required property int index

    text: provider === "Custom" ? Commons.I18n.t("network.dnsCustom") : provider
    fontSize: Style.font.bodySmall
    foreground: root.bar.foreground
    fontFamily: root.bar.fontFamily
    horizontalPadding: Style.spacing.controlPaddingX
    verticalPadding: Style.spacing.controlPaddingY + Style.space(2)
    bordered: true

    // Map the panel's domain semantics onto Button's structural props:
    // `current DNS` is the pill's `active` fill; the keyboard cursor lights
    // up `hasCursor`.
    active: root.dnsProvider === provider
    hasCursor: root.cursorActive && root.focusSection === "dns" && root.dnsIndex === index

    onHovered: function(isHovered) {
      if (!isHovered) return
      root.cursorActive = true
      root.focusSection = "dns"
      root.dnsIndex = pill.index
    }
  }

  // A single Wi-Fi network entry. Collapses to a one-line pill normally;
  // expands inline to a passphrase prompt when the user picks a network that
  // requires credentials we do not have. Clicking a connected row
  // disconnects.
  component NetworkRow: CursorSurface {
    id: row
    required property var net
    required property int index

    readonly property bool isConnected: net && net.connected
    readonly property bool isKnown: !!(net && net.known)
    readonly property bool requiresCredentials: net ? root.requiresCredentials(net.security) : false
    readonly property bool isEnterprise: net
      ? (net.security === WifiSecurityType.Wpa2Eap || net.security === WifiSecurityType.WpaEap)
      : false
    readonly property bool canForget: root.canForgetNetwork(net)
    readonly property bool isSelected: root.focusSection === "wifi" && root.selectedIndex === index
    readonly property bool forgetFocused: isSelected && root.wifiActionFocused && canForget
    readonly property bool forgetVisible: canForget && (!requiresCredentials || forgetFocused || rightMouse.containsMouse)

    hasCursor: root.cursorActive && isSelected && !root.wifiActionFocused
    current: isConnected
    foreground: root.bar.foreground
    fill: root.hoverFill
    currentFill: root.selectedFill
    // Gate on the matching *Kind/*Reason being non-empty so a hidden-SSID
    // row (ssid == "") doesn't match the "" defaults of actionSsid etc.
    readonly property bool isBusy: root.actionKind !== "" && root.actionSsid === (net ? net.ssid : "")
    readonly property bool isFailed: root.failureReason !== "" && root.failureSsid === (net ? net.ssid : "")
    readonly property bool isPasswordOpen: root.passwordSsid !== "" && root.passwordSsid === (net ? net.ssid : "")

    function submitCredentials() {
      if (!net || root.busy || root.passwordText.length === 0) return
      if (isEnterprise) {
        root.passwordText = ""
        root.identityText = ""
        root.refuseEnterprise(net.ssid)
        return
      }
      root.connectWithPassphrase(net.ssid, root.passwordText)
    }

    Connections {
      target: row.net ? root.networkForSsid(row.net.ssid) : null
      function onConnectionFailed(reason) {
        // Background auto-connect retries fire this too; only reprompt for
        // the connect started from this panel. Checked before
        // failNetworkAction, which clears the action state.
        var ours = root.actionKind === "connect" && root.actionSsid === (row.net.ssid || "")
        root.failNetworkAction(root.networkForSsid(row.net.ssid), reason)
        if (ours && root.shouldRepromptPassphrase(reason, row.requiresCredentials)) root.openPasswordPrompt(row.net.ssid)
      }
      function onConnectedChanged() {
        if (row.net) root.checkActionCompletion(root.networkForSsid(row.net.ssid))
      }
      function onKnownChanged() {
        if (row.net) root.checkActionCompletion(root.networkForSsid(row.net.ssid))
      }
      function onStateChangingChanged() {
        if (row.net) root.checkActionCompletion(root.networkForSsid(row.net.ssid))
      }
    }

    readonly property string statusText: {
      if (!net) return ""
      if (isPasswordOpen) return ""
      if (isBusy && root.actionKind === "connect") return Commons.I18n.t("network.connecting")
      if (isBusy && root.actionKind === "disconnect") return Commons.I18n.t("network.disconnecting")
      if (isBusy && root.actionKind === "forget") return Commons.I18n.t("network.forgetting")
      if (isFailed) return root.failureReason || Commons.I18n.t("network.failed")
      if (isConnected && root.kind === "wifi" && root.hasCaptivePortal) return Commons.I18n.t("network.signInRequired")
      if (isConnected) return Commons.I18n.t("network.connected")
      return ""
    }

    readonly property color statusColor: {
      if (isFailed) return root.bar.urgent
      if (isBusy) return root.bar.foreground
      if (isConnected && root.kind === "wifi" && root.hasCaptivePortal) return root.bar.urgent
      if (isConnected) return root.bar.foreground
      return Qt.darker(root.bar.foreground, 1.5)
    }

    implicitHeight: rowBody.implicitHeight + (isPasswordOpen ? passwordPanel.implicitHeight + Style.spacing.md : 0)

    MouseArea {
      id: rowMouse
      anchors.left: parent.left
      anchors.right: parent.right
      anchors.top: parent.top
      height: rowBody.implicitHeight
      hoverEnabled: true
      acceptedButtons: Qt.LeftButton
      cursorShape: Qt.PointingHandCursor
      enabled: !root.busy

      // Move the cursor here when the mouse enters; mouse leaving doesn't
      // clear it (so the cursor stays where the mouse last was and
      // subsequent j/k pick up from this row).
      onContainsMouseChanged: if (containsMouse) { root.cursorActive = true; root.focusSection = "wifi"; root.selectedIndex = row.index; root.wifiActionFocused = false }

      onClicked: {
        if (!row.net) return
        // Resync cursor in case keyboard nav moved it away while the mouse
        // stayed parked on this row — the click target is unambiguously here.
        root.cursorActive = true
        root.focusSection = "wifi"
        root.selectedIndex = row.index
        root.wifiActionFocused = false
        if (row.isConnected) {
          root.disconnectRow(row.net.ssid)
          return
        }
        if (row.isEnterprise && !row.isKnown) {
          root.refuseEnterprise(row.net.ssid)
          return
        }
        if (row.requiresCredentials && !row.isKnown) {
          root.openPasswordPrompt(row.net.ssid)
          return
        }
        root.connectDirectly(row.net.ssid)
      }
    }

    Item {
      id: rowBody
      anchors.left: parent.left
      anchors.right: parent.right
      anchors.top: parent.top
      anchors.leftMargin: Style.space(10)
      anchors.rightMargin: Style.space(10)
      implicitHeight: Math.max(networkIcon.implicitHeight, networkInfo.implicitHeight, rightAction.implicitHeight) + Style.spacing.rowPaddingX

      Text {
        id: networkIcon
        textFormat: Text.PlainText
        text: row.net ? Model.connectionIcon("wifi", row.net.signal,
          row.isConnected && root.kind === "wifi" ? root.connectivity : "") : ""
        color: row.statusColor
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.title
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
      }

      // The right edge shows a lock for networks that require credentials and
      // reveals Forget on hover. Known passwordless networks show Forget
      // directly rather than reserving an invisible or misleading target.
      Item {
        id: rightAction
        visible: row.requiresCredentials || row.canForget
        width: Style.space(22)
        implicitHeight: lockIndicator.implicitHeight
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter

        Text {
          id: lockIndicator
          textFormat: Text.PlainText
          visible: row.requiresCredentials || row.forgetVisible
          width: parent.width
          anchors.verticalCenter: parent.verticalCenter
          horizontalAlignment: Text.AlignHCenter
          text: row.forgetVisible ? "󰅙" : "󰌾"
          color: row.forgetVisible ? root.bar.urgent : Qt.darker(root.bar.foreground, 1.4)
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.subtitle
        }

        BorderSurface {
          anchors.fill: parent
          visible: row.forgetFocused
          color: Style.hoverFillFor(root.bar.urgent, root.bar.urgent)
          borderSpec: Border.controlSpec("hover-cursor", root.bar.urgent, root.bar.urgent)
          radius: Style.cornerRadius
          z: -1
        }

        MouseArea {
          id: rightMouse
          anchors.fill: parent
          hoverEnabled: true
          acceptedButtons: Qt.LeftButton
          enabled: row.canForget && !root.busy
          cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
          onContainsMouseChanged: if (containsMouse) { root.cursorActive = true; root.focusSection = "wifi"; root.selectedIndex = row.index; root.wifiActionFocused = true }
          onClicked: if (row.net) root.forget(row.net)
        }

        PanelToolTip {
          visible: rightMouse.containsMouse || row.forgetFocused
          text: Commons.I18n.t("network.forgetNetwork")
          fontFamily: root.bar.fontFamily
        }
      }

      Column {
        id: networkInfo
        spacing: Style.space(1)
        anchors.left: networkIcon.right
        anchors.leftMargin: Style.space(10)
        anchors.right: rightAction.visible ? rightAction.left : parent.right
        anchors.rightMargin: rightAction.visible ? Style.space(8) : 0
        anchors.verticalCenter: parent.verticalCenter

        Text {
          textFormat: Text.PlainText
          text: row.net ? (row.net.ssid || Commons.I18n.t("network.hidden")) : ""
          color: root.bar.foreground
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.body
          elide: Text.ElideRight
          width: parent.width
        }
        Text {
          textFormat: Text.PlainText
          // Signal strength is conveyed by the wifi-bars icon and the
          // right-edge glyph/buttons carry protection or forget affordances,
          // so the second line only carries action status (Connecting…,
          // Connected, Failed, etc.). Collapses to zero height when empty
          // so rows without status keep a tight one-line look.
          text: row.statusText
          visible: row.statusText !== ""
          color: row.statusColor
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.caption
          elide: Text.ElideRight
          width: parent.width
        }
      }
    }

    Timer {
      id: failureTimer
      interval: 2000
      running: row.isFailed && row.isPasswordOpen
      onTriggered: {
        root.failureSsid = ""
        root.failureReason = ""
        pwField.forceActiveFocus()
      }
    }

    // Inline passphrase prompt — shown when we hit a protected network we
    // don't have saved credentials for, or when a connect fails because the
    // saved passphrase is wrong. Submitting (Enter or the check button) fires
    // connect; Esc cancels back to the row.
    Item {
      id: passwordPanel
      visible: row.isPasswordOpen
      anchors.left: parent.left
      anchors.right: parent.right
      anchors.top: rowMouse.bottom
      anchors.leftMargin: Style.space(10)
      anchors.rightMargin: Style.space(10)
      anchors.topMargin: Style.space(4)
      implicitHeight: (idField.visible ? idField.implicitHeight + Style.space(4) : 0) + pwField.implicitHeight + Style.spacing.rowGap
      height: implicitHeight

      TextField {
        id: idField
        visible: row.isEnterprise && !row.isBusy && !row.isFailed
        anchors.left: parent.left
        anchors.right: connectPwBtn.left
        anchors.top: parent.top
        anchors.rightMargin: Style.space(6)
        placeholderText: Commons.I18n.t("network.identity")
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        foreground: root.bar.foreground
        horizontalPadding: Style.spacing.controlGap
        verticalPadding: Style.spacing.controlPaddingY
        enabled: !row.isBusy
        text: row.isPasswordOpen ? root.identityText : ""

        onAccepted: pwField.forceActiveFocus()
        onTextChanged: if (row.isPasswordOpen && text !== root.identityText) root.identityText = text
        Keys.onEscapePressed: root.cancelPasswordPrompt()

        onVisibleChanged: if (visible) Qt.callLater(forceActiveFocus)
        Component.onCompleted: if (visible) Qt.callLater(forceActiveFocus)
      }

      TextField {
        id: pwField
        visible: !row.isBusy && !row.isFailed
        anchors.left: parent.left
        anchors.right: connectPwBtn.left
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Style.spacing.rowGap / 2
        anchors.rightMargin: Style.space(6)
        password: true
        placeholderText: Commons.I18n.t("network.passphrase")
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        foreground: root.bar.foreground
        horizontalPadding: Style.spacing.controlGap
        verticalPadding: Style.spacing.controlPaddingY
        enabled: !row.isBusy
        text: row.isPasswordOpen ? root.passwordText : ""

        onAccepted: row.submitCredentials()
        onTextChanged: if (row.isPasswordOpen && text !== root.passwordText) root.passwordText = text
        Keys.onEscapePressed: root.cancelPasswordPrompt()

        onVisibleChanged: if (visible && !row.isEnterprise) Qt.callLater(forceActiveFocus)
        Component.onCompleted: if (visible && !row.isEnterprise) Qt.callLater(forceActiveFocus)
      }

      BorderSurface {
        id: statusMsgWrapper
        visible: row.isBusy || row.isFailed
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        height: Style.spacing.controlHeight
        color: Style.normalFillFor(root.bar.foreground)
        borderSpec: Border.controlSpec("normal", root.bar.foreground, Commons.Color.accent)
        radius: Style.cornerRadius

        Text {
          textFormat: Text.PlainText
          anchors.fill: parent
          horizontalAlignment: Text.AlignHCenter
          verticalAlignment: Text.AlignVCenter
          text: row.isFailed ? Commons.I18n.t("network.wrongPassword") : Commons.I18n.t("network.connecting")
          color: row.isFailed ? root.bar.urgent : root.bar.foreground
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.bodySmall
        }
      }

      // 22×22 right-anchored to line up with lockIndicator above. Esc closes
      // the prompt (handled by pwField.Keys.onEscapePressed)
      // so there's no separate cancel button.
      PanelActionButton {
        id: connectPwBtn
        visible: !row.isBusy && !row.isFailed
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        enabled: row.net && pwField.text.length > 0 && (!row.isEnterprise || idField.text.length > 0)
        iconText: "󰄬"
        tooltipText: Commons.I18n.t("network.connect")
        foreground: root.bar.foreground
        fontFamily: root.bar.fontFamily
        onClicked: row.submitCredentials()
      }
    }
  }


}
