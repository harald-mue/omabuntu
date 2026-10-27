import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_minimize():
    path = ROOT / 'tools/omabuntu_hyprland_window_minimize.py'
    spec = importlib.util.spec_from_file_location('omabuntu_hyprland_window_minimize', path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MinimizeHelperTests(unittest.TestCase):
    def test_no_floated_tag_is_no_op_success(self):
        module = load_minimize()
        with patch.object(module, 'resolve_target', return_value=('0x1', 6, ['other'])), \
             patch.object(module, 'dispatch') as dispatch:
            self.assertEqual(module.main([]), 0)
            dispatch.assert_not_called()

    def test_minimize_tags_moves_and_refocuses_workspace(self):
        module = load_minimize()
        with patch.object(module, 'resolve_target', return_value=('0xabc', 6, ['omabuntu-mode-floated'])), \
             patch.object(module, 'dispatch') as dispatch:
            self.assertEqual(module.main([]), 0)
        calls = [args[0] for args, _ in dispatch.call_args_list]
        self.assertTrue(any('omabuntu-minimized-from-6' in call for call in calls))
        self.assertTrue(any('special:minimized' in call for call in calls))
        self.assertTrue(any('hl.dsp.focus({ workspace = "6" })' in call for call in calls))

    def test_replaces_stale_minimized_from_tag(self):
        module = load_minimize()
        tags = ['omabuntu-mode-floated', 'omabuntu-minimized-from-3']
        with patch.object(module, 'resolve_target', return_value=('0xabc', 6, tags)), \
             patch.object(module, 'dispatch') as dispatch:
            module.main([])
        calls = [args[0] for args, _ in dispatch.call_args_list]
        self.assertIn(
            'hl.dsp.window.tag({ tag = "-omabuntu-minimized-from-3", window = "address:0xabc" })',
            calls,
        )


if __name__ == '__main__':
    unittest.main()
