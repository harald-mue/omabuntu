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
        reusable = patch.object(published, 'manager_reusable', return_value=False)
        reusable.start()
        self.addCleanup(reusable.stop)

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

    def test_declining_inner_package_review_defers_tools_without_outer_question(self):
        with patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'command', 'summary': 'missing'}), \
             patch.object(published, 'review_plugin_packages', return_value=({'blockers': []}, Path('/review/package-plan.json'))), \
             patch.object(published, 'ask') as ask, patch.object(published.setup, 'main', return_value=0) as apply:
            self.assertFalse(published.offer_plugin_packages())
            ask.assert_not_called()
            apply.assert_called_once_with(['--packages', '--plugin-build-only', '--plan', '/review/package-plan.json', '--apply'])

    def test_existing_tools_do_not_prompt_for_installation(self):
        with patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'done'}), \
             patch.object(published, 'ask') as ask, patch.object(published.setup, 'main') as apply:
            self.assertTrue(published.offer_plugin_packages())
            ask.assert_not_called()
            apply.assert_not_called()

    def test_blocked_optional_packages_can_be_deferred_without_application_attempt(self):
        with patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'command', 'summary': 'missing'}), \
             patch.object(published, 'review_plugin_packages', return_value=({'blockers': ['Installed package changes refused']}, Path('/review/plan.json'))), \
             patch.object(published, 'ask', return_value=True), patch.object(published.setup, 'main') as apply:
            self.assertFalse(published.offer_plugin_packages())
            apply.assert_not_called()
        self.assertIn('No plugin packages applied', self.stream.getvalue())

    def test_blocked_optional_packages_can_cancel_before_deployment(self):
        with patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'command', 'summary': 'missing'}), \
             patch.object(published, 'review_plugin_packages', return_value=({'blockers': ['blocked']}, Path('/review/plan.json'))), \
             patch.object(published, 'ask', return_value=False), patch.object(published.setup, 'main') as apply:
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

    def test_build_and_live_load_keep_separate_inner_approval_stages(self):
        with patch.object(published.plugin_manager, 'plan', return_value={'blockers': []}), \
             patch.object(published.user_install, 'Installation'), \
             patch.object(published, 'ask') as ask, \
             patch.object(published.setup, 'main', return_value=0) as apply:
            published.offer_plugins(ROOT)
            ask.assert_not_called()
            self.assertEqual([c.args[0] for c in apply.call_args_list],
                             [['--plugins', '--apply'], ['--plugins-activate', '--apply']])

    def test_separate_live_approval_is_forwarded_but_not_login_consent(self):
        with patch.object(published.plugin_manager, 'plan', return_value={'blockers': []}), \
             patch.object(published.user_install, 'Installation'), \
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
             patch.object(published, 'ask') as ask, patch.object(published.setup, 'main', return_value=0) as apply:
            published.offer_plugins(ROOT)
        ask.assert_not_called()
        apply.assert_called_once_with(['--plugins-activate', '--apply'])

    def test_published_native_pair_gets_its_own_handoff_approval(self):
        incoming = {'update_contract': {'native_target': published.native_transition.TO}}
        old = {'update_contract': {'native_target': published.native_transition.FROM}}
        with patch.object(sys, 'argv', ['published', '--bundle', '/fixture']), \
             patch.object(published.user_install, 'verify_bundle', side_effect=[incoming, old, incoming]), \
             patch.object(published.plugin_manager, 'bundle_policy', return_value=None), \
             patch.object(published.setup_guide, 'ppa_stage', return_value={'status': 'done'}), \
             patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'done'}), \
             patch.object(published.setup_guide, 'font_stage', return_value={'status': 'done'}), \
             patch.object(published.user_install, 'Installation') as installation, \
             patch.object(published, 'offer_artwork'), \
             patch.object(published, 'offer_hyprpaper_condition'), \
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
             patch.object(published, 'offer_hyprpaper_condition'), \
             patch.object(published, 'offer_session') as session, \
             patch.object(published, 'offer_plugins') as plugins, \
             patch.object(published.setup, 'main', return_value=0) as apply:
            installation.return_value.selected.return_value = None
            installation.return_value.running.return_value = None
            def installed(options):
                installation.return_value.selected.return_value = 'releases/new'
                return 0
            apply.side_effect = installed
            published.main()
        apply.assert_called_once_with(['--bundle', '/fixture', '--apply'])
        session.assert_called_once_with(ROOT)
        plugins.assert_called_once_with(ROOT, prerequisites_ready=False)
        self.assertIn('rerun the same install.sh entry point', self.stream.getvalue())

    def test_current_application_discovers_repair_without_redeploy_or_compilers(self):
        current = {'version': 'current'}
        with patch.object(sys, 'argv', ['published', '--bundle', '/fixture']), \
             patch.object(published.user_install, 'verify_bundle', return_value=current), \
             patch.object(published.plugin_manager, 'bundle_policy', return_value={}), \
             patch.object(published.setup_guide, 'ppa_stage', return_value={'status': 'done'}), \
             patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'done'}), \
             patch.object(published.setup_guide, 'font_stage', return_value={'status': 'done'}), \
             patch.object(published, 'manager_reusable', return_value=True), \
             patch.object(published, 'offer_plugin_packages') as packages, \
             patch.object(published, 'offer_session') as session, \
             patch.object(published.user_install, 'Installation') as installation, \
             patch.object(published.plugin_manager, 'plan', return_value={'receipt_before': {'activated': True}, 'blockers': ['enabled']}), \
             patch.object(published.native_transition, 'manager_ready', return_value={'loaded': []}), \
             patch.object(published, 'offer_artwork'), \
             patch.object(published, 'offer_hyprpaper_condition'), \
             patch.object(published, 'ask') as ask, patch.object(published.setup, 'main', return_value=0) as apply:
            installation.return_value.selected.return_value = 'releases/current'
            installation.return_value.running.return_value = {'pid': 1}
            published.main()
        packages.assert_not_called()
        session.assert_called_once_with(ROOT)
        ask.assert_not_called()
        apply.assert_called_once_with(['--plugins-repair', '--apply'])
        self.assertIn('skipping deployment/restart', self.stream.getvalue())

    def test_cancelled_deployment_does_not_proceed_to_desktop_steps(self):
        incoming, old = {'version': 'new'}, {'version': 'old'}
        with patch.object(sys, 'argv', ['published', '--bundle', '/fixture']), \
             patch.object(published.user_install, 'verify_bundle', side_effect=[incoming, old, old]), \
             patch.object(published.plugin_manager, 'bundle_policy', return_value={}), \
             patch.object(published.setup_guide, 'ppa_stage', return_value={'status': 'done'}), \
             patch.object(published.setup_guide, 'packages_stage', return_value={'status': 'done'}), \
             patch.object(published.setup_guide, 'font_stage', return_value={'status': 'done'}), \
             patch.object(published, 'offer_plugin_packages', return_value=True), \
             patch.object(published.user_install, 'Installation') as installation, \
             patch.object(published, 'offer_hyprpaper_condition'), \
             patch.object(published, 'offer_session') as session, patch.object(published, 'offer_plugins') as plugins, \
             patch.object(published.setup, 'main', return_value=0):
            installation.return_value.selected.return_value = 'releases/old'
            installation.return_value.running.return_value = None
            published.main()
        session.assert_not_called()
        plugins.assert_not_called()

    def test_hyprpaper_condition_skips_when_the_unit_is_absent(self):
        with patch.object(published.deploy_hyprpaper_condition, 'review', return_value={'unit': None, 'current': False}), \
             patch.object(published, 'ask') as ask, patch.object(published.deploy_hyprpaper_condition, 'deploy') as deploy:
            published.offer_hyprpaper_condition()
        ask.assert_not_called()
        deploy.assert_not_called()

    def test_hyprpaper_condition_never_repeats_the_question_when_current(self):
        with patch.object(published.deploy_hyprpaper_condition, 'review', return_value={'unit': Path('/usr/lib/systemd/user/hyprpaper.service'), 'current': True}), \
             patch.object(published, 'ask') as ask, patch.object(published.deploy_hyprpaper_condition, 'deploy') as deploy:
            published.offer_hyprpaper_condition()
        ask.assert_not_called()
        deploy.assert_not_called()

    def test_hyprpaper_condition_asks_once_and_deploys(self):
        with patch.object(published.deploy_hyprpaper_condition, 'review', return_value={'unit': Path('/usr/lib/systemd/user/hyprpaper.service'), 'current': False}), \
             patch.object(published, 'ask', return_value=True) as ask, \
             patch.object(published.deploy_hyprpaper_condition, 'deploy', return_value={'changed': True, 'backup': None}) as deploy:
            published.offer_hyprpaper_condition()
        ask.assert_called_once()
        deploy.assert_called_once_with()
        self.assertIn('takes effect at the next login', self.stream.getvalue())

    def test_hyprpaper_condition_decline_preserves_every_wayland_session(self):
        with patch.object(published.deploy_hyprpaper_condition, 'review', return_value={'unit': Path('/usr/lib/systemd/user/hyprpaper.service'), 'current': False}), \
             patch.object(published, 'ask', return_value=False), \
             patch.object(published.deploy_hyprpaper_condition, 'deploy') as deploy:
            published.offer_hyprpaper_condition()
        deploy.assert_not_called()
        self.assertIn('every Wayland session', self.stream.getvalue())

    def test_hyprpaper_condition_failure_does_not_touch_the_service(self):
        with patch.object(published.deploy_hyprpaper_condition, 'review', return_value={'unit': Path('/usr/lib/systemd/user/hyprpaper.service'), 'current': False}), \
             patch.object(published, 'ask', return_value=True), \
             patch.object(published.deploy_hyprpaper_condition, 'deploy', side_effect=ValueError('unsafe')):
            published.offer_hyprpaper_condition()
        self.assertIn('no service was changed', self.stream.getvalue())

    def test_skip_keyboard_choice_preserves_profile_without_an_extra_yes_no(self):
        with patch.object(published.session_config, 'require_stopped'), \
             patch.object(published.session_config, 'plan', return_value={'blockers': [], 'changes': ['module'], 'keyboard_layout': 'de'}), \
             patch('builtins.input', return_value='skip'), patch.object(published, 'ask') as ask, \
             patch.object(published.setup, 'main') as apply:
            published.offer_session(ROOT)
        ask.assert_not_called()
        apply.assert_not_called()

    def test_current_login_files_do_not_repeat_persistent_grant_questions(self):
        with patch.object(published.session_config, 'require_stopped'), \
             patch.object(published.session_config, 'plan', return_value={'blockers': [], 'changes': []}), \
             patch.object(published.session_activation, 'plan', return_value={'blockers': [], 'changes': []}), \
             patch.object(published, 'ask') as ask, patch.object(published.setup, 'main') as apply:
            published.offer_session(ROOT)
        ask.assert_not_called()
        apply.assert_not_called()

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
             patch.object(published, 'ask', side_effect=[True, False]), \
             patch.object(published.setup, 'main', return_value=0) as apply:
            published.offer_session(ROOT)
            apply.assert_called_once_with(['--session-activate', '--apply', '--enable-plugin-login'])


