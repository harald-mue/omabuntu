"""Personal folders remain; the withdrawn image importer must stay absent."""
import contextlib
import io
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
import menu_model
import theme_backend
import user_backgrounds as artwork


class UserBackgroundTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.config = self.base / 'config'; self.config.mkdir(mode=0o700)
        self.state = self.base / 'state'; self.assets = self.base / 'assets'; self.assets.mkdir()
        env = patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.config), 'OMABUNTU_STATE_HOME': str(self.state)})
        env.start(); self.addCleanup(env.stop)
        self.destination = self.config / 'omabuntu/backgrounds/tokyo-night'

    def own_image(self):
        with artwork.folder('tokyo-night', create=True): pass
        path = self.destination / 'own.png'; path.write_bytes(b'synthetic listing fixture')
        return path

    def current_theme(self, name='tokyo-night'):
        (self.state / 'current').mkdir(parents=True, exist_ok=True)
        (self.state / 'current/theme.json').write_text(json.dumps({'name': name}))

    def test_folder_open_uses_fixed_file_uri_without_wallpaper_apply(self):
        calls = []
        with patch.object(background_backend, 'apply_background', side_effect=AssertionError('No apply')):
            self.assertTrue(artwork.open_folder('tokyo-night', run=lambda argv: calls.append(argv) or 0)['ok'])
        self.assertEqual(calls, [['xdg-open', self.destination.as_uri()]])
        self.assertFalse(self.state.exists())

    def test_normal_folder_launcher_has_no_expiry(self):
        with patch.object(artwork.subprocess, 'Popen') as spawn:
            self.assertEqual(artwork.open_folder('tokyo-night')['status'], 'started-not-accepted')
        self.assertEqual(spawn.call_args.args[0], ['xdg-open', self.destination.as_uri()])
        self.assertNotIn('timeout', spawn.call_args.kwargs)

    def test_invalid_theme_and_relative_config_are_refused(self):
        for theme in (None, '', '../escape', '/tmp/escape', '.', 'bad/name', 'a\nb', 'A'):
            self.assertFalse(artwork.open_folder(theme, run=lambda _: 0)['ok'])
            self.assertEqual(artwork.images(theme), [])
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': 'relative'}):
            self.assertFalse(artwork.open_folder('tokyo-night')['ok'])

    def test_symlink_destination_is_refused_without_writing_target(self):
        other = self.base / 'other'; other.mkdir()
        (self.config / 'omabuntu').symlink_to(other, target_is_directory=True)
        self.assertFalse(artwork.open_folder('tokyo-night', run=lambda _: 0)['ok'])
        self.assertEqual(list(other.iterdir()), [])
        self.assertEqual(artwork.images('tokyo-night'), [])

    def test_writable_by_others_destination_refused(self):
        self.own_image(); self.destination.chmod(0o777)
        self.assertFalse(artwork.open_folder('tokyo-night', run=lambda _: 0)['ok'])
        self.assertEqual(artwork.images('tokyo-night'), [])

    def test_builtins_personal_and_pictures_keep_their_order(self):
        self.current_theme(); own = self.own_image()
        supplied = self.assets / 'tokyo-night'; supplied.mkdir()
        (supplied / 'builtin.png').write_bytes(b'fixture')
        pictures = self.base / 'Pictures'; pictures.mkdir(); (pictures / 'picture.png').write_bytes(b'fixture')
        self.assertEqual([p.name for p in background_backend.backgrounds([pictures], assets=self.assets)], ['builtin.png', 'own.png', 'picture.png'])
        self.assertIn(str(own), background_backend.allowed_paths([], assets=self.assets))

    def test_other_theme_personal_images_remain_restorable(self):
        own = self.own_image(); self.current_theme('gruvbox')
        self.assertEqual(background_backend.backgrounds([], assets=self.assets), [])
        self.assertIn(str(own), background_backend.allowed_paths([], assets=self.assets))
        self.assertIn('tokyo-night', background_backend.theme_ids(self.assets))

    def test_personal_enumeration_is_nonrecursive_and_bounded(self):
        self.own_image()
        (self.destination / 'nested').mkdir(); (self.destination / 'nested/child.png').write_bytes(b'fixture')
        (self.destination / '.hidden.png').write_bytes(b'fixture'); (self.destination / 'empty.png').touch()
        (self.destination / 'link.png').symlink_to(self.destination / 'own.png')
        (self.destination / 'bad,name.png').write_bytes(b'fixture')
        self.assertEqual([p.name for p in artwork.images('tokyo-night')], ['own.png'])
        with patch.object(artwork, 'MAX_FILES', 0): self.assertEqual(artwork.images('tokyo-night'), [])

    def test_selected_personal_image_is_remembered_without_overwriting_outgoing_choice(self):
        self.current_theme(); own = str(self.own_image())
        no_daemon = {'ok': False, 'message': 'synthetic no daemon'}
        with patch.object(background_backend, 'apply_background', return_value=no_daemon):
            self.assertTrue(background_backend.set_background(own, dirs=[], assets=self.assets)['ok'])
        self.assertEqual(theme_backend.theme_background('tokyo-night', assets=self.assets), own)
        other = self.assets / 'gruvbox'; other.mkdir(); (other / 'builtin.png').write_bytes(b'fixture')
        with patch.object(background_backend, 'apply_background', return_value=no_daemon):
            theme_backend.set_theme('gruvbox', assets=self.assets, run=lambda _: (0, ''), config_path=self.base / 'missing')
        self.assertEqual(theme_backend.theme_background_choices()['tokyo-night'], own)

    def test_withdrawn_import_has_no_menu_route_cli_or_backend(self):
        items, _ = menu_model.load_definitions()
        self.assertNotIn('appearance.background-import', items)
        self.assertFalse(menu_model.ACTION_RE.fullmatch('omabuntu-open:background-import'))
        self.assertEqual(menu_model.run_item('appearance.background-import')['error'], 'unknown')
        self.assertFalse(hasattr(artwork, 'import_images'))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(menu_model.main(['import-backgrounds', 'tokyo-night', '[]']), 2)
        self.assertEqual(json.loads(out.getvalue())['error'], 'usage')
        self.assertEqual(items['appearance.background-folder']['action'], 'omabuntu-background:open-folder')

    def test_dialog_and_its_ui_adaptations_are_entirely_removed(self):
        for name in ('ImagePicker.qml', 'CommandMenu.qml', 'TrialShell.qml'):
            text = (ROOT / 'config/shell/preview' / name).read_text()
            for forbidden in ('FileDialog', 'QtQuick.Dialogs', 'importDialog', 'importFiles', 'openImport', 'openBackgroundImport', 'background-import'):
                self.assertNotIn(forbidden, text, (name, forbidden))
        self.assertNotIn('qml6-module-qtquick-dialogs', (ROOT / 'packages/installer-runtime.json').read_text())


if __name__ == '__main__': unittest.main()
