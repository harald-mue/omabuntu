#!/usr/bin/env python3
"""Check a staged runtime in Bubblewrap; plan-only unless --run is supplied.

Only fixed, generated nonvisual QML probes are accepted. No host session access,
service objects, PAM conversation, shell configuration, or desktop activation.
"""

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import build_runtime as builder

ROOT = Path(__file__).resolve().parents[1]
PREFIX = builder.PREFIX
MODULES = (
    "Quickshell", "Quickshell.Io", "Quickshell.Widgets", "Quickshell.Wayland",
    "Quickshell.Hyprland", "Quickshell.Bluetooth", "Quickshell.Networking",
    "Quickshell.WindowManager", "Quickshell.X11", "Quickshell.I3", "Quickshell.DBusMenu",
    "Quickshell.Services.UPower", "Quickshell.Services.Pam",
    "Quickshell.Services.Notifications", "Quickshell.Services.Mpris",
    "Quickshell.Services.Greetd", "Quickshell.Services.Pipewire",
    "Quickshell.Services.SystemTray", "Quickshell.Services.Polkit",
    "QtQuick", "QtQuick.Controls", "QtQuick.Layouts", "QtQuick.Shapes",
    "QtQuick.Effects", "QtQuick.Window", "QtQuick.Templates", "QtQml.Models",
    "Qt.labs.folderlistmodel",
)
# Nullable typed properties resolve representative types without constructing them.
# Aggregate/singleton-only modules remain import-only, never singleton accesses.
PROBE_TYPES = {
    "Quickshell": "ShellRoot", "Quickshell.Io": "Process",
    "Quickshell.Widgets": "ClippingRectangle", "Quickshell.Bluetooth": "BluetoothAdapter",
    "Quickshell.Networking": "NetworkDevice", "Quickshell.WindowManager": "Windowset",
    "Quickshell.X11": "XPanelWindow", "Quickshell.DBusMenu": "DBusMenuHandle",
    "Quickshell.Services.UPower": "UPowerDevice", "Quickshell.Services.Pam": "PamContext",
    "Quickshell.Services.Notifications": "NotificationServer", "Quickshell.Services.Mpris": "MprisPlayer",
    "Quickshell.Services.Pipewire": "PwNode", "Quickshell.Services.SystemTray": "SystemTrayItem",
    "Quickshell.Services.Polkit": "PolkitAgent", "QtQuick": "Item",
    "QtQuick.Controls": "Button", "QtQuick.Layouts": "RowLayout", "QtQuick.Shapes": "Shape",
    "QtQuick.Effects": "MultiEffect", "QtQuick.Window": "Window", "QtQuick.Templates": "Control",
    "QtQml.Models": "ListModel", "Qt.labs.folderlistmodel": "FolderListModel",
}
NEGATIVE_MODULE = "Omabuntu.NonexistentModule"
MARKER = "OMABUNTU_IMPORT_OK"


def verify_stage(root, candidate):
    """Refuse out-of-workspace, changed, or unsuccessfully staged artifacts."""
    builds = root / "work/builds"
    if builds.is_symlink() or (root / "work").is_symlink():
        raise builder.BuildError("Refusing symlinked workspace parents")
    candidate = Path(candidate)
    if candidate.is_symlink():
        raise builder.BuildError("Refusing a symlinked build directory")
    workspace = candidate.resolve()
    if workspace.parent != builds.resolve() or not workspace.is_dir():
        raise builder.BuildError("Choose a direct build directory under this project's work/builds")
    report_path = workspace / "report.json"
    report = json.loads(report_path.read_text())
    if not report.get("steps") or not all(step.get("status") == "passed" for step in report["steps"]):
        raise builder.BuildError("All original sandbox steps must have passed")
    evidence = report
    if report.get("status") == "failed":
        evidence = json.loads((workspace / "assessment.json").read_text())
        if evidence.get("original_report_sha256") != builder.digest(report_path):
            raise builder.BuildError("Reassessment does not match the original report")
    if evidence.get("status") not in ("staged", "staged-with-warnings") or not evidence.get("shaders"):
        raise builder.BuildError("Require a completed stage and shader assessment")
    _, locked = builder.load_inputs(root)
    if report.get("source_lock") != locked:
        raise builder.BuildError("The build does not match the current source lock")
    stage = workspace / "stage"
    if stage.is_symlink() or builder.artifact_manifest(stage) != evidence.get("artifacts"):
        raise builder.BuildError("Staged artifacts differ from recorded hashes or link targets")
    runtime = stage / PREFIX.lstrip("/")
    if not (runtime / "bin/quickshell").is_file():
        raise builder.BuildError("Staged Quickshell binary is missing")
    return workspace, runtime, evidence


