"""Execute the generated eval with real Lua and fixture-only compositor calls."""
import ctypes
import ctypes.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import workspace_modes


class LuaPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name = ctypes.util.find_library('lua5.4')
        if not name:
            raise unittest.SkipTest('Executable persistence tests need the system Lua 5.4 library')
        cls.lua = ctypes.CDLL(name)
        cls.lua.luaL_newstate.restype = ctypes.c_void_p
        cls.lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
        cls.lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        cls.lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                     ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
        cls.lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        cls.lua.lua_tolstring.restype = ctypes.c_char_p
        cls.lua.lua_close.argtypes = [ctypes.c_void_p]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / 'omabuntu'
        (self.state / 'current').mkdir(parents=True)
        self.path = self.state / 'current/workspace-layouts.txt'

    def execute(self, script, extra=''):
        prelude = '''
local env = %s
os.getenv = function(key)
  if key == "XDG_STATE_HOME" or key == "HOME" then return env end
  return nil
end
hl = {
  workspace_rule = function(_) end,
  get_windows = function(_) return {} end,
  get_workspace_windows = function(_) return {} end,
}
''' % json.dumps(str(self.state.parent))
        state = self.lua.luaL_newstate()
        try:
            self.lua.luaL_openlibs(state)
            status = self.lua.luaL_loadstring(state, (prelude + extra + '\n' + script).encode())
            if not status:
                status = self.lua.lua_pcallk(state, 0, 0, 0, 0, None)
            if status:
                raise AssertionError(self.lua.lua_tolstring(state, -1, None).decode())
        finally:
            self.lua.lua_close(state)

    def test_all_modes_persist_preserving_other_workspaces_and_default_removes(self):
        self.path.write_text('2 floating\n')
        self.execute(workspace_modes.program(1, 'scrolling'))
        self.assertEqual(self.path.read_text(), '1 scrolling\n2 floating\n')
        self.execute(workspace_modes.program(1, 'floating'))
        self.assertEqual(self.path.read_text(), '1 floating\n2 floating\n')
        self.execute(workspace_modes.program(1, 'dwindle'))
        self.assertEqual(self.path.read_text(), '2 floating\n')
        self.execute(workspace_modes.program(2, 'dwindle'))
        self.assertFalse(self.path.exists())

    def test_save_failure_is_not_reported_as_success(self):
        self.path.parent.rmdir()
        with self.assertRaisesRegex(AssertionError, 'save workspace mode'):
            self.execute(workspace_modes.program(1, 'scrolling'))

    def test_atomic_replace_failure_preserves_saved_modes(self):
        self.path.write_text('2 floating\n')
        with self.assertRaisesRegex(AssertionError, 'save workspace mode'):
            self.execute(workspace_modes.program(1, 'scrolling'),
                         'os.rename = function() return nil, "fixture refusal" end')
        self.assertEqual(self.path.read_text(), '2 floating\n')

    def test_a_new_config_load_restores_saved_scrolling_rules(self):
        self.execute(workspace_modes.program(3, 'scrolling'))
        managed = (ROOT / 'config/hypr/omabuntu-managed.lua').read_text()
        self.execute(managed + '\nassert(restored == "3:scrolling")', '''
restored = nil
hl.config = function(_) end
hl.workspace_rule = function(rule) restored = rule.workspace .. ":" .. rule.layout end
''')

    def test_claim_program_compiles_and_ignores_a_vanished_window(self):
        self.execute(workspace_modes.claim_program('0x123', 1),
                     'hl.get_window = function(_) return nil end')

    def test_membership_is_independent_of_floating_ownership(self):
        for floating, fullscreen, pinned in [(True, 0, False), (False, 0, False),
                                             (False, 2, False), (True, 0, True),
                                             (False, 0, True)]:
            with self.subTest(floating=floating, fullscreen=fullscreen, pinned=pinned):
                eligible = not floating and fullscreen == 0
                extra = '''
local tags = {}
local floats = 0
local refreshed = 0
local window = {address="0xabc", workspace={id=4}, floating=%s,
                fullscreen=%d, pinned=%s}
hl = {
  get_window = function(_) return window end,
  dispatch = function(_) end,
  plugin = {hyprbars={}}, config = function(_) end,
  window_rule = function(_) refreshed = refreshed + 1 end,
  dsp = {window = {
    tag = function(spec) tags[spec.tag] = true; return spec end,
    float = function(spec) floats = floats + 1; return spec end,
  }},
}
''' % (str(floating).lower(), fullscreen, str(pinned).lower())
                self.execute('(function()\n' + workspace_modes.claim_program('0xabc', 4) + '\nend)()\n' + '''
assert(tags["+omabuntu-floating-workspace"], "missing workspace membership")
assert((tags["+omabuntu-mode-floated"] == true) == %s, "wrong ownership")
assert(floats == %d, "unexpected floating change")
assert(refreshed == 2, "membership must refresh titlebars even without placement")
''' % (str(eligible).lower(), int(eligible)), extra)

    def test_restore_after_maximized_or_fullscreen_claims_and_places_only_once(self):
        claim = workspace_modes.claim_program('0xabc', 4, 2)
        for mode in (1, 2):
            with self.subTest(mode=mode):
                extra = '''
local window = {address="0xabc",workspace={id=4},floating=false,fullscreen=%d,
                monitor={width=1600,height=1000,scale=1}}
local tags, floats, placements = {}, 0, 0
hl = {
  get_window=function(_) return window end,
  dispatch=function(_) end,
  dsp={window={
    tag=function(s) tags[s.tag]=true; return s end,
    float=function(s)
      assert(s.action == "on")
      window.floating=true; floats=floats+1; return s
    end,
    resize=function(s)
      assert(s.x == 1024 and s.y == 680 and s.relative == false)
      placements=placements+1; return s
    end,
    center=function(s) placements=placements+1; return s end,
    move=function(s)
      assert(s.x == 0 and s.y == 0 and s.relative == true)
      placements=placements+1; return s
    end,
  }},
}
''' % mode
                self.execute('local function arrange()\n' + claim + '''
end
arrange()
assert(floats == 0 and placements == 0, "must preserve maximized/fullscreen")
assert(tags["+omabuntu-floating-workspace"])
assert(not tags["+omabuntu-mode-floated"])
window.fullscreen = 0
arrange()
assert(floats == 1 and placements == 3 and window.floating, "restore must float and place")
assert(tags["+omabuntu-mode-floated"])
arrange()
assert(floats == 1 and placements == 3, "later events must preserve floating geometry")
''', extra)

    def test_drag_drop_retile_is_corrected_without_resizing_preexisting_float(self):
        claim = workspace_modes.claim_program('0xabc', 4, 2)
        extra = '''
local window = {address="0xabc",workspace={id=4},floating=true,fullscreen=0,
                monitor={width=1600,height=1000,scale=1}}
local tags, floats, placements = {}, 0, 0
hl = {
  get_window=function(_) return window end,
  dispatch=function(_) end,
  dsp={window={
    tag=function(s) tags[s.tag]=true; return s end,
    float=function(s)
      assert(s.action == "on")
      window.floating=true; floats=floats+1; return s
    end,
    resize=function(s)
      assert(s.x == 1024 and s.y == 680)
      placements=placements+1; return s
    end,
    center=function(s) placements=placements+1; return s end,
    move=function(s) placements=placements+1; return s end,
  }},
}
'''
        self.execute('local function arrange()\n' + claim + '''
end
-- Move-time claim: the native tiled drag is temporarily floating.
arrange()
assert(floats == 0 and placements == 0, "must preserve current floating geometry")
assert(tags["+omabuntu-floating-workspace"] and not tags["+omabuntu-mode-floated"])
-- Drop emits floating-off; the deferred correction uses the same live-state claim.
window.floating = false
arrange()
assert(window.floating and floats == 1 and placements == 3)
assert(tags["+omabuntu-mode-floated"])
arrange()
assert(floats == 1 and placements == 3, "duplicate claims must not replace geometry")
-- No event snapshot may force a now-maximized window back out of maximization.
window.floating = false
window.fullscreen = 1
arrange()
assert(floats == 1 and placements == 3 and window.fullscreen == 1)
-- A stale addressed candidate must not affect its new destination.
window.fullscreen = 0
window.workspace.id = 5
arrange()
assert(floats == 1 and placements == 3)
''', extra)

    def test_workspace_toggle_marks_all_members_but_tiles_only_owned_unpinned(self):
        extra = '''
local windows = {
  {address="0xa",floating=false,fullscreen=0},
  {address="0xb",floating=true,fullscreen=0},
  {address="0xc",floating=false,fullscreen=2},
  {address="0xd",floating=true,fullscreen=0,pinned=true},
}
local tags, floats, refreshed = {}, {}, 0
hl = {
  get_workspace_windows = function(_) return windows end,
  get_windows = function(_) return {windows[1], windows[4]} end,
  workspace_rule = function(_) end,
  plugin = {hyprbars={}}, config = function(_) end,
  window_rule = function(_) refreshed = refreshed + 1 end,
  dispatch = function(_) end,
  dsp = {window = {
    tag = function(s)
      tags[s.window.address .. s.tag] = true
      return s
    end,
    float = function(s) floats[s.window.address] = s.action; return s end,
  }},
}
'''
        self.execute(workspace_modes.program(4, 'floating') + '''
for _, w in ipairs(windows) do
  assert(tags[w.address .. "+omabuntu-floating-workspace"], "member omitted")
end
assert(floats["0xa"] == "on")
assert(not floats["0xb"] and not floats["0xc"] and not floats["0xd"])
assert(tags["0xa+omabuntu-mode-floated"])
assert(not tags["0xb+omabuntu-mode-floated"])
assert(refreshed == 2)
''', extra)
        self.execute(workspace_modes.program(4, 'dwindle') + '''
for _, w in ipairs(windows) do
  assert(tags[w.address .. "-omabuntu-floating-workspace"], "membership retained")
end
assert(floats["0xa"] == "off")
assert(not floats["0xb"] and not floats["0xc"] and not floats["0xd"])
assert(tags["0xa-omabuntu-mode-floated"])
assert(not tags["0xd-omabuntu-mode-floated"], "pinned ownership lost")
assert(refreshed == 2)
''', extra)

    def test_unowned_release_still_refreshes_titlebars(self):
        self.execute('(function()\n' + workspace_modes.release_program('0xabc', 4) + '\nend)()\nassert(refreshed == 2)', '''
refreshed = 0
hl.get_window = function(_) return {workspace={id=4}, tags={}} end
hl.dispatch = function(_) end
hl.dsp = {window={tag=function(s)
  assert(s.tag == "-omabuntu-floating-workspace")
  return s
end, float=function(_) error("must not tile unowned window") end}}
hl.plugin = {hyprbars={}}
hl.config = function(_) end
hl.window_rule = function(_) refreshed = refreshed + 1 end
''')

    def test_membership_rejects_stale_destination(self):
        self.execute(workspace_modes.claim_program('0xabc', 4), '''
hl.get_window = function(_) return {workspace={id=5},floating=true} end
hl.dispatch = function(_) error("stale move must not change tags") end
''')

    def test_release_tiles_only_windows_the_mode_floated(self):
        log = self.state.parent / 'release-calls.txt'

        def run(body, address='0xabc'):
            extra = '''
calls = assert(io.open(%s, "w"))
window = {
  address = "0xabc",
  workspace = { id = 4 },
  pinned = false,
  tags = { "omabuntu-mode-floated" },
}
hl = {
  get_window = function(selector)
    if selector == "address:0xabc" then return window end
    return nil
  end,
  get_windows = function(filter)
    if filter and filter.tag == "omabuntu-mode-floated" and window.listed then
      return { window }
    end
    return {}
  end,
  dispatch = function(_) end,
  dsp = { window = {
    float = function(spec)
      calls:write("float " .. tostring(spec.action) .. "\\n")
      calls:flush()
      return spec
    end,
    tag = function(spec)
      calls:write("tag " .. tostring(spec.tag) .. "\\n")
      calls:flush()
      return spec
    end,
  } },
}
window.listed = true
%s
''' % (json.dumps(str(log)), body)
            self.execute(workspace_modes.release_program(address, 4) + '\ncalls:close()\n', extra)
            text = log.read_text() if log.exists() else ''
            log.unlink(missing_ok=True)
            return text

        membership = 'tag -omabuntu-floating-workspace\n'
        tiled = membership + 'tag -omabuntu-mode-floated\nfloat off\n'
        self.assertEqual(run(''), tiled)
        self.assertEqual(run('window.listed = false\nwindow.tags = { "omabuntu-mode-floated*" }'), tiled)
        self.assertEqual(run('window.listed = false\nwindow.tags = "omabuntu-mode-floated"'), tiled)
        self.assertEqual(run('window.pinned = true'), membership)
        self.assertEqual(run('window.workspace.id = 2'), '')
        self.assertEqual(run('window.listed = false\nwindow.tags = {}'), membership)
        self.assertEqual(run('', address='0xdef'), '')
