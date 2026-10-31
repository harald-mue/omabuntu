"""Pinned Nerd Font contracts; no network, real font-cache or desktop changes."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import desktop_font as font
import install as guided


class DesktopFontTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.data = b'font fixture bytes'
        self.pin = copy.deepcopy(font.inputs(ROOT))
        self.pin.update(bytes=len(self.data), sha256=hashlib.sha256(self.data).hexdigest())
        (self.root / 'licenses').mkdir()
        for item in self.pin['notices']:
            shutil.copyfile(ROOT / item['path'], self.root / item['path'])
        p = patch.object(font, 'inputs', return_value=self.pin)
        p.start()
        self.addCleanup(p.stop)
        p = patch.dict(os.environ, {'XDG_DATA_HOME': str(self.root / 'data'),
                                   'XDG_STATE_HOME': str(self.root / 'state')})
        p.start()
        self.addCleanup(p.stop)
        self.commands = []

    def execute(self, command, timeout=15):
        self.commands.append(command)
        if command[0] == 'fc-cache':
            return ''
        if 'charset' in command[1]:
            return '20-7e f000-f4ff f0000-f1fff\n'
        return self.pin['family'] + '\n'

    def fetch(self, url, limit):
        self.assertEqual(url, font.URL)
        self.assertEqual(limit, len(self.data))
        return self.data

    def plan(self):
        return font.plan(self.root, self.home)

    def apply(self, plan):
        return font.apply(plan, guided.digest(plan), fetch=self.fetch, execute=self.execute)

    def test_plan_has_no_download_or_directory_creation(self):
        plan = self.plan()
        self.assertFalse(plan['blockers'])
        self.assertFalse((self.root / 'data').exists())
        self.assertFalse((self.root / 'work').exists())

    def test_cache_is_verified_and_reused_without_registration(self):
        first = font.obtain(self.root, fetch=self.fetch, execute=self.execute)
        second = font.obtain(self.root, fetch=lambda *a: self.fail('redownload'), execute=self.execute)
        self.assertEqual(first, second)
        self.assertFalse(any(command[0] == 'fc-cache' for command in self.commands))
        first.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            font.obtain(self.root, fetch=self.fetch, execute=self.execute)

    def test_bad_download_is_not_published(self):
        with self.assertRaisesRegex(ValueError, 'Downloaded desktop font differs'):
            font.obtain(self.root, fetch=lambda *a: b'bad', execute=self.execute)
        self.assertFalse(list((self.root / 'work').rglob('*.ttf')))

    def test_stage_copies_font_and_notices_but_does_not_register(self):
        cached = font.obtain(self.root, fetch=self.fetch, execute=self.execute)
        output = self.root / 'bundle'
        font.stage(self.root, output, cached, execute=self.execute)
        self.assertEqual((output / 'assets/fonts' / font.FILENAME).read_bytes(), self.data)
        for record in self.pin['notices']:
            copied = output / 'licenses/desktop-font' / Path(record['path']).name
            self.assertEqual(hashlib.sha256(copied.read_bytes()).hexdigest(), record['sha256'])
        self.assertFalse(any(command[0] == 'fc-cache' for command in self.commands))

    def test_apply_installs_content_addressed_user_font_preserving_preferences(self):
        preference = self.root / 'state/omabuntu/current/font.txt'
        preference.parent.mkdir(parents=True)
        (self.root / 'state/omabuntu').chmod(0o700)
        preference.write_text('My chosen font\n')
        plan = self.plan()
        result = self.apply(plan)
        self.assertEqual(result['status'], 'installed-and-resolved')
        self.assertEqual((Path(plan['target']) / font.FILENAME).read_bytes(), self.data)
        self.assertEqual(preference.read_text(), 'My chosen font\n')
        self.assertFalse(result['preferences_changed'])
        self.assertFalse(result['desktop_restarted'])
        self.assertIn(['fc-cache', '-f', plan['target']], self.commands)
        record = json.loads(Path(result['journal']).read_text())
        self.assertTrue(all(not item['existed'] for item in record['plan']['before'].values()))

    def test_local_conflicts_and_symlinks_are_never_overwritten(self):
        plan = self.plan()
        target = Path(plan['target']) / font.FILENAME
        target.parent.mkdir(parents=True)
        target.write_bytes(b'personal font')
        self.assertTrue(self.plan()['blockers'])
        with self.assertRaises(ValueError):
            self.apply(plan)
        self.assertEqual(target.read_bytes(), b'personal font')
        target.unlink()
        target.symlink_to(self.root / 'elsewhere')
        with self.assertRaises(ValueError):
            self.plan()

    def test_failed_cache_refresh_leaves_evidence_not_user_font_removal(self):
        plan = self.plan()
        def fail_cache(command, timeout=15):
            if command[0] == 'fc-cache':
                raise ValueError('fixture failure')
            return self.execute(command, timeout)
        with self.assertRaises(ValueError):
            font.apply(plan, guided.digest(plan), fetch=self.fetch, execute=fail_cache)
        self.assertTrue((Path(plan['target']) / font.FILENAME).is_file())
        journal = next((self.root / 'state/omabuntu/font-transactions').glob('*/transaction.json'))
        self.assertEqual(json.loads(journal.read_text())['status'], 'incomplete-review-required')

    def test_approval_and_glyphs_are_checked(self):
        plan = self.plan()
        with self.assertRaises(ValueError):
            font.apply(plan, 'wrong', fetch=lambda *a: self.fail('download'))
        self.assertTrue(font.charset_contains('f000-f4ff f0000-f1fff', self.pin['required_glyphs']))
        self.assertFalse(font.charset_contains('20-7e', self.pin['required_glyphs']))
        self.assertFalse(font.charset_contains('not-hex', self.pin['required_glyphs']))
        self.assertFalse(font.charset_contains('f4ff-f000', self.pin['required_glyphs']))


class FontPinTests(unittest.TestCase):
    def test_checked_in_pin_and_notices_are_valid(self):
        pin = font.inputs(ROOT)
        self.assertEqual(pin['family'], 'JetBrainsMono Nerd Font')
        self.assertEqual(pin['bytes'], 2469104)
        self.assertEqual(pin['license'], 'OFL-1.1')
