#!/usr/bin/env python3
"""Private per-theme still folders; no chooser, import, copying or activation."""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import stat
import subprocess

MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_FILES = 512
SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp'}
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def valid_theme(theme):
    return isinstance(theme, str) and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', theme) is not None


def config_home():
    path = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
    if not path.is_absolute():
        raise ValueError('XDG_CONFIG_HOME must be absolute.')
    return path


@contextmanager
def directory(path, create=False, owned=False):
    """Traverse with directory descriptors; refuse every symlink component."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Expected an absolute directory without traversal.')
    fd = os.open('/', DIRECTORY_FLAGS)
    try:
        for part in path.parts[1:]:
            try:
                child = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                child = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        if owned and (info.st_uid != os.getuid() or info.st_mode & 0o022):
            raise ValueError('Artwork directories must be owned and not writable by others.')
        yield fd
    finally:
        os.close(fd)


@contextmanager
def folder(theme, create=False):
    if not valid_theme(theme):
        raise ValueError('Choose a valid theme before managing backgrounds.')
    base = config_home()
    with directory(base, create=create, owned=True):
        pass
    for path in (base / 'omabuntu', base / 'omabuntu/backgrounds'):
        with directory(path, create=create, owned=True):
            pass
    path = base / 'omabuntu/backgrounds' / theme
    with directory(path, create=create, owned=True) as fd:
        yield path, fd


def images(theme):
    """Direct level only; a missing/unsafe personal tree contributes no rows."""
    if not valid_theme(theme):
        return []
    try:
        with folder(theme) as (path, fd):
            result = []
            for name in sorted(os.listdir(fd)):
                if len(result) >= MAX_FILES:
                    break
                if Path(name).suffix.lower() not in SUFFIXES or name.startswith('.'):
                    continue
                if any(ord(c) < 32 or ord(c) == 127 or c == ',' for c in name):
                    continue
                try:
                    info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                except OSError:
                    continue
                if stat.S_ISREG(info.st_mode) and 0 < info.st_size <= MAX_IMAGE_BYTES:
                    result.append(path / name)
            return result
    except (OSError, ValueError):
        return []


def theme_ids():
    try:
        with directory(config_home() / 'omabuntu/backgrounds', owned=True) as fd:
            return sorted(name for name in os.listdir(fd) if valid_theme(name)
                          and stat.S_ISDIR(os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode))[:MAX_FILES]
    except (OSError, ValueError):
        return []


def open_folder(theme, run=None):
    """Open the current theme's folder like upstream; never apply a background."""
    try:
        with folder(theme, create=True) as (path, _):
            uri = path.as_uri()
        if run is None:
            subprocess.Popen(['xdg-open', uri], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
            return {'ok': True, 'status': 'started-not-accepted'}
        code = run(['xdg-open', uri])
        return {'ok': code == 0}
    except (OSError, ValueError) as error:
        return {'ok': False, 'error': 'folder', 'message': str(error)}
