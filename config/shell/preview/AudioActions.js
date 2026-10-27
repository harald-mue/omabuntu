.pragma library

// Resolve fresh on every action: PipeWire may reuse an ID after hot-unplug.
// Only playback devices are writable here, never streams or capture devices.
function resolve(nodes, key) {
  if (!key || typeof key.name !== "string" || !key.name || !Number.isInteger(key.id)) return null;
  for (var i = 0; i < nodes.length; ++i) {
    var node = nodes[i];
    if (node && node.id === key.id && node.name === key.name && node.ready
        && node.isSink && !node.isStream && node.audio) return node;
  }
  return null;
}

function setVolume(nodes, key, value) {
  if (typeof value !== "number" || !isFinite(value)) return false;
  var node = resolve(nodes, key);
  if (!node) return false;
  node.audio.volume = Math.max(0, Math.min(1, value));
  return true;
}

function toggleMute(nodes, key) {
  var node = resolve(nodes, key);
  if (!node) return false;
  node.audio.muted = !node.audio.muted;
  return true;
}

// Typed capture devices only, mirroring the sink resolver above: never
// streams, never sinks, and no node Quickshell leaves without PwNode.audio.
// Untyped virtual sources stay excluded; they need the excluded upstream
// process route.
function resolveSource(nodes, key) {
  if (!key || typeof key.name !== "string" || !key.name || !Number.isInteger(key.id)) return null;
  for (var i = 0; i < nodes.length; ++i) {
    var node = nodes[i];
    if (node && node.id === key.id && node.name === key.name && node.ready
        && !node.isSink && !node.isStream && node.audio) return node;
  }
  return null;
}

function setSourceVolume(nodes, key, value) {
  if (typeof value !== "number" || !isFinite(value)) return false;
  var node = resolveSource(nodes, key);
  if (!node) return false;
  node.audio.volume = Math.max(0, Math.min(1, value));
  return true;
}

function toggleSourceMute(nodes, key) {
  var node = resolveSource(nodes, key);
  if (!node) return false;
  node.audio.muted = !node.audio.muted;
  return true;
}
