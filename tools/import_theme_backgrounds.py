#!/usr/bin/env python3
"""Import upstream theme background stills and preview images as data.

Omarchy's pinned commit 03ff1eff ships, per theme, `backgrounds/` stills
and a `preview.png` (the theme picker preview; `find_preview` in
`omarchy-theme-switcher` uses it, falling back to the first backgrounds
image). This tool downloads those image assets read-only into the repo:

  config/menu/backgrounds/<theme>/<file>   still wallpapers
  config/menu/themes-previews/<theme>.png   picker previews

and records provenance (per-file git blob SHA, size, raw URL) in
upstream/theme-backgrounds.json. License caveat, recorded in the file: the
upstream repository declares only its root MIT license; the individual
images carry no per-file license upstream. Import stays local; publication
stays behind the project's publication gate.

Excluded: `backgrounds/intros/` videos and every video/animated suffix
(96 MB of intros; no wallpaper engine is ported), `preview-unlock.png`
and `unlock.png` (lock-screen art, out of scope), and every upstream
script (none is imported or executed).

CLI: import_theme_backgrounds.py [--check] [--theme <id>]
--check verifies existing files against the recorded provenance without
downloading. The pinned upstream tree is always fetched through the
GitHub API; existing verified files are never re-downloaded.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/omacom/omarchy'
COMMIT = '03ff1eff3812933f7088484533784d2f63eaf19a'
API = 'https://api.github.com/repos/omacom/omarchy'
RAW = 'https://raw.githubusercontent.com/omacom/omarchy/%s' % COMMIT
RECORD = ROOT / 'upstream' / 'theme-backgrounds.json'
BACKGROUNDS = ROOT / 'config' / 'menu' / 'backgrounds'
PREVIEWS = ROOT / 'config' / 'menu' / 'themes-previews'
MAX_FILE_BYTES = 64 * 1024 * 1024
STILL_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}
VIDEO_SUFFIXES = {'.mp4', '.m4v', '.mov', '.webm', '.mkv', '.avi', '.gif'}


def git_blob_sha(data):
    digest = hashlib.sha1()
    digest.update(b'blob %d\x00' % len(data))
    digest.update(data)
    return digest.hexdigest()


def fetch(url, as_json=False, timeout=30):
    request = urllib.request.Request(url, headers={'User-Agent': 'omabuntu-import'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
    return json.loads(payload) if as_json else payload


def theme_tree(timeout=30):
    """The pinned themes subtree: {theme: {relative path: {size, sha}}}."""
    root = fetch('%s/git/trees/%s' % (API, COMMIT), as_json=True, timeout=timeout)
    themes_sha = next(entry['sha'] for entry in root['tree'] if entry['path'] == 'themes')
    tree = fetch('%s/git/trees/%s?recursive=1' % (API, themes_sha), as_json=True, timeout=timeout)
    if tree.get('truncated'):
        raise RuntimeError('themes subtree listing was truncated upstream')
    result = {}
    for entry in tree['tree']:
        parts = entry['path'].split('/')
        if entry['type'] != 'blob' or len(parts) < 2:
            continue
        theme, name = parts[0], parts[-1]
        result.setdefault(theme, {})[entry['path']] = {
            'name': name, 'size': entry.get('size'), 'sha': entry.get('sha'),
        }
    return result


def wanted_files(tree, theme_id=None):
    """Still backgrounds and preview.png per theme, in stable order."""
    files = []
    for theme in sorted(tree):
        if theme_id is not None and theme != theme_id:
            continue
        for path, meta in sorted(tree[theme].items()):
            parts = path.split('/')
            if len(parts) == 2 and parts[1] == 'preview.png':
                files.append((theme, 'preview', path, meta))
            elif len(parts) == 3 and parts[1] == 'backgrounds' and parts[2] != 'intros':
                suffix = Path(meta['name']).suffix.lower()
                if suffix in STILL_SUFFIXES:
                    files.append((theme, 'background', path, meta))
                elif suffix in VIDEO_SUFFIXES:
                    continue
    return files


def target_path(kind, theme, upstream_path):
    if kind == 'preview':
        return PREVIEWS / ('%s.png' % theme)
    return BACKGROUNDS / theme / Path(upstream_path).name


def verify_file(path, meta):
    if path.is_symlink() or not path.is_file():
        return False
    data = path.read_bytes()
    if len(data) != meta['size'] or git_blob_sha(data) != meta['sha']:
        return False
    return True


def import_files(files, record, only_theme=None):
    imported = 0
    entries = record.setdefault('files', {})
    for theme, kind, path, meta in files:
        if only_theme is not None and theme != only_theme:
            continue
        if meta['size'] is None or meta['size'] > MAX_FILE_BYTES:
            raise RuntimeError('refusing oversized or unsized upstream file: %s' % path)
        target = target_path(kind, theme, path)
        if verify_file(target, meta):
            data = target.read_bytes()
        else:
            url = '%s/themes/%s' % (RAW, path)
            data = fetch(url)
            if len(data) != meta['size'] or git_blob_sha(data) != meta['sha']:
                raise RuntimeError('downloaded bytes do not match the pinned blob: %s' % path)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + '.part')
            temporary.write_bytes(data)
            temporary.replace(target)
            imported += 1
            time.sleep(0.05)
        theme_entry = entries.setdefault(theme, {})
        theme_entry['%s/%s' % (kind, target.name)] = {
            'upstream_path': 'themes/%s' % path,
            'bytes': meta['size'],
            'blob_sha': meta['sha'],
            'url': '%s/themes/%s' % (RAW, path),
        }
    return imported


def fresh_record():
    return {
        'schema_version': 1,
        'status': 'image-assets-imported-local-license-caveat',
        'source': {
            'repository': REPOSITORY,
            'commit': COMMIT,
            'license': 'Upstream declares only the root MIT license; the individual images carry no per-file license upstream. Local import only; publication stays behind the project publication gate.',
            'note': 'Still backgrounds and preview.png only. Videos, backgrounds/intros, unlock.png, and preview-unlock.png are not imported. No upstream script is imported or executed.',
        },
        'files': {},
    }


def load_record():
    if RECORD.is_symlink() or not RECORD.is_file():
        return fresh_record()
    try:
        payload = json.loads(RECORD.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fresh_record()
    if not isinstance(payload, dict) or payload.get('schema_version') != 1 \
            or payload.get('source', {}).get('commit') != COMMIT:
        return fresh_record()
    return payload


def check_files(files, record):
    """Verify every recorded file on disk against the pinned blobs."""
    failures = []
    expected = {}
    for theme, kind, path, meta in files:
        expected[target_path(kind, theme, path).as_posix()] = (theme, kind, path, meta)
    for target, (theme, kind, path, meta) in sorted(expected.items()):
        if not verify_file(Path(target), meta):
            failures.append(target)
    if failures:
        print(json.dumps({'ok': False, 'mismatched': failures[:20], 'count': len(failures)}))
        return 1
    print(json.dumps({'ok': True, 'verified': len(expected)}))
    return 0


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--theme')
    args = parser.parse_args(argv)
    tree = theme_tree()
    files = wanted_files(tree, args.theme)
    record = load_record()
    if args.check:
        return check_files(files, record)
    imported = import_files(files, record, args.theme)
    record['generated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    total = sum(len(themes) for themes in record['files'].values())
    print(json.dumps({'ok': True, 'downloaded': imported, 'recorded': total}))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
