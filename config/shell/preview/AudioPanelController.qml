import QtQuick
import qs.Commons
import "AudioPresentation.js" as Presentation
import "AudioRouting.js" as Routing
import "Port/AudioModel.js" as Model

// Backend boundary for the source-derived Omarchy output/input/stream frontend.
// Native QObjects never escape the provider; no shell helpers or IPC here.
// Cursor model mirrors upstream Panel.qml: the virtual "header" hero, then
// sections with a slider row (-1) above device rows (0..N-1).
Item {
  id: root
  required property QtObject bar
  required property QtObject backend
  property var panelWindow: null
  property var profileControls: null
  property bool opened: false
  // The authored Advanced audio surface is disabled, not a user preference.
  readonly property bool advancedAudioAvailable: false
  property bool advancedAudio: false
  onAdvancedAudioChanged: {
    if (advancedAudio && !advancedAudioAvailable) { advancedAudio = false; return; }
    dragTarget = null; cancelInputDrag(); cursorActive = false;
    focusSection = advancedAudio ? "profiles" : "output";
    selectedIndex = advancedAudio ? 0 : -1;
    Qt.callLater(resetScroll);
  }
  property bool cursorActive: false
  property string focusSection: "output"
  property int selectedIndex: -1
  property string errorText: ""
  property var dragTarget: null
  property var dragSourceTarget: null
  property bool inputDragCancelledState: false
  property real wheelRemainder: 0
  readonly property var current: backend.state.current
  readonly property var sink: current
  readonly property var displayAudioSinks: opened ? backend.state.outputs : []
  readonly property var displayAudioStreams: opened ? backend.streamState.streams : []
  readonly property bool outputControlAvailable: !!current && current.controlAvailable !== false
  readonly property real outputVolume: current ? current.volume : 0
  readonly property bool outputMuted: !current || current.muted
  // Typed and separately proved untyped input observations.
  readonly property var source: backend.inputState.current
  readonly property var displayAudioSources: opened ? backend.inputState.inputs : []
  readonly property real inputVolume: source ? source.volume : 0
  readonly property bool inputMuted: !source || source.muted
  readonly property bool hasInput: !!source
  readonly property bool inputControlAvailable: hasInput && source.controlAvailable !== false
  readonly property bool inputWriteAvailable: inputControlAvailable && source.writeAvailable !== false
  readonly property bool inputUnavailable: !!backend.inputState.defaultPresent && !inputControlAvailable
  readonly property bool inputLevelKnown: inputControlAvailable
  readonly property bool inputLevelShown: !!source && source.untyped !== true
  readonly property real inputPeak: backend.peak
  // Original hero semantics: on while either channel remains unmuted.
  // The bar glyph and the separate output/input row actions stay channel-local.
  readonly property bool anyAudible: (!!current && !outputMuted) || (hasInput && !inputMuted)
  readonly property bool headerHasCursor: cursorActive && focusSection === "header"
  readonly property string toggleHint: current && !outputControlAvailable ? "Output route unavailable"
    : (inputUnavailable ? "Microphone controls unavailable"
    : (anyAudible ? "Mute output and microphone" : "Unmute output and microphone"))
  readonly property color hoverFill: Style.hoverFillFor(bar.foreground)
  readonly property color selectedFill: Style.selectedFillFor(bar.foreground)
  readonly property string currentKey: current ? current.id + ":" + current.name + ":" + current.serial
    + ":" + (current.control ? current.control.proof : "") : ""
  readonly property string icon: current && !outputControlAvailable ? "󰓃" : Presentation.icon(current)
  implicitWidth: 26
  implicitHeight: 26
  onCurrentKeyChanged: wheelRemainder = 0
  onDisplayAudioSinksChanged: clampCursor()
  onDisplayAudioSourcesChanged: clampCursor()
  onInputControlAvailableChanged: { clampCursor(); if (!inputControlAvailable) cancelInputDrag(); }
  onSourceChanged: if (dragSourceTarget && (!source || source.id !== dragSourceTarget.id
    || source.name !== dragSourceTarget.name || source.serial !== dragSourceTarget.serial
    || source.bridgeKey !== dragSourceTarget.bridgeKey
    || (source.control ? !Routing.sameKey(source.control, dragSourceTarget.control) : !!dragSourceTarget.control))) cancelInputDrag()
  onDisplayAudioStreamsChanged: clampCursor()
  onVisibleSectionsChanged: clampCursor()
  onOpenedChanged: {
    if (typeof backend.setMonitoring === "function") backend.setMonitoring(root, opened);
    else backend.monitoring = opened;
    if (opened) {
      errorText = "";
      cursorActive = false;
      focusSection = "output";
      selectedIndex = -1;
      Qt.callLater(resetScroll);
    } else {
      advancedAudio = false;
      dragTarget = null;
      cancelInputDrag();
    }
  }
  Component.onDestruction: if (typeof backend.setMonitoring === "function") backend.setMonitoring(root, false)
  function open() { opened = true; }
  function close() { opened = false; }
  function toggle() { opened = !opened; }
  function setVolume(key, value) {
    errorText = backend.setVolume(key, value) ? "" : "Output device or route changed; request refused or outcome uncertain";
  }
  function setOutputVolume(value) { setVolume(dragTarget || current, value); }
  function toggleMute() {
    errorText = backend.toggleMute(current) ? "" : "Output route unavailable or mute outcome uncertain";
  }
  function toggleOutputMute() { toggleMute(); }
  // Explicit original hero/right-click action; never called by opening/readback.
  function toggleAllMuted() {
    errorText = backend.toggleAllMuted(current, source) ? ""
      : "Audio state changed; check output and microphone mute";
  }
  function setDefaultSink(row) {
    errorText = backend.chooseOutput(row) ? "" : "Output selection unavailable or outcome uncertain";
  }
  signal inputDragCancelled()
  function cancelInputDrag() {
    if (dragSourceTarget) inputDragCancelledState = true;
    dragSourceTarget = null; inputDragCancelled();
  }
  function beginInputDrag() { inputDragCancelledState = false; dragSourceTarget = source; }
  function finishInputDrag(value) {
    if (inputDragCancelledState) { inputDragCancelledState = false; return; }
    var captured = dragSourceTarget;
    dragSourceTarget = null;
    if (captured && captured.untyped) errorText = backend.setSourceVolume(captured, value)
      ? "" : "Microphone changed, unavailable or gain outcome uncertain";
  }
  function setInputVolume(value) {
    if (inputDragCancelledState) { errorText = "Microphone gesture cancelled; start a new action"; return; }
    // The pulse-backed gesture issues once on release, never a replay/retarget
    // of asynchronous intermediate moves. Typed controls remain continuous.
    if (dragSourceTarget && dragSourceTarget.untyped) return;
    errorText = backend.setSourceVolume(dragSourceTarget || source, value) ? "" : "Microphone changed, unavailable or gain outcome uncertain";
  }
  function toggleInputMute() {
    errorText = backend.toggleSourceMute(source) ? "" : "Microphone unavailable or mute outcome uncertain";
  }
  function setDefaultSource(row) {
    errorText = backend.chooseInput(row) ? "" : "Input selection unavailable or outcome uncertain";
  }
  function setStreamVolume(row, value) {
    errorText = backend.setStreamVolume(row, value) ? "" : "Playback stream is no longer available";
  }
  function toggleStreamMute(row) {
    errorText = backend.toggleStreamMute(row) ? "" : "Playback stream is no longer available";
  }
  function streamLabel(row) { return row ? row.label : ""; }
  function outputIcon() { return icon; }
  function outputVolumeName(value, muted) {
    return current && !outputControlAvailable ? "Output route unavailable" : Model.outputVolumeName(value, muted, I18n.t);
  }
  function nodeLabel(row) { return row ? row.label : ""; }
  function sinkGlyph(row) { return row ? row.glyph : "󰓃"; }
  function sourceGlyph(row) { return row ? row.glyph : "󰍬"; }
  // Rows never retain native nodes. Inputs additionally require the captured
  // serial/provider/generation proof, so an old row cannot acquire a new node.
  function nodeFor(key) {
    if (!key) return null;
    var outputs = backend.state.outputs;
    for (var i = 0; i < outputs.length; i++)
      if (outputs[i].id === key.id && outputs[i].name === key.name) return outputs[i];
    var inputs = backend.inputState.inputs;
    for (var j = 0; j < inputs.length; j++)
      if (inputs[j].id === key.id && inputs[j].name === key.name && inputs[j].serial === key.serial
          && (key.control ? Routing.sameKey(inputs[j].control, key.control) : !inputs[j].control)) return inputs[j];
    var streams = backend.streamState.streams;
    for (var k = 0; k < streams.length; k++)
      if (streams[k].id === key.id && streams[k].name === key.name
          && streams[k].serial === key.serial) return streams[k];
    return null;
  }
  function wheel(delta) {
    if (!outputControlAvailable || !isFinite(delta)) return;
    wheelRemainder += delta;
    var steps = Math.trunc(wheelRemainder / 120);
    wheelRemainder -= steps * 120;
    if (steps !== 0) setVolume(current, current.volume + steps * 0.05);
  }
  // ---- Upstream cursor model (Panel.qml), including per-stream sliders ----
  function sectionCount(section) {
    if (section === "output") return displayAudioSinks.length;
    if (section === "input") return displayAudioSources.length;
    if (section === "streams") return displayAudioStreams.length;
    if (section === "profiles") return advancedAudioAvailable && profileControls ? profileControls.actions.length : 0;
    return 0;
  }
  function sectionVisible(section) {
    if (advancedAudio && section !== "profiles") return false;
    if (section === "output") return true;
    if (section === "input") return displayAudioSources.length > 0 || !!source;
    if (section === "streams") return displayAudioStreams.length > 0;
    if (section === "profiles") return advancedAudioAvailable && !!profileControls && profileControls.actions.length > 0;
    return false;
  }
  function sectionHasSlider(section) {
    if (section === "output") return true;
    if (section === "input") return inputControlAvailable;
    return false;
  }
  readonly property var visibleSections: {
    var list = [];
    if (sectionVisible("output")) list.push("output");
    if (sectionVisible("input")) list.push("input");
    if (sectionVisible("streams")) list.push("streams");
    if (sectionVisible("profiles")) list.push("profiles");
    return list;
  }
  function setHeaderCursor() { cursorActive = true; focusSection = advancedAudio ? "profiles" : "header"; if (advancedAudio) selectedIndex = 0; }
  function moveCursor(delta) {
    var sections = visibleSections;
    if (sections.length === 0) return;
    if (focusSection === "header") {
      if (delta > 0) { focusSection = sections[0]; selectedIndex = sectionHasSlider(sections[0]) ? -1 : 0; }
      return;
    }
    var sIdx = sections.indexOf(focusSection);
    if (sIdx < 0) { focusSection = sections[0]; selectedIndex = sectionHasSlider(focusSection) ? -1 : 0; return; }
    var idx = selectedIndex;
    var max = sectionCount(focusSection) - 1;
    var hasSlider = sectionHasSlider(focusSection);
    var floor = hasSlider ? -1 : 0;
    if (delta > 0) {
      if (idx < max) { selectedIndex = idx + 1; return; }
      if (sIdx < sections.length - 1) {
        focusSection = sections[sIdx + 1];
        selectedIndex = sectionHasSlider(focusSection) ? -1 : 0;
      }
    } else {
      if (idx > floor) { selectedIndex = idx - 1; return; }
      if (sIdx > 0) {
        focusSection = sections[sIdx - 1];
        var prevMax = sectionCount(focusSection) - 1;
        selectedIndex = prevMax >= 0 ? prevMax : (sectionHasSlider(focusSection) ? -1 : 0);
      } else if (!advancedAudio) {
        focusSection = "header";
      }
    }
  }
  function clampCursor() {
    var sections = visibleSections;
    if (!sections || !sections.length) return;
    // "header" is virtual and never appears in visibleSections: clamping it
    // would knock the cursor off the hero switch on every mute toggle.
    if (focusSection === "header") return;
    if (sections.indexOf(focusSection) < 0) {
      focusSection = sections[0];
      selectedIndex = sectionHasSlider(focusSection) ? -1 : 0;
      return;
    }
    var count = sectionCount(focusSection);
    var hasSlider = sectionHasSlider(focusSection);
    var floor = hasSlider ? -1 : 0;
    if (selectedIndex > count - 1) selectedIndex = Math.max(floor, count - 1);
    if (selectedIndex < floor) selectedIndex = floor;
  }
  // Device rows are no-ops for h/l; stream rows adjust only their own slider.
  function adjustVolume(delta) {
    if (advancedAudio) return;
    if (focusSection === "output" && selectedIndex === -1) setOutputVolume(outputVolume + delta);
    else if (focusSection === "input" && selectedIndex === -1) {
      inputDragCancelledState = false;
      setInputVolume(inputVolume + delta);
    }
    else if (focusSection === "streams" && selectedIndex >= 0) {
      var row = nodeFor(displayAudioStreams[selectedIndex]);
      if (row) setStreamVolume(row, row.volume + delta);
    }
  }
  function activateCursor() {
    if (advancedAudio && focusSection !== "profiles") return;
    if (focusSection === "profiles") {
      if (advancedAudioAvailable && profileControls) profileControls.activate(selectedIndex);
      return;
    }
    if (focusSection === "header") { toggleAllMuted(); return; }
    if (focusSection === "output") {
      if (selectedIndex === -1) { toggleOutputMute(); return; }
      setDefaultSink(nodeFor(displayAudioSinks[selectedIndex]));
      return;
    }
    if (focusSection === "input") {
      if (selectedIndex === -1) { toggleInputMute(); return; }
      setDefaultSource(nodeFor(displayAudioSources[selectedIndex]));
      return;
    }
    if (focusSection === "streams" && selectedIndex >= 0)
      toggleStreamMute(displayAudioStreams[selectedIndex]);
  }
  function switchPanel(direction) {
    return bar && typeof bar.switchPanelFrom === "function" ? bar.switchPanelFrom(root, direction) : false;
  }
  // Adapted from the original panel's scroll/cursor helpers.
  function resetScroll() {
    var area = panelWindow && panelWindow.loadedContent ? panelWindow.loadedContent.scrollArea : null;
    if (area && area.contentItem) area.contentItem.contentY = 0;
  }
  function ensureCursorVisible(item) {
    var area = panelWindow && panelWindow.loadedContent ? panelWindow.loadedContent.scrollArea : null;
    var flick = area ? area.contentItem : null;
    if (!item || !flick || flick.contentY === undefined) return;
    var maxY = Math.max(0, flick.contentHeight - flick.height);
    if (maxY <= 24 || (focusSection === "output" && selectedIndex === -1)) { flick.contentY = 0; return; }
    var point = item.mapToItem(flick.contentItem || flick, 0, 0);
    if (point.y < flick.contentY + 6) flick.contentY = Math.max(0, point.y - 6);
    else if (point.y + item.height > flick.contentY + flick.height - 6)
      flick.contentY = Math.min(maxY, point.y + item.height + 6 - flick.height);
  }
}
