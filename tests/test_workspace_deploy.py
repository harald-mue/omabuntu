"""Exercise deployment journaling/recovery with fixture-only files and host IO."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import user_install
import workspace_deploy as deploy
import workspace_migration as migration
import test_monitor_workspaces as policy_tests
import test_workspace_persistence as persistence


class App:
    def __init__(self, base):
        self.root, self.state = base / 'data', base / 'state'
        self.root.mkdir(mode=0o700); self.state.mkdir(mode=0o700)
        self.live = True
        self.starts = 0
        self.fail_start = False
    def selected(self): return 'releases/candidate'
    def require_settled(self): pass
    def running(self): return {'pid': 123} if self.live else None
    def stop(self): self.live = False
    def start(self, restore_background=True):
        assert restore_background is False
        self.starts += 1
        if self.fail_start:
            self.fail_start = False
            raise ValueError('Fixture start failure')
        self.live = True


class Host:
    def __init__(self, config, state):
        self.config, self.state = config, state
        self.disabled = False
        self.fail = None
        self.reloads = 0
        self.binding_rows = [dict(modmask=mods, key=str(slot % 10), keycode=0, description=label + str(slot))
                             for mods, label in ((64, 'Switch to workspace '), (65, 'Move window to workspace '))
                             for slot in range(1, 11)]
        self.value = {'monitors': [dict(id=0,name='eDP-1',description='Laptop',mirrorOf='none'),
                                   dict(id=1,name='DP-1',description='External',mirrorOf='none')],
                      'workspaces': [dict(id=1,monitor='eDP-1',windows=0,tiledLayout='dwindle'),
                                     dict(id=2,monitor='DP-1',windows=1,tiledLayout='scrolling')],
                      'clients': [dict(address='0xabc',monitor=1,floating=False,fullscreen=0,tags=[],workspace=2)]}
    def snapshot(self): return copy.deepcopy(self.value)
    def bindings(self): return copy.deepcopy(self.binding_rows)
    def state_home(self): return str(self.state)
    def errors(self): return ''
    def autoreload(self): return self.disabled
    def set_autoreload(self, value): self.disabled = value
    def reload(self):
        self.reloads += 1
        if 'require("omabuntu-monitor-workspaces")' not in (self.config/'hyprland.lua').read_text():
            return
        for w in self.value['workspaces']:
            if w['id'] == 2:
                w['id'] = 12
        for w in self.value['clients']:
            if w['workspace'] == 2: w['workspace'] = 12
        (self.state/'current/workspace-layouts.txt').write_text('12 scrolling\n')
        (self.state/'monitor-workspaces').write_text('0\teDP-1\tLaptop\n1\tDP-1\tExternal\n')
        if self.fail == 'reload':
            self.fail = None
            raise ValueError('Fixture partial reload failure')
    def preflight_inverse(self, before, mapping):
        pass
    def inverse(self, before, mapping):
        if self.fail == 'inverse': raise ValueError('Fixture inverse failure')
        self.value = copy.deepcopy(before)


class WorkspaceDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'work'); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.app = App(self.base)
        self.config = self.base/'config'; self.config.mkdir()
        self.original = '-- Fixture geometry preserved\n' + migration.LEGACY_BINDINGS + '\n'
        (self.config/'hyprland.lua').write_text(self.original)
        (self.app.state/'current').mkdir()
        (self.app.state/'current/workspace-layouts.txt').write_text('2 scrolling\n')
        self.release = self.app.root / self.app.selected(); self.release.mkdir(parents=True)
        for name in set(user_install.INCOMING) | set(deploy.ARTIFACTS):
            path = self.release/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text('fixture\n')
        meta = {'schema_version':1,'scope':'omabuntu-user-release-v1','version':'candidate',
                'autostart':False,'lock_activation':False,'files':user_install.file_manifest(self.release)}
        (self.release/'release.json').write_text(json.dumps(meta))
        self.host = Host(self.config,self.app.state)

    def review(self): return deploy.plan(self.app,self.config,host=self.host)
    def apply(self, reviewed=None):
        reviewed = reviewed or self.review()
        return deploy.apply(self.app,reviewed,deploy.digest(reviewed),self.host)

    def journal(self): return next((self.app.state/'workspace-transactions').glob('*/transaction.json'))

    def test_original_chord_set_matches_real_lua_binding_source(self):
        import keybindings_menu
        rows = keybindings_menu.scan_lua_source((ROOT/'config/hypr/monitor-workspace-bindings.lua').read_text())
        self.assertEqual({deploy.binding_chord(row) for row in rows}, deploy.target_chords())
        self.assertEqual(len(rows), len(deploy.target_chords()))

    def test_conflicting_or_stale_runtime_bindings_are_not_overlaid(self):
        reviewed = self.review()
        self.host.binding_rows.append(dict(modmask=64, key='Tab', keycode=0, description='Existing custom binding'))
        self.assertTrue(self.review()['blockers'])
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.apply(reviewed)
        self.assertTrue(self.app.live)
        self.assertFalse(list((self.app.state/'workspace-transactions').glob('*/transaction.json')))
        self.host.binding_rows[-1] = dict(modmask=64, key='', keycode=10, description='Duplicate numeric slot')
        self.assertTrue(self.review()['blockers'])

    def test_state_directory_probe_uses_repl_not_success_only_eval(self):
        with patch.object(deploy.Host, 'command', return_value=str(self.app.state)) as command:
            self.assertEqual(deploy.Host().state_home(), str(self.app.state))
        self.assertEqual(command.call_args.args[0], 'repl')
        self.assertIn('OMABUNTU_STATE_HOME', command.call_args.args[1])

    def test_plan_is_readonly_and_apply_preserves_membership_then_explicit_rollback(self):
        before = self.host.snapshot()
        reviewed = self.review()
        self.assertEqual((self.config/'hyprland.lua').read_text(),self.original)
        self.assertFalse((self.app.state/'workspace-transactions').exists())
        result = self.apply(reviewed)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(self.host.snapshot()['clients'][0]['workspace'],12)
        self.assertEqual((self.app.state/'monitor-workspaces-policy').read_text(),'monitor-local-v1\n')
        self.assertTrue(self.app.live); self.assertFalse(self.host.disabled)
        deploy.recover(self.app,Path(result['journal']),self.host)
        self.assertEqual(self.host.snapshot(),before)
        self.assertEqual((self.config/'hyprland.lua').read_text(),self.original)
        self.assertEqual((self.app.state/'current/workspace-layouts.txt').read_text(),'2 scrolling\n')
        self.assertFalse((self.config/'omabuntu-monitor-workspaces.lua').exists())
        self.assertFalse((self.app.state/'monitor-workspaces-policy').exists())
        self.assertTrue(self.app.live)

    def test_partial_reload_failure_restores_before_state(self):
        before = self.host.snapshot(); self.host.fail='reload'
        with self.assertRaisesRegex(ValueError,'deployment failed'): self.apply()
        self.assertEqual(self.host.snapshot(),before)
        self.assertEqual(user_install.read_json(self.journal())['status'],'restored')
        self.assertTrue(self.app.live)
        self.assertEqual((self.config/'hyprland.lua').read_text(),self.original)

    def test_start_failure_restores_original_configuration_and_restarts(self):
        self.app.fail_start=True
        with self.assertRaisesRegex(ValueError,'deployment failed'): self.apply()
        self.assertEqual(user_install.read_json(self.journal())['status'],'restored')
        self.assertTrue(self.app.live)
        self.assertEqual(self.app.starts,2)

    def test_stale_window_membership_or_config_rejected_before_stop(self):
        reviewed=self.review(); self.host.value['clients'][0]['address']='0xdef'
        with self.assertRaisesRegex(ValueError,'changed'): self.apply(reviewed)
        self.assertTrue(self.app.live)
        self.assertFalse(list((self.app.state/'workspace-transactions').glob('*/transaction.json')))
        self.host.value['clients'][0]['address']='0xabc'
        reviewed=self.review(); (self.config/'hyprland.lua').write_text(self.original+'-- edited\n')
        with self.assertRaisesRegex(ValueError,'changed'): self.apply(reviewed)
        self.assertTrue(self.app.live)

    def test_bad_digest_or_missing_candidate_artifact_never_stops_bar(self):
        reviewed=self.review()
        with self.assertRaisesRegex(ValueError,'approval'): deploy.apply(self.app,reviewed,'bad',self.host)
        self.assertTrue(self.app.live)
        (self.release/deploy.ARTIFACTS[2]).unlink()
        with self.assertRaises(ValueError): self.review()
        self.assertTrue(self.app.live)

    def test_concurrent_edits_refuse_rollback_without_overwriting(self):
        result=self.apply()
        edited=(self.config/'hyprland.lua').read_text()+'-- concurrent user edit\n'
        (self.config/'hyprland.lua').write_text(edited)
        with self.assertRaisesRegex(ValueError,'Concurrent configuration'): deploy.recover(self.app,Path(result['journal']),self.host)
        self.assertEqual((self.config/'hyprland.lua').read_text(),edited)

    def test_failed_inverse_remains_recoverable_and_blocks_next_apply(self):
        self.apply(); self.host.fail='inverse'
        with self.assertRaisesRegex(ValueError,'inverse'): deploy.recover(self.app,self.journal(),self.host)
        self.assertEqual(user_install.read_json(self.journal())['status'],'restoring')
        self.host.fail=None
        deploy.recover(self.app,self.journal(),self.host)
        self.assertEqual(user_install.read_json(self.journal())['status'],'restored')

    def test_layout_changes_are_not_silently_overwritten(self):
        result=self.apply()
        (self.app.state/'current/workspace-layouts.txt').write_text('12 floating\n')
        with self.assertRaisesRegex(ValueError,'layout edits'): deploy.recover(self.app,Path(result['journal']),self.host)
        self.assertEqual((self.app.state/'current/workspace-layouts.txt').read_text(),'12 floating\n')

    def test_original_autoreload_setting_is_restored(self):
        self.host.disabled=True
        result=self.apply()
        self.assertTrue(self.host.disabled)
        deploy.recover(self.app,Path(result['journal']),self.host)
        self.assertTrue(self.host.disabled)


class ExecutableInverseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): persistence.LuaPersistenceTests.setUpClass.__func__(cls)
    def setUp(self): persistence.LuaPersistenceTests.setUp(self)
    execute = persistence.LuaPersistenceTests.execute

    def test_inverse_checks_membership_and_restores_workspace_identity(self):
        before={'clients':[{'address':'0xabc','workspace':2}]}
        mapping={'workspaces':[{'old_id':2,'new_id':12,'monitor':'DP-1'}]}
        script=deploy.inverse_program(before,mapping)
        self.execute(policy_tests.FIXTURE+'''
local moved=spaces[2]; spaces[2]=nil; moved.id=12; spaces[12]=moved
hl.get_workspace_windows=function(id) if id==12 then return windows else return {} end end
'''+script+'''
assert(spaces[2] and not spaces[12])
''')

    def test_inverse_preflight_refuses_a_reused_old_id_without_renumbering(self):
        before={'clients':[{'address':'0xabc','workspace':2}]}
        mapping={'workspaces':[{'old_id':2,'new_id':12,'monitor':'DP-1'}]}
        script=deploy.inverse_program(before,mapping)
        self.execute(policy_tests.FIXTURE+'''
spaces[12]={id=12,monitor=external}
hl.get_workspace_windows=function(_) return windows end
local ok=pcall(function()
'''+script+'''
end)
assert(not ok and spaces[2] and spaces[12])
''')


if __name__ == '__main__': unittest.main()
