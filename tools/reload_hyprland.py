#!/usr/bin/env python3
"""Reload configuration, not the compositor; refuse reported configuration errors."""
import subprocess


def reload_config(run=None):
    run = run or subprocess.run
    for command in (['hyprctl', 'reload'], ['hyprctl', 'configerrors']):
        result = run(command, capture_output=True, text=True, timeout=20, check=True)
        if command[-1] == 'configerrors' and result.stdout.strip():
            raise ValueError('Hyprland configuration errors:\n' + result.stdout)
    print('Hyprland configuration reloaded; compositor and applications remain running.')


if __name__ == '__main__':
    try:
        reload_config()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
