.pragma library

// Resolve fresh on every action: PipeWire may reuse an ID after hot-unplug.
// Output, typed input and playback streams have separate mutation boundaries.
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

// Eligibility must not inspect properties: nodes are not bound yet while
// PwObjectTracker is selecting them. Capture/processing/shell streams stay out.
function playbackStream(node) {
  return !!node && node.isSink === true && node.isStream === true && !!node.audio
    && String(node.name || "") !== "quickshell"
    && String(node.name || "").indexOf("omarchy_speaker_tuning") !== 0;
}

function streamSerial(node) {
  if (!node || !node.ready) return "";
  var props = node.properties || {};
  var serial = String(props["object.serial"] || "");
  return /^[1-9][0-9]{0,19}$/.test(serial) ? serial : "";
}

// Streams are short-lived and names/IDs can both be reused. The bound PipeWire
// object serial is mandatory; missing identity fails closed, never falls back.
function resolveStream(nodes, key) {
  if (!key || typeof key.name !== "string" || !key.name || !Number.isInteger(key.id)
      || typeof key.serial !== "string" || !/^[1-9][0-9]{0,19}$/.test(key.serial)) return null;
  for (var i = 0; i < nodes.length; ++i) {
    var node = nodes[i];
    if (playbackStream(node) && node.ready && node.id === key.id
        && node.name === key.name && streamSerial(node) === key.serial) return node;
  }
  return null;
}

// The hero owns output AND microphone. Capture keys include object.serial so
// an ID/name reused between projection and activation cannot unmute a new node.
function masterTarget(nodes, key, source) {
  var node = source ? resolveSource(nodes, key) : resolve(nodes, key);
  return node && key && typeof key.serial === "string" && key.serial !== ""
    && streamSerial(node) === key.serial ? node : null;
}

function masterDefaultMatches(key, node) {
  if (!key) return !node;
  return !!node && node.ready && node.id === key.id && node.name === key.name
    && typeof key.serial === "string" && key.serial !== ""
    && streamSerial(node) === key.serial;
}

function toggleAllMuted(outputs, sources, outputKey, inputKey) {
  if ((outputKey !== null && (!outputKey || typeof outputKey !== "object"))
      || (inputKey !== null && (!inputKey || typeof inputKey !== "object"))) return false;
  var output = outputKey ? masterTarget(outputs, outputKey, false) : null;
  var input = inputKey ? masterTarget(sources, inputKey, true) : null;
  // Preflight every requested channel before writing either one. A vanished
  // channel must not turn a two-channel request into a silent partial action.
  if ((!output && outputKey) || (!input && inputKey) || (!output && !input)) return false;
  var mute = !!((output && !output.audio.muted) || (input && !input.audio.muted));
  try {
    if (output) output.audio.muted = mute;
    if (input) input.audio.muted = mute;
  } catch (error) {
    // Native setters are not atomic across channels. Never retry or unmute as
    // compensation; the caller reports uncertainty and rereads native state.
    return false;
  }
  return true;
}

function setStreamVolume(nodes, key, value) {
  if (typeof value !== "number" || !isFinite(value)) return false;
  var node = resolveStream(nodes, key);
  if (!node) return false;
  // Match the original stream slider's explicit 0..150% range, not device gain.
  node.audio.volume = Math.max(0, Math.min(1.5, value));
  return true;
}

function toggleStreamMute(nodes, key) {
  var node = resolveStream(nodes, key);
  if (!node) return false;
  node.audio.muted = !node.audio.muted;
  return true;
}
