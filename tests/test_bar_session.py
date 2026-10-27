"""Session lifetime/process contracts; never starts or stops a real process."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import bar_session as session


class BarSessionTests(unittest.TestCase):
    def record(self):
        return {"pid": 1234, "identity": {"start_ticks": "5678", "argv": [
            str(ROOT / "work/builds/example/stage/opt/omabuntu-runtime/bin/quickshell"),
            "--no-color", "--path", str(ROOT / "work/bar-session/example/probe/TrialShell.qml")]}}

    def test_grant_is_explicit_and_has_no_duration(self):
        self.assertEqual(session.GRANT, {"schema_version": 1, "scope": "bar-session-v1", "lifetime": "session"})
        text = (ROOT / "config/shell/preview/TrialShell.qml").read_text()
        self.assertIn('snapshot.scope === "bar-session-v1" ? 0', text)
        self.assertIn("if (lifetimeMs > 0) expiry.start();", text)

    def test_launcher_has_no_timeout_wrapper_or_autostart(self):
        text = (ROOT / "tools/bar_session.py").read_text()
        self.assertNotIn('["timeout"', text)
        self.assertIn("start_new_session=True", text)
        self.assertNotIn("SIGKILL", text)
        self.assertNotIn("uwsm stop", text)
        self.assertNotIn("hyprctl eval", text)

    def test_process_match_requires_full_identity(self):
        record = self.record()
        with patch.object(session, "process_identity", return_value=record["identity"]):
            self.assertTrue(session.matches(record))
        with patch.object(session, "process_identity", return_value={**record["identity"], "start_ticks": "reused"}):
            self.assertFalse(session.matches(record))
        with patch.object(session, "process_identity", return_value=None):
            self.assertFalse(session.matches(record))

    def test_foreign_paths_and_commands_cannot_be_stopped(self):
        record = self.record()
        for args in (["/usr/bin/quickshell", "--no-color", "--path", "/outside/TrialShell.qml"],
                     ["/usr/bin/bash", "--no-color", "--path", "/outside/TrialShell.qml"],
                     [str(ROOT / "work/builds/../other/stage/opt/omabuntu-runtime/bin/quickshell"), "--no-color", "--path", record["identity"]["argv"][3]]):
            with self.subTest(args=args), patch.object(session, "process_identity") as identity:
                self.assertFalse(session.matches({"pid": 1234, "identity": {"start_ticks": "1", "argv": args}}))
                identity.assert_not_called()
        self.assertFalse(session.matches(None))

    def test_invalid_pid_is_never_inspected(self):
        for pid in (True, 0, 1, -1, "1234", None):
            self.assertIsNone(session.process_identity(pid))

    def test_duplicate_shell_refused_before_staging(self):
        with patch.object(session, "read_record", return_value=None), \
             patch.object(session.subprocess, "run", return_value=Mock(returncode=0)), \
             patch.object(session.preview, "verified_sources") as verify:
            with self.assertRaisesRegex(RuntimeError, "Another Quickshell"):
                session.start(ROOT / "work/bar-session", ROOT / "work/builds/fixture")
            verify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
