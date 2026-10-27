"""Synthetic Wi-Fi control probes. The fixture module replaces Quickshell.Networking."""
import re

CASES = ("connect-known", "passphrase", "enterprise", "disconnect-forget", "toggle-scan", "stale", "refresh-state", "navigation-state", "scan-state", "signal-state", "negative")
MARKER = "OMABUNTU_WIFI_FIXTURE_OK"
ENUMS = {
    "NetworkBackendType": {"None": 0, "NetworkManager": 1},
    "DeviceType": {"None": 0, "Wifi": 1, "Wired": 2},
    "NetworkConnectivity": {"Unknown": 0, "None": 1, "Portal": 2, "Limited": 3, "Full": 4},
    "WifiSecurityType": {"Wpa3SuiteB192": 0, "Sae": 1, "Wpa2Eap": 2, "Wpa2Psk": 3, "WpaEap": 4,
                         "WpaPsk": 5, "StaticWep": 6, "DynamicWep": 7, "Leap": 8, "Owe": 9, "Open": 10, "Unknown": 11},
    "ConnectionFailReason": {"Unknown": 0, "NoSecrets": 1, "WifiClientDisconnected": 2,
                             "WifiClientFailed": 3, "WifiAuthTimeout": 4, "WifiNetworkLost": 5},
}
NETWORK = """import QtQml
QtObject {
  property string name: ""
  property bool connected: false
  property bool known: false
  property bool stateChanging: false
  property real signalStrength: 0
  property int security: 10
  property int connectCount: 0
  property int disconnectCount: 0
  property int forgetCount: 0
  property int pskCount: 0
  property bool pskAccepted: false
  signal connectionFailed(int reason)
  function connect() { connectCount += 1 }
  function disconnect() { disconnectCount += 1 }
  function forget() { forgetCount += 1 }
  function connectWithPsk(value) { pskCount += 1; pskAccepted = value === "fixture-psk" }
}
"""
DEVICE = """import QtQml
QtObject {
  property int type: 1
  property string name: "wlan-fixture"
  property bool connected: false
  property string address: "192.0.2.20"
  property bool scannerEnabled: false
  property var networks: ({ values: [] })
  function disconnect() { throw new Error("device disconnect is not a network action"); }
}
"""
NETWORKING = """pragma Singleton
import QtQml
QtObject {
  property int backend: 1
  property bool wifiEnabled: true
  property bool wifiHardwareEnabled: true
  property bool canCheckConnectivity: true
  property bool connectivityCheckEnabled: true
  property int connectivity: 4
  property var devices: ({ values: [] })
  property int checks: 0
  function checkConnectivity() { checks += 1 }
}
"""


def enum_qml(name, values):
    # QML enum values are addressable as Type.Value. Properties cannot use those names.
    body = ",\n".join("    " + key + " = " + str(value) for key, value in values.items())
    return "pragma Singleton\nimport QtQml\nQtObject {\n  enum Value {\n" + body + "\n  }\n}\n"


