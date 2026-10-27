"""Runtime-probe contracts using synthetic files; never start Qt or a host service."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_runtime", ROOT / "tools/check_runtime.py")
checker = importlib.util.module_from_spec(SPEC)
with patch.object(sys, "path", [str(ROOT / "tools"), *sys.path]):
    SPEC.loader.exec_module(checker)


class RuntimeCheckTests(unittest.TestCase):
    def setUp(self):
        work = ROOT / "work"
        work.mkdir(mode=0o700, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="runtime-tests-", dir=work)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.build = self.root / "work/builds/example"
        self.runtime = self.build / "stage" / checker.PREFIX.lstrip("/")
        (self.runtime / "bin").mkdir(parents=True)
        (self.runtime / "bin/quickshell").write_bytes(b"Synthetic executable; never run")
        self.report = {
            "status": "staged-with-warnings", "steps": [{"status": "passed"}],
            "source_lock": {}, "shaders": [{"path": "synthetic.qsb"}],
            "artifacts": checker.builder.artifact_manifest(self.build / "stage"),
        }
        self.save_report()

    def save_report(self):
        (self.build / "report.json").write_text(json.dumps(self.report))

    def verify(self):
        with patch.object(checker.builder, "load_inputs", return_value=({}, {})):
            return checker.verify_stage(self.root, self.build)

    def test_default_is_plan_only(self):
        with patch.object(checker, "run_checks") as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(checker.main([]), 0)
        run.assert_not_called()

    def test_run_requires_explicit_build_directory(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            checker.main(["--run"])

    def test_fixed_probes_are_nonvisual_and_do_not_use_service_objects(self):
        for module in checker.MODULES:
            qml = checker.qml_probe(module, checker.MARKER)
            self.assertIn("ShellRoot {", qml)
            self.assertIn("Qt.quit()", qml)
            for unsafe in ("Process {", "Window {", "PamContext {", "SessionLock {", "Notifications."):
                self.assertNotIn(unsafe, qml)

    def test_type_resolution_uses_nullable_properties_without_construction(self):
        self.assertTrue(set(checker.PROBE_TYPES).issubset(checker.MODULES))
        for module, type_name in checker.PROBE_TYPES.items():
            qml = checker.qml_probe(module, "SAFE_MARKER")
            self.assertIn(f"{type_name} typeProbe: null", qml)
            self.assertNotIn(f"{type_name} {{", qml.split("ShellRoot {", 1)[1])
            self.assertNotIn("createObject", qml)
        self.assertNotIn("typeProbe", checker.qml_probe("Quickshell.Services.Greetd", "SAFE_MARKER"))

    def test_arbitrary_imports_and_marker_injection_are_rejected(self):
        for module, marker in (("../../private", "OK"), ("Quickshell", 'OK\"); Process {')):
            with self.assertRaises(checker.builder.BuildError):
                checker.qml_probe(module, marker)

    def test_sandbox_has_only_one_project_local_writable_bind(self):
        case = self.root / "case"
        argv = checker.sandbox_command(self.runtime, case, ["/usr/bin/true"])
        self.assertIn("--unshare-all", argv)
        self.assertIn("--die-with-parent", argv)
        self.assertIn("--clearenv", argv)
        self.assertNotIn("--share-net", argv)
        binds = [argv[i + 1:i + 3] for i, arg in enumerate(argv) if arg == "--bind"]
        self.assertEqual(binds, [[str(case / "home"), "/home/probe"]])
        readonly = [argv[i + 1:i + 3] for i, arg in enumerate(argv) if arg == "--ro-bind"]
        self.assertIn([str(self.runtime), checker.PREFIX], readonly)
        self.assertIn([str(case / "probe"), "/probe"], readonly)
        self.assertFalse(any(source in ("/home", "/run", "/tmp", "/dev/dri") for source, _ in readonly))
        environment = {argv[i + 1]: argv[i + 2] for i, arg in enumerate(argv) if arg == "--setenv"}
        self.assertEqual(environment["QT_QPA_PLATFORM"], "offscreen")
        self.assertEqual(environment["QS_DISABLE_CRASH_HANDLER"], "1")
        for bus in ("DBUS_SYSTEM_BUS_ADDRESS", "DBUS_SESSION_BUS_ADDRESS"):
            self.assertTrue(environment[bus].startswith("unix:path=/nonexistent/"))
        for variable in ("DISPLAY", "WAYLAND_DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "LD_PRELOAD"):
            self.assertNotIn(variable, environment)

    def test_qml_success_requires_exit_marker_and_loaded_configuration(self):
        good = f"Configuration Loaded\n{checker.MARKER}"
        self.assertTrue(checker.classify_qml(0, good, checker.MARKER))
        for code, text in ((0, "Configuration Loaded"), (1, good), (None, good), (0, good + "\nundefined symbol"), (0, good + "\nERROR: Another issue")):
            self.assertFalse(checker.classify_qml(code, text, checker.MARKER))

    def test_negative_control_requires_specific_missing_import_not_crash_or_timeout(self):
        error = f'module "{checker.NEGATIVE_MODULE}" is not installed'
        self.assertTrue(checker.classify_qml(255, error, checker.MARKER, negative=True))
        for code, text in ((0, error), (None, error), (-11, error), (139, error), (1, error), (255, "other failure"), (255, error + checker.MARKER)):
            self.assertFalse(checker.classify_qml(code, text, checker.MARKER, negative=True))

    def test_verified_stage_matches_recorded_files(self):
        self.assertEqual(self.verify()[1], self.runtime)

    def test_modified_runtime_is_rejected_before_execution(self):
        (self.runtime / "bin/quickshell").write_bytes(b"changed")
        with self.assertRaisesRegex(checker.builder.BuildError, "differ"):
            self.verify()

    def test_build_outside_expected_parent_is_rejected(self):
        with self.assertRaisesRegex(checker.builder.BuildError, "direct build directory"):
            checker.verify_stage(self.root, self.root)

    def test_symlinked_build_is_rejected(self):
        alias = self.build.parent / "alias"
        alias.symlink_to(self.build, target_is_directory=True)
        with self.assertRaisesRegex(checker.builder.BuildError, "symlinked build"):
            checker.verify_stage(self.root, alias)

    def test_failed_build_step_is_rejected(self):
        self.report["steps"][0]["status"] = "failed"
        self.save_report()
        with self.assertRaisesRegex(checker.builder.BuildError, "steps"):
            self.verify()

    def test_reassessment_must_reference_original_report_hash(self):
        evidence = dict(self.report, original_report_sha256="incorrect")
        self.report["status"] = "failed"
        self.save_report()
        (self.build / "assessment.json").write_text(json.dumps(evidence))
        with self.assertRaisesRegex(checker.builder.BuildError, "original report"):
            self.verify()
        evidence["original_report_sha256"] = checker.builder.digest(self.build / "report.json")
        (self.build / "assessment.json").write_text(json.dumps(evidence))
        self.assertEqual(self.verify()[1], self.runtime)

    def test_preflight_timeout_is_recorded_and_stops_without_fallback(self):
        with patch.object(checker.shutil, "which", return_value="/usr/bin/tool"), \
             patch.object(checker, "verify_stage", return_value=(self.build, self.runtime, self.report)), \
             patch.object(checker.subprocess, "run", side_effect=subprocess.TimeoutExpired(["bwrap"], 20)) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            result = checker.run_checks(self.root, self.build)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["checks"][0]["status"], "timeout")
        self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
