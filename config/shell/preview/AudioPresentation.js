.pragma library
.import "Port/AudioModel.js" as Model

// Display delegates receive primitives, never native node references.
function snapshot(ready, nodes, sink) {
  var rows = [];
  var current = null;
  for (var i = 0; ready && i < nodes.length; ++i) {
    var node = nodes[i];
    if (!node || !node.ready || !node.isSink || node.isStream || !node.audio) continue;
    var volume = Number(node.audio.volume);
    var row = Object.freeze({id:node.id, name:String(node.name || ""), label:Model.nodeLabel(node),
      glyph:Model.sinkGlyph(node), volume:isFinite(volume) ? volume : 0, muted:!!node.audio.muted,
      headphones:Model.isHeadphones(node)});
    rows.push(row);
    if (sink && node.id === sink.id && node.name === sink.name) current = row;
  }
  return Object.freeze({ready:!!ready, current:current, outputs:Object.freeze(rows)});
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
      glyph:Model.sourceGlyph(node), volume:isFinite(volume) ? volume : 0, muted:!!node.audio.muted});
    rows.push(row);
    if (source && node.id === source.id && node.name === source.name) current = row;
  }
  return Object.freeze({ready:!!ready, current:current, inputs:Object.freeze(rows)});
}

// Same output glyph ladder as Omarchy audio/Panel.qml:475-488. Playback
// status only; the hero switch stays output-only in this slice.
function icon(current) {
  if (!current) return "";
  if (current.headphones) return "󰋋";
  if (current.muted) return "";
  if (current.volume >= 0.67) return "";
  if (current.volume >= 0.34) return "";
  if (current.volume > 0) return "";
  return "";
}
