"""Subscription protocol with disposable Python emitters, never a native server."""
import copy
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import audio_events as events
import audio_pactl as pulse

CONTEXT = {'socket': '/synthetic/pulse/native', 'instance': 'fixture'}


class EventTests(unittest.TestCase):
    def run_stream(self, payload, probe=None):
        self.children, self.commands, self.lines = [], [], []
        def spawn(argv, **kwargs):
            self.commands.append((argv, kwargs))
            self.assertEqual(argv, ['/usr/bin/pactl', '--server=unix:/synthetic/pulse/native',
                                   '--client-name=omabuntu-audio-events', 'subscribe'])
            self.assertNotIn('PULSE_COOKIE', kwargs['env'])
            self.assertEqual(kwargs['env']['HOME'], '/nonexistent')
            # Only this fixed disposable diagnostic subprocess is executed.
            child = subprocess.Popen([sys.executable, '-I', '-c',
                'import sys,time;sys.stdout.buffer.write(' + repr(payload) + ');sys.stdout.flush();time.sleep(.15)'], **kwargs)
            self.children.append(child)
            return child
        binary = SimpleNamespace(st_mode=stat.S_IFREG | 0o755, st_uid=0)
        with patch.object(Path, 'lstat', return_value=binary), patch.object(os, 'access', return_value=True):
            events.subscribe(self.lines.append, probe=probe or (lambda: copy.deepcopy(CONTEXT)), popen=spawn)

    def test_ready_and_only_reviewed_facilities_invalidate_without_forwarding_contents(self):
        self.run_stream(b"Event 'new' on sink #1\nEvent 'change' on source #2\nEvent 'change' on sink-input #3\nprivate junk\nEvent 'remove' on card #4\n")
        self.assertEqual(self.lines, ['ready', 'changed', 'changed', 'changed'])
        self.assertEqual(len(self.commands), 1)
        self.assertTrue(all(c.poll() is not None and c.stdout.closed for c in self.children))

    def test_context_drift_revokes_before_event_emission_and_cleans_child(self):
        reads = 0
        def probe():
            nonlocal reads
            reads += 1
            return {**CONTEXT, 'instance': 'changed' if reads > 2 else 'fixture'}
        with self.assertRaisesRegex(pulse.AudioError, 'server-context-changed'):
            self.run_stream(b"Event 'change' on sink #1\n", probe)
        self.assertEqual(self.lines, ['ready'])
        self.assertTrue(all(c.poll() is not None for c in self.children))

    def test_oversized_line_and_partial_frame_are_bounded(self):
        for payload in (b'x' * 129 + b'\n', b'x' * 9000):
            with self.subTest(length=len(payload)), self.assertRaisesRegex(pulse.AudioError, 'audio-event-frame-limit'):
                self.run_stream(payload)
            self.assertTrue(all(c.poll() is not None for c in self.children))

    def test_unrecognized_facility_flood_is_bounded_too(self):
        with self.assertRaisesRegex(pulse.AudioError, 'audio-event-rate-limit'):
            self.run_stream(b'ignored\n' * 257)
        self.assertEqual(self.lines, ['ready'])

    def test_stream_end_has_no_reconnect_or_setter(self):
        self.run_stream(b'')
        self.assertEqual(len(self.commands), 1)
        self.assertEqual(self.lines, ['ready'])

    def test_cli_has_separate_query_and_transport_risk_grants(self):
        with patch.object(events, 'subscribe') as subscribe:
            self.assertEqual(events.main([]), 2)
            self.assertEqual(events.main(['--allow-existing-user-audio-queries']), 2)
            subscribe.assert_not_called()


if __name__ == '__main__': unittest.main()
