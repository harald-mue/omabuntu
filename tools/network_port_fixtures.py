"""Fixed synthetic network-presentation probes. Never instantiate native Networking."""
import re

CASES = ("unavailable", "disconnected", "ethernet", "wifi", "restricted", "changes", "negative")
MARKER = "OMABUNTU_NETWORK_FIXTURE_OK"


def fixture(name):
    if name not in CASES:
        raise ValueError("Unknown network fixture")
    return '''//@ pragma IgnoreSystemSettings
import QtQuick
import Quickshell
import "NetworkPresentation.js" as Presentation
import "Port/NetworkModel.js" as Model
ShellRoot {
  property var owner: null
  property var view: null
  function require(value, message) { if (!value) throw new Error(message); }
  function mutation() { throw new Error("forbidden network mutation"); }
  Timer { interval: 200; running: true; onTriggered: {
    try {
      var mode = "%s";
      var types = {Wired:1, Wifi:2};
      var states = {None:1, Portal:2, Limited:3, Full:4};
      require(Model.wifiIconFor(0) === "󰤯" && Model.wifiIconFor(21) === "󰤟" && Model.wifiIconFor(100) === "󰤨", "original signal thresholds");
      require(Model.connectionIcon("ethernet",-1,"portal") === "󰈂", "restricted ethernet glyph");
      require(Model.connectionIcon("wifi",72,"limited") === "󰤩", "restricted wifi glyph");
      var wifi = {type:2, name:"wlan-fixture", connected:true,
        networks:{values:[{connected:true, name:"<b>Fixture</b>", signalStrength:0.72,
                          connect:mutation, forget:mutation, disconnect:mutation}]},
        disconnect:mutation};
      var wire = {type:1, name:"ethernet-fixture", connected:true, disconnect:mutation};
      var devices = [];
      if (mode === "wifi" || mode === "restricted" || mode === "changes") devices = [wifi];
      if (mode === "ethernet" || mode === "unavailable") devices = [wifi,wire];
      var conn = mode === "restricted" ? 2 : 4;
      var snapshot = Presentation.snapshot(mode !== "unavailable",devices,types,conn,states,true);
      require(Object.isFrozen(snapshot) && Object.isFrozen(snapshot.devices), "frozen display snapshot");
      for (var row of snapshot.devices) require(Object.isFrozen(row), "frozen row");
      var factory = Qt.createComponent("PortTrayHost.qml", Component.PreferSynchronous);
      require(factory.status === Component.Ready, factory.errorString());
      owner = factory.createObject(null); factory.destroy();
      factory = Qt.createComponent("NetworkStatusView.qml", Component.PreferSynchronous);
      require(factory.status === Component.Ready, factory.errorString());
      view = factory.createObject(null,{bar:owner.ownerApi,state:snapshot}); factory.destroy();
      require(view !== null, "network view construction");
      if (mode === "unavailable") require(snapshot.kind === "unknown" && view.icon === "?" && snapshot.devices.length === 0 && snapshot.connectivity === "unknown", "unknown is not disconnected or stale-connected");
      if (mode === "disconnected") require(snapshot.kind === "disconnected", "disconnected devices");
      if (mode === "ethernet") require(snapshot.kind === "ethernet" && snapshot.label === "ethernet-fixture", "wired first");
      if (mode === "wifi" || mode === "restricted") require(snapshot.signal === 72 && snapshot.label === "<b>Fixture</b>", "primitive wifi values");
      require(view.icon === (snapshot.kind === "unknown" ? "?" : Model.connectionIcon(snapshot.kind,snapshot.signal,snapshot.connectivity)), "original icon model");
      if (mode === "restricted") require(snapshot.connectivity === "portal", "cached portal state");
      var noProbe = Presentation.snapshot(true,devices,types,2,states,false);
      if (devices.length > 0) require(noProbe.connectivity === "unknown", "ignore disabled cached probe");
      var noAp = Presentation.snapshot(true,[{type:2,name:"wifi-no-ap",connected:true,networks:{values:[]}}],types,4,states,true);
      require(noAp.kind === "wifi" && noAp.signal === -1, "connected device survives AP churn without invented signal");
      if (mode === "changes") {
        wifi.networks.values[0].name = "Changed";
        require(snapshot.label === "<b>Fixture</b>", "snapshot retained no live network wrapper");
        view.state = Presentation.snapshot(true,[],types,4,states,true);
        require(view.state.kind === "disconnected" && view.state.devices.length === 0, "device removal");
      }
      require(!view.opened, "no popup opens automatically");
      if (mode === "negative") throw new Error("deliberate network assertion");
      console.log("%s::" + mode);
      view.destroy(); owner.destroy(); Qt.callLater(function() { Qt.quit(); });
    } catch(error) { console.error("OMABUNTU_NETWORK_ASSERT", String(error)); Qt.callLater(function() { Qt.exit(42); }); }
  } }
}
''' % (name, MARKER)


def classify(name, code, text):
    if name not in CASES:
        return False
    errors = re.findall(r"^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b.*", text, re.M)
    if name == "negative":
        return code == 42 and len(errors) == 1 and "deliberate network assertion" in errors[0] and MARKER not in text
    return code == 0 and not errors and text.count(MARKER + "::" + name) == 1 and "Configuration Loaded" in text
