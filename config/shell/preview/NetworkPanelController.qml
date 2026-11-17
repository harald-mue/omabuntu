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
  readonly property string pendingDnsProvider: pendingChoice("dns-set")
  readonly property string dnsEffective: pendingDnsProvider !== "" ? pendingDnsProvider : dnsProvider
  property bool customDnsOpen: false
  property string bandCurrent: ""
  property string bandSelected: "auto"
  property var bandAvailable: []
  readonly property string pendingBand: pendingChoice("band-set")
  property int bandIndex: 0
  property bool bandAutoFocused: true
  property int dnsIndex: 0
  property var ethernetProfiles: []
  property var vpnProfiles: []
  property int profileIndex: 0
  property int portalRequest: 0
  property bool profilesOpen: false
  property string serviceNote: ""
  property var queue: []
  property var inFlight: null
  property bool finishing: false
  property var connectionDetails: ({})
  property var detailsMissing: []
  property real prevRxBytes: 0
  property real prevTxBytes: 0
  property real prevSampleTime: 0
  property string prevIface: ""
  property real downloadRate: 0
  property real uploadRate: 0
  readonly property bool hasTransferStats: info.rx_bytes !== undefined && info.tx_bytes !== undefined
  // External probes are not admitted: preserve the original unavailable cells.
  readonly property bool hasInternetPing: false
  readonly property real internetPingLatency: -1
  readonly property int internetPingPacketLoss: 0
  signal shareRequested(string iface, string ssid)
  signal speedRequested(string connection)

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
  readonly property string nativeIface: {
    var device = kind === "ethernet" ? wiredDevice : (kind === "wifi" ? wifiDevice : null)
    return device ? String(device.name || "") : ""
  }
  readonly property var info: {
    if (pendingBand !== "" && nativeIface === "" && connectionDetails.iface) return connectionDetails
    var values = connectionDetails.iface === nativeIface ? connectionDetails : {}
    return Object.assign({}, values, {type: kind, iface: nativeIface,
      ssid: connectedWifiNetwork ? String(connectedWifiNetwork.name || "") : ""})
  }
  onNativeIfaceChanged: Qt.callLater(root.resetDetails)
  function resetDetails() {
    if (pendingBand !== "" && nativeIface === "") return
    connectionDetails = ({})
    prevIface = ""
    prevSampleTime = 0
    downloadRate = 0
    uploadRate = 0
    resetActiveApSignal()
    if (opened && nativeIface !== "") requestNm("details", [nativeIface])
  }
  readonly property bool canDisconnect: !!connectedWifiNetwork
  readonly property bool canShareWifi: kind === "wifi" && !!connectedWifiNetwork
    && !isEnterprise(connectedWifiNetwork.security)
  readonly property bool canRunSpeedTest: info.iface !== ""
  readonly property bool canToggleWifi: networkManagerAvailable && wifiStationAvailable
  readonly property int qrHeaderIndex: canShareWifi ? 0 : -1
  readonly property int speedHeaderIndex: canRunSpeedTest ? (canShareWifi ? 1 : 0) : -1
  readonly property int toggleHeaderIndex: canToggleWifi ? (canShareWifi ? 1 : 0) + (canRunSpeedTest ? 1 : 0) : -1
  readonly property int headerActionCount: (canShareWifi ? 1 : 0) + (canRunSpeedTest ? 1 : 0) + (canToggleWifi ? 1 : 0)
  readonly property bool qrHeaderHasCursor: qrHeaderIndex >= 0 && cursorActive && focusSection === "header" && headerIndex === qrHeaderIndex
  readonly property bool speedHeaderHasCursor: speedHeaderIndex >= 0 && cursorActive && focusSection === "header" && headerIndex === speedHeaderIndex
  readonly property bool toggleHeaderHasCursor: toggleHeaderIndex >= 0 && cursorActive && focusSection === "header" && headerIndex === toggleHeaderIndex
  readonly property string toggleHint: I18n.t(Networking.wifiEnabled ? "network.turnWifiOff" : "network.turnWifiOn")
  property int connectionPhraseIndex: 0
  readonly property var connectionPhrases: [I18n.t("network.phrase1"), I18n.t("network.phrase2"),
    I18n.t("network.phrase3"), I18n.t("network.phrase4"), I18n.t("network.phrase5"),
    I18n.t("network.phrase6"), I18n.t("network.phrase7")]
  readonly property string connectionPhrase: connectionPhrases[connectionPhraseIndex % connectionPhrases.length]
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
  onFocusSectionChanged: syncProfileCursor()
  onEthernetProfilesChanged: syncProfileCursor()
  onVpnProfilesChanged: syncProfileCursor()
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
      profilesOpen = false
      customDnsOpen = false
      serviceNote = ""
      prevSampleTime = 0
      prevIface = ""
      downloadRate = 0
      uploadRate = 0
    }
  }
  Component.onCompleted: syncWifiNetworks()
  Component.onDestruction: if (scannerDevice) scannerDevice.scannerEnabled = false

  function open() { opened = true }
  function close() { opened = false }
  function switchPanel(direction) {
    return bar && typeof bar.switchPanelFrom === "function" ? bar.switchPanelFrom(root, direction) : false;
  }
  function headerDetail() { return Model.headerDetail(info, I18n.formatNumber) }
  function copyToClipboard(value) { if (value) requestNm("copy-address", [String(value)]) }
  function formatBytes(value) { return Model.formatBytes(value, I18n.formatNumber) }
  function formatRate(value) { return Model.formatRate(value, I18n.formatNumber) }
  function formatPingLatency(value) { return Model.formatPingLatency(value, hasInternetPing, I18n.t, I18n.formatNumber) }
  function formatPacketLoss(value) { return Model.formatPacketLoss(value, hasInternetPing, I18n.formatNumber) }
  function applyDetails(payload) {
    var next = payload.details
    if (!next || next.iface !== nativeIface) return
    connectionDetails = Object.assign({}, next, {type: kind, ssid: info.ssid || ""})
    detailsMissing = payload.missing || []
    if (typeof next.rx_bytes !== "number" || typeof next.tx_bytes !== "number") {
      prevIface = ""
      prevSampleTime = 0
      downloadRate = 0
      uploadRate = 0
      return
    }
    var state = Model.throughputState({prevIface: prevIface, prevRxBytes: prevRxBytes,
      prevTxBytes: prevTxBytes, prevSampleTime: prevSampleTime, downloadRate: downloadRate,
      uploadRate: uploadRate}, next, Date.now() / 1000)
    prevIface = state.prevIface
    prevRxBytes = state.prevRxBytes
    prevTxBytes = state.prevTxBytes
    prevSampleTime = state.prevSampleTime
    downloadRate = state.downloadRate
    uploadRate = state.uploadRate
  }
  function toggleProfiles() {
    profilesOpen = !profilesOpen
    if (!profilesOpen && (focusSection === "ethernet" || focusSection === "vpn")) focusSection = "dns"
  }
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
    if (opened) {
      requestNm("status", [])
      if (nativeIface !== "") requestNm("details", [nativeIface])
    }
  }
  function networkHelper() {
    var value = Quickshell.env("OMABUNTU_NETWORK_HELPER")
    if (value === undefined || value === null) return ""
    var text = String(value)
    if (text.indexOf("/network_nm.py") !== text.length - 14 || text.indexOf(" ") !== -1) return ""
    return text
  }
  function pendingChoice(kind) {
    var value = ""
    var requests = (inFlight ? [inFlight] : []).concat(queue || [])
    for (var i = 0; i < requests.length; i++)
      if (requests[i].kind === kind) value = requests[i].args[0]
    return value
  }
  function requestNm(kind, args) {
    if (["status", "signal", "details", "dns-set", "band-set", "connect", "disconnect", "copy-address"].indexOf(kind) < 0) return false
    if (networkHelper() === "") { serviceNote = I18n.t("network.helperUnavailable"); return false }
    var read = kind === "status" || kind === "signal" || kind === "details"
    var next = queue.filter(function(item) {
      if (item.kind !== kind) return true
      // Read refreshes and absolute DNS/band edits coalesce; profile actions do not.
      return !read && kind !== "dns-set" && kind !== "band-set"
    })
    if (next.length >= 64) { serviceNote = I18n.t("network.actionFailed"); return false }
    var item = {kind: kind, args: (args || []).slice(), generation: signalGeneration}
    if (read) queue = next.concat([item])
    else queue = next.filter(function(old) { return ["status", "signal", "details"].indexOf(old.kind) < 0 })
      .concat([item], next.filter(function(old) { return ["status", "signal", "details"].indexOf(old.kind) >= 0 }))
    pumpNm()
    return true
  }
  function pumpNm() {
    if (finishing || nmProc.running || !queue.length) return
    inFlight = queue[0]
    queue = queue.slice(1)
    nmProc.requestKind = inFlight.kind
    nmProc.signalGeneration = inFlight.generation
    nmProc.exec(["python3", networkHelper(), inFlight.kind].concat(inFlight.args))
  }
  function finishNm(kind, code, text) {
    finishing = true
    var item = inFlight
    var payload = null
    try { payload = JSON.parse(String(text || "").trim()) } catch (error) {}
    var accepted = code === 0 && payload && payload.ok === true
    if (item && item.kind === kind) {
      if (kind === "signal" && accepted) applyActiveApSignal(payload, item.generation)
      else if (kind === "details" && accepted) {
        if (item.generation === signalGeneration && item.args[0] === nativeIface) applyDetails(payload)
      } else if (kind === "status" && accepted) {
        dnsProvider = String(payload.dns || "DHCP")
        bandCurrent = String(payload.band || "")
        bandSelected = String(payload.selected || "auto")
        bandAvailable = payload.available || []
        ethernetProfiles = payload.ethernet || []
        vpnProfiles = payload.vpn || []
      } else if (kind === "dns-set" && accepted) dnsProvider = item.args[0]
      else if (kind === "band-set" && accepted) bandSelected = item.args[0]
      if (!accepted) {
        serviceNote = I18n.t("network.actionFailed")
        console.warn("OMABUNTU_NETWORK_REQUEST_FAILED", kind)
      }
    }
    inFlight = null
    // Never launch a poll reentrantly before a waiting user mutation.
    if (item && ["dns-set", "band-set", "connect", "disconnect"].indexOf(kind) >= 0 && opened)
      requestNm("status", [])
    finishing = false
    Qt.callLater(root.pumpNm)
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
  function syncProfileCursor() {
    if (focusSection !== "ethernet" && focusSection !== "vpn") return
    var rows = (focusSection === "vpn" ? vpnProfiles : ethernetProfiles) || []
    if (!profilesOpen || !rows.length) { focusSection = "dns"; profileIndex = 0; return }
    profileIndex = Math.max(0, Math.min(rows.length - 1, profileIndex))
  }
  function moveProfileCursor(delta) {
    if (!profilesOpen) { focusSection = "dns"; return }
    var rows = focusSection === "vpn" ? vpnProfiles : ethernetProfiles
    var next = profileIndex + delta
    if (next >= 0 && next < rows.length) { profileIndex = next; return }
    if (delta < 0) {
      if (focusSection === "vpn" && ethernetProfiles.length) {
        focusSection = "ethernet"
        profileIndex = ethernetProfiles.length - 1
      } else focusSection = "dns"
    } else if (focusSection === "ethernet" && vpnProfiles.length) {
      focusSection = "vpn"
      profileIndex = 0
    } else if (wifiNetworks.length) {
      focusSection = "wifi"
      selectedIndex = 0
    }
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
    if (!canShareWifi || !nativeIface) return
    var iface = nativeIface
    var ssid = info.ssid || "Wi-Fi"
    close()
    shareRequested(iface, ssid)
  }
  function summonSpeedTest() {
    if (!canRunSpeedTest) return
    var name = kind === "wifi" ? info.ssid : I18n.t("network.ethernet")
    close()
    speedRequested(name)
  }
  function setBand(band) {
    if (band !== "auto" && band !== "2.4" && band !== "5" && band !== "6") return
    serviceNote = ""
    requestNm("band-set", [band])
  }
  function setDns(provider) {
    if (provider === "Custom") { customDnsOpen = true; focusSection = "dns"; return }
    if (provider !== "DHCP" && provider !== "Cloudflare" && provider !== "Google") return
    customDnsOpen = false
    serviceNote = ""
    requestNm("dns-set", [provider])
  }
  function applyCustomDns(text) {
    var value = String(text || "").replace(/\s+/g, "").trim()
    if (!/^[0-9a-fA-F:.,]+$/.test(value)) { serviceNote = I18n.t("network.actionFailed"); return }
    serviceNote = ""
    if (!requestNm("dns-set", ["Custom", value])) return
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
    stdout: StdioCollector { id: nmOut; waitForEnd: true }
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
    onTriggered: if (root.nativeIface !== "") root.requestNm("details", [root.nativeIface])
  }
  Timer {
    interval: 10000
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
