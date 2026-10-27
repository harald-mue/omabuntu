"""Process-scoped Lua include workaround; never modify the session environment."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import omabuntu_hyprpm as wrapper


class HyprpmWrapperTests(unittest.TestCase):
    def test_environment_is_copied(self):
        original = {'PATH': '/usr/bin', 'OTHER': 'unchanged'}
        result = wrapper.build_environment(original)
        self.assertEqual(result['CPLUS_INCLUDE_PATH'], '/usr/include/lua5.4')
        self.assertEqual(result['OTHER'], 'unchanged')
        self.assertNotIn('CPLUS_INCLUDE_PATH', original)

    def test_existing_paths_and_order_are_preserved(self):
        result = wrapper.build_environment({'CPLUS_INCLUDE_PATH': '/first:/second'})
        self.assertEqual(result['CPLUS_INCLUDE_PATH'], '/first:/second:/usr/include/lua5.4')

    def test_no_duplicate_include(self):
        original = {'CPLUS_INCLUDE_PATH': '/usr/include/lua5.4:/custom'}
        self.assertEqual(wrapper.build_environment(original), original)

    def test_empty_value_has_no_leading_current_directory_entry(self):
        result = wrapper.build_environment({'CPLUS_INCLUDE_PATH': ''})
        self.assertEqual(result['CPLUS_INCLUDE_PATH'], '/usr/include/lua5.4')

    def test_missing_header_stops_before_execution(self):
        with patch.object(Path, 'is_file', return_value=False), \
                patch.object(wrapper.os, 'execve') as execute, \
                patch('builtins.print'):
            self.assertEqual(wrapper.main(['update']), 2)
            execute.assert_not_called()

    def test_missing_hyprpm(self):
        with patch.object(Path, 'is_file', return_value=True), \
                patch.object(wrapper.shutil, 'which', return_value=None), \
                patch('builtins.print'):
            self.assertEqual(wrapper.main([]), 127)

    def test_arguments_pass_through_without_implicit_actions(self):
        args = ['add', 'https://example.invalid/repo', 'revision with spaces']
        with patch.object(Path, 'is_file', return_value=True), \
                patch.object(wrapper.shutil, 'which', return_value='/usr/bin/hyprpm'), \
                patch.dict(os.environ, {'PATH': '/usr/bin'}, clear=True), \
                patch.object(wrapper.os, 'execve') as execute:
            wrapper.main(args)
            executable, argv, environment = execute.call_args.args
            self.assertEqual(executable, '/usr/bin/hyprpm')
            self.assertEqual(argv, [executable, *args])
            self.assertEqual(environment['CPLUS_INCLUDE_PATH'], '/usr/include/lua5.4')
            self.assertNotIn('CPLUS_INCLUDE_PATH', os.environ)

    def test_execution_failure(self):
        with patch.object(Path, 'is_file', return_value=True), \
                patch.object(wrapper.shutil, 'which', return_value='/usr/bin/hyprpm'), \
                patch.object(wrapper.os, 'execve', side_effect=PermissionError('denied')), \
                patch('builtins.print'):
            self.assertEqual(wrapper.main(['list']), 126)
