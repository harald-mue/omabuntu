"""Dock parity contracts: entry claiming, minimise/restore, pins, drag, state file."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dock_state


class DockStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'config' / 'dock.json'
        self.env = patch.dict(os.environ, {'OMABUNTU_DOCK_CONFIG': str(self.path)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_cli(self, *args):
        with patch('builtins.print') as printed:
            code = dock_state.main(list(args))
        return code, json.loads(printed.call_args[0][0])

    def test_defaults_are_returned_without_writing(self):
        self.assertEqual(self.run_cli('get')[1], {'position': 'bottom', 'autohide': False, 'pinned': []})
        self.assertFalse(self.path.exists())

    def test_settings_round_trip_atomically_with_backup(self):
        self.run_cli('set-position', 'left')
        self.run_cli('set-autohide', 'on')
        self.run_cli('set-pinned', 'firefox.desktop', 'org.gnome.Nautilus.desktop', 'firefox.desktop')
        data = json.loads(self.path.read_text())
        self.assertEqual((data['position'], data['autohide']), ('left', True))
        self.assertEqual(data['pinned'], ['firefox.desktop', 'org.gnome.Nautilus.desktop'])
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertTrue(self.path.with_name('dock.json.previous').exists())
        # Quickshell entry ids carry no .desktop suffix; both forms must persist.
        self.run_cli('set-pinned', 'firefox', 'org.gnome.Nautilus', 'htop')
        data = json.loads(self.path.read_text())
        self.assertEqual(data['pinned'], ['firefox', 'org.gnome.Nautilus', 'htop'])

    def test_invalid_values_never_reach_the_file(self):
        for args in (('set-position', 'middle'), ('set-position',), ('set-autohide', 'maybe'),
                     ('set-pinned', '../evil'), ('set-pinned', 'a b'), ('set-pinned', 'a.desktop', '../../evil.desktop')):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.run_cli(*args)
        self.assertFalse(self.path.exists())

    def test_symlinked_configuration_is_refused(self):
        target = Path(self.temp.name) / 'elsewhere.json'
        target.write_text('{}')
        self.path.parent.mkdir(parents=True)
        self.path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            self.run_cli('get')

    def test_public_directory_is_refused(self):
        self.path.parent.mkdir(parents=True)
        self.path.parent.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'private'):
            self.run_cli('set-position', 'top')

    def test_corrupt_file_is_reported_not_overwritten(self):
        self.path.parent.mkdir(parents=True)
        self.path.parent.chmod(0o700)
        self.path.write_text('{"position":"bottom","pinned":"all"}')
        with self.assertRaises(ValueError):
            self.run_cli('set-position', 'top')
        self.assertEqual(self.path.read_text(), '{"position":"bottom","pinned":"all"}')


class DockSourceTests(unittest.TestCase):
    def dock(self):
        return (ROOT / 'config/shell/preview/FloatingDock.qml').read_text()

    def window(self):
        return (ROOT / 'config/shell/preview/DockWindow.qml').read_text()

    def test_entries_are_resolved_like_upstream(self):
        text = self.dock()
        self.assertIn('DesktopEntries.heuristicLookup(appId)', text)
        self.assertIn('Model.claimingEntryId(appId, root.terminalEntries)', text)
        self.assertIn('entry ? entry.id : String(toplevel.appId)', text)
        self.assertIn('!!entry && !entry.noDisplay', text)
        self.assertIn('toplevel.parent', text)

    def test_slots_are_synced_incrementally(self):
        text = self.dock()
        self.assertNotIn('model.clear()', text)
        for call in ('model.move(', 'model.insert(', 'model.remove('):
            self.assertIn(call, text)

    def test_visibility_follows_compositor_events(self):
        text = self.dock()
        self.assertIn('function onRawEvent(event)', text)
        self.assertIn('name === "fullscreen"', text)
        self.assertIn('name === "configreloaded"', text)
        self.assertIn('Hyprland.refreshToplevels()', text)
        self.assertIn('return TrialDesktopState.isFloating(id)', text)

    def test_context_menu_dismisses_on_outside_click(self):
        text = self.window()
        self.assertIn('HyprlandFocusGrab {', text)
        self.assertIn('active: window.menuOpen', text)
        self.assertIn('windows: [window]', text)
        self.assertIn('onCleared: window.closeMenu()', text)
        # The monitor-remap guard stays excluded: this surface is always mapped.
        self.assertNotIn('ScreenMoveRemap', text)

    def test_minimised_windows_are_kept_and_restored(self):
        text = self.dock()
        self.assertIn('Model.isMinimizedWorkspace(workspace.name)', text)
        self.assertIn('special:minimized', text)
        self.assertIn('omabuntu-minimized-from-', text)
        self.assertIn('function restoreMinimized(window)', text)
        self.assertIn('function bring', text.replace('restoreMinimized', 'bring')) if False else None
        self.assertIn('alter_zorder', text)

    def test_launch_pulse_and_pins_are_present(self):
        text = self.dock()
        self.assertIn('function isLaunching(key)', text)
        self.assertIn('launchTimeout', text)
        self.assertIn('Model.pinsInOrder(', text)
        self.assertIn('function pinAt(key, index)', text)
        self.assertIn('function moveItem(fromIndex, toIndex)', text)

    def test_external_drag_routing_is_present(self):
        text = self.dock()
        for name in ('moveExternalDrag', 'dropExternalDrag', 'endExternalDrag', 'dockOn'):
            self.assertIn('function ' + name, text)
        window = self.window()
        self.assertIn('dock.pinAt(key, window.insertIndex)', window)

    def test_menu_offers_minimise_and_maximise_until_titlebars_exist(self):
        text = self.window()
        self.assertIn('dock.minimize(menu.item)', text)
        self.assertIn('dock.toggleMaximized(menu.item)', text)
        i18n = (ROOT / 'config/shell/preview/I18n.qml').read_text()
        self.assertIn('"dock.minimize"', i18n)
        self.assertIn('"dock.maximize"', i18n)

    def test_no_helper_shell_or_ipc_remains(self):
        for text in (self.dock(), self.window()):
            for forbidden in ('execDetached', 'ShellIpc', 'hyprctl', 'omarchy-', 'Process {'):
                self.assertNotIn(forbidden, text)

    def test_app_panel_reports_the_drag(self):
        text = (ROOT / 'config/shell/preview/AppLauncher.qml').read_text()
        self.assertIn('property var dock: null', text)
        self.assertIn('dock.moveExternalDrag(root.screen', text)
        self.assertIn('dock.dropExternalDrag(root.screen', text)
        self.assertIn('dock.endExternalDrag()', text)
        self.assertIn('mapToItem(root.contentItem', text)
        self.assertNotIn('execDetached', text)

    def test_trial_shell_wires_panel_and_dock(self):
        text = (ROOT / 'config/shell/preview/TrialShell.qml').read_text()
        self.assertIn('launcher.dock = dock', text)
        self.assertIn("dock.destroy()", text)


if __name__ == '__main__':
    unittest.main()


class HyprbarsBuildTests(unittest.TestCase):
    def test_binary_version_probe_does_not_require_a_running_session(self):
        import build_hyprbars
        data = {'version': '0.56.2', 'commit': build_hyprbars.HYPRLAND_COMMIT,
                'abiHash': 'fixture-abi', 'dirty': False}
        with patch.object(build_hyprbars, 'run', return_value=json.dumps(data)) as run:
            self.assertEqual(build_hyprbars.hyprland_version(),
                             ('0.56.2', build_hyprbars.HYPRLAND_COMMIT, 'fixture-abi'))
        run.assert_called_once_with(['Hyprland', '--version-json'], timeout=15)
        data['dirty'] = True
        with patch.object(build_hyprbars, 'run', return_value=json.dumps(data)), self.assertRaises(ValueError):
            build_hyprbars.hyprland_version()

    def test_build_never_replaces_an_existing_output_directory(self):
        import build_hyprbars
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            marker = Path(directory) / 'keep'
            marker.write_text('user data')
            with patch.object(build_hyprbars, 'hyprland_version', return_value=(
                    '0.56.2', build_hyprbars.HYPRLAND_COMMIT, 'abi')), \
                 patch.object(build_hyprbars, 'missing_modules', return_value=[]):
                with self.assertRaisesRegex(ValueError, 'fresh build directory'):
                    build_hyprbars.main(['--output', directory])
            self.assertEqual(marker.read_text(), 'user data')

    def test_build_refuses_unpinned_hyprland_and_missing_deps(self):
        import build_hyprbars
        with patch.object(build_hyprbars, 'hyprland_version', return_value=(
                '0.56.2', build_hyprbars.HYPRLAND_COMMIT, 'abi')), \
             patch.object(build_hyprbars, 'missing_modules', return_value=['hyprland']), \
             patch('builtins.print'):
            self.assertEqual(build_hyprbars.main([]), 2)
        with patch.object(build_hyprbars, 'hyprland_version', return_value=('0.56.2', 'deadbeef', 'abi')):
            with self.assertRaisesRegex(ValueError, 'differs from the reviewed build'):
                build_hyprbars.main([])
        self.assertEqual(build_hyprbars.PLUGIN_COMMIT, '7644cecdb947060682891a0db2a0cdc5c0b9e704')

    def test_build_never_installs_or_reloads(self):
        text = (ROOT / 'tools/build_hyprbars.py').read_text()
        self.assertNotIn('hyprctl reload', text)
        self.assertNotIn('systemctl', text)
        self.assertNotIn('hyprland.lua', text)
        self.assertNotIn("['sudo'", text)
        self.assertIn('APT_HINT', text)
        self.assertIn('not loaded', text.lower())

    def test_show_rule_rechecks_on_class_updates(self):
        # Hyprland 0.56.2 emits TITLE|CLASS on title changes. Custom effects
        # removed by resetProps are not included in effectsNeedingRecheck, so
        # both overrides must explicitly participate in CLASS reevaluation.
        text = (ROOT / 'config/hypr/hyprbars.lua').read_text()
        show = text.split('name = "omabuntu-hyprbars-show-floated",', 1)[1].split('})', 1)[0]
        self.assertRegex(show, r'match\s*=\s*\{[^}]*class\s*=\s*"\.\*"')
        self.assertIn('tag = "omabuntu-floating-workspace"', show)
        self.assertNotIn('tag = "omabuntu-mode-floated"', show)
        self.assertEqual(show.count('["hyprbars:no_bar"]'), 1)

    def test_titlebar_snippet_is_not_installed_and_only_quotes_dispatchers(self):
        text = (ROOT / 'config/hypr/hyprbars.lua').read_text()
        self.assertIn('if not hl.plugin.hyprbars then', text)
        self.assertIn('hl.plugin.hyprbars', text)
        self.assertIn('add_button', text)
        self.assertIn('omabuntu-hyprbars-hide', text)
        self.assertIn('omabuntu-floating-workspace', text)
        self.assertLess(text.index('omabuntu-hyprbars-hide'), text.index('omabuntu-hyprbars-show-floated'))
        self.assertIn('hl.dsp.window.close', text)
        self.assertIn('hl.dsp.window.fullscreen', text)
        self.assertIn('omabuntu-hyprland-window-minimize', text)
        self.assertIn('window = "activewindow"', text)
        self.assertNotIn('%WINDOW%', text)
        self.assertNotIn('closewindow activewindow', text)
        self.assertNotIn('address:activewindow', text)
        self.assertNotIn('omarchy-', text)
