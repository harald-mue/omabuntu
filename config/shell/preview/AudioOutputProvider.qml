import QtQuick
import Quickshell.Services.Pipewire
import qs.Commons as Commons
import "AudioActions.js" as Actions
import "AudioPresentation.js" as Presentation
import "AudioRouting.js" as Routing
import "AudioInput.js" as Input
import "AudioUntyped.js" as Untyped

// Observe the existing server. Mutations occur only through explicit UI actions.
// Selected output and loudness target remain separate. Recognized DSP routes use
// native endpoint observations and fresh identity proofs, never helper execution.
// Typed capture stays native; the optional shared bridge admits untyped inputs
// using both native-generation and pulse-server observation proofs. No process
// dispatch in this provider, daemon restart or startup write. Peak monitoring
// uses typed inputs only while at least one panel is open.
QtObject {
  id: root
  property QtObject bridge: null
  property QtObject feedback: null
  property var monitoringOwners: []
  function setMonitoring(owner, value) {
    var next=monitoringOwners.filter(function(item){return item!==owner;});
    if(value)next.push(owner);
    monitoringOwners=next;monitoring=next.length>0;
  }
  onStateChanged: if(feedback)feedback.observe("output",state.current)
  onInputStateChanged: if(feedback)feedback.observe("input",inputState.current)
  onFeedbackChanged: if(feedback){feedback.observe("output",state.current);feedback.observe("input",inputState.current)}
  readonly property var candidates: {
    var values = Pipewire.nodes ? Pipewire.nodes.values : [];
    return values.filter(function(node) { return node && node.isSink && !node.isStream; });
  }
  // Track untyped candidates only when default or reported by the granted
  // bridge; projection still requires matching names, serials and generations.
  readonly property var sourceCandidates: {
    var values = Pipewire.nodes ? Pipewire.nodes.values : [];
    return values.filter(function(node) {
      return node && !node.isSink && !node.isStream && String(node.name || "") !== "quickshell"
        && (node.audio || node===Pipewire.defaultAudioSource || (root.bridge && root.bridge.known
          && root.bridge.snapshot.sources.some(function(row){return row.name===node.name;})));
    });
  }
  readonly property var streamCandidates: {
    var values = Pipewire.nodes ? Pipewire.nodes.values : [];
    return values.filter(Actions.playbackStream);
  }
  property PwObjectTracker outputTracker: PwObjectTracker { objects: root.candidates }
  property PwObjectTracker sourceTracker: PwObjectTracker { objects: root.sourceCandidates }
  property PwObjectTracker streamTracker: PwObjectTracker { objects: root.streamCandidates }
  // Set by the panel controller: the monitor runs only while the panel is open,
  // exactly like upstream's root.opened gate.
  property bool monitoring: false
  property PwNodePeakMonitor inputPeakMonitor: PwNodePeakMonitor {
    id: sourcePeak
    node: Pipewire.defaultAudioSource
    enabled: root.monitoring && !!Pipewire.defaultAudioSource && !!Pipewire.defaultAudioSource.audio
  }
  readonly property var routeAuthority: Routing.createAuthority()
  readonly property var routeLinks: Pipewire.linkGroups ? Pipewire.linkGroups.values : []
  readonly property var routeSources: Routing.sources(Pipewire.nodes ? Pipewire.nodes.values : [], candidates)
  property PwObjectTracker routeTracker: PwObjectTracker { objects: root.routeSources }
  readonly property var volumeRoute: Routing.resolve(Pipewire.nodes ? Pipewire.nodes.values : [],
    routeLinks, Pipewire.defaultAudioSink, routeAuthority)
  readonly property var state: Presentation.routedSnapshot(Pipewire.ready, candidates, Pipewire.defaultAudioSink, volumeRoute)
  readonly property var inputAuthority: Routing.createAuthority()
  readonly property var inputState: Untyped.merge(Input.snapshot(Pipewire.ready, Pipewire.nodes ? Pipewire.nodes.values : [],
    Pipewire.defaultAudioSource, inputAuthority), Pipewire.ready, Pipewire.nodes ? Pipewire.nodes.values : [],
    Pipewire.defaultAudioSource, bridge, inputAuthority)
  readonly property var streamState: Presentation.streamSnapshot(Pipewire.ready, streamCandidates, Commons.MediaSelection.state)
  readonly property real peak: sourcePeak.peak
  function setStreamVolume(key, value) { return Actions.setStreamVolume(streamCandidates, key, value); }
  function toggleStreamMute(key) { return Actions.toggleStreamMute(streamCandidates, key); }
  function volumeTarget(key) {
    if (!Pipewire.ready || !key || !Actions.masterDefaultMatches(key, Pipewire.defaultAudioSink)) return null;
    return Routing.target(Pipewire.nodes ? Pipewire.nodes.values : [], routeLinks,
      Pipewire.defaultAudioSink, routeAuthority, key.control);
  }
  function setVolume(key, value) {
    var target = volumeTarget(key);
    if (!target || typeof value !== "number" || !isFinite(value)) return false;
    try { return Actions.setVolume(candidates, routeAuthority.capture(target), value); }
    catch (error) { return false; } // Uncertain bridge request; never replay.
  }
  function toggleMute(key) {
    var target = volumeTarget(key);
    if (!target) return false;
    try { return Actions.toggleMute(candidates, routeAuthority.capture(target)); }
    catch (error) { return false; }
  }
  function toggleAllMuted(outputKey, inputKey) {
    if (!Pipewire.ready
        || !Actions.masterDefaultMatches(outputKey, Pipewire.defaultAudioSink)
        || !Actions.masterDefaultMatches(inputKey, Pipewire.defaultAudioSource)) return false;
    var target = outputKey ? volumeTarget(outputKey) : null;
    if (outputKey && !target) return false;
    var input = inputKey ? sourceTarget(inputKey, true) : null;
    if (inputKey && !input) return false;
    if (inputKey && inputKey.untyped) {
      if (!bridge || !bridge.writable) return false;
      // The bridge cannot prove asynchronous DSP graph ownership. Never send
      // a combined request to a stale physical target behind a virtual default.
      if (outputKey && target.name !== Pipewire.defaultAudioSink.name) return false;
      var muted = (!!outputKey && !outputKey.muted) || !inputKey.muted;
      if (!outputKey) return bridge.change("mute",{name:inputKey.name,serial:inputKey.serial},muted,inputKey.bridgeKey);
      return bridge.change("master",{name:inputKey.name,serial:inputKey.serial},muted,inputKey.bridgeKey,
        {name:target.name,serial:Actions.streamSerial(target),selected:Pipewire.defaultAudioSink.name});
    }
    return Actions.toggleAllMuted(target ? [target] : [], input ? [input] : [],
      target ? routeAuthority.capture(target) : null, inputKey);
  }
  function chooseOutput(key) {
    var node = Pipewire.ready ? Actions.masterTarget(candidates, key, false) : null;
    if (!node) return false;
    try { Pipewire.preferredDefaultAudioSink = node; return true; }
    catch (error) { return false; }
  }
  function sourceTarget(key, requireDefault) {
    if (key && key.untyped) return Untyped.target(Pipewire.ready, Pipewire.nodes ? Pipewire.nodes.values : [],
      Pipewire.defaultAudioSource, bridge, inputAuthority, key, requireDefault);
    return Input.target(Pipewire.ready, Pipewire.nodes ? Pipewire.nodes.values : [],
      Pipewire.defaultAudioSource, inputAuthority, key, requireDefault);
  }
  function setSourceVolume(key, value) {
    var node = sourceTarget(key, true);
    if (!node) return false;
    if (key.untyped) {
      if (typeof value !== "number" || !isFinite(value)) return false;
      return bridge.change("volume",{name:key.name,serial:key.serial},Math.max(0,Math.min(1,value)),key.bridgeKey);
    }
    try { return Actions.setSourceVolume([node], key, value); }
    catch (error) { return false; } // Uncertain bridge request; never replay.
  }
  function toggleSourceMute(key) {
    var node = sourceTarget(key, true);
    if (!node) return false;
    if (key.untyped) return bridge.change("mute",{name:key.name,serial:key.serial},!key.muted,key.bridgeKey);
    try { return Actions.toggleSourceMute([node], key); }
    catch (error) { return false; }
  }
  function chooseInput(key) {
    var node = sourceTarget(key, false);
    if (!node) return false;
    try { Pipewire.preferredDefaultAudioSource = node; return true; }
    catch (error) { return false; }
  }
}
