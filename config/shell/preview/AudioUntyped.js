.pragma library
.import "AudioRouting.js" as Routing
.import "AudioActions.js" as Actions
.import "Port/AudioModel.js" as Model

// The running pulse bridge supplies levels; QML also proves native object
// generation. Neither node name nor recycled ID alone authorizes a setter.
function eligible(node) {
  return !!node && node.ready && node.isSink === false && node.isStream === false
    && !node.audio && node.name !== "quickshell";
}
function rowFor(node, bridge, authority) {
  if (!eligible(node) || !bridge || !bridge.known || !bridge.snapshot) return null;
  var serial = Actions.streamSerial(node);
  var matches = bridge.snapshot.sources.filter(function(row){return row.name===node.name && row.serial===serial;});
  var proof = authority.capture(node);
  if (matches.length!==1 || !proof) return null;
  var value = matches[0];
  return Object.freeze({id:node.id,name:node.name,serial:serial,label:Model.nodeLabel(node),glyph:Model.sourceGlyph(node),
    volume:value.volume,muted:value.muted,control:proof,controlAvailable:true,writeAvailable:!!bridge.writable,
    untyped:true,bridgeKey:bridge.snapshot.key});
}
function merge(base, ready, nodes, source, bridge, authority) {
  var rows = base.inputs.slice(), current=base.current;
  for(var i=0;ready && i<nodes.length;i++) {
    var node=nodes[i];
    if(!eligible(node) || !Routing.currentNode(nodes,node))continue;
    var row=rowFor(node,bridge,authority);
    if(!row)continue;
    rows.push(row);
    if(node===source && bridge.snapshot.default_source===node.name)current=row;
  }
  return Object.freeze({ready:base.ready,defaultPresent:!!source,current:current,inputs:Object.freeze(rows)});
}
function target(ready,nodes,source,bridge,authority,row,requireDefault) {
  if(!ready || !row || row.untyped!==true || row.controlAvailable!==true || !row.control || !bridge || !bridge.writable
      || row.bridgeKey!==bridge.snapshot.key)return null;
  for(var i=0;i<nodes.length;i++) {
    var node=nodes[i];
    if(!eligible(node) || !Routing.currentNode(nodes,node) || (requireDefault && node!==source))continue;
    if(requireDefault && bridge.snapshot.default_source!==node.name)continue;
    if(node.id===row.id && node.name===row.name && Actions.streamSerial(node)===row.serial
        && Routing.sameKey(authority.capture(node),row.control))return node;
  }
  return null;
}
