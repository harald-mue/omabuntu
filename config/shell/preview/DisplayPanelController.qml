import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

// Exactly one reviewed helper process, fixed verbs and argv (never a shell).
DesktopPanelController {
  id: root
  property var displays: []
  property var profiles: null
  property bool profilePage: false
  readonly property var textSizeStops: [9,10,11,12,14,16,20]
  function currentTextIndex() { return textSizeStops.indexOf(Style.font.baseSize) }
  function displayedTextPx() { return Style.font.baseSize }
  function setTextSize(value) { if(profiles&&!profiles.busy&&!profiles.data.pending)profiles.textSize(value) }
  function adjustTextSize(delta) { setTextSize(textSizeStops[Math.max(0,Math.min(textSizeStops.length-1,currentTextIndex()+delta))]) }
  property int brightnessPercent: 0
  property bool brightnessAvailable: false
  property string focusedMonitor: ""
  property string monitorScale: "1"
  property string errorText: ""
  property string helper: Quickshell.env("OMABUNTU_DISPLAY_HELPER")
  property string focusSection: "brightness"
  property int selectedIndex: -1
  property real wheelAccumulator: 0
  property var queue: []
  property var inFlight: []
  property var lastState: null
  property bool finishing: false
  readonly property bool reflowingText: false
  readonly property var scaleValues: ["1", "1.25", "1.5", "1.6", "2", "3", "4"]
  readonly property int enabledDisplayCount: displays.filter(function(d) { return d.enabled; }).length
  onOpenedChanged: { profilePage=false;if (opened) request("status", []) }
  Component.onCompleted: request("status", [])
  Connections {
    target: root.profiles
    function onBusyChanged() { if(root.profiles.busy)root.queue=root.queue.filter(function(item){return item[0]!=="scale"}) }
    function onDataChanged() { if(root.profiles.data.pending)root.queue=root.queue.filter(function(item){return item[0]!=="scale"}) }
  }
  function request(kind, args) {
    if (!helper.endsWith("/display_backend.py") || helper.indexOf(" ") >= 0) { errorText = "Display helper is unavailable"; return; }
    if (["status", "brightness", "scale"].indexOf(kind) < 0) return;
    if(kind==="scale"&&profiles&&(profiles.busy||profiles.data.pending)) {errorText="A monitor profile transaction is pending";return}
    var item = [kind].concat(args)
    var remaining = queue.filter(function(old) {
      return old[0] !== kind || (kind === "scale" && old[1] !== item[1])
    })
    if (kind === "status") queue = remaining.concat([item])
    else queue = remaining.filter(function(old) { return old[0] !== "status" }).concat([item], remaining.filter(function(old) { return old[0] === "status" }))
    pump()
  }
  function pump() {
    if (backend.running || finishing || !queue.length) return
    inFlight = queue[0]
    queue = queue.slice(1)
    backend.exec(["python3", helper].concat(inFlight))
  }
  function applyState(data) {
    displays = data.displays.map(function(d) { return { name: d.name, enabled: !d.disabled, focused: !!d.focused }; })
    for (var i = 0; i < data.displays.length; i++) if (data.displays[i].focused) {
      focusedMonitor = data.displays[i].name
      monitorScale = String(data.displays[i].scale)
    }
    brightnessAvailable = !!data.backlight
    if (data.backlight) brightnessPercent = data.backlight.percent
    var pending = [inFlight].concat(queue)
    for (var j = 0; j < pending.length; j++) {
      var args = pending[j]
      if (args[0] === "brightness") brightnessPercent = Number(args[1])
      else if (args[0] === "scale" && args[1] === focusedMonitor) monitorScale = args[2]
    }
  }
  function setBrightness(value) {
    brightnessPercent = Math.max(1, Math.min(100, Math.round(value)))
    request("brightness", [String(brightnessPercent)])
  }
  function previewBrightness(value) { brightnessPercent = Math.round(value); }
  function adjustBrightness(delta) { setBrightness(brightnessPercent + delta); }
  function showBrightnessOsd(percent) {} // OSD is outside this trial.
  function brightnessName(percent) { return Math.round(percent) + "%"; }
  function effectiveScale(value) { return Number(value); }
  function activeScaleIndex() { return scaleValues.indexOf(monitorScale); }
  function setScale(value) { if(profiles&&(profiles.busy||profiles.data.pending))return;monitorScale = String(value); request("scale", [focusedMonitor, String(value)]); }
  function toggleDisplay(name, enabled) { profilePage=true;if(profiles)profiles.refresh() } // Enable/disable requires the reviewed profile transaction.
  // Cursor/section logic derived from the pinned Omarchy monitor/Panel.qml (MIT).
  readonly property var visibleSections: {
    var list = []
    if (brightnessAvailable) list.push("brightness")
    if(profiles)list.push("textsize")
    list.push("scale")
    if (displays.length > 1) list.push("monitors")
    return list
  }

  function sectionCount(section) {
    if (section === "brightness") return 0  // only the slider sentinel at -1
    if (section === "textsize") return 0    // slider sentinel at -1, like brightness
    if (section === "scale") return scaleValues.length
    if (section === "monitors") return displays.length
    return 0
  }

  function sectionIsSingleRow(section) {
    // brightness and text size are lone sliders; scale presets sit horizontally.
    return section === "brightness" || section === "textsize" || section === "scale"
  }

  function sectionFirstIndex(section) {
    if (section === "brightness" || section === "textsize") return -1
    return 0
  }

  function moveCursor(delta) {
    var sections = visibleSections
    if (!sections || sections.length === 0) return
    var sIdx = sections.indexOf(focusSection)
    if (sIdx < 0) {
      focusSection = sections[0]
      selectedIndex = sectionFirstIndex(focusSection)
      return
    }
    var inSingleRow = sectionIsSingleRow(focusSection)
    var max = inSingleRow ? 0 : sectionCount(focusSection) - 1

    if (delta > 0) {
      if (!inSingleRow && selectedIndex < max) { selectedIndex = selectedIndex + 1; return }
      if (sIdx < sections.length - 1) {
        focusSection = sections[sIdx + 1]
        selectedIndex = sectionFirstIndex(focusSection)
      }
    } else {
      if (!inSingleRow && selectedIndex > 0) { selectedIndex = selectedIndex - 1; return }
      if (sIdx > 0) {
        var prev = sections[sIdx - 1]
        focusSection = prev
        // Coming up from below — land on the last navigable row of the prev
        // section, or its sentinel for single-row sections.
        selectedIndex = sectionIsSingleRow(prev) ? sectionFirstIndex(prev) : sectionCount(prev) - 1
      }
    }
  }

  // h/l: in scale section, walks the preset row; everywhere else, no-op
  // because adjustBrightness handles horizontal motion on the brightness
  // slider.
  function moveCursorH(delta) {
    if (focusSection !== "scale") return
    var next = selectedIndex + delta
    if (next < 0) next = 0
    if (next > scaleValues.length - 1) next = scaleValues.length - 1
    selectedIndex = next
  }

  function activateCursor() { if (focusSection === "scale") setScale(scaleValues[selectedIndex]); }
  function wheel(delta) {
    wheelAccumulator += delta;
    var steps = Math.trunc(wheelAccumulator / 120);
    wheelAccumulator -= steps * 120;
    if (steps && brightnessAvailable) adjustBrightness(steps * 5);
  }
  Process {
    id: backend
    stdout: StdioCollector { id: output }
    onExited: function(code) {
      root.finishing = true
      root.inFlight = []
      try {
        var data = JSON.parse(output.text)
        if (code !== 0 || data.error) {
          root.errorText = data.error || "Display action failed"
          if (root.lastState) root.applyState(root.lastState)
        } else {
          root.applyState(data)
          root.lastState = data
          root.errorText = ""
        }
      } catch (error) {
        root.errorText = "Display backend unavailable"
        if (root.lastState) root.applyState(root.lastState)
      }
      root.finishing = false
      Qt.callLater(root.pump)
    }
  }
  Timer { interval: 2000; repeat: true; running: root.opened; onTriggered: root.request("status", []) }
}
