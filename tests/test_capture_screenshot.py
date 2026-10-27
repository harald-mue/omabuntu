"""Omasnap argument mapping. These tests never start Omasnap or capture a screen."""
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import capture_screenshot
import keybindings_menu


class CaptureScreenshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "work")
        self.addCleanup(self.temp.cleanup)
        self.binary = Path(self.temp.name) / "omasnap"
        self.binary.write_text("#!/bin/sh\nexit 0\n")
        self.binary.chmod(0o755)

    def test_wrapper_maps_copy_save_and_drops_slurp(self):
        argv, env = capture_screenshot.plan(
            ["windows", "copy", "slurp", "save", "scroll", "--save"],
            {"HOME": "/home/x", "WAYLAND_DISPLAY": "wayland-1",
             "OMARCHY_SCREENSHOT_DIR": "/tmp/legacy"},
            binary=str(self.binary))
        self.assertEqual(argv, [
            str(self.binary), "windows", "--copy", "--save", "scroll", "--save"])
        self.assertEqual(env["OMASNAP_SCREENSHOT_DIR"], "/tmp/legacy")
        self.assertEqual(env["WAYLAND_DISPLAY"], "wayland-1")

    def test_native_directory_wins_over_the_legacy_one(self):
        _, env = capture_screenshot.plan(
            [],
            {"OMARCHY_SCREENSHOT_DIR": "/tmp/legacy",
             "OMASNAP_SCREENSHOT_DIR": "/tmp/native"},
            binary=str(self.binary))
        self.assertEqual(env["OMASNAP_SCREENSHOT_DIR"], "/tmp/native")

    def test_one_runtime_socket_fills_a_missing_wayland_display(self):
        runtime = Path(self.temp.name) / "run"
        runtime.mkdir()
        endpoint = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(endpoint.close)
        endpoint.bind(str(runtime / "wayland-3"))
        (runtime / "wayland-3.lock").write_text("")
        _, env = capture_screenshot.plan(
            [], {"XDG_RUNTIME_DIR": str(runtime)}, binary=str(self.binary))
        self.assertEqual(env["WAYLAND_DISPLAY"], "wayland-3")
        extra = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(extra.close)
        extra.bind(str(runtime / "wayland-4"))
        _, several = capture_screenshot.plan(
            [], {"XDG_RUNTIME_DIR": str(runtime)}, binary=str(self.binary))
        self.assertNotIn("WAYLAND_DISPLAY", several)
        _, kept = capture_screenshot.plan(
            [], {"XDG_RUNTIME_DIR": str(runtime), "WAYLAND_DISPLAY": "wayland-1"},
            binary=str(self.binary))
        self.assertEqual(kept["WAYLAND_DISPLAY"], "wayland-1")

    def test_missing_symlink_relative_and_foreign_names_are_refused(self):
        with self.assertRaisesRegex(capture_screenshot.CaptureError, "missing"):
            capture_screenshot.approved_binary({"HOME": "/home/x"})
        self.binary.unlink()
        self.binary.symlink_to(self.binary.parent / "elsewhere")
        with self.assertRaisesRegex(capture_screenshot.CaptureError, "regular file"):
            capture_screenshot.approved_binary({}, binary=str(self.binary))
        self.binary.unlink()
        self.binary.write_text("#!/bin/sh\n")
        self.binary.chmod(0o644)
        with self.assertRaisesRegex(capture_screenshot.CaptureError, "not executable"):
            capture_screenshot.approved_binary({}, binary=str(self.binary))
        with self.assertRaisesRegex(capture_screenshot.CaptureError, "absolute"):
            capture_screenshot.approved_binary({"OMABUNTU_OMASNAP": "omasnap"})
        foreign = Path(self.temp.name) / "hyprlock"
        foreign.write_text("#!/bin/sh\n")
        foreign.chmod(0o755)
        with self.assertRaisesRegex(capture_screenshot.CaptureError, "named omasnap"):
            capture_screenshot.approved_binary({}, binary=str(foreign))

    def test_newline_arguments_are_refused_before_execution(self):
        with self.assertRaisesRegex(capture_screenshot.CaptureError, "refused"):
            capture_screenshot.plan(["copy\n--save"], {}, binary=str(self.binary))

    def test_launch_replaces_the_process_and_a_missing_binary_does_not(self):
        seen = {}

        def record(path, argv, env):
            seen["path"] = path
            seen["argv"] = argv
            seen["dir"] = env.get("OMASNAP_SCREENSHOT_DIR")

        with patch.object(capture_screenshot.os, "execve", side_effect=record):
            self.assertEqual(capture_screenshot.main(
                ["fullscreen", "copy"],
                {"HOME": "/home/x", "OMARCHY_SCREENSHOT_DIR": "/tmp/shots"},
                binary=str(self.binary)), 0)
        self.assertEqual(seen["path"], str(self.binary))
        self.assertEqual(seen["argv"], [str(self.binary), "fullscreen", "--copy"])
        self.assertEqual(seen["dir"], "/tmp/shots")

        with patch.object(capture_screenshot.os, "execve", side_effect=record):
            self.assertEqual(capture_screenshot.main(["copy"], os.environ, binary=str(self.binary)), 0)
        self.assertNotIsInstance(os.environ, dict)
        self.assertEqual(seen["argv"], [str(self.binary), "--copy"])
        with patch.object(capture_screenshot.os, "execve") as execve, \
                patch("sys.stderr"):
            code = capture_screenshot.main([], {"HOME": "/home/missing"})
        self.assertEqual(code, 1)
        execve.assert_not_called()

    def test_exec_failure_does_not_capture_another_way(self):
        with patch.object(capture_screenshot.os, "execve", side_effect=OSError("denied")), \
                patch("sys.stderr") as err:
            code = capture_screenshot.main([], {}, binary=str(self.binary))
        written = "".join(call.args[0] for call in err.write.call_args_list)
        self.assertEqual(code, 1)
        self.assertIn("did not start", written)
        self.assertNotIn("denied", written)

    def test_menu_does_not_treat_the_screenshot_as_a_session_action(self):
        self.assertFalse(keybindings_menu.session_action(str(self.binary)))
        self.assertFalse(keybindings_menu.session_action("omasnap"))
        self.assertTrue(keybindings_menu.session_action("omabuntu lock --apply"))

    def test_helper_starts_only_through_exec(self):
        text = (ROOT / "tools/capture_screenshot.py").read_text()
        self.assertNotIn("subprocess", text)
        self.assertNotIn("os.system", text)
        self.assertNotIn("Popen", text)
        self.assertEqual(text.count("os.execve"), 1)
        self.assertIn('elif arg == "slurp"', text)

    def test_pinned_notices_match_the_recorded_omasnap_commit(self):
        pin = json.loads((ROOT / "upstream/omasnap-source.json").read_text())
        self.assertEqual(pin["commit"], "a432f40b14598a4a02b89fa0054f9a0ba3662dd4")
        self.assertEqual(pin["version"], "1.24.0")
        self.assertEqual(pin["status"], "pinned-not-built")
        notices = [pin["license"], *pin["bundled_notices"], pin["fonts_note"]]
        for notice in notices:
            path = ROOT / notice["notice_path"]
            self.assertFalse(path.is_symlink())
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, notice["sha256"])
            self.assertNotIn("Neucha.ttf", path.name)
        mode = (ROOT / "licenses/Omasnap-MIT.txt").stat().st_mode
        self.assertFalse(mode & stat.S_IXUSR)
