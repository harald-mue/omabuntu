"""Signed public-release metadata and archive retrieval, without installation."""
import hashlib
import json
from pathlib import Path
import re

import download_release as transport
import release_archive

VERSION = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z')
TARGET = 'ubuntu-26.04-x86_64'


def version_tuple(value):
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ValueError('Not a public semantic release version')
    return tuple(map(int, value.split('.')))


def bundle_public_version(value):
    """Normalize only the publisher's exact release- prefix, not local suffixes."""
    if isinstance(value, str) and value.startswith('release-'):
        value = value[len('release-'):]
    version_tuple(value)
    return value


def availability(installed, incoming, provenance):
    """Do not order private derivatives or silently replace unpublished fixes."""
    version_tuple(incoming)
    if (not isinstance(provenance, dict)
            or any(key.startswith('local_') and key != 'local_image_directories' for key in provenance)):
        return 'local-release-blocked'
    try:
        current = version_tuple(bundle_public_version(installed))
    except ValueError:
        return 'local-release-blocked'
    candidate = version_tuple(incoming)
    return 'newer' if candidate > current else 'current' if candidate == current else 'downgrade-blocked'


def discover(key, directory, fetch=None, verify=None):
    """Only the API tag is a discovery hint; trust signed metadata, not API text."""
    fetch = fetch or transport.fetch
    verify = verify or transport.verify
    directory = Path(directory)
    fetch(transport.API, directory / 'github.json', 1024 * 1024)
    api = json.loads((directory / 'github.json').read_text())
    if not isinstance(api, dict):
        raise ValueError('Unexpected release discovery response')
    tag = api.get('tag_name', '')
    if not isinstance(tag, str) or not tag.startswith('v') or api.get('draft') or api.get('prerelease'):
        raise ValueError('Unexpected public release')
    version_tuple(tag[1:])
    base = 'https://github.com/' + transport.REPOSITORY + '/releases/download/' + tag + '/'
    for name in ('SHA256SUMS', 'SHA256SUMS.sig'):
        fetch(base + name, directory / name, 65536)
    verify(key, directory / 'SHA256SUMS', directory / 'SHA256SUMS.sig', directory)
    hashes = transport.checksums((directory / 'SHA256SUMS').read_text())
    archive = 'omabuntu-' + tag[1:] + '-' + TARGET + '.tar.gz'
    if 'release.json' not in hashes or archive not in hashes:
        raise ValueError('Missing signed release checksums')
    fetch(base + 'release.json', directory / 'release.json', 65536)
    raw = (directory / 'release.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != hashes['release.json']:
        raise ValueError('Release metadata checksum mismatch')
    meta = json.loads(raw)
    if (not isinstance(meta, dict) or meta.get('version') != tag[1:]
            or meta.get('target') != TARGET or meta.get('archive') != archive
            or meta.get('sha256') != hashes[archive]
            or type(meta.get('bytes')) is not int or not 0 < meta['bytes'] <= 2 * 1024**3):
        raise ValueError('Signed release metadata mismatch')
    return {'version': meta['version'], 'archive': archive, 'sha256': meta['sha256'],
            'bytes': meta['bytes'], 'url': base + archive}


def download(info, directory, fetch=None):
    """Accept the in-memory verified discover result, never a user URL argument."""
    fetch = fetch or transport.fetch
    directory = Path(directory)
    path = directory / info['archive']
    fetch(info['url'], path, info['bytes'])
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if path.stat().st_size != info['bytes'] or actual != info['sha256']:
        raise ValueError('Release archive size/checksum mismatch')
    destination = directory / 'unpacked'
    release_archive.extract(path, destination)
    return destination / 'bundle'
