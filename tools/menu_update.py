"""Launch only the installed independent update terminal, never an update inline."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def launch():
    root = Path(__file__).resolve().parents[1]
    runner = root / 'updater/tools/application_update.py'
    terminal = shutil.which('xdg-terminal-exec')
    if (not terminal or not runner.is_file() or runner.is_symlink()
            or any(part.is_symlink() for part in runner.parents)
            or not (root / 'release.json').is_file()):
        return {'ok': False, 'error': 'missing', 'message': 'Installed update runner or xdg-terminal-exec is missing.'}
    # The runner validates session, selected bundle integrity and every approval.
    # Separate process/session: restarting the shell must not kill its updater.
    command = [terminal, '--title=Omabuntu Update', '-e', sys.executable, '-B', str(runner)]
    try:
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True,
                         env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    except OSError as error:
        return {'ok': False, 'error': 'failed', 'message': 'Could not open update terminal: ' + str(error)}
    return {'ok': True, 'status': 'terminal-started-not-updated'}