if __name__ == '__main__':
    unittest.main()



class PublishedArtworkTests(unittest.TestCase):
    def setUp(self):
        self.stream = io.StringIO()
        self.output = contextlib.redirect_stdout(self.stream)
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.installation = published.user_install.Installation(
            self.base / 'data', self.base / 'state', self.base / 'bin')
        self.release = self.installation.root / 'releases/public'
        self.release.mkdir(parents=True)
        patch.object(self.installation, 'selected', return_value='releases/public').start()
        self.addCleanup(patch.stopall)

    def flow(self, plan):
        with patch.object(published, 'ask', return_value=True) as ask, \
             patch.object(published.user_artwork, 'plan', return_value=plan) as review, \
             patch.object(published.user_artwork, 'apply') as apply:
            published.offer_artwork(self.installation)
        return ask, review, apply

    def test_artwork_free_release_offers_one_private_download(self):
        plan = {'missing': ['backgrounds/tokyo/0.webp'], 'bytes': 10, 'blockers': []}
        ask, review, apply = self.flow(plan)
        review.assert_called_once_with()
        ask.assert_called_once()
        apply.assert_called_once()
        self.assertEqual(apply.call_args.args[0], plan)
        self.assertEqual(apply.call_args.args[1], published.guided.digest(plan))
        self.assertEqual(apply.call_args.kwargs.get('progress'), published.user_artwork.terminal_progress)

    def test_release_local_artwork_never_offers_a_download(self):
        (self.release / 'config/menu/backgrounds').mkdir(parents=True)
        ask, review, apply = self.flow({'missing': ['x'], 'bytes': 1, 'blockers': []})
        ask.assert_not_called()
        review.assert_not_called()
        apply.assert_not_called()

    def test_complete_artwork_skips_the_download_question(self):
        ask, review, apply = self.flow({'missing': [], 'bytes': 1, 'blockers': []})
        ask.assert_not_called()
        apply.assert_not_called()

    def test_failed_download_is_reported_without_silent_success(self):
        with patch.object(published, 'ask', return_value=True), \
             patch.object(published.user_artwork, 'plan',
                          return_value={'missing': ['a'], 'bytes': 1, 'blockers': []}), \
             patch.object(published.user_artwork, 'apply', side_effect=ValueError('network')):
            published.offer_artwork(self.installation)
        self.assertIn('download failed', self.stream.getvalue())