def fixture(name):
    if name not in CASES:
        raise ValueError("Unknown wifi fixture")
    return """//@ pragma IgnoreSystemSettings
import QtQuick
import Quickshell
import "FixtureNetworking" as Net
ShellRoot {
  id: test
  property int phase: 0
  property int waits: 0
  property var owner: null
  property var view: null
  property var device: null
  property var known: null
  property var locked: null
  property var enterprise: null
  function require(value, message) { if (!value) throw new Error(message); }
  function make(entryName, security, strength, isKnown) {
    var factory = Qt.createComponent("FixtureNetwork.qml", Component.PreferSynchronous);
    require(factory.status === Component.Ready, factory.errorString());
    var item = factory.createObject(test, {name:entryName, security:security, signalStrength:strength, known:isKnown});
    factory.destroy();
    return item;
  }
  Window {
    id: scene
    width: 420
    height: 320
    visible: true
  }
  Timer {
    interval: 180
    running: true
    repeat: true
    onTriggered: {
      try {
        var mode = "%s";
        if (test.phase === 0) {
          var factory = Qt.createComponent("PortTrayHost.qml", Component.PreferSynchronous);
          require(factory.status === Component.Ready, factory.errorString());
          test.owner = factory.createObject(scene); factory.destroy();
          factory = Qt.createComponent("FixtureDevice.qml", Component.PreferSynchronous);
          require(factory.status === Component.Ready, factory.errorString());
          test.device = factory.createObject(test); factory.destroy();
          test.known = test.make("Known", 10, 0.9, true);
          test.locked = test.make("Locked", 3, 0.5, false);
          test.enterprise = test.make("Enterprise", 2, 0.1, false);
          test.device.networks = ({ values: [test.known, test.locked, test.enterprise] });
          if (mode === "disconnect-forget") { test.known.connected = true; test.device.connected = true; }
          Net.Networking.devices = ({ values: [test.device] });
          factory = Qt.createComponent("NetworkControlView.qml", Component.PreferSynchronous);
          require(factory.status === Component.Ready, factory.errorString());
          test.view = factory.createObject(scene, {bar:test.owner.ownerApi}); factory.destroy();
          require(test.view !== null && !test.view.opened && !test.device.scannerEnabled && test.known.connectCount === 0, "no connection or scan before opening");
          require(test.view.wifiNetworks.length === 3 && test.view.wifiNetworks[0].ssid === "Known", "known networks stay ahead of stronger unknown ones");
          test.view.open();
          test.phase = 1;
          return;
        }
        if (!test.device.scannerEnabled && test.waits < 6) { test.waits += 1; return }
        require(test.device.scannerEnabled === true, "opening enables the station scanner");
        if (mode === "connect-known") {
          test.view.connectDirectly("Known");
          require(test.known.connectCount === 1 && test.locked.pskCount === 0 && test.enterprise.connectCount === 0, "known profile connects directly");
        }
        if (mode === "passphrase") {
          test.view.openPasswordPrompt("Locked");
          test.view.connectWithPassphrase("Locked", "fixture-psk");
          require(test.locked.pskAccepted && test.locked.pskCount === 1 && test.view.passwordText === "" && test.known.connectCount === 0, "passphrase is delivered once and cleared");
        }
        if (mode === "enterprise") {
          test.view.selectedIndex = 2; test.view.focusSection = "wifi"; test.view.cursorActive = true; test.view.activateSelected();
          require(test.enterprise.connectCount === 0 && test.enterprise.pskCount === 0 && test.view.failureSsid === "Enterprise" && test.view.passwordText === "", "unsaved enterprise profile is refused");
          test.enterprise.known = true; test.view.connectDirectly("Enterprise");
          require(test.enterprise.connectCount === 1, "saved enterprise profile activates without a new secret");
        }
        if (mode === "disconnect-forget") {
          test.view.disconnectRow("Known");
          require(test.known.disconnectCount === 1, "connected row disconnects that network");
          test.known.connected = false; test.view.clearAction(); test.view.forget({ssid:"Known"});
          require(test.known.forgetCount === 1, "saved disconnected network can be forgotten");
        }
        if (mode === "toggle-scan") {
          var enabled = Net.Networking.wifiEnabled;
          test.view.toggleNetwork();
          require(Net.Networking.wifiEnabled !== enabled && test.known.connectCount === 0, "radio toggle does not connect");
        }
        if (mode === "stale") {
          test.known.connected = true;
          test.view.disconnectRow("Missing");
          require(test.known.disconnectCount === 0 && test.locked.disconnectCount === 0, "stale SSID does not disconnect another network");
        }
        if (mode === "refresh-state") {
          if (test.phase === 1) {
            test.view.selectedIndex = 0; test.view.wifiActionFocused = true;
            test.view.forget({ssid:"Known"});
            require(test.view.busy, "forget starts busy");
            test.known.known = false;
            test.phase = 2; return;
          }
          var index = test.view.wifiIndexForSsid("Known");
          if (test.phase === 2) {
            require(!test.view.busy && !test.view.wifiNetworks[index].known, "forget updates snapshot without reopening or replacing objects");
            require(!test.view.wifiActionFocused, "forget action focus cleared");
            test.view.connectDirectly("Known"); test.known.connected = true;
            test.phase = 3; return;
          }
          if (test.phase === 3) {
            require(!test.view.busy && test.view.wifiNetworks[index].connected, "connect updates snapshot");
            test.view.disconnectRow("Known"); test.known.connected = false;
            test.phase = 4; return;
          }
          if (test.phase === 4) {
            require(!test.view.busy && !test.view.wifiNetworks[index].connected, "disconnect updates snapshot");
            test.view.connectDirectly("Known"); test.known.known = true;
            test.known.connectionFailed(0);
            test.phase = 5; return;
          }
          require(!test.view.busy && test.view.wifiNetworks[index].known, "failure updates snapshot");
        }
        if (mode === "navigation-state") {
          if (test.phase === 1) {
            test.view.dnsProvider = "Google";
            test.view.bandAvailable = ["2.4", "5", "6"]; test.view.bandSelected = "6";
            require(test.view.dnsIndex === 2 && test.view.bandIndex === 2, "async settings align keyboard indices");
            test.known.connected = true;
            Net.Networking.connectivity = 2;
            require(test.view.focusSection === "portal", "portal arrival takes cursor");
            Net.Networking.connectivity = 4;
            require(test.view.focusSection !== "portal", "portal departure releases cursor");
            test.view.openPasswordPrompt("Locked");
            test.view.selectedIndex = 0; test.view.syncWifiNetworks();
            require(test.view.wifiNetworks[test.view.selectedIndex].ssid === "Locked", "password selection follows SSID");
            test.view.cancelPasswordPrompt(); test.phase = 2; return;
          }
          require(scene.activeFocusItem !== null && scene.activeFocusItem.blocked === false, "password dismissal restores key catcher focus");
          test.view.selectedIndex = 2;
          test.device.networks = ({values:[test.known]});
          require(test.view.selectedIndex === 0, "shrinking list clamps selection");
          test.view.focusSection = "wifi"; test.device.networks = ({values:[]});
          require(test.view.selectedIndex === -1 && test.view.focusSection === "dns", "empty list restores valid section");
        }
        if (mode === "scan-state") {
          if (test.phase === 1) {
            test.locked.signalStrength = 0.99;
            require(test.view.wifiNetworks[test.view.wifiIndexForSsid("Locked")].signal === 50, "snapshot waits for scan completion");
            test.phase = 2; test.waits = 0; return;
          }
          if (test.view.scanning && test.waits++ < 15) return;
          require(!test.view.scanning && test.view.wifiNetworks[test.view.wifiIndexForSsid("Locked")].signal === 99, "scan completion rebuilds unchanged object list");
        }
        if (mode === "signal-state") {
          test.known.connected = true; test.known.signalStrength = 0;
          test.view.finishNm("signal", 0, JSON.stringify({ok:true, iface:"wlan-fixture", signal:73}));
          require(test.view.activeApSignal === -1, "unsolicited generation cannot update strength");
          var generation = test.view.signalGeneration;
          test.view.applyActiveApSignal({iface:"other", signal:95}, generation);
          require(test.view.activeApSignal === -1, "different interface is ignored");
          test.view.applyActiveApSignal({iface:"wlan-fixture", signal:73}, generation);
          require(test.view.signalStrength === 73, "active AP fallback supplies strength");
          test.view.applyActiveApSignal({iface:"wlan-fixture", signal:null}, generation);
          require(test.view.activeApSignal === -1, "malformed strength is unknown rather than zero");
          test.known.connected = false;
          test.view.applyActiveApSignal({iface:"wlan-fixture", signal:73}, generation);
          require(test.view.activeApSignal === -1, "link change invalidates in-flight strength");
        }
        test.view.close();
        require(test.device.scannerEnabled === false, "closing releases the scanner");
        if (mode === "negative") throw new Error("deliberate wifi assertion");
        console.log("%s::" + mode);
        running = false;
        test.view.destroy(); test.owner.destroy(); Qt.callLater(function() { Qt.quit(); });
      } catch (error) { running = false; console.error("OMABUNTU_WIFI_ASSERT", String(error)); Qt.callLater(function() { Qt.exit(42); }); }
    }
  }
}
""" % (name, MARKER)


def classify(name, code, text):
    if name not in CASES:
        return False
    errors = re.findall(r"^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b.*", text, re.M)
    if name == "negative":
        return code == 42 and len(errors) == 1 and "deliberate wifi assertion" in errors[0] and MARKER not in text
    return code == 0 and not errors and text.count(MARKER + "::" + name) == 1 and "Configuration Loaded" in text
