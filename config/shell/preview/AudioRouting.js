.pragma library
.import "AudioActions.js" as Actions

// Native endpoint adapter for the reviewed original output-sink helper policy.
// No subprocesses, graph edits, playback, profile switches or idle config reads.
var authoritySerial = 0;
function createAuthority() {
  var scope = ++authoritySerial;
  var identities = new WeakMap();
  var serial = 0;
  function capture(node) {
    if (!Number.isSafeInteger(scope) || !node || !node.ready || !Number.isInteger(node.id)
        || typeof node.name !== "string" || !node.name) return null;
    var objectSerial = Actions.streamSerial(node);
    if (!objectSerial) return null;
    var old = identities.get(node);
    if (old && old.id === node.id && old.name === node.name && old.serial === objectSerial) return old;
    if (serial >= Number.MAX_SAFE_INTEGER) return null;
    var key = Object.freeze({scope:scope, id:node.id, name:node.name, serial:objectSerial, generation:++serial});
    identities.set(node, key);
    return key;
  }
  return Object.freeze({capture:capture});
}

function sink(node) {
  return !!node && node.isSink === true && node.isStream === false && !!node.audio;
}

function virtualSink(node) {
  if (!sink(node) || !node.ready) return false;
  var name = node.name;
  if (name.indexOf("alsa_output.") === 0 || name.indexOf("bluez_output.") === 0) return false;
  if (name === "easyeffects_sink" || name.indexOf("effect_input.") === 0
      || name.indexOf("omarchy_speaker_tuning") === 0) return true;
  var flag = (node.properties || {})["node.virtual"];
  return flag === true || flag === "true" || flag === "1";
}

// Exact/preferred matches win over the original effect_input prefix fallback.
// Matching is routing presentation policy, never a security identity proof.
function sourceRank(name, sourceName) {
  if (typeof name !== "string" || !name || typeof sourceName !== "string") return 0;
  var output = name.replace(/^effect_input\./, "effect_output.");
  if (sourceName === output || (output === name && sourceName.indexOf(name) === 0)) return 2;
  if (name === "easyeffects_sink" && sourceName.indexOf("ee_") === 0) return 2;
  return sourceName.indexOf(name) === 0 ? 1 : 0;
}

// Only constant names are read before tracking; properties require ready nodes.
function sources(nodes, sinks) {
  return nodes.filter(function(node) {
    return !!node && sinks.some(function(output) {
      return virtualSink(output) && sourceRank(output.name, node.name) > 0;
    });
  });
}

function sameKey(a, b) {
  return !!a && !!b && a.scope === b.scope && a.id === b.id && a.name === b.name
    && a.serial === b.serial && a.generation === b.generation;
}

function currentNode(nodes, node) {
  if (nodes.indexOf(node) === -1) return false;
  return nodes.filter(function(other) { return other && other.id === node.id; }).length === 1;
}

function record(status, selected, target, steps) {
  return Object.freeze({status:status, selected:selected, target:target,
    proof:target ? JSON.stringify([selected, target, steps]) : ""});
}

function resolve(nodes, links, selected, authority) {
  if (!selected) return record("absent", null, null, []);
  if (!sink(selected) || !currentNode(nodes, selected)) return record("unready", null, null, []);
  var selectedKey = authority.capture(selected);
  if (!selectedKey) return record("unready", null, null, []);
  var current = selected, visited = [], steps = [];
  for (var depth = 0; depth < 8; ++depth) {
    var key = authority.capture(current);
    if (!key || !currentNode(nodes, current)) return record("unready", selectedKey, null, []);
    var identity = key.id + ":" + key.generation;
    if (visited.indexOf(identity) !== -1) return record("cycle", selectedKey, null, []);
    visited.push(identity);
    if (!virtualSink(current)) return record(steps.length ? "resolved" : "direct", selectedKey, key, steps);
    var matches = [], rank = 0;
    for (var i = 0; i < links.length; ++i) {
      var link = links[i];
      if (!link || !link.source || !sink(link.target)) continue;
      // The original EasyEffects 8 port branch admits only hardware outputs.
      if (current.name === "easyeffects_sink" && link.source.name.indexOf("ee_") === 0
          && link.target.name.indexOf("alsa_output.") !== 0 && link.target.name.indexOf("bluez_output.") !== 0) continue;
      var candidateRank = sourceRank(current.name, link.source.name);
      if (!candidateRank || candidateRank < rank) continue;
      if (candidateRank > rank) { matches = []; rank = candidateRank; }
      matches.push(link);
    }
    if (!matches.length) return record("unresolved", selectedKey, null, []);
    var target = null, edges = [];
    for (var j = 0; j < matches.length; ++j) {
      var edge = matches[j];
      if (!currentNode(nodes, edge.source) || !currentNode(nodes, edge.target)) return record("unready", selectedKey, null, []);
      var sourceKey = authority.capture(edge.source), targetKey = authority.capture(edge.target);
      if (!sourceKey || !targetKey) return record("unready", selectedKey, null, []);
      if (target && target !== edge.target) return record("ambiguous", selectedKey, null, []);
      target = edge.target;
      var proof = JSON.stringify([sourceKey, targetKey]);
      if (edges.indexOf(proof) === -1) edges.push(proof);
    }
    edges.sort();steps.push(edges);current = target;
  }
  return record("limit", selectedKey, null, []);
}

function target(nodes, links, selected, authority, captured) {
  if (!captured || Object.keys(captured).length !== 4 || typeof captured.proof !== "string" || !captured.proof) return null;
  var fresh = resolve(nodes, links, selected, authority);
  if (!fresh.target || fresh.status !== captured.status || fresh.proof !== captured.proof
      || !sameKey(fresh.selected, captured.selected) || !sameKey(fresh.target, captured.target)) return null;
  for (var i = 0; i < nodes.length; ++i) {
    var node = nodes[i];
    if (sink(node) && sameKey(authority.capture(node), fresh.target)) return node;
  }
  return null;
}
