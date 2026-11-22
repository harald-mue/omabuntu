import QtQuick
import Quickshell.Services.Pipewire
import qs.Commons as Commons
import "AudioActions.js" as Actions
import "AudioPresentation.js" as Presentation
import "AudioRouting.js" as Routing
import "AudioInput.js" as Input

// Observe the existing server. Mutations occur only through explicit UI actions.
// Selected output and loudness target remain separate. Recognized DSP routes use
// native endpoint observations and fresh identity proofs, never helper execution.
// Typed capture devices are readable/writable like sinks; untyped virtual
// sources stay excluded (upstream routes them through a separate process
// wrapper). No helper, daemon restart or startup write. The peak monitor is
// the native Quickshell PwNodePeakMonitor on the default source, enabled only
// while the panel opens.
Item {
  id: root
  readonly property var candidates: {
    var values = Pipewire.nodes ? Pipewire.nodes.values : [];
    return values.filter(function(node) { return node && node.isSink && !node.isStream; });
  }
  // Upstream candidateSources skips sinks, streams, the shell's own node and
  // anything without typed audio; untyped virtual sources are not offered.
  readonly property var sourceCandidates: {
    var values = Pipewire.nodes ? Pipewire.nodes.values : [];
    return values.filter(function(node) {
      return node && !node.isSink && !node.isStream && node.audio
        && String(node.name || "") !== "quickshell";
    });
  }
  readonly property var streamCandidates: {
    var values = Pipewire.nodes ? Pipewire.nodes.values : [];
    return values.filter(Actions.playbackStream);
  }
  PwObjectTracker { objects: root.candidates }
  PwObjectTracker { objects: root.sourceCandidates }
  PwObjectTracker { objects: root.streamCandidates }
  // Set by the panel controller: the monitor runs only while the panel is open,
  // exactly like upstream's root.opened gate.
  property bool monitoring: false
  PwNodePeakMonitor {
    id: sourcePeak
    node: Pipewire.defaultAudioSource
    enabled: root.monitoring && !!Pipewire.defaultAudioSource
  }
  readonly property var routeAuthority: Routing.createAuthority()
  readonly property var routeLinks: Pipewire.linkGroups ? Pipewire.linkGroups.values : []
  readonly property var routeSources: Routing.sources(Pipewire.nodes ? Pipewire.nodes.values : [], candidates)
  PwObjectTracker { objects: root.routeSources }
  readonly property var volumeRoute: Routing.resolve(Pipewire.nodes ? Pipewire.nodes.values : [],
    routeLinks, Pipewire.defaultAudioSink, routeAuthority)
  readonly property var state: Presentation.routedSnapshot(Pipewire.ready, candidates, Pipewire.defaultAudioSink, volumeRoute)
  readonly property var inputAuthority: Routing.createAuthority()
  readonly property var inputState: Input.snapshot(Pipewire.ready, Pipewire.nodes ? Pipewire.nodes.values : [],
    Pipewire.defaultAudioSource, inputAuthority)
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
    catch (error) { return false; } // Uncertain native request; never replay.
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
    return Input.target(Pipewire.ready, Pipewire.nodes ? Pipewire.nodes.values : [],
      Pipewire.defaultAudioSource, inputAuthority, key, requireDefault);
  }
  function setSourceVolume(key, value) {
    var node = sourceTarget(key, true);
    if (!node) return false;
    try { return Actions.setSourceVolume([node], key, value); }
    catch (error) { return false; } // Uncertain native request; never replay.
  }
  function toggleSourceMute(key) {
    var node = sourceTarget(key, true);
    if (!node) return false;
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
