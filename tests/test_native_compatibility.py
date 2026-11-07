"""Native family admission is not plugin ABI, authentication or live acceptance."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import native_compatibility as native
import install as guided
import plugin_manager
import update_payload


class NativeCompatibilityTests(unittest.TestCase):
    def test_stable_patch_families_and_distribution_revisions_are_admitted(self):
        cases = {
            'hyprland': ('0.57.0', '0.57.1-1ppa1~1resolute1', '1:0.57.12+ds1-2'),
            'qt': ('6.10.2', '6.10.3+dfsg-1ubuntu1', '6.10.12-1'),
            'hyprlock': ('0.9.6', '0.9.7-1ppa1~1resolute1', '0.9.10'),
        }
        for component, versions in cases.items():
            for version in versions:
                with self.subTest(component=component, version=version):
                    result = native.assess(component, version, 'APT candidate')
                    self.assertTrue(result['ok'], result['message'])
                    self.assertIn(version, result['message'])

    def test_missing_prerelease_development_and_new_families_are_not_guessed(self):
        cases = {
            'hyprland': (None, '', '(none)', '0.57.0~rc1-1', '0.57.1-rc1', '0.57.1+git1',
                         '0.57.01', 'v0.57.1', '0.56.2', '0.58.0', '1.0.0', '0.57.1 dirty', {}),
            'qt': ('6.10.1', '6.11.0', '6.9.3'),
            'hyprlock': ('0.9.5', '0.10.0', '0.9.7-beta1'),
        }
        for component, versions in cases.items():
            for version in versions:
                with self.subTest(component=component, version=version):
                    result = native.assess(component, version, 'APT candidate')
                    self.assertFalse(result['ok'])
                    for text in ('supported', 'Next:', 'APT candidate'):
                        self.assertIn(text, result['message'])
                    self.assertIsNotNone(result['reason'])

    def test_known_exclusion_changes_policy_and_overrides_family(self):
        before = guided.digest(native.policy())
        with patch.dict(native.EXCLUDED['hyprland'], {'0.57.1': 'synthetic regression'}):
            result = native.assess('hyprland', '0.57.1-1', 'installed package')
            self.assertFalse(result['ok'])
            self.assertIn('synthetic regression', result['message'])
            self.assertNotEqual(before, guided.digest(native.policy()))

    def test_policy_copy_cannot_mutate_exclusions(self):
        data = native.policy()
        data['families']['hyprland']['excluded']['0.57.1'] = 'untrusted caller'
        self.assertTrue(native.assess('hyprland', '0.57.1', 'fixture')['ok'])

    def test_binary_json_metadata_requires_clean_valid_source_identity(self):
        metadata = {'version': '0.57.1', 'commit': 'a' * 40, 'dirty': False}
        result = native.hyprland_binary({'status': 'ok', 'stdout': json.dumps(metadata)})
        self.assertTrue(result['ok'])
        for changed in ({'dirty': True}, {'dirty': None}, {'commit': ''}, {'version': '0.58.0'}):
            with self.subTest(changed=changed):
                result = native.hyprland_metadata(dict(metadata, **changed), 'fixture binary')
                self.assertFalse(result['ok'])
        for text in ('not json', '{}', '[]', '{"version":"0.57.1"}'):
            self.assertFalse(native.hyprland_binary({'status': 'ok', 'stdout': text})['ok'])

    def test_probe_timeout_missing_command_and_failure_remain_explicit(self):
        for status in ('timeout', 'missing', 'failed'):
            for check in (native.hyprland_binary, native.hyprlock_binary):
                with self.subTest(status=status, check=check.__name__):
                    result = check({'status': status})
                    self.assertFalse(result['ok'])
                    self.assertIn(status, result['message'])

    def test_lock_version_parser_accepts_new_patch_without_starting_locker(self):
        for text in ('Hyprlock version v0.9.7\n', 'Hyprlock version v0.9.7 (commit abc)\n'):
            self.assertTrue(native.hyprlock_binary({'status': 'ok', 'stdout': text})['ok'])
        for text in ('Hyprlock version v0.9.7-rc1', 'Other tool v0.9.7',
                     'Hyprlock version v0.9.6\nHyprlock version v0.9.7\n'):
            self.assertFalse(native.hyprlock_binary({'status': 'ok', 'stdout': text})['ok'])

    def test_package_selection_distinguishes_installed_from_candidate(self):
        policy = ''.join(name + ':\n  Candidate: ' + version + '\n' for name, version in (
            ('hyprland', '0.57.1-1ppa1~1resolute1'), ('hyprlock', '0.9.7-1'), ('libqt6core6t64', '6.10.3-1')))
        payload = {'policy': policy, 'before': {'installed': {'hyprland': '0.57.0-1'}}}
        checks = native.package_checks(payload)
        self.assertTrue(all(check['ok'] for check in checks))
        compositor = next(row for row in checks if row['component'] == 'hyprland')
        self.assertEqual(compositor['source'], 'installed package')
        self.assertEqual(compositor['detected'], '0.57.0-1')
        self.assertEqual(compositor['candidate'], '0.57.1-1ppa1~1resolute1')
        self.assertEqual(next(row for row in checks if row['component'] == 'hyprlock')['source'], 'APT candidate')

    def test_diagnostic_does_not_emit_raw_terminal_controls(self):
        result = native.assess('hyprland', '0.57.1\x1b[2J', 'APT candidate')
        self.assertFalse(result['ok'])
        self.assertNotIn('\x1b', result['message'])
        self.assertIn('\\u001b', result['message'])

    def test_application_preflight_failure_includes_actual_reason_and_report(self):
        failed = native.assess('hyprland', '0.58.0-1', 'APT candidate')
        message = guided.preflight_failure({'checks': [dict(failed, name='hyprland-target')]}, 'private/preflight.json')
        for text in ('0.58.0-1', '>=0.57.0, <0.58.0', 'APT candidate', 'private/preflight.json', 'No application switch'):
            self.assertIn(text, message)

    def test_shell_patch_admission_does_not_bypass_plugin_source_or_abi_guards(self):
        metadata = {'version': '0.57.1', 'commit': 'b' * 40, 'dirty': False, 'abiHash': 'same-claimed-abi'}
        self.assertTrue(native.hyprland_metadata(metadata, 'fixture')['ok'])
        issue = plugin_manager.target_blocker(plugin_manager.policy(), metadata)
        self.assertIsNotNone(issue)
        for text in ('0.57.1', 'not approved', 'not a plugin ABI proof', 'existing plugin state'):
            self.assertIn(text, issue)

    def test_standalone_update_payload_contains_shared_policy(self):
        self.assertIn('native_compatibility', update_payload.modules(ROOT))


if __name__ == '__main__':
    unittest.main()
