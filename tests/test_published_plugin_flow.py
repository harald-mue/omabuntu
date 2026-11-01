"""Published application installation offers, but never implies, plugin consent."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import published_install as published


class PublishedPluginFlowTests(unittest.TestCase):
    def setUp(self):
        self.stream = io.StringIO()
        self.output = contextlib.redirect_stdout(self.stream)
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_optional_review_creates_private_parent_directories(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as temporary:
            root = Path(temporary)
            with patch.object(published, '__file__', str(root / 'tools/published_install.py')), \
                 patch.object(published.bootstrap_packages, 'prepare', return_value={'blockers': []}) as prepare:
                plan, path = published.review_plugin_packages()
            self.assertFalse(plan['blockers'])
            self.assertEqual(path.name, 'package-plan.json')
            for directory in (root / 'work', root / 'work/bootstrap', path.parent):
                self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            prepare.assert_called_once_with(path.parent, plugin_build_only=True)

    def test_missing_plugin_tools_are_a_separately_approved_scope(self):
        with patch.object(published.setup_guide, 'packages_stage', side_effect=[
                 {'status': 'command', 'summary': 'missing'}, {'status': 'done'}]) as stage, \
             patch.object(published, 'review_plugin_packages', return_value=({'blockers': []}, Path('/review/package-plan.json'))), \
             patch.object(published, 'ask', return_value=True), patch.object(published.setup, 'main', return_value=0) as apply:
            self.assertTrue(published.offer_plugin_packages())
            self.assertTrue(stage.call_args.kwargs['plugin_build_only'])
            apply.assert_called_once_with(['--packages', '--plugin-build-only', '--plan', '/review/package-plan.json', '--apply'])

    def test_declining_tools_does_not_cancel_or_build_the_application(self):
        with patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'command', 'summary': 'missing'}), \
             patch.object(published, 'ask', return_value=False), patch.object(published.setup, 'main') as apply:
            self.assertFalse(published.offer_plugin_packages())
            apply.assert_not_called()

    def test_existing_tools_do_not_prompt_for_installation(self):
        with patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'done'}), \
             patch.object(published, 'ask') as ask, patch.object(published.setup, 'main') as apply:
            self.assertTrue(published.offer_plugin_packages())
            ask.assert_not_called()
            apply.assert_not_called()

    def test_blocked_optional_packages_can_be_deferred_without_application_attempt(self):
        with patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'command', 'summary': 'missing'}), \
             patch.object(published, 'review_plugin_packages', return_value=({'blockers': ['Installed package changes refused']}, Path('/review/plan.json'))), \
             patch.object(published, 'ask', side_effect=[True, True]), patch.object(published.setup, 'main') as apply:
            self.assertFalse(published.offer_plugin_packages())
            apply.assert_not_called()
        self.assertIn('No plugin packages applied', self.stream.getvalue())

    def test_blocked_optional_packages_can_cancel_before_deployment(self):
        with patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'command', 'summary': 'missing'}), \
             patch.object(published, 'review_plugin_packages', return_value=({'blockers': ['blocked']}, Path('/review/plan.json'))), \
             patch.object(published, 'ask', side_effect=[True, False]), patch.object(published.setup, 'main') as apply:
            with self.assertRaises(SystemExit):
                published.offer_plugin_packages()
            apply.assert_not_called()

    def test_failed_optional_apply_is_not_swallowed_as_deferral(self):
        with patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'command', 'summary': 'missing'}), \
             patch.object(published, 'review_plugin_packages', return_value=({'blockers': []}, Path('/review/plan.json'))), \
             patch.object(published, 'ask', return_value=True), patch.object(published.setup, 'main', return_value=1):
            with self.assertRaises(SystemExit):
                published.offer_plugin_packages()

    def test_inner_package_decline_does_not_imply_tools_ready(self):
        with patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'command', 'summary': 'missing'}), \
             patch.object(published, 'review_plugin_packages', return_value=({'blockers': []}, Path('/review/plan.json'))), \
             patch.object(published, 'ask', return_value=True), patch.object(published.setup, 'main', return_value=0):
            self.assertFalse(published.offer_plugin_packages())

    def test_deferred_packages_do_not_offer_a_new_plugin_build(self):
        with patch.object(published.plugin_manager, 'plan', return_value={'blockers': []}), \
             patch.object(published, 'ask') as ask, patch.object(published.setup, 'main') as apply:
            published.offer_plugins(ROOT, prerequisites_ready=False)
            ask.assert_not_called()
            apply.assert_not_called()
        self.assertNotIn('--plugins --apply', self.stream.getvalue())

    def test_mismatched_session_defers_without_build_or_load(self):
        with patch.object(published.plugin_manager, 'plan', return_value={'blockers': ['Installed and running differ']}), \
             patch.object(published, 'ask') as ask, patch.object(published.setup, 'main') as apply:
            published.offer_plugins(ROOT)
            ask.assert_not_called()
            apply.assert_not_called()

    def test_ready_session_still_asks_separately_before_live_loading(self):
        with patch.object(published.plugin_manager, 'plan', return_value={'blockers': []}), \
             patch.object(published, 'ask', side_effect=[True, False]), \
             patch.object(published.setup, 'main', return_value=0) as apply:
            published.offer_plugins(ROOT)
            apply.assert_called_once_with(['--plugins', '--apply'])

    def test_separate_live_approval_is_forwarded_but_not_login_consent(self):
        with patch.object(published.plugin_manager, 'plan', return_value={'blockers': []}), \
             patch.object(published, 'ask', return_value=True), \
             patch.object(published.setup, 'main', return_value=0) as apply:
            published.offer_plugins(ROOT)
            self.assertEqual([c.args[0] for c in apply.call_args_list],
                             [['--plugins', '--apply'], ['--plugins-activate', '--apply']])

    def test_healthy_active_manager_is_not_rebuilt_or_loaded_again(self):
        with patch.object(published.plugin_manager, 'plan', return_value={'receipt_before': {}, 'blockers': ['enabled']}), \
             patch.object(published.native_transition, 'manager_ready', return_value={'loaded': [{'name': 'hyprbars'}]}), \
             patch.object(published, 'ask') as ask, patch.object(published.setup, 'main') as apply:
            published.offer_plugins(ROOT, prerequisites_ready=False)
        ask.assert_not_called()
        apply.assert_not_called()

    def test_healthy_disabled_manager_still_needs_live_consent(self):
        with patch.object(published.plugin_manager, 'plan', return_value={'receipt_before': {}, 'blockers': []}), \
             patch.object(published.native_transition, 'manager_ready', return_value={'loaded': []}), \
             patch.object(published, 'ask', return_value=False) as ask, patch.object(published.setup, 'main') as apply:
            published.offer_plugins(ROOT)
        self.assertEqual(ask.call_count, 1)
        apply.assert_not_called()

    def test_published_native_pair_gets_its_own_handoff_approval(self):
        incoming = {'update_contract': {'native_target': published.native_transition.TO}}
        old = {'update_contract': {'native_target': published.native_transition.FROM}}
        with patch.object(sys, 'argv', ['published', '--bundle', '/fixture']), \
             patch.object(published.user_install, 'verify_bundle', side_effect=[incoming, old]), \
             patch.object(published.plugin_manager, 'bundle_policy', return_value=None), \
             patch.object(published.setup_guide, 'ppa_stage', return_value={'status': 'done'}), \
             patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'done'}), \
             patch.object(published.setup_guide, 'font_stage', return_value={'status': 'done'}), \
             patch.object(published.user_install, 'Installation') as installation, \
             patch.object(published, 'ask', return_value=True) as ask, \
             patch.object(published.setup, 'main', return_value=0) as apply:
            installation.return_value.selected.return_value = 'releases/old'
            installation.return_value.running.return_value = None
            published.main()
        self.assertEqual(ask.call_count, 1)
        self.assertIn('--migrate-native', apply.call_args.args[0])
        self.assertNotIn('--restart-bar', apply.call_args.args[0])

    def test_single_entry_installs_and_offers_profile_after_package_deferral(self):
        with patch.object(sys, 'argv', ['published', '--bundle', '/fixture']), \
             patch.object(published.user_install, 'verify_bundle', return_value={}), \
             patch.object(published.plugin_manager, 'bundle_policy', return_value={}), \
             patch.object(published.setup_guide, 'ppa_stage', return_value={'status': 'done'}), \
             patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'done'}), \
             patch.object(published.setup_guide, 'font_stage', return_value={'status': 'done'}), \
             patch.object(published.user_install, 'Installation') as installation, \
             patch.object(published, 'offer_plugin_packages', return_value=False), \
             patch.object(published, 'offer_session') as session, \
             patch.object(published, 'offer_plugins') as plugins, \
             patch.object(published.setup, 'main', return_value=0) as apply:
            installation.return_value.selected.return_value = None
            installation.return_value.running.return_value = None
            published.main()
        apply.assert_called_once_with(['--bundle', '/fixture', '--apply'])
        session.assert_called_once_with(ROOT)
        plugins.assert_called_once_with(ROOT, prerequisites_ready=False)
        self.assertIn('rerun the same install.sh entry point', self.stream.getvalue())

    def test_live_session_never_gets_configuration_writes(self):
        with patch.object(published.session_config, 'require_stopped', side_effect=ValueError('running')), \
             patch.object(published.session_config, 'plan') as plan, patch.object(published.setup, 'main') as apply:
            published.offer_session(ROOT)
            plan.assert_not_called()
            apply.assert_not_called()

    def test_private_profile_is_not_adopted_or_merged(self):
        with patch.object(published.session_config, 'require_stopped'), \
             patch.object(published.session_config, 'plan', return_value={'blockers': ['unowned profile']}), \
             patch.object(published, 'ask') as ask, patch.object(published.setup, 'main') as apply:
            published.offer_session(ROOT)
            ask.assert_not_called()
            apply.assert_not_called()

    def test_plugin_login_consent_does_not_enable_bar_unit(self):
        with patch.object(published.session_config, 'require_stopped'), \
             patch.object(published.session_config, 'plan', return_value={'blockers': [], 'changes': []}), \
             patch.object(published.session_activation, 'plan', return_value={'blockers': []}), \
             patch.object(published, 'ask', side_effect=[True, True, False]), \
             patch.object(published.setup, 'main', return_value=0) as apply:
            published.offer_session(ROOT)
            apply.assert_called_once_with(['--session-activate', '--apply', '--enable-plugin-login'])


if __name__ == '__main__':
    unittest.main()
