"""Candidate-pinned, simulation-only APT planning. Never installs packages."""

import json
import re

GROUPS = ("build_dependencies", "cpptrace_dependencies", "runtime_dependencies")
PACKAGE_NAME = re.compile(r"[a-z0-9][a-z0-9+.-]*\Z")
VERSION = re.compile(r"[0-9][A-Za-z0-9.+:~\-]*\Z")


def load_manifest(path):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("name") != "quickshell":
        raise ValueError("Unsupported package manifest")
    packages = []
    for group in GROUPS:
        values = manifest.get(group)
        if not isinstance(values, list) or not values:
            raise ValueError(f"Missing package group: {group}")
        for name in values:
            if not isinstance(name, str) or not PACKAGE_NAME.fullmatch(name):
                raise ValueError("Invalid package name in manifest")
            if name not in packages:
                packages.append(name)
    return manifest, packages


def parse_policy(text):
    """Read LC_ALL=C apt-cache policy output, preserving raw evidence elsewhere."""
    result = {}
    current = None
    for line in text.splitlines():
        if line and not line[0].isspace() and line.endswith(":"):
            current = line[:-1]
            result[current] = {"installed": None, "candidate": None}
        elif current:
            for key in ("installed", "candidate"):
                prefix = key.title() + ":"
                if line.strip().startswith(prefix):
                    value = line.strip()[len(prefix):].strip()
                    if value != "(none)" and not VERSION.fullmatch(value):
                        raise ValueError("Unrecognized package version in APT policy")
                    result[current][key] = None if value == "(none)" else value
    return result


def summarize_simulation(text):
    """Summarize standard APT transaction lines; full output remains authoritative."""
    result = {"new": [], "upgraded_or_changed": [], "removed": []}
    for line in text.splitlines():
        if line.startswith("Inst "):
            fields = line.split()
            if len(fields) >= 3:
                key = "upgraded_or_changed" if fields[2].startswith("[") else "new"
                result[key].append(fields[1])
        elif line.startswith("Remv "):
            fields = line.split()
            if len(fields) >= 2:
                result["removed"].append(fields[1])
    return result


def create_plan(path, run):
    manifest, packages = load_manifest(path)
    policy = run(["apt-cache", "policy", *packages], timeout=30)
    report = {
        "schema_version": 1,
        "kind": "quickshell-package-plan",
        "status": "blocked",
        "manifest": manifest,
        "policy": policy,
        "simulation": None,
        "approval": "Not approved for installation or build",
        "limitations": [
            "Local APT metadata may be stale; no metadata refresh or network request.",
            "Explicit candidates are pinned for simulation, not a portable dependency lock.",
            "A successful simulation does not prove build or shell compatibility.",
            "No package installation, CMake configuration, or desktop activation is performed.",
        ],
    }
    if policy["status"] != "ok":
        report["reason"] = "APT policy probe failed"
        return report
    candidates = parse_policy(policy["stdout"])
    report["packages"] = {
        name: candidates.get(name, {"installed": None, "candidate": None}) for name in packages
    }
    missing = [name for name in packages if not report["packages"][name]["candidate"]]
    report["missing_candidates"] = missing
    if missing:
        report["reason"] = "Some explicit packages have no local candidate"
        return report
    pinned = [name + "=" + report["packages"][name]["candidate"] for name in packages]
    command = ["apt-get", "--simulate", "--no-remove", "--no-install-recommends", "install", *pinned]
    report["simulation"] = run(command, timeout=90)
    report["transaction"] = summarize_simulation(report["simulation"]["stdout"])
    if report["simulation"]["status"] != "ok":
        report["reason"] = "APT simulation failed; inspect the private report"
    elif report["transaction"]["removed"]:
        report["reason"] = "APT reported removals despite the no-remove policy"
    else:
        report["status"] = "review-required"
        report["reason"] = "Simulation completed; explicit approval and package-origin review required"
    return report
