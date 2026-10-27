"""Build safety contracts; no network, compiler, or external build is invoked."""

import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_runtime", ROOT / "tools" / "build_runtime.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BuildTests(unittest.TestCase):
    def setUp(self):
        work = ROOT / "work"
        work.mkdir(mode=0o700, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="build-tests-", dir=work)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def archive(self, name="source/CMakeLists.txt", kind=tarfile.REGTYPE):
        path = self.root / "source.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            item = tarfile.TarInfo(name)
            item.type = kind
            if kind == tarfile.REGTYPE:
                data = b"# Synthetic source\n"
                item.size = len(data)
                archive.addfile(item, io.BytesIO(data))
            else:
                item.linkname = "/outside"
                archive.addfile(item)
        return path

    def test_source_lock_matches_manifest_and_archives_are_pinned(self):
        manifest, sources = builder.load_inputs(ROOT)
        self.assertEqual(set(sources), {"cpptrace", "quickshell"})
        self.assertEqual(manifest["sources"][0]["commit"], sources["quickshell"]["commit"])
        for source in sources.values():
            self.assertRegex(source["archive_sha256"], r"^[a-f0-9]{64}$")

    def test_default_command_does_not_fetch_or_build(self):
        with patch.object(builder, "build") as build, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(builder.main([]), 0)
        build.assert_not_called()

    def test_extract_regular_source(self):
        path = self.archive()
        destination = self.root / "unpacked"
        destination.mkdir()
        source = builder.extract_source(path, destination, {"archive_root": "source"})
        self.assertEqual((source / "CMakeLists.txt").read_text(), "# Synthetic source\n")

    def test_reject_traversal_before_extracting(self):
        path = self.archive("source/../escaped")
        with self.assertRaises(builder.BuildError):
            builder.extract_source(path, self.root, {"archive_root": "source"})
        self.assertFalse((self.root / "escaped").exists())

    def test_reject_links_and_devices(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE):
            with self.subTest(kind=kind):
                path = self.archive("source/link", kind)
                with self.assertRaises(builder.BuildError):
                    builder.extract_source(path, self.root, {"archive_root": "source"})

    def test_cached_archive_mismatch_does_not_trigger_download(self):
        source = {"name": "example", "commit": "a" * 40, "archive_bytes": 3, "archive_sha256": "0" * 64}
        (self.root / ("example-" + "a" * 40 + ".tar.gz")).write_bytes(b"bad")
        with patch.object(builder.urllib.request, "urlopen") as fetch:
            with self.assertRaises(builder.BuildError):
                builder.fetch_archive(source, self.root)
        fetch.assert_not_called()

    def test_network_checksum_mismatch_is_not_cached(self):
        source = {
            "name": "example", "commit": "a" * 40, "archive_url": "https://example.invalid/source",
            "archive_sha256": "0" * 64,
        }
        with patch.object(builder.urllib.request, "urlopen", return_value=io.BytesIO(b"wrong")):
            with self.assertRaises(builder.BuildError):
                builder.fetch_archive(source, self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_sandbox_has_no_host_home_or_network_and_sources_are_read_only(self):
        command = builder.sandbox_command(self.root, ["cmake", "--version"], self.root / "sources")
        self.assertIn("--unshare-all", command)
        self.assertIn("--clearenv", command)
        self.assertNotIn("--share-net", command)
        self.assertNotIn(["--ro-bind", "/", "/"], [command[i:i + 3] for i in range(len(command))])
        self.assertIn(["--ro-bind", str(self.root / "sources"), "/source"], [command[i:i + 3] for i in range(len(command))])
        writable = [command[i + 1] for i, arg in enumerate(command) if arg == "--bind"]
        self.assertEqual(writable, [str(self.root / name) for name in ("build", "stage", "home")])
        self.assertEqual(command[-2:], ["cmake", "--version"])

    def test_cmake_prefix_is_sandbox_only_and_external_cpptrace_is_used(self):
        manifest, sources = builder.load_inputs(ROOT)
        command = builder.cmake_command("quickshell", sources["quickshell"], manifest["proposed_cmake_options"]["quickshell"])
        self.assertIn("-DCMAKE_INSTALL_PREFIX=/opt/omabuntu-runtime", command)
        self.assertIn("-DCMAKE_PREFIX_PATH=/stage/opt/omabuntu-runtime", command)
        self.assertIn("-DVENDOR_CPPTRACE=OFF", command)
        self.assertIn("-DINSTALL_QML_PREFIX=lib/qt6/qml", command)
        with self.assertRaises(builder.BuildError):
            builder.cmake_command("cpptrace", sources["cpptrace"], {"CMAKE_INSTALL_PREFIX": "/usr"})

    def test_artifact_manifest_does_not_follow_symlinks(self):
        (self.root / "data").write_bytes(b"example")
        (self.root / "link").symlink_to("/not-mounted-private-path")
        artifacts = builder.artifact_manifest(self.root)
        self.assertEqual(artifacts[0]["sha256"], hashlib.sha256(b"example").hexdigest())
        self.assertEqual(artifacts[1], {"path": "link", "type": "symlink", "target": "/not-mounted-private-path"})

    def create_assessment_fixture(self):
        module_root = self.root / "stage" / builder.PREFIX.lstrip("/") / "lib/qt6/qml/Quickshell"
        for module in (
            "", "Io", "Wayland", "Hyprland", "Bluetooth", "Networking",
            "Services/Pam", "Services/Polkit", "Services/Pipewire", "Services/Mpris",
            "Services/Notifications", "Services/SystemTray", "Services/UPower",
        ):
            directory = module_root / module
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "qmldir").write_text("# Synthetic metadata\n")
        shaders = self.root / "build/quickshell/src/widgets/.qsb/shaders"
        shaders.mkdir(parents=True)
        for name in ("cliprect.frag.qsb", "cliprect-ub.frag.qsb"):
            (shaders / name).write_bytes(b"synthetic shader")
        (self.root / "logs").mkdir()
        return shaders

    def test_assessment_ignores_qsb_directories_and_hashes_only_shader_files(self):
        self.create_assessment_fixture()
        result = builder.assess_outputs(self.root)
        self.assertEqual(result["status"], "staged")
        self.assertEqual(len(result["shaders"]), 2)
        self.assertTrue(all(item["bytes"] > 0 for item in result["shaders"]))
        self.assertTrue(all(result["qml_metadata"].values()))

    def test_assessment_rejects_empty_shader_outputs(self):
        shaders = self.create_assessment_fixture()
        (shaders / "cliprect.frag.qsb").write_bytes(b"")
        with self.assertRaisesRegex(builder.BuildError, "shader outputs"):
            builder.assess_outputs(self.root)

    def test_assessment_rejects_logged_optimizer_failure(self):
        self.create_assessment_fixture()
        (self.root / "logs/build.log").write_text("Failed to run spirv-opt\n")
        with self.assertRaisesRegex(builder.BuildError, "Shader optimization failed"):
            builder.assess_outputs(self.root)

    def test_warning_summary_keeps_non_shader_diagnostics_visible(self):
        (self.root / "configure.log").write_text(
            "The qml plugin 'example' is a dependency\n"
            "Manually-specified variables were not used\n"
        )
        (self.root / "build.log").write_text(
            "warning: control reaches end of non-void function\n"
            "XML failed validation\n"
            "Type is used as base type but cannot be found\n"
        )
        counts = builder.warning_summary(self.root)
        self.assertEqual(counts["shader_optimizer_failures"], 0)
        for name in ("qt_qml_link_targets", "compiler_diagnostics", "wayland_xml_validation", "qml_typeinfo", "unused_cmake_options"):
            self.assertEqual(counts[name], 1)

    def test_warning_summary_detects_optimizer_failure(self):
        (self.root / "build.log").write_text("Failed to run spirv-opt\nFailed to run spirv-opt\n")
        self.assertEqual(builder.warning_summary(self.root)["shader_optimizer_failures"], 2)

    def test_missing_optimizer_blocks_build_before_workspace_allocation(self):
        def which(program):
            return None if program == "spirv-opt" else "/usr/bin/" + program

        with patch.object(builder.shutil, "which", side_effect=which), \
             patch.object(builder, "private_directory") as allocate:
            with self.assertRaisesRegex(builder.BuildError, "spirv-opt"):
                builder.build()
        allocate.assert_not_called()

    def test_private_directory_refuses_symlinks(self):
        path = self.root / "link"
        path.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(builder.BuildError):
            builder.private_directory(path)


if __name__ == "__main__":
    unittest.main()
