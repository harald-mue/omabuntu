"""Contracts for the menu backends (plan 002). No live hyprctl, gsettings,
fc-list, systemctl, or user state: every runner and directory is injected.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import background_backend
import font_backend
import menu_common
import power_actions
import theme_backend


class TempState(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        os.environ['OMABUNTU_STATE_HOME'] = self.home.name
        self.addCleanup(self.home.cleanup)
        self.addCleanup(os.environ.pop, 'OMABUNTU_STATE_HOME', None)


class ThemeTests(TempState):
    def test_prettify_matches_upstream_list(self):
        self.assertEqual(theme_backend.prettify('tokyo-night'), 'Tokyo Night')
        self.assertEqual(theme_backend.prettify('catppuccin-latte'), 'Catppuccin Latte')

    def test_hyprland_colors_prefer_upstream_border_values(self):
        active, inactive = theme_backend.hyprland_colors({
            'accent': '#89b4fa', 'muted': '#585b70',
            'hyprland_active_border': 'rgba(26a269ee) rgba(2ec27eee) 45deg',
            'hyprland_inactive_border': 'rgba(584e51aa)'})
        self.assertEqual(active, 'rgba(26a269ee) rgba(2ec27eee) 45deg')
        self.assertEqual(inactive, 'rgba(584e51aa)')
        active, inactive = theme_backend.hyprland_colors({'accent': '#89b4fa', 'muted': '#585b70'})
        self.assertEqual(active, 'rgba(89b4faee)')
        self.assertEqual(inactive, 'rgba(585b70aa)')

    def test_bundled_palettes_load_with_all_upstream_themes(self):
        themes = theme_backend.themes()
        self.assertEqual(len(themes), 23)
        self.assertIn('gruvbox', themes)
        self.assertIn('catppuccin-latte', themes)

    def test_set_theme_writes_state_applies_live_and_backs_up(self):
        target = menu_common.state_home() / 'current' / 'theme.json'
        menu_common.write_json(target, {'name': 'nord'})
        runs = []

        def fake_run(argv):
            runs.append(argv)
            return 0, ''

        result = theme_backend.set_theme('gruvbox', run=fake_run)
        self.assertTrue(result['ok'])
        self.assertEqual(result['applied'], ['general:col.active_border', 'general:col.inactive_border'])
        state = json.loads(target.read_text())
        self.assertEqual(state['name'], 'gruvbox')
        backups = menu_common.state_home() / 'backups'
        self.assertTrue(any((directory / 'theme.json').is_file()
                           for directory in backups.iterdir()))
        self.assertTrue((menu_common.state_home() / 'operations.jsonl').is_file())

    def test_unknown_theme_is_refused(self):
        self.assertEqual(theme_backend.set_theme('nope', run=lambda a: (0, ''))['error'], 'unknown')

    def test_rewrite_border_colors_updates_only_the_two_literals(self):
        text = ('hl.config({\n'
                '    general = {\n'
                '        col = {\n'
                '            active_border = "rgb(7aa2f7)",\n'
                '            inactive_border = "rgb(414868)",\n'
                '        },\n'
                '    },\n'
                '})\n')
        rewritten = theme_backend.rewrite_border_colors(text, 'rgba(b59790ee)', 'rgba(584e51aa)')
        self.assertIn('active_border = "rgba(b59790ee)"', rewritten)
        self.assertIn('inactive_border = "rgba(584e51aa)"', rewritten)
        self.assertEqual(rewritten.count('rgba('), 2)
        self.assertEqual(theme_backend.rewrite_border_colors('nothing here', 'a', 'b'), None)

    def test_persist_border_colors_backs_up_and_writes(self):
        with tempfile.TemporaryDirectory() as config:
            config_path = Path(config) / 'hyprland.lua'
            config_path.write_text('active_border = "rgb(7aa2f7)"\ninactive_border = "rgb(414868)"\n')
            self.assertTrue(theme_backend.persist_border_colors('rgba(111111ee)', 'rgba(222222aa)',
                                                                config_path))
            text = config_path.read_text()
            self.assertIn('"rgba(111111ee)"', text)
            self.assertIn('"rgba(222222aa)"', text)
            backups = menu_common.state_home() / 'backups'
            self.assertTrue(any((directory / 'hyprland.lua').is_file()
                                for directory in backups.iterdir()))
            missing = theme_backend.persist_border_colors('x', 'y', Path(config) / 'absent.lua')
            self.assertFalse(missing)

    def test_rows_carry_the_imported_preview_image(self):
        with tempfile.TemporaryDirectory() as directory:
            previews = Path(directory) / 'themes-previews'
            previews.mkdir()
            for theme in theme_backend.themes():
                (previews / (theme + '.png')).write_bytes(b'fixture')
            with patch.object(theme_backend, 'PREVIEWS', previews):
                rows = theme_backend.rows()
            self.assertEqual(len(rows), 23)
            for row in rows:
                self.assertTrue(row['image'].endswith('/themes-previews/%s.png' % row['value']), row)

    def test_theme_rows_work_without_local_preview_images(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(theme_backend, 'PREVIEWS', Path(directory) / 'absent'):
                rows = theme_backend.rows()
            self.assertEqual(len(rows), 23)
            self.assertTrue(all(not row['image'] for row in rows))

    def test_theme_background_prefers_recorded_choice_then_first_still(self):
        with tempfile.TemporaryDirectory() as assets:
            theme_dir = Path(assets) / 'gruvbox'
            theme_dir.mkdir()
            (theme_dir / '0-first.jpg').write_bytes(b'x')
            (theme_dir / '1-second.jpg').write_bytes(b'x')
            self.assertEqual(theme_backend.theme_background('gruvbox', assets=assets),
                             str(theme_dir / '0-first.jpg'))
            chosen = str(theme_dir / '1-second.jpg')
            theme_backend.record_theme_background('gruvbox', chosen)
            self.assertEqual(theme_backend.theme_background('gruvbox', assets=assets), chosen)
            self.assertIsNone(theme_backend.theme_background('nord', assets=assets))

    def test_set_theme_persists_borders_and_applies_the_theme_background(self):
        with tempfile.TemporaryDirectory() as config, tempfile.TemporaryDirectory() as assets:
            config_path = Path(config) / 'hyprland.lua'
            config_path.write_text('active_border = "rgb(7aa2f7)"\ninactive_border = "rgb(414868)"\n')
            theme_dir = Path(assets) / 'gruvbox'
            theme_dir.mkdir()
            still = theme_dir / '0-forest.jpg'
            still.write_bytes(b'x')

            def fake_background_run(argv):
                return 1, ''

            result = theme_backend.set_theme('gruvbox', run=lambda a: (0, ''),
                                             config_path=config_path, assets=assets,
                                             background_run=fake_background_run)
            self.assertTrue(result['ok'])
            self.assertTrue(result['persisted'])
            # The theme's background is recorded through the reviewed path;
            # with no daemon answering, nothing is applied live.
            self.assertTrue(result['background'])
            state = json.loads((menu_common.state_home() / 'current' / 'theme.json').read_text())
            self.assertEqual(state['background'], str(still))
            self.assertIn('"rgba(7daea3ee)"', config_path.read_text())
            background = json.loads((menu_common.state_home() / 'current' / 'background.json').read_text())
            self.assertEqual(background['path'], str(still))
            self.assertFalse(background['applied'])

    def test_symlinked_palette_file_is_refused(self):
        with tempfile.TemporaryDirectory() as other:
            real = Path(other) / 'real.json'
            real.write_text('{"schema_version": 1, "themes": {"x": {}}}')
            link = Path(other) / 'link.json'
            link.symlink_to(real)
            self.assertEqual(theme_backend.themes(link), {})


class FontTests(TempState):
    def test_families_parse_and_dedupe(self):
        self.assertEqual(font_backend.families('A\nB\nA\n'), ['A', 'B'])

    def test_gsettings_font_keeps_previous_size(self):
        self.assertEqual(font_backend.gsettings_font('Inter', 'Ubuntu 12'), 'Inter 12')
        self.assertEqual(font_backend.gsettings_font('Inter', None), 'Inter 11')

    def test_set_font_records_state_and_gtk(self):
        runs = []

        def fake_run(argv):
            runs.append(argv)
            if argv[1] == 'get':
                return 0, "'Ubuntu Sans 12'\n"
            return 0, ''

        result = font_backend.set_font('Ubuntu Sans', available=['Ubuntu Sans'], run=fake_run)
        self.assertTrue(result['ok'])
        self.assertTrue(result['gtk'])
        self.assertIn(['gsettings', 'set', 'org.gnome.desktop.interface', 'font-name', 'Ubuntu Sans 12'], runs)
        self.assertEqual((menu_common.state_home() / 'current' / 'font.txt').read_text().strip(),
                         'Ubuntu Sans')

    def test_unknown_font_is_refused(self):
        self.assertEqual(font_backend.set_font('Nope', available=['Ubuntu Sans'])['error'], 'unknown')

    def test_gsettings_run_rejects_other_keys(self):
        with self.assertRaises(ValueError):
            font_backend.gsettings_run(['gsettings', 'set', 'org.gnome.desktop.interface', 'text-scaling-factor', '2'])

    def test_fontconfig_xml_substitutes_and_escapes(self):
        xml = font_backend.fontconfig_xml('A & B <Ltd>')
        self.assertIn('<string>A &amp; B &lt;Ltd&gt;</string>', xml)
        for needle in ('monospace', 'prepend_first', 'binding="strong"'):
            self.assertIn(needle, xml)

    def test_rewrite_ghostty_font_handles_quoted_bare_and_absent(self):
        quoted = font_backend.rewrite_ghostty_font('font-family = "Old"\n', 'New')
        self.assertEqual(quoted, 'font-family = "New"\n')
        bare = font_backend.rewrite_ghostty_font('font-family = Old\n', 'New')
        self.assertEqual(bare, 'font-family = "New"\n')
        self.assertIsNone(font_backend.rewrite_ghostty_font('theme = dark\n', 'New'))

    def test_set_font_writes_fontconfig_and_ghostty_with_backup(self):
        with tempfile.TemporaryDirectory() as config:
            ghostty_dir = Path(config) / 'ghostty'
            ghostty_dir.mkdir()
            (ghostty_dir / 'config').write_text('font-family = "Old"\n')
            signals = []

            def fake_run(argv):
                if argv[1] == 'get':
                    return 0, "'Ubuntu Sans 12'\n"
                return 0, ''

            result = font_backend.set_font('Ubuntu Sans', available=['Ubuntu Sans'], run=fake_run,
                                            signal_run=lambda argv: signals.append(argv) or (0, ''),
                                            config=config)
            self.assertTrue(result['ok'])
            self.assertTrue(result['gtk'])
            self.assertTrue(result['fontconfig'])
            self.assertEqual(result['ghostty'], [str(ghostty_dir / 'config')])
            fonts_conf = Path(config) / 'fontconfig' / 'fonts.conf'
            self.assertIn('<string>Ubuntu Sans</string>', fonts_conf.read_text())
            self.assertEqual((ghostty_dir / 'config').read_text(), 'font-family = "Ubuntu Sans"\n')
            self.assertEqual(signals, [['pkill', '-SIGUSR2', '-x', 'ghostty']])
            backups = menu_common.state_home() / 'backups'
            names = {path.name for directory in backups.iterdir() for path in directory.iterdir()}
            self.assertIn('config', names)
            # A second apply finds the previous fonts.conf and backs it up.
            font_backend.set_font('Ubuntu Mono', available=['Ubuntu Mono'], run=fake_run,
                                 signal_run=lambda argv: (0, ''), config=config)
            names = {path.name for directory in backups.iterdir() for path in directory.iterdir()}
            self.assertIn('fonts.conf', names)

    def test_set_font_skips_ghostty_without_a_config(self):
        with tempfile.TemporaryDirectory() as config:
            result = font_backend.set_font('Ubuntu Sans', available=['Ubuntu Sans'],
                                            run=lambda argv: (0, "'Ubuntu 11'\n") if argv[1] == 'get' else (0, ''),
                                            signal_run=lambda argv: (0, ''), config=config)
            self.assertTrue(result['ok'])
            self.assertEqual(result['ghostty'], [])

    def test_pkill_run_refuses_other_targets(self):
        with self.assertRaises(ValueError):
            font_backend.pkill_run(['pkill', '-SIGUSR2', '-x', 'kitty'])
        with self.assertRaises(ValueError):
            font_backend.pkill_run(['pkill', '-9', 'ghostty'])


class BackgroundTests(TempState):
    def setUp(self):
        super().setUp()
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.base = Path(self.dir.name)
        (self.base / 'one.jpg').write_bytes(b'x')
        (self.base / 'two.png').write_bytes(b'x')
        (self.base / 'note.txt').write_text('no')

    def test_rows_list_images_with_current_flag(self):
        rows = background_backend.rows([self.base])
        self.assertEqual([row['value'] for row in rows],
                         [str(self.base / 'one.jpg'), str(self.base / 'two.png')])
        self.assertFalse(any(row['current'] for row in rows))

    def test_set_records_only_listed_files(self):
        result = background_backend.set_background(str(self.base / 'one.jpg'), dirs=[self.base],
                                                  run=lambda argv, timeout=5: (1, ''))
        self.assertTrue(result['ok'])
        self.assertFalse(result['applied'])
        self.assertTrue(result['lock_background'])
        self.assertEqual(background_backend.current(), str(self.base / 'one.jpg'))
        link = menu_common.state_home() / 'current' / 'lock-background'
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), str((self.base / 'one.jpg').resolve()))

    def test_publish_leaves_a_regular_file_in_place(self):
        link = menu_common.state_home() / 'current' / 'lock-background'
        link.write_text('keep')
        self.assertFalse(background_backend.publish_lock_background(self.base / 'one.jpg'))
        self.assertEqual(link.read_text(), 'keep')
        self.assertFalse(link.is_symlink())

    def test_set_refuses_outside_files_and_symlinks(self):
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / 'outside.jpg'
            outside.write_bytes(b'x')
            self.assertEqual(background_backend.set_background(str(outside), dirs=[self.base])['error'],
                             'refused')
        link = self.base / 'link.png'
        link.symlink_to(self.base / 'one.jpg')
        self.assertEqual(background_backend.set_background(str(link), dirs=[self.base])['error'],
                         'unknown')

    def test_theme_backgrounds_list_first_when_a_theme_is_current(self):
        with tempfile.TemporaryDirectory() as assets:
            theme_dir = Path(assets) / 'gruvbox'
            theme_dir.mkdir()
            still = theme_dir / '0-forest.jpg'
            still.write_bytes(b'x')
            menu_common.write_json(menu_common.state_home() / 'current' / 'theme.json',
                                   {'name': 'gruvbox'})
            files = background_backend.backgrounds([self.base], assets=assets)
            self.assertEqual(str(files[0]), str(still))
            self.assertIn(str(self.base / 'one.jpg'), [str(path) for path in files])

    def test_allowed_paths_include_every_theme_still(self):
        with tempfile.TemporaryDirectory() as assets:
            theme_dir = Path(assets) / 'gruvbox'
            theme_dir.mkdir()
            still = theme_dir / '0-forest.jpg'
            still.write_bytes(b'x')
            allowed = background_backend.allowed_paths([self.base], assets=assets)
            self.assertIn(str(still.resolve()), allowed)
            self.assertIn(str((self.base / 'one.jpg').resolve()), allowed)

    def test_apply_background_uses_the_current_hyprpaper_request(self):
        calls = []

        def fake_run(argv, timeout=5):
            calls.append(argv)
            if argv[1] == 'monitors':
                return 0, '[{"name": "DP-1"}, {"name": "HDMI-A-1"}]'
            return 0, ''

        result = background_backend.apply_background('/tmp/wall.jpg', run=fake_run)
        self.assertTrue(result['ok'])
        self.assertEqual(calls[0], ['hyprctl', 'monitors', '-j'])
        self.assertIn(['hyprctl', 'hyprpaper', 'wallpaper', 'DP-1,/tmp/wall.jpg'], calls)
        self.assertIn(['hyprctl', 'hyprpaper', 'wallpaper', 'HDMI-A-1,/tmp/wall.jpg'], calls)
        self.assertNotIn(['hyprctl', 'hyprpaper', 'preload', '/tmp/wall.jpg'], calls)
        self.assertEqual(len(calls), 3)

    def test_apply_background_falls_back_to_the_legacy_sequence(self):
        calls = []

        def fake_run(argv, timeout=5):
            calls.append(argv)
            if argv[1] == 'monitors':
                return 0, '[{"name": "DP-1"}]'
            # Before the legacy preload the current request is rejected.
            if argv[2] == 'wallpaper' and not any(call[2] == 'preload' for call in calls):
                return 1, 'error: invalid hyprpaper request'
            return 0, ''

        result = background_backend.apply_background('/tmp/wall.jpg', run=fake_run)
        self.assertTrue(result['ok'])
        self.assertIn(['hyprctl', 'hyprpaper', 'preload', '/tmp/wall.jpg'], calls)
        self.assertEqual(calls[-1], ['hyprctl', 'hyprpaper', 'unload', 'all'])

    def test_apply_background_fails_closed_without_a_daemon(self):
        self.assertEqual(background_backend.apply_background('/tmp/wall.jpg', run=lambda a, t=5: (1, '')),
                         {'ok': False, 'method': 'hyprpaper'})
        failing = {'wallpaper': (1, ''), 'preload': (1, '')}

        def fake_run(argv, timeout=5):
            if argv[1] == 'monitors':
                return 0, '[{"name": "DP-1"}]'
            return failing.get(argv[2], (0, ''))

        self.assertFalse(background_backend.apply_background('/tmp/wall.jpg', run=fake_run)['ok'])

    def test_hyprctl_run_rejects_other_commands(self):
        with self.assertRaises(ValueError):
            background_backend.hyprctl_run(['hyprctl', 'dispatch', 'exec', 'x'])
        with self.assertRaises(ValueError):
            background_backend.hyprctl_run(['hyprctl', 'hyprpaper', 'wallpaper'])
        with self.assertRaises(ValueError):
            background_backend.hyprctl_run(['hyprctl', 'hyprpaper', 'bogus', 'x'])

    def test_set_background_marks_applied_when_the_daemon_answers(self):
        def fake_run(argv, timeout=5):
            if argv[1] == 'monitors':
                return 0, '[{"name": "DP-1"}]'
            return 0, ''

        result = background_backend.set_background(str(self.base / 'one.jpg'), dirs=[self.base],
                                                   run=fake_run)
        self.assertTrue(result['ok'])
        self.assertTrue(result['applied'])
        payload = json.loads((menu_common.state_home() / 'current' / 'background.json').read_text())
        self.assertTrue(payload['applied'])
        self.assertTrue(result['lock_background'])


class PowerTests(TempState):
    def test_availability_follows_kernel_states(self):
        self.assertTrue(power_actions.can_suspend('freeze mem disk'))
        self.assertFalse(power_actions.can_suspend('disk'))
        self.assertTrue(power_actions.can_hibernate('freeze mem disk'))
        self.assertFalse(power_actions.can_hibernate('freeze mem'))

    def test_unknown_verb_is_refused(self):
        self.assertEqual(power_actions.perform('explode')['error'], 'refused')

    def test_gates_block_every_verb(self):
        for verb in ('suspend', 'logout', 'reboot', 'shutdown', 'hibernate', 'poweroff'):
            result = power_actions.perform(verb, run=lambda a: (0, ''),
                                            states='freeze mem disk')
            self.assertEqual(result['error'], 'gate', verb)

    def test_hibernate_needs_disk_even_when_enabled(self):
        power_actions.enable('hibernate')
        result = power_actions.perform('hibernate', run=lambda a: (0, ''), states='freeze mem')
        self.assertEqual(result['error'], 'refused')
        self.assertEqual(result['message'], 'Hibernate is not available.')

    def test_enabled_hibernate_runs_systemctl_hibernate(self):
        power_actions.enable('hibernate')
        runs = []
        result = power_actions.perform('hibernate', run=lambda argv: (runs.append(argv), (0, ''))[1],
                                        states='freeze mem disk')
        self.assertTrue(result['ok'])
        self.assertEqual(runs, [['systemctl', 'hibernate']])

    def test_poweroff_uses_the_shutdown_gate(self):
        power_actions.enable('poweroff')
        self.assertEqual(power_actions.gates(), {'shutdown': True})
        runs = []
        result = power_actions.perform('poweroff', run=lambda argv: (runs.append(argv), (0, ''))[1],
                                        states='freeze mem disk')
        self.assertTrue(result['ok'])
        self.assertEqual(runs, [['systemctl', 'poweroff']])

    def test_enabled_gate_runs_the_exact_command(self):
        runs = []

        def fake_run(argv):
            runs.append(argv)
            return 0, ''

        power_actions.enable('reboot')
        result = power_actions.perform('reboot', run=fake_run, states='freeze mem disk')
        self.assertTrue(result['ok'])
        self.assertEqual(runs, [['systemctl', 'reboot']])

    def test_logout_maps_to_uwsm_stop(self):
        power_actions.enable('logout')
        runs = []
        result = power_actions.perform('logout', run=lambda argv: (runs.append(argv), (0, ''))[1],
                                        states='freeze mem disk')
        self.assertTrue(result['ok'])
        self.assertEqual(runs, [['uwsm', 'stop']])

    def test_live_run_rejects_anything_else(self):
        with self.assertRaises(ValueError):
            power_actions.live_run(['systemctl', 'poweroff', 'now'])
        with self.assertRaises(ValueError):
            power_actions.live_run(['bash', '-c', 'true'])


if __name__ == '__main__':
    unittest.main()


class BackgroundRestoreTests(TempState):
    """Plan 020 login restore of the recorded background."""

    def setUp(self):
        super().setUp()
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.assets = Path(self.dir.name)
        theme = self.assets / 'tokyo-night'
        theme.mkdir()
        (theme / '1-winding-road.webp').write_bytes(b'x')

    def record(self, path):
        menu_common.write_json(menu_common.state_home() / 'current' / 'background.json',
                               {'schema_version': 1, 'path': str(path), 'applied': True})

    def daemon(self, monitors=('eDP-1', 'DP-5')):
        calls = []

        def run(argv, timeout=5):
            calls.append(list(argv))
            if argv[1:3] == ['monitors', '-j']:
                return 0, json.dumps([{'name': name} for name in monitors])
            return 0, 'ok'

        return run, calls

    def test_unrecorded_and_missing_are_reported_not_raised(self):
        self.assertEqual(background_backend.restore_background()['error'], 'unrecorded')
        self.record(self.assets / 'tokyo-night' / 'gone.webp')
        self.assertEqual(background_backend.restore_background()['error'], 'missing')

    def test_restore_rebases_onto_the_selected_release_and_applies_per_monitor(self):
        stale = '/old/release/config/menu/backgrounds/tokyo-night/1-winding-road.webp'
        self.record(stale)
        run, calls = self.daemon()
        result = background_backend.restore_background(run=run, assets=self.assets)
        self.assertTrue(result['ok'])
        self.assertEqual(result['path'], str(self.assets / 'tokyo-night' / '1-winding-road.webp'))
        self.assertEqual(calls[0], ['hyprctl', 'monitors', '-j'])
        self.assertEqual(calls[1:], [['hyprctl', 'hyprpaper', 'wallpaper',
                                      'eDP-1,' + str(self.assets / 'tokyo-night' / '1-winding-road.webp')],
                                     ['hyprctl', 'hyprpaper', 'wallpaper',
                                      'DP-5,' + str(self.assets / 'tokyo-night' / '1-winding-road.webp')]])
        link = menu_common.state_home() / 'current' / 'lock-background'
        self.assertEqual(os.readlink(link),
                         str((self.assets / 'tokyo-night' / '1-winding-road.webp').resolve()))
        self.assertTrue(result['lock_background'])
        # A restore never re-records the choice.
        self.assertEqual(json.loads((menu_common.state_home() / 'current' / 'background.json').read_text())['path'],
                         stale)

    def test_restore_refuses_files_outside_the_listed_directories(self):
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / 'outside.webp'
            outside.write_bytes(b'x')
            self.record(outside)
            run, _ = self.daemon()
            self.assertEqual(background_backend.restore_background(run=run, assets=self.assets)['error'],
                             'refused')
            self.assertFalse((menu_common.state_home() / 'current' / 'lock-background').exists())

    def test_restore_without_a_daemon_is_not_applied_and_never_raises(self):
        self.record(self.assets / 'tokyo-night' / '1-winding-road.webp')
        result = background_backend.restore_background(run=lambda argv, timeout=5: (1, ''), assets=self.assets)
        self.assertFalse(result['ok'])
        self.assertIn('method', result)
        self.assertTrue(result['lock_background'])
        link = menu_common.state_home() / 'current' / 'lock-background'
        self.assertEqual(os.readlink(link),
                         str((self.assets / 'tokyo-night' / '1-winding-road.webp').resolve()))
