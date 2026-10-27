import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Networking
import qs.Commons
import "Port/NetworkModel.js" as Model

// Native NetworkManager actions for the extracted Omarchy network surface.
// DNS, band, QR, speed test, portal, Ethernet and VPN run through the Ubuntu
// helper named by OMABUNTU_NETWORK_HELPER. No Omarchy helper and no new
// 802.1X profile. Passphrases are handed to connectWithPsk and cleared.
Item {
  id: root
  required property QtObject bar
  property bool opened: false
  property bool cursorActive: false
  property string focusSection: "dns"
  property int selectedIndex: -1
  property int headerIndex: 0
  property bool wifiActionFocused: false
  property bool scanning: false
  property bool wifiStationAvailable: false
  property var wifiNetworks: []
  property var scannerDevice: null
  property string actionSsid: ""
  property string actionKind: ""
  property string failureSsid: ""
  property string failureReason: ""
  property string passwordSsid: ""
  property string passwordText: ""
  property string identityText: ""
  property string dnsProvider: "DHCP"
  property string pendingDnsProvider: ""
  property bool customDnsOpen: false
  property string bandCurrent: ""
  property string bandSelected: "auto"
  property var bandAvailable: []
  property string pendingBand: ""
  property int bandIndex: 0
  property bool bandAutoFocused: true
  property int dnsIndex: 0
  property var ethernetProfiles: []
  property var vpnProfiles: []
  property int profileIndex: 0
  property int portalRequest: 0
  property bool qrOpen: false
  property int qrSize: 0
  property string qrModules: ""
  property bool speedOpen: false
  property bool speedRunning: false
  property string speedDown: ""
  property string speedUp: ""
  property string serviceNote: ""
  property string queuedKind: ""
  property var queuedArgs: []

  readonly property bool networkManagerAvailable: Networking.backend === NetworkBackendType.NetworkManager
  readonly property bool checksEnabled: Networking.canCheckConnectivity && Networking.connectivityCheckEnabled
  readonly property var networkDevices: Networking.devices ? Networking.devices.values : []
  readonly property var wifiDevice: findDevice(DeviceType.Wifi)
  readonly property var wiredDevice: findDevice(DeviceType.Wired)
  readonly property var wifiNetworkObjects: wifiDevice && wifiDevice.networks ? wifiDevice.networks.values : []
  readonly property var connectedWifiNetwork: findConnected()
  readonly property string kind: {
    if (wiredDevice && wiredDevice.connected) return "ethernet"
    if (connectedWifiNetwork) return "wifi"
    if (wifiDevice && wifiDevice.connected) return "wifi"
    return "disconnected"
  }
  property int activeApSignal: -1
  property int signalGeneration: 0
  readonly property bool needsActiveApSignal: kind === "wifi"
    && !(connectedWifiNetwork && connectedWifiNetwork.signalStrength > 0)
  readonly property int signalStrength: kind === "wifi"
    ? Model.connectedSignalStrength(connectedWifiNetwork ? connectedWifiNetwork.signalStrength : 0, activeApSignal) : -1
  readonly property string connectivity: Model.connectivityState(
    kind, Networking.connectivity, NetworkConnectivity, checksEnabled)
  readonly property bool hasCaptivePortal: connectivity === "portal"
  readonly property bool restricted: hasCaptivePortal || connectivity === "limited"
  readonly property string icon: networkManagerAvailable
    ? Model.connectionIcon(kind, signalStrength, connectivity) : "?"
  readonly property var info: {
    var device = wiredDevice && wiredDevice.connected ? wiredDevice
      : (wifiDevice && wifiDevice.connected ? wifiDevice : null)
    return {
      type: kind === "ethernet" ? "ethernet" : (kind === "wifi" ? "wifi" : ""),
      ssid: connectedWifiNetwork ? (connectedWifiNetwork.name || "") : "",
      iface: device ? (device.name || "") : "",
      ip: device && device.address ? String(device.address) : ""
    }
  }
  readonly property bool canDisconnect: !!connectedWifiNetwork
  readonly property bool canShareWifi: kind === "wifi" && !!connectedWifiNetwork
    && !isEnterprise(connectedWifiNetwork.security)
  readonly property bool canRunSpeedTest: info.iface !== ""
  readonly property bool canToggleWifi: networkManagerAvailable && Networking.wifiHardwareEnabled !== false
  readonly property int qrHeaderIndex: canShareWifi ? 0 : -1
  readonly property int speedHeaderIndex: canRunSpeedTest ? (canShareWifi ? 1 : 0) : -1
  readonly property int toggleHeaderIndex: canToggleWifi ? (canShareWifi ? 1 : 0) + (canRunSpeedTest ? 1 : 0) : -1
  readonly property int headerActionCount: (canShareWifi ? 1 : 0) + (canRunSpeedTest ? 1 : 0) + (canToggleWifi ? 1 : 0)
  readonly property bool qrHeaderHasCursor: qrHeaderIndex >= 0 && cursorActive && focusSection === "header" && headerIndex === qrHeaderIndex
  readonly property bool speedHeaderHasCursor: speedHeaderIndex >= 0 && cursorActive && focusSection === "header" && headerIndex === speedHeaderIndex
  readonly property bool toggleHeaderHasCursor: toggleHeaderIndex >= 0 && cursorActive && focusSection === "header" && headerIndex === toggleHeaderIndex
  readonly property string toggleHint: I18n.t(Networking.wifiEnabled ? "network.turnWifiOff" : "network.turnWifiOn")
  readonly property string connectionPhrase: I18n.t("network.connectedPhrase")
  readonly property bool busy: actionKind !== ""
  readonly property var dnsProviders: ["DHCP", "Cloudflare", "Google", "Custom"]
  readonly property string bandEffective: pendingBand !== "" ? pendingBand : bandSelected
  readonly property bool bandBusy: pendingBand !== ""
  readonly property bool bandPinned: bandEffective !== "auto"
  readonly property bool canSelectBand: (kind === "wifi" || bandBusy) && (bandAvailable.length > 1 || bandPinned)
  readonly property bool bandPillsVisible: canSelectBand && bandPinned
  readonly property string bandSectionTitle: Model.bandSectionTitle(bandEffective, bandCurrent, I18n.t, I18n.formatNumber)
  readonly property color hoverFill: bar ? Style.hoverFillFor(bar.foreground, Color.accent) : "transparent"
  readonly property color selectedFill: bar ? Style.selectedFillFor(bar.foreground, Color.accent) : "transparent"
  implicitWidth: 26
  implicitHeight: 26

  onWifiNetworkObjectsChanged: syncWifiNetworks()
  onWifiDeviceChanged: {
    resetActiveApSignal()
    setScannerEnabled(true)
    syncWifiNetworks()
  }
  onKindChanged: resetActiveApSignal()
  onConnectedWifiNetworkChanged: resetActiveApSignal()
  onWifiNetworksChanged: {
    if (wifiNetworks.length === 0) {
      selectedIndex = -1
      wifiActionFocused = false
      if (focusSection === "wifi") focusSection = "dns"
    } else if (passwordSsid !== "") {
      var passwordIndex = wifiIndexForSsid(passwordSsid)
      if (passwordIndex >= 0) { selectedIndex = passwordIndex; focusSection = "wifi" }
    } else if (selectedIndex >= wifiNetworks.length) selectedIndex = wifiNetworks.length - 1
    else if (selectedIndex < 0 && opened) selectedIndex = 0
    if (selectedIndex < 0 || selectedIndex >= wifiNetworks.length || !canForgetNetwork(wifiNetworks[selectedIndex]))
      wifiActionFocused = false
  }
  onDnsProviderChanged: syncDnsIndex()
  onBandSelectedChanged: syncBandIndex()
  onHasCaptivePortalChanged: {
    if (hasCaptivePortal && opened && passwordSsid === "") {
      focusSection = "portal"
      cursorActive = true
    } else if (!hasCaptivePortal && focusSection === "portal") {
      focusSection = headerActionCount > 0 ? "header" : "dns"
      headerIndex = 0
    }
  }
  onHeaderActionCountChanged: clampHeaderIndex()
  onBandAvailableChanged: syncBandIndex()
  onCanSelectBandChanged: if (!canSelectBand && focusSection === "band") focusSection = "dns"
  onBandPillsVisibleChanged: if (!bandPillsVisible) bandAutoFocused = true
  onOpenedChanged: {
    if (opened) {
      refresh(true)
      selectedIndex = wifiNetworks.length > 0 ? 0 : -1
      wifiActionFocused = false
      syncDnsIndex()
      syncBandIndex()
      focusSection = hasCaptivePortal ? "portal" : (wifiNetworks.length > 0 ? "wifi" : "dns")
      cursorActive = hasCaptivePortal
    } else {
      scanRestart.stop()
      scanDone.stop()
      scanning = false
      cancelPasswordPrompt()
      setScannerEnabled(false)
      qrOpen = false
      qrModules = ""
      qrSize = 0
      speedOpen = false
      customDnsOpen = false
      serviceNote = ""
    }
  }
  Component.onCompleted: syncWifiNetworks()
  Component.onDestruction: if (scannerDevice) scannerDevice.scannerEnabled = false

  function open() { opened = true }
  function close() { opened = false }
  function switchPanel(direction) {}
  function headerDetail() { return info.ip || "" }
  function findDevice(type) {
    var devices = networkDevices || []
    var fallback = null
    for (var i = 0; i < devices.length; i++) {
      var device = devices[i]
      if (!device || device.type !== type) continue
      if (device.connected) return device
      if (!fallback) fallback = device
    }
    return fallback
  }
  function findConnected() {
    var networks = wifiNetworkObjects || []
    for (var i = 0; i < networks.length; i++)
      if (networks[i] && networks[i].connected) return networks[i]
    return null
  }
  function networkForSsid(ssid) {
    var networks = wifiNetworkObjects || []
    for (var i = 0; i < networks.length; i++)
      if (networks[i] && networks[i].name === ssid) return networks[i]
    return null
  }
  function resetActiveApSignal() {
    activeApSignal = -1
    signalGeneration += 1
  }
  function applyActiveApSignal(payload, generation) {
    if (generation !== signalGeneration || !wifiDevice || payload.iface !== wifiDevice.name) return
    var strength = payload.signal
    activeApSignal = typeof strength === "number" && isFinite(strength)
      && strength >= 0 && strength <= 100 ? Math.round(strength) : -1
  }
  function wifiIndexForSsid(ssid) {
    for (var i = 0; i < wifiNetworks.length; i++)
      if (wifiNetworks[i] && wifiNetworks[i].ssid === ssid) return i
    return -1
  }
  function syncDnsIndex() {
    var index = dnsProviders.indexOf(dnsProvider)
    dnsIndex = index >= 0 ? index : 0
  }
  function syncBandIndex() {
    var index = bandAvailable.indexOf(bandSelected)
    bandIndex = index >= 0 ? index : 0
  }
  function syncWifiNetworks() {
    var nets = []
    var networks = wifiNetworkObjects || []
    for (var i = 0; i < networks.length; i++) {
      var network = networks[i]
      if (!network) continue
      checkActionCompletion(network)
      var row = Model.wifiRow(network)
      if (row) nets.push(row)
    }
    wifiNetworks = Model.sortWifiRows(nets)
    wifiStationAvailable = !!wifiDevice
  }
  function setScannerEnabled(enabled) {
    var next = opened ? wifiDevice : null
    if (scannerDevice && scannerDevice !== next) scannerDevice.scannerEnabled = false
    scannerDevice = next
    if (scannerDevice) scannerDevice.scannerEnabled = enabled
  }
  function refresh(scanWifi) {
    if (checksEnabled && kind !== "disconnected") Networking.checkConnectivity()
    if (opened && wifiDevice) {
      if (scanWifi) {
        setScannerEnabled(false)
        scanning = true
        scanRestart.start()
      } else setScannerEnabled(true)
    }
    syncWifiNetworks()
    if (scanWifi && opened && wifiDevice) scanning = true
    if (opened) requestNm("status", [])
  }
  function networkHelper() {
    var value = Quickshell.env("OMABUNTU_NETWORK_HELPER")
    if (value === undefined || value === null) return ""
    var text = String(value)
    if (text.indexOf("/network_nm.py") !== text.length - 14 || text.indexOf(" ") !== -1) return ""
    return text
  }
  function requestNm(kind, args) {
    var helper = networkHelper()
    if (helper === "") return false
    if (nmProc.running) {
      if (kind !== "status" && kind !== "signal") { queuedKind = kind; queuedArgs = args || [] }
      return false
    }
    var command = ["python3", helper, kind]
    var extra = args || []
    for (var i = 0; i < extra.length; i++) command.push(String(extra[i]))
    nmProc.requestKind = kind
    nmProc.signalGeneration = signalGeneration
    nmProc.exec(command)
    return true
  }
  function finishNm(kind, code, text) {
    var payload = null
    try { payload = JSON.parse(String(text || "").trim()) } catch (error) { payload = null }
    var accepted = payload && payload.ok === true
    if (kind === "signal" && accepted) {
      applyActiveApSignal(payload, nmProc.signalGeneration)
    } else if (kind === "status" && accepted) {
      if (pendingDnsProvider === "") dnsProvider = String(payload.dns || "DHCP")
      if (pendingBand === "") {
        bandCurrent = String(payload.band || "")
        bandSelected = String(payload.selected || "auto")
        bandAvailable = payload.available || []
      }
      ethernetProfiles = payload.ethernet || []
      vpnProfiles = payload.vpn || []
    } else if (kind === "dns-set") {
      if (accepted && pendingDnsProvider !== "") dnsProvider = pendingDnsProvider
      else if (!accepted) serviceNote = I18n.t("network.actionFailed")
      pendingDnsProvider = ""
    } else if (kind === "band-set") {
      if (accepted) bandSelected = pendingBand
      else serviceNote = I18n.t("network.actionFailed")
      pendingBand = ""
    } else if (kind === "qr") {
      var modules = accepted ? String(payload.modules || "") : ""
      var size = accepted ? Number(payload.size || 0) : 0
      if (accepted && size >= 21 && size <= 80 && modules.length === size * size && /^[01]+$/.test(modules)) {
        qrSize = size
        qrModules = modules
      } else {
        qrOpen = false
        qrModules = ""
        qrSize = 0
        serviceNote = I18n.t("network.qrFailed")
      }
    } else if (kind === "speed") {
      speedRunning = false
      if (accepted && speedOpen) {
        speedDown = String(payload.down)
        speedUp = String(payload.up)
      } else if (speedOpen) serviceNote = I18n.t("network.speedFailed")
    } else if ((kind === "connect" || kind === "disconnect") && !accepted) {
      serviceNote = I18n.t("network.actionFailed")
    }
    if (kind !== "status" && kind !== "signal" && kind !== "qr" && kind !== "speed" && opened) requestNm("status", [])
    if (queuedKind !== "" && !nmProc.running) {
      var next = queuedKind
      var nextArgs = queuedArgs
      queuedKind = ""
      queuedArgs = []
      requestNm(next, nextArgs)
    }
  }
  function requiresCredentials(security) {
    return Model.requiresCredentials(security, WifiSecurityType.Open, WifiSecurityType.Owe)
  }
  function isEnterprise(security) {
    return security === WifiSecurityType.Wpa2Eap || security === WifiSecurityType.WpaEap
  }
  function canForgetNetwork(network) { return Model.canForgetNetwork(network) }
  function wifiSectionTitle(index) { return Model.wifiSectionTitle(wifiNetworks, index, I18n.t) }
  function bandLabel(band) { return Model.bandLabel(band, I18n.t, I18n.formatNumber) }
  function bandTooltip(band) { return Model.bandTooltip(band, I18n.t, I18n.formatNumber) }
  function selectByDelta(delta) {
    if (wifiNetworks.length === 0) { selectedIndex = -1; return }
    if (selectedIndex < 0) selectedIndex = delta > 0 ? 0 : wifiNetworks.length - 1
    else selectedIndex = Math.max(0, Math.min(wifiNetworks.length - 1, selectedIndex + delta))
    wifiActionFocused = false
  }
  function selectWifiActionByDelta(delta) {
    if (selectedIndex < 0 || selectedIndex >= wifiNetworks.length) return
    if (!canForgetNetwork(wifiNetworks[selectedIndex])) { wifiActionFocused = false; return }
    wifiActionFocused = delta > 0
  }
  function clampHeaderIndex() {
    var max = Math.max(0, headerActionCount - 1)
    if (headerIndex > max) headerIndex = max
    if (headerIndex < 0) headerIndex = 0
  }
  function selectHeaderByDelta(delta) {
    headerIndex = Math.max(0, Math.min(headerActionCount - 1, headerIndex + delta))
  }
  function setHeaderCursor(index) {
    cursorActive = true
    focusSection = "header"
    headerIndex = index
  }
  function activateHeader() {
    if (headerIndex === qrHeaderIndex) summonWifiQr()
    else if (headerIndex === speedHeaderIndex) summonSpeedTest()
    else if (headerIndex === toggleHeaderIndex) toggleNetwork()
  }
  function selectDnsByDelta(delta) {
    dnsIndex = Math.max(0, Math.min(dnsProviders.length - 1, dnsIndex + delta))
  }
  function activateDns() {
    if (dnsIndex < 0 || dnsIndex >= dnsProviders.length) return
    setDns(dnsProviders[dnsIndex])
  }
  function selectBandByDelta(delta) {
    bandIndex = Math.max(0, Math.min(bandAvailable.length - 1, bandIndex + delta))
  }
  function activateBand() {
    if (bandAutoFocused) { toggleBandAuto(); return }
    if (bandIndex < 0 || bandIndex >= bandAvailable.length) return
    setBand(bandAvailable[bandIndex])
  }
  function toggleBandAuto() {
    if (bandSelected !== "auto") { setBand("auto"); return }
    if (bandCurrent === "") return
    setBand(bandCurrent)
  }
  function selectProfileByDelta(delta) {
    var rows = focusSection === "vpn" ? vpnProfiles : ethernetProfiles
    if (!rows || rows.length === 0) return
    profileIndex = Math.max(0, Math.min(rows.length - 1, profileIndex + delta))
  }
  function activateProfile(kind) {
    var rows = kind === "vpn" ? vpnProfiles : ethernetProfiles
    if (profileIndex < 0 || profileIndex >= rows.length) return
    var row = rows[profileIndex]
    toggleProfile(row.uuid, !!row.active)
  }
  function toggleProfile(uuid, active) {
    var text = String(uuid || "")
    if (!/^[0-9a-fA-F-]{36}$/.test(text)) return
    serviceNote = ""
    requestNm(active ? "disconnect" : "connect", [text])
  }
  function toggleNetwork() {
    if (!canToggleWifi) return
    Networking.wifiEnabled = !Networking.wifiEnabled
    if (opened) Qt.callLater(function() { root.refresh(true) })
  }
  function openCaptivePortal() {
    if (!hasCaptivePortal) return
    portalRequest += 1
  }
  function summonWifiQr() {
    if (!canShareWifi) return
    qrOpen = true
    speedOpen = false
    serviceNote = ""
    if (networkHelper() === "") { serviceNote = I18n.t("network.helperUnavailable"); return }
    requestNm("qr", [])
  }
  function summonSpeedTest() {
    if (!canRunSpeedTest || speedRunning) return
    speedOpen = true
    qrOpen = false
    qrModules = ""
    speedDown = ""
    speedUp = ""
    serviceNote = ""
    if (networkHelper() === "") { serviceNote = I18n.t("network.helperUnavailable"); return }
    speedRunning = true
    requestNm("speed", [])
  }
  function setBand(band) {
    if (band !== "auto" && band !== "2.4" && band !== "5" && band !== "6") return
    pendingBand = band
    serviceNote = ""
    if (networkHelper() === "") { pendingBand = ""; serviceNote = I18n.t("network.helperUnavailable"); return }
    requestNm("band-set", [band])
  }
  function setDns(provider) {
    if (provider === "Custom") { customDnsOpen = true; focusSection = "dns"; return }
    if (provider !== "DHCP" && provider !== "Cloudflare" && provider !== "Google") return
    customDnsOpen = false
    pendingDnsProvider = provider
    serviceNote = ""
    if (networkHelper() === "") {
      pendingDnsProvider = ""
      serviceNote = I18n.t("network.helperUnavailable")
      return
    }
    requestNm("dns-set", [provider])
    close()
  }
  function applyCustomDns(text) {
    var value = String(text || "").replace(/\s+/g, "").trim()
    if (!/^[0-9a-fA-F:.,]+$/.test(value)) { serviceNote = I18n.t("network.actionFailed"); return }
    pendingDnsProvider = "Custom"
    serviceNote = ""
    if (networkHelper() === "" || !requestNm("dns-set", ["Custom", value])) {
      if (networkHelper() === "") pendingDnsProvider = ""
      return
    }
    customDnsOpen = false
  }
  function openPasswordPrompt(ssid) {
    if (passwordSsid !== ssid) {
      passwordText = ""
      identityText = ""
    }
    passwordSsid = ssid
  }
  function cancelPasswordPrompt() {
    passwordSsid = ""
    passwordText = ""
    identityText = ""
  }
  function refuseEnterprise(ssid) {
    cancelPasswordPrompt()
    failureSsid = ssid || ""
    failureReason = I18n.t("network.enterpriseUnavailable")
  }
  function clearAction() {
    actionTimeout.stop()
    if (actionKind === "connect") passwordSsid = ""
    failureSsid = ""
    failureReason = ""
    actionSsid = ""
    actionKind = ""
    passwordText = ""
    identityText = ""
    // Rebuilding the list can destroy the delegate emitting this signal.
    Qt.callLater(root.syncWifiNetworks)
  }
  function failNetworkAction(network, reason) {
    if (!network || actionKind === "" || actionSsid !== (network.name || "")) return
    actionTimeout.stop()
    failureSsid = actionSsid
    failureReason = Model.networkFailureReason(
      reason, requiresCredentials(network.security), ConnectionFailReason, I18n.t)
    actionSsid = ""
    actionKind = ""
    passwordText = ""
    identityText = ""
    Qt.callLater(root.syncWifiNetworks)
  }
  function shouldRepromptPassphrase(reason, needsCredentials) {
    return Model.shouldRepromptPassphrase(reason, needsCredentials, ConnectionFailReason)
  }
  function checkActionCompletion(network) {
    if (!network || actionKind === "" || actionSsid !== (network.name || "")) return
    if (actionKind === "connect" && network.connected) clearAction()
    else if (actionKind === "disconnect" && !network.connected && !network.stateChanging) clearAction()
    else if (actionKind === "forget" && !network.known && !network.stateChanging) clearAction()
  }
  function runAction(kind, network, callback) {
    if (actionKind !== "" || !network) return
    actionSsid = network.name || ""
    actionKind = kind
    failureSsid = ""
    failureReason = ""
    callback(network)
    actionTimeout.restart()
  }
  function connectDirectly(ssid) {
    var network = networkForSsid(ssid)
    if (network && isEnterprise(network.security) && !network.known) { refuseEnterprise(ssid); return }
    runAction("connect", network, function(item) { item.connect() })
  }
  function connectWithPassphrase(ssid, passphrase) {
    var network = networkForSsid(ssid)
    if (!network || isEnterprise(network.security)) { refuseEnterprise(ssid); return }
    runAction("connect", network, function(item) {
      item.connectWithPsk(passphrase)
      root.passwordText = ""
      root.identityText = ""
    })
  }
  function disconnectRow(ssid) {
    var network = networkForSsid(ssid)
    if (network && network.connected)
      runAction("disconnect", network, function(item) { item.disconnect() })
  }
  function forget(net) {
    var network = net ? networkForSsid(net.ssid) : null
    if (network && network.known && !network.connected)
      runAction("forget", network, function(item) { item.forget() })
  }
  function activateSelected() {
    if (busy || selectedIndex < 0 || selectedIndex >= wifiNetworks.length) return
    var net = wifiNetworks[selectedIndex]
    if (!net) return
    if (wifiActionFocused && canForgetNetwork(net)) { forget(net); return }
    if (net.connected) { disconnectRow(net.ssid); return }
    if (isEnterprise(net.security) && !net.known) { refuseEnterprise(net.ssid); return }
    if (requiresCredentials(net.security) && !net.known) { openPasswordPrompt(net.ssid); return }
    connectDirectly(net.ssid)
  }

  Process {
    id: nmProc
    property string requestKind: ""
    property int signalGeneration: -1
    stdout: StdioCollector { id: nmOut }
    onExited: function(code) { root.finishNm(requestKind, code, nmOut.text) }
  }
  Timer {
    id: scanRestart
    interval: 100
    repeat: false
    onTriggered: {
      if (root.opened && root.wifiDevice) {
        root.setScannerEnabled(true)
        scanDone.restart()
      } else root.scanning = false
    }
  }
  Timer {
    id: scanDone
    interval: 1500
    repeat: false
    onTriggered: {
      root.syncWifiNetworks()
      root.scanning = false
    }
  }
  Timer {
    id: actionTimeout
    interval: 30000
    repeat: false
    onTriggered: {
      if (!root.actionKind) return
      root.failureSsid = root.actionSsid
      root.failureReason = I18n.t(root.actionKind === "connect" ? "network.timedOutConnecting"
        : (root.actionKind === "disconnect" ? "network.timedOutDisconnecting" : "network.timedOutForgetting"))
      root.actionSsid = ""
      root.actionKind = ""
      root.passwordText = ""
      root.identityText = ""
    }
  }
  Timer {
    id: connectivityPoll
    interval: 10000
    repeat: true
    running: root.restricted && root.checksEnabled
    onTriggered: if (root.kind !== "disconnected") Networking.checkConnectivity()
  }
  Timer {
    id: detailsPoll
    interval: 1500
    repeat: true
    running: root.opened
    onTriggered: root.requestNm("status", [])
  }
  Timer {
    id: activeApSignalPoll
    interval: 1500
    repeat: true
    running: root.needsActiveApSignal
    onTriggered: root.requestNm("signal", [])
  }
}
