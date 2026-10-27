#!/usr/bin/env python3
"""Plan or run fixed nonvisual gate fixtures, never the original shell or services."""

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import check_runtime as runtime_check

builder = runtime_check.builder
ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("GuardedHost.qml", "LoadPolicy.js")
MARKER = "OMABUNTU_GATE_OK"
ALPHA = "fixture.alpha"
BETA = "fixture.beta"
PROTECTED = (
    "omarchy.background", "omarchy.dock", "omarchy.lock", "omarchy.notifications",
    "omarchy.polkit", "omarchy.battery", "omarchy.idle", "omarchy.media",
    "omarchy.nightlight", "omarchy.remote-session",
)
CATALOG = {
    ALPHA: {"kind": "widget", "url": "file:///probe/components/Allowed.qml", "capabilities": []},
    BETA: {"kind": "bar", "url": "file:///probe/components/Allowed.qml", "capabilities": []},
}


def configuration(ids):
    return json.dumps({"schema_version": 1, "components": ids})


def specifications():
    """Fixed data only. No caller-supplied QML, actions, component URLs or catalogs."""
    cases = []

    def add(name, text="", catalog=None, state="blocked", attempts=0, created=0,
            destroyed=0, active=0, action="none", hook="none", negative=False):
        cases.append(dict(name=name, text=text, catalog=CATALOG if catalog is None else catalog,
                          state=state, attempts=attempts, created=created, destroyed=destroyed,
                          active=active, action=action, hook=hook, negative=negative))

    add("default-deny", catalog={})
    add("empty-plan", configuration([]), catalog={}, state="empty")
    add("empty-catalog", configuration([ALPHA]), catalog={})
    add("catalog-in-config", json.dumps({"schema_version": 1, "components": [ALPHA],
                                       "reviewedCatalog": CATALOG}), catalog={})
    for name, text in (
        ("invalid-json", "{"), ("null-config", "null"),
        ("legacy-fallback", '{"plugins":[]}'),
        ("wrong-version", '{"schema_version":true,"components":[]}'),
        ("wrong-components-type", '{"schema_version":1,"components":{}}'),
        ("extra-action", '{"schema_version":1,"components":[],"action":"forbidden"}'),
        ("prototype-key", '{"schema_version":1,"components":[],"__proto__":{}}'),
        ("duplicate-id", configuration([ALPHA, ALPHA])),
        ("unknown-id", configuration(["unknown.widget"])),
        ("inherited-id", configuration(["constructor"])),
        ("whole-plan-validation", configuration([ALPHA, "unknown.widget"])),
        ("oversized-list", configuration([ALPHA] * 17)),
        ("oversized-text", " " * 65537),
    ):
        add(name, text)
    for name, replacement in (
        ("service-kind", {"kind": "service"}),
        ("process-capability", {"capabilities": ["process"]}),
        ("remote-url", {"url": "https://invalid.example/Forbidden.qml"}),
        ("outside-url", {"url": "file:///usr/share/Forbidden.qml"}),
        ("encoded-traversal", {"url": "file:///probe/components/%2e%2e/Forbidden.qml"}),
    ):
        add(name, configuration([ALPHA]), catalog={ALPHA: {**CATALOG[ALPHA], **replacement}})
    for component_id in PROTECTED:
        add(component_id.replace(".", "-"), configuration([component_id]),
            catalog={component_id: CATALOG[ALPHA]})
    add("positive-widget", configuration([ALPHA]), state="fixtures-loaded", attempts=1, created=1, active=1)
    add("positive-two", configuration([ALPHA, BETA]), state="fixtures-loaded", attempts=2, created=2, active=2)
    for name, action in (("reload-sticky", "reload"), ("invalid-reload-sticky", "invalid"),
                         ("catalog-replacement", "catalog")):
        add(name, configuration([ALPHA]), attempts=1, created=1, destroyed=1, action=action)
    add("reentrant-revocation", configuration([ALPHA, BETA]), attempts=1,
        created=1, destroyed=1, hook="revoke")
    add("catalog-snapshot", configuration([ALPHA, BETA]), state="fixtures-loaded",
        attempts=2, created=2, active=2, hook="mutate")
    add("preparation-failure", configuration([ALPHA, BETA]),
        catalog={ALPHA: CATALOG[ALPHA], BETA: {**CATALOG[BETA], "url": "file:///probe/components/Missing.qml"}},
        attempts=2, created=1, destroyed=1)
    add("object-failure", configuration([ALPHA]),
        catalog={ALPHA: {**CATALOG[ALPHA], "url": "file:///probe/components/Required.qml"}}, attempts=1)
    add("assertion-negative-control", configuration([ALPHA]), state="fixtures-loaded",
        attempts=1, created=1, active=0, negative=True)
    return tuple(cases)


