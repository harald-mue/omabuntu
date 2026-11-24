.pragma library
.import "Port/AudioModel.js" as Model
.import "AudioActions.js" as Actions

// Display delegates receive primitives, never native node references.
function snapshot(ready, nodes, sink) {
  var rows = [];
  var current = null;
  for (var i = 0; ready && i < nodes.length; ++i) {
    var node = nodes[i];
    if (!node || !node.ready || !node.isSink || node.isStream || !node.audio) continue;
    var volume = Number(node.audio.volume);
    var row = Object.freeze({id:node.id, name:String(node.name || ""), label:Model.nodeLabel(node),
      glyph:Model.sinkGlyph(node), serial:Actions.streamSerial(node),
      volume:isFinite(volume) ? volume : 0, muted:!!node.audio.muted,
      headphones:Model.isHeadphones(node)});
    rows.push(row);
    if (sink && node.id === sink.id && node.name === sink.name) current = row;
  }
  return Object.freeze({ready:!!ready, current:current, outputs:Object.freeze(rows)});
}

// Keep default selection/rows separate from the resolved loudness target.
// The control record is immutable primitive data, never a native node.
function routedSnapshot(ready, nodes, sink, control) {
  var base = snapshot(ready, nodes, sink);
  if (!base.current) return base;
  var selected = base.current, target = null;
  if (control && control.selected && control.target
      && selected.id === control.selected.id && selected.name === control.selected.name
      && selected.serial === control.selected.serial) {
    for (var i = 0; i < base.outputs.length; ++i) {
      var row = base.outputs[i];
      if (row.id === control.target.id && row.name === control.target.name
          && row.serial === control.target.serial) target = row;
    }
  }
  var current = Object.freeze(Object.assign({}, selected, {
    volume:target ? target.volume : 0, muted:target ? target.muted : true,
    headphones:target ? target.headphones : selected.headphones,
    controlAvailable:!!target, control:control
  }));
  return Object.freeze({ready:base.ready, current:current, outputs:base.outputs});
}

// Input rows for the "input" section: typed capture devices only, with
// the upstream source glyph. Untyped virtual sources stay excluded.
function inputSnapshot(ready, nodes, source) {
  var rows = [];
  var current = null;
  for (var i = 0; ready && i < nodes.length; ++i) {
    var node = nodes[i];
    if (!node || !node.ready || node.isSink || node.isStream || !node.audio) continue;
    if (String(node.name || "") === "quickshell") continue;
    var volume = Number(node.audio.volume);
    var row = Object.freeze({id:node.id, name:String(node.name || ""), label:Model.nodeLabel(node),
      glyph:Model.sourceGlyph(node), serial:Actions.streamSerial(node),
      volume:isFinite(volume) ? volume : 0, muted:!!node.audio.muted});
    rows.push(row);
    if (source && node.id === source.id && node.name === source.name) current = row;
  }
  return Object.freeze({ready:!!ready, current:current, inputs:Object.freeze(rows)});
}

// Keep descriptors bounded and literal; never interpret browser/meeting metadata.
function streamDescriptor(node, label) {
  var p = node.properties || {};
  var values = [p["media.name"], node.description, p["media.role"]];
  for (var i = 0; i < values.length; ++i) {
    var value = values[i];
    if (typeof value !== "string" || value.length > 512
        || /[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]/.test(value)) continue;
    value = value.trim().replace(/\s+/g, " ");
    if (value && value.toLowerCase() !== label.trim().toLowerCase()) return value.slice(0, 96);
  }
  return "";
}

// Read bound streams only; unbound properties must never be dereferenced.
// No native object or arbitrary property dictionary reaches a visual delegate.
function streamSnapshot(ready, nodes, media) {
  var players = media && Array.isArray(media.players) ? media.players : [];
  var active = media ? media.active : null;
  var eligible = [];
  for (var i = 0; ready && i < nodes.length; ++i) {
    var node = nodes[i];
    if (Actions.playbackStream(node) && node.ready && Actions.streamSerial(node)
        && Number.isInteger(node.id) && typeof node.name === "string" && node.name) eligible.push(node);
  }
  var labels = eligible.map(function(node) { return String(Model.streamLabel(node, players, eligible) || "Stream"); });
  var counts = Object.create(null);
  labels.forEach(function(label) { var key = label.trim().toLowerCase(); counts[key] = (counts[key] || 0) + 1; });
  var rows = eligible.map(function(node, index) {
    var label = labels[index];
    if (counts[label.trim().toLowerCase()] > 1) {
      var detail = streamDescriptor(node, label);
      // A current server-local stream ID, NOT a person or meeting participant.
      label += " · Stream #" + Actions.streamSerial(node) + (detail ? " · " + detail : "");
    }
    var volume = Number(node.audio.volume);
    return Object.freeze({id:node.id, name:node.name, serial:Actions.streamSerial(node),
      label:label,
      active:!!Model.streamRepresentsPlayer(node, active, players, eligible),
      volume:isFinite(volume) ? volume : 0, muted:!!node.audio.muted});
  });
  return Object.freeze({ready:!!ready, streams:Object.freeze(rows)});
}

// Same output glyph ladder as Omarchy audio/Panel.qml:475-488. Playback
// status only; master output/microphone audibility is tracked by the controller.
function icon(current) {
  if (!current) return "";
  if (current.headphones) return "󰋋";
  if (current.muted) return "";
  if (current.volume >= 0.67) return "";
  if (current.volume >= 0.34) return "";
  if (current.volume > 0) return "";
  return "";
}
