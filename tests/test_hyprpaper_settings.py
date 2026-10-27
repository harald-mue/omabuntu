"""Contracts for the separate wallpaper-daemon splash configuration."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HyprpaperSplashTests(unittest.TestCase):
    def test_daemon_template_disables_only_its_own_splash(self):
        text = (ROOT / 'config/hypr/hyprpaper.conf').read_text()
        settings = [line.split('#', 1)[0].strip() for line in text.splitlines()]
        settings = [line for line in settings if line]
        self.assertEqual(settings, ['splash = false'])
        self.assertTrue(text.endswith('\n'))

    def test_template_is_recorded_in_future_immutable_bundles(self):
        tree = ast.parse((ROOT / 'tools/package_user.py').read_text())
        copied = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple):
                copied.extend(item.value for item in node.iter.elts
                              if isinstance(item, ast.Constant) and isinstance(item.value, str))
        self.assertIn('hypr/hyprpaper.conf', copied)

    def test_compositor_splash_is_still_independently_disabled(self):
        text = (ROOT / 'config/hypr/omabuntu-managed.lua').read_text()
        self.assertIn('disable_splash_rendering = true', text)
        self.assertIn('disable_hyprland_logo = true', text)
