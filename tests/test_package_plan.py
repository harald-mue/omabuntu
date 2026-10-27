"""Simulation-only package planning tests; APT is never invoked."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_plan", ROOT / "tools" / "package_plan.py")
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)


class PackagePlanTests(unittest.TestCase):
    def setUp(self):
        work = ROOT / "work"
        work.mkdir(mode=0o700, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="package-tests-", dir=work)
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "manifest.json"
        self.manifest = {
            "schema_version": 1, "name": "quickshell",
            "build_dependencies": ["build-example"],
            "cpptrace_dependencies": ["trace-example"],
            "runtime_dependencies": ["runtime-example"],
        }
        self.write_manifest()

    def write_manifest(self):
        self.path.write_text(json.dumps(self.manifest))

    def run_plan(self, policy=None, policy_status="ok", simulation_status="ok", transaction=""):
        calls = []
        if policy is None:
            policy = "\n".join(
                f"{name}:\n  Installed: (none)\n  Candidate: 1:2.3-4~test1"
                for name in ("build-example", "trace-example", "runtime-example")
            )

        def run(args, **kwargs):
            calls.append(args)
            if args[0] == "apt-cache":
                return {"status": policy_status, "stdout": policy, "stderr": "", "command": args}
            return {"status": simulation_status, "stdout": transaction, "stderr": "", "command": args}

        return planner.create_plan(self.path, run), calls

    def test_simulation_is_always_explicit_and_candidate_pinned(self):
        report, calls = self.run_plan(transaction="Inst new-example (1.0 Ubuntu [amd64])\n")
        self.assertEqual(report["status"], "review-required")
        command = calls[-1]
        self.assertEqual(command[:5], ["apt-get", "--simulate", "--no-remove", "--no-install-recommends", "install"])
        self.assertTrue(all("=1:2.3-4~test1" in item for item in command[5:]))
        self.assertEqual(report["transaction"]["new"], ["new-example"])

    def test_missing_candidate_blocks_simulation(self):
        report, calls = self.run_plan(policy="build-example:\n  Installed: (none)\n  Candidate: (none)\n")
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(len(calls), 1)
        self.assertIsNone(report["simulation"])

    def test_failed_policy_blocks_simulation(self):
        report, calls = self.run_plan(policy_status="timeout")
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(len(calls), 1)

    def test_failed_simulation_is_not_success(self):
        report, _ = self.run_plan(simulation_status="failed")
        self.assertEqual(report["status"], "blocked")

    def test_removal_is_blocked_even_if_command_returns_success(self):
        report, _ = self.run_plan(transaction="Remv existing-agent [1.0]\n")
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["transaction"]["removed"], ["existing-agent"])

    def test_upgrade_is_visible_and_needs_review(self):
        report, _ = self.run_plan(transaction="Inst example [1.0] (2.0 Ubuntu [amd64])\n")
        self.assertEqual(report["status"], "review-required")
        self.assertEqual(report["transaction"]["upgraded_or_changed"], ["example"])

    def test_invalid_package_name_is_rejected_before_commands(self):
        for name in ("--allow-unauthenticated", "package;false", "Package", "../file.deb", "pkg=1.0"):
            with self.subTest(name=name):
                self.manifest["build_dependencies"] = [name]
                self.write_manifest()
                with self.assertRaises(ValueError):
                    self.run_plan()

    def test_invalid_candidate_is_rejected_before_simulation(self):
        with self.assertRaises(ValueError):
            self.run_plan(policy="build-example:\n  Candidate: --bad-option\n")

    def test_deduplicate_groups(self):
        self.manifest["runtime_dependencies"].append("build-example")
        self.write_manifest()
        _, packages = planner.load_manifest(self.path)
        self.assertEqual(packages.count("build-example"), 1)

    def test_bad_manifest_version(self):
        self.manifest["schema_version"] = 99
        self.write_manifest()
        with self.assertRaises(ValueError):
            self.run_plan()

    def test_real_manifest_contains_pinned_sources_and_required_features(self):
        manifest, packages = planner.load_manifest(ROOT / "packages" / "quickshell-plan.json")
        self.assertEqual(len(packages), len(set(packages)))
        self.assertIn("spirv-tools", manifest["build_dependencies"])
        for source in manifest["sources"]:
            self.assertRegex(source["commit"], r"^[a-f0-9]{40}$")
        options = manifest["proposed_cmake_options"]
        self.assertEqual(options["quickshell"]["VENDOR_CPPTRACE"], "OFF")
        for feature in ("SERVICE_PAM", "SERVICE_POLKIT", "CRASH_HANDLER"):
            self.assertEqual(options["quickshell"][feature], "ON")
        self.assertEqual(options["cpptrace"]["CPPTRACE_USE_EXTERNAL_LIBDWARF"], "ON")


if __name__ == "__main__":
    unittest.main()
