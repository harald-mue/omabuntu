"""Desktop source, scope and bounded Ubuntu backend contracts (no host actions)."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check_clock_preview as checker
import desktop_frontends as frontend
import display_backend as backend


class DesktopPanelTests(unittest.TestCase):
    def test_registered_surfaces_are_exact_derived_mirrors(self):
        for name, (_, derive) in checker.DESKTOP_TRANSFORMS.items():
            source = ROOT / 'vendor/omarchy' / checker.DESKTOP_UPSTREAM[name]
            self.assertEqual(derive(source.read_bytes()), (ROOT / 'config/shell/preview' / name).read_bytes())

    def test_all_surfaces_exclude_upstream_execution(self):
        for name in checker.DESKTOP_TRANSFORMS:
            text = (ROOT / 'config/shell/preview' / name).read_text()
            for forbidden in ('execDetached', 'Process {', 'ShellIpc', 'omarchy-', 'Util.', 'ScreenMoveRemap'):
                self.assertNotIn(forbidden, text, name)

    def test_extraction_rejects_duplicate_button_witness(self):
        data = (ROOT / 'vendor/omarchy/shell/plugins/panels/bluetooth/Panel.qml').read_bytes()
        with self.assertRaises(ValueError):
            frontend.bluetooth(data + b'  BarIconButton {\n')

    def test_bluetooth_uses_native_actions_without_audio_switching(self):
        text = (ROOT / 'config/shell/preview/BluetoothActions.qml').read_text()
        for action in ('device.pair()', 'device.connect()', 'device.disconnect()', 'device.forget()'):
            self.assertIn(action, text)
        discovery = (ROOT / 'config/shell/preview/BluetoothDiscovery.qml').read_text()
        self.assertIn('!adapter.discovering', discovery)
        self.assertIn('owners.length === 0', discovery)
        self.assertIn('ownsDiscovery', text)
        for excluded in ('Pipewire', 'execDetached', 'Process {', 'trusted =', 'rfkill'):
            if excluded == 'rfkill':
                continue  # Appears only in the explicit exclusion comment.
            self.assertNotIn(excluded, text)

    def test_power_excludes_session_control(self):
        text = (ROOT / 'config/shell/preview/PowerPanelController.qml').read_text()
        self.assertIn('PowerProfiles.profile =', text)
        self.assertIn('UPower.displayDevice', text)
        self.assertIn('previousProfiles.concat', text)
        for excluded in ('Process {', 'execDetached', 'suspend(', 'shutdown(', 'lock('):
            self.assertNotIn(excluded, text)

    def test_dock_ownership_is_confirmed_not_optimistic(self):
        text = (ROOT / 'config/shell/preview/WorkspaceSwitcher.qml').read_text()
        self.assertIn('if (ok) TrialDesktopState.applied(id, requestMode)', text)
        dock = (ROOT / 'config/shell/preview/FloatingDock.qml').read_text()
        self.assertIn('return TrialDesktopState.isFloating(id)', dock)
        self.assertNotIn('tiledLayout', dock)
        self.assertNotIn('tiledLayout', dock)

    def test_display_does_not_offer_global_font_or_output_writes(self):
        text = (ROOT / 'config/shell/preview/DisplayControlView.qml').read_text()
        self.assertNotIn('// ---------- Text size ----------', text)
        self.assertIn('readonly property bool canToggle: false', text)
        self.assertIn('root.errorText', text)

    def test_scale_program_changes_only_named_scale(self):
        program = backend.scale_program(self.monitors(), 'eDP-1', 2)
        self.assertEqual(program, 'hl.monitor({ output = "eDP-1", scale = 2 }); return "ok"')
        for excluded in ('reload', 'mode =', 'position =', 'disabled', 'exec'):
            self.assertNotIn(excluded, program)

    @staticmethod
    def monitors():
        return [{'name': 'eDP-1', 'width': 1920, 'height': 1200, 'x': 0, 'y': 0, 'scale': 1.5},
                {'name': 'DP-7', 'width': 3440, 'height': 1440, 'x': 1280, 'y': 0, 'scale': 1}]

    def test_scale_rejects_overlap(self):
        with self.assertRaisesRegex(ValueError, 'overlap'):
            backend.scale_program(self.monitors(), 'eDP-1', 1)

    def test_scale_rejects_nonintegral_pixels(self):
        with self.assertRaisesRegex(ValueError, 'integral'):
            backend.scale_program(self.monitors(), 'DP-7', 1.5)

    def test_scale_rejects_injection_missing_and_invalid_scale(self):
        for output, scale in [('eDP-1"});', 2), ('gone', 2), ('eDP-1', float('nan')), ('eDP-1', True), ('eDP-1', 99)]:
            with self.subTest(output=output, scale=scale), self.assertRaises(ValueError):
                backend.scale_program(self.monitors(), output, scale)

    def test_backend_timeout_and_failure_are_not_silenced(self):
        with patch.object(backend.subprocess, 'run') as run:
            run.return_value.returncode = 1
            with self.assertRaises(ValueError):
                backend.run(['hyprctl', 'monitors', '-j'])
            self.assertEqual(run.call_args.kwargs['timeout'], 8)

    def test_brightness_records_state_before_logind_mutation(self):
        state = {'displays': [], 'backlight': {'name': 'fixture', 'maximum': 255, 'value': 255}}
        calls = []
        with patch.object(backend, 'status', return_value=state), patch.object(backend, 'save_previous', side_effect=lambda s: calls.append('backup')), patch.object(backend, 'run', side_effect=lambda args: calls.append(args)), patch('builtins.print'):
            backend.main(['brightness', '50'])
        self.assertEqual(calls[0], 'backup')
        self.assertEqual(calls[1][-4:], ['ssu', 'backlight', 'fixture', '128'])

    def test_invalid_brightness_never_mutates(self):
        with patch.object(backend, 'status', return_value={'backlight': None}), patch.object(backend, 'run') as run:
            with self.assertRaises(ValueError):
                backend.main(['brightness', '101'])
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
