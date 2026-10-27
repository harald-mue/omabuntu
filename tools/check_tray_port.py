#!/usr/bin/env python3
"""Fixed isolated tray/network fixtures, never a host-session launcher."""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import check_clock_preview as preview
import check_runtime as runtime
import network_port_fixtures as network
import audio_port_fixtures as audio
import tooltip_port_fixtures as tooltip
import bar_frame_fixtures as frame
import app_launcher_fixtures as apps
import wifi_control_fixtures as wifi
import keybindings_menu_fixtures as keys

ROOT = Path(__file__).resolve().parents[1]
CASES = ("empty", "active", "passive", "preferences", "negative")
MARKER = "OMABUNTU_TRAY_FIXTURE_OK"


def fixture(name):
    if name not in CASES:
        raise ValueError("Unknown fixed fixture")
    return '''//@ pragma IgnoreSystemSettings
import QtQuick
import Quickshell
import "FixtureTray" as F
ShellRoot {
  property var instance: null
  function require(value, message) { if (!value) throw new Error(message); }
  Timer { interval: 200; running: true; onTriggered: {
    try {
      var factory = Qt.createComponent("PortTrayHost.qml", Component.PreferSynchronous);
      require(factory.status === Component.Ready, factory.errorString());
      instance = factory.createObject(null);
      require(instance !== null, "host creation");
      var mode = "%s";
      require(instance.itemCount === 0, "empty initial model");
      if (mode !== "empty") {
        F.SystemTray.items = { values: [{ id:"fixture", title:"Fixture", tooltipTitle:"Fixture", icon:"", status: mode === "passive" ? 0 : 1 }] };
        require(instance.itemCount === (mode === "passive" ? 0 : 1), "live model update");
      }
      if (mode === "preferences") {
        instance.widget.togglePin("fixture");
        require(instance.preferences.pinned.indexOf("fixture") !== -1, "pin owner update");
        require(instance.widget.pinnedItems.length === 1, "pinned bucket");
        instance.widget.toggleHide("fixture");
        require(instance.preferences.pinned.length === 0, "hidden removes pin");
        require(instance.widget.drawerItems.length === 0, "hidden bucket");
        instance.widget.toggleHide("fixture");
        require(instance.widget.drawerItems.length === 1, "restore drawer");
      }
      if (mode === "negative") throw new Error("deliberate tray assertion");
      console.log("%s::" + mode);
      instance.destroy(); Qt.callLater(function() { Qt.quit(); });
    } catch(error) { console.error("OMABUNTU_TRAY_ASSERT", String(error)); Qt.callLater(function() { Qt.exit(42); }); }
  } }
}
''' % (name, MARKER)


def classify(name, code, text):
    errors = re.findall(r"^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b.*", text, re.M)
    if name == "negative":
        return code == 42 and len(errors) == 1 and "deliberate tray assertion" in errors[0] and MARKER not in text
    return code == 0 and not errors and text.count(MARKER + "::" + name) == 1 and "Configuration Loaded" in text


