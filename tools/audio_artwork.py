#!/usr/bin/env python3
"""Admit bounded owned cached PNG/JPEG artwork; never fetch remote URLs."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import stat
import struct
import sys
import urllib.parse
import zlib

import appearance_backend as files

MAX_BYTES = 4 * 1024 * 1024
MAX_SIDE = 2048


def dimensions(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        if (len(data) < 33 or data[8:16] != b'\0\0\0\rIHDR'
                or zlib.crc32(data[12:29]) != int.from_bytes(data[29:33], 'big')):
            raise ValueError('invalid-artwork-header')
        width, height = struct.unpack('>II', data[16:24]); suffix = '.png'
    elif data.startswith(b'\xff\xd8'):
        offset = 2; width = height = 0; suffix = '.jpg'
        while offset + 4 <= len(data):
            if data[offset] != 255: raise ValueError('invalid-artwork-header')
            while offset < len(data) and data[offset] == 255: offset += 1
            if offset >= len(data): break
            marker = data[offset]; offset += 1
            if marker in (0xd9, 0xda): break
            if marker in (0x01, *range(0xd0, 0xd8)): continue
            length = int.from_bytes(data[offset:offset + 2], 'big')
            if length < 2 or offset + length > len(data): raise ValueError('invalid-artwork-header')
            if marker in (0xc0, 0xc1, 0xc2):
                if length < 8 or data[offset + 2] != 8: raise ValueError('invalid-artwork-header')
                height, width = struct.unpack('>HH', data[offset + 3:offset + 7]); break
            offset += length
        if not width or not height: raise ValueError('invalid-artwork-header')
    else:
        raise ValueError('unsupported-artwork-format')
    if not 1 <= width <= MAX_SIDE or not 1 <= height <= MAX_SIDE:
        raise ValueError('artwork-dimensions-limit')
    return suffix


def admit(url, cache=None):
    if not isinstance(url, str) or len(url) > 8192: raise ValueError('invalid-artwork-url')
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'file' or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError('only-local-cache-artwork')
    source = Path(urllib.parse.unquote_to_bytes(parsed.path).decode('utf-8'))
    cache = Path(cache) if cache is not None else Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache')))
    if not cache.is_absolute() or not source.is_absolute() or '..' in source.parts or not source.is_relative_to(cache):
        raise ValueError('artwork-outside-cache')
    files.safe(cache); files.safe(source)
    # Cache roots and all descendants used here must be owned and not writable
    # by other users. No arbitrary player-selected home/credential file is read.
    for p in (cache, *reversed(source.relative_to(cache).parents)):
        directory = p if p.is_absolute() else cache / p
        info = directory.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise ValueError('unsafe-artwork-directory')
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or before.st_nlink != 1
                or before.st_mode & 0o022 or before.st_size > MAX_BYTES):
            raise ValueError('unsafe-artwork-file')
        with os.fdopen(fd, 'rb', closefd=False) as stream: data = stream.read(MAX_BYTES + 1)
        after = os.fstat(fd)
        if len(data) > MAX_BYTES or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('artwork-changed')
    finally:
        os.close(fd)
    suffix = dimensions(data)
    destination = cache / 'omabuntu/audio-art'
    files.mkdirs(destination)
    info = destination.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('private-artwork-cache-required')
    name = hashlib.sha256(data).hexdigest() + suffix
    target = destination / name
    files.safe(target)
    if target.exists():
        info = target.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_size != len(data) or info.st_nlink != 1
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600):
            raise ValueError('artwork-cache-differs')
        fd = os.open(target, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        try:
            with os.fdopen(fd, 'rb', closefd=False) as stream: existing = stream.read(MAX_BYTES + 1)
        finally:
            os.close(fd)
        if existing != data:
            raise ValueError('artwork-cache-differs')
    else:
        entries = list(itertools.islice(destination.iterdir(), 65))
        if len(entries) >= 64 or sum(p.lstat().st_size for p in entries) + len(data) > 32 * 1024 * 1024:
            raise ValueError('artwork-cache-limit')
        if any(p.is_symlink() or not p.is_file() for p in entries):
            raise ValueError('unsafe-artwork-cache')
        # A deterministic new immutable cache object; never overwrite old art.
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream: stream.write(data); stream.flush(); os.fsync(stream.fileno())
    return target.as_uri()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-local-artwork', action='store_true')
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(16385)
        if not args.allow_local_artwork or len(raw) > 16384: raise ValueError('artwork-grant-or-limit')
        packet = json.loads(raw)
        if (not isinstance(packet, dict) or set(packet) != {'url', 'key'}
                or type(packet['key']) is not int or not 0 <= packet['key'] <= 0x7fffffff):
            raise ValueError('invalid-artwork-request')
        result = {'ok': True, 'source': admit(packet.get('url')), 'key': packet.get('key')}
    except (OSError, ValueError, TypeError): result = {'ok': False, 'source': ''}
    print(json.dumps(result))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
