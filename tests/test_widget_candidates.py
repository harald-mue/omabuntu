"""Synthetic dependency/provenance contracts; unit tests never execute JS or Qt."""

import contextlib
import copy
import hashlib
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
with patch.object(sys, "path", [str(ROOT / "tools"), *sys.path]):
    def load(name):
        spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    audit = load("audit_widgets")
    clock = load("check_clock_model")


class WidgetAuditTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "work").mkdir(mode=0o700, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "work")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ref = self.root / "reference"
        self.shell = self.ref / audit.audit_shell.SHELL
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        self.files = {
            "Commons/qmldir": "module qs.Commons\nsingleton Style 1.0 Style.qml\n",
            "Commons/Style.qml": "pragma Singleton\nimport QtQml\nQtObject {}\n",
            "Ui/qmldir": "module qs.Ui\nBarWidget 1.0 BarWidget.qml\n",
            "Ui/BarWidget.qml": "import QtQuick\nimport qs.Commons\nItem { property int size: Style.size }\n",
            "plugins/bar/Bar.qml": "import QtQuick\nimport qs.Ui\nItem {}\n",
            "plugins/panels/clock/BarWidget.qml": 'import qs.Ui\nimport "Model.js" as Model\nBarWidget {}\n',
            "plugins/panels/clock/Model.js": "function example() { return 1; }\n",
            "plugins/bar/widgets/Spacer.qml": "import qs.Ui\nBarWidget {}\n",
        }
        self.pin = json.loads((ROOT / "upstream/omarchy-source.json").read_text())
        (self.root / "upstream").mkdir()
        (self.root / "upstream/omarchy-source.json").write_text(json.dumps(self.pin))
        self.save()

    def save(self):
        entries = []
        for name, text in self.files.items():
            path = self.shell / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            data = text.encode()
            digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            entries.append({"path": "shell/" + name, "type": "blob", "mode": "100644", "sha": digest})
        self.save_tree({"truncated": False, "tree": entries})

    def save_tree(self, tree):
        data = json.dumps(tree).encode()
        (self.evidence / "source-tree.json").write_bytes(data)
        (self.evidence / "source-provenance.json").write_text(json.dumps({
            "repository": self.pin["repository"], "commit": self.pin["commit"],
            "tree_url": "https://api.github.com/repos/omacom/omarchy/git/trees/" + self.pin["commit"] + "?recursive=1",
            "tree_response_sha256": hashlib.sha256(data).hexdigest(),
        }))

    def run_audit(self):
        return audit.audit(self.ref, self.evidence, self.root)

    def test_pinned_base_and_local_js_closure(self):
        result = self.run_audit()
        self.assertIn("Commons/Style.qml", result["closures"]["spacer"])
        self.assertIn("Ui/BarWidget.qml", result["closures"]["clock"])
        self.assertIn("plugins/panels/clock/Model.js", result["closures"]["clock"])
        self.assertNotIn("plugins/panels/clock/Model.js", result["closures"]["spacer"])
        self.assertIn("not-load-approval", result["status"])

    def test_no_reference_execution_or_network(self):
        with patch("subprocess.run") as run, patch("urllib.request.urlopen") as network:
            self.run_audit()
        run.assert_not_called()
        network.assert_not_called()

    def test_changed_reference_bytes_rejected(self):
        (self.shell / "Ui/BarWidget.qml").write_text("changed")
        with self.assertRaisesRegex(audit.builder.BuildError, "differs from pinned"):
            self.run_audit()

    def test_tree_digest_mismatch_rejected(self):
        with (self.evidence / "source-tree.json").open("a") as stream:
            stream.write(" ")
        with self.assertRaisesRegex(audit.builder.BuildError, "does not bind"):
            self.run_audit()

    def test_wrong_commit_rejected(self):
        p = self.evidence / "source-provenance.json"
        value = json.loads(p.read_text())
        value["commit"] = "0" * 40
        p.write_text(json.dumps(value))
        with self.assertRaises(audit.builder.BuildError):
            self.run_audit()

    def test_truncated_duplicate_and_malformed_tree_rejected(self):
        tree = json.loads((self.evidence / "source-tree.json").read_text())
        variants = [dict(tree, truncated=True), dict(tree, tree=[*tree["tree"], tree["tree"][0]]),
                    dict(tree, tree=[42]), dict(tree, tree=[{"path": "../escape"}])]
        for value in variants:
            with self.subTest(value=value):
                self.save_tree(value)
                with self.assertRaises(audit.builder.BuildError):
                    self.run_audit()

    def test_linked_reference_and_evidence_rejected(self):
        for name, target in (("linked-reference", self.ref), ("linked-evidence", self.evidence)):
            link = self.root / name
            link.symlink_to(target, target_is_directory=True)
            with self.subTest(name=name), self.assertRaises(audit.builder.BuildError):
                audit.audit(link if target == self.ref else self.ref,
                            link if target == self.evidence else self.evidence, self.root)

    def test_linked_source_rejected(self):
        target = self.shell / "Commons/Style.qml"
        target.unlink()
        replacement = self.root / "passive-file"
        replacement.write_text(self.files["Commons/Style.qml"])
        target.symlink_to(replacement)
        with self.assertRaisesRegex(audit.builder.BuildError, "symlink"):
            self.run_audit()

    def test_oversized_source_rejected(self):
        (self.shell / "Commons/Style.qml").write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        with self.assertRaisesRegex(audit.builder.BuildError, "bounded regular"):
            self.run_audit()

    def test_unsupported_missing_and_traversing_module_exports_rejected(self):
        for text in ("module qs.Ui\nplugin foreign\n", "module qs.Ui\nMissing 1.0 Missing.qml\n",
                     "module qs.Ui\nEscape 1.0 ../../../escape.qml\n", "module wrong.name\n",
                     "BarWidget 1.0 BarWidget.qml\n"):
            with self.subTest(text=text), self.assertRaises(audit.builder.BuildError):
                audit.parse_exports(text, "Ui", {"Ui/BarWidget.qml": "unused"})

    def test_missing_explicit_import_rejected(self):
        self.files["plugins/panels/clock/BarWidget.qml"] = 'import "Missing.js" as Missing\n'
        self.save()
        with self.assertRaisesRegex(audit.builder.BuildError, "Missing explicit"):
            self.run_audit()

    def test_qualified_import_and_literal_panel_edge(self):
        self.files["plugins/panels/clock/Panel.qml"] = "import QtQml\nQtObject {}\n"
        self.files["plugins/panels/clock/BarWidget.qml"] = ('import qs.Commons as Common\n'
            'import QtQuick\nItem { property int size: Common.Style.size; property url child: Qt.resolvedUrl("Panel.qml") }\n')
        self.save()
        result = self.run_audit()
        self.assertIn("Commons/Style.qml", result["closures"]["clock"])
        self.assertIn("plugins/panels/clock/Panel.qml", result["closures"]["clock"])

    def test_unknown_dynamic_source_recorded_not_followed(self):
        self.files["plugins/panels/clock/BarWidget.qml"] += '\n// "Unknown.qml"\n// Qt.createComponent(registryUrl)\n'
        self.save()
        record = next(x for x in self.run_audit()["files"] if x["path"] == audit.ENTRYPOINTS["clock"])
        self.assertEqual(record["unresolved_source_literals"], ["Unknown.qml"])
        self.assertTrue(record["dynamic_reference_lines"])

    def test_comment_refs_are_explicitly_conservative(self):
        self.files["plugins/bar/Bar.qml"] += "// BarWidget is a possible future widget.\n"
        self.save()
        self.assertIn("Ui/BarWidget.qml", self.run_audit()["closures"]["bar"])

    def test_local_paths_normalize_inside_root_but_reject_escape(self):
        self.assertEqual(audit.local_path("Ui", "../Commons/Style.qml"), "Commons/Style.qml")
        for value in ("../../escape.qml", "/absolute.qml", "file:///external.qml", "%2e%2e/escape.qml"):
            with self.subTest(value=value), self.assertRaises(audit.builder.BuildError):
                audit.local_path("Ui", value)


