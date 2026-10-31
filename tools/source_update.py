"""Fetch only already reviewed source archives. Never move a checkout.

Trust is the pinned commit in this repository, not a checksum, tag or branch.
A checksum only proves the download matches that pin. No build or deployment.
"""
import hashlib
import json
import os
from pathlib import Path
import urllib.request

import build_plugin
import build_runtime
import install as guided
import user_install

ROOT = Path(__file__).resolve().parents[1]
POLICY = ('Reviewed pins only. No branches, tags, latest refs or checkout resets. '
          'SHA-256 is a consistency check, not a publisher signature.')


def pins(root=ROOT):
    runtime = user_install.read_json(root / 'upstream/source-lock.json')
    plugin = build_plugin.inputs(root)
    screenshot = json.loads((root / 'upstream/omasnap-source.json').read_text())
    omarchy = user_install.read_json(root / 'upstream/omarchy-source.json')
    records = []
    for item in runtime['sources']:
        records.append(archive_pin(item))
    records.append(archive_pin(screenshot))
    for item in plugin['sources']:
        records.append(archive_pin(item))
    if not re_commit(omarchy.get('commit')) or omarchy.get('repository') != 'https://github.com/omacom/omarchy':
        raise ValueError('Omarchy source pin differs')
    records.append({'name': 'omarchy', 'repository': omarchy['repository'], 'commit': omarchy['commit'],
                    'archive_url': None, 'fetch': False,
                    'reason': 'Commit pin only; artwork files use the separate locked downloader.'})
    if len({(item['repository'], item['commit']) for item in records}) != len(records):
        raise ValueError('Duplicate source pin')
    return records


def re_commit(value):
    return isinstance(value, str) and len(value) == 40 and all(character in '0123456789abcdef' for character in value)


def archive_pin(item):
    commit = item.get('commit')
    repository = item.get('repository', '')
    name = item.get('name') or repository.rstrip('/').rsplit('/', 1)[-1]
    expected = 'https://codeload.github.com/' + repository.removeprefix('https://github.com/') + '/tar.gz/' + str(commit)
    if (not repository.startswith('https://github.com/') or not re_commit(commit)
            or item.get('archive_url') != expected or item.get('archive_root') != name + '-' + commit
            or type(item.get('archive_bytes')) is not int or not 0 < item['archive_bytes'] <= build_runtime.MAX_ARCHIVE_BYTES
            or not isinstance(item.get('archive_sha256'), str) or len(item['archive_sha256']) != 64):
        raise ValueError('Unreviewed source archive pin: ' + str(name))
    return {'name': name, 'repository': repository, 'commit': commit, 'archive_url': expected,
            'archive_bytes': item['archive_bytes'], 'archive_sha256': item['archive_sha256'],
            'archive_root': item['archive_root'], 'fetch': True}


def cache_state(root, item):
    if not item['fetch']:
        return {'cached': False, 'fetched_here': False}
    path = root / 'work/source-cache' / (item['name'] + '-' + item['commit'] + '.tar.gz')
    if path.is_symlink():
        raise ValueError('Symlinked source cache: ' + item['name'])
    if not path.exists():
        return {'cached': False, 'path': str(path)}
    if not path.is_file() or path.stat().st_size != item['archive_bytes']:
        return {'cached': True, 'matches': False, 'path': str(path)}
    return {'cached': True, 'matches': hashlib.sha256(path.read_bytes()).hexdigest() == item['archive_sha256'],
            'path': str(path)}


def review(root=ROOT):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Review sources as your normal user')
    user_install.safe_parents(root)
    records = []
    for item in pins(root):
        state = cache_state(root, item)
        records.append({**item, 'cache': state})
    blockers = ['Cached source differs and is retained: ' + item['name']
                for item in records if item['cache'].get('matches') is False]
    return {'schema_version': 1, 'kind': 'omabuntu-source-update', 'root': str(Path(root).absolute()),
            'policy': POLICY, 'sources': records, 'blockers': blockers,
            'checkout_reset': False, 'builds': False, 'deploys': False,
            'publisher_signature': False, 'status': 'blocked' if blockers else 'review-required'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch_one(item, cache, opener):
    path = cache / (item['name'] + '-' + item['commit'] + '.tar.gz')
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('Unsafe source cache: ' + item['name'])
    if path.exists():
        if path.stat().st_size != item['archive_bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != item['archive_sha256']:
            raise ValueError('Cached source differs and is retained: ' + item['name'])
        return {'name': item['name'], 'status': 'reused', 'path': str(path)}
    request = urllib.request.Request(item['archive_url'], headers={'User-Agent': 'Omabuntu-pinned-source-update'})
    with opener.open(request, timeout=60) as response:
        data = response.read(item['archive_bytes'] + 1)
    if len(data) != item['archive_bytes'] or hashlib.sha256(data).hexdigest() != item['archive_sha256']:
        raise ValueError('Downloaded source differs from the reviewed pin: ' + item['name'])
    temporary = cache / ('.download-' + item['name'] + '-' + user_install.stamp())
    created = False
    try:
        with temporary.open('xb') as stream:
            created = True
            stream.write(data)
        os.link(temporary, path)
    finally:
        if created:
            temporary.unlink(missing_ok=True)
    return {'name': item['name'], 'status': 'fetched', 'path': str(path), 'executed': False}


def apply(reviewed, approval, opener=None):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Fetch sources as your normal user')
    if guided.digest(reviewed) != approval or reviewed.get('kind') != 'omabuntu-source-update' or reviewed.get('blockers'):
        raise ValueError('Source approval differs or a cache conflict needs review')
    root = Path(reviewed['root'])
    if root != ROOT.absolute():
        raise ValueError('Source review belongs to another checkout')
    fresh = review(root)
    if fresh != reviewed:
        raise ValueError('Source pins or cache changed; review again')
    cache = user_install.private_directory(root / 'work/source-cache')
    downloader = opener or urllib.request.build_opener(NoRedirect)
    results = []
    for item in reviewed['sources']:
        if not item['fetch']:
            results.append({'name': item['name'], 'status': 'not-fetched', 'reason': item['reason']})
            continue
        results.append(fetch_one(item, cache, downloader))
    if any(item.get('executed') for item in results):
        raise ValueError('Source acquisition must not execute downloads')
    return {'status': 'archives-verified', 'results': results, 'checkout_reset': False,
            'builds': False, 'deploys': False, 'publisher_signature': False}
