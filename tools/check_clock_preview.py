#!/usr/bin/env python3
"""Plan or run sealed clock/bar preview checks. Never connects to a host session."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import zlib

import audit_widgets
import audio_frontend
import keyboard_frontend
import check_runtime
import tooltip_port
import bar_frame
import network_frontend
import workspace_modes
import desktop_frontends
import clock_frontend

builder = check_runtime.builder
ROOT = Path(__file__).resolve().parents[1]
COMMIT = "03ff1eff3812933f7088484533784d2f63eaf19a"
UPSTREAM = {
    "Ui/BarWidget.qml": "shell/Ui/BarWidget.qml",
    "Ui/WidgetButton.qml": "shell/Ui/WidgetButton.qml",
    "Ui/OpticalGlyph.qml": "shell/Ui/OpticalGlyph.qml",
    "Spacer.qml": "shell/plugins/bar/widgets/Spacer.qml",
    "ClockLabel.qml": "shell/plugins/panels/clock/BarWidget.qml",
    "Model.js": "shell/plugins/panels/clock/Model.js",
    "CalendarPanel.qml": "shell/plugins/panels/clock/Panel.qml",
    "ClockControlView.qml": "shell/plugins/panels/clock/BarWidget.qml",
    "Port/Tray.qml": "shell/plugins/bar/widgets/Tray.qml",
    "Port/TrayModel.js": "shell/plugins/bar/widgets/TrayModel.js",
    "Port/NetworkModel.js": "shell/plugins/panels/network/Model.js",
    "Port/AudioModel.js": "shell/plugins/panels/audio/Model.js",
    "Ui/PanelSlider.qml": "shell/Ui/PanelSlider.qml",
    "AudioOutputView.qml": "shell/plugins/panels/audio/Panel.qml",
    "BarTooltip.qml": "shell/plugins/bar/Bar.qml",
    "BarFrame.qml": "shell/plugins/bar/Bar.qml",
    "BarTooltipHost.qml": "shell/plugins/bar/Bar.qml",
    "Ui/KeyboardPanel.qml": "shell/Ui/KeyboardPanel.qml",
    "Ui/PanelKeyCatcher.qml": "shell/Ui/PanelKeyCatcher.qml",
    "Ui/CursorSurface.qml": "shell/Ui/CursorSurface.qml",
    "Ui/ToggleSwitch.qml": "shell/Ui/ToggleSwitch.qml",
    "Ui/PanelToolTip.qml": "shell/Ui/PanelToolTip.qml",
    "Ui/PanelSeparator.qml": "shell/Ui/PanelSeparator.qml",
    "Ui/PanelSectionHeader.qml": "shell/Ui/PanelSectionHeader.qml",
    "Ui/PopupCard.qml": "shell/Ui/PopupCard.qml",
    "Ui/BarIconButton.qml": "shell/Ui/BarIconButton.qml",
    "Ui/BarIconContent.qml": "shell/Ui/BarIconContent.qml",
    "Ui/IconContentBounds.qml": "shell/Ui/IconContentBounds.qml",
    "Ui/Button.qml": "shell/Ui/Button.qml",
    "Ui/BorderSurface.qml": "shell/Ui/BorderSurface.qml",
    "Ui/BorderOverlay.qml": "shell/Ui/BorderOverlay.qml",
    "Commons/Border.qml": "shell/Commons/Border.qml",
    "Commons/BorderGeometry.js": "shell/Commons/BorderGeometry.js",
    "Ui/PanelActionButton.qml": "shell/Ui/PanelActionButton.qml",
    "Ui/TextField.qml": "shell/Ui/TextField.qml",
    "NetworkControlView.qml": "shell/plugins/panels/network/Panel.qml",
    "WorkspaceSwitcher.qml": "shell/plugins/bar/widgets/Workspaces.qml",
    "KeyboardLayout.qml": "shell/plugins/bar/widgets/KeyboardLayout.qml",
    "KeyboardLayoutModel.js": "shell/plugins/bar/widgets/KeyboardLayoutModel.js",
    "Commons/Util.qml": "shell/Commons/Util.qml",
    "Commons/InputDevices.qml": "shell/Commons/InputDevices.qml",
}
DESKTOP_UPSTREAM = {
    "BluetoothControlView.qml": "shell/plugins/panels/bluetooth/Panel.qml",
    "BluetoothPanelController.qml": "shell/plugins/panels/bluetooth/Panel.qml",
    "DisplayControlView.qml": "shell/plugins/panels/monitor/Panel.qml",
    "PowerControlView.qml": "shell/plugins/panels/power/Panel.qml",
    "DockWindow.qml": "shell/plugins/dock/DockWindow.qml",
    "Port/BluetoothModel.js": "shell/plugins/panels/bluetooth/Model.js",
    "Port/DisplayModel.js": "shell/plugins/panels/monitor/Model.js",
    "Port/PowerModel.js": "shell/plugins/panels/power/Model.js",
    "Port/DockModel.js": "shell/plugins/dock/DockModel.js",
}
DESKTOP_TRANSFORMS = {
    "BluetoothControlView.qml": ("bluetooth-surface-v1", desktop_frontends.bluetooth),
    "BluetoothPanelController.qml": ("bluetooth-cursor-v1", desktop_frontends.bluetooth_controller),
    "DisplayControlView.qml": ("display-surface-v1", desktop_frontends.display),
    "PowerControlView.qml": ("power-surface-v1", desktop_frontends.power),
    "DockWindow.qml": ("floating-dock-window-v1", desktop_frontends.dock),
}
UPSTREAM.update(DESKTOP_UPSTREAM)
AUTHORED = {name: "config/shell/preview/" + source for name, source in (
    ("Commons/Style.qml", "Style.qml"), ("Commons/Color.qml", "Color.qml"),
    ("Commons/I18n.qml", "I18n.qml"), ("PreviewContent.qml", "PreviewContent.qml"),
    ("TrialPolicy.js", "TrialPolicy.js"), ("TrialShell.qml", "TrialShell.qml"),
    ("TrialPanel.qml", "TrialPanel.qml"), ("LiveStatus.qml", "LiveStatus.qml"),
    ("AppLauncher.qml", "AppLauncher.qml"), ("KeybindingsMenu.qml", "KeybindingsMenu.qml"),
    ("PortTrayHost.qml", "PortTrayHost.qml"),
    ("NetworkPresentation.js", "NetworkPresentation.js"),
    ("NetworkStatusProvider.qml", "NetworkStatusProvider.qml"),
    ("NetworkStatusView.qml", "NetworkStatusView.qml"),
    ("AudioActions.js", "AudioActions.js"), ("AudioPresentation.js", "AudioPresentation.js"),
    ("AudioOutputProvider.qml", "AudioOutputProvider.qml"), ("AudioPanelController.qml", "AudioPanelController.qml"),
    ("NetworkPanelController.qml", "NetworkPanelController.qml"))}
for name in ("DesktopPanelController", "BluetoothActions", "DisplayPanelController", "PowerPanelController", "FloatingDock"):
    AUTHORED[name + ".qml"] = "config/shell/preview/" + name + ".qml"
AUTHORED["Commons/TrialDesktopState.qml"] = "config/shell/preview/TrialDesktopState.qml"
AUTHORED["Commons/BluetoothDiscovery.qml"] = "config/shell/preview/BluetoothDiscovery.qml"
AUTHORED["Commons/InputMethodState.qml"] = "config/shell/preview/InputMethodState.qml"
AUTHORED["DockState.qml"] = "config/shell/preview/DockState.qml"
AUTHORED["CommandMenu.qml"] = "config/shell/preview/CommandMenu.qml"
AUTHORED["LaunchFeedback.qml"] = "config/shell/preview/LaunchFeedback.qml"
AUTHORED["ImagePicker.qml"] = "config/shell/preview/ImagePicker.qml"
AUTHORED["ImagePickerModel.js"] = "config/shell/preview/ImagePickerModel.js"
AUTHORED["MenuModel.js"] = "config/shell/preview/MenuModel.js"
AUTHORED["MenuButton.qml"] = "config/shell/preview/MenuButton.qml"
AUTHORED["OmarchyMark.qml"] = "config/shell/preview/OmarchyMark.qml"
AUTHORED["BarRun.js"] = "config/shell/preview/BarRun.js"
MAPS = {"Ui/qmldir": "module qs.Ui\nBarWidget 1.0 BarWidget.qml\nWidgetButton 1.0 WidgetButton.qml\nOpticalGlyph 1.0 OpticalGlyph.qml\n",
        "Commons/qmldir": "module qs.Commons\nsingleton Style 1.0 Style.qml\nsingleton Color 1.0 Color.qml\nsingleton I18n 1.0 I18n.qml\n"}
MAPS["Ui/qmldir"] += "".join(name + " 1.0 " + name + ".qml\n" for name in (
    "PopupCard", "BarIconButton", "BarIconContent", "IconContentBounds", "Button", "BorderSurface", "BorderOverlay", "PanelSlider", "KeyboardPanel", "PanelKeyCatcher",
    "CursorSurface", "ToggleSwitch", "PanelToolTip", "PanelSeparator", "PanelSectionHeader", "PanelActionButton", "TextField"))
MAPS["Commons/qmldir"] += "singleton Border 1.0 Border.qml\nsingleton TrialDesktopState 1.0 TrialDesktopState.qml\nsingleton BluetoothDiscovery 1.0 BluetoothDiscovery.qml\n"
MAPS["Commons/qmldir"] += "singleton Util 1.0 Util.qml\nsingleton InputDevices 1.0 InputDevices.qml\nsingleton InputMethodState 1.0 InputMethodState.qml\n"
MAPS["Port/qmldir"] = "Tray 1.0 Tray.qml\n"
MARKER = "OMABUNTU_PREVIEW_OK"
SCOPE = "sealed-clock-bar-preview-v1"
CASES = ("content", "render", "policy", "entry-denied", "assertion-control")


def derive_clock(data):
    """Exact reviewed read-only extraction; retain original text/font/format UI."""
    text = data.decode()

    def replace(old, new=""):
        nonlocal text
        if text.count(old) != 1:
            raise builder.BuildError("Clock extraction witness differs")
        text = text.replace(old, new)

    def remove_between(start, end):
        if text.count(start) != 1 or text.count(end) != 1:
            raise builder.BuildError("Clock extraction boundaries differ")
        replace(text[text.index(start):text.index(end)])

    replace("import Quickshell.Io\n")
    remove_between("// Date/time label for the bar", "BarWidget {\n")
    text = ("// Derived read-only trial of Omarchy's clock BarWidget; upstream MIT notice\n"
            "// is preserved in LICENSE. See upstream/clock-preview.json for exact origin.\n"
            "// Calendar, IPC, persistence and all pointer actions are deliberately absent.\n" + text)
    remove_between("  readonly property string configuredAltFormat", "  readonly property string activeFormat")
    remove_between("\n  function refresh() {", "  // Day and month names")
    remove_between("  // Day and month names", "  readonly property var formatLocale")
    remove_between("  // ---- Calendar popup.", "  implicitWidth: button.implicitWidth")
    replace("  onBarChanged: injectPanel()\n  onSettingsChanged: injectPanel()\n")
    remove_between("  Loader {\n    id: panelLoader", "  WidgetButton {\n")
    replace('    tooltipText: I18n.t("clock.toggleFormat")', '    tooltipText: ""\n    interactive: false\n    pressable: false')
    remove_between("    onPressed: function(b)", "    Column {\n")
    for forbidden in ("Panel.qml", "panelLoader", "ShellIpc", "Quickshell.Io", "cycleFormat", ".run(", "updateEntryInline"):
        if forbidden in text:
            raise builder.BuildError("Active clock path remains in extraction")
    return text.encode()


def verified_sources(root):
    meta = json.loads(audit_widgets.bounded(root, "upstream/clock-preview.json"))
    pin = json.loads(audit_widgets.bounded(root, "upstream/omarchy-source.json"))
    source = {"repository": "https://github.com/omacom/omarchy", "commit": COMMIT}
    if (not isinstance(meta, dict) or type(meta.get("schema_version")) is not int or meta["schema_version"] != 1
            or meta.get("source") != source or meta.get("scope") != SCOPE
            or meta.get("production_catalog") != "empty" or meta.get("host_activation") != "separate-approval-required"
            or meta.get("module_maps") != MAPS or not isinstance(meta.get("upstream"), dict)
            or set(meta["upstream"]) != set(UPSTREAM) or not isinstance(meta.get("authored"), dict)
            or set(meta["authored"]) != set(AUTHORED) or not isinstance(pin, dict)
            or any(pin.get(key) != value for key, value in source.items())
            or not isinstance(pin.get("license"), dict) or pin["license"].get("spdx") != "MIT"
            or meta.get("notice_paths") != ["licenses/Omarchy-MIT.txt", "vendor/omarchy/LICENSE"]):
        raise builder.BuildError("Require the exact reviewed clock-preview profile")
    files = {name: data.encode() for name, data in MAPS.items()}
    for target, source_path in UPSTREAM.items():
        record = meta["upstream"][target]
        vendor = "vendor/omarchy/" + source_path
        transform = {"ClockLabel.qml": "readonly-clock-v1", "AudioOutputView.qml": "audio-output-frontend-v1",
                     "CalendarPanel.qml": "clock-calendar-v1", "ClockControlView.qml": "clock-calendar-host-v1",
                     "Ui/KeyboardPanel.qml": "ondemand-keyboard-panel-v1",
                     "BarTooltip.qml": "bar-tooltip-window-v1", "BarTooltipHost.qml": "bar-tooltip-host-v1",
                     "BarFrame.qml": "fixed-horizontal-sections-v1",
                     "NetworkControlView.qml": "network-control-frontend-v1",
                     "WorkspaceSwitcher.qml": "workspace-switcher-v1",
                     "KeyboardLayout.qml": "keyboard-layout-widget-v1"}.get(target, "none")
        if target in DESKTOP_TRANSFORMS:
            transform = DESKTOP_TRANSFORMS[target][0]
        if (not isinstance(record, dict) or record.get("path") != source_path or record.get("vendor_path") != vendor
                or record.get("license") != "MIT" or record.get("source_modifications") != []
                or record.get("stage_transform") != transform
                or record.get("url") != "https://raw.githubusercontent.com/omacom/omarchy/" + COMMIT + "/" + source_path):
            raise builder.BuildError("Upstream clock-preview provenance differs")
        wide = source_path in ("shell/plugins/bar/Bar.qml", "shell/plugins/panels/network/Panel.qml")
        data = audit_widgets.bounded(root, vendor, 131072 if wide else 65536)
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if (record.get("bytes") != len(data) or record.get("sha256") != hashlib.sha256(data).hexdigest()
                or record.get("git_blob_sha1") != blob):
            raise builder.BuildError("Upstream clock-preview source changed")
        transforms = {"readonly-clock-v1": derive_clock, "audio-output-frontend-v1": audio_frontend.derive_audio,
                      "ondemand-keyboard-panel-v1": audio_frontend.derive_keyboard,
                      "bar-tooltip-window-v1": tooltip_port.derive_window, "bar-tooltip-host-v1": tooltip_port.derive_host,
                      "fixed-horizontal-sections-v1": bar_frame.derive_frame,
                      "network-control-frontend-v1": network_frontend.derive_network,
                      "workspace-switcher-v1": workspace_modes.derive_workspaces,
                      "keyboard-layout-widget-v1": keyboard_frontend.derive_keyboard_layout,
                      "clock-calendar-v1": clock_frontend.derive_calendar,
                      "clock-calendar-host-v1": clock_frontend.derive_host}
        transforms.update({key: fn for key, fn in DESKTOP_TRANSFORMS.values()})
        files[target] = transforms[transform](data) if transform != "none" else data
        if target in DESKTOP_TRANSFORMS and files[target] != audit_widgets.bounded(root, "config/shell/preview/" + target, 65536):
            raise builder.BuildError("Generated desktop frontend mirror differs")
        if target == "AudioOutputView.qml" and files[target] != audit_widgets.bounded(root, "config/shell/preview/AudioOutputView.qml", 65536):
            raise builder.BuildError("Generated audio frontend mirror differs")
        if target == "NetworkControlView.qml" and files[target] != audit_widgets.bounded(root, "config/shell/preview/NetworkControlView.qml", 65536):
            raise builder.BuildError("Generated network frontend mirror differs")
        if target == "WorkspaceSwitcher.qml" and files[target] != audit_widgets.bounded(root, "config/shell/preview/WorkspaceSwitcher.qml", 65536):
            raise builder.BuildError("Generated workspace switcher mirror differs")
        if target == "KeyboardLayout.qml" and files[target] != audit_widgets.bounded(root, "config/shell/preview/KeyboardLayout.qml", 65536):
            raise builder.BuildError("Generated keyboard layout mirror differs")
        if target in ("CalendarPanel.qml", "ClockControlView.qml") and files[target] != audit_widgets.bounded(root, "config/shell/preview/" + target, 65536):
            raise builder.BuildError("Generated clock calendar mirror differs")
        if hashlib.sha256(files[target]).hexdigest() != record.get("staged_sha256"):
            raise builder.BuildError("Staged clock extraction differs from review")
    for target, path in AUTHORED.items():
        record = meta["authored"][target]
        data = audit_widgets.bounded(root, path, 65536)
        if not isinstance(record, dict) or record.get("path") != path or record.get("sha256") != hashlib.sha256(data).hexdigest():
            raise builder.BuildError("Authored preview source differs from review")
        files[target] = data
    for path in meta["notice_paths"]:
        data = audit_widgets.bounded(root, path, 8192)
        if hashlib.sha256(data).hexdigest() != pin["license"].get("sha256"):
            raise builder.BuildError("Complete upstream notice differs")
    files["LICENSE"] = data
    return files, meta


def probe(name):
    if name not in CASES:
        raise builder.BuildError("Only fixed clock-preview diagnostics are allowed")
    return '''//@ pragma IgnoreSystemSettings
import QtQuick
import Quickshell
import "TrialPolicy.js" as Policy
ShellRoot {
  id: test
  property var instance: null
  function require(value, message) { if (!value) throw new Error(message); }
  function finish() {
    console.log("OMABUNTU_PREVIEW_OK::%s");
    if (instance) instance.destroy();
    Qt.callLater(function() { Qt.quit(); });
  }
  function check() {
    var mode = %s;
    if (mode === "policy") {
      var good = Policy.prepare('{"schema_version":1,"scope":"clock-bar-trial-v1","duration_seconds":60}');
      require(good !== null && Object.isFrozen(good), "frozen grant");
      var bad = ["", "{", "null", "[]", " ".repeat(4097), '{"plugins":[]}'];
      var session = Policy.prepare('{"schema_version":1,"scope":"bar-session-v1","lifetime":"session"}');
      require(session !== null && Object.isFrozen(session) && session.lifetime === "session", "explicit session lifetime");
      for (var value of [null, true, 0, "forever", "", 3600]) {
        require(Policy.prepare(JSON.stringify({schema_version:1,scope:"bar-session-v1",lifetime:value})) === null, "deny ambiguous lifetime");
      }
      require(Policy.prepare('{"schema_version":1,"scope":"bar-session-v1","lifetime":"session","duration_seconds":60}') === null, "deny mixed lifetime");
      require(Policy.prepare('{"schema_version":true,"scope":"bar-session-v1","lifetime":"session"}') === null, "deny boolean schema");
      var base = {schema_version:1, scope:"clock-bar-trial-v1", duration_seconds:60};
      for (var pair of [["schema_version",true],["scope","full-shell"],["duration_seconds",true],
                       ["duration_seconds",0],["duration_seconds",3601],["duration_seconds",5.5],
                       ["run","forbidden"],["url","file:///outside.qml"]]) {
        var p = Object.assign({}, base); p[pair[0]] = pair[1]; bad.push(JSON.stringify(p));
      }
      for (var value of bad) require(Policy.prepare(value) === null, "deny invalid grant");
      require(Policy.prepare(JSON.stringify(Object.assign({},base,{duration_seconds:5}))) !== null, "minimum lifetime");
      require(Policy.prepare(JSON.stringify(Object.assign({},base,{duration_seconds:3600}))) !== null, "maximum lifetime");
      test.finish(); return;
    }
    var factory = Qt.createComponent(mode === "render" ? "RenderHost.qml" : "PreviewContent.qml", Component.PreferSynchronous);
    require(factory.status === Component.Ready, factory.errorString());
    instance = factory.createObject(null);
    factory.destroy();
    require(instance !== null, "content creation");
    var frame = mode === "render" ? instance.frame : instance;
    require(frame.actionsDisabled && frame.spacerWidth === 12 && frame.labelWidth > 20, "content geometry/actions");
    require(/^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) [0-9]{2}:[0-9]{2}$/.test(frame.labelText), "English weekday/time");
    require(typeof frame.passiveBar.run === "undefined" && typeof frame.passiveBar.shell === "undefined", "no command host");
    var component = Qt.createComponent("ClockLabel.qml", Component.PreferSynchronous);
    require(component.status === Component.Ready, component.errorString());
    var clock = component.createObject(null, {bar:frame.passiveBar, settings:Object.freeze({format:"dddd HH:mm"}), enabled:false});
    component.destroy(); require(clock !== null, "format fixture");
    require(clock.formatted(new Date(2026,0,1,9,7)) === "Donnerstag 09:07", "original locale formatter");
    clock.settings = Object.freeze({format:"yyyy-MM-dd 'W'ww"});
    require(clock.formatted(new Date(2025,11,29,9,7)) === "2025-12-29 W01", "original ISO-week formatter");
    for (var field of ["cycleFormat", "togglePanel", "opened", "injectPanel"])
      require(typeof clock[field] === "undefined", "active path absent: " + field);
    clock.destroy();
    if (mode === "assertion-control") {
      console.error("OMABUNTU_PREVIEW_ASSERTION_FAILED deliberate geometry mismatch");
      instance.destroy(); Qt.exit(42); return;
    }
    if (mode === "render") { capture.start(); return; }
    test.finish();
  }
  Timer {
    interval: 1; running: true; repeat: false
    onTriggered: {
      try { test.check(); }
      catch (error) { console.error("OMABUNTU_PREVIEW_EXCEPTION", String(error)); Qt.exit(43); }
    }
  }
  Timer {
    id: capture; interval: 200; repeat: false
    onTriggered: {
      var accepted = test.instance.frame.grabToImage(function(result) {
        if (!result.saveToFile("/home/probe/frame.png")) {
          console.error("OMABUNTU_PREVIEW_IMAGE_FAILED"); Qt.exit(43); return;
        }
        test.finish();
      });
      if (!accepted) { console.error("OMABUNTU_PREVIEW_GRAB_FAILED"); Qt.exit(43); }
    }
  }
}
''' % (name, json.dumps(name))


RENDER_HOST = '''import QtQuick
import QtQuick.Window
Window {
  width: 960; height: 32; visible: true
  readonly property Item frame: content
  PreviewContent { id: content; anchors.fill: parent }
}
'''


def classify(name, code, text):
    if name not in CASES or "Configuration Loaded" not in text:
        return False
    diagnostics = re.findall(r"^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b[^\n]*", text, re.MULTILINE)
    if name == "assertion-control":
        return (code == 42 and MARKER not in text and len(diagnostics) == 1
                and re.match(r"\s*ERROR\b", diagnostics[0]) is not None
                and "OMABUNTU_PREVIEW_ASSERTION_FAILED deliberate geometry mismatch" in diagnostics[0])
    if code != 0 or diagnostics or "OMABUNTU_TRIAL_STARTED" in text:
        return False
    if name == "entry-denied":
        return text.count("OMABUNTU_TRIAL_STOP missing or invalid grant") == 1 and MARKER not in text
    return text.count(MARKER + "::" + name) == 1


def inspect_png(path):
    """Bounded RGB(A) PNG reconstruction; distinguish painted text from blank output."""
    with path.open("rb") as stream:
        data = stream.read(1048577)
    if len(data) > 1048576 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise builder.BuildError("Invalid bounded preview PNG")
    position, packed, width, height, channels = 8, bytearray(), None, None, None
    while position < len(data):
        if position + 12 > len(data):
            raise builder.BuildError("Truncated preview PNG")
        length = struct.unpack_from(">I", data, position)[0]
        kind = data[position+4:position+8]; payload = data[position+8:position+8+length]
        if len(payload) != length or position+12+length > len(data):
            raise builder.BuildError("Truncated preview PNG chunk")
        if zlib.crc32(kind+payload) & 0xffffffff != struct.unpack_from(">I", data, position+8+length)[0]:
            raise builder.BuildError("Preview PNG CRC differs")
        position += length+12
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if (width, height) != (960,32) or depth != 8 or color not in (2,6) or any((compression,filtering,interlace)):
                raise builder.BuildError("Unexpected preview PNG format")
            channels = 3 if color == 2 else 4
        elif kind == b"IDAT":
            packed.extend(payload)
        elif kind == b"IEND":
            if position != len(data):
                raise builder.BuildError("Trailing preview PNG content")
            break
    if channels is None:
        raise builder.BuildError("Missing preview PNG header")
    size = height*(width*channels+1)
    decoder = zlib.decompressobj(); raw = decoder.decompress(bytes(packed), size+1)
    if len(raw) != size or not decoder.eof or decoder.unused_data:
        raise builder.BuildError("Unexpected preview PNG decompression")
    stride = width*channels; previous = bytearray(stride); painted = 0
    for y in range(height):
        method = raw[y*(stride+1)]; row = bytearray(raw[y*(stride+1)+1:(y+1)*(stride+1)])
        if method > 4:
            raise builder.BuildError("Unknown PNG row filter")
        for x in range(stride):
            left = row[x-channels] if x >= channels else 0; up = previous[x]; corner = previous[x-channels] if x >= channels else 0
            p = left+up-corner; distances = (abs(p-left),abs(p-up),abs(p-corner))
            predictor = (left,up,corner)[distances.index(min(distances))]
            row[x] = (row[x] + (0,left,up,(left+up)//2,predictor)[method]) & 255
        for x in range(width):
            pixel = row[x*channels:(x+1)*channels]
            if channels == 4 and pixel[3] != 255:
                raise builder.BuildError("Unexpected transparent preview pixel")
            if tuple(pixel[:3]) != (16,19,21):
                if not 200 <= x < 760:
                    raise builder.BuildError("Unexpected painting outside clock region")
                painted += 1
        previous = row
    if not 100 <= painted <= 6000:
        raise builder.BuildError("Blank or unexpectedly filled preview image")
    return dict(width=width,height=height,painted_pixels=painted,sha256=hashlib.sha256(data).hexdigest())


def run_checks(root, candidate):
    if shutil.which("bwrap") is None:
        raise builder.BuildError("Bubblewrap required; no host fallback")
    files, meta = verified_sources(root)
    build, runtime, evidence = check_runtime.verify_stage(root, candidate)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = builder.private_directory(builder.private_directory(root / "work/clock-preview") / stamp)
    report = dict(schema_version=1,status="running",checks=[],profile=meta,build=str(build),
                  checker_sha256=builder.digest(Path(__file__)),profile_sha256=builder.digest(root / "upstream/clock-preview.json"),
                  runtime_checker_sha256=builder.digest(root / "tools/check_runtime.py"),
                  limits="Fixed contained Item/QtQuick offscreen window checks only; no host Wayland, production panel, services, authentication, deployment or desktop acceptance.")
    report_path = output / "report.json"
    def save():
        report_path.write_text(json.dumps(report,indent=2)+"\n")
    save()
    try:
        for name in CASES:
            case = builder.private_directory(output / name)
            for folder in ("probe","home","home/runtime","home/config","home/cache","home/state","home/data"):
                builder.private_directory(case / folder)
            for relative, data in files.items():
                path = case / "probe" / relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
            (case / "probe/RenderHost.qml").write_text(RENDER_HOST)
            (case / "probe/shell.qml").write_text(probe(name) if name != "entry-denied" else files["TrialShell.qml"].decode())
            (case / "probe/fonts.conf").write_text('<fontconfig><dir>/usr/share/fonts</dir><cachedir>/home/probe/cache/fontconfig</cachedir></fontconfig>\n')
            before = builder.artifact_manifest(case / "probe")
            command = check_runtime.sandbox_command(runtime,case,[check_runtime.PREFIX+"/bin/quickshell","--no-color","--no-detailed-logs","--path","/probe/shell.qml"])
            check = dict(name=name,status="running",command=command,probe_artifacts=before)
            report["checks"].append(check); save()
            log = case / "output.log"
            with log.open("x") as stream:
                try:
                    result = subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=20,check=False)
                    check["returncode"] = result.returncode
                except subprocess.TimeoutExpired:
                    check.update(returncode=None,timed_out=True)
            text = log.read_text(errors="replace")
            check.update(log_sha256=builder.digest(log),inputs_unchanged=builder.artifact_manifest(case / "probe")==before,
                         diagnostics={level:len(re.findall(r"^\s*"+level+r"\b",text,re.MULTILINE)) for level in ("WARN","ERROR","FATAL","CRITICAL")})
            passed = check["inputs_unchanged"] and classify(name,check["returncode"],text)
            if passed and name == "render":
                check["image"] = inspect_png(case / "home/frame.png")
            check["status"] = "passed" if passed else "failed"; save()
            if not passed:
                raise builder.BuildError("Clock-preview check failed: "+name)
        report["status"] = "isolated-clock-preview-passed"
    except (OSError,ValueError,builder.BuildError,zlib.error,struct.error) as error:
        report.update(status="failed",error=str(error))
    report["stage_unchanged"] = builder.artifact_manifest(build / "stage")==evidence["artifacts"]
    if not report["stage_unchanged"]:
        report.update(status="failed",error="Stage changed during preview checks")
    save(); print("Private clock-preview check:",report_path)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",action="store_true",help="Run fixed isolated offscreen checks, never a host session")
    parser.add_argument("--build-dir",type=Path)
    args=parser.parse_args(argv)
    if not args.run:
        print("Plan only: sealed clock content, private offscreen render, strict policy/denied entry and assertion controls. No host-session launch.")
        return 0
    if args.build_dir is None:
        parser.error("--run requires --build-dir")
    os.umask(0o077)
    try:
        return 0 if run_checks(ROOT,args.build_dir)["status"]=="isolated-clock-preview-passed" else 1
    except (OSError,ValueError,builder.BuildError) as error:
        print("Refusing clock preview:",error,file=sys.stderr);return 1


if __name__ == "__main__":
    raise SystemExit(main())
