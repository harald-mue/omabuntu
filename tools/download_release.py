#!/usr/bin/env python3
"""Download a signed published release, never install packages or start a session."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

import release_archive

REPOSITORY = 'harald-mue/omabuntu'
API = 'https://api.github.com/repos/' + REPOSITORY + '/releases/latest'


class HTTPSRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != 'https' or parsed.hostname not in (
                'api.github.com', 'github.com', 'release-assets.githubusercontent.com'):
            raise ValueError('Unexpected download redirect')
        return super().redirect_request(request, response, code, message, headers, newurl)


def fetch(url, destination, limit):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('api.github.com', 'github.com'):
        raise ValueError('Unexpected release URL')
    request = urllib.request.Request(url, headers={'User-Agent': 'Omabuntu-release-installer'})
    started = time.monotonic()
    opener = urllib.request.build_opener(HTTPSRedirects())
    with opener.open(request, timeout=30) as response, open(destination, 'xb') as output:
        final = urllib.parse.urlparse(response.url)
        if final.scheme != 'https' or final.hostname not in (
                'api.github.com', 'github.com', 'release-assets.githubusercontent.com'):
            raise ValueError('Unexpected download redirect')
        total = 0
        while True:
            if time.monotonic() - started > 600:
                raise ValueError('Download exceeded total time limit')
            data = response.read(1024 * 1024)
            if not data:
                break
            total += len(data)
            if total > limit:
                raise ValueError('Download exceeds size limit')
            output.write(data)


def checksums(text):
    entries = {}
    for line in text.splitlines():
        match = re.fullmatch(r'([a-f0-9]{64})  ([A-Za-z0-9._-]+)', line)
        if not match or match[2] in entries:
            raise ValueError('Invalid checksum document')
        entries[match[2]] = match[1]
    return entries


def verify(key, sums, signature, directory):
    parts = key.read_text().strip().split()
    if len(parts) < 2 or parts[0] != 'ssh-ed25519':
        raise ValueError('Expected a trusted Ed25519 publisher public key')
    allowed = directory / 'allowed_signers'
    allowed.write_text('omabuntu ' + ' '.join(parts[:2]) + '\n')
    with sums.open('rb') as source:
        subprocess.run(['ssh-keygen', '-Y', 'verify', '-f', str(allowed), '-I', 'omabuntu',
                        '-n', 'omabuntu-release', '-s', str(signature)],
                       stdin=source, check=True, timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-key', type=Path, required=True)
    args = parser.parse_args()
    if os.getuid() == 0:
        raise ValueError('Run as your normal user, not root')
    if platform.machine() != 'x86_64':
        raise ValueError('Published releases support x86_64 only')
    info = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    if info.get('ID', '').strip('"') != 'ubuntu' or info.get('VERSION_ID', '').strip('"') != '26.04':
        raise ValueError('Published releases require Ubuntu 26.04')
    with tempfile.TemporaryDirectory(prefix='omabuntu-release-') as temporary:
        directory = Path(temporary)
        index = directory / 'github.json'
        fetch(API, index, 1024 * 1024)
        release = json.loads(index.read_text())
        tag = release['tag_name']
        if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', tag) or release.get('draft') or release.get('prerelease'):
            raise ValueError('Unexpected published release')
        name = 'omabuntu-' + tag[1:] + '-ubuntu-26.04-x86_64.tar.gz'
        base = 'https://github.com/' + REPOSITORY + '/releases/download/' + tag + '/'
        for item in ('SHA256SUMS', 'SHA256SUMS.sig'):
            fetch(base + item, directory / item, 65536)
        verify(args.public_key, directory / 'SHA256SUMS', directory / 'SHA256SUMS.sig', directory)
        hashes = checksums((directory / 'SHA256SUMS').read_text())
        for item, limit in ((name, 2 * 1024**3), ('release.json', 65536)):
            if item not in hashes:
                raise ValueError('Missing signed checksum: ' + item)
            fetch(base + item, directory / item, limit)
            if hashlib.sha256((directory / item).read_bytes()).hexdigest() != hashes[item]:
                raise ValueError('Checksum mismatch: ' + item)
        metadata = json.loads((directory / 'release.json').read_text())
        if (metadata['version'] != tag[1:] or metadata['archive'] != name
                or metadata['target'] != 'ubuntu-26.04-x86_64'
                or metadata['sha256'] != hashes[name]
                or metadata['bytes'] != (directory / name).stat().st_size):
            raise ValueError('Release metadata mismatch')
        cache = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache')))
        if not cache.is_absolute() or any(p.is_symlink() for p in (cache, *cache.parents)):
            raise ValueError('Unsafe cache directory')
        cache = cache / 'omabuntu/published'
        if any(p.is_symlink() for p in (cache, *cache.parents)):
            raise ValueError('Unsafe cache directory')
        cache.mkdir(parents=True, mode=0o700, exist_ok=True)
        retained = Path(tempfile.mkdtemp(prefix=tag + '-', dir=cache))
        target = retained / 'unpacked'
        release_archive.extract(directory / name, target)
        print('Installer source and private prerequisite reports retained at ' + str(target), flush=True)
        print('Verified publisher signature and archive for ' + tag, flush=True)
        subprocess.run(['python3', '-B', str(target / 'source/tools/published_install.py'),
                        '--bundle', str(target / 'bundle')], check=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit('Download stopped: ' + str(error))
