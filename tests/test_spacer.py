"""Sealed-spacer provenance/probe contracts; unit tests never start Qt."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_spacer", ROOT / "tools/check_spacer.py")
checker = importlib.util.module_from_spec(SPEC)
with patch.object(sys, "path", [str(ROOT / "tools"), *sys.path]):
    SPEC.loader.exec_module(checker)


class SpacerTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "work").mkdir(mode=0o700, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "work")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        names = ["upstream/omarchy-source.json", "upstream/spacer-candidate.json",
                 "licenses/Omarchy-MIT.txt", "vendor/omarchy/LICENSE", *checker.AUTHORED.values(),
                 *("vendor/omarchy/" + source for source in checker.ORIGINALS.values())]
        for name in names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)

    def case(self, name):
        return next(case for case in checker.CASES if case["name"] == name)

    def output(self, case):
        return ("Configuration Loaded\n" + (checker.TRIPWIRE + "\n") * case["touches"]
                + checker.MARKER + "::" + case["name"] + " " + json.dumps(case["expected"]) + "\n")

    def test_default_plan_does_not_run(self):
        with patch.object(checker, "run_checks") as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(checker.main([]), 0)
        run.assert_not_called()

    def test_run_requires_build(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            checker.main(["--run"])

    def test_sealed_sources_and_unchanged_upstream_bytes(self):
        files, meta = checker.verified_sources(self.root)
        self.assertEqual(set(files), set(checker.ORIGINALS) | set(checker.AUTHORED) | set(checker.MAPS) | {"LICENSE"})
        for target, source in checker.ORIGINALS.items():
            self.assertEqual(files[target], (ROOT / "vendor/omarchy" / source).read_bytes())
            self.assertNotIn(checker.TRIPWIRE.encode(), files[target])
        self.assertIn(checker.TRIPWIRE.encode(), files["Commons/Style.qml"])
        self.assertEqual(meta["production_catalog"], "empty")

    def test_changed_original_rejected(self):
        (self.root / "vendor/omarchy/shell/Ui/BarWidget.qml").write_text("changed")
        with self.assertRaisesRegex(checker.builder.BuildError, "bytes changed"):
            checker.verified_sources(self.root)

    def test_changed_authored_adapter_rejected(self):
        (self.root / "config/shell/PassiveStyle.qml").write_text("changed")
        with self.assertRaisesRegex(checker.builder.BuildError, "passive profile differs"):
            checker.verified_sources(self.root)

    def test_changed_notice_rejected(self):
        (self.root / "vendor/omarchy/LICENSE").write_text("incomplete MIT")
        with self.assertRaisesRegex(checker.builder.BuildError, "notice differs"):
            checker.verified_sources(self.root)

    def test_linked_source_rejected(self):
        path = self.root / "config/shell/PassiveStyle.qml"
        path.unlink()
        path.symlink_to(ROOT / "config/shell/PassiveStyle.qml")
        with self.assertRaisesRegex(checker.builder.BuildError, "symlink"):
            checker.verified_sources(self.root)

    def test_module_and_scope_expansion_rejected(self):
        path = self.root / "upstream/spacer-candidate.json"
        original = json.loads(path.read_text())
        for kind in ("module", "scope", "original", "authored", "catalog"):
            data = copy.deepcopy(original)
            if kind == "module": data["module_maps"]["Commons/qmldir"] += "InputDevices 1.0 InputDevices.qml\n"
            elif kind == "scope": data["scope"] = "full-shell"
            elif kind == "original": data["originals"]["Extra.qml"] = {}
            elif kind == "authored": data["authored"]["Extra.qml"] = {}
            else: data["production_catalog"] = "enabled"
            path.write_text(json.dumps(data))
            with self.subTest(kind=kind), self.assertRaises(checker.builder.BuildError):
                checker.verified_sources(self.root)

    def test_no_probe_watcher_command_or_window_in_authored_profile(self):
        for name in checker.AUTHORED.values():
            text = (ROOT / name).read_text()
            for forbidden in ("Process {", "FileView", "watchChanges", "execDetached", "Quickshell", "Window {", "Timer {"):
                self.assertNotIn(forbidden, text)

    def test_fixed_probe_names_and_no_window_construction(self):
        names = [case["name"] for case in checker.CASES]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            text = checker.qml_probe(name)
            for forbidden in ("Window {", "Process {", "FileView", "Quickshell.Services", "PanelWindow"):
                self.assertNotIn(forbidden, text)
        with self.assertRaises(checker.builder.BuildError):
            checker.qml_probe("arbitrary")

    def test_classifier_exact_metrics_exit_and_loaded_configuration(self):
        case = self.case("horizontal")
        output = self.output(case)
        self.assertTrue(checker.classify(case, 0, output))
        for code, text in ((None, output), (-11, output), (255, output), (0, ""),
                           (0, output.replace("Configuration Loaded", "")), (0, output + output),
                           (0, output.replace('[12, 32, true]', '[12, 32, 1]')),
                           (0, output.replace('"created": 1', '"created": true'))):
            self.assertFalse(checker.classify(case, code, text))

    def test_unexpected_diagnostics_or_style_activation_fail(self):
        case = self.case("horizontal")
        output = self.output(case)
        for line in ("WARN unexpected", "ERROR unrelated", "FATAL failure", "CRITICAL failure", checker.TRIPWIRE):
            self.assertFalse(checker.classify(case, 0, output + line))

    def test_late_injection_requires_tripwire_control(self):
        case = self.case("late-injection-control")
        output = self.output(case)
        self.assertTrue(checker.classify(case, 0, output))
        self.assertFalse(checker.classify(case, 0, output.replace(checker.TRIPWIRE, "")))

    def test_negative_assertion_requires_specific_failure(self):
        case = self.case("assertion-negative-control")
        output = "Configuration Loaded\nERROR qml: OMABUNTU_SPACER_ASSERTION_FAILED deliberate geometry mismatch\n"
        self.assertTrue(checker.classify(case, 42, output))
        for code, text in ((0, output), (None, output), (-11, output), (42, output + "WARN unrelated\n"),
                           (42, output.replace("deliberate geometry mismatch", "other failure")),
                           (42, output + checker.MARKER)):
            self.assertFalse(checker.classify(case, code, text))

    def test_invalid_config_cases_never_expect_construction(self):
        for name in ("missing", "invalid-json", "null", "legacy-config", "wrong-bool", "wrong-schema",
                     "bar-zero", "bar-oversized", "fractional", "negative-size", "oversized-size",
                     "extra-command", "oversized-input", "invalid-api"):
            case = self.case(name)
            self.assertEqual(case["expected"]["created"], 0)
            self.assertEqual(case["expected"]["attempts"], 0)
            self.assertEqual(case["touches"], 0)

    def test_missing_bubblewrap_refuses_without_fallback(self):
        with patch.object(checker.shutil, "which", return_value=None), patch.object(checker.subprocess, "run") as run:
            with self.assertRaises(checker.builder.BuildError):
                checker.run_checks(self.root, self.root)
        run.assert_not_called()

    def test_bad_source_stops_before_stage_or_process(self):
        (self.root / "config/shell/PassiveStyle.qml").write_text("changed")
        with patch.object(checker.shutil, "which", return_value="bwrap"), \
                patch.object(checker.check_runtime, "verify_stage") as verify, patch.object(checker.subprocess, "run") as run:
            with self.assertRaises(checker.builder.BuildError):
                checker.run_checks(self.root, self.root)
        verify.assert_not_called()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
