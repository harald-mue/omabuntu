#!/usr/bin/env python3
"""Omabuntu diagnostics, APT simulation, and isolated profile checks; no deployment."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = (
    "hyprland", "quickshell", "uwsm", "ghostty", "hyprsunset",
    "xdg-desktop-portal-hyprland", "qt6-base-dev", "qt6-declarative-dev",
    "libqt6core6t64", "libqt6qml6", "libqt6quick6", "qt6-wayland", "pipewire", "wireplumber",
)
BINARIES = (
    "Hyprland", "hyprctl", "quickshell", "qs", "uwsm", "ghostty",
    "hyprlock", "hypridle", "hyprsunset", "wl-copy", "wpctl", "qmake6",
)


def probe(args, timeout=15, env=None, cwd=None):
    """Capture an explicit diagnostic command; never use shell expansion."""
    result = {"command": list(args)}
    try:
        completed = subprocess.run(
            args, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False,
            env={**(os.environ if env is None else env), "LC_ALL": "C"}, cwd=cwd,
        )
        result.update(
            status="ok" if completed.returncode == 0 else "failed",
            returncode=completed.returncode,
            stdout=completed.stdout, stderr=completed.stderr,
        )
    except FileNotFoundError:
        result.update(status="missing", returncode=None, stdout="", stderr="Command not found")
    except subprocess.TimeoutExpired:
        # Partial timeout output may be bytes and may contain unreviewed data.
        result.update(status="timeout", returncode=None, stdout="", stderr="Probe timed out")
    except OSError as error:
        result.update(status="error", returncode=None, stdout="", stderr=str(error))
    return result


def read_os_release(path=Path("/etc/os-release")):
    """Parse selected os-release fields as data, never source the file."""
    try:
        values = {}
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            key, separator, value = line.partition("=")
            if separator and key in {"ID", "VERSION_ID", "PRETTY_NAME"}:
                values[key] = value.strip().strip("\"'")
        return {"status": "ok", "values": values}
    except OSError as error:
        return {"status": "error", "values": {}, "error": str(error)}


def collect():
    """Collect a deliberately narrow inventory, without user-config contents."""
    session = {key: os.environ.get(key) for key in (
        "XDG_CURRENT_DESKTOP", "XDG_SESSION_TYPE", "XDG_SESSION_DESKTOP",
    )}
    commands = {
        # This exits before compositor startup in the inspected 0.56.2 source.
        # It reports the installed binary, not a running session's version.
        "hyprland_binary_version": ["Hyprland", "--version-json"],
        "packages": ["dpkg-query", "-W", "-f=${binary:Package}\t${Version}\n", *PACKAGES],
        "apt_candidates": ["apt-cache", "policy", *PACKAGES],
    }
    # Do not target another session or start a compositor from a GNOME terminal.
    hyprland_context = bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"))
    if hyprland_context:
        commands["hyprland_version"] = ["hyprctl", "version"]
        commands["hyprland_configerrors"] = ["hyprctl", "configerrors"]
    probes = {name: probe(args) for name, args in commands.items()}
    if not hyprland_context:
        for name in ("hyprland_version", "hyprland_configerrors"):
            probes[name] = {
                "status": "skipped", "reason": "No Hyprland instance in this process environment",
            }
    return {
        "schema_version": 1,
        "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "architecture": platform.machine(),
        "os": read_os_release(),
        "session": session,
        "binaries": {name: shutil.which(name) for name in BINARIES},
        "probes": probes,
        "limitations": [
            "Collection success is not desktop readiness or security acceptance.",
            "APT metadata is local and may be stale; no refresh or network request was made.",
            "Package versions do not prove loaded QML modules or runtime API compatibility.",
            "No configuration, service, authentication, or session state was changed.",
            "Reports are private and must be reviewed before sharing.",
        ],
    }


def new_report_directory(root=ROOT, category="doctor"):
    """Allocate a private artifact directory without following parent symlinks."""
    if category not in {"doctor", "package-plan", "profile-check"}:
        raise ValueError("Unknown report category")
    parent = root
    for name in ("work", category):
        parent = parent / name
        try:
            parent.mkdir(mode=0o700)
        except FileExistsError:
            pass
        if parent.is_symlink() or not parent.is_dir():
            raise OSError("Report parent must be a real directory")
        if parent.stat().st_mode & 0o077:
            raise OSError("Report parent must be private (no group/other permissions)")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    folder = parent / stamp
    folder.mkdir(mode=0o700)
    return folder


def save_json(output, report):
    """Write a new private report without overwriting existing evidence."""
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return output


def write_report(report, root=ROOT, category="doctor"):
    folder = new_report_directory(root, category)
    return save_json(folder / "report.json", report)


def check_profile(root=ROOT, run=probe):
    """Check only the bundled profile with the inspected Hyprland build.

    Lua configuration is executable code, not a sandboxed data format. This is
    process-environment isolation for our reviewed profile, not a security sandbox.
    """
    folder = new_report_directory(root, "profile-check")
    binary = shutil.which("Hyprland")
    report = {
        "schema_version": 1, "kind": "minimal-profile-check", "status": "blocked",
        "limitations": [
            "Parser acceptance is not functional desktop or security acceptance.",
            "No active user configuration is read, replaced, or reloaded by this tool.",
            "The bundled Lua profile is trusted executable code; isolation is not a sandbox.",
        ],
    }
    if binary is None:
        report["reason"] = "Hyprland binary is unavailable"
        return save_json(folder / "report.json", report), report
    version = run([binary, "--version-json"])
    report["binary_version"] = version
    try:
        build = json.loads(version.get("stdout", ""))
    except (ValueError, TypeError):
        build = {}
    expected = "efb50993780079460b0cbed1363e2166a2de1d9f"
    if (version["status"] != "ok" or not isinstance(build, dict)
            or build.get("version") != "0.56.2" or build.get("commit") != expected
            or build.get("dirty") is not False):
        report["reason"] = "Profile validation requires the reviewed clean Hyprland 0.56.2 build"
        return save_json(folder / "report.json", report), report
    profile = root / "config" / "hypr" / "minimal.lua"
    if profile.is_symlink() or not profile.is_file():
        report["reason"] = "Bundled profile must be a regular file"
        return save_json(folder / "report.json", report), report
    content = profile.read_bytes()
    snapshot = folder / "minimal.lua"
    descriptor = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
    report["profile_sha256"] = hashlib.sha256(content).hexdigest()
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
    for variable, name in (
        ("HOME", "home"), ("XDG_CONFIG_HOME", "config"),
        ("XDG_DATA_HOME", "data"), ("XDG_STATE_HOME", "state"),
        ("XDG_CACHE_HOME", "cache"), ("XDG_RUNTIME_DIR", "runtime"),
    ):
        directory = folder / name
        directory.mkdir(mode=0o700)
        environment[variable] = str(directory)
    report["validation"] = run(
        [binary, "--verify-config", "--config", str(snapshot)],
        timeout=30, env=environment, cwd=folder,
    )
    report["status"] = "passed" if report["validation"]["status"] == "ok" else "failed"
    return save_json(folder / "report.json", report), report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("doctor", help="Collect private read-only diagnostics; no installation")
    plan_parser = subcommands.add_parser("plan", help="Simulate packages; never install or build")
    plan_parser.add_argument("component", choices=["quickshell"])
    subcommands.add_parser("check-profile", help="Check bundled Lua in isolation; no active reload")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        report = collect()
        try:
            output = write_report(report)
        except OSError as error:
            print(f"Could not write private diagnostic report: {error}", file=sys.stderr)
            return 1
        print(f"Private diagnostic report: {output}")
        for name, result in report["probes"].items():
            print(f"  {name}: {result['status']}")
        print("Collection completed; this is not a desktop readiness verdict.")
        print("No packages, configuration, services, or session state changed.")
    elif args.command == "plan":
        from package_plan import create_plan

        try:
            report = create_plan(ROOT / "packages" / "quickshell-plan.json", probe)
            output = write_report(report, category="package-plan")
        except (OSError, ValueError) as error:
            print(f"Could not collect package plan: {error}", file=sys.stderr)
            return 1
        print(f"Private package plan: {output}")
        print(f"Status: {report['status']}; {report['reason']}")
        for key, packages in report.get("transaction", {}).items():
            print(f"  {key}: {len(packages)}")
        print("No packages installed, sources changed, or builds started.")
        return 0 if report["status"] == "review-required" else 1
    elif args.command == "check-profile":
        try:
            output, report = check_profile()
        except OSError as error:
            print(f"Could not check profile: {error}", file=sys.stderr)
            return 1
        print(f"Private profile report: {output}")
        print(f"Status: {report['status']}")
        print("Parser checks only; no active configuration or session changes.")
        return 0 if report["status"] == "passed" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