def qml_probe(module, marker):
    """Generate only allowlisted imports and a nonvisual root; no service access."""
    if module not in (*MODULES, NEGATIVE_MODULE) or not re.fullmatch(r"[A-Z0-9_]+", marker):
        raise builder.BuildError("Only fixed probe modules and safe markers are allowed")
    extra = "" if module == "Quickshell" else f"import {module} as Probe\n"
    type_name = PROBE_TYPES.get(module)
    qualified = type_name if module == "Quickshell" else f"Probe.{type_name}"
    typed_property = f"    property {qualified} typeProbe: null\n" if type_name else ""
    return (
        "//@ pragma IgnoreSystemSettings\n"
        "import QtQml\nimport Quickshell\n" + extra +
        "ShellRoot {\n" + typed_property +
        "    Component.onCompleted: {\n"
        f'        console.log("{marker}");\n'
        "        Qt.callLater(function() { Qt.quit(); });\n"
        "    }\n}\n"
    )


def sandbox_command(runtime, case, command):
    """Read-only runtime and probe; private HOME, no real buses, GPU or displays."""
    environment = {
        "PATH": "/usr/bin:/bin", "HOME": "/home/probe", "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8", "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software", "QML_IMPORT_PATH": PREFIX + "/lib/qt6/qml",
        "QML_IMPORT_TRACE": "1", "QS_DISABLE_CRASH_HANDLER": "1",
        "XDG_RUNTIME_DIR": "/home/probe/runtime", "XDG_CONFIG_HOME": "/home/probe/config",
        "XDG_DATA_HOME": "/home/probe/data", "XDG_STATE_HOME": "/home/probe/state",
        "XDG_CACHE_HOME": "/home/probe/cache", "XDG_CONFIG_DIRS": "/nonexistent/config",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent/session-bus",
        "DBUS_SYSTEM_BUS_ADDRESS": "unix:path=/nonexistent/system-bus",
        "PULSE_SERVER": "unix:/nonexistent/pulse", "PIPEWIRE_REMOTE": "omabuntu-no-server",
        "FONTCONFIG_FILE": "/probe/fonts.conf",
    }
    args = [
        "bwrap", "--unshare-all", "--die-with-parent", "--new-session",
        "--ro-bind", "/usr", "/usr",
        "--symlink", "usr/bin", "/bin", "--symlink", "usr/sbin", "/sbin",
        "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
        "--dir", "/etc", "--ro-bind", "/etc/alternatives", "/etc/alternatives",
        "--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--ro-bind", str(runtime), PREFIX,
        "--ro-bind", str(case / "probe"), "/probe",
        "--bind", str(case / "home"), "/home/probe", "--clearenv",
    ]
    for key, value in environment.items():
        args.extend(["--setenv", key, value])
    return [*args, "--chdir", "/home/probe", "--", *command]


def classify_qml(returncode, output, marker, negative=False):
    if negative:
        return returncode == 255 and marker not in output and (
            f'module "{NEGATIVE_MODULE}" is not installed' in output
        )
    return returncode == 0 and marker in output and "Configuration Loaded" in output and not any(
        message in output for message in ("Failed to load configuration", "undefined symbol", "is not installed")
    ) and not re.search(r"^\s*(?:ERROR|FATAL|CRITICAL)\b", output, re.MULTILINE)


