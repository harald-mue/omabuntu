"""Record a release still for the next login. Never start hyprpaper or hyprctl."""
import json
from pathlib import Path

SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}


def default_still(release):
    root = Path(release) / 'config/menu/backgrounds'
    if root.is_symlink() or not root.is_dir():
        return None
    chosen = None
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Release wallpaper tree contains a symlink')
        if not path.is_file() or path.suffix.lower() not in SUFFIXES:
            continue
        if path.stat().st_size <= 0 or path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError('Release wallpaper is empty or too large')
        if chosen is None:
            chosen = path
    return chosen


def record(path):
    return json.dumps({'schema_version': 1, 'path': str(path), 'applied': False,
                       'note': 'Recorded for next login; hyprpaper was not started.'}, indent=2) + '\n'


def publish_lock(link, target):
    if link.is_symlink():
        return os_readlink_matches(link, target)
    if link.exists():
        return False
    temporary = link.with_name(link.name + '.tmp')
    if temporary.exists() or temporary.is_symlink():
        raise ValueError('Lock-background temporary path already exists')
    temporary.symlink_to(target)
    temporary.replace(link)
    return os_readlink_matches(link, target)


def os_readlink_matches(link, target):
    import os
    return link.is_symlink() and os.readlink(link) == str(target)
