"""Persistent plugin grants fail closed; no native process is started."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import plugin_login
import plugin_manager


class PluginLoginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.release = self.home / 'releases/test'
        self.config = self.home / 'config'
        self.state = self.home / 'state/omabuntu'
        self.directory = self.home / 'cache'
        for path in (self.release / 'native', self.config / 'hypr', self.state,
                     self.directory / 'hyprland-plugins'):
            path.mkdir(parents=True)
        self.policy = plugin_manager.policy()
        self.native = {'version': '0.57.0', 'dirty': False, 'abiHash': 'fixture-abi',
                       'commit': self.policy['targets']['0.57.0']['hyprland_commit']}
        self.running = {'commit': self.native['commit'], 'flags': [], 'abiHash': 'fixture-abi'}
        self.loaded = []
        self.calls = []
        self.write_json(self.release / 'native/hyprpm.json', self.policy)
        self.activation = {'release': 'releases/test', 'library': None,
                           'plugin_login_enabled': True, 'files': {}}
        for name in ('activation', 'titlebars'):
            text = '-- fixture ' + name
            (self.config / ('hypr/omabuntu-' + name + '.lua')).write_text(text)
            self.activation['files'][name] = hashlib.sha256(text.encode()).hexdigest()
        self.save_activation()
        (self.state / 'control.lock').write_text('')
        library = self.directory / 'hyprland-plugins/hyprbars.so'
        library.write_bytes(b'fixture library')
        self.receipt = {'activated': True, 'native': self.native.copy(), 'library': str(library),
                        'library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
                        'policy_digest': plugin_login.digest(self.policy)}
        self.write_json(self.state / 'hyprpm.json', self.receipt)
        self.write_repo()
        headers = self.directory / 'headersRoot/share/pkgconfig/hyprland.pc'
        headers.parent.mkdir(parents=True)
        headers.write_text('prefix=' + str(self.directory / 'headersRoot/include') + '\nVersion: 0.57.0\n')
        version = self.directory / 'headersRoot/include/hyprland/src/version.h'
        version.parent.mkdir(parents=True)
        version.write_text('#define GIT_COMMIT_HASH "' + self.native['commit'] + '"\n#define GIT_DIRTY "clean"\n')
        (self.directory / 'state.toml').write_text('[state]\nhash = "fixture-abi"\n')
        mock = patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.config),
                                      'XDG_STATE_HOME': str(self.home / 'state')})
        mock.start()
        self.addCleanup(mock.stop)

    def write_json(self, path, data):
        path.write_text(json.dumps(data))

    def save_activation(self):
        self.write_json(self.state / 'session-activation.json', self.activation)

    def write_repo(self, extra=''):
        target = self.policy['targets']['0.57.0']
        (self.directory / 'hyprland-plugins/state.toml').write_text(
            '[repository]\nname = "hyprland-plugins"\nurl = ' + json.dumps(self.policy['repository']) + '\n'
            'rev = ' + json.dumps(target['plugin_commit']) + '\n'
            'hash = ' + json.dumps(target['plugin_commit']) + '\n'
            '[hyprbars]\nfilename = "hyprbars.so"\nenabled = true\nfailed = false\n' + extra)

    def inspect(self, argv):
        self.calls.append(argv)
        if argv[0] == 'Hyprland':
            return json.dumps(self.native)
        if argv == ['hyprctl', '-j', 'version']:
            return json.dumps(self.running)
        if argv == ['hyprctl', '-j', 'plugin', 'list']:
            return json.dumps(self.loaded)
        if argv == ['hyprpm', 'reload']:
            self.loaded = [{'name': 'hyprbars'}]
            return 'ok'
        if argv[:2] == ['hyprctl', 'eval']:
            return 'ok'
        raise AssertionError(argv)

    def run_login(self):
        return plugin_login.run(self.release, self.home, self.directory, self.inspect)

    def assert_refused(self):
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.run_login()
        self.assertFalse(any(c[0] == 'hyprpm' or c[:2] == ['hyprctl', 'eval'] for c in self.calls))

    def test_success_only_reloads_existing_plugin_and_applies_owned_titlebars(self):
        result = self.run_login()
        self.assertEqual(result['status'], 'loaded-and-configured')
        self.assertFalse(result['configuration_reloaded'])
        self.assertEqual([c for c in self.calls if c[0] == 'hyprpm'], [['hyprpm', 'reload']])
        self.assertEqual(len([c for c in self.calls if c[:2] == ['hyprctl', 'eval']]), 1)
        self.assertFalse(any('sudo' in c or 'update' in c or 'enable' in c for c in self.calls))

    def test_already_loaded_does_not_duplicate_titlebar_buttons(self):
        self.loaded = [{'name': 'hyprbars'}]
        self.assertEqual(self.run_login()['status'], 'already-loaded')
        self.assertFalse(any(c[0] == 'hyprpm' or c[:2] == ['hyprctl', 'eval'] for c in self.calls))

    def test_explicit_live_rules_do_not_require_or_create_a_persistent_grant(self):
        self.activation['plugin_login_enabled'] = False
        self.save_activation()
        self.loaded = [{'name': 'hyprbars'}]
        result = plugin_login.run(self.release, self.home, self.directory, self.inspect, configure_only=True)
        self.assertEqual(result['status'], 'loaded-and-configured')
        self.assertFalse(any(c[0] == 'hyprpm' for c in self.calls))
        self.assertFalse(json.loads((self.state / 'session-activation.json').read_text())['plugin_login_enabled'])

    def test_live_rules_do_not_load_a_missing_plugin(self):
        with self.assertRaisesRegex(ValueError, 'already loaded'):
            plugin_login.run(self.release, self.home, self.directory, self.inspect, configure_only=True)
        self.assertFalse(any(c[0] == 'hyprpm' for c in self.calls))

    def test_missing_persistent_grant_is_not_inferred_from_enabled_plugin(self):
        self.activation.pop('plugin_login_enabled')
        self.save_activation()
        self.assert_refused()

    def test_unprepared_or_disabled_receipt_is_not_enabled_at_login(self):
        self.receipt['activated'] = False
        self.write_json(self.state / 'hyprpm.json', self.receipt)
        self.assert_refused()

    def test_installed_running_mismatch_is_blocked_without_restarting(self):
        self.running['commit'] = self.policy['targets']['0.56.2']['hyprland_commit']
        self.assert_refused()

    def test_same_commit_different_abi_is_not_loaded(self):
        self.running['abiHash'] = 'other-abi'
        self.assert_refused()

    def test_compiled_native_mismatch_is_blocked(self):
        self.receipt['native']['commit'] = '0' * 40
        self.write_json(self.state / 'hyprpm.json', self.receipt)
        self.assert_refused()

    def test_titlebar_edits_are_not_overwritten_or_evaluated(self):
        (self.config / 'hypr/omabuntu-titlebars.lua').write_text('-- user edit')
        self.assert_refused()

    def test_missing_headers_never_falls_back_to_privileged_cache_creation(self):
        (self.directory / 'headersRoot/share/pkgconfig/hyprland.pc').unlink()
        with patch.object(plugin_login, 'system_headers') as fallback:
            self.assert_refused()
        fallback.assert_not_called()

    def test_package_headers_are_accepted_only_for_empty_existing_cache(self):
        headers = self.directory / 'headersRoot'
        headers.rename(self.home / 'saved-cache-headers')
        headers.mkdir()
        expected = {'layout': 'system-package', 'files': {'fixture': 'verified'}}
        with patch.object(plugin_login, 'system_headers', return_value=expected):
            reviewed = plugin_login.review(self.release, self.home, self.directory, self.inspect)
            self.assertEqual(reviewed['headers'], expected)
            self.receipt['headers'] = {'layout': 'system-package', 'files': {'fixture': 'changed'}}
            self.write_json(self.state / 'hyprpm.json', self.receipt)
            self.assert_refused()
        self.assertNotIn(['hyprpm', 'reload'], self.calls)

    def test_changed_loader_filename_is_not_executed(self):
        path = self.directory / 'hyprland-plugins/state.toml'
        path.write_text(path.read_text().replace('filename = "hyprbars.so"', 'filename = "../../other.so"'))
        self.assert_refused()

    def test_library_drift_is_refused(self):
        (self.directory / 'hyprland-plugins/hyprbars.so').write_bytes(b'changed')
        self.assert_refused()

    def test_other_enabled_plugin_cannot_be_loaded_implicitly(self):
        self.write_repo('[other]\nenabled = true\nfailed = false\n')
        self.assert_refused()

    def test_other_loaded_plugin_cannot_be_unloaded_implicitly(self):
        self.loaded = [{'name': 'other'}]
        self.assert_refused()

    def test_failed_transaction_blocks_login(self):
        transaction = self.state / 'plugin-transactions/failed/transaction.json'
        transaction.parent.mkdir(parents=True)
        self.write_json(transaction, {'status': 'manual-review-required'})
        self.assert_refused()

    def test_symlink_receipt_is_refused(self):
        path = self.state / 'hyprpm.json'
        path.rename(path.with_suffix('.original'))
        path.symlink_to(path.with_suffix('.original'))
        self.assert_refused()

    def test_missing_actual_load_does_not_apply_rules(self):
        def inspect(argv):
            if argv == ['hyprpm', 'reload']:
                self.calls.append(argv)
                return 'ok'
            return self.inspect(argv)
        with self.assertRaisesRegex(ValueError, 'without loading'):
            plugin_login.run(self.release, self.home, self.directory, inspect)
        self.assertFalse(any(c[:2] == ['hyprctl', 'eval'] for c in self.calls))


if __name__ == '__main__':
    unittest.main()
