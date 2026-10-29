"""Contracts for defaults_backend (plan 040)."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import defaults_backend
import menu_common
import menu_model

class DefaultsBackendTests(unittest.TestCase):
    def test_xdg_settings_run_rejects_other_commands(self):
        with self.assertRaises(ValueError):
            defaults_backend.xdg_settings_run(['xdg-settings', 'set', 'default-url-scheme-handler', 'x'])

    def test_browser_rows_mark_current_and_deduplicate_vendor_ids(self):
        with tempfile.TemporaryDirectory() as apps:
            app_dir = Path(apps)
            chrome = app_dir / 'opt' / 'chrome'
            chrome.parent.mkdir(parents=True, exist_ok=True)
            chrome.write_text('#!/bin/sh\n')
            chrome.chmod(0o755)
            desktop_body = (
                '[Desktop Entry]\nName=Google Chrome\nCategories=Network;WebBrowser;\n'
                'Exec=%s %%U\nTryExec=%s\n' % (chrome, chrome))
            (app_dir / 'google-chrome.desktop').write_text(desktop_body)
            (app_dir / 'com.google.Chrome.desktop').write_text(
                '[Desktop Entry]\nName=Google Chrome Hidden\nNoDisplay=true\n'
                + desktop_body.split('\n', 1)[1])
            original = defaults_backend.APPLICATION_DIRS
            defaults_backend.APPLICATION_DIRS = (app_dir,)
            try:
                rows = defaults_backend.browser_rows(
                    run=lambda argv: (0, 'google-chrome.desktop') if argv[1] == 'get' else (1, ''))
            finally:
                defaults_backend.APPLICATION_DIRS = original
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['value'], 'google-chrome.desktop')
            self.assertTrue(rows[0]['current'])

    def test_set_browser_refuses_unknown_and_outside_candidates(self):
        with tempfile.TemporaryDirectory() as apps:
            app_dir = Path(apps)
            binary = app_dir / 'opt' / 'edge'
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.write_text('#!/bin/sh\n')
            binary.chmod(0o755)
            (app_dir / 'edge.desktop').write_text(
                '[Desktop Entry]\nName=Edge\nCategories=Network;WebBrowser;\n'
                'Exec=%s %%U\nTryExec=%s\n' % (binary, binary))
            original = defaults_backend.APPLICATION_DIRS
            defaults_backend.APPLICATION_DIRS = (app_dir,)
            try:
                self.assertEqual(defaults_backend.set_browser('bad id')['error'], 'unknown')
                self.assertEqual(defaults_backend.set_browser('missing.desktop')['error'], 'refused')
                self.assertEqual(defaults_backend.set_browser('edge.desktop', run=lambda argv: (0, ''))['ok'], True)
            finally:
                defaults_backend.APPLICATION_DIRS = original

    def test_set_terminal_writes_the_hyprland_preference_list(self):
        with tempfile.TemporaryDirectory() as config:
            with tempfile.TemporaryDirectory() as apps:
                app_dir = Path(apps)
                (app_dir / 'kitty.desktop').write_text(
                    '[Desktop Entry]\nName=kitty\nCategories=System;TerminalEmulator;\n'
                    'Exec=kitty\nTryExec=kitty\nX-TerminalArgExec=--\n')
                kitty = app_dir / 'kitty'
                kitty.write_text('#!/bin/sh\n')
                kitty.chmod(0o755)
                original_dirs = defaults_backend.APPLICATION_DIRS
                defaults_backend.APPLICATION_DIRS = (app_dir,)
                os.environ['XDG_CONFIG_HOME'] = config
                os.environ['XDG_CURRENT_DESKTOP'] = 'Hyprland'
                try:
                    original_current = defaults_backend.current_terminal
                    defaults_backend.current_terminal = lambda: 'kitty.desktop'
                    result = defaults_backend.set_terminal('kitty.desktop', config=config)
                finally:
                    defaults_backend.current_terminal = original_current
                    defaults_backend.APPLICATION_DIRS = original_dirs
                    del os.environ['XDG_CONFIG_HOME']
                    del os.environ['XDG_CURRENT_DESKTOP']
            target = Path(config) / 'hyprland-xdg-terminals.list'
            self.assertTrue(result['ok'])
            self.assertEqual(target.read_text().strip(), 'kitty.desktop')


class MenuModelDefaultsTests(unittest.TestCase):
    def test_provider_rows_include_default_browsers(self):
        rows = menu_model.provider_rows('default-browsers')
        self.assertIsInstance(rows, list)
        if rows:
            self.assertIn('value', rows[0])
            self.assertIn('current', rows[0])


if __name__ == '__main__':
    unittest.main()
