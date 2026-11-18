"""Activation focus deployment contracts; fixture files and fake compositor only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import focus_policy as focus
import user_install as u


class Host:
    def __init__(self, directory, live=False):
        self.directory, self.live = directory, live
        self.enabled, self.disabled = False, False
        self.reloads = 0
        self.fail_once = False
        self.concurrent = False
        self.invalid = False
    def context(self, recovery=False):
        if self.invalid and not recovery: raise ValueError('Fixture config error')
        return ({'live': False} if not self.live else
                {'live': True, 'focus': self.enabled, 'autoreload': self.disabled, 'signature': 'fixture'})
    def guard(self, value): self.disabled = value
    def focus(self, value): self.enabled = value
    def option(self, name):
        return self.enabled if name == 'misc:focus_on_activate' else self.disabled
    def reload(self):
        self.reloads += 1
        self.disabled = False
        text = (self.directory / 'hyprland.lua').read_text()
        self.enabled = focus.INCLUDE in text and (self.directory / focus.NAME).exists()
        if self.fail_once:
            self.fail_once = False
            self.invalid = True
            if self.concurrent:
                with (self.directory / 'hyprland.lua').open('a') as stream: stream.write('-- user concurrent edit\n')
            raise ValueError('Fixture reload failure')
        self.invalid = False


class FocusPolicyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work');self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.app = u.Installation(self.base/'app', self.base/'state', self.base/'bin/omabuntu')
        selected = patch.object(self.app, 'selected', return_value='releases/new');selected.start();self.addCleanup(selected.stop)
        bundle = self.app.root / 'releases/new';bundle.mkdir(parents=True)
        for name in set(u.INCOMING) | {focus.ARTIFACT}:
            path = bundle/name;path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(focus.PAYLOAD if name == focus.ARTIFACT else 'fixture')
            path.chmod(0o755 if name == 'runtime/bin/quickshell' else 0o444)
        self.meta = {'schema_version':1, 'scope':'omabuntu-user-release-v1', 'version':'new',
                     'autostart':False,'lock_activation':False,'files':u.file_manifest(bundle)}
        (bundle/'release.json').write_text(json.dumps(self.meta))
        self.directory = self.base/'config/hypr';self.directory.mkdir(parents=True)
        self.entry = self.directory/'hyprland.lua'
        self.original = '-- personal profile\nhl.config({ general = { gaps_in = 4 } })\n'
        self.entry.write_text(self.original);self.entry.chmod(0o640)
        self.host = Host(self.directory)
    def plan(self): return focus.plan(self.app,self.directory,self.host)
    def apply(self, reviewed=None):
        reviewed = reviewed or self.plan()
        return focus.apply(self.app,reviewed,focus.digest(reviewed),self.host)
    def ensure(self, confirm=None):
        return focus.ensure(self.app,confirm or Mock(return_value=True),lambda message: None,
                            directory=self.directory,host=self.host)
    def journal(self): return next((self.app.state/'focus-policy-transactions').glob('*/transaction.json'))

    def test_shipped_payload_and_fresh_profiles_match_reviewed_rule(self):
        self.assertEqual((ROOT/focus.ARTIFACT).read_text(),focus.PAYLOAD)
        for name in ('config/hypr/session-template.lua.in','config/hypr/minimal.lua'):
            self.assertIn('focus_on_activate = true',(ROOT/name).read_text())
        self.assertNotIn('focus-policy.lua',u.INCOMING)  # Older verified bundles remain readable.

    def test_plan_is_readonly_and_stopped_install_is_additive_and_backed_up(self):
        reviewed = self.plan()
        self.assertFalse(self.app.state.exists())
        self.assertEqual(self.entry.read_text(),self.original)
        self.assertEqual(self.apply(reviewed)['status'],'staged-next-login')
        self.assertEqual(self.entry.read_text(),self.original+'\n'+focus.MARKER+'\n'+focus.INCLUDE+'\n')
        self.assertEqual(self.entry.stat().st_mode&0o777,0o640)
        self.assertEqual((self.journal().parent/'entry').read_text(),self.original)
        self.assertEqual(self.host.reloads,0)

    def test_repeat_install_or_update_does_not_prompt_write_or_reload(self):
        first = Mock(return_value=True);self.ensure(first);first.assert_called_once()
        before = self.entry.stat().st_mtime_ns
        second = Mock(return_value=True)
        self.assertEqual(self.ensure(second)['status'],'current')
        second.assert_not_called();self.assertEqual(before,self.entry.stat().st_mtime_ns)
        self.assertEqual(len(list((self.app.state/'focus-policy-transactions').glob('*/transaction.json'))),1)

    def test_live_upgrade_reloads_and_restores_previous_autoreload(self):
        self.host.live = True;self.host.disabled = True
        self.assertEqual(self.apply()['status'],'applied-live')
        self.assertTrue(self.host.enabled);self.assertTrue(self.host.disabled)
        self.assertEqual(self.host.reloads,1)
        confirm=Mock();self.ensure(confirm);confirm.assert_not_called()

    def test_decline_keeps_personal_profile_and_has_no_transaction(self):
        self.assertEqual(self.ensure(Mock(return_value=False))['status'],'deferred-by-user')
        self.assertEqual(self.entry.read_text(),self.original)
        self.assertFalse(self.app.state.exists())

    def test_missing_profile_defers_without_compositor_probe(self):
        self.entry.unlink()
        with patch.object(self.host,'context') as context:
            self.assertEqual(self.plan()['status'],'deferred-no-profile')
        context.assert_not_called()

    def test_edited_module_or_ambiguous_include_is_not_overwritten(self):
        module=self.directory/focus.NAME;module.write_text('-- user override\n')
        self.assertTrue(self.plan()['blockers']);self.assertEqual(self.ensure()['status'],'blocked')
        self.assertEqual(module.read_text(),'-- user override\n')
        module.unlink();self.entry.write_text(self.original+'dofile("omabuntu-focus.lua")\n')
        self.assertTrue(self.plan()['blockers'])

    def test_symlinked_target_is_refused(self):
        (self.directory/focus.NAME).symlink_to(self.entry)
        with self.assertRaisesRegex(ValueError,'Unsafe'):self.plan()
        self.assertEqual(self.entry.read_text(),self.original)

    def test_stale_input_and_bad_approval_do_not_write(self):
        reviewed=self.plan()
        with self.assertRaises(ValueError):focus.apply(self.app,reviewed,'bad',self.host)
        self.assertFalse(self.app.state.exists())
        self.entry.write_text(self.original+'-- user edit\n')
        with self.assertRaisesRegex(ValueError,'changed'):self.apply(reviewed)
        self.assertFalse((self.directory/focus.NAME).exists())

    def test_failed_reload_restores_bytes_modes_runtime_and_autoreload(self):
        self.host.live=True;self.host.disabled=True;self.host.fail_once=True
        with self.assertRaisesRegex(ValueError,'reload'):self.apply()
        self.assertEqual(self.entry.read_text(),self.original)
        self.assertEqual(self.entry.stat().st_mode&0o777,0o640)
        self.assertFalse((self.directory/focus.NAME).exists())
        self.assertFalse(self.host.enabled);self.assertTrue(self.host.disabled)
        self.assertEqual(u.read_json(self.journal())['status'],'restored')

    def test_concurrent_edits_are_preserved_and_recovery_can_resume(self):
        self.host.live=True;self.host.fail_once=True;self.host.concurrent=True
        with self.assertRaisesRegex(ValueError,'Concurrent'):self.apply()
        changed=self.entry.read_text();self.assertIn('-- user concurrent edit',changed)
        self.assertTrue(focus.pending(self.app))
        self.assertEqual(self.ensure()['status'],'failed')
        reviewed=u.read_json(self.journal())['plan']
        self.entry.write_text(reviewed['payload']['entry'])
        self.entry.chmod(reviewed['before']['entry']['mode'])
        self.assertEqual(focus.recover(self.app,self.journal(),self.host)['status'],'restored')
        self.assertEqual(self.entry.read_text(),self.original)

    def test_explicit_recovery_checks_backup_integrity_and_session_identity(self):
        self.host.live=True;self.apply();journal=self.journal();backup=journal.parent/'entry'
        backup.write_text('-- corrupted backup\n')
        with self.assertRaisesRegex(ValueError,'integrity'):focus.recover(self.app,journal,self.host)
        self.assertIn(focus.INCLUDE,self.entry.read_text())

    def test_old_bundle_does_not_read_or_write_host_configuration(self):
        with patch.object(focus.u,'verify_bundle',return_value={'files':{}}),patch.object(self.host,'context') as context:
            self.assertEqual(self.ensure()['status'],'not-shipped')
        context.assert_not_called();self.assertFalse(self.app.state.exists())

    def test_focus_rollout_preserves_later_explicit_managed_profile_adoption(self):
        import session_config
        managed=self.directory/'omabuntu-managed.lua'
        template=(ROOT/'config/hypr/omabuntu-managed.lua').read_bytes()
        managed.write_bytes(template)
        entry=session_config.MANAGED_MARKER+'\n'+session_config.MANAGED_INCLUDE+'\n'+focus.MARKER+'\n'+focus.INCLUDE+'\n'
        (self.directory/focus.NAME).write_text(focus.PAYLOAD)
        self.assertTrue(session_config.adoptable(entry,managed,template))
        (self.directory/focus.NAME).write_text('-- user override\n')
        self.assertFalse(session_config.adoptable(entry,managed,template))

    def test_real_host_adapter_checks_session_version_errors_and_options(self):
        metadata = json.dumps({'version':'0.57.0','dirty':False,'commit':'0'*40})
        with patch.dict('os.environ', {'XDG_CURRENT_DESKTOP':'Hyprland', 'HYPRLAND_INSTANCE_SIGNATURE':'fixture'}), \
             patch.object(focus.subprocess,'run',return_value=Mock(returncode=0)), \
             patch.object(focus.Host,'command',side_effect=[metadata,'', '{"bool":false}', '{"bool":true}']) as command:
            self.assertEqual(focus.Host().context(),{'live':True,'focus':False,'autoreload':True,'signature':'fixture'})
            self.assertIn(('configerrors',),[call.args for call in command.call_args_list])
        with patch.dict('os.environ', {'XDG_CURRENT_DESKTOP':'GNOME','HYPRLAND_INSTANCE_SIGNATURE':''}), \
             patch.object(focus.subprocess,'run',return_value=Mock(returncode=0)), \
             patch.object(focus.Host,'command') as command:
            with self.assertRaisesRegex(ValueError,'outside'):focus.Host().context()
            command.assert_not_called()

    def test_invalid_payload_never_runs_configuration(self):
        with patch.object(focus.u,'verify_bundle',return_value=self.meta):
            (self.app.root/'releases/new'/focus.ARTIFACT).chmod(0o644)
            (self.app.root/'releases/new'/focus.ARTIFACT).write_text('error("unreviewed")\n')
            with self.assertRaisesRegex(ValueError,'Unreviewed'):self.plan()
        self.assertEqual(self.entry.read_text(),self.original)
