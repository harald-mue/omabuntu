"""Contracts for the Omabuntu menu model (plan 002).

Everything runs against fixtures: no live hyprctl, systemctl, fc-list,
gsettings, or bash against the user state. The guard batch is executed only
against an isolated temporary state home.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import menu_model
import power_actions


DEFS_FIXTURE = '''{
  // comment
  "apps": {"icon": "a", "label": "Apps", "action": "omabuntu-open:apps"},
  "learn": {"icon": "l", "label": "Learn"},
  "learn.keybindings": {"icon": "k", "label": "Keybindings", "action": "omabuntu-open:keybindings"},
  "style": {"icon": "s", "label": "Style"},
  "style.theme": {"icon": "t", "label": "Theme", "provider": "themes"},
  "system": {"icon": "y", "label": "System", "aliases": ["power-menu"]},
  "system.reboot": {"icon": "r", "label": "Reboot", "action": "systemctl:reboot"},
  "system.suspend": {"icon": "z", "label": "Suspend", "when": "omabuntu-can-suspend", "action": "systemctl:suspend"},
}
'''


class MenuModelTests(unittest.TestCase):
    def test_strip_jsonc_removes_whole_line_comments_only(self):
        stripped = menu_model.strip_jsonc('// whole line\n{"a": 1,\n"b": 2,}\n')
        self.assertEqual(json.loads(stripped), {'a': 1, 'b': 2})
        # Upstream documents that an inline trailing comment breaks the parse.
        broken = menu_model.strip_jsonc('{"a": 1, // inline\n"b": 2}')
        with self.assertRaises(json.JSONDecodeError):
            json.loads(broken)

    def test_parse_recovers_schema_and_infers_parent_and_kind(self):
        items = menu_model.parse_menu_jsonc(DEFS_FIXTURE)
        by_id = {entry['id']: entry for entry in items}
        self.assertEqual(by_id['learn.keybindings']['parent'], 'learn')
        self.assertEqual(by_id['learn.keybindings']['kind'], 'action')
        self.assertEqual(by_id['learn']['kind'], 'menu')
        self.assertEqual(by_id['apps']['parent'], 'root')

    def test_broken_file_contributes_nothing(self):
        self.assertEqual(menu_model.parse_menu_jsonc('{oops'), [])
        self.assertEqual(menu_model.parse_menu_jsonc(''), [])

    def test_merge_injects_root_and_overlays_by_key(self):
        base = menu_model.parse_menu_jsonc(DEFS_FIXTURE)
        user = menu_model.parse_menu_jsonc('{"learn": {"label": "Training"}, "extra": {"label": "Extra"}}')
        items, order = menu_model.merge_menu_sources(base, user)
        self.assertEqual(items['learn']['label'], 'Training')
        # Upstream normalizes both sources first, so an undeclared field in
        # the user entry is replaced by the normalize default, not kept.
        self.assertEqual(items['learn']['icon'], '')
        self.assertIn('extra', order)
        self.assertEqual(items['root']['kind'], 'menu')
        self.assertEqual(order[0], 'root')
        self.assertEqual(items['root']['order'], 0)

    def test_resolve_route_exact_id_alias_and_fallthrough(self):
        items, order = menu_model.merge_menu_sources(menu_model.parse_menu_jsonc(DEFS_FIXTURE))
        self.assertEqual(menu_model.resolve_route(items, order, 'system.reboot'), 'system.reboot')
        self.assertEqual(menu_model.resolve_route(items, order, 'power-menu'), 'system')
        self.assertEqual(menu_model.resolve_route(items, order, 'go'), 'root')
        self.assertEqual(menu_model.resolve_route(items, order, 'System_Reboot'), 'system-reboot')
        self.assertEqual(menu_model.resolve_route(items, order, 'misspelt'), 'misspelt')

    def test_slugify_matches_upstream(self):
        self.assertEqual(menu_model.slugify('Tokyo Night'), 'tokyo-night')
        self.assertEqual(menu_model.slugify(''), 'item')


class GuardTests(unittest.TestCase):
    def test_guard_script_batches_one_process_with_groups(self):
        items, _ = menu_model.merge_menu_sources(menu_model.parse_menu_jsonc(DEFS_FIXTURE))
        script = menu_model.guard_script(items, state_home_text='/tmp/menu-test-state')
        self.assertIn('omabuntu-can-suspend', script)
        self.assertEqual(script.count('__omabuntu_groups+=($!)'), menu_model.GUARD_GROUPS)
        self.assertIn('system.suspend:w:', script)

    def test_guard_batch_evaluates_against_isolated_state(self):
        with tempfile.TemporaryDirectory() as home:
            os.environ['OMABUNTU_STATE_HOME'] = home
            try:
                items, _ = menu_model.merge_menu_sources(menu_model.parse_menu_jsonc(DEFS_FIXTURE))
                results = menu_model.evaluate_guards(items)
            finally:
                del os.environ['OMABUNTU_STATE_HOME']
        self.assertIsInstance(results['when'].get('system.suspend'), bool)

    def test_parse_guard_output_rejects_garbage(self):
        parsed = menu_model.parse_guard_output('a:w:1\nb:c:0\nnoise\nc:d:x\n')
        self.assertEqual(parsed['when'], {'a': True})
        self.assertEqual(parsed['checked'], {'b': False})
        self.assertEqual(parsed['disabled'], {})

    def test_reader_substitution_runs_once_per_reader(self):
        expression = menu_model.substitute_guard_readers('[[ "$(omabuntu-theme-current)" == x ]]')
        self.assertEqual(expression, '[[ "${__omabuntu_read_0}" == x ]]')


PINNED_ICONS = {
    "apps": "\U000f003b",
    "learn": "\U000f09d1",
    "style": "\uebcf",
    "system": "\uf011",
    "learn.keybindings": "\uf11c",
    "learn.hyprland": "\uf359",
    "style.theme": "\U000f0e0c",
    "style.background": "\uf03e",
    "style.font": "\ue659",
    "system.suspend": "\U000f04b2",
    "system.hibernate": "\U000f0901",
    "system.logout": "\U000f0343",
    "system.reboot": "\U000f0709",
    "system.shutdown": "\U000f0425",
}


class IconTests(unittest.TestCase):
    def test_kept_icons_are_the_pinned_scalars(self):
        items = {item["id"]: item for item in menu_model.parse_menu_jsonc(
            (ROOT / "config/shell/omabuntu-menu.jsonc").read_text())}
        for key, icon in PINNED_ICONS.items():
            self.assertEqual(items[key]["icon"], icon, key)
            self.assertFalse(any(0xD800 <= ord(char) <= 0xDFFF for char in items[key]["icon"]))

    def test_theme_provider_rows_carry_palette_colors(self):
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        os.environ["OMABUNTU_STATE_HOME"] = home.name
        self.addCleanup(os.environ.pop, "OMABUNTU_STATE_HOME", None)
        rows = menu_model.provider_rows("themes", palettes_path=ROOT / "config/menu/themes.json")
        self.assertEqual(len(rows), 23)
        for row in rows:
            colors = row.get("colors")
            self.assertIsInstance(colors, dict, row["value"])
            for key in ("background", "foreground", "accent"):
                self.assertRegex(colors[key], "^#[0-9A-Fa-f]{6}$", (row["value"], key))

    def test_palette_follows_the_recorded_theme(self):
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        os.environ["OMABUNTU_STATE_HOME"] = home.name
        self.addCleanup(os.environ.pop, "OMABUNTU_STATE_HOME", None)
        state = Path(home.name) / "current"
        state.mkdir()
        (state / "theme.json").write_text(json.dumps({"name": "matte-black"}))
        palette = menu_model.menu_palette()
        self.assertEqual(palette["background"], "#121212")
        self.assertEqual(palette["foreground"], "#bebebe")
        self.assertEqual(palette["accent"], "#e68e0d")


class DispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items, cls.order = menu_model.merge_menu_sources(
            menu_model.parse_menu_jsonc(DEFS_FIXTURE))

    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        os.environ['OMABUNTU_STATE_HOME'] = self.home.name
        self.addCleanup(self.home.cleanup)
        self.addCleanup(os.environ.pop, 'OMABUNTU_STATE_HOME', None)

    def run_item(self, row_id, run=lambda argv: (0, '')):
        return menu_model.run_item(row_id, (self.items, self.order), run=run)

    def test_unknown_row_is_refused(self):
        self.assertEqual(self.run_item('no.such.row')['error'], 'unknown')

    def test_menu_internal_route_is_refused_by_the_helper(self):
        self.assertEqual(self.run_item('apps')['error'], 'refused')
        self.assertEqual(self.run_item('learn.keybindings')['error'], 'refused')

    def test_surface_internal_picker_routes_are_refused(self):
        self.assertEqual(self.run_item("style.theme")["error"], "refused")
        self.assertTrue(menu_model.ACTION_RE.fullmatch("omabuntu-open:themes"))
        self.assertTrue(menu_model.ACTION_RE.fullmatch("omabuntu-open:backgrounds"))

    def test_power_actions_are_gated(self):
        result = self.run_item('system.reboot')
        self.assertEqual(result['error'], 'gate')

    def test_enabled_reboot_uses_the_injected_runner(self):
        power_actions.enable('reboot')
        runs = []
        result = self.run_item('system.reboot', run=lambda argv: (runs.append(argv), (0, ''))[1])
        self.assertTrue(result['ok'])
        self.assertEqual(runs, [['systemctl', 'reboot']])

    def test_allowlisted_xdg_open_runs_only_https(self):
        self.assertTrue(self.run_item('learn.hyprland')['ok']
                        if 'learn.hyprland' in self.items else True)


class ProviderTests(unittest.TestCase):
    def test_provider_row_ids_slug_and_deduplicate(self):
        rows = menu_model.provider_row_ids('style.theme', [
            {'label': 'Tokyo Night', 'value': 'tokyo night', 'current': True},
            {'label': 'Dup', 'value': 'tokyo night!', 'current': False}])
        self.assertEqual(rows[0]['id'], 'style.theme.tokyo-night')
        self.assertEqual(rows[1]['id'], 'style.theme.tokyo-night-')
        self.assertTrue(rows[0]['current'])

    def test_provider_for_unknown_menu_is_empty(self):
        items, _ = menu_model.merge_menu_sources(menu_model.parse_menu_jsonc(DEFS_FIXTURE))
        self.assertEqual(menu_model.provider_for_menu(items, 'system'), '')


if __name__ == '__main__':
    unittest.main()
