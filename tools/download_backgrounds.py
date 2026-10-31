#!/usr/bin/env python3
"""Download locked wallpaper assets into a staging/cache directory, not Git.

Default is a plan. --check is offline. --download requires explicit invocation,
uses only committed pinned URLs, and never overwrites local conflicting files.
Image-specific redistribution rights are not established by root MIT licensing.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'upstream/theme-backgrounds.json'
COMMIT = '03ff1eff3812933f7088484533784d2f63eaf19a'
PREFIX = 'https://raw.githubusercontent.com/omacom/omarchy/' + COMMIT + '/'
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
NOTICE = ('Images are downloaded locally from pinned upstream URLs. Individual image '
          'licenses are not established by the repository MIT license; these assets '
          'are not cleared for redistribution in public Omabuntu bundles.')


class AssetError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssetError('Artwork redirects are not permitted')


def entries(record):
    if (not isinstance(record, dict) or record.get('schema_version') != 1
            or not isinstance(record.get('source'), dict)
            or record['source'].get('commit') != COMMIT
            or record.get('source', {}).get('repository') != 'https://github.com/omacom/omarchy'
            or not isinstance(record.get('files'), dict)):
        raise AssetError('Unsupported artwork lock')
    result = []
    seen = set()
    for theme, files in record['files'].items():
        if not isinstance(theme, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', theme) or not isinstance(files, dict):
            raise AssetError('Invalid theme')
        for name, meta in files.items():
            if not isinstance(name, str) or not isinstance(meta, dict):
                raise AssetError('Invalid asset record')
            path = PurePosixPath(name)
            if len(path.parts) != 2 or path.parts[0] not in ('background', 'preview'):
                raise AssetError('Invalid asset path')
            kind, filename = path.parts
            if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', filename)
                    or PurePosixPath(filename).suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp')):
                raise AssetError('Invalid asset filename')
            if kind == 'preview':
                if filename != theme + '.png':
                    raise AssetError('Invalid preview filename')
                source = 'themes/' + theme + '/preview.png'
                target = 'themes-previews/' + filename
            else:
                source = 'themes/' + theme + '/backgrounds/' + filename
                target = 'backgrounds/' + theme + '/' + filename
            if (meta.get('upstream_path') != source or meta.get('url') != PREFIX + source
                    or type(meta.get('bytes')) is not int or not 0 < meta['bytes'] <= MAX_FILE_BYTES
                    or not isinstance(meta.get('blob_sha'), str)
                    or not re.fullmatch(r'[a-f0-9]{40}', meta['blob_sha']) or target in seen):
                raise AssetError('Artwork source or integrity lock differs')
            seen.add(target)
            result.append(dict(meta, target=target))
    if not result or sum(item['bytes'] for item in result) > MAX_TOTAL_BYTES:
        raise AssetError('Artwork set is empty or too large')
    return result


def safe_path(path):
    path = Path(os.path.abspath(path))
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise AssetError('Symlinked artwork path refused')
    return path


def verify(data, item):
    if len(data) != item['bytes']:
        raise AssetError('Artwork length differs: ' + item['target'])
    digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if digest != item['blob_sha']:
        raise AssetError('Artwork hash differs: ' + item['target'])
    return hashlib.sha256(data).hexdigest()


def fetch(item):
    request = urllib.request.Request(item['url'], headers={'User-Agent': 'Omabuntu-Artwork/1.0'})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
        return response.read(item['bytes'] + 1)


def materialize(destination, record, download=False, fetcher=None, cache_roots=()):
    items = entries(record)
    destination = safe_path(destination)
    report = {'downloaded': 0, 'reused': 0, 'missing': [], 'files': {}}
    for item in items:
        target = safe_path(destination / item['target'])
        if target.exists():
            if not target.is_file() or target.stat().st_size != item['bytes']:
                raise AssetError('Local artwork conflict: ' + item['target'])
            try:
                digest = verify(target.read_bytes(), item)
            except AssetError as error:
                raise AssetError('Local artwork conflict: ' + item['target']) from error
            report['reused'] += 1
        elif not download:
            report['missing'].append(item['target'])
            continue
        else:
            data = None
            for cache in cache_roots:
                try:
                    cached = safe_path(Path(cache) / item['target'])
                    if not cached.is_file() or cached.stat().st_size != item['bytes']:
                        continue
                    candidate = cached.read_bytes()
                    verify(candidate, item)
                    data = candidate
                    break
                except (OSError, AssetError):
                    continue
            reused = data is not None
            if data is None:
                data = (fetch if fetcher is None else fetcher)(item)
            digest = verify(data, item)
            target.parent.mkdir(parents=True, exist_ok=True)
            safe_path(target)
            fd, temporary = tempfile.mkstemp(prefix='.omabuntu-asset-', dir=target.parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                # Atomic publication without overwriting a concurrent/local file.
                os.link(temporary, target)
            finally:
                Path(temporary).unlink(missing_ok=True)
            report['reused' if reused else 'downloaded'] += 1
        report['files'][item['target']] = {'sha256': digest, 'bytes': item['bytes']}
    report['ok'] = not report['missing']
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--download', action='store_true')
    mode.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path, help='Private staging/cache directory containing backgrounds and themes-previews')
    args = parser.parse_args(argv)
    if (args.download or args.check) and args.output is None:
        parser.error('--output is required for download/check')
    try:
        record = json.loads(MANIFEST.read_text())
        locked = entries(record)
        if not args.download and not args.check:
            print(json.dumps({'status': 'plan-only', 'files': len(locked),
                              'bytes': sum(item['bytes'] for item in locked), 'notice': NOTICE}))
            return 0
        if args.download:
            print(NOTICE)
        report = materialize(args.output, record, download=args.download)
        print(json.dumps(report, sort_keys=True))
        return 0 if report['ok'] else 1
    except (OSError, ValueError) as error:
        print('Artwork not ready: ' + str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
