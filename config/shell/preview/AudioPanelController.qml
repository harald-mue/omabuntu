import QtQuick
import qs.Commons
import "AudioPresentation.js" as Presentation
import "Port/AudioModel.js" as Model

// Backend boundary for the source-derived Omarchy output+input frontend.
// Native QObjects never escape the provider; no shell helpers or IPC here.
// Cursor model mirrors upstream Panel.qml: the virtual "header" hero, then
// sections with a slider row (-1) above device rows (0..N-1).
Item {
  id: root
  required property QtObject bar
  required property QtObject backend
  property var panelWindow: null
  property bool opened: false
  property bool cursorActive: false
  property string focusSection: "output"
  property int selectedIndex: -1
  property string errorText: ""
  property var dragTarget: null
  property var dragSourceTarget: null
  property real wheelRemainder: 0
  readonly property var current: backend.state.current
  readonly property var sink: current
  readonly property var displayAudioSinks: opened ? backend.state.outputs : []
  readonly property real outputVolume: current ? current.volume : 0
  readonly property bool outputMuted: !current || current.muted
  // Input section state; typed sources only.
  readonly property var source: backend.inputState.current
  readonly property var displayAudioSources: opened ? backend.inputState.inputs : []
  readonly property real inputVolume: source ? source.volume : 0
  readonly property bool inputMuted: !source || source.muted
  readonly property bool hasInput: !!source
  readonly property bool inputLevelKnown: hasInput
  readonly property bool inputLevelShown: !!source
  readonly property real inputPeak: backend.peak
  // The hero stays OUTPUT ONLY in this stage (documented deviation from
  // upstream's two-channel master mute).
  readonly property bool anyAudible: !!current && !outputMuted
  readonly property bool headerHasCursor: cursorActive && focusSection === "header"
  readonly property string toggleHint: I18n.t(anyAudible ? "audio.mute" : "audio.unmute")
  readonly property color hoverFill: Style.hoverFillFor(bar.foreground)
  readonly property color selectedFill: Style.selectedFillFor(bar.foreground)
  readonly property string currentKey: current ? current.id + ":" + current.name : ""
  readonly property string icon: Presentation.icon(current)
  implicitWidth: 26
  implicitHeight: 26
  onCurrentKeyChanged: wheelRemainder = 0
  onDisplayAudioSinksChanged: clampCursor()
  onDisplayAudioSourcesChanged: clampCursor()
  onOpenedChanged: {
    backend.monitoring = opened;
    if (opened) {
      errorText = "";
      cursorActive = false;
      focusSection = "output";
      selectedIndex = -1;
      Qt.callLater(resetScroll);
    } else {
      dragTarget = null;
      dragSourceTarget = null;
    }
  }
  function close() { opened = false; }
  function toggle() { opened = !opened; }
  function setVolume(key, value) {
    errorText = backend.setVolume(key, value) ? "" : "Output device is no longer available";
  }
  function setOutputVolume(value) { setVolume(dragTarget || current, value); }
  function toggleMute() {
    errorText = backend.toggleMute(current) ? "" : "No audio output available";
  }
  function toggleOutputMute() { toggleMute(); }
  // Original header/right-click action is deliberately OUTPUT ONLY here.
  function toggleAllMuted() { toggleMute(); }
  function setDefaultSink(row) {
    errorText = backend.chooseOutput(row) ? "" : "Output device is no longer available";
  }
  function setInputVolume(value) {
    errorText = backend.setSourceVolume(dragSourceTarget || source, value) ? "" : "Input device is no longer available";
  }
  function toggleInputMute() {
    errorText = backend.toggleSourceMute(source) ? "" : "No audio input available";
  }
  function setDefaultSource(row) {
    errorText = backend.chooseInput(row) ? "" : "Input device is no longer available";
  }
  function outputIcon() { return icon; }
  function outputVolumeName(value, muted) { return Model.outputVolumeName(value, muted, I18n.t); }
  function nodeLabel(row) { return row ? row.label : ""; }
  function sinkGlyph(row) { return row ? row.glyph : "󰓃"; }
  function sourceGlyph(row) { return row ? row.glyph : "󰍬"; }
  // A row resolves through either list; PipeWire may reuse ids, so both
  // id and name must match. Rows never dangle; a vanished node returns null.
  function nodeFor(key) {
    if (!key) return null;
    var outputs = backend.state.outputs;
    for (var i = 0; i < outputs.length; i++)
      if (outputs[i].id === key.id && outputs[i].name === key.name) return outputs[i];
    var inputs = backend.inputState.inputs;
    for (var j = 0; j < inputs.length; j++)
      if (inputs[j].id === key.id && inputs[j].name === key.name) return inputs[j];
    return null;
  }
  function wheel(delta) {
    if (!current || !isFinite(delta)) return;
    wheelRemainder += delta;
    var steps = Math.trunc(wheelRemainder / 120);
    wheelRemainder -= steps * 120;
    if (steps !== 0) setVolume(current, current.volume + steps * 0.05);
  }
  // ---- Upstream cursor model (Panel.qml), streams excluded ----
  function sectionCount(section) {
    if (section === "output") return displayAudioSinks.length;
    if (section === "input") return displayAudioSources.length;
    return 0;
  }
  function sectionVisible(section) {
    if (section === "output") return true;
    if (section === "input") return displayAudioSources.length > 0 || !!source;
    return false;
  }
  function sectionHasSlider(section) {
    if (section === "output") return true;
    if (section === "input") return !!source;
    return false;
  }
  readonly property var visibleSections: {
    var list = [];
    if (sectionVisible("output")) list.push("output");
    if (sectionVisible("input")) list.push("input");
    return list;
  }
  function setHeaderCursor() { cursorActive = true; focusSection = "header"; }
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
      } else {
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
  // Device rows (selectedIndex >= 0) are no-ops for h/l, exactly upstream.
  function adjustVolume(delta) {
    if (focusSection === "output" && selectedIndex === -1) setOutputVolume(outputVolume + delta);
    else if (focusSection === "input" && selectedIndex === -1) setInputVolume(inputVolume + delta);
  }
  function activateCursor() {
    if (focusSection === "header") { toggleAllMuted(); return; }
    if (focusSection === "output") {
      if (selectedIndex === -1) { toggleOutputMute(); return; }
      setDefaultSink(nodeFor(displayAudioSinks[selectedIndex]));
      return;
    }
    if (focusSection === "input") {
      if (selectedIndex === -1) { toggleInputMute(); return; }
      setDefaultSource(nodeFor(displayAudioSources[selectedIndex]));
    }
  }
  // Cross-panel registry switching is not present; Tab stays within this panel.
  function switchPanel(direction) {
    cursorActive = true;
    focusSection = focusSection === "header" ? "output" : "header";
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
