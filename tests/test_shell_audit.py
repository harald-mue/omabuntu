"""Static reference auditing never runs reference programs or follows their links."""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("audit_shell", ROOT / "tools/audit_shell.py")
auditor = importlib.util.module_from_spec(SPEC)
with patch.object(sys, "path", [str(ROOT / "tools"), *sys.path]):
    SPEC.loader.exec_module(auditor)


class ShellAuditTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "work").mkdir(mode=0o700, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="shell-audit-tests-", dir=ROOT / "work")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for directory in (auditor.SHELL, auditor.HELPERS):
            (self.root / directory).mkdir(parents=True)
        for relative in auditor.EXTRA:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{}\n")
        (self.root / auditor.SHELL / "shell.qml").write_text('ShellRoot { /* omarchy-launch-demo */ }\n')
        (self.root / auditor.HELPERS / "omarchy-launch-demo").write_text("#!/bin/bash\nomarchy-demo-next\n")
        (self.root / auditor.HELPERS / "omarchy-demo-next").write_text("#!/bin/bash\npacman -Q\n")

    def manifest(self, folder="demo", identifier="omarchy.demo", entry="Service.qml"):
        directory = self.root / auditor.SHELL / "plugins" / folder
        directory.mkdir(parents=True)
        (directory / "Service.qml").write_text("Item {}\n")
        data = {"schemaVersion": 1, "id": identifier, "kinds": ["service"],
                "keepLoaded": True, "entryPoints": {"service": entry}}
        (directory / "manifest.json").write_text(json.dumps(data))
        return directory

    def test_static_audit_preserves_warning_status_and_transitive_candidates(self):
        self.manifest()
        result = auditor.audit(self.root)
        self.assertEqual(result["status"], "audit-only-not-activation-approved")
        self.assertEqual(result["potential_helper_closure"], ["omarchy-demo-next", "omarchy-launch-demo"])
        self.assertEqual(result["service_manifests"][0]["id"], "omarchy.demo")
        self.assertTrue(result["service_manifests"][0]["keepLoaded"])
        self.assertEqual(result["finding_counts"]["arch_management"], 1)

    def test_packaging_provenance_is_commit_pinned_and_matches_runtime_source(self):
        provenance = json.loads((ROOT / "upstream/quickshell-packaging.json").read_text())
        _, sources = auditor.builder.load_inputs(ROOT)
        self.assertEqual(provenance["upstream_commit"], sources["quickshell"]["commit"])
        self.assertRegex(provenance["packaging_commit"], r"^[a-f0-9]{40}$")
        for field in ("pkgbuild", "patch", "arch_transaction_hook"):
            self.assertIn("/" + provenance["packaging_commit"] + "/", provenance[field]["url"])
            self.assertRegex(provenance[field]["sha256"], r"^[a-f0-9]{64}$")

    def test_historical_patch_is_metadata_not_an_approved_build_input(self):
        provenance = json.loads((ROOT / "upstream/quickshell-packaging.json").read_text())
        self.assertEqual(provenance["status"], "research-metadata-not-a-build-input")
        self.assertTrue(provenance["patch"]["target_decision"].startswith("Not applied."))
        _, sources = auditor.builder.load_inputs(ROOT)
        self.assertNotIn("patch", sources["quickshell"])

    def test_comments_are_explicitly_conservative_findings_not_execution(self):
        helpers, findings = auditor.scan_text("// sudo pacman omarchy-example\n")
        self.assertEqual(helpers, ["omarchy-example"])
        self.assertEqual({x["category"] for x in findings}, {"privilege", "arch_management"})

    def test_closure_handles_cycles_and_unknown_tokens(self):
        self.assertEqual(auditor.closure(["a", "missing"], {"a": ["b"], "b": ["a", "unknown"]}), ["a", "b"])

    def test_reference_text_is_never_executed(self):
        marker = self.root / "must-not-exist"
        (self.root / auditor.HELPERS / "omarchy-do-not-run").write_text(f"touch {marker}\n")
        with patch.object(subprocess, "run", side_effect=AssertionError("No execution")), \
             patch.object(auditor.os, "system", side_effect=AssertionError("No execution")), \
             patch.object(auditor.builder, "fetch_archive", side_effect=AssertionError("No network")):
            auditor.audit(self.root)
        self.assertFalse(marker.exists())

    def test_file_content_is_hashed_without_being_copied_into_report(self):
        p = self.root / auditor.SHELL / "shell.qml"
        result = auditor.audit(self.root)
        record = next(item for item in result["files"] if item["path"] == str(auditor.SHELL / "shell.qml"))
        self.assertEqual(record["sha256"], hashlib.sha256(p.read_bytes()).hexdigest())
        self.assertNotIn("content", record)

    def test_helper_symlinks_are_rejected(self):
        (self.root / auditor.HELPERS / "omarchy-link").symlink_to(self.root / auditor.SHELL / "shell.qml")
        with self.assertRaisesRegex(auditor.builder.BuildError, "symlink"):
            auditor.audit(self.root)

    def test_same_directory_helper_alias_is_recorded_without_dereferencing(self):
        (self.root / auditor.HELPERS / "omarchy-alias").symlink_to("omarchy-launch-demo")
        result = auditor.audit(self.root)
        self.assertEqual(result["helper_aliases"], {"omarchy-alias": "omarchy-launch-demo"})
        record = next(x for x in result["files"] if x.get("type") == "symlink")
        self.assertEqual(record["target"], "omarchy-launch-demo")
        self.assertNotIn("sha256", record)

    def test_helper_alias_chain_is_rejected(self):
        (self.root / auditor.HELPERS / "omarchy-one").symlink_to("omarchy-two")
        (self.root / auditor.HELPERS / "omarchy-two").symlink_to("omarchy-launch-demo")
        with self.assertRaisesRegex(auditor.builder.BuildError, "symlink"):
            auditor.audit(self.root)

    def test_directory_symlinks_are_rejected(self):
        (self.root / auditor.SHELL / "escape").symlink_to(self.root / auditor.HELPERS, target_is_directory=True)
        with self.assertRaisesRegex(auditor.builder.BuildError, "Symlinked"):
            auditor.audit(self.root)

    def test_absolute_manifest_entry_is_rejected(self):
        self.manifest(entry=str(self.root / auditor.SHELL / "shell.qml"))
        with self.assertRaisesRegex(auditor.builder.BuildError, "stay inside"):
            auditor.audit(self.root)

    def test_parent_traversal_manifest_entry_is_rejected(self):
        self.manifest(entry="../../../shell.qml")
        with self.assertRaisesRegex(auditor.builder.BuildError, "stay inside"):
            auditor.audit(self.root)

    def test_duplicate_manifest_ids_are_rejected(self):
        self.manifest(folder="one")
        self.manifest(folder="two")
        with self.assertRaisesRegex(auditor.builder.BuildError, "Duplicate"):
            auditor.audit(self.root)

    def test_malformed_plugin_kinds_are_rejected(self):
        directory = self.manifest()
        path = directory / "manifest.json"
        item = json.loads(path.read_text())
        item["kinds"] = "service"
        path.write_text(json.dumps(item))
        with self.assertRaisesRegex(auditor.builder.BuildError, "kinds"):
            auditor.audit(self.root)

    def test_missing_reference_layout_is_not_partial_success(self):
        with self.assertRaisesRegex(auditor.builder.BuildError, "Required reference"):
            auditor.audit(self.root / auditor.SHELL)

    def test_oversized_text_file_is_rejected(self):
        with (self.root / auditor.SHELL / "Huge.qml").open("wb") as stream:
            stream.truncate(8 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(auditor.builder.BuildError, "bounded regular"):
            auditor.audit(self.root)


if __name__ == "__main__":
    unittest.main()