CASES = specifications()


def probe_qml(name):
    case = next((case for case in CASES if case["name"] == name), None)
    if case is None:
        raise builder.BuildError("Only fixed gate cases are accepted")
    hooks = {
        "none": "",
        "revoke": "gate.reload();",
        "mutate": 'gate.reviewedCatalog["fixture.beta"].url = "file:///probe/components/Missing.qml";',
    }
    actions = {
        "none": "",
        "reload": "gate.reload(); gate.start();",
        "invalid": 'gate.configurationText = "{"; gate.configurationText = ' + json.dumps(configuration([ALPHA])) + "; gate.start();",
        "catalog": "gate.reviewedCatalog = ({}); gate.start();",
    }
    expected = {"state": case["state"], "attempts": case["attempts"], "created": case["created"],
                "destroyed": case["destroyed"], "active": case["active"]}
    initial = ""
    if case["action"] != "none":
        initial = '''if (gate.state !== "fixtures-loaded" || gate.activeCount !== 1 || test.createdCount !== 1) {
          console.error("OMABUNTU_GATE_INITIAL_FAILED"); Qt.exit(43); return;
        }'''
    return '''//@ pragma IgnoreSystemSettings
import QtQml
import Quickshell
ShellRoot {
  id: test
  property int phase: 0
  property int createdCount: 0
  property int destroyedCount: 0
  property GuardedHost gate: GuardedHost {
    configurationText: %s
    reviewedCatalog: (%s)
    onObjectCreated: function(componentId, instance) {
      if (instance.initialized) test.createdCount++;
      instance.tearingDown.connect(function() { test.destroyedCount++; });
      %s
    }
  }
  Timer {
    id: checkTimer
    interval: 60
    running: true
    repeat: false
    onTriggered: {
      if (phase === 0) {
        %s
        %s
        phase = 1;
        checkTimer.restart();
        return;
      }
      var actual = {state: gate.state, attempts: gate.loadAttempts, created: test.createdCount,
                    destroyed: test.destroyedCount, active: gate.activeCount, reason: gate.reason};
      var expected = %s;
      var keys = Object.keys(expected);
      for (var i = 0; i < keys.length; i++) {
        if (actual[keys[i]] !== expected[keys[i]]) {
          console.error("OMABUNTU_GATE_ASSERTION_FAILED", JSON.stringify(actual));
          Qt.exit(42); return;
        }
      }
      console.log("%s::%s", JSON.stringify(actual));
      Qt.quit();
    }
  }
}
''' % (json.dumps(case["text"]), json.dumps(case["catalog"]), hooks[case["hook"]],
       initial, actions[case["action"]], json.dumps(expected), MARKER, name)


def classify(case, returncode, output):
    marker = MARKER + "::" + case["name"]
    diagnostics = re.findall(r"^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b[^\n]*", output, re.MULTILINE)
    if "Configuration Loaded" not in output:
        return False
    if case["negative"]:
        return (returncode == 42 and marker not in output and len(diagnostics) == 1
                and re.match(r"\s*ERROR\b", diagnostics[0]) is not None
                and "OMABUNTU_GATE_ASSERTION_FAILED" in diagnostics[0])
    expected_warning = (case["name"] == "object-failure" and len(diagnostics) == 1
                        and re.match(r"\s*WARN\b", diagnostics[0]) is not None
                        and "Required property token was not initialized" in diagnostics[0])
    return (returncode == 0 and marker in output
            and "OMABUNTU_GATE_ASSERTION_FAILED" not in output
            and (not diagnostics or expected_warning)
            and "Failed to load configuration" not in output)


