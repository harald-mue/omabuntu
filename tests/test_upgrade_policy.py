"""Upgrade policy stays closed. No APT command is executed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import upgrade_policy as policy


class UpgradePolicyTests(unittest.TestCase):
    def test_additions_do_not_require_an_upgrade_policy(self):
        decision = policy.classify({'new': ['git'], 'upgraded_or_changed': [], 'removed': []})
        self.assertFalse(decision['required'])
        self.assertTrue(decision['permitted'])

    def test_upgrades_and_native_packages_remain_refused(self):
        decision = policy.classify({'new': [], 'upgraded_or_changed': ['libssl3t64'], 'removed': []}, allow=('libssl3t64',))
        self.assertTrue(decision['required'])
        self.assertFalse(decision['permitted'])
        native = policy.classify({'new': [], 'upgraded_or_changed': ['hyprland'], 'removed': []}, allow=('hyprland',))
        self.assertFalse(native['permitted'])
        self.assertIn('refused', native['reason'])

    def test_removals_are_not_reclassified_as_upgrades(self):
        decision = policy.classify({'new': [], 'upgraded_or_changed': [], 'removed': ['git']})
        self.assertFalse(decision['required'])
        self.assertFalse(decision['permitted'])
