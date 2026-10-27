#!/usr/bin/env python3
"""Plan or run sealed original-spacer Item geometry checks; no windows/services."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import audit_widgets
import check_runtime

builder = check_runtime.builder
ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = {"Ui/BarWidget.qml": "shell/Ui/BarWidget.qml", "Spacer.qml": "shell/plugins/bar/widgets/Spacer.qml"}
AUTHORED = {"PassiveContract.js": "config/shell/PassiveContract.js", "PassiveBarApi.qml": "config/shell/PassiveBarApi.qml",
            "Commons/Style.qml": "config/shell/PassiveStyle.qml"}
MAPS = {"Ui/qmldir": "module qs.Ui\nBarWidget 1.0 BarWidget.qml\n",
        "Commons/qmldir": "module qs.Commons\nsingleton Style 1.0 Style.qml\n"}
MARKER = "OMABUNTU_SPACER_OK"
TRIPWIRE = "OMABUNTU_SPACER_STYLE_TOUCHED"


def configuration(vertical=False, bar=32, size=12):
    return json.dumps(dict(schema_version=1, vertical=vertical, bar_size=bar, spacer_size=size))


def specifications():
    result = []

    def add(name, text="", mode="normal", geometry=None, touches=0, blocked=False):
        live = geometry is not None
        result.append(dict(name=name, text=text, mode=mode, touches=touches,
                           expected={"created": int(live), "attempts": int(live), "geometry": geometry or [],
                                     "readonly": live, "namespaceBlocked": blocked}))
    add("horizontal", configuration(), geometry=[12, 32, True])
    add("vertical", configuration(True, 40, 24), geometry=[40, 24, True])
    add("original-default-size", configuration(), mode="default", geometry=[12, 32, True])
    add("zero-hidden", configuration(size=0), geometry=[0, 32, False])
    add("atomic-rebind", configuration(), mode="rebind", geometry=[48, 7, True])
    for name, text in (("missing", ""), ("invalid-json", "{"), ("null", "null"),
                       ("legacy-config", '{"plugins":[]}'),
                       ("wrong-bool", configuration().replace('false', '"false"')),
                       ("wrong-schema", configuration().replace('"schema_version": 1', '"schema_version": true')),
                       ("bar-zero", configuration(bar=0)), ("bar-oversized", configuration(bar=257)),
                       ("fractional", configuration(size=1.5)), ("negative-size", configuration(size=-1)),
                       ("oversized-size", configuration(size=4097)),
                       ("extra-command", configuration()[:-1] + ',"run":"forbidden"}'),
                       ("oversized-input", " " * 4097)):
        add(name, text)
    add("invalid-api", configuration(), mode="invalid-api")
    add("late-injection-control", configuration(True, 40, 24), mode="late", geometry=[40, 24, True], touches=1)
    add("sealed-namespace-control", mode="namespace", blocked=True)
    add("assertion-negative-control", configuration(), mode="assertion", geometry=[12, 32, True])
    return tuple(result)


CASES = specifications()


def verified_sources(root):
    pin = json.loads(audit_widgets.bounded(root, "upstream/omarchy-source.json"))
    meta = json.loads(audit_widgets.bounded(root, "upstream/spacer-candidate.json"))
    if (not isinstance(pin, dict) or pin.get("repository") != "https://github.com/omacom/omarchy"
            or not isinstance(pin.get("commit"), str) or not re.fullmatch(r"[0-9a-f]{40}", pin["commit"])
            or not isinstance(meta, dict) or type(meta.get("schema_version")) is not int or meta["schema_version"] != 1
            or meta.get("source") != {"repository": pin["repository"], "commit": pin["commit"]}
            or meta.get("scope") != "isolated-spacer-geometry-only" or meta.get("production_catalog") != "empty"
            or meta.get("module_maps") != MAPS or not isinstance(meta.get("originals"), dict)
            or set(meta["originals"]) != set(ORIGINALS) or not isinstance(meta.get("authored"), dict)
            or set(meta["authored"]) != set(AUTHORED)
            or meta.get("notice_paths") != ["licenses/Omarchy-MIT.txt", "vendor/omarchy/LICENSE"]):
        raise builder.BuildError("Require the exact reviewed sealed spacer profile")
    files = {name: text.encode() for name, text in MAPS.items()}
    for target, source in ORIGINALS.items():
        record = meta["originals"][target]
        path = "vendor/omarchy/" + source
        url = "https://raw.githubusercontent.com/omacom/omarchy/" + pin["commit"] + "/" + source
        if (not isinstance(record, dict) or record.get("path") != source or record.get("vendor_path") != path
                or record.get("url") != url or record.get("modifications") != [] or record.get("license") != "MIT"):
            raise builder.BuildError("Upstream spacer provenance differs")
        data = audit_widgets.bounded(root, path, 65536)
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if len(data) != record.get("bytes") or hashlib.sha256(data).hexdigest() != record.get("sha256") or blob != record.get("git_blob_sha1"):
            raise builder.BuildError("Upstream spacer bytes changed")
        files[target] = data
    for target, path in AUTHORED.items():
        record = meta["authored"][target]
        data = audit_widgets.bounded(root, path, 65536)
        if not isinstance(record, dict) or record.get("path") != path or hashlib.sha256(data).hexdigest() != record.get("sha256"):
            raise builder.BuildError("Authored passive profile differs from review")
        files[target] = data
    if not isinstance(pin.get("license"), dict) or pin["license"].get("spdx") != "MIT":
        raise builder.BuildError("Require pinned upstream MIT metadata")
    for path in meta["notice_paths"]:
        data = audit_widgets.bounded(root, path, 8192)
        if hashlib.sha256(data).hexdigest() != pin["license"].get("sha256"):
            raise builder.BuildError("Complete upstream notice differs")
    files["LICENSE"] = audit_widgets.bounded(root, "vendor/omarchy/LICENSE", 8192)
    style = files["Commons/Style.qml"].decode()
    if not style.endswith("}\n"):
        raise builder.BuildError("Unsupported authored Style instrumentation point")
    files["Commons/Style.qml"] = (style[:-2] + '\n  Component.onCompleted: console.log("' + TRIPWIRE + '")\n}\n').encode()
    return files, meta


def qml_probe(name):
    spec = next((case for case in CASES if case["name"] == name), None)
    if spec is None:
        raise builder.BuildError("Only fixed spacer cases are accepted")
    return '''//@ pragma IgnoreSystemSettings
import QtQml
import Quickshell
import "PassiveContract.js" as Contract
ShellRoot {
  id: test
  function runCheck() {
    var mode = %s;
    var text = %s;
    var attempts = 0;
    var item = null;
    var readonlyView = false;
    var namespaceBlocked = false;
    var plan = Contract.prepare(text);
    if (mode === "namespace") {
      var forbidden = Qt.createComponent("file:///probe/Forbidden.qml", Component.PreferSynchronous);
      namespaceBlocked = forbidden.status === Component.Error
        && forbidden.errorString().indexOf("InputDevices is not a type") !== -1;
      forbidden.destroy();
    } else if (plan !== null) {
      var apiComponent = Qt.createComponent("file:///probe/PassiveBarApi.qml", Component.PreferSynchronous);
      var api = apiComponent.createObject(test, {snapshotJson: mode === "invalid-api" ? "{}" : text});
      apiComponent.destroy();
      if (!api) throw new Error("Passive API creation failed");
      if (api.valid) {
        if (!Object.isFrozen(api.snapshot)) throw new Error("Snapshot is not frozen");
        var originalSize = api.barSize;
        try { api.barSize = originalSize + 1; } catch (error) { readonlyView = true; }
        if (!readonlyView || api.barSize !== originalSize || typeof api.run !== "undefined"
            || typeof api.shell !== "undefined" || typeof api.moduleWidgets !== "undefined")
          throw new Error("API is not the readonly geometry view");
        var component = Qt.createComponent("file:///probe/Spacer.qml", Component.PreferSynchronous);
        attempts++;
        if (component.status !== Component.Ready) throw new Error(component.errorString());
        var properties = {bar: api, settings: Object.freeze({size: plan.spacer_size})};
        if (mode === "default") delete properties.settings;
        if (mode === "late") delete properties.bar;
        item = component.createObject(null, properties);
        component.destroy();
        if (!item) throw new Error("Spacer creation failed");
        if (mode === "late") { var unsafeHeight = item.implicitHeight; item.bar = api; }
        if (mode === "rebind") {
          var next = JSON.stringify({schema_version:1, vertical:true, bar_size:48, spacer_size:7});
          var nextComponent = Qt.createComponent("file:///probe/PassiveBarApi.qml", Component.PreferSynchronous);
          var nextApi = nextComponent.createObject(test, {snapshotJson: next});
          nextComponent.destroy();
          if (!nextApi || !nextApi.valid) throw new Error("Replacement API invalid");
          item.bar = nextApi;
          item.settings = Object.freeze({size:7});
          api.destroy();
        }
        if (item.parent !== null) throw new Error("Unexpected visual parent");
        if (mode === "assertion" && item.implicitWidth !== 9999) {
          console.error("OMABUNTU_SPACER_ASSERTION_FAILED deliberate geometry mismatch");
          item.destroy(); Qt.exit(42); return;
        }
      }
    }
    var result = {created: item ? 1 : 0, attempts: attempts,
                  geometry: item ? [item.implicitWidth, item.implicitHeight, item.visible] : [],
                  readonly: readonlyView, namespaceBlocked: namespaceBlocked};
    console.log("%s::%s", JSON.stringify(result));
    if (item) item.destroy();
    Qt.callLater(function() { Qt.quit(); });
  }
  Timer {
    interval: 1
    running: true
    repeat: false
    onTriggered: {
      try { test.runCheck(); }
      catch (error) { console.error("OMABUNTU_SPACER_EXCEPTION", String(error)); Qt.exit(43); }
    }
  }
}
''' % (json.dumps(spec["mode"]), json.dumps(spec["text"]), MARKER, name)


def classify(spec, code, output):
    diagnostics = re.findall(r"^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b[^\n]*", output, re.MULTILINE)
    if "Configuration Loaded" not in output or output.count(TRIPWIRE) != spec["touches"]:
        return False
    if spec["mode"] == "assertion":
        return (code == 42 and MARKER not in output and len(diagnostics) == 1
                and re.match(r"\s*ERROR\b", diagnostics[0]) is not None
                and "OMABUNTU_SPACER_ASSERTION_FAILED deliberate geometry mismatch" in diagnostics[0])
    matches = re.findall(re.escape(MARKER + "::" + spec["name"]) + r" (\{[^\n]+\})", output)
    try:
        return (code == 0 and not diagnostics and len(matches) == 1
                and json.dumps(json.loads(matches[0]), sort_keys=True) == json.dumps(spec["expected"], sort_keys=True) and "Failed to load configuration" not in output)
    except ValueError:
        return False


def run_checks(root, candidate):
    if shutil.which("bwrap") is None:
        raise builder.BuildError("Bubblewrap required; no less-isolated fallback")
    files, meta = verified_sources(root)
    build, runtime, evidence = check_runtime.verify_stage(root, candidate)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = builder.private_directory(builder.private_directory(root / "work/spacer-check") / stamp)
    report_path = output / "report.json"
    report = {"schema_version": 1, "status": "running", "checks": [], "build": str(build),
              "profile": meta, "checker_sha256": builder.digest(Path(__file__)),
              "runtime_checker_sha256": builder.digest(root / "tools/check_runtime.py"),
              "profile_sha256": builder.digest(root / "upstream/spacer-candidate.json"),
              "limits": "Sealed original spacer/base Item geometry with authored passive API/Style only; no windows, rendering, original Commons/Style, other plugins, services or host integration.",
              "isolation": "Established Bubblewrap runtime probes; read-only sources/runtime, private HOME, no real buses/display/compositor/GPU/network. Diagnostic-only crash suppression."}
    def save():
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    save()
    try:
        for spec in CASES:
            case = builder.private_directory(output / spec["name"])
            for name in ("probe", "home", "home/runtime", "home/config", "home/data", "home/state", "home/cache"):
                builder.private_directory(case / name)
            for name, data in files.items():
                path = case / "probe" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            (case / "probe/Forbidden.qml").write_text("import QtQml\nimport qs.Commons\nInputDevices {}\n")
            (case / "probe/shell.qml").write_text(qml_probe(spec["name"]))
            (case / "probe/fonts.conf").write_text('<fontconfig><dir>/usr/share/fonts</dir><cachedir>/home/probe/cache/fontconfig</cachedir></fontconfig>\n')
            before = builder.artifact_manifest(case / "probe")
            command = check_runtime.sandbox_command(runtime, case, [check_runtime.PREFIX + "/bin/quickshell", "--no-color", "--no-detailed-logs", "--path", "/probe/shell.qml"])
            log = case / "output.log"
            check = {"name": spec["name"], "mode": spec["mode"], "expected": spec["expected"], "command": command,
                     "probe_artifacts": before, "log": str(log.relative_to(output)), "status": "running"}
            report["checks"].append(check)
            save()
            with log.open("x") as stream:
                try:
                    result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=20, check=False)
                    check["returncode"] = result.returncode
                except subprocess.TimeoutExpired:
                    check.update(returncode=None, timed_out=True)
            text = log.read_text(errors="replace")
            check.update(log_sha256=builder.digest(log), style_touches=text.count(TRIPWIRE),
                         inputs_unchanged=builder.artifact_manifest(case / "probe") == before,
                         diagnostics={level: len(re.findall(r"^\s*" + level + r"\b", text, re.MULTILINE)) for level in ("WARN", "ERROR", "FATAL", "CRITICAL")})
            check["status"] = "passed" if check["inputs_unchanged"] and classify(spec, check["returncode"], text) else "failed"
            save()
            if check["status"] != "passed":
                raise builder.BuildError("Spacer case failed: " + spec["name"])
        report["status"] = "isolated-spacer-geometry-passed"
    except (OSError, ValueError, builder.BuildError) as error:
        report.update(status="failed", error=str(error))
    report["stage_unchanged"] = builder.artifact_manifest(build / "stage") == evidence["artifacts"]
    if not report["stage_unchanged"]:
        report.update(status="failed", error="Stage changed during checks")
    save()
    print(f"Private spacer check: {report_path}")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--build-dir", type=Path)
    args = parser.parse_args(argv)
    if not args.run:
        print(f"Plan only: {len(CASES)} sealed offscreen Item geometry cases. No files/processes/desktop changes.")
        return 0
    if args.build_dir is None:
        parser.error("--run requires --build-dir")
    os.umask(0o077)
    try:
        report = run_checks(ROOT, args.build_dir)
    except (OSError, ValueError, builder.BuildError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0 if report["status"] == "isolated-spacer-geometry-passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
