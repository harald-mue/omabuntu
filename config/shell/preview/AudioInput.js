.pragma library
.import "AudioRouting.js" as Routing
.import "AudioPresentation.js" as Presentation

// Typed microphone ownership only. No helpers, graph policy or untyped setters.
// Authority is provider-local; delegates retain primitive proofs, not QObjects.
function eligible(node) {
  return !!node && node.isSink === false && node.isStream === false && !!node.audio
    && typeof node.name === "string" && node.name !== "quickshell";
}

function usable(node) {
  return eligible(node) && node.ready && typeof node.audio.volume === "number"
    && isFinite(node.audio.volume) && typeof node.audio.muted === "boolean";
}

function snapshot(ready, nodes, source, authority) {
  var base = Presentation.inputSnapshot(ready, nodes, source);
  var current = null;
  var rows = base.inputs.map(function(row) {
    var matches = nodes.filter(function(node) {
      return eligible(node) && node.id === row.id && node.name === row.name;
    });
    var node = matches.length === 1 ? matches[0] : null;
    var control = node && Routing.currentNode(nodes, node) && usable(node)
      ? authority.capture(node) : null;
    var entry = Object.freeze(Object.assign({}, row, {control:control, controlAvailable:!!control}));
    // The native default must be this object, not a replacement sharing its ID.
    if (node && node === source && Routing.currentNode(nodes, source)) current = entry;
    return entry;
  });
  return Object.freeze({ready:base.ready, defaultPresent:!!source,
    current:current, inputs:Object.freeze(rows)});
}

function target(ready, nodes, source, authority, row, requireDefault) {
  if (!ready || !row || !row.control || row.controlAvailable !== true
      || row.id !== row.control.id || row.name !== row.control.name
      || row.serial !== row.control.serial) return null;
  for (var i = 0; i < nodes.length; ++i) {
    var node = nodes[i];
    if (!usable(node) || !Routing.currentNode(nodes, node)) continue;
    if (requireDefault && node !== source) continue;
    if (Routing.sameKey(authority.capture(node), row.control)) return node;
  }
  return null;
}
