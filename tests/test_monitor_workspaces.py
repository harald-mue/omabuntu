"""Original monitor policy executed with real Lua and fixture-only compositor IO."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import monitor_workspaces
import workspace_migration
import test_workspace_persistence as persistence

FIXTURE = r'''
local events, calls, spaces, tags = {}, {}, {}, {}
local laptop = {id=0, name="eDP-1", description="Fixture Laptop", focused=false}
local external = {id=1, name="DP-1", description="Fixture External", focused=true}
local monitors, active = {laptop, external}, external
local function add(id, monitor, count)
  local w = {id=id, name=tostring(id), monitor=monitor, windows=count or 0}
  spaces[id] = w
  return w
end
laptop.active_workspace = add(1,laptop,0)
external.active_workspace = add(2,external,1)
local windows = {{address="0xabc",workspace=spaces[2],tags={"omabuntu-minimized-from-2"}}}
local function action(kind)
  return function(args) return {kind=kind,args=args} end
end
hl = {
  dsp={focus=action("focus"),workspace={change_id=action("renumber"),move=action("move_workspace")},
    window={move=action("move_window"),tag=action("tag")}},
  on=function(name, fn) events[name]=fn end,
  timer=function(fn, _) fn() end,
  get_monitors=function() return monitors end,
  get_active_monitor=function() return active end,
  get_monitor=function(name)
    if name == "r" then return external end
    if name == "l" then return laptop end
    for _, m in ipairs(monitors) do if m.name==name then return m end end
  end,
  get_workspace=function(id) return spaces[tonumber(id)] end,
  get_workspaces=function()
    local result={} for _, w in pairs(spaces) do result[#result+1]=w end
    return result
  end,
  get_active_workspace=function() return active.active_workspace end,
  get_active_window=function() return windows[1] end,
  get_window=function(_) return windows[1] end,
  get_windows=function() return windows end,
  workspace_rule=function(rule) calls[#calls+1]={kind="rule",args=rule} end,
}
for _, m in ipairs(monitors) do
  function m:set_workspace(args) self.active_workspace=spaces[tonumber(args.workspace)] end
end
hl.dispatch=function(a)
  calls[#calls+1]=a
  local arg=a.args
  if a.kind=="focus" then
    if arg.monitor then
      laptop.focused=false external.focused=false
      active=hl.get_monitor(arg.monitor) active.focused=true
    elseif arg.workspace then
      local id=tonumber(arg.workspace)
      if id then
        local w=spaces[id] or add(id,active,0)
        active=w.monitor active.active_workspace=w
      end
    end
  elseif a.kind=="renumber" then
    local old=tonumber(arg.workspace)
    assert(spaces[old] and not spaces[arg.id])
    local w=spaces[old] spaces[old]=nil
    w.id=arg.id w.name=tostring(arg.id) spaces[arg.id]=w
  elseif a.kind=="move_workspace" then
    local w=spaces[tonumber(arg.workspace)] or active.active_workspace
    w.monitor=hl.get_monitor(arg.monitor)
  elseif a.kind=="tag" then
    tags[#tags+1]=arg.tag
  end
end
'''


class MonitorPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        persistence.LuaPersistenceTests.setUpClass.__func__(cls)

    def setUp(self):
        persistence.LuaPersistenceTests.setUp(self)

    execute = persistence.LuaPersistenceTests.execute

    def run_policy(self, script='', before=''):
        source = monitor_workspaces.artifacts()['config/hypr/monitor-workspaces.lua'].decode()
        self.execute(FIXTURE + before + '\nlocal policy=(function()\n' + source + '\nend)()\n' + script)

    def test_original_policy_mirrors_and_provenance(self):
        monitor_workspaces.verify()
        source = (ROOT / monitor_workspaces.POLICY).read_text()
        generated = monitor_workspaces.artifacts()['config/hypr/monitor-workspaces.lua'].decode()
        for section in ('local function identities_of', 'function M.focus', 'function M.reconcile',
                        'hl.on("monitor.removed"', 'local function restore()', 'local function merge()'):
            self.assertIn(section, source)
            self.assertIn(section, generated)
        self.assertNotIn('require("default.hypr.paths")', generated)
        self.assertIn('omabuntu_workspaces = M', generated)

    def test_focus_and_window_move_are_local_and_silent_move_stays_silent(self):
        self.run_policy('''
policy.focus(3)()
assert(active==external and external.active_workspace.id==13)
policy.move_window(4,false)()
local a=calls[#calls]
assert(a.kind=="move_window" and a.args.workspace=="14" and a.args.follow==false)
policy.focus(3,"eDP-1")()
assert(active==laptop and laptop.active_workspace.id==3)
''')

    def test_initial_adoption_preserves_monitor_layout_and_minimized_tags(self):
        self.path.write_text('2 floating\n')
        self.run_policy('''
policy.reconcile()
assert(spaces[12] and spaces[12].monitor==external and not spaces[2])
assert(tags[1]=="-omabuntu-minimized-from-2")
assert(tags[2]=="+omabuntu-minimized-from-12")
assert(external.active_workspace.id==12)
''')
        self.assertEqual(self.path.read_text(), '12 floating\n')

    def test_scrolling_layout_moves_and_old_rule_is_cleared(self):
        self.path.write_text('2 scrolling\n')
        self.run_policy('''
policy.reconcile()
local old,new=false,false
for _, a in ipairs(calls) do
  if a.kind=="rule" and a.args.workspace=="2" then old=a.args.layout=="dwindle" end
  if a.kind=="rule" and a.args.workspace=="12" then new=a.args.layout=="scrolling" end
end
assert(old and new)
''')
        self.assertEqual(self.path.read_text(), '12 scrolling\n')

    def test_saved_destination_collision_blocks_before_renumber(self):
        self.path.write_text('2 floating\n12 scrolling\n')
        self.run_policy('''
local ok,err=pcall(policy.reconcile)
assert(not ok and tostring(err):find("Destination has a saved layout",1,true))
assert(spaces[2] and not spaces[12])
''')
        self.assertEqual(self.path.read_text(), '2 floating\n12 scrolling\n')

    def test_write_failure_does_not_renumber(self):
        self.path.parent.rmdir()
        self.run_policy('''
local ok=pcall(policy.reconcile)
assert(not ok and spaces[2] and not spaces[12])
''')

    def test_failed_dispatch_restores_saved_modes(self):
        self.path.write_text('2 floating\n')
        self.run_policy('''
local dispatch=hl.dispatch
hl.dispatch=function(a) if a.kind=="renumber" then error("fixture failure") end return dispatch(a) end
local ok=pcall(policy.reconcile)
assert(not ok and spaces[2] and not spaces[12])
''')
        self.assertEqual(self.path.read_text(), '2 floating\n')

    def test_monitor_identity_survives_connector_change(self):
        self.run_policy('''
assert(policy.workspace_id(external,1)==11)
external.name="DP-9"
assert(policy.workspace_id(external,1)==11)
''')
        assignments = (self.state / 'monitor-workspaces').read_text()
        self.assertIn('1\tDP-9\tFixture External', assignments)

    def test_unplug_merge_and_replug_restore_layout_and_membership(self):
        self.path.write_text('2 scrolling\n')
        self.run_policy('''
policy.reconcile()
assert(spaces[12])
-- Model the compositor's native evacuation before the original removal hook.
monitors={laptop} active=laptop
spaces[12].monitor=laptop laptop.active_workspace=spaces[12]
policy.reconcile(nil,"DP-1")
assert(not spaces[12] and spaces[2] and spaces[2].monitor==laptop)
monitors={laptop,external}
policy.reconcile("DP-1")
assert(spaces[12] and spaces[12].monitor==external and not spaces[2])
''')
        self.assertEqual(self.path.read_text(), '12 scrolling\n')

    def test_all_ten_slots_and_directional_bindings_execute_original_factories(self):
        bindings = (ROOT / 'config/hypr/monitor-workspace-bindings.lua').read_text()
        self.run_policy('''
local bound, count = {}, 0
hl.bind=function(key,action,options) bound[key]=action count=count+1 end
''' + bindings + '''
assert(count==45)
bound["SUPER + code:10"]()
assert(active==external and external.active_workspace.id==11)
bound["SUPER + code:19"]()
assert(external.active_workspace.id==20)
bound["SUPER + SHIFT + ALT + code:11"]()
local a=calls[#calls]
assert(a.kind=="move_window" and a.args.workspace=="12" and a.args.follow==false)
bound["SUPER + SHIFT + CTRL + LEFT"]()
a=calls[#calls]
assert(a.kind=="move_window" and a.args.monitor=="eDP-1")
''')

    def test_full_block_keeps_evacuated_workspace_as_guest(self):
        self.run_policy('''
assert(policy.workspace_id(external,1)==11)
spaces[2]=nil
external.active_workspace=add(12,external,1)
windows[1].workspace=spaces[12]
for id=1,10 do if not spaces[id] then add(id,laptop,1) end end
monitors={laptop} active=laptop
spaces[12].monitor=laptop laptop.active_workspace=spaces[12]
policy.reconcile(nil,"DP-1")
assert(spaces[12] and spaces[12].monitor==laptop)
''')

    def test_invalid_duplicate_saved_state_blocks_before_changes(self):
        self.path.write_text('2 floating\n2 scrolling\n')
        self.run_policy('''
local ok=pcall(policy.reconcile)
assert(not ok and spaces[2] and not spaces[12])
''')
        self.assertEqual(self.path.read_text(), '2 floating\n2 scrolling\n')

    def test_original_widget_layout_and_guest_presentation_retained(self):
        original = (ROOT / monitor_workspaces.WIDGET).read_text()
        derived = monitor_workspaces.artifacts()['config/shell/preview/MonitorWorkspaces.qml'].decode()
        self.assertEqual(original[original.index('  GridLayout {'):], derived[derived.index('  GridLayout {'):])
        self.assertIn('var ids = [base + 1, base + 2, base + 3, base + 4, base + 5]', derived)
        self.assertIn('root.monitor.activeWorkspace.id', derived)
        self.assertIn('root.block * root.slots', derived)
        self.assertNotIn('ShellIpc', derived)
        self.assertNotIn('omarchy-hyprland', derived)
        self.assertIn('layoutBackend.apply(', derived)


class MigrationPreviewTests(unittest.TestCase):
    def setUp(self):
        self.monitors = [dict(id=0,name='eDP-1',description='Laptop'),
                         dict(id=1,name='DP-1',description='External'),
                         dict(id=2,name='DP-2',description='Other')]
        self.spaces = [dict(id=1,monitor='eDP-1',windows=0),
                       dict(id=2,monitor='DP-1',windows=2),dict(id=5,monitor='DP-2',windows=1)]

    def test_preserves_output_slot_and_layout(self):
        result = workspace_migration.preview(self.monitors,self.spaces,'2 scrolling\n5 floating\n')
        self.assertFalse(result['blockers'])
        self.assertEqual({x['old_id']:x['new_id'] for x in result['workspaces']},{1:1,2:12,5:25})
        self.assertEqual(result['layouts_after'],'12 scrolling\n25 floating\n')

    def test_saved_or_live_destination_collisions_are_blocked(self):
        result = workspace_migration.preview(self.monitors,self.spaces,'12 floating\n')
        self.assertEqual(result['status'],'blocked')
        self.assertTrue(result['blockers'])
        self.spaces.append(dict(id=12,monitor='DP-2',windows=1))
        self.assertTrue(workspace_migration.preview(self.monitors,self.spaces)['blockers'])

    def test_orphaned_saved_mode_requires_attribution(self):
        self.assertTrue(workspace_migration.preview(self.monitors,self.spaces,'7 floating\n')['blockers'])

    def test_remembered_identity_not_connector_is_authoritative(self):
        assignments='0\teDP-1\tLaptop\n3\tDP-old\tExternal\n'
        result=workspace_migration.preview(self.monitors,self.spaces,assignments=assignments)
        self.assertEqual(result['workspaces'][1]['new_id'],32)

    def test_configuration_patch_changes_only_reviewed_global_loop(self):
        before = '-- Fixture private geometry\nhl.monitor({output="fixture"})\n' + workspace_migration.LEGACY_BINDINGS + '\n-- Fixture lock and application binds\n'
        after = workspace_migration.configuration_patch(before)
        self.assertEqual(before.split(workspace_migration.LEGACY_BINDINGS)[0], after.split('-- Original monitor-local')[0])
        self.assertTrue(after.endswith('\n-- Fixture lock and application binds\n'))
        self.assertIn('require("omabuntu-monitor-workspaces")', after)
        self.assertNotIn('workspace = i', after)
        for text in (before + workspace_migration.LEGACY_BINDINGS, before.replace('i % 10', 'i'), after):
            with self.assertRaises(ValueError): workspace_migration.configuration_patch(text)

    def test_invalid_layouts_or_assignments_rejected(self):
        for text in ('0 floating\n','1 invalid\n','1 floating\n1 scrolling\n'):
            with self.assertRaises(ValueError): workspace_migration.parse_layouts(text)
        with self.assertRaises(ValueError): workspace_migration.parse_blocks('0\ta\tA\n0\tb\tB\n')

    def test_snapshot_changes_with_membership(self):
        first=workspace_migration.preview(self.monitors,self.spaces)['snapshot_sha256']
        self.spaces[1]['windows']+=1
        self.assertNotEqual(first,workspace_migration.preview(self.monitors,self.spaces)['snapshot_sha256'])

    def test_inspection_queries_only_readonly_endpoints_and_discards_titles(self):
        with patch.object(workspace_migration,'query',side_effect=[self.monitors,[dict(self.spaces[0],lastwindowtitle='PRIVATE')]]) as query, \
                patch.object(workspace_migration,'bounded_text',return_value=''):
            result=workspace_migration.inspect(Path('/fixture'))
        self.assertEqual([c.args[0] for c in query.call_args_list],['monitors','workspaces'])
        self.assertNotIn('PRIVATE',json.dumps(result))


if __name__ == '__main__':
    unittest.main()