def run_checks(root, candidate):
    for program in ("bwrap", "readelf", "ldd"):
        if shutil.which(program) is None:
            raise builder.BuildError(f"Required diagnostic tool is absent: {program}")
    build_dir, runtime, evidence = verify_stage(root, candidate)
    parent = builder.private_directory(root / "work/runtime-check")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = builder.private_directory(parent / stamp)
    report = {
        "schema_version": 1, "status": "running", "build": str(build_dir), "checks": [],
        "runtime_sha256": builder.digest(runtime / "bin/quickshell"),
        "build_warning_counts": evidence.get("warning_counts", {}),
        "limits": "Nonvisual imports only. No singleton service use, full shell, host session, PAM, lock, GPU, or compositor acceptance.",
        "isolation": "Bubblewrap private PID/network/filesystem namespaces; runtime/probes read-only; private HOME; no host sockets or real buses.",
        "crash_handler": "Disabled for disposable diagnostics only; compiled runtime unchanged. No crash/restart acceptance.",
    }
    report_path = output / "report.json"

    def save():
        report_path.write_text(json.dumps(report, indent=2) + "\n")

    def run(name, command, qml=None, marker=None, negative=False, module=None):
        case = builder.private_directory(output / name)
        for directory in ("probe", "home"):
            builder.private_directory(case / directory)
        for directory in ("runtime", "config", "data", "state", "cache"):
            builder.private_directory(case / "home" / directory)
        (case / "probe/fonts.conf").write_text(
            '<fontconfig><dir>/usr/share/fonts</dir><cachedir>/home/probe/cache/fontconfig</cachedir></fontconfig>\n'
        )
        if qml is not None:
            (case / "probe/shell.qml").write_text(qml)
        argv = sandbox_command(runtime, case, command)
        log = case / "output.log"
        check = {"name": name, "command": argv, "status": "running", "log": str(log.relative_to(output))}
        if qml is not None:
            check["qml_sha256"] = builder.digest(case / "probe/shell.qml")
            check["module"] = module
            check["resolved_type"] = PROBE_TYPES.get(module)
            check["scope"] = "import-and-nullable-type-resolution" if module in PROBE_TYPES else "import-only"
        report["checks"].append(check)
        save()
        with log.open("x") as stream:
            try:
                result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=20, check=False)
                check["returncode"] = result.returncode
            except subprocess.TimeoutExpired:
                check.update(returncode=None, status="timeout")
        text = log.read_text(errors="replace")
        check["diagnostics"] = [
            line for line in text.splitlines() if re.match(r"\s*(?:WARN|ERROR|FATAL|CRITICAL)\b", line)
        ]
        if name == "elf-dynamic":
            check["needed_libraries"] = re.findall(r"Shared library: \[([^\]]+)\]", text)
            check["library_search_paths"] = re.findall(r"Library (?:runpath|rpath): \[([^\]]+)\]", text)
        if check["status"] != "timeout":
            if marker:
                passed = classify_qml(check["returncode"], text, marker, negative)
            elif name == "linkage":
                passed = check["returncode"] == 0 and not re.search(r"not found|undefined symbol", text)
                passed = passed and all(library in text for library in ("libQt6Core", "libQt6Qml", "libQt6Quick"))
            else:
                passed = check["returncode"] == 0
            check["status"] = "passed" if passed else "failed"
        check["log_sha256"] = builder.digest(log)
        save()
        print(f"{name}: {check['status']}", flush=True)
        return check["status"] == "passed"

    save()
    try:
        if not run("sandbox-preflight", ["/usr/bin/true"]):
            raise builder.BuildError("Sandbox preflight failed; no less-isolated fallback")
        if not run("elf-dynamic", ["readelf", "-d", PREFIX + "/bin/quickshell"]):
            raise builder.BuildError("ELF inspection failed")
        if not run("linkage", ["ldd", "-r", PREFIX + "/bin/quickshell"]):
            raise builder.BuildError("Runtime linkage failed")
        command = [PREFIX + "/bin/quickshell", "--no-color", "--no-detailed-logs", "--path", "/probe/shell.qml"]
        if not run("baseline", command, qml_probe("Quickshell", MARKER), MARKER, module="Quickshell"):
            raise builder.BuildError("Baseline failed; do not interpret module probes as valid")
        if not run("negative-control", command, qml_probe(NEGATIVE_MODULE, MARKER), MARKER, negative=True):
            raise builder.BuildError("Missing-import negative control failed")
        for index, module in enumerate(MODULES[1:], 1):
            marker = f"{MARKER}_{index}"
            run(module.lower().replace(".", "-"), command, qml_probe(module, marker), marker, module=module)
        if builder.artifact_manifest(build_dir / "stage") != evidence["artifacts"]:
            raise builder.BuildError("Staged files changed during checks")
        report["stage_unchanged"] = True
        report["status"] = "isolated-imports-passed" if all(
            check["status"] == "passed" for check in report["checks"]
        ) else "failed"
    except (OSError, ValueError, builder.BuildError) as error:
        report.update(status="failed", error=str(error))
    save()
    print(f"Private runtime check: {report_path}", flush=True)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Run fixed nonvisual probes in Bubblewrap")
    parser.add_argument("--build-dir", type=Path, help="Direct directory under this project's work/builds")
    args = parser.parse_args(argv)
    if not args.run:
        print("Plan only. No directories, subprocesses, QML, or desktop changes.")
        print("After approval: python3 tools/check_runtime.py --run --build-dir work/builds/<timestamp>")
        print(f"ELF/linkage, positive/negative controls, and {len(MODULES)} nonvisual module imports.")
        return 0
    if args.build_dir is None:
        parser.error("--run requires --build-dir")
    os.umask(0o077)
    try:
        report = run_checks(ROOT, args.build_dir)
    except (OSError, ValueError, builder.BuildError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0 if report["status"] == "isolated-imports-passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
