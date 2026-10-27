.pragma library

// Copies display primitives only. Never retains WifiNetwork QObject wrappers,
// calls methods, reads nmSettings, or changes any NetworkManager property.
function snapshot(available, devices, types, connectivity, states, checksEnabled) {
  var rows = [], wired = null, wifi = null;
  for (var i = 0; available && i < devices.length; ++i) {
    var device = devices[i];
    if (!device || (device.type !== types.Wired && device.type !== types.Wifi)) continue;
    var name = String(device.name || "");
    var connected = !!device.connected;
    var isWifi = device.type === types.Wifi;
    var label = "", signal = -1;
    if (isWifi) {
      var networks = device.networks ? device.networks.values : [];
      for (var n = 0; n < networks.length; ++n) {
        var network = networks[n];
        if (!network || !network.connected) continue;
        label = String(network.name || "");
        var raw = Number(network.signalStrength);
        signal = isFinite(raw) ? Math.max(0, Math.min(100, Math.round(raw * 100))) : -1;
        break;
      }
    }
    var row = Object.freeze({name:name, kind:isWifi ? "wifi" : "ethernet", connected:connected,
                             label:label, signal:signal});
    rows.push(row);
    if (connected && isWifi && wifi === null) wifi = row;
    if (connected && !isWifi && wired === null) wired = row;
  }
  // Matches Omarchy's wired-first display policy. This is not a VPN/default
  // route detector, nor proof that an Internet endpoint is reachable.
  var active = wired || wifi;
  var kind = !available ? "unknown" : (active ? active.kind : "disconnected");
  var status = kind === "unknown" ? "unknown" : kind === "disconnected" ? "none" : "unknown";
  if (active && checksEnabled) {
    if (connectivity === states.Portal) status = "portal";
    else if (connectivity === states.Limited) status = "limited";
    else if (connectivity === states.Full) status = "full";
    else if (connectivity === states.None) status = "none";
  }
  return Object.freeze({available:!!available, kind:kind, connectivity:status,
                        signal:active ? active.signal : -1,
                        label:active ? (active.label || active.name) : "",
                        devices:Object.freeze(rows)});
}
