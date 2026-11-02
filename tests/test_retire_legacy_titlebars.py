"""Legacy titlebar retirement contracts (plan 075). No live files."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import retire_legacy_titlebars as retire


LEGACY_ENTRY = '''-- private profile
require("omabuntu-managed")

-- Floating-workspace titlebar buttons (hyprbars). The sibling file is
-- the reviewed Omarchy snippet.
require("hyprbars")

-- hyprpm's enabled flag is bookkeeping, not a compositor load.
-- The legacy artifact fails the version check.
hl.on("hyprland.start", function()
    local loaded = false
    for _, plugin in ipairs(hl.get_loaded_plugins() or {}) do
        if plugin.name == "hyprbars" then
            loaded = true
        end
    end
    if not loaded then
        hl.plugin.load("/var/cache/hyprpm/example/hyprland-plugins/hyprbars.so")
    end
end)
'''

CLEAN_ENTRY = '''-- private profile
require("omabuntu-managed")
'''


class RetirementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'home'
        self.hypr = self.home / '.config/hypr'
        self.hypr.mkdir(parents=True)
        os.environ.pop('XDG_CONFIG_HOME', None)

    def write_entry(self, text):
        (self.hypr / 'hyprland.lua').write_text(text)

    def write_supports(self):
        (self.hypr / 'omabuntu-activation.lua').write_text('-- granted\n')
        (self.hypr / 'hyprbars.lua').write_text('-- private rules\n')

    def test_review_detects_the_exact_legacy_wiring_read_only(self):
        self.write_entry(LEGACY_ENTRY)
        self.write_supports()
        before = (self.hypr / 'hyprland.lua').read_text()
        info = retire.review(self.home)
        self.assertTrue(info['require_line'])
        self.assertTrue(info['handler'])
        self.assertFalse(info['handler_unknown'])
        self.assertTrue(info['managed_include'])
        self.assertTrue(info['activation_exist'])
        self.assertTrue(info['rules_exist'])
        self.assertGreater(info['lines'], 10)
        self.assertEqual(before, (self.hypr / 'hyprland.lua').read_text())

    def test_review_flags_an_unknown_handler_shape(self):
        text = LEGACY_ENTRY.replace('local loaded = false', 'local custom = true')
        self.write_entry(text)
        self.write_supports()
        info = retire.review(self.home)
        self.assertTrue(info['handler_unknown'])
        with self.assertRaises(ValueError):
            retire.apply(self.home)
        self.assertIn('require("hyprbars")', (self.hypr / 'hyprland.lua').read_text())

    def test_apply_removes_the_blocks_and_retires_the_rules_file(self):
        self.write_entry(LEGACY_ENTRY)
        self.write_supports()
        result = retire.apply(self.home)
        self.assertTrue(result['changed'])
        entry = (self.hypr / 'hyprland.lua').read_text()
        self.assertNotIn('require("hyprbars")', entry)
        self.assertNotIn('hyprland.start', entry)
        self.assertIn('require("omabuntu-managed")', entry)
        self.assertTrue(entry.endswith('\n'))
        self.assertFalse((self.hypr / 'hyprbars.lua').exists())
        backups = list(self.hypr.glob('hyprbars.lua.bak-*'))
        self.assertEqual(len(backups), 1)
        entry_backups = list(self.hypr.glob('hyprland.lua.bak-*'))
        self.assertEqual(len(entry_backups), 1)
        self.assertIn('require("hyprbars")', entry_backups[0].read_text())

    def test_apply_is_a_noop_without_legacy_wiring(self):
        self.write_entry(CLEAN_ENTRY)
        self.write_supports()
        result = retire.apply(self.home)
        self.assertFalse(result['changed'])
        self.assertEqual((self.hypr / 'hyprland.lua').read_text(), CLEAN_ENTRY)
        self.assertEqual(list(self.hypr.glob('*.bak-*')), [])

    def test_apply_refuses_without_a_rules_carrier(self):
        self.write_entry(LEGACY_ENTRY.replace('require("omabuntu-managed")\n', ''))
        self.write_supports()
        with self.assertRaises(ValueError):
            retire.apply(self.home)
        self.assertIn('require("hyprbars")', (self.hypr / 'hyprland.lua').read_text())

    def test_apply_refuses_without_the_granted_activation(self):
        self.write_entry(LEGACY_ENTRY)
        (self.hypr / 'hyprbars.lua').write_text('-- private rules\n')
        with self.assertRaises(ValueError):
            retire.apply(self.home)
        self.assertIn('require("hyprbars")', (self.hypr / 'hyprland.lua').read_text())
        self.assertTrue((self.hypr / 'hyprbars.lua').exists())

    def test_rollback_restores_entry_and_rules(self):
        self.write_entry(LEGACY_ENTRY)
        self.write_supports()
        retire.apply(self.home)
        result = retire.rollback(self.home)
        self.assertEqual((self.hypr / 'hyprland.lua').read_text(), LEGACY_ENTRY)
        self.assertTrue((self.hypr / 'hyprbars.lua').exists())
        self.assertTrue(result['entry_backup'])
        self.assertTrue(result['rules'])

    def test_rollback_without_backups_changes_nothing(self):
        self.write_entry(CLEAN_ENTRY)
        result = retire.rollback(self.home)
        self.assertIsNone(result['entry_backup'])
        self.assertIsNone(result['rules'])
        self.assertEqual((self.hypr / 'hyprland.lua').read_text(), CLEAN_ENTRY)


if __name__ == '__main__':
    unittest.main()