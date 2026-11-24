import QtQuick
import Quickshell.Bluetooth
import qs.Commons
import "Port/BluetoothModel.js" as DeviceModel

// Original pending-action semantics, with bounded native BlueZ invocations.
// API state confirms completion, not invocation. No structured operation-error
// signal exists in the pinned API; deadlines report uncertainty, not rejection.
// Optional shared owned-agent actions are separate from the legacy fallback.
// No automatic trust, audio routing, rfkill, service restart or default-agent takeover.
DesktopPanelController {
  id: actions
  readonly property var adapter: Bluetooth.defaultAdapter
  readonly property var devices: adapter && adapter.devices ? adapter.devices.values : []
  property var session: null
  property string rowOwner: Date.now().toString(16) + Math.random().toString(16).slice(2)
  property var rowIdentities: new WeakMap()
  property var rowCounter: ({value:0})
  function projectDevice(device) {
    if (!resolveDevice(device)) return null;
    if (!rowIdentities.has(device)) rowIdentities.set(device, ++rowCounter.value);
    return Object.freeze(Object.assign({}, DeviceModel.deviceRow(device), {control:Object.freeze({
      owner:rowOwner, generation:rowIdentities.get(device), path:device.dbusPath, adapter:adapter.dbusPath})}));
  }
  function resolveRow(row) {
    if (!row || !row.dev || !row.dev.control || row.dev.control.owner !== rowOwner
        || !adapter || row.dev.control.adapter !== adapter.dbusPath) return null;
    for (var i=0;i<devices.length;i++) {
      var device=devices[i];
      if (device.address === row.dev.address && device.dbusPath === row.dev.control.path
          && rowIdentities.get(device) === row.dev.control.generation) return device;
    }
    return null;
  }
  property bool ownsDiscovery: false
  property var pendingRecords: ({})
  property string errorText: ""
  onOpenedChanged: {
    cursorActive = false;
    if (opened) { BluetoothDiscovery.acquire(actions, adapter); ownsDiscovery = true; }
    else {
      if (session && session.pending && session.prompt) session.cancel();
      BluetoothDiscovery.release(actions); ownsDiscovery = false;
    }
  }
  onAdapterChanged: {
    if (Object.keys(pendingRecords).length) errorText = "Bluetooth adapter changed; pending actions were not replayed";
    pendingRecords = ({});
    BluetoothDiscovery.release(actions);
    if (opened) BluetoothDiscovery.acquire(actions, adapter);
  }
  onDevicesChanged: syncPendingActions()
  Component.onDestruction: BluetoothDiscovery.release(actions)
  Connections {
    target: actions.adapter
    function onEnabledChanged() {
      actions.syncPendingActions();
      if (actions.opened) BluetoothDiscovery.acquire(actions, actions.adapter);
    }
  }
  Connections {
    target: actions.session
    function onErrorTextChanged() { actions.errorText = actions.session.errorText; }
  }
  function toggleBluetooth() {
    if (session && session.pending) { errorText = "Cancel the current Bluetooth request before changing the adapter"; return; }
    if (adapter) adapter.enabled = !adapter.enabled;
  }
  function pendingAction(address) {
    if (typeof session !== "undefined" && session && session.pending && session.pending.address === address) return session.pending.action;
    return pendingRecords[address] ? pendingRecords[address].action : "";
  }
  function resolveDevice(device) {
    if (!device || !adapter || !device.address || !device.dbusPath || !adapter.dbusPath) return null;
    // Initial calls must carry the actual current object, not a retained wrapper
    // or a forged primitive. Subsequent polls store only path/address primitives.
    return devices.indexOf(device) >= 0 ? device : null;
  }
  function beginDeviceAction(device, action) {
    if (["connecting", "disconnecting", "forgetting"].indexOf(action) < 0) return false;
    if (typeof session !== "undefined" && session && session.configured) {
      device = resolveDevice(device);
      if (!device) { errorText = "Bluetooth device is no longer available"; return false; }
      return session.begin(device, adapter, action);
    }
    // Legacy paired-device controls remain available in bundles without the
    // optional helper. Unpaired actions require the owned-agent capability.
    if (typeof session !== "undefined" && session && action === "connecting" && device && !device.paired && !device.bonded) {
      errorText = "Owned Bluetooth pairing helper unavailable; no agent or package installed automatically"; return false;
    }
    syncPendingActions();
    device = resolveDevice(device);
    if (!device) { errorText = "Bluetooth device is no longer available"; return false; }
    if (pendingAction(device.address)) { errorText = "A Bluetooth action is still pending for this device"; return false; }
    if (action === "connecting" && (!adapter.enabled || device.blocked)) {
      errorText = "Bluetooth is off or this device is blocked"; return false;
    }
    var record = {address:device.address, path:device.dbusPath, adapter:adapter.dbusPath,
      action:action, phase:action, deadline:Date.now() + 30000};
    var next = Object.assign({}, pendingRecords);
    next[record.address] = record;
    pendingRecords = next;
    errorText = "";
    try {
      if (action === "connecting") {
        if (device.paired || device.bonded) device.connect();
        else {
          // Pairing uses the existing session agent only. Being trusted alone
          // is not pairing acceptance and never grants us an agent or trust.
          record.phase = "pairing";
          device.pair();
        }
      } else if (action === "disconnecting") device.disconnect();
      else if (action === "forgetting") device.forget();
    } catch (error) {
      next = Object.assign({}, pendingRecords);
      delete next[record.address];
      pendingRecords = next;
      errorText = "Bluetooth action could not be issued; inspect the device state";
      return false;
    }
    return true;
  }
  function connectDevice(device) {
    if (!resolveDevice(device)) { errorText = "Bluetooth device is no longer available"; return false; }
    if (device.connected) return false;
    return beginDeviceAction(device, "connecting");
  }
  function disconnectDevice(device) {
    if (!resolveDevice(device)) { errorText = "Bluetooth device is no longer available"; return false; }
    if (!device.connected) return false;
    return beginDeviceAction(device, "disconnecting");
  }
  function forgetDevice(device) { return beginDeviceAction(device, "forgetting"); }
  function syncPendingActions() {
    var next = Object.assign({}, pendingRecords);
    var changed = false;
    for (var address in next) {
      var record = next[address];
      var found = null;
      for (var i = 0; i < devices.length; ++i) {
        var device = devices[i];
        if (device && device.address === address && device.dbusPath === record.path) { found = device; break; }
      }
      var ownerLost = !adapter || adapter.dbusPath !== record.adapter;
      var finished = !ownerLost && (
        (record.action === "connecting" && found && found.connected)
        || (record.action === "disconnecting" && found && !found.connected)
        || (record.action === "forgetting" && (!found || (!found.paired && !found.bonded && !found.trusted))));
      if (finished) {
        delete next[address]; changed = true;
        if (errorText === "A Bluetooth action is still pending for this device") errorText = "";
        continue;
      }
      if (ownerLost || !found || (record.action === "connecting" && !adapter.enabled)
          || Date.now() >= record.deadline) {
        delete next[address]; changed = true;
        errorText = "Bluetooth action did not complete; inspect the device and existing pairing agent";
        continue;
      }
      if (record.phase === "pairing" && (found.paired || found.bonded) && !found.pairing) {
        // Advance before invocation so state notifications cannot repeat it.
        next[address] = Object.assign({}, record, {phase:"connecting"});
        pendingRecords = next;
        changed = true;
        try { found.connect(); }
        catch (error) {
          delete next[address];
          errorText = "Bluetooth connection could not be issued after pairing";
        }
      }
    }
    if (changed) pendingRecords = Object.assign({}, next);
  }
  // Operation deadline only: the panel/bar themselves never expire.
  Timer {
    interval: 250; repeat: true; running: Object.keys(actions.pendingRecords).length > 0
    onTriggered: actions.syncPendingActions()
  }
}
