"""Local dev/stable pointers to immutable releases. No download or publication.

A channel file is a reviewed pin, not a publisher signature and not permission
to redistribute artwork.
"""
import json
import os
from pathlib import Path
import re

import install as guided
import user_install

NAMES = {'stable', 'dev'}
KIND = 'omabuntu-release-channels'


def identity(bundle):
    meta = user_install.verify_bundle(Path(bundle))
    return meta['version'], guided.digest(meta)


def document(channels):
    if not isinstance(channels, dict) or not channels or not set(channels) <= NAMES:
        raise ValueError('Channels must be stable and/or dev')
    cleaned = {}
    for name, item in channels.items():
        if (not isinstance(item, dict) or set(item) != {'version', 'bundle_sha256'}
                or not user_install.VERSION.fullmatch(item['version'])
                or not re.fullmatch(r'[a-f0-9]{64}', item['bundle_sha256'])):
            raise ValueError('Channel entry must pin only a version and SHA-256')
        cleaned[name] = {'version': item['version'], 'bundle_sha256': item['bundle_sha256']}
    return {'schema_version': 1, 'kind': KIND, 'channels': cleaned, 'publisher_signature': False,
            'artwork_included': False,
            'note': 'Channel pin only. Not a publisher signature or an artwork redistribution grant.'}


def from_bundle(name, bundle, current=None):
    if name not in NAMES:
        raise ValueError('Unknown channel')
    version, digest = identity(bundle)
    channels = {}
    if current:
        channels.update(load(current)['channels'])
    channels[name] = {'version': version, 'bundle_sha256': digest}
    return document(channels)


def load(path):
    path = Path(path)
    user_install.safe_parents(path.parent)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError('Unsafe channel file')
    data = user_install.read_json(path)
    if not isinstance(data, dict) or data.get('publisher_signature') is not False or data.get('artwork_included') is not False:
        raise ValueError('Channel file must not claim a signature or artwork grant')
    loaded = document(data.get('channels'))
    if data.get('schema_version') != 1 or data.get('kind') != KIND:
        raise ValueError('Unsupported channel file')
    return loaded


def resolve(channel_file, name, release_dir):
    if name not in NAMES:
        raise ValueError('Unknown channel')
    item = load(channel_file)['channels'].get(name)
    if item is None:
        raise ValueError('Channel is not pinned: ' + name)
    root = user_install.safe_parents(Path(release_dir).absolute())
    bundle = root / item['version']
    if bundle.is_symlink():
        raise ValueError('Refusing a symlinked release')
    version, digest = identity(bundle)
    if version != item['version'] or digest != item['bundle_sha256']:
        raise ValueError('Release does not match the channel pin')
    return {'channel': name, 'version': version, 'bundle': str(bundle), 'bundle_sha256': digest,
            'publisher_signature': False, 'downloaded': False, 'published': False}


def write(path, record, replace=False):
    path = Path(path)
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Write a channel file as your normal user')
    record = document(record['channels'])
    user_install.safe_parents(path.parent)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('Unsafe channel destination')
    if path.exists() and not replace:
        raise ValueError('Channel file exists; pass --replace to update the pin')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '-' + user_install.stamp())
    created = False
    try:
        with temporary.open('xb') as stream:
            created = True
            stream.write((json.dumps(record, indent=2) + '\n').encode())
        temporary.chmod(0o644)
        temporary.replace(path)
    finally:
        if created:
            temporary.unlink(missing_ok=True)
    if load(path) != record:
        raise ValueError('Written channel file differs')
    return path
