"""Plan 018 installer-managed Hyprland settings checks."""
import ctypes
import ctypes.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
DEPLOY = ROOT / 'tools' / 'deploy_hypr_settings.py'
TEMPLATE = ROOT / 'config' / 'hypr' / 'omabuntu-managed.lua'

BASE_CONFIG = '''-- user configuration
hl.config({ general = { gaps_in = 2 } })

hl.bind("SUPER + RETURN", hl.dsp.exec_cmd("ghostty"))
'''


def run_tool(args, *, expect=0, home=None):
    command = [sys.executable, str(DEPLOY)]
    if home is not None:
        command += ['--home', str(home)]
    command += list(args)
    result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    if result.returncode != expect:
        raise AssertionError(f'exit {result.returncode} (want {expect}): {result.stdout}{result.stderr}')
    return result


class ManagedTemplateTests(unittest.TestCase):
    def setUp(self):
        self.text = TEMPLATE.read_text()

    def test_contains_only_reviewed_settings(self):
        self.assertIn('disable_splash_rendering = true', self.text)
        self.assertIn('disable_hyprland_logo = true', self.text)
        self.assertIn('col = { splash = 0x00000000 }', self.text)
        self.assertIn('no_donation_nag = true', self.text)
        self.assertIn('no_update_news = true', self.text)
        self.assertIn('render = { cm_auto_hdr = 0 }', self.text)

    def test_evaluation_profile_disables_automatic_hdr(self):
        text = (ROOT / 'config/hypr/minimal.lua').read_text()
        self.assertIn('render = { cm_auto_hdr = 0 }', text)

    def test_dofiles_only_the_granted_activation_file(self):
        # Plan 073: a config-time hl.plugin.load registration is discarded
        # before the compositor creates its plugin system, so the snippet has
        # no plugin route of its own. The persistent login load belongs to
        # the separately granted activation file; only this guarded dofile.
        self.assertIn('dofile(activation)', self.text)
        self.assertIn('"/hypr/omabuntu-activation.lua"', self.text)
        self.assertIn('local granted = io.open(activation, "r")', self.text)
        self.assertEqual(self.text.count('dofile'), 1)
        code = '\n'.join(line for line in self.text.splitlines()
                         if not line.lstrip().startswith('--'))
        self.assertNotIn('hl.plugin.load', code)
        self.assertNotIn('hyprbars.so', code)

    def test_restores_saved_workspace_layouts(self):
        self.assertIn('workspace-layouts.txt', self.text)
        self.assertIn('mode == "scrolling"', self.text)
        self.assertIn('hl.workspace_rule({ workspace = id, layout = "scrolling" })', self.text)
        self.assertEqual(self.text.count('hl.workspace_rule'), 1)

    def test_contains_no_desktop_behaviour(self):
        code = '\n'.join(line for line in self.text.splitlines()
                         if not line.lstrip().startswith('--'))
        self.assertNotIn('hl.bind(', code)
        self.assertNotIn('hl.on(', code)
        self.assertNotIn('hl.monitor(', code)
        self.assertNotIn('exec', code)
        self.assertNotIn('os.execute', code)


class DeployToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.hypr = self.home / '.config/hypr'
        self.hypr.mkdir(parents=True)
        self.config = self.hypr / 'hyprland.lua'
        self.config.write_text(BASE_CONFIG)

    def tearDown(self):
        self.temp.cleanup()

    def managed_lines(self):
        return [line for line in self.config.read_text().splitlines()
                if 'omabuntu-managed' in line]

    def test_plan_is_read_only(self):
        before = self.config.read_text()
        result = run_tool(['plan'], home=self.home)
        self.assertIn('require("omabuntu-managed")', result.stdout)
        self.assertEqual(before, self.config.read_text())
        self.assertFalse((self.hypr / 'omabuntu-managed.lua').exists())

    def test_apply_writes_snippet_and_one_include(self):
        run_tool(['apply'], home=self.home)
        managed = self.hypr / 'omabuntu-managed.lua'
        self.assertEqual(managed.read_text(), TEMPLATE.read_text())
        self.assertEqual(self.managed_lines(), ['require("omabuntu-managed")'])
        self.assertTrue(self.config.read_text().startswith(BASE_CONFIG))

    def test_apply_is_idempotent_and_keeps_a_single_include(self):
        run_tool(['apply'], home=self.home)
        first = self.config.read_text()
        run_tool(['apply'], home=self.home)
        self.assertEqual(first, self.config.read_text())
        self.assertEqual(self.managed_lines(), ['require("omabuntu-managed")'])
        self.assertEqual(len(list(self.hypr.glob('hyprland.lua.bak-*'))), 1)

    def test_apply_backs_up_a_changed_snippet(self):
        run_tool(['apply'], home=self.home)
        managed = self.hypr / 'omabuntu-managed.lua'
        managed.write_text('-- local edit\n')
        run_tool(['apply'], home=self.home)
        self.assertEqual(managed.read_text(), TEMPLATE.read_text())
        backups = list(self.hypr.glob('omabuntu-managed.lua.bak-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), '-- local edit\n')

    def test_refuses_a_different_reference(self):
        self.config.write_text(BASE_CONFIG + 'dofile("omabuntu-managed.lua")\n')
        before = self.config.read_text()
        result = run_tool(['apply'], expect=2, home=self.home)
        self.assertIn('different omabuntu-managed reference', result.stderr)
        self.assertEqual(before, self.config.read_text())

    def test_refuses_a_duplicate_include(self):
        line = 'require("omabuntu-managed")\n'
        self.config.write_text(BASE_CONFIG + line + line)
        run_tool(['apply'], expect=2, home=self.home)

    def test_remove_restores_the_original_configuration(self):
        run_tool(['apply'], home=self.home)
        run_tool(['remove'], home=self.home)
        self.assertEqual(self.config.read_text(), BASE_CONFIG)
        self.assertFalse((self.hypr / 'omabuntu-managed.lua').exists())

    def test_remove_preserves_existing_trailing_blank_lines(self):
        original = BASE_CONFIG + '\n\n'
        self.config.write_text(original)
        run_tool(['apply'], home=self.home)
        run_tool(['remove'], home=self.home)
        self.assertEqual(self.config.read_text(), original)

    def test_dry_run_writes_nothing(self):
        result = run_tool(['apply', '--dry-run'], home=self.home)
        self.assertIn('Dry run', result.stdout)
        self.assertEqual(self.config.read_text(), BASE_CONFIG)
        self.assertFalse((self.hypr / 'omabuntu-managed.lua').exists())

    def test_refusal_does_not_write_the_managed_file(self):
        self.config.write_text(BASE_CONFIG + 'dofile("omabuntu-managed.lua")\n')
        run_tool(['apply'], expect=2, home=self.home)
        self.assertFalse((self.hypr / 'omabuntu-managed.lua').exists())

    def test_symlinked_parent_is_refused_without_writes(self):
        real = self.home / 'real-hypr'
        self.hypr.rename(real)
        self.hypr.symlink_to(real, target_is_directory=True)
        run_tool(['apply'], expect=2, home=self.home)
        self.assertFalse((real / 'omabuntu-managed.lua').exists())
        self.assertEqual((real / 'hyprland.lua').read_text(), BASE_CONFIG)

    def test_remove_backs_up_snippet(self):
        run_tool(['apply'], home=self.home)
        run_tool(['remove'], home=self.home)
        backups = list(self.hypr.glob('omabuntu-managed.lua.bak-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), TEMPLATE.read_text())

    def test_plan_prints_a_unified_diff(self):
        result = run_tool(['plan'], home=self.home)
        self.assertIn('@@', result.stdout)
        self.assertIn('+require("omabuntu-managed")', result.stdout)

    def test_missing_configuration_is_an_error(self):
        self.config.unlink()
        run_tool(['apply'], expect=2, home=self.home)


class ManagedSnippetLuaTests(unittest.TestCase):
    """Execute the managed snippet with a mock compositor API (plan 073)."""

    @classmethod
    def setUpClass(cls):
        name = ctypes.util.find_library('lua5.4')
        if not name:
            raise unittest.SkipTest('Snippet execution needs the Lua 5.4 library')
        cls.lua = ctypes.CDLL(name)
        cls.lua.luaL_newstate.restype = ctypes.c_void_p
        cls.lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
        cls.lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        cls.lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
        cls.lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        cls.lua.lua_tolstring.restype = ctypes.c_char_p
        cls.lua.lua_close.argtypes = [ctypes.c_void_p]

    def run_lua(self, script):
        state = self.lua.luaL_newstate()
        try:
            self.lua.luaL_openlibs(state)
            result = self.lua.luaL_loadstring(state, script.encode())
            if result == 0:
                result = self.lua.lua_pcallk(state, 0, 0, 0, 0, None)
            if result:
                message = self.lua.lua_tolstring(state, -1, None)
                self.fail(message.decode() if message else 'Lua execution failed')
        finally:
            self.lua.lua_close(state)

    def test_missing_activation_and_layouts_load_nothing(self):
        self.run_lua(
            'configured = {}\n'
            'hl = {config = function(t) configured[#configured + 1] = t end,\n'
            '       workspace_rule = function(t) error("no saved layout") end}\n'
            'io.open = function(path, mode) assert(mode == "r"); return nil end\n'
            'dofile = function(path) error("nothing may load") end\n'
            + TEMPLATE.read_text()
            + '\nassert(#configured == 1)\n'
            'assert(configured[1].misc.disable_splash_rendering == true)\n'
            'assert(configured[1].ecosystem.no_donation_nag == true)\n'
            'assert(configured[1].ecosystem.no_update_news == true)\n'
            'assert(configured[1].render.cm_auto_hdr == 0)\n')

    def test_present_activation_is_dofiled_exactly_once(self):
        self.run_lua(
            'dofiles = {}\n'
            'local function handle() return {close = function() end} end\n'
            'hl = {config = function() end, workspace_rule = function() end}\n'
            'io.open = function(path, mode)\n'
            '  assert(mode == "r")\n'
            '  if path:find("omabuntu-activation.lua", 1, true) then return handle() end\n'
            '  return nil\n'
            'end\n'
            'dofile = function(path) dofiles[#dofiles + 1] = path end\n'
            + TEMPLATE.read_text()
            + '\nassert(#dofiles == 1)\n'
            'assert(dofiles[1]:find("/hypr/omabuntu-activation.lua", 1, true))\n')


if __name__ == '__main__':
    unittest.main()
