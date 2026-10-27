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

        tiled = 'tag -omabuntu-mode-floated\nfloat off\n'
        self.assertEqual(run(''), tiled)
        self.assertEqual(run('window.listed = false\nwindow.tags = { "omabuntu-mode-floated*" }'), tiled)
        self.assertEqual(run('window.listed = false\nwindow.tags = "omabuntu-mode-floated"'), tiled)
        self.assertEqual(run('window.pinned = true'), '')
        self.assertEqual(run('window.workspace.id = 2'), '')
        self.assertEqual(run('window.listed = false\nwindow.tags = {}'), '')
        self.assertEqual(run('', address='0xdef'), '')