def run_checks(root, candidate):
    if shutil.which("bwrap") is None:
        raise builder.BuildError("Bubblewrap is required; no less-isolated fallback")
    build, runtime, evidence = runtime_check.verify_stage(root, candidate)
    sources = root / "config/shell"
    if (root / "config").is_symlink() or sources.is_symlink():
        raise builder.BuildError("Refusing linked gate source directories")
    contents = {}
    for name in SOURCES:
        path = sources / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 131072:
            raise builder.BuildError("Gate sources must be bounded regular project files")
        contents[name] = path.read_bytes()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output_dir = builder.private_directory(builder.private_directory(root / "work/shell-gate") / stamp)
    report_path = output_dir / "report.json"
    report = {"schema_version": 1, "status": "running", "build": str(build), "checks": [],
              "checker_sha256": builder.digest(Path(__file__)),
              "runtime_checker_sha256": builder.digest(root / "tools/check_runtime.py"),
              "limits": "Nonvisual authored fixtures only. No original shell/plugins, service objects, real bus, compositor, GPU, authentication or desktop acceptance.",
              "isolation": "Existing Bubblewrap runtime-probe namespaces; read-only runtime/fixtures, private HOME, no host session/network.",
              "crash_handler": "Disabled only in disposable diagnostics; compiled stage unchanged."}

    def save():
        report_path.write_text(json.dumps(report, indent=2) + "\n")

    save()
    try:
        for spec in CASES:
            case = builder.private_directory(output_dir / spec["name"])
            for name in ("probe", "home", "probe/components", "home/runtime", "home/config", "home/data", "home/state", "home/cache"):
                builder.private_directory(case / name)
            for name, data in contents.items():
                (case / "probe" / name).write_bytes(data)
            (case / "probe/fonts.conf").write_text('<fontconfig><dir>/usr/share/fonts</dir><cachedir>/home/probe/cache/fontconfig</cachedir></fontconfig>\n')
            (case / "probe/components/Allowed.qml").write_text('import QtQml\nQtObject {\n property bool initialized: false\n signal tearingDown()\n Component.onCompleted: initialized = true\n Component.onDestruction: tearingDown()\n}\n')
            (case / "probe/components/Required.qml").write_text('import QtQml\nQtObject { required property string token }\n')
            (case / "probe/shell.qml").write_text(probe_qml(spec["name"]))
            before = builder.artifact_manifest(case / "probe")
            command = runtime_check.sandbox_command(runtime, case, [
                runtime_check.PREFIX + "/bin/quickshell", "--no-color", "--no-detailed-logs", "--path", "/probe/shell.qml"])
            log = case / "output.log"
            check = {"name": spec["name"], "negative_control": spec["negative"], "command": command,
                     "probe_artifacts": before, "log": str(log.relative_to(output_dir)), "status": "running"}
            report["checks"].append(check)
            save()
            with log.open("x") as stream:
                try:
                    process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=20, check=False)
                    check["returncode"] = process.returncode
                except subprocess.TimeoutExpired:
                    check.update(returncode=None, timed_out=True)
            text = log.read_text(errors="replace")
            check["log_sha256"] = builder.digest(log)
            check["diagnostics"] = {level: len(re.findall(r"^\s*" + level + r"\b", text, re.MULTILINE))
                                    for level in ("WARN", "ERROR", "FATAL", "CRITICAL")}
            check["inputs_unchanged"] = builder.artifact_manifest(case / "probe") == before
            check["status"] = "passed" if check["inputs_unchanged"] and classify(spec, check["returncode"], text) else "failed"
            save()
            if check["status"] != "passed":
                raise builder.BuildError("Gate fixture failed: " + spec["name"])
        report["status"] = "isolated-gate-fixtures-passed"
    except (OSError, ValueError, builder.BuildError) as error:
        report.update(status="failed", error=str(error))
    report["stage_unchanged"] = builder.artifact_manifest(build / "stage") == evidence["artifacts"]
    if not report["stage_unchanged"]:
        report.update(status="failed", error="Stage changed during gate checks")
    save()
    print(f"Private gate check: {report_path}", flush=True)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Run fixed authored fixtures in the isolated runtime")
    parser.add_argument("--build-dir", type=Path)
    args = parser.parse_args(argv)
    if not args.run:
        print(f"Plan only: {len(CASES)} fixed nonvisual gate cases. No files, processes or desktop changes.")
        print("After approval: python3 tools/check_shell_gate.py --run --build-dir work/builds/<timestamp>")
        return 0
    if args.build_dir is None:
        parser.error("--run requires --build-dir")
    os.umask(0o077)
    try:
        report = run_checks(ROOT, args.build_dir)
    except (OSError, ValueError, builder.BuildError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0 if report["status"] == "isolated-gate-fixtures-passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