class ClockModelContracts(unittest.TestCase):
    def setUp(self):
        (ROOT / "work").mkdir(mode=0o700, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "work")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in (clock.MODEL, "upstream/omarchy-source.json", "upstream/widget-candidates.json",
                     "licenses/Omarchy-MIT.txt", "vendor/omarchy/LICENSE"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)

    def test_public_model_and_both_notices_match(self):
        data, record = clock.verified_model(self.root)
        self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])
        self.assertEqual(record["dependency_files"], [])

    def test_changed_model_refused(self):
        (self.root / clock.MODEL).write_text("changed")
        with self.assertRaisesRegex(clock.builder.BuildError, "bytes changed"):
            clock.verified_model(self.root)

    def test_changed_notice_refused(self):
        (self.root / "vendor/omarchy/LICENSE").write_text("MIT without full notice")
        with self.assertRaisesRegex(clock.builder.BuildError, "notice differs"):
            clock.verified_model(self.root)

    def test_scope_path_and_dependencies_cannot_expand(self):
        path = self.root / "upstream/widget-candidates.json"
        original = json.loads(path.read_text())
        for field, value in (("vendor_path", "../escape"), ("approved_scope", "full-shell"),
                             ("dependency_files", ["extra.js"]), ("modifications", ["edited"]),
                             ("url", "https://invalid.example/Model.js")):
            data = copy.deepcopy(original)
            data["imports"][0][field] = value
            path.write_text(json.dumps(data))
            with self.subTest(field=field), self.assertRaises(clock.builder.BuildError):
                clock.verified_model(self.root)

    def test_linked_model_refused(self):
        path = self.root / clock.MODEL
        data = path.read_bytes()
        path.unlink()
        replacement = self.root / "replacement.js"
        replacement.write_bytes(data)
        path.symlink_to(replacement)
        with self.assertRaisesRegex(clock.builder.BuildError, "symlink"):
            clock.verified_model(self.root)

    def test_default_plan_only_and_run_needs_build(self):
        with patch.object(clock, "run_checks") as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(clock.main([]), 0)
        run.assert_not_called()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            clock.main(["--run"])

    def test_fixed_probe_has_no_original_ui_or_service_types(self):
        for case in clock.CASES:
            qml = clock.qml_probe(case[0])
            self.assertIn('import "Model.js" as Model', qml)
            for forbidden in ("import QtQuick", "Process {", "Window {", "BarWidget {", "Panel {", "SystemClock {", "Quickshell.Services"):
                self.assertNotIn(forbidden, qml)
        with self.assertRaises(clock.builder.BuildError):
            clock.qml_probe("arbitrary")

    def test_metrics_exit_and_diagnostics_strict(self):
        case = clock.CASES[0]
        output = 'Configuration Loaded\nDEBUG qml: OMABUNTU_CLOCK_OK::utc {"assertions":221,"timezone":"UTC"}\n'
        self.assertTrue(clock.classify(case, 0, output))
        for code, value in ((None, output), (-11, output), (255, output),
                            (0, output.replace("221", "220")), (0, output.replace('"UTC"', '"wrong"')),
                            (0, output + output), (0, output.replace("Configuration Loaded", ""))):
            self.assertFalse(clock.classify(case, code, value))
        for level in ("WARN", "ERROR", "FATAL", "CRITICAL"):
            self.assertFalse(clock.classify(case, 0, output + level + " unexpected\n"))

    def test_negative_requires_exact_deliberate_assertion(self):
        case = clock.CASES[-1]
        good = "Configuration Loaded\nERROR qml: OMABUNTU_CLOCK_ASSERTION_FAILED deliberate ISO-week mismatch\n"
        self.assertTrue(clock.classify(case, 42, good))
        for code, value in ((0, good), (-11, good), (None, good), (42, good.replace("deliberate ISO-week mismatch", "unrelated")),
                            (42, good + "WARN unrelated\n"), (42, good + clock.MARKER)):
            self.assertFalse(clock.classify(case, code, value))

    def test_bubblewrap_absent_stops_no_fallback(self):
        with patch.object(clock.shutil, "which", return_value=None), patch.object(clock.subprocess, "run") as run:
            with self.assertRaises(clock.builder.BuildError):
                clock.run_checks(self.root, self.root)
        run.assert_not_called()

    def test_bad_source_stops_before_stage_or_process(self):
        (self.root / clock.MODEL).write_text("changed")
        with patch.object(clock.shutil, "which", return_value="bwrap"), \
                patch.object(clock.check_runtime, "verify_stage") as verify, patch.object(clock.subprocess, "run") as run:
            with self.assertRaises(clock.builder.BuildError):
                clock.run_checks(self.root, self.root)
        verify.assert_not_called()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
