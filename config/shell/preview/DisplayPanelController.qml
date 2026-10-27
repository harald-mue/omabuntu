import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

// Exactly one reviewed helper process, fixed verbs and argv (never a shell).
DesktopPanelController {
  id: root
  property var displays: []
  property int brightnessPercent: 0
  property bool brightnessAvailable: false
  property string focusedMonitor: ""
  property string monitorScale: "1"
  property string errorText: ""
  property string helper: Quickshell.env("OMABUNTU_DISPLAY_HELPER")
  property string focusSection: "brightness"
  property int selectedIndex: -1
  property real wheelAccumulator: 0
  readonly property bool reflowingText: false
  readonly property var scaleValues: ["1", "1.25", "1.5", "1.6", "2", "3", "4"]
  readonly property int enabledDisplayCount: displays.filter(function(d) { return d.enabled; }).length
  onOpenedChanged: if (opened) request("status", [])
  Component.onCompleted: request("status", [])
  function request(kind, args) {
    if (backend.running || !helper.endsWith("/display_backend.py") || helper.indexOf(" ") >= 0) return;
    if (["status", "brightness", "scale"].indexOf(kind) < 0) return;
    backend.exec(["python3", helper, kind].concat(args));
  }
  function setBrightness(value) { request("brightness", [String(Math.max(1, Math.min(100, Math.round(value))))]); }
  function previewBrightness(value) { brightnessPercent = Math.round(value); }
  function adjustBrightness(delta) { setBrightness(brightnessPercent + delta); }
  function showBrightnessOsd(percent) {} // OSD is outside this trial.
  function brightnessName(percent) { return Math.round(percent) + "%"; }
  function effectiveScale(value) { return Number(value); }
  function activeScaleIndex() { return scaleValues.indexOf(monitorScale); }
  function setScale(value) { request("scale", [focusedMonitor, String(value)]); }
  function toggleDisplay(name, enabled) {} // Read-only output inventory; no disabling.
  function moveCursor(delta) {
    cursorActive = true;
    focusSection = focusSection === "brightness" ? "scale" : "brightness";
    selectedIndex = focusSection === "scale" ? Math.max(0, activeScaleIndex()) : -1;
  }
  function moveCursorH(delta) { selectedIndex = Math.max(0, Math.min(scaleValues.length - 1, selectedIndex + delta)); }
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
      try {
        var data = JSON.parse(output.text);
        if (code !== 0 || data.error) { root.errorText = data.error || "Display action failed"; return; }
        root.errorText = "";
        root.displays = data.displays.map(function(d) { return { name: d.name, enabled: !d.disabled, focused: !!d.focused }; });
        for (var i = 0; i < data.displays.length; i++) if (data.displays[i].focused) {
          root.focusedMonitor = data.displays[i].name;
          root.monitorScale = String(data.displays[i].scale);
        }
        root.brightnessAvailable = !!data.backlight;
        if (data.backlight) root.brightnessPercent = data.backlight.percent;
      } catch (error) { root.errorText = "Display backend unavailable"; }
    }
  }
  Timer { interval: 2000; repeat: true; running: root.opened; onTriggered: root.request("status", []) }
}
