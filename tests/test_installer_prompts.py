"""Installer Yes defaults preserve individual approval gates and fail on EOF."""
import contextlib
import io
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import setup
import setup_ui
import published_install


class Terminal(io.StringIO):
    def isatty(self):
        return True


class InstallerPromptTests(unittest.TestCase):
    def test_enter_and_explicit_yes_accept_the_displayed_default(self):
        for answer in ('', '  ', 'y', 'Y', 'yes', ' YES '):
            with self.subTest(answer=answer), patch('builtins.input', return_value=answer) as prompt:
                self.assertTrue(setup_ui.confirm('Approve fixture?'))
                prompt.assert_called_once_with('Approve fixture? [Y/n] ')

    def test_explicit_no_unknown_and_eof_decline(self):
        for answer in ('n', 'N', 'no', ' NO ', 'anything else'):
            with self.subTest(answer=answer), patch('builtins.input', return_value=answer):
                self.assertFalse(setup_ui.confirm('Approve fixture?'))
        with patch('builtins.input', side_effect=EOFError):
            self.assertFalse(setup_ui.confirm('Approve fixture?'))

    def test_interrupt_remains_an_abort(self):
        with patch('builtins.input', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            setup_ui.confirm('Approve fixture?')

    def test_published_installer_uses_the_same_enter_default(self):
        with patch('builtins.input', return_value='') as prompt:
            self.assertTrue(published_install.ask('Review fixture?'))
        prompt.assert_called_once_with('Review fixture? [Y/n] ')

    def test_checkout_enter_authorizes_only_the_selected_stage(self):
        reviewed = {'action': 'prepare', 'commands': [], 'blockers': []}
        with patch.object(setup.plugin_manager, 'plan', return_value=reviewed), \
             patch.object(setup.plugin_manager, 'apply', return_value={'status': 'plugin-prepared'}) as apply, \
             patch.object(sys, 'stdin', Terminal()), patch('builtins.input', return_value='') as prompt, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--plugins', '--apply']), 0)
        apply.assert_called_once_with(reviewed, setup.guided.digest(reviewed))
        self.assertEqual(prompt.call_count, 1)

    def test_checkout_no_and_eof_do_not_execute(self):
        reviewed = {'action': 'prepare', 'commands': [], 'blockers': []}
        for answer in ('n', 'no', EOFError):
            with self.subTest(answer=answer), \
                 patch.object(setup.plugin_manager, 'plan', return_value=reviewed), \
                 patch.object(setup.plugin_manager, 'apply') as apply, patch.object(sys, 'stdin', Terminal()), \
                 patch('builtins.input', **({'side_effect': EOFError} if answer is EOFError else {'return_value': answer})), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(setup.main(['--plugins', '--apply']), 0)
            apply.assert_not_called()

    def test_enter_does_not_replace_exact_migration_or_recovery_phrases(self):
        for options, backend, action in ((['--plugins-migrate'], setup.plugin_migration, 'migrate'),
                                         (['--plugins-recover', '/fixture/transaction.json'],
                                          setup.plugin_recovery, 'migrate-recover')):
            reviewed = {'action': action, 'commands': [], 'blockers': []}
            with self.subTest(action=action), patch.object(backend, 'plan', return_value=reviewed), \
                 patch.object(backend, 'apply') as apply, patch.object(sys, 'stdin', Terminal()), \
                 patch('builtins.input', side_effect=['', '']), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(setup.main([*options, '--apply']), 0)
            apply.assert_not_called()

    def test_installer_sources_do_not_reintroduce_no_default_prompts(self):
        for name in ('setup.py', 'published_install.py'):
            text = (ROOT / 'tools' / name).read_text()
            self.assertNotIn('[y/N]', text)
