"""Guided setup contracts: one local stage, no system or desktop start."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import setup_guide as guide


def item(identifier, status, summary='fixture', command=''):
    return guide.stage(identifier, status, summary, command)


class GuideTests(unittest.TestCase):
    def review(self, statuses):
        order = ('host', 'ppa', 'packages', 'font', 'build', 'release', 'session', 'activation', 'login')
        stages = [item(name, statuses.get(name, 'done'), command='./install.sh --' + name) for name in order]
        return {'schema_version': 1, 'kind': 'omabuntu-setup-guide', 'root': str(ROOT),
                'stages': stages, 'next': next(name for name in order if statuses.get(name, 'done') != 'done'),
                'starts_desktop': False, 'installs_packages': False, 'ready_to_apply': False}

    def test_review_is_not_a_ready_installer_and_keeps_order(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory, \
             patch.object(guide, 'host_stage', return_value=item('host', 'done')), \
             patch.object(guide, 'font_stage', return_value=item('font', 'apply')), \
             patch.object(guide, 'build_stage', return_value=item('build', 'blocked', 'missing dependency')), \
             patch.object(guide, 'release_stage', return_value=item('release', 'blocked', 'build first')), \
             patch.object(guide, 'session_stage', return_value=item('session', 'blocked', 'later')), \
             patch.object(guide, 'activation_stage', return_value=item('activation', 'blocked', 'later')):
            reviewed = guide.review(ROOT, installation=object(), installed=lambda name: True,
                                    apt_root=Path(directory))
        self.assertEqual([item['id'] for item in reviewed['stages']],
                         ['host', 'ppa', 'packages', 'font', 'build', 'release', 'session', 'activation', 'login'])
        self.assertFalse(reviewed['ready_to_apply'])
        self.assertFalse(reviewed['starts_desktop'])
        self.assertFalse(reviewed['installs_packages'])
        self.assertEqual(reviewed['next'], 'ppa')
        self.assertFalse((Path(directory) / 'sources.list.d').exists())

    def test_apply_runs_only_the_next_local_stage(self):
        reviewed = self.review({'font': 'apply', 'build': 'apply'})
        calls = []
        runners = {'font': lambda: calls.append('font') or {'started': False},
                   'build': lambda: calls.append('build') or {'started': False}}
        result = guide.apply_next(reviewed, guide.guided.digest(reviewed), lambda item: True, runners)
        self.assertEqual(result['stage'], 'font')
        self.assertEqual(calls, ['font'])
        self.assertFalse(result['started'])
        self.assertFalse(result['installs_packages'])

    def test_system_manual_and_blocked_steps_are_not_applied(self):
        for status, name in (('command', 'ppa'), ('blocked', 'build'), ('manual', 'login')):
            reviewed = self.review({name: status})
            with self.assertRaises(ValueError):
                guide.apply_next(reviewed, guide.guided.digest(reviewed), lambda item: True, {})

    def test_declined_confirmation_calls_no_runner(self):
        reviewed = self.review({'session': 'apply'})
        result = guide.apply_next(reviewed, guide.guided.digest(reviewed), lambda item: False,
                                  {'session': lambda: (_ for _ in ()).throw(AssertionError('ran'))})
        self.assertEqual(result['status'], 'cancelled')

    def test_runner_that_starts_a_desktop_is_rejected(self):
        reviewed = self.review({'activation': 'apply'})
        with self.assertRaises(ValueError):
            guide.apply_next(reviewed, guide.guided.digest(reviewed), lambda item: True,
                             {'activation': lambda: {'started': True}})

    def test_package_probe_uses_status_not_installation(self):
        commands = []
        def installed(name):
            commands.append(name)
            return name != 'missing-package'
        with patch.object(guide.bootstrap_packages, 'request_manifest', return_value=(
                {'groups': {'runtime': ['present', 'missing-package']}}, {})):
            item = guide.packages_stage(installed)
        self.assertEqual(item['status'], 'command')
        self.assertIn('missing-package', item['summary'])
        self.assertNotIn('apt-get', item['command'])
        self.assertEqual(commands, ['present', 'missing-package'])

    def test_system_stage_becomes_apply_only_with_explicit_permission(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory, \
             patch.object(guide, 'host_stage', return_value=item('host', 'done')), \
             patch.object(guide, 'font_stage', return_value=item('font', 'done')), \
             patch.object(guide, 'build_stage', return_value=item('build', 'done', command=str(Path(directory)))), \
             patch.object(guide, 'release_stage', return_value=item('release', 'done')), \
             patch.object(guide, 'session_stage', return_value=item('session', 'done')), \
             patch.object(guide, 'activation_stage', return_value=item('activation', 'done')):
            denied = guide.review(ROOT, installation=object(), installed=lambda name: False, apt_root=Path(directory))
            allowed = guide.review(ROOT, installation=object(), installed=lambda name: False,
                                   apt_root=Path(directory), allow_system=True)
        self.assertEqual(denied['stages'][1]['status'], 'command')
        self.assertEqual(allowed['stages'][1]['status'], 'apply')
        self.assertFalse(allowed['installs_packages'])
        with self.assertRaises(ValueError):
            guide.apply_next(denied, guide.guided.digest(denied), lambda item: True, {})

    def test_unmanaged_ppa_duplicate_is_not_treated_as_a_setup_command(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            root = Path(directory)
            listed = root / 'sources.list.d'
            listed.mkdir()
            (root / 'sources.list').write_text('# empty\n')
            (listed / 'other.sources').write_text('URIs: https://ppa.launchpadcontent.net/cppiber/hyprland/ubuntu\n')
            item = guide.ppa_stage(root)
        self.assertEqual(item['status'], 'done')
        self.assertNotIn('--ppa', item['command'])
        self.assertIn('other.sources', item['summary'])
        self.assertIn('not be duplicated', item['summary'])

    def test_root_review_is_refused(self):
        with patch.object(guide.os, 'getuid', return_value=0), self.assertRaises(ValueError):
            guide.review()
