#!/usr/bin/env python3
"""Map Omarchy screenshot arguments onto one approved Omasnap binary.

Pinned Omarchy ``bin/omarchy-capture-screenshot`` (commit 03ff1eff) does not
capture anything itself. ``copy`` becomes ``--copy``, ``save`` becomes
``--save``, a bare ``slurp`` argument is dropped, and every other argument is
passed through. ``OMARCHY_SCREENSHOT_DIR`` is copied to
``OMASNAP_SCREENSHOT_DIR`` only when the latter is unset.

The default binary is ``~/.local/bin/omasnap``. ``OMABUNTU_OMASNAP`` may name
another absolute regular file whose name is ``omasnap``. This process is
replaced with that one file. The process environment is a mapping, not a
dict. This Hyprland process does not export ``WAYLAND_DISPLAY``; when that
variable is empty and the runtime directory contains exactly one Wayland
socket, the child receives its name. Nothing is captured while the binary
is missing, and this module never calls grim, slurp, hyprctl, or a shell.
"""
import collections.abc
import os
from pathlib import Path
import sys


class CaptureError(ValueError):
    pass


def mapped_arguments(args):
    if not isinstance(args, (list, tuple)):
        raise CaptureError("arguments")
    mapped = []
    for arg in args:
        if not isinstance(arg, str) or "\n" in arg or "\0" in arg or len(arg) > 4096:
            raise CaptureError("refused")
        if arg == "copy":
            mapped.append("--copy")
        elif arg == "save":
            mapped.append("--save")
        elif arg == "slurp":
            continue
        else:
            mapped.append(arg)
    return mapped


def wayland_display(env):
    """Name the one runtime socket when the compositor exported none."""
    current = env.get("WAYLAND_DISPLAY") or ""
    if current:
        return current
    runtime = env.get("XDG_RUNTIME_DIR") or ""
    root = Path(runtime)
    if not runtime or not root.is_absolute() or root.is_symlink() or not root.is_dir():
        return ""
    names = []
    try:
        entries = list(root.iterdir())
    except OSError:
        return ""
    for entry in entries:
        name = entry.name
        if not name.startswith("wayland-") or name.endswith(".lock") or entry.is_symlink():
            continue
        try:
            if entry.is_socket():
                names.append(name)
        except OSError:
            continue
    return names[0] if len(names) == 1 else ""


def capture_environment(environ):
    if not isinstance(environ, collections.abc.Mapping):
        raise CaptureError("environment")
    env = dict(environ)
    legacy = env.get("OMARCHY_SCREENSHOT_DIR") or ""
    native = env.get("OMASNAP_SCREENSHOT_DIR") or ""
    if legacy and not native:
        env["OMASNAP_SCREENSHOT_DIR"] = legacy
    display = wayland_display(env)
    if display and not env.get("WAYLAND_DISPLAY"):
        env["WAYLAND_DISPLAY"] = display
    return env


def approved_binary(environ, binary=None):
    if not isinstance(environ, collections.abc.Mapping):
        raise CaptureError("environment")
    chosen = binary
    if chosen is None:
        chosen = environ.get("OMABUNTU_OMASNAP") or ""
        if not chosen:
            home = environ.get("HOME") or ""
            if not home or not Path(home).is_absolute():
                raise CaptureError("HOME must be absolute")
            chosen = str(Path(home) / ".local/bin/omasnap")
    path = Path(chosen)
    if not isinstance(chosen, str) or not path.is_absolute() or "\0" in chosen:
        raise CaptureError("Omasnap path must be absolute")
    if path.name != "omasnap":
        raise CaptureError("Approved Omasnap binary must be named omasnap")
    if path.is_symlink():
        raise CaptureError("Approved Omasnap binary must be a regular file")
    if not path.is_file():
        raise CaptureError("Approved Omasnap binary is missing")
    if not os.access(path, os.X_OK):
        raise CaptureError("Approved Omasnap binary is not executable")
    return path


def plan(args, environ, binary=None):
    path = approved_binary(environ, binary)
    return [str(path), *mapped_arguments(args)], capture_environment(environ)


def main(argv=None, environ=None, binary=None):
    args = list(sys.argv[1:] if argv is None else argv)
    env = os.environ if environ is None else environ
    try:
        command, child = plan(args, env, binary)
        os.execve(command[0], command, child)
    except CaptureError as error:
        print(error, file=sys.stderr)
        return 1
    except OSError:
        print("Omasnap did not start", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
