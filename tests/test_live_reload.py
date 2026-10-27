"""Live reload must preserve the session and surface configuration errors."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock

SPEC = importlib.util.spec_from_file_location(
    'reload_hyprland', Path(__file__).resolve().parents[1] / 'tools/reload_hyprland.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReloadTests(unittest.TestCase):
    def test_reload_then_check_errors(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0, '\n', ''))
        MODULE.reload_config(run)
        self.assertEqual([c.args[0] for c in run.call_args_list],
                         [['hyprctl', 'reload'], ['hyprctl', 'configerrors']])
        for call in run.call_args_list:
            self.assertEqual(call.kwargs['timeout'], 20)
            self.assertTrue(call.kwargs['check'])

    def test_reported_config_errors_fail(self):
        run = Mock(side_effect=[subprocess.CompletedProcess([], 0, 'ok', ''),
                                subprocess.CompletedProcess([], 0, 'bad option', '')])
        with self.assertRaisesRegex(ValueError, 'bad option'):
            MODULE.reload_config(run)

    def test_failed_reload_does_not_continue(self):
        run = Mock(side_effect=subprocess.CalledProcessError(1, ['hyprctl', 'reload']))
        with self.assertRaises(subprocess.CalledProcessError):
            MODULE.reload_config(run)
        self.assertEqual(run.call_count, 1)
