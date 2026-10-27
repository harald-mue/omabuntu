#!/usr/bin/env python3
"""Plan or run fixed original clock-math tests in isolated Qt; never its UI/plugin."""

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
MODEL = "vendor/omarchy/shell/plugins/panels/clock/Model.js"
SOURCE = "shell/plugins/panels/clock/Model.js"
CASES = (("utc", "UTC", 0, False), ("berlin", "Europe/Berlin", -60, False),
         ("havana", "America/Havana", 300, False), ("santiago", "America/Santiago", 180, False),
         ("negative-control", "UTC", 0, True))
MARKER = "OMABUNTU_CLOCK_OK"
ASSERTIONS = 221


def verified_model(root):
    """Only the fixed reviewed file and complete notices; no arbitrary paths."""
    metadata = json.loads(audit_widgets.bounded(root, "upstream/widget-candidates.json"))
    pin = json.loads(audit_widgets.bounded(root, "upstream/omarchy-source.json"))
    if (not isinstance(metadata, dict) or not isinstance(pin, dict)
            or pin.get("repository") != "https://github.com/omacom/omarchy"
            or not isinstance(pin.get("commit"), str) or not re.fullmatch(r"[0-9a-f]{40}", pin["commit"])
            or not isinstance(pin.get("license"), dict) or pin["license"].get("spdx") != "MIT"
            or not isinstance(pin["license"].get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", pin["license"]["sha256"])):
        raise builder.BuildError("Invalid pinned source/license metadata")
    if (type(metadata.get("schema_version")) is not int or metadata["schema_version"] != 1
            or metadata.get("source") != {"repository": pin["repository"], "commit": pin["commit"]}
            or not isinstance(metadata.get("imports"), list) or len(metadata["imports"]) != 1):
        raise builder.BuildError("Require the single reviewed original clock model")
    record = metadata["imports"][0]
    url = "https://raw.githubusercontent.com/omacom/omarchy/" + pin["commit"] + "/" + SOURCE
    if (not isinstance(record, dict) or record.get("vendor_path") != MODEL or record.get("path") != SOURCE
            or record.get("url") != url or record.get("commit") != pin["commit"]
            or record.get("repository") != pin["repository"] or record.get("license") != "MIT"
            or record.get("approved_scope") != "pure-date-and-format-functions-only"
            or record.get("dependency_files") != [] or record.get("modifications") != []
            or record.get("notice_paths") != ["licenses/Omarchy-MIT.txt", "vendor/omarchy/LICENSE"]):
        raise builder.BuildError("Model provenance/review scope differs")
    data = audit_widgets.bounded(root, MODEL, 65536)
    blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if (hashlib.sha256(data).hexdigest() != record.get("sha256") or blob != record.get("git_blob_sha1")
            or len(data) != record.get("bytes")):
        raise builder.BuildError("Original clock model bytes changed")
    for name in ("licenses/Omarchy-MIT.txt", "vendor/omarchy/LICENSE"):
        notice = audit_widgets.bounded(root, name, 8192)
        if hashlib.sha256(notice).hexdigest() != pin["license"]["sha256"]:
            raise builder.BuildError("Complete upstream MIT notice differs")
    return data, record


def qml_probe(name):
    spec = next((case for case in CASES if case[0] == name), None)
    if spec is None:
        raise builder.BuildError("Only fixed clock-math cases are accepted")
    return '''//@ pragma IgnoreSystemSettings
import QtQml
import Quickshell
import "Model.js" as Model
ShellRoot {
  id: test
  property int assertions: 0
  property string failure: ""
  function equal(actual, expected, label) {
    assertions++;
    if (JSON.stringify(actual) !== JSON.stringify(expected) && failure === "") failure = label;
  }
  function grid(year, month, first, last, today) {
    var rows = Model.monthGrid(year, month, 1, today);
    equal(rows.length, 6, "six rows");
    var keys = [];
    var marked = 0;
    var previous = null;
    for (var i = 0; i < rows.length; i++) {
      equal(rows[i].days.length, 7, "seven days");
      for (var j = 0; j < rows[i].days.length; j++) {
        var cell = rows[i].days[j];
        var stamp = Date.UTC(cell.year, cell.month, cell.day);
        equal(keys.indexOf(cell.key), -1, "unique civil date");
        if (previous !== null) equal(stamp - previous, 86400000, "continuous UTC grid");
        previous = stamp;
        keys.push(cell.key);
        if (cell.today) marked++;
      }
    }
    equal(keys[0], first, "first grid date");
    equal(keys[41], last, "last grid date");
    equal(marked, 1, "single today marker");
  }
  function runChecks() {
    equal(new Date(2024, 0, 15, 12).getTimezoneOffset(), %d, "timezone actually selected");
    equal(Model.dateKey(2024, 1, 9), "2024-02-09", "date identity");
    equal(Model.keyForDate(new Date(2024, 1, 9, 12)), "2024-02-09", "local date identity");
    equal(Model.isoWeek(2021, 0, 1), 53, "ISO previous year");
    equal(Model.isoWeek(2021, 0, 4), 1, "ISO first Monday");
    equal(Model.isoWeekLiteral(2021, 0, 4), "01", "padded ISO week");
    equal(Model.daysInYear(2024), 366, "leap year");
    equal(Model.daysInYear(2025), 365, "ordinary year");
    equal(Model.dayOfYear(2024, 1, 29), 60, "leap day");
    equal(Model.yearProgress(2026, 0, 1), 0, "start of year");
    equal(Model.yearProgressPercent(2026, 11, 31), 100, "rounded last-day percent");
    equal(Model.normalizedWeekStart("sun", 1), 0, "named week start");
    equal(Model.normalizedWeekStart("invalid", 1), 1, "week start fallback");
    equal(Model.normalizedWeekStart(-1, 1), 6, "negative week start");
    equal(Model.weekStartSettingName(1), "monday", "persistable week start name");
    equal(Model.toggledWeekStart(6), 1, "nonstandard start toggles to Monday");
    equal(Model.weekdayOrder(0), [0,1,2,3,4,5,6], "Sunday order");
    equal(Model.clockNeedsSeconds("HH:mm:ss"), true, "seconds format");
    equal(Model.clockNeedsSeconds("'seconds' HH:mm"), false, "quoted seconds literal");
    equal(Model.clockNeedsSeconds(undefined), false, "missing format");
    equal(Model.clockFormatRing("HH:mm", "HH:mm", ["HH:mm", "dddd HH:mm"]),
          ["HH:mm", "dddd HH:mm"], "stable deduplicated ring");
    equal(Model.clockFormatRing("", "", []), ["HH:mm"], "empty ring fallback");
    equal(Model.nextClockFormat(["a", "b"], "b"), "a", "ring wrap");
    equal(Model.nextClockFormat(["a", "b"], "unknown"), "a", "unknown format");
    equal(Model.nextClockFormat([], "a"), "", "no next format");
    var formats = Model.clockFormats(false);
    formats[0] = "changed";
    equal(Model.clockFormats(false)[0], "dddd HH:mm", "presets are detached");
    equal(Model.clockFormats(true)[0], "HH\\n—\\nmm", "original vertical preset");
    equal(Model.parseBirthYear("2030", 2026), 0, "future birth year rejected");
    equal(Model.ageFromBirthYear(1979, 2026), 47, "upstream example age");
    equal(Model.parseAge("3.5"), 0, "fractional age rejected");
    equal(Model.parseLifeExpectancy("invalid"), 90, "default expectancy");
    equal(Model.lifeProgressPercent(45, 90), 50, "life percentage");
    equal(Model.lifeProgress(120, 90), 1, "life percentage clamp");
    equal(Model.stepMonth(2023, 11, 1), {year:2024, month:0}, "forward year boundary");
    equal(Model.stepMonth(2024, 0, -1), {year:2023, month:11}, "backward year boundary");
    grid(2012, 3, "2012-03-26", "2012-05-06", "2012-04-01");
    grid(2019, 8, "2019-08-26", "2019-10-06", "2019-09-08");
    if (%s) equal(Model.isoWeek(2021, 0, 1), 1, "deliberate ISO-week mismatch");
    if (failure !== "") {
      console.error("OMABUNTU_CLOCK_ASSERTION_FAILED", failure);
      Qt.exit(42); return;
    }
    console.log("%s::%s", JSON.stringify({assertions: assertions, timezone: %s}));
    Qt.quit();
  }
  Timer {
    interval: 1
    running: true
    repeat: false
    onTriggered: {
      try { test.runChecks(); }
      catch (error) { console.error("OMABUNTU_CLOCK_EXCEPTION", String(error)); Qt.exit(43); }
    }
  }
}
''' % (spec[2], "true" if spec[3] else "false", MARKER, name, json.dumps(spec[1]))


def metrics(spec, output):
    matches = re.findall(re.escape(MARKER + "::" + spec[0]) + r" (\{[^\n]+\})", output)
    if len(matches) != 1:
        return None
    try:
        value = json.loads(matches[0])
    except ValueError:
        return None
    return value if value == {"assertions": ASSERTIONS, "timezone": spec[1]} else None


def classify(spec, code, output):
    diagnostics = re.findall(r"^\s*(?:WARN|ERROR|FATAL|CRITICAL)\b[^\n]*", output, re.MULTILINE)
    marker = MARKER + "::" + spec[0]
    if "Configuration Loaded" not in output:
        return False
    if spec[3]:
        return (code == 42 and MARKER not in output and len(diagnostics) == 1
                and re.match(r"\s*ERROR\b", diagnostics[0]) is not None
                and "OMABUNTU_CLOCK_ASSERTION_FAILED deliberate ISO-week mismatch" in diagnostics[0])
    return (code == 0 and marker in output and metrics(spec, output) is not None
            and not diagnostics and "Failed to load configuration" not in output)


def run_checks(root, candidate):
    if shutil.which("bwrap") is None:
        raise builder.BuildError("Bubblewrap required; no less-isolated fallback")
    data, origin = verified_model(root)
    build, runtime, evidence = check_runtime.verify_stage(root, candidate)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = builder.private_directory(builder.private_directory(root / "work/clock-model") / stamp)
    path = directory / "report.json"
    report = {"schema_version": 1, "status": "running", "checks": [], "build": str(build), "model": origin,
              "checker_sha256": builder.digest(Path(__file__)),
              "runtime_checker_sha256": builder.digest(root / "tools/check_runtime.py"),
              "audit_widgets_sha256": builder.digest(root / "tools/audit_widgets.py"),
              "model_provenance_sha256": builder.digest(root / "upstream/widget-candidates.json"),
              "source_metadata_sha256": builder.digest(root / "upstream/omarchy-source.json"),
              "limits": "Pure original date/format functions only; no original QML/plugin/widget/clock object, UI, IPC, service, host session or auth acceptance.",
              "isolation": "Existing Bubblewrap runtime checks; read-only runtime/probes, private HOME, no real bus/display/compositor/GPU/network. Crash handler disabled for disposable diagnostics only."}

    def save():
        path.write_text(json.dumps(report, indent=2) + "\n")

    save()
    try:
        for spec in CASES:
            case = builder.private_directory(directory / spec[0])
            for child in ("probe", "home", "home/runtime", "home/config", "home/data", "home/state", "home/cache"):
                builder.private_directory(case / child)
            (case / "probe/Model.js").write_bytes(data)
            (case / "probe/LICENSE").write_bytes(audit_widgets.bounded(root, "vendor/omarchy/LICENSE", 8192))
            (case / "probe/shell.qml").write_text(qml_probe(spec[0]))
            (case / "probe/fonts.conf").write_text('<fontconfig><dir>/usr/share/fonts</dir><cachedir>/home/probe/cache/fontconfig</cachedir></fontconfig>\n')
            before = builder.artifact_manifest(case / "probe")
            command = check_runtime.sandbox_command(runtime, case, [check_runtime.PREFIX + "/bin/quickshell", "--no-color", "--no-detailed-logs", "--path", "/probe/shell.qml"])
            offset = command.index("--chdir")
            command[offset:offset] = ["--setenv", "TZ", spec[1]]
            log = case / "output.log"
            check = {"name": spec[0], "timezone": spec[1], "negative_control": spec[3], "command": command,
                     "probe_artifacts": before, "log": str(log.relative_to(directory)), "status": "running"}
            report["checks"].append(check)
            save()
            with log.open("x") as stream:
                try:
                    result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=20, check=False)
                    check["returncode"] = result.returncode
                except subprocess.TimeoutExpired:
                    check.update(returncode=None, timed_out=True)
            text = log.read_text(errors="replace")
            check["log_sha256"] = builder.digest(log)
            check["metrics"] = metrics(spec, text)
            check["diagnostics"] = {level: len(re.findall(r"^\s*" + level + r"\b", text, re.MULTILINE))
                                    for level in ("WARN", "ERROR", "FATAL", "CRITICAL")}
            check["inputs_unchanged"] = builder.artifact_manifest(case / "probe") == before
            check["status"] = "passed" if check["inputs_unchanged"] and classify(spec, check["returncode"], text) else "failed"
            save()
            if check["status"] != "passed":
                raise builder.BuildError("Clock-model check failed: " + spec[0])
        report["status"] = "isolated-clock-math-passed"
    except (OSError, ValueError, builder.BuildError) as error:
        report.update(status="failed", error=str(error))
    report["stage_unchanged"] = builder.artifact_manifest(build / "stage") == evidence["artifacts"]
    if not report["stage_unchanged"]:
        report.update(status="failed", error="Stage changed during clock checks")
    save()
    print(f"Private clock-model check: {path}")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--build-dir", type=Path)
    args = parser.parse_args(argv)
    if not args.run:
        print("Plan only: four Qt timezone cases plus one assertion-negative control. No files/processes/desktop changes.")
        return 0
    if args.build_dir is None:
        parser.error("--run requires --build-dir")
    os.umask(0o077)
    try:
        report = run_checks(ROOT, args.build_dir)
    except (OSError, ValueError, builder.BuildError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0 if report["status"] == "isolated-clock-math-passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
