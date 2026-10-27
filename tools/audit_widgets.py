#!/usr/bin/env python3
"""Read-only, pinned lexical dependency audit of the original bar/clock/spacer.

This is not a QML parser, runtime reachability proof, or component load approval.
No reference code, shell helper, plugin or network request is executed.
"""

import argparse
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import sys

import audit_shell

builder = audit_shell.builder
ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINTS = {
    "bar": "plugins/bar/Bar.qml",
    "clock": "plugins/panels/clock/BarWidget.qml",
    "spacer": "plugins/bar/widgets/Spacer.qml",
}
MODULES = {"qs.Commons": "Commons", "qs.Ui": "Ui"}
IMPORT = re.compile(r'^\s*\.?import\s+(?:"([^"\n]+)"|([\w.]+))(?:\s+[0-9.]+)?(?:\s+as\s+(\w+))?', re.MULTILINE)
SYMBOL = re.compile(r'(?<![\w.])([A-Z][A-Za-z0-9_]*)\b')
QUALIFIED = re.compile(r'(?<![\w.])([A-Z][A-Za-z0-9_]*)\.([A-Z][A-Za-z0-9_]*)\b')
LITERAL = re.compile(r'["\']([^"\'\n]+\.(?:qml|js))["\']')
DYNAMIC = re.compile(r'Qt\.(?:createComponent|createQmlObject|resolvedUrl)|\b(?:source|sourceComponent)\s*:|\bcreateObject\s*\(')


def bounded(root, relative, limit=2 * 1024 * 1024):
    path = audit_shell.plain_path(root, Path(relative))
    if not path.is_file() or path.stat().st_size > limit:
        raise builder.BuildError(f"Expected bounded regular file: {relative}")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise builder.BuildError("Input grew beyond the read bound")
    return data


def local_path(directory, value):
    if not isinstance(value, str) or not value or re.search(r'[:%\\\x00-\x20]', value) or value.startswith("/"):
        raise builder.BuildError("Unsupported local source path")
    result = posixpath.normpath(posixpath.join(directory, value))
    if result == ".." or result.startswith("../"):
        raise builder.BuildError("Source path escapes the shell tree")
    return result


def load_index(evidence, pin):
    evidence = Path(evidence)
    if evidence.is_symlink() or not evidence.is_dir():
        raise builder.BuildError("Choose a real source-evidence directory")
    provenance = json.loads(bounded(evidence, "source-provenance.json"))
    data = bounded(evidence, "source-tree.json", 8 * 1024 * 1024)
    url = "https://api.github.com/repos/omacom/omarchy/git/trees/" + pin["commit"] + "?recursive=1"
    if (not isinstance(provenance, dict) or provenance.get("commit") != pin["commit"] or provenance.get("repository") != pin["repository"]
            or provenance.get("tree_url") != url
            or provenance.get("tree_response_sha256") != hashlib.sha256(data).hexdigest()):
        raise builder.BuildError("Source evidence does not bind the pinned tree response")
    tree = json.loads(data)
    if (not isinstance(tree, dict) or tree.get("truncated") is not False
            or not isinstance(tree.get("tree"), list) or len(tree["tree"]) > 10000):
        raise builder.BuildError("Require a bounded non-truncated Git tree")
    paths = set()
    index = {}
    for record in tree["tree"]:
        if not isinstance(record, dict):
            raise builder.BuildError("Invalid Git tree entry")
        name = record.get("path")
        if (not isinstance(name, str) or PurePosixPath(name).is_absolute()
                or ".." in PurePosixPath(name).parts or str(PurePosixPath(name)) != name or name in paths):
            raise builder.BuildError("Invalid or duplicate Git tree path")
        paths.add(name)
        if not name.startswith("shell/") or record.get("type") != "blob":
            continue
        relative = name[len("shell/"):]
        if Path(relative).suffix not in (".qml", ".js") and Path(relative).name != "qmldir":
            continue
        if (record.get("mode") not in ("100644", "100755") or not isinstance(record.get("sha"), str)
                or not re.fullmatch(r"[0-9a-f]{40}", record["sha"])):
            raise builder.BuildError("Unsupported source blob type or hash")
        index[relative] = record["sha"]
    return index, hashlib.sha256(data).hexdigest()


def parse_exports(text, directory, index):
    result = {}
    module_seen = False
    for line in text.splitlines():
        parts = line.split("#", 1)[0].split()
        if not parts:
            continue
        if parts[0] == "module":
            if module_seen or parts != ["module", "qs." + directory]:
                raise builder.BuildError("Unexpected or duplicate module declaration")
            module_seen = True
            continue
        if parts[0] == "singleton":
            parts = parts[1:]
        if len(parts) != 3 or not re.fullmatch(r"[A-Z][A-Za-z0-9_]*", parts[0]) or not re.fullmatch(r"\d+\.\d+", parts[1]):
            raise builder.BuildError("Unsupported qmldir declaration")
        target = local_path(directory, parts[2])
        if target not in index or not target.endswith(".qml") or parts[0] in result:
            raise builder.BuildError("Duplicate or missing module export")
        result[parts[0]] = target
    if not module_seen:
        raise builder.BuildError("Missing module declaration")
    return result


