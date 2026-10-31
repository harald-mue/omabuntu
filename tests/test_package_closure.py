"""Package closure summaries do not install or claim VM acceptance."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import package_closure as closure


class PackageClosureTests(unittest.TestCase):
    def test_summary_separates_dependencies_and_never_accepts_closure(self):
        payload = {'packages': ['hyprland', 'git'], 'pinned': ['git=1'],
                   'transaction': {'new': ['git', 'libgit'], 'upgraded_or_changed': [], 'removed': []},
                   'blockers': []}
        summary = closure.summarize(payload)
        self.assertEqual(summary['direct_additions'], ['git'])
        self.assertEqual(summary['dependency_additions'], ['libgit'])
        self.assertFalse(summary['closure_accepted'])
        self.assertFalse(summary['packages_installed'])

    def test_review_uses_the_injected_probe_and_does_not_apply(self):
        payload = {'packages': ['git'], 'pinned': [], 'transaction': {'new': [], 'upgraded_or_changed': [], 'removed': []},
                   'blockers': ['No APT candidate: git']}
        with patch.object(closure.bootstrap_packages, 'prepare', return_value={'payload': payload, 'blockers': payload['blockers']}) as prepare, \
             patch.object(closure.user_install, 'private_directory', side_effect=lambda path: path), \
             patch.object(closure.user_install, 'stamp', return_value='fixture'):
            summary = closure.review(ROOT, run=lambda argv: None)
        prepare.assert_called_once()
        self.assertEqual(summary['status'], 'blocked')
        self.assertFalse(summary['packages_installed'])
