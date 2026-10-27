"""Synthetic diagnostics tests; no real desktop or package commands are run."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("omabuntu", ROOT / "tools" / "omabuntu.py")
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)


class ProbeTests(unittest.TestCase):
    def test_success_and_safe_arguments(self):
        completed = subprocess.CompletedProcess(["example"], 0, "version", "")
        with patch.object(doctor.subprocess, "run", return_value=completed) as run:
            result = doctor.probe(["example", "--version"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["stdout"], "version")
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(run.call_args.kwargs["timeout"], 15)

    def test_failed_command_preserves_evidence(self):
        completed = subprocess.CompletedProcess(["example"], 2, "partial", "failure")
        with patch.object(doctor.subprocess, "run", return_value=completed):
            result = doctor.probe(["example"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["returncode"], 2)
        self.assertEqual(result["stdout"], "partial")

    def test_missing_command(self):
        with patch.object(doctor.subprocess, "run", side_effect=FileNotFoundError()):
            self.assertEqual(doctor.probe(["absent"])["status"], "missing")

    def test_timeout_is_serializable(self):
        error = subprocess.TimeoutExpired(["example"], 15, output=b"partial")
        with patch.object(doctor.subprocess, "run", side_effect=error):
            result = doctor.probe(["example"])
        self.assertEqual(result["status"], "timeout")
        json.dumps(result)

    def test_permission_error(self):
        with patch.object(doctor.subprocess, "run", side_effect=PermissionError("denied")):
            self.assertEqual(doctor.probe(["example"])["status"], "error")

    def test_invalid_utf8_output(self):
        # Only a local Python child is run, not a desktop or package command.
        result = doctor.probe([sys.executable, "-c", "import os; os.write(1, bytes([255]))"])
        self.assertEqual(result["status"], "ok")
        self.assertIn("\ufffd", result["stdout"])


class CollectionTests(unittest.TestCase):
    def collect_with_environment(self, environment):
        with patch.dict(os.environ, environment, clear=True), \
             patch.object(doctor, "probe", return_value={"status": "ok"}) as probe, \
             patch.object(doctor, "read_os_release", return_value={"status": "ok", "values": {}}), \
             patch.object(doctor.shutil, "which", return_value=None):
            report = doctor.collect()
        return report, [call.args[0] for call in probe.call_args_list]

    def test_gnome_does_not_query_hyprland(self):
        report, commands = self.collect_with_environment({"XDG_CURRENT_DESKTOP": "GNOME"})
        self.assertEqual(report["probes"]["hyprland_version"]["status"], "skipped")
        self.assertFalse(any(command[0] == "hyprctl" for command in commands))
        self.assertEqual(
            {command[0] for command in commands}, {"dpkg-query", "apt-cache", "Hyprland"},
        )
        self.assertIn(["Hyprland", "--version-json"], commands)
        self.assertEqual(report["probes"]["hyprland_binary_version"]["status"], "ok")

    def test_hyprland_context_queries_only_read_only_endpoints(self):
        report, commands = self.collect_with_environment({"HYPRLAND_INSTANCE_SIGNATURE": "synthetic"})
        self.assertIn(["hyprctl", "version"], commands)
        self.assertIn(["hyprctl", "configerrors"], commands)
        self.assertNotIn("HYPRLAND_INSTANCE_SIGNATURE", json.dumps(report))
        self.assertNotIn(["hyprctl", "reload"], commands)

    def test_failed_binary_probe_does_not_hide_package_evidence(self):
        def fail_binary(args):
            return {"status": "missing" if args[0] == "Hyprland" else "ok"}

        with patch.dict(os.environ, {}, clear=True), \
             patch.object(doctor, "probe", side_effect=fail_binary), \
             patch.object(doctor, "read_os_release", return_value={"status": "ok", "values": {}}), \
             patch.object(doctor.shutil, "which", return_value=None):
            report = doctor.collect()
        self.assertEqual(report["probes"]["hyprland_binary_version"]["status"], "missing")
        self.assertEqual(report["probes"]["packages"]["status"], "ok")

    def test_help_does_not_collect(self):
        with patch.object(doctor, "collect") as collect, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                doctor.main(["--help"])
        self.assertEqual(error.exception.code, 0)
        collect.assert_not_called()


class FileTests(unittest.TestCase):
    def setUp(self):
        # Keep all temporary artifacts inside the project workspace.
        work = ROOT / "work"
        work.mkdir(mode=0o700, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="tests-", dir=work)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_os_release_is_parsed_not_executed(self):
        source = self.root / "os-release"
        source.write_text('ID=ubuntu\nVERSION_ID="26.04"\nIGNORED=$(false)\n', encoding="utf-8")
        result = doctor.read_os_release(source)
        self.assertEqual(result["values"], {"ID": "ubuntu", "VERSION_ID": "26.04"})

    def test_missing_os_release(self):
        self.assertEqual(doctor.read_os_release(self.root / "absent")["status"], "error")

    def test_private_unique_reports(self):
        first = doctor.write_report({"example": True}, self.root)
        second = doctor.write_report({}, self.root)
        self.assertNotEqual(first, second)
        self.assertEqual(json.loads(first.read_text()), {"example": True})
        self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(first.parent.stat().st_mode), 0o700)
        self.assertFalse((self.root / "config").exists())

    def test_refuse_symlinked_work_directory(self):
        destination = self.root / "destination"
        destination.mkdir()
        (self.root / "work").symlink_to(destination, target_is_directory=True)
        with self.assertRaises(OSError):
            doctor.write_report({}, self.root)
        self.assertEqual(list(destination.iterdir()), [])

    def test_refuse_public_report_parent(self):
        work = self.root / "work"
        work.mkdir(mode=0o700)
        work.chmod(0o755)
        with self.assertRaises(OSError):
            doctor.write_report({}, self.root)


if __name__ == "__main__":
    unittest.main()
