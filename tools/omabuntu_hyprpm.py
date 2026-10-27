#!/usr/bin/env python3
"""Run hyprpm with the Ubuntu Lua include workaround scoped to its process."""
import os
from pathlib import Path
import shutil
import sys

LUA_INCLUDE = Path('/usr/include/lua5.4')


def build_environment(environment):
    """Copy the environment and append Lua without replacing existing paths."""
    result = dict(environment)
    current = result.get('CPLUS_INCLUDE_PATH', '')
    include = str(LUA_INCLUDE)
    if include not in current.split(os.pathsep):
        result['CPLUS_INCLUDE_PATH'] = current + os.pathsep + include if current else include
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    if not (LUA_INCLUDE / 'lua.h').is_file():
        print('omabuntu-hyprpm: missing /usr/include/lua5.4/lua.h; '
              'check the liblua5.4-dev package. No packages were installed.', file=sys.stderr)
        return 2
    executable = shutil.which('hyprpm')
    if executable is None:
        print('omabuntu-hyprpm: hyprpm is not available on PATH.', file=sys.stderr)
        return 127
    try:
        # Replace this process: signals and exit status belong to hyprpm.
        # No shell, elevation, force flag or implicit build/reload is added.
        os.execve(executable, [executable, *args], build_environment(os.environ))
    except OSError as error:
        print('omabuntu-hyprpm: cannot execute hyprpm: ' + str(error), file=sys.stderr)
        return 126


if __name__ == '__main__':
    raise SystemExit(main())
