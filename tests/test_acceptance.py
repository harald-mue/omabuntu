"""Acceptance gates stay read-only and never claim a native login."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import acceptance


class AcceptanceTests(unittest.TestCase):
    def test_review_never_accepts_login_or_installs(self):
        done = acceptance.gate('host', 'done', 'ok')
        with patch.object(acceptance, 'host_gate', return_value=done), \
             patch.object(acceptance, 'ppa_gate', return_value=acceptance.gate('ppa', 'done', 'ok')), \
             patch.object(acceptance, 'packages_gate', return_value=acceptance.gate('packages', 'done', 'ok')), \
             patch.object(acceptance, 'font_gate', return_value=acceptance.gate('font', 'done', 'ok')), \
             patch.object(acceptance, 'bundle_gate', return_value=acceptance.gate('bundle', 'done', 'ok')), \
             patch.object(acceptance, 'session_gate', return_value=acceptance.gate('session', 'done', 'ok')), \
             patch.object(acceptance, 'activation_gate', return_value=acceptance.gate('activation', 'done', 'ok')):
            reviewed = acceptance.review(ROOT, installation=object())
        self.assertFalse(reviewed['accepted'])
        self.assertFalse(reviewed['starts_desktop'])
        self.assertFalse(reviewed['packages_installed'])
        self.assertTrue(reviewed['ready_for_native_login'])
        self.assertEqual(reviewed['gates'][-1]['status'], 'manual')

    def test_blocked_gate_is_not_ready(self):
        with patch.object(acceptance, 'host_gate', return_value=acceptance.gate('host', 'blocked', 'wrong system')), \
             patch.object(acceptance, 'ppa_gate', return_value=acceptance.gate('ppa', 'done', 'ok')), \
             patch.object(acceptance, 'packages_gate', return_value=acceptance.gate('packages', 'done', 'ok')), \
             patch.object(acceptance, 'font_gate', return_value=acceptance.gate('font', 'done', 'ok')), \
             patch.object(acceptance, 'bundle_gate', return_value=acceptance.gate('bundle', 'done', 'ok')), \
             patch.object(acceptance, 'session_gate', return_value=acceptance.gate('session', 'done', 'ok')), \
             patch.object(acceptance, 'activation_gate', return_value=acceptance.gate('activation', 'done', 'ok')):
            reviewed = acceptance.review(ROOT, installation=object())
        self.assertFalse(reviewed['ready_for_native_login'])
        self.assertFalse(reviewed['accepted'])
