"""Private native capture contracts; no live debugger attachment or desktop."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import native_crash_capture as capture


class NativeCaptureTests(unittest.TestCase):
    def test_script_disables_data_expansion_downloads_and_aslr_changes(self):
        script = capture.gdb_script('/private/capture')
        for command in ('set auto-load off', 'set debuginfod enabled off',
                        'set disable-randomization off', 'set startup-with-shell off',
                        'set may-call-functions off', 'set print frame-arguments none',
                        'set print entry-values no', 'set print raw-values on'):
            self.assertIn(command, script)
        self.assertIn('backtrace -no-filters -frame-arguments none -entry-values no', script)
        self.assertIn('-frame-info location-and-address 64', script)
        for forbidden in ('generate-core-file', 'gcore', 'backtrace full', 'info locals',
                          'info registers', 'set disable-randomization on', 'attach '):
            self.assertNotIn(forbidden, script)

    def test_script_has_bounded_threads_frames_and_output(self):
        script = capture.gdb_script('/private/capture')
        self.assertIn('threads[:64]', script)
        self.assertIn('text[:1000000]', script)
        self.assertIn('set backtrace limit 64', script)
        self.assertIn("gdb.execute('kill', to_string=True)", script)

    def test_generated_embedded_python_is_syntax_valid(self):
        script = capture.gdb_script('/a/path with "quotes"')
        body = script.split('\npython\n', 1)[1].rsplit('\nend\n', 1)[0]
        compile(body, '<gdb-python>', 'exec')

    def test_ordinary_probes_are_delegated_without_modification(self):
        original = Mock(return_value='probe-result')
        adapter = capture.SpawnAdapter(['/approved/quickshell'], original)
        self.assertEqual(adapter(['pgrep', '-x', 'quickshell'], text=True), 'probe-result')
        original.assert_called_once_with(['pgrep', '-x', 'quickshell'], text=True)
        self.assertFalse(adapter.used)

    def test_adapter_restores_popen_after_failure(self):
        manager = Mock()
        manager.subprocess = Mock()
        original = manager.subprocess.Popen
        with self.assertRaisesRegex(ValueError, 'fixture'):
            with capture.adapted_spawn(manager, ['/approved/quickshell']):
                self.assertIsNot(manager.subprocess.Popen, original)
                raise ValueError('fixture')
        self.assertIs(manager.subprocess.Popen, original)

    def test_stale_or_reused_pid_never_receives_signal(self):
        record = {'pid': 12345, 'identity': {'start_ticks': '1', 'argv': ['expected']}}
        with patch.object(capture.deployment, 'identity', return_value={'start_ticks': '2', 'argv': ['expected']}), patch.object(capture.os, 'kill') as kill:
            self.assertFalse(capture.signal_owned(record, 15))
            kill.assert_not_called()

    def test_missing_identity_never_authorizes_a_signal(self):
        with patch.object(capture.deployment, 'identity', return_value=None), patch.object(capture.os, 'kill') as kill:
            self.assertFalse(capture.signal_owned({'pid': 12345}, 15))
            self.assertFalse(capture.signal_owned(None, 15))
            kill.assert_not_called()

    def test_handoff_requires_both_parent_and_tracer(self):
        with patch.object(Path, 'read_text', return_value='PPid:\t99\nTracerPid:\t99\n'):
            self.assertTrue(capture.traced_by(123, 99))
        with patch.object(Path, 'read_text', return_value='PPid:\t99\nTracerPid:\t0\n'):
            self.assertFalse(capture.traced_by(123, 99))
        with patch.object(Path, 'read_text', side_effect=FileNotFoundError):
            self.assertFalse(capture.traced_by(123, 99))

    def test_exact_identity_can_receive_signal(self):
        record = {'pid': 12345, 'identity': {'start_ticks': '1', 'argv': ['expected']}}
        with patch.object(capture.deployment, 'identity', return_value=record['identity']), patch.object(capture.os, 'kill') as kill:
            self.assertTrue(capture.signal_owned(record, 15))
            kill.assert_called_once_with(12345, 15)

    def test_child_exposes_inferior_pid_not_supervisor(self):
        supervisor = Mock(pid=999)
        supervisor.poll.return_value = None
        child = capture.CaptureChild(supervisor, {'pid': 123}, Path('/private'))
        with patch.object(capture, 'same_process', return_value=True):
            self.assertEqual(child.pid, 123)
            self.assertIsNone(child.poll())
        with patch.object(capture, 'same_process', return_value=False):
            self.assertEqual(child.poll(), 1)

    def test_child_termination_is_identity_gated_and_reaps_supervisor(self):
        supervisor = Mock()
        record = {'pid': 123}
        child = capture.CaptureChild(supervisor, record, Path('/private'))
        with patch.object(capture, 'signal_owned') as send:
            child.terminate()
        send.assert_called_once_with(record, capture.signal.SIGTERM)
        supervisor.terminate.assert_called_once()
        supervisor.wait.assert_called_once_with(timeout=5)

    def test_live_command_defaults_to_plan_only(self):
        with patch.object(capture, 'activate') as activate, patch('builtins.print'):
            self.assertEqual(capture.main(['start']), 0)
            activate.assert_not_called()

    def test_no_normal_session_expiry_in_supervisor(self):
        source = (ROOT / 'tools/native_crash_capture.py').read_text()
        self.assertIn("if owned is None and time.monotonic() - started > 10:", source)
        self.assertIn("capture_since = None", source)
        self.assertIn("elif time.monotonic() - capture_since > 15:", source)
        self.assertNotIn('SIGALRM', source)
        self.assertNotIn('threading.Timer', source)


if __name__ == '__main__':
    unittest.main()
