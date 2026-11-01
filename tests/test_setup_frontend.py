"""Setup UI and safe planning contracts; no system or desktop changes."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import setup_ui

SPEC = importlib.util.spec_from_file_location('omabuntu_setup', ROOT / 'tools/setup.py')
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)

SYSTEM = {'status': 'ok', 'values': {'ID': 'ubuntu', 'VERSION_ID': '26.04'}}
INSTALLED = {'ok': True, 'installed': True, 'previous_available': True}


def plan(mode='install', **kwargs):
    return setup.inspect(mode, os_info=SYSTEM, architecture='x86_64',
                         which=lambda _: '/example', installation=INSTALLED, **kwargs)


class PluginFrontendTests(unittest.TestCase):
    def test_native_handoff_flag_requires_versioned_explicit_update_bundle(self):
        with patch.object(setup.release_update, 'review') as review:
            for options in (['--migrate-native'], ['--bundle', '/fixture', '--migrate-native'],
                            ['--update', '--migrate-native'],
                            ['--update', '--bundle', '/fixture', '--migrate-native', '--allow-legacy-state']):
                with self.subTest(options=options), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        setup.main(options)
        review.assert_not_called()

    def test_native_handoff_readonly_flag_is_forwarded_without_apply(self):
        with patch.object(setup.release_update, 'review', return_value={'migrate_native': True}) as review, \
             patch.object(setup.release_update, 'apply') as apply, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--update', '--bundle', '/fixture', '--migrate-native', '--json']), 0)
        self.assertTrue(review.call_args.kwargs['migrate_native'])
        apply.assert_not_called()

    def test_recovery_review_never_runs_manager_commands(self):
        reviewed = {'action': 'migrate-recover', 'commands': [], 'blockers': [],
                    'headers': {'layout': 'system-package'}}
        with patch.object(setup.plugin_recovery, 'plan', return_value=reviewed) as plan, \
             patch.object(setup.plugin_recovery, 'apply') as apply, \
             patch.object(setup.plugin_manager, 'apply') as normal, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--plugins-recover', '/fixture/transaction.json']), 0)
        self.assertEqual(plan.call_args.args[0], Path('/fixture/transaction.json'))
        apply.assert_not_called()
        normal.assert_not_called()

    def test_recovery_apply_requires_terminal_and_exact_continuation_consent(self):
        reviewed = {'action': 'migrate-recover', 'commands': [], 'blockers': [],
                    'headers': {'layout': 'system-package'}}
        with patch.object(setup.plugin_recovery, 'plan', return_value=reviewed), \
             patch.object(setup.plugin_recovery, 'apply') as apply, \
             patch.object(sys, 'stdin', io.StringIO()), contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(setup.main(['--plugins-recover', '/fixture/transaction.json', '--apply']), 1)
        apply.assert_not_called()
        with patch.object(setup.plugin_recovery, 'plan', return_value=reviewed), \
             patch.object(setup.plugin_recovery, 'apply') as apply, \
             patch.object(sys, 'stdin', Terminal()), patch('builtins.input', side_effect=['yes', 'yes']), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--plugins-recover', '/fixture/transaction.json', '--apply']), 0)
        apply.assert_not_called()

    def test_recovery_confirmation_never_authorizes_live_activation(self):
        reviewed = {'action': 'migrate-recover', 'commands': [], 'blockers': [],
                    'headers': {'layout': 'system-package'}}
        with patch.object(setup.plugin_recovery, 'plan', return_value=reviewed), \
             patch.object(setup.plugin_recovery, 'apply', return_value={'status': 'plugin-migrated-disabled'}) as apply, \
             patch.object(setup.plugin_manager, 'apply') as normal, \
             patch.object(sys, 'stdin', Terminal()), \
             patch('builtins.input', side_effect=['yes', setup.plugin_recovery.CONFIRMATION]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--plugins-recover', '/fixture/transaction.json', '--apply']), 0)
        self.assertTrue(apply.call_args.kwargs['resume_approved'])
        normal.assert_not_called()

    def test_migration_review_is_separate_and_read_only(self):
        reviewed = {'action': 'migrate', 'commands': [], 'blockers': []}
        with patch.object(setup.plugin_migration, 'plan', return_value=reviewed), \
             patch.object(setup.plugin_migration, 'apply') as apply, \
             patch.object(setup.plugin_manager, 'apply') as normal, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--plugins-migrate']), 0)
        apply.assert_not_called()
        normal.assert_not_called()

    def test_migration_apply_refuses_noninteractive_or_json_consent(self):
        reviewed = {'action': 'migrate', 'commands': [], 'blockers': []}
        with patch.object(setup.plugin_migration, 'plan', return_value=reviewed), \
             patch.object(setup.plugin_migration, 'apply') as apply, \
             patch.object(sys, 'stdin', io.StringIO()), contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(setup.main(['--plugins-migrate', '--apply']), 1)
            self.assertEqual(setup.main(['--plugins-migrate', '--apply', '--json']), 1)
        apply.assert_not_called()

    def test_migration_options_do_not_leak_to_release_or_other_plugin_stages(self):
        with patch.object(setup.plugin_migration, 'plan') as plan:
            for args in (['--plugins-migrate', '--plugins-activate'],
                         ['--plugins-migrate', '--bundle', '/fixture'],
                         ['--plugins-migrate', '--restart-bar'], ['--plugins-migrate', '--allow-legacy-state']):
                with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        setup.main(args)
            plan.assert_not_called()

    def test_migration_replacement_needs_exact_second_confirmation(self):
        reviewed = {'action': 'migrate', 'commands': [], 'blockers': []}
        for confirmation in ('yes', '', 'replace something-else'):
            with self.subTest(confirmation=confirmation), \
                 patch.object(setup.plugin_migration, 'plan', return_value=reviewed), \
                 patch.object(setup.plugin_migration, 'apply') as apply, \
                 patch.object(sys, 'stdin', Terminal()), patch('builtins.input', side_effect=['yes', confirmation]), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(setup.main(['--plugins-migrate', '--apply']), 0)
                apply.assert_not_called()

    def test_migration_consent_never_implies_live_activation_or_packages(self):
        reviewed = {'action': 'migrate', 'commands': [], 'blockers': []}
        with patch.object(setup.plugin_migration, 'plan', return_value=reviewed), \
             patch.object(setup.plugin_migration, 'apply', return_value={'status': 'plugin-migrated-disabled'}) as apply, \
             patch.object(setup.plugin_manager, 'apply') as normal, \
             patch.object(setup.bootstrap_packages, 'apply') as packages, \
             patch.object(sys, 'stdin', Terminal()), \
             patch('builtins.input', side_effect=['yes', setup.plugin_migration.CONFIRMATION]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--plugins-migrate', '--apply']), 0)
        self.assertTrue(apply.call_args.kwargs['replace_approved'])
        normal.assert_not_called()
        packages.assert_not_called()

    def test_plugin_review_never_applies_or_routes_to_release(self):
        reviewed = {'action': 'prepare', 'commands': [], 'blockers': []}
        with patch.object(setup.plugin_manager, 'plan', return_value=reviewed), \
             patch.object(setup.plugin_manager, 'apply') as apply, \
             patch.object(setup, 'local_release') as release, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--plugins']), 0)
        apply.assert_not_called()
        release.assert_not_called()

    def test_noninteractive_live_plugin_apply_is_refused(self):
        reviewed = {'action': 'activate', 'commands': [], 'blockers': []}
        with patch.object(setup.plugin_manager, 'plan', return_value=reviewed), \
             patch.object(setup.plugin_manager, 'apply') as apply, \
             patch.object(sys, 'stdin', io.StringIO()), contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(setup.main(['--plugins-activate', '--apply']), 1)
        apply.assert_not_called()

    def test_package_scopes_are_mutually_exclusive_and_package_only(self):
        for args in (['--runtime-only'], ['--plugin-build-only'], ['--enable-plugin-login'],
                     ['--session-activate', '--enable-plugin-login', '--disable-plugin-login'],
                     ['--packages', '--runtime-only', '--plugin-build-only']):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    setup.main(args)


class RemovedDistributionOptionsTests(unittest.TestCase):
    def test_obsolete_options_are_rejected_before_any_operation(self):
        options = (['--channels'], ['--update', '--channel', 'stable'],
                   ['--set-channel', 'dev'], ['--channels-file', 'pins.json'],
                   ['--release-dir', 'work/user-releases'],
                   ['--write-channel', 'pins.json'], ['--replace-channel'])
        with patch.object(setup, 'inspect') as inspect, \
             patch.object(setup, 'local_release') as release, \
             patch.object(setup, 'guide_stage') as guide:
            for args in options:
                with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        setup.main(args)
                    self.assertEqual(error.exception.code, 2)
            inspect.assert_not_called()
            release.assert_not_called()
            guide.assert_not_called()

    def test_help_has_no_obsolete_distribution_options(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as error:
            setup.main(['--help'])
        self.assertEqual(error.exception.code, 0)
        self.assertNotIn('channel', output.getvalue().lower())
        self.assertIn('--bundle', output.getvalue())

    def test_obsolete_implementation_and_pin_are_removed(self):
        for name in ('tools/release_channels.py', 'tests/test_release_channels.py',
                     'channels/omabuntu.json'):
            self.assertFalse((ROOT / name).exists(), name)


class Terminal(io.StringIO):
    def isatty(self):
        return True


class SetupFrontendTests(unittest.TestCase):
    def test_wordmark_is_compact_block_text_with_ascii_fallback(self):
        rows = setup_ui.wordmark().splitlines()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(len(row) <= 40 for row in rows))
        self.assertIn('█▀█', rows[0])
        ascii_rows = setup_ui.wordmark(ascii_only=True).splitlines()
        self.assertEqual(len(ascii_rows), 5)
        self.assertTrue(all(len(row) <= 58 and row.isascii() for row in ascii_rows))

    def test_dumb_or_ascii_terminal_uses_ascii_art(self):
        class AsciiTerminal(Terminal):
            @property
            def encoding(self):
                return 'ascii'
        for stream, env in [(Terminal(), {'TERM': 'dumb'}),
                            (AsciiTerminal(), {'TERM': 'xterm'})]:
            setup_ui.Console(stream, environ=env, width=80).welcome('Installation plan')
            self.assertNotIn('█', stream.getvalue())
            self.assertIn('###', stream.getvalue())

    def test_unicode_banner_and_tagline_are_shown_on_capable_terminal(self):
        stream = Terminal()
        setup_ui.Console(stream, environ={'TERM': 'xterm'}, width=80).welcome('Installation plan')
        self.assertIn('█▀█', stream.getvalue())
        self.assertIn('Your Ubuntu. Reimagined.', stream.getvalue())

    def test_colors_only_in_tty_and_no_color_is_respected(self):
        for stream, env, plain, expected in [
            (Terminal(), {'TERM': 'xterm'}, False, True),
            (Terminal(), {'TERM': 'xterm', 'NO_COLOR': ''}, False, False),
            (Terminal(), {'TERM': 'dumb'}, False, False),
            (Terminal(), {'TERM': 'xterm'}, True, False),
            (io.StringIO(), {'TERM': 'xterm'}, False, False),
        ]:
            console = setup_ui.Console(stream, plain=plain, environ=env)
            console.welcome('Installation plan')
            self.assertEqual('\033[' in stream.getvalue(), expected)

    def test_small_terminal_gets_compact_banner(self):
        stream = io.StringIO()
        setup_ui.Console(stream, width=28).welcome('Update plan')
        self.assertIn('OMABUNTU', stream.getvalue())
        self.assertNotIn('###', stream.getvalue())

    def test_plans_never_claim_ready_or_make_changes(self):
        for mode in ('install', 'update', 'rollback'):
            result = plan(mode)
            self.assertEqual(result['mode'], mode)
            self.assertTrue(result['target_supported'])
            self.assertFalse(result['ready_to_apply'])
            self.assertFalse(result['changes_made'])
            self.assertEqual(result['sources']['artwork_files'], 120)
            self.assertTrue(result['blockers'])

    def test_missing_installation_blocks_update_and_rollback(self):
        result = setup.inspect('rollback', os_info=SYSTEM, architecture='x86_64', which=lambda _: None,
                               installation={'ok': True, 'installed': False, 'previous_available': False})
        self.assertIn('No verified Omabuntu installation was found', result['blockers'])
        self.assertIn('No verified previous release is available', result['blockers'])

    def test_unsupported_host_does_not_pass(self):
        result = setup.inspect(os_info={'status': 'ok', 'values': {'ID': 'debian'}},
                               architecture='aarch64', which=lambda _: None, installation=INSTALLED)
        self.assertFalse(result['target_supported'])

    def test_invalid_source_inputs_block_before_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            result = plan(root=Path(directory))
        self.assertFalse(result['sources']['ok'])
        self.assertFalse(result['ready_to_apply'])

    def test_json_output_has_no_banner_or_ansi(self):
        stream = io.StringIO()
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup, 'inspect', return_value=plan()), contextlib.redirect_stdout(stream):
            self.assertEqual(setup.main(['--json']), 0)
        self.assertFalse(json.loads(stream.getvalue())['changes_made'])
        self.assertNotIn('\033', stream.getvalue())

    def test_check_is_nonzero_and_unsupported_apply_is_refused(self):
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup, 'inspect', return_value=plan()), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(setup.main(['--check']), 1)
            with self.assertRaises(SystemExit):
                setup.main(['--apply'])

    def test_explicit_bundle_plan_does_not_apply(self):
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup.release_update, 'review', return_value={'version': 'v2'}) as review, \
             patch.object(setup.release_update, 'apply') as apply, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(setup.main(['--update', '--bundle', '/fixture/bundle', '--json']), 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'reviewed-not-applied')
        self.assertEqual(review.call_args.args[2], 'update')
        apply.assert_not_called()

    def test_noninteractive_apply_without_approval_is_blocked(self):
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup.release_update, 'review', return_value={'version': 'v2'}), \
             patch.object(setup.release_update, 'apply') as apply, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(setup.main(['--bundle', '/fixture/bundle', '--json', '--apply']), 1)
        self.assertEqual(json.loads(output.getvalue())['status'], 'blocked')
        apply.assert_not_called()

    def test_json_apply_stays_one_document_with_legacy_manager_output(self):
        def applied(*args):
            print('Wallpaper restore: fixture')
            return {'status': 'installed-not-started'}
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup.release_update, 'review', return_value={'version': 'v2'}), \
             patch.object(setup.release_update, 'apply', side_effect=applied), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(setup.main(['--bundle', '/fixture/bundle', '--json', '--apply', '--approve', 'fixture']), 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'installed-not-started')
        self.assertNotIn('Wallpaper', output.getvalue())

    def test_package_and_source_modes_route_without_release_apply(self):
        for args in (['--ppa'], ['--packages'], ['--packages', '--base-only']):
            with self.subTest(args=args), patch.object(setup.os, 'getuid', return_value=1000), \
                 patch.object(setup, 'system_stage', return_value=0) as stage, \
                 patch.object(setup.release_update, 'apply') as apply:
                self.assertEqual(setup.main(args), 0)
                stage.assert_called_once()
                apply.assert_not_called()

    def test_source_bar_options_and_json_system_apply_are_refused(self):
        for args in (['--ppa', '--restart-bar'], ['--ppa', '--base-only'],
                     ['--packages', '--bundle', '/fixture'], ['--ppa', '--apply', '--json']):
            with self.subTest(args=args), patch.object(setup.os, 'getuid', return_value=1000), \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                setup.main(args)

    def test_saved_plan_is_a_regular_file_not_a_directory(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            root = Path(directory)
            saved = root / 'source-plan.json'
            saved.write_text(json.dumps({'kind': 'omabuntu-ppa-plan', 'blockers': []}))
            with patch.object(setup.os, 'getuid', return_value=1000), \
                 patch.object(setup, 'ROOT', root), \
                 patch.object(setup.bootstrap_sources, 'apply') as apply, \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(setup.main(['--ppa', '--plan', str(saved), '--json']), 0)
            self.assertEqual(json.loads(output.getvalue())['plan']['kind'], 'omabuntu-ppa-plan')
            apply.assert_not_called()

    def test_build_mode_does_not_route_to_deployment(self):
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup, 'build_stage', return_value=0) as stage, \
             patch.object(setup.release_update, 'apply') as apply:
            self.assertEqual(setup.main(['--build-release', '--jobs', '2', '--skip-artwork']), 0)
        stage.assert_called_once()
        apply.assert_not_called()

    def test_build_requires_separate_noninteractive_download_approval(self):
        plan = {'version': 'fixture', 'blockers': [], 'artwork': True}
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup.bootstrap_build, 'create_plan', return_value=plan), \
             patch.object(setup.bootstrap_build, 'apply') as apply, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(setup.main(['--build-release', '--apply', '--json']), 1)
        self.assertEqual(json.loads(output.getvalue())['status'], 'blocked')
        apply.assert_not_called()

    def test_font_mode_never_routes_to_deployment(self):
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup, 'font_stage', return_value=0) as stage, \
             patch.object(setup.release_update, 'apply') as deploy:
            self.assertEqual(setup.main(['--font']), 0)
        stage.assert_called_once()
        deploy.assert_not_called()

    def test_font_install_needs_explicit_approval(self):
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup.desktop_font, 'plan', return_value={'blockers': []}), \
             patch.object(setup.desktop_font, 'apply') as apply, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(setup.main(['--font', '--apply', '--json']), 1)
        self.assertEqual(json.loads(output.getvalue())['status'], 'blocked')
        apply.assert_not_called()

    def test_default_entry_shows_the_guide_without_applying(self):
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup, 'guide_stage', return_value=0) as guide, \
             patch.object(setup.release_update, 'apply') as apply:
            self.assertEqual(setup.main(['--plain']), 0)
        guide.assert_called_once()
        apply.assert_not_called()

    def test_guide_does_not_route_to_package_or_release_apply(self):
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup, 'guide_stage', return_value=0) as stage, \
             patch.object(setup.bootstrap_packages, 'apply') as packages, \
             patch.object(setup.release_update, 'apply') as release:
            self.assertEqual(setup.main(['--guide']), 0)
        stage.assert_called_once()
        packages.assert_not_called()
        release.assert_not_called()

    def test_activation_stage_does_not_start_a_release(self):
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup, 'activation_stage', return_value=0) as stage, \
             patch.object(setup.release_update, 'apply') as apply:
            self.assertEqual(setup.main(['--session-activate', '--enable-login']), 0)
        stage.assert_called_once()
        apply.assert_not_called()

    def test_session_stage_is_separate_from_release_restart(self):
        with patch.object(setup.os, 'getuid', return_value=1000), \
             patch.object(setup, 'session_stage', return_value=0) as stage, \
             patch.object(setup.release_update, 'apply') as apply:
            self.assertEqual(setup.main(['--session-config', '--keyboard-layout', 'de']), 0)
        stage.assert_called_once()
        self.assertIsNone(stage.call_args.args[0].manual_lock)
        apply.assert_not_called()

    def test_session_options_do_not_leak_into_other_stages(self):
        for args in (['--font', '--keyboard-layout', 'de'], ['--session-config', '--restart-bar'],
                     ['--session-config', '--bundle', '/fixture']):
            with self.subTest(args=args), patch.object(setup.os, 'getuid', return_value=1000), \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                setup.main(args)

    def test_root_is_refused(self):
        with patch.object(setup.os, 'getuid', return_value=0), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            setup.main([])

    def test_display_labels_pending_steps_not_fake_progress(self):
        stream = io.StringIO()
        setup.display(plan(), setup_ui.Console(stream, plain=True))
        self.assertIn('PREVIEW ONLY', stream.getvalue())
        self.assertIn('[BLOCKED]', stream.getvalue())
        self.assertIn('not a working stock-Ubuntu installer yet', stream.getvalue())

    def test_shell_wrapper_works_from_another_directory_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='omabuntu setup ') as directory:
            root = Path(directory)
            (root / 'tools').mkdir()
            script = root / 'install.sh'
            script.write_bytes((ROOT / 'install.sh').read_bytes())
            (root / 'tools/setup.py').write_text('import json,sys;print(json.dumps(sys.argv[1:]))\n')
            result = subprocess.run(['sh', str(script), '--update', '--plain'], cwd='/',
                                    capture_output=True, text=True, timeout=10, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), ['--update', '--plain'])


if __name__ == '__main__':
    unittest.main()
