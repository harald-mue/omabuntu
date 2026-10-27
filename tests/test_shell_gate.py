"""Gate probe contracts and public provenance; unit tests never launch Qt."""

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_shell_gate", ROOT / "tools/check_shell_gate.py")
checker = importlib.util.module_from_spec(SPEC)
with patch.object(sys, "path", [str(ROOT / "tools"), *sys.path]):
    SPEC.loader.exec_module(checker)


class ShellGateTests(unittest.TestCase):
    def case(self, name):
        return next(case for case in checker.CASES if case["name"] == name)

    def output(self, name):
        return "Configuration Loaded\n INFO qml: " + checker.MARKER + "::" + name + "\n"

    def test_default_is_plan_only(self):
        with patch.object(checker, "run_checks") as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(checker.main([]), 0)
        run.assert_not_called()

    def test_run_requires_build_directory(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            checker.main(["--run"])

    def test_rejects_arbitrary_probe_names(self):
        for name in ("../custom", "custom.qml", "", "omarchy-launch-shell"):
            with self.subTest(name=name), self.assertRaises(checker.builder.BuildError):
                checker.probe_qml(name)

    def test_fixed_names_and_nonvisual_qml(self):
        names = [case["name"] for case in checker.CASES]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertRegex(name, r"^[a-z][a-z0-9-]+$")
            qml = checker.probe_qml(name)
            self.assertIn("ShellRoot {", qml)
            self.assertIn("GuardedHost", qml)
            for forbidden in ("Process {", "Window {", "PamContext", "NotificationServer", "PolkitAgent", "import QtQuick"):
                self.assertNotIn(forbidden, qml)

    def test_all_ten_service_ids_have_negative_fixtures(self):
        self.assertEqual(len(checker.PROTECTED), 10)
        source = (ROOT / "config/shell/LoadPolicy.js").read_text()
        for component_id in checker.PROTECTED:
            case = self.case(component_id.replace(".", "-"))
            self.assertEqual(case["attempts"], 0)
            self.assertEqual(json.loads(case["text"])["components"], [component_id])
            self.assertIn(json.dumps(component_id), source)

    def test_lifecycle_and_snapshot_cases_are_present(self):
        for name in ("whole-plan-validation", "catalog-in-config", "reload-sticky", "invalid-reload-sticky",
                     "catalog-replacement", "reentrant-revocation", "catalog-snapshot",
                     "preparation-failure", "object-failure", "assertion-negative-control"):
            self.assertIsInstance(self.case(name), dict)
        self.assertEqual(self.case("reentrant-revocation")["attempts"], 1)
        self.assertEqual(self.case("preparation-failure")["destroyed"], 1)
        self.assertEqual(self.case("catalog-snapshot")["active"], 2)

    def test_shipped_host_has_no_original_startup_objects(self):
        source = (ROOT / "config/shell/GuardedHost.qml").read_text()
        self.assertIn("property var reviewedCatalog: ({})", source)
        self.assertIn('property string configurationText: ""', source)
        for forbidden in ("PluginRegistry", "AppLibrary", "BrightnessKeys", "BackgroundIntro", "Quickshell.Services", "Process {", "Timer {"):
            self.assertNotIn(forbidden, source)

    def test_classifier_requires_success_exit_marker_and_loaded_configuration(self):
        case = self.case("positive-widget")
        good = self.output(case["name"])
        self.assertTrue(checker.classify(case, 0, good))
        for code, output in ((-11, good), (None, good), (255, good), (0, ""),
                             (0, checker.MARKER + "::" + case["name"]),
                             (0, good + "\nFailed to load configuration")):
            self.assertFalse(checker.classify(case, code, output))

    def test_classifier_rejects_unexpected_diagnostics(self):
        case = self.case("positive-widget")
        for level in ("WARN", "ERROR", "FATAL", "CRITICAL"):
            self.assertFalse(checker.classify(case, 0, self.output(case["name"]) + level + " unrelated\n"))

    def test_only_specific_required_property_warning_is_accepted(self):
        case = self.case("object-failure")
        warning = "WARN: file:///probe/components/Required.qml:2:12: Required property token was not initialized\n"
        self.assertTrue(checker.classify(case, 0, self.output(case["name"]) + warning))
        self.assertFalse(checker.classify(case, 0, self.output(case["name"]) + warning + "WARN another error\n"))
        self.assertFalse(checker.classify(case, 0, self.output(case["name"]) + "WARN unrelated\n"))

    def test_negative_control_requires_specific_assertion_failure(self):
        case = self.case("assertion-negative-control")
        output = 'Configuration Loaded\n ERROR qml: OMABUNTU_GATE_ASSERTION_FAILED {"active":1}\n'
        self.assertTrue(checker.classify(case, 42, output))
        for code, value in ((0, output), (-11, output), (None, output), (42, ""),
                            (42, output + "ERROR unrelated\n"), (42, output + self.output(case["name"]))):
            self.assertFalse(checker.classify(case, code, value))

    def test_no_bubblewrap_means_no_fallback(self):
        with patch.object(checker.shutil, "which", return_value=None), \
                patch.object(checker.runtime_check, "verify_stage") as verify, \
                patch.object(checker.subprocess, "run") as run:
            with self.assertRaises(checker.builder.BuildError):
                checker.run_checks(ROOT, ROOT)
        verify.assert_not_called()
        run.assert_not_called()

    def test_stage_rejection_stops_before_any_process(self):
        with patch.object(checker.shutil, "which", return_value="bwrap"), \
                patch.object(checker.runtime_check, "verify_stage", side_effect=checker.builder.BuildError("changed stage")), \
                patch.object(checker.subprocess, "run") as run:
            with self.assertRaisesRegex(checker.builder.BuildError, "changed stage"):
                checker.run_checks(ROOT, ROOT)
        run.assert_not_called()

    def test_linked_gate_source_is_rejected_before_any_process(self):
        (ROOT / "work").mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "linked-sources").mkdir()
            (root / "config/shell").symlink_to(root / "linked-sources", target_is_directory=True)
            with patch.object(checker.shutil, "which", return_value="bwrap"), \
                    patch.object(checker.runtime_check, "verify_stage", return_value=(root, root, {})), \
                    patch.object(checker.subprocess, "run") as run:
                with self.assertRaisesRegex(checker.builder.BuildError, "linked gate"):
                    checker.run_checks(root, root)
            run.assert_not_called()
            self.assertFalse((root / "work/shell-gate").exists())

    def test_full_mit_notice_matches_pinned_provenance(self):
        data = json.loads((ROOT / "upstream/omarchy-source.json").read_text())
        self.assertRegex(data["commit"], r"^[0-9a-f]{40}$")
        license_record = data["license"]
        notice = (ROOT / license_record["notice_path"]).read_bytes()
        self.assertEqual(hashlib.sha256(notice).hexdigest(), license_record["sha256"])
        self.assertIn(data["commit"], license_record["url"])
        self.assertIn(b"Copyright (c) David Heinemeier Hansson", notice)
        self.assertIn(b"THE SOFTWARE IS PROVIDED", notice)
        self.assertEqual(data["reference_comparison"]["shell_entries"], 249)
        self.assertEqual(data["reference_comparison"]["shell_entries_matched"], 249)
        self.assertEqual(data["package_recipe"]["status"], "not-matched")


if __name__ == "__main__":
    unittest.main()
