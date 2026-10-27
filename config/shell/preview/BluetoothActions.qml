import QtQuick
import Quickshell.Bluetooth
import qs.Commons

// Native BlueZ actions. Discovery is stopped only if this panel started it.
// No automatic audio routing, rfkill, service restart or pairing-agent setup.
DesktopPanelController {
  id: actions
  readonly property var adapter: Bluetooth.defaultAdapter
  readonly property var devices: adapter && adapter.devices ? adapter.devices.values : []
  property bool ownsDiscovery: false
  property string pairingAddress: ""
  property string errorText: ""
  onOpenedChanged: {
    cursorActive = false;
    if (opened) { BluetoothDiscovery.acquire(actions, adapter); ownsDiscovery = true; }
    else { BluetoothDiscovery.release(actions); ownsDiscovery = false; }
  }
  Component.onDestruction: BluetoothDiscovery.release(actions)
  Connections {
    target: actions.adapter
    function onEnabledChanged() {
      if (actions.opened) BluetoothDiscovery.acquire(actions, actions.adapter);
    }
  }
  function toggleBluetooth() { if (adapter) adapter.enabled = !adapter.enabled; }
  function connectDevice(device) {
    if (!device || !adapter || !adapter.enabled) return;
    errorText = "";
    if (!device.paired && !device.bonded) {
      pairingAddress = device.address;
      pairingDeadline.restart();
      device.pair();
    } else device.connect();
  }
  function disconnectDevice(device) { if (device) device.disconnect(); }
  function forgetDevice(device) { if (device) device.forget(); }
  function pendingAction(address) { return pairingAddress === address ? "connecting" : ""; }
  Timer {
    interval: 250; repeat: true; running: actions.pairingAddress !== ""
    onTriggered: {
      for (var i = 0; i < actions.devices.length; i++) {
        var device = actions.devices[i];
        if (device.address === actions.pairingAddress && device.paired && !device.pairing) {
          actions.pairingAddress = ""; pairingDeadline.stop(); device.connect(); return;
        }
      }
    }
  }
  Timer {
    id: pairingDeadline
    interval: 30000
    onTriggered: { actions.errorText = "Pairing did not complete; an existing BlueZ agent may be required"; actions.pairingAddress = ""; }
  }
}
