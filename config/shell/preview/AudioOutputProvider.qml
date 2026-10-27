import QtQuick
import Quickshell.Services.Pipewire
import "AudioActions.js" as Actions
import "AudioPresentation.js" as Presentation

// Observe the existing server. Mutations occur only through explicit UI actions.
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
  PwObjectTracker { objects: root.candidates }
  PwObjectTracker { objects: root.sourceCandidates }
  // Set by the panel controller: the monitor runs only while the panel is open,
  // exactly like upstream's root.opened gate.
  property bool monitoring: false
  PwNodePeakMonitor {
    id: sourcePeak
    node: Pipewire.defaultAudioSource
    enabled: root.monitoring && !!Pipewire.defaultAudioSource
  }
  readonly property var state: Presentation.snapshot(Pipewire.ready, candidates, Pipewire.defaultAudioSink)
  readonly property var inputState: Presentation.inputSnapshot(Pipewire.ready, sourceCandidates, Pipewire.defaultAudioSource)
  readonly property real peak: sourcePeak.peak
  function setVolume(key, value) { return Actions.setVolume(candidates, key, value); }
  function toggleMute(key) { return Actions.toggleMute(candidates, key); }
  function chooseOutput(key) {
    var node = Actions.resolve(candidates, key);
    if (!node) return false;
    Pipewire.preferredDefaultAudioSink = node;
    return true;
  }
  function setSourceVolume(key, value) { return Actions.setSourceVolume(sourceCandidates, key, value); }
  function toggleSourceMute(key) { return Actions.toggleSourceMute(sourceCandidates, key); }
  function chooseInput(key) {
    var node = Actions.resolveSource(sourceCandidates, key);
    if (!node) return false;
    Pipewire.preferredDefaultAudioSource = node;
    return true;
  }
}
