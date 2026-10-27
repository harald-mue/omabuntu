#!/usr/bin/env python3
"""Read-only static reference audit; never execute, source, or import reference code.

Reports are private and ignored. A successful audit run is not activation approval
or proof that lexical helper references are actual calls or complete dependencies.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import build_runtime as builder

ROOT = Path(__file__).resolve().parents[1]
SHELL = Path("snapshot/omarchy/usr-share-omarchy/shell")
HELPERS = Path("snapshot/system-reference/usr/bin")
EXTRA = (
    Path("snapshot/omarchy/usr-share-omarchy/default/omarchy/omarchy-menu.jsonc"),
    Path("snapshot/omarchy/usr-share-omarchy/config/omarchy/shell.json"),
    Path("snapshot/omarchy/usr-share-omarchy/default/hypr/autostart.lua"),
)
SUFFIXES = {".qml", ".js", ".sh", ".json", ".jsonc", ".toml"}
HELPER_TOKEN = re.compile(r"\bomarchy-[a-z0-9][a-z0-9-]*\b")
PATTERNS = {
    "privilege": r"\b(?:sudo|pkexec)\b",
    "arch_management": r"\b(?:pacman|yay|makepkg|mkinitcpio|limine|snapper)\b",
    "service_session_control": r"\b(?:systemctl|loginctl|powerprofilesctl)\b",
    "authentication_lock": r"\b(?:PamContext|PolkitAgent|WlSessionLock)\b|/etc/pam\.d/",
    "network": r"https?://|\b(?:curl|wget|XMLHttpRequest)\b",
    "command_dispatch": r"execDetached|execArgv|\bProcess\s*\{|\bcommand\s*:|\.command\s*=",
    "dynamic_qml": r"Qt\.create(?:Component|QmlObject)|createObject\s*\(",
    "startup": r"Component\.onCompleted|\brunning\s*:\s*true",
    "persistent_settings": r"\.setText\s*\(|\b(?:gsettings|dconf|chmod|chown)\b",
}


def plain_path(reference, relative):
    if relative.is_absolute() or ".." in relative.parts:
        raise builder.BuildError("Reference paths must stay inside the named package")
    current = reference
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise builder.BuildError(f"Refusing a reference symlink: {relative}")
    return current


def scan_text(text):
    """Conservative lexical findings include comments/strings, not control flow."""
    findings = []
    helpers = set()
    for number, line in enumerate(text.splitlines(), 1):
        helpers.update(HELPER_TOKEN.findall(line))
        for category, pattern in PATTERNS.items():
            if re.search(pattern, line):
                findings.append({"line": number, "category": category})
    return sorted(helpers), findings


def closure(seeds, edges):
    pending = list(seeds)
    seen = set()
    while pending:
        name = pending.pop()
        if name in seen or name not in edges:
            continue
        seen.add(name)
        pending.extend(edges[name])
    return sorted(seen)


def audit(reference):
    reference = Path(reference)
    if reference.is_symlink() or not reference.is_dir():
        raise builder.BuildError("Choose a real reference directory, not a symlink")
    reference = reference.resolve()
    paths = []
    for relative in (SHELL, HELPERS):
        base = plain_path(reference, relative)
        if not base.is_dir():
            raise builder.BuildError(f"Required reference directory missing: {relative}")
        for directory, dirs, files in os.walk(base, followlinks=False):
            for name in dirs:
                if (Path(directory) / name).is_symlink():
                    raise builder.BuildError("Symlinked reference subdirectories are not scanned")
            for name in sorted(files):
                path = Path(directory) / name
                if relative == HELPERS and not (name == "omarchy" or name.startswith("omarchy-")):
                    continue
                if relative == SHELL and path.suffix not in SUFFIXES and name != "qmldir":
                    continue
                paths.append(path.relative_to(reference))
    paths.extend(EXTRA)
    if len(paths) > 5000:
        raise builder.BuildError("Reference audit exceeds the file limit")
    records = []
    manifests = []
    edges = {}
    aliases = {}
    seeds = set()
    tokens = set()
    for relative in sorted(paths):
        leaf = reference / relative
        if relative.parent == HELPERS and leaf.is_symlink():
            target = os.readlink(leaf)
            if not re.fullmatch(r"omarchy(?:-[a-z0-9][a-z0-9-]*)?", target):
                raise builder.BuildError("Refusing unsafe helper symlink target")
            target_path = plain_path(reference, HELPERS / target)
            if not target_path.is_file():
                raise builder.BuildError("Helper alias target is not a captured regular file")
            # Record the alias edge without opening or following the symlink.
            aliases[relative.name] = target
            edges[relative.name] = [target]
            records.append({"path": str(relative), "type": "symlink", "target": target,
                            "helper_tokens": [target], "findings": []})
            continue
        path = plain_path(reference, relative)
        if not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
            raise builder.BuildError(f"Expected a bounded regular text file: {relative}")
        with path.open("rb") as stream:
            data = stream.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise builder.BuildError("Text file grew past the audit limit")
        text = data.decode("utf-8")
        helpers, findings = scan_text(text)
        tokens.update(helpers)
        records.append({"path": str(relative), "sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data), "helper_tokens": helpers, "findings": findings})
        if relative.is_relative_to(HELPERS):
            edges[relative.name] = helpers
        else:
            seeds.update(helpers)
        if relative.is_relative_to(SHELL) and (relative.name == "manifest.json" or relative.name.endswith(".manifest.json")):
            item = json.loads(text)
            if not isinstance(item, dict) or item.get("schemaVersion") != 1 or not isinstance(item.get("id"), str):
                raise builder.BuildError(f"Unsupported plugin manifest: {relative}")
            kinds = item.get("kinds")
            if (not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", item["id"])
                    or not isinstance(kinds, list) or not kinds
                    or any(kind not in ("bar", "bar-widget", "service", "panel", "overlay", "menu") for kind in kinds)
                    or not isinstance(item.get("keepLoaded", False), bool)):
                raise builder.BuildError("Invalid plugin identity, kinds, or lifetime metadata")
            entrypoints = item.get("entryPoints")
            if not isinstance(entrypoints, dict) or not entrypoints:
                raise builder.BuildError("Invalid entry point map")
            for value in entrypoints.values():
                if not isinstance(value, str):
                    raise builder.BuildError("Invalid entry point path")
                entry = plain_path(reference, relative.parent / value)
                if not entry.is_file() or not entry.is_relative_to(reference / relative.parent):
                    raise builder.BuildError("Plugin entry point is missing or escapes its directory")
            manifests.append({"id": item["id"], "path": str(relative), "kinds": item.get("kinds", []),
                              "keepLoaded": item.get("keepLoaded", False), "entryPoints": entrypoints})
    ids = [item["id"] for item in manifests]
    if len(ids) != len(set(ids)):
        raise builder.BuildError("Duplicate first-party plugin identifiers")
    seeds.update(("omarchy-launch-shell", "omarchy-shell"))
    reachable = closure(seeds, edges)
    counts = {category: sum(f["category"] == category for r in records for f in r["findings"])
              for category in PATTERNS}
    return {
        "schema_version": 1, "status": "audit-only-not-activation-approved",
        "method": "Read regular reference text only; no reference execution, shell parsing by execution, imports, or network.",
        "limitations": "Lexical overapproximation includes comments/strings. Dynamic dispatch, bare omarchy subcommands, plugin discovery, script sourcing, and non-Omarchy external commands are not a complete call graph. No helper is approved by this report.",
        "files": records, "file_count": len(records) - len(aliases), "helper_count": len(edges),
        "helper_aliases": aliases,
        "manifests": manifests, "manifest_count": len(manifests),
        "service_manifests": [item for item in manifests if "service" in item["kinds"]],
        "finding_counts": counts, "seed_helper_candidates": sorted(seeds & edges.keys()),
        "potential_helper_closure": reachable, "helper_edges": edges,
        "unresolved_tokens": sorted(tokens - edges.keys()),
        "unresolved_token_warning": "Tokens can be names, namespaces, comments, or absent helpers; not a missing-executable verdict.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True, help="Explicit private reference package root")
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        report = audit(args.reference)
        work = builder.private_directory(ROOT / "work")
        parent = builder.private_directory(work / "shell-audit")
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        destination = builder.private_directory(parent / stamp) / "report.json"
        destination.write_text(json.dumps(report, indent=2) + "\n")
    except (OSError, ValueError, builder.BuildError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"Private static audit: {destination}")
    print(f"{report['file_count']} text files; {report['helper_count']} helper entries (including {len(report['helper_aliases'])} passive aliases); {report['manifest_count']} manifests")
    print(f"{len(report['potential_helper_closure'])} potential lexical helper dependencies; not execution reachability or approval")
    print("No reference programs, configuration changes, network queries, services, or desktop shell executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
