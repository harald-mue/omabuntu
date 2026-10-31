"""Generic-session contracts in fixture homes; no real compositor actions."""
import ctypes
import ctypes.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import session_config as session
import user_install

NATIVE = {'version': '0.56.2', 'commit': session.build_hyprbars.HYPRLAND_COMMIT,
          'dirty': False, 'abiHash': 'fixture'}


class SessionConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / 'home'
        self.home.mkdir()
        p = patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.base / 'config'),
                                    'XDG_DATA_HOME': str(self.base / 'data'),
                                    'XDG_STATE_HOME': str(self.base / 'state')})
        p.start()
        self.addCleanup(p.stop)
        for obj, name, value in [(session.bootstrap_sources, 'host_check', None),
                                 (session.build_hyprbars, 'installed_version', NATIVE),
                                 (session, 'layouts', {'us', 'de', 'gb'})]:
            p = patch.object(obj, name, return_value=value)
            p.start()
            self.addCleanup(p.stop)
        _, self.app, self.paths = session.locations(self.home)
        bundle = self.base / 'bundle'
        bundle.mkdir()
        for name in set(user_install.INCOMING + user_install.SESSION_HELPERS + user_install.SESSION_LOCK_HELPERS):
            path = bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture ' + name)
            path.chmod(0o755 if name.startswith('runtime/bin/') else 0o444)
        meta = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': 'test',
                'autostart': False, 'lock_activation': False, 'files': user_install.file_manifest(bundle)}
        (bundle / 'release.json').write_text(json.dumps(meta))
        self.app.install(bundle)

    def plan(self, **kwargs):
        return session.plan(ROOT, self.home, **kwargs)

    def apply(self, plan):
        return session.apply(plan, session.guided.digest(plan), check_stopped=lambda: None)

    def test_plan_is_read_only_and_has_no_private_monitor_rules(self):
        plan = self.plan()
        self.assertFalse(plan['blockers'])
        self.assertFalse(self.paths['entry'].parent.exists())
        self.assertFalse((self.app.state / 'session-transactions').exists())
        text = plan['payload']['module']
        self.assertNotIn('DP-7', text)
        self.assertNotIn('desc:', text)
        self.assertNotIn('hl.plugin.load', text)
        self.assertNotIn('hl.on(', text)
        self.assertIn('scale = 1', text)
        self.assertIn('xdg-terminal-exec', text)
        self.assertIn('PYTHONDONTWRITEBYTECODE=1', text)
        self.assertIn('omabuntu:menu', text)
        self.assertNotIn('SUPER + CTRL + L', text)

    def test_fresh_apply_records_before_state_and_does_not_activate(self):
        plan = self.plan(keyboard='de,us')
        with patch.object(session.subprocess, 'run') as run:
            result = self.apply(plan)
        run.assert_not_called()
        self.assertEqual(result['status'], 'configured-not-activated')
        self.assertFalse(result['reloaded'])
        self.assertFalse(result['desktop_started'])
        self.assertEqual(self.paths['entry'].read_text(), session.ENTRY)
        receipt = json.loads(self.paths['receipt'].read_text())
        self.assertEqual(receipt['keyboard_layout'], 'de,us')
        journal = json.loads(Path(result['journal']).read_text())
        self.assertTrue(all(not state['existed'] for state in journal['plan']['before'].values()))

    def test_update_preserves_user_entry_theme_edits_and_choices(self):
        self.apply(self.plan(keyboard='de', manual_lock=True))
        entry = self.paths['entry'].read_text().replace('caccccee', '112233ee')
        entry += '\n-- Personal additions stay here.\n'
        self.paths['entry'].write_text(entry)
        unchanged = self.plan()
        self.assertEqual(unchanged['keyboard_layout'], 'de')
        self.assertTrue(unchanged['manual_lock'])
        self.assertFalse(unchanged['changes'])
        self.assertEqual(self.apply(unchanged)['status'], 'already-current')
        changed = self.plan(keyboard='gb')
        self.assertNotIn('entry', changed['changes'])
        result = self.apply(changed)
        self.assertEqual(self.paths['entry'].read_text(), entry)
        backup = Path(result['journal']).parent / 'module'
        self.assertIn('kb_layout = "de"', backup.read_text())
        self.assertIn('kb_layout = "gb"', self.paths['module'].read_text())

    def test_untouched_managed_snippet_can_be_adopted_without_touching_user_code(self):
        directory = self.paths['entry'].parent
        directory.mkdir(parents=True)
        template = (ROOT / 'config/hypr/omabuntu-managed.lua').read_bytes()
        (directory / 'omabuntu-managed.lua').write_bytes(template)
        self.paths['entry'].write_text('-- Omabuntu installer-managed settings (plan 018)\nrequire("omabuntu-managed")\n')
        blocked = self.plan()
        self.assertTrue(any('adopt-managed' in item for item in blocked['blockers']))
        reviewed = self.plan(adopt_managed=True)
        self.assertFalse(reviewed['blockers'])
        self.assertIn('entry', reviewed['changes'])
        self.assertNotIn('omabuntu-managed', reviewed['payload']['entry'])
        self.apply(reviewed)
        self.assertEqual(self.paths['entry'].read_text(), session.ENTRY)
        self.assertEqual((directory / 'omabuntu-managed.lua').read_bytes(), template)

    def test_user_lines_block_managed_adoption(self):
        directory = self.paths['entry'].parent
        directory.mkdir(parents=True)
        (directory / 'omabuntu-managed.lua').write_bytes((ROOT / 'config/hypr/omabuntu-managed.lua').read_bytes())
        self.paths['entry'].write_text('require("omabuntu-managed")\nhl.monitor({ output = "DP-1" })\n')
        reviewed = self.plan(adopt_managed=True)
        self.assertTrue(reviewed['blockers'])
        self.assertFalse(self.paths['module'].exists())

    def test_unowned_lua_or_legacy_profile_is_never_overwritten(self):
        self.paths['entry'].parent.mkdir(parents=True)
        legacy = self.paths['entry'].with_name('hyprland.conf')
        legacy.write_text('existing user profile')
        plan = self.plan()
        self.assertTrue(plan['blockers'])
        with self.assertRaises(ValueError):
            self.apply(plan)
        self.assertEqual(legacy.read_text(), 'existing user profile')
        self.assertFalse(self.paths['entry'].exists())

    def test_user_edits_to_owned_module_block_updates(self):
        self.apply(self.plan())
        self.paths['module'].write_text('-- user edited this module\n')
        plan = self.plan(keyboard='de')
        self.assertTrue(plan['blockers'])
        with self.assertRaises(ValueError):
            self.apply(plan)
        self.assertEqual(self.paths['module'].read_text(), '-- user edited this module\n')

    def test_keyboard_injection_and_unknown_layout_are_refused(self):
        for value in ('us"); os.execute("bad")', 'no_such_layout', 'us\n', 'us,', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.plan(keyboard=value)

    def test_unsafe_paths_and_invalid_receipts_are_refused(self):
        self.paths['entry'].parent.mkdir(parents=True)
        self.paths['entry'].symlink_to(self.base / 'elsewhere')
        with self.assertRaises(ValueError):
            self.plan()
        self.paths['entry'].unlink()
        self.paths['receipt'].write_text('{}')
        with self.assertRaises(ValueError):
            self.plan()

    def test_approval_and_source_drift_block_before_writes(self):
        plan = self.plan()
        with self.assertRaises(ValueError):
            session.apply(plan, 'wrong', check_stopped=lambda: None)
        self.paths['entry'].parent.mkdir(parents=True)
        self.paths['entry'].write_text('new user config')
        with self.assertRaises(ValueError):
            self.apply(plan)
        self.assertEqual(self.paths['entry'].read_text(), 'new user config')

    def test_temporary_name_collision_does_not_delete_existing_file(self):
        path = self.paths['module']
        path.parent.mkdir(parents=True)
        existing = path.with_name('.' + path.name + '-collision')
        existing.write_text('existing temporary data')
        with patch.object(session.user_install, 'stamp', return_value='collision'), self.assertRaises(FileExistsError):
            session.write(path, b'new data', 0o644)
        self.assertEqual(existing.read_text(), 'existing temporary data')
        self.assertFalse(path.exists())

    def test_synchronous_failure_restores_only_own_written_files(self):
        plan = self.plan()
        original = session.write
        failed = []
        def write(path, data, mode):
            original(path, data, mode)
            if path == self.paths['module'] and not failed:
                failed.append(True)
                raise OSError('fixture failure after rename')
        with patch.object(session, 'write', side_effect=write), self.assertRaises(ValueError):
            self.apply(plan)
        self.assertFalse(self.paths['module'].exists())
        self.assertFalse(self.paths['entry'].exists())
        self.assertFalse(self.paths['receipt'].exists())
        self.assertFalse(session.pending(self.app))

    def test_concurrent_user_edit_requires_manual_recovery_not_overwrite(self):
        plan = self.plan()
        original = session.write
        def write(path, data, mode):
            original(path, data, mode)
            path.write_text('-- concurrent user edit\n')
            raise OSError('fixture failure')
        with patch.object(session, 'write', side_effect=write), self.assertRaises(ValueError):
            self.apply(plan)
        self.assertEqual(self.paths['module'].read_text(), '-- concurrent user edit\n')
        self.assertTrue(session.pending(self.app))
        self.assertTrue(self.plan()['blockers'])

    def test_live_session_and_unknown_lookup_are_refused(self):
        plan = self.plan()
        with patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE': 'fixture'}), \
             patch.object(session.subprocess, 'run') as run, self.assertRaises(ValueError):
            session.apply(plan, session.guided.digest(plan))
        run.assert_not_called()
        with patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE': '', 'XDG_CURRENT_DESKTOP': 'GNOME'}):
            with patch.object(session.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), self.assertRaises(ValueError):
                session.require_stopped()
            with patch.object(session.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
                session.require_stopped()


class LuaSessionTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name = ctypes.util.find_library('lua5.4')
        if not name:
            raise unittest.SkipTest('Template execution needs the Lua 5.4 library')
        cls.lua = ctypes.CDLL(name)
        cls.lua.luaL_newstate.restype = ctypes.c_void_p
        cls.lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
        cls.lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        cls.lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
        cls.lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        cls.lua.lua_tolstring.restype = ctypes.c_char_p
        cls.lua.lua_close.argtypes = [ctypes.c_void_p]

    def test_rendered_config_parses_and_registers_only_mock_actions(self):
        app = user_install.Installation(Path('/fixture/data'), Path('/fixture/state'), Path("/fixture/it's home/omabuntu"))
        text = session.render(ROOT, app, 'de,us', True)
        script = '''
local bindings = {}
local function action(kind, arg) return {kind=kind, arg=arg} end
local window = setmetatable({}, {__index=function(_, key) return function(arg) return action(key,arg) end end})
local workspace = {toggle_special=function(arg) return action('special',arg) end}
hl = {dsp={window=window, workspace=workspace}}
for _, key in ipairs({'exec_cmd','global','layout','focus'}) do
  hl.dsp[key] = function(arg) return action(key,arg) end
end
hl.monitor = function(t) assert(t.output == '' and t.scale == 1 and t.position == 'auto') end
hl.config = function(t) assert(t.input.kb_layout == 'de,us') end
hl.bind = function(key, fn, options) assert(type(fn)=='table'); bindings[key]={fn=fn, options=options} end
hl.workspace_rule = function(t) error('No layout file in fixture') end
io.open = function(path, mode) assert(mode=='r'); return nil end
''' + text + '''
assert(bindings['SUPER + SPACE'].fn.kind == 'global')
assert(bindings['SUPER + SPACE'].fn.arg == 'omabuntu:menu')
assert(bindings['SUPER + RETURN'].fn.arg == 'xdg-terminal-exec')
assert(bindings['SUPER + CTRL + L'].options.release == true)
assert(bindings['PRINT'].fn.arg:find('capture_screenshot.py',1,true))
assert(bindings['SUPER + M'].fn.arg:find('omabuntu_hyprland_window_minimize.py',1,true))
assert(bindings['SUPER + mouse:272'].options.mouse == true)
'''
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