def run_checks(root, build_dir, suite="tray"):
    if suite not in ("tray", "network", "audio", "tooltip", "frame", "apps", "wifi", "keys"):
        raise ValueError("Only fixed desktop fixture suites")
    suites = {"tray": (CASES, fixture, classify), "network": (network.CASES, network.fixture, network.classify),
              "audio": (audio.CASES, audio.fixture, audio.classify),
              "tooltip": (tooltip.CASES, tooltip.fixture, tooltip.classify),
              "frame": (frame.CASES, frame.fixture, frame.classify),
              "apps": (apps.CASES, apps.fixture, apps.classify),
              "wifi": (wifi.CASES, wifi.fixture, wifi.classify),
              "keys": (keys.CASES, keys.fixture, keys.classify)}
    cases, generate, assess = suites[suite]
    if shutil.which("bwrap") is None:
        raise runtime.builder.BuildError("Bubblewrap required; no host fallback")
    files, meta = preview.verified_sources(root)
    build, stage, evidence = runtime.verify_stage(root, build_dir)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    base = runtime.builder.private_directory(runtime.builder.private_directory(root / ("work/" + suite + "-port")) / stamp)
    report = {"status": "running", "checks": [], "profile_sha256": runtime.builder.digest(root / "upstream/clock-preview.json"),
              "checker_sha256": runtime.builder.digest(Path(__file__)),
              "network_fixtures_sha256": runtime.builder.digest(root / "tools/network_port_fixtures.py"),
              "audio_fixtures_sha256": runtime.builder.digest(root / "tools/audio_port_fixtures.py"),
              "tooltip_fixtures_sha256": runtime.builder.digest(root / "tools/tooltip_port_fixtures.py"),
              "tooltip_extraction_sha256": runtime.builder.digest(root / "tools/tooltip_port.py"),
              "frame_fixtures_sha256": runtime.builder.digest(root / "tools/bar_frame_fixtures.py"),
              "frame_extraction_sha256": runtime.builder.digest(root / "tools/bar_frame.py"),
              "app_fixtures_sha256": runtime.builder.digest(root / "tools/app_launcher_fixtures.py"),
              "key_fixtures_sha256": runtime.builder.digest(root / "tools/keybindings_menu_fixtures.py"),
              "wifi_fixtures_sha256": runtime.builder.digest(root / "tools/wifi_control_fixtures.py"),
              "wifi_extraction_sha256": runtime.builder.digest(root / "tools/network_frontend.py"),
              "suite": suite,
              "surface_fixture": ("synthetic KeyboardPanel ownership; original audio content/controls" if suite == "audio"
                                  else "original bubble measured without native popup/anchor" if suite == "tooltip"
                                  else "selector copy without layer or shortcut ownership" if suite == "keys" else None),
              "limits": "Fixed synthetic desktop fixtures and primitive device inputs. No native NetworkManager/PipeWire, live DBus, application menu, host pointer, native tooltip popup/anchoring, focus-grab, GPU or interactive acceptance."}
    try:
        for name in cases:
            case = runtime.builder.private_directory(base / name)
            for folder in ("probe", "home", "home/runtime", "home/config", "home/cache", "home/state", "home/data"):
                runtime.builder.private_directory(case / folder)
            for relative, data in files.items():
                path = case / "probe" / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                if suite == "apps" and relative == "AppLauncher.qml":
                    data = apps.fixture_launcher(data, native=name == "native-cold")
                if suite == "keys" and relative == "KeybindingsMenu.qml":
                    data = keys.fixture_menu(data)
                if suite in ("audio", "wifi") and relative == "Ui/KeyboardPanel.qml":
                    data = audio.KEYBOARD_SURFACE.encode()
                if suite == "wifi" and relative in ("NetworkControlView.qml", "NetworkPanelController.qml"):
                    witness = b"import Quickshell.Networking\n"
                    if data.count(witness) != 1:
                        raise runtime.builder.BuildError("Network service witness changed")
                    data = data.replace(witness, b'import "FixtureNetworking"\n')
                if suite == "frame" and relative in ("LiveStatus.qml", "WorkspaceSwitcher.qml"):
                    witness = b"import Quickshell.Hyprland\n"
                    if data.count(witness) != 1:
                        raise runtime.builder.BuildError("Hyprland fixture witness differs")
                    data = data.replace(witness, b'import "FixtureHyprland"\n')
                if relative == "Port/Tray.qml":
                    # Only the fixture copy uses a fake service. Production bytes stay unchanged.
                    witness = b"import Quickshell.Services.SystemTray\n"
                    if data.count(witness) != 1:
                        raise runtime.builder.BuildError("Tray service witness changed")
                    data = data.replace(witness, b'import "../FixtureTray"\n')
                path.write_bytes(data)
            fake = case / "probe/FixtureTray"
            fake.mkdir()
            (fake / "qmldir").write_text("singleton SystemTray 1.0 SystemTray.qml\nsingleton Status 1.0 Status.qml\n")
            (fake / "SystemTray.qml").write_text('pragma Singleton\nimport QtQml\nQtObject { property var items: ({ values: [] }) }\n')
            (fake / "Status.qml").write_text('pragma Singleton\nimport QtQml\nQtObject { enum State { Passive, Active, NeedsAttention } }\n')
            if suite == "apps":
                fake_entries = case / "probe/FixtureEntries"
                fake_entries.mkdir()
                (fake_entries / "qmldir").write_text("singleton DesktopEntries 1.0 DesktopEntries.qml\n")
                (fake_entries / "DesktopEntries.qml").write_text(apps.ENTRIES)
            if suite == "frame":
                fake_hypr = case / "probe/FixtureHyprland"
                fake_hypr.mkdir()
                (fake_hypr / "qmldir").write_text("singleton Hyprland 1.0 Hyprland.qml\n")
                (fake_hypr / "Hyprland.qml").write_text(frame.HYPRLAND)
            if suite == "tooltip":
                (case / "probe/TooltipBubbleFixture.qml").write_bytes(tooltip.bubble_fixture(files["BarTooltip.qml"]))
            if suite == "wifi":
                fake_net = case / "probe/FixtureNetworking"
                fake_net.mkdir()
                qmldir = ["module FixtureNetworking", "singleton Networking 1.0 Networking.qml"]
                (fake_net / "Networking.qml").write_text(wifi.NETWORKING)
                for enum, values in wifi.ENUMS.items():
                    qmldir.append("singleton " + enum + " 1.0 " + enum + ".qml")
                    (fake_net / (enum + ".qml")).write_text(wifi.enum_qml(enum, values))
                (fake_net / "qmldir").write_text("\n".join(qmldir) + "\n")
                (case / "probe/FixtureNetwork.qml").write_text(wifi.NETWORK)
                (case / "probe/FixtureDevice.qml").write_text(wifi.DEVICE)
            (case / "probe/shell.qml").write_text(generate(name))
            (case / "probe/fonts.conf").write_text('<fontconfig><dir>/usr/share/fonts</dir><cachedir>/home/probe/cache/fontconfig</cachedir></fontconfig>\n')
            if suite == "apps" and name == "native-cold":
                catalog = case / "home/data/applications"
                catalog.mkdir()
                for entry in ("Alpha", "Beta"):
                    (catalog / (entry.lower() + ".desktop")).write_text(
                        "[Desktop Entry]\nType=Application\nName=" + entry + "\nExec=/usr/bin/false\n")
            before = runtime.builder.artifact_manifest(case / "probe")
            command = runtime.sandbox_command(stage, case, [runtime.PREFIX + "/bin/quickshell", "--no-color", "--no-detailed-logs", "--path", "/probe/shell.qml"])
            if suite == "apps" and name == "native-cold":
                index = command.index("--chdir")
                command[index:index] = ["--setenv", "XDG_DATA_DIRS", "/nonexistent/data"]
            log = case / "output.log"
            code = None
            with log.open("x") as stream:
                try:
                    code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=20, check=False).returncode
                except subprocess.TimeoutExpired:
                    pass
            text = log.read_text(errors="replace")
            unchanged = before == runtime.builder.artifact_manifest(case / "probe")
            passed = unchanged and assess(name, code, text)
            report["checks"].append({"name": name, "passed": passed, "returncode": code, "inputs_unchanged": unchanged,
                                      "log_sha256": runtime.builder.digest(log), "command": command})
            if not passed:
                raise runtime.builder.BuildError("Tray fixture failed: " + name)
        report["status"] = "isolated-" + suite + "-fixtures-passed"
    except (OSError, ValueError, runtime.builder.BuildError) as error:
        report.update(status="failed", error=str(error))
    report["stage_unchanged"] = runtime.builder.artifact_manifest(build / "stage") == evidence["artifacts"]
    if not report["stage_unchanged"]:
        report.update(status="failed", error="Stage changed")
    (base / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Private " + suite + " report:", base / "report.json")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--build-dir", type=Path)
    parser.add_argument("--suite", choices=("tray", "network", "audio", "tooltip", "frame", "apps", "wifi", "keys"), default="tray")
    args = parser.parse_args()
    if not args.run:
        print("Plan only:", args.suite, "fixed synthetic fixtures; no host session or native NetworkManager.")
        return 0
    if args.build_dir is None:
        parser.error("--run requires --build-dir")
    return 0 if run_checks(ROOT, args.build_dir, args.suite)["status"] == "isolated-" + args.suite + "-fixtures-passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