def dependencies(path, text, index, exports):
    directory = posixpath.dirname(path)
    candidates = {}
    aliases = {}
    edges = set()
    external = set()
    unresolved = set()
    witnesses = []

    def add_symbols(mapping):
        for name, target in mapping.items():
            candidates.setdefault(name, set()).add(target)

    # Implicit same-directory QML types; version/precedence is not inferred.
    if path.endswith(".qml"):
        add_symbols({Path(name).stem: name for name in index
                     if posixpath.dirname(name) == directory and name.endswith(".qml")})
        if directory in exports:
            add_symbols(exports[directory])
            edges.add(directory + "/qmldir")
    for match in IMPORT.finditer(text):
        literal, module, alias = match.groups()
        if literal is not None:
            target = local_path(directory, literal)
            if target.endswith((".qml", ".js")):
                if target not in index:
                    raise builder.BuildError("Missing explicit local import: " + target)
                edges.add(target)
            else:
                local = {Path(name).stem: name for name in index
                         if posixpath.dirname(name) == target and name.endswith(".qml")}
                if not local:
                    raise builder.BuildError("Unresolved local directory import")
                if target + "/qmldir" in index:
                    if target not in exports:
                        raise builder.BuildError("Unsupported local directory module")
                    edges.add(target + "/qmldir")
                    local = exports[target]
                if alias:
                    aliases[alias] = local
                else:
                    add_symbols(local)
        elif module in MODULES:
            location = MODULES[module]
            edges.add(location + "/qmldir")
            if alias:
                aliases[alias] = exports[location]
            else:
                add_symbols(exports[location])
        elif module.startswith("qs."):
            raise builder.BuildError("Unsupported local module: " + module)
        else:
            external.add(module)
    if path.endswith(".qml"):
        for token in set(SYMBOL.findall(text)):
            edges.update(candidates.get(token, set()))
        for alias, token in QUALIFIED.findall(text):
            target = aliases.get(alias, {}).get(token)
            if target:
                edges.add(target)
    for value in LITERAL.findall(text):
        try:
            target = local_path(directory, value)
        except builder.BuildError:
            unresolved.add(value)
            continue
        if target in index:
            edges.add(target)
        else:
            unresolved.add(value)
    for number, line in enumerate(text.splitlines(), 1):
        if DYNAMIC.search(line):
            witnesses.append(number)
    edges.discard(path)
    return {"edges": sorted(edges), "external_imports": sorted(external),
            "unresolved_source_literals": sorted(unresolved), "dynamic_reference_lines": witnesses,
            "ambiguous_symbols": sorted(name for name, targets in candidates.items() if len(targets - {path}) > 1)}


def audit(reference, evidence, root=ROOT):
    reference = Path(reference)
    if reference.is_symlink() or not reference.is_dir():
        raise builder.BuildError("Choose a real reference directory")
    reference = reference.resolve()
    pin = json.loads(bounded(root, "upstream/omarchy-source.json"))
    if (not isinstance(pin, dict) or pin.get("repository") != "https://github.com/omacom/omarchy"
            or not isinstance(pin.get("commit"), str) or not re.fullmatch(r"[0-9a-f]{40}", pin["commit"])):
        raise builder.BuildError("Invalid pinned source metadata")
    index, tree_digest = load_index(evidence, pin)
    records = {}
    texts = {}

    def read(path):
        if path not in index:
            raise builder.BuildError("Source is absent from pinned tree: " + path)
        if path not in texts:
            data = bounded(reference, audit_shell.SHELL / path)
            blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            if blob != index[path]:
                raise builder.BuildError("Captured source differs from pinned blob: " + path)
            if sum(record["bytes"] for record in records.values()) + len(data) > 32 * 1024 * 1024:
                raise builder.BuildError("Dependency text exceeds the aggregate read bound")
            texts[path] = data.decode("utf-8")
            records[path] = {"path": path, "sha256": hashlib.sha256(data).hexdigest(),
                             "git_blob_sha1": blob, "bytes": len(data)}
        return texts[path]

    exports = {directory: parse_exports(read(directory + "/qmldir"), directory, index)
               for directory in MODULES.values()}
    pending = list(ENTRYPOINTS.values())
    graph = {}
    while pending:
        path = pending.pop()
        if path in graph:
            continue
        if len(graph) >= 500:
            raise builder.BuildError("Dependency graph exceeds the file bound")
        text = read(path)
        details = {"edges": [], "external_imports": [], "unresolved_source_literals": [],
                   "dynamic_reference_lines": [], "ambiguous_symbols": []}
        if Path(path).name != "qmldir":
            details = dependencies(path, text, index, exports)
        helpers, findings = audit_shell.scan_text(text)
        graph[path] = details["edges"]
        records[path].update(details, helper_tokens=helpers, findings=findings)
        pending.extend(details["edges"])
    closures = {name: audit_shell.closure([path], graph) for name, path in ENTRYPOINTS.items()}
    return {"schema_version": 1, "status": "static-reference-audit-not-load-approval",
            "source_commit": pin["commit"], "source_tree_response_sha256": tree_digest,
            "entrypoints": ENTRYPOINTS, "closures": closures, "files": sorted(records.values(), key=lambda item: item["path"]),
            "limits": "Lexical overapproximation includes comments/strings, not QML precedence, eager instantiation, runtime or complete dependency proof. Dynamic registries, JS context, native module internals, data/assets and external helper closures remain separate. No reference code executed; no network, imports, catalog changes or desktop activation."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--source-evidence", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = audit(args.reference, args.source_evidence)
        directory = builder.private_directory(ROOT / "work/widget-audit")
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        output = builder.private_directory(directory / stamp) / "report.json"
        report["auditor_sha256"] = builder.digest(Path(__file__))
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Private widget audit: {output}")
        print("Pinned files:", len(report["files"]), "; lexical closure sizes:",
              {name: len(paths) for name, paths in report["closures"].items()})
    except (OSError, ValueError, builder.BuildError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
