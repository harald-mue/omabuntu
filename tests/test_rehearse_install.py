"""The rehearsal stays inside its fixture and restores a failed start."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import rehearse_install as rehearse
import session_config


class RehearsalTests(unittest.TestCase):
    def test_lifecycle_restores_failure_and_rolls_back_without_host_writes(self):
        sentinel = Path.home() / '.config/hypr/hyprland.lua'
        before = sentinel.read_bytes() if sentinel.is_file() else None
        native = {'version': '0.56.2', 'commit': session_config.build_hyprbars.HYPRLAND_COMMIT, 'dirty': False}
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            base = Path(directory)
            env = {'XDG_CONFIG_HOME': str(base / 'config'), 'XDG_DATA_HOME': str(base / 'data'),
                   'XDG_STATE_HOME': str(base / 'state'), 'HYPRLAND_INSTANCE_SIGNATURE': ''}
            old = {key: os.environ.get(key) for key in env}
            os.environ.update(env)
            try:
                report = rehearse.run(base, native)
            finally:
                for key, value in old.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
        self.assertEqual(report['installed'], 'installed-not-started')
        self.assertEqual(report['repeated'], 'already-installed')
        self.assertEqual(report['failed_start'], 'restored')
        self.assertEqual(report['selected_after_failure'], 'releases/v1')
        self.assertEqual(report['updated'], 'installed-not-started')
        self.assertEqual(report['updated_selected'], 'releases/v2')
        self.assertEqual(report['final_selected'], 'releases/v1')
        self.assertEqual(report['session'], 'configured-not-activated')
        self.assertEqual(report['activation'], 'prepared-for-next-login')
        self.assertNotIn('start-ok', report['events'])
        self.assertFalse(report['vm_accepted'])
        after = sentinel.read_bytes() if sentinel.is_file() else None
        self.assertEqual(before, after)
