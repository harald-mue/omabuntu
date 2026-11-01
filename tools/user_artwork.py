#!/usr/bin/env python3
"""Plan and download the pinned Omarchy theme artwork into private user storage.

Public releases ship artwork-free: the upstream stills/previews are not cleared
for redistribution. This stage downloads the pinned set from the recorded
upstream commit into ~/.local/share/omabuntu/artwork so the themes/backgrounds
menus work on a normal installed release. Nothing is redistributed, executed or
installed system-wide; existing conflicting files are never overwritten.

CLI: user_artwork.py [--check] [--download] [--output DIR]
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import download_backgrounds
import install as guided

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'upstream' / 'theme-backgrounds.json'


def artwork_home(data_home=None):
    """Private per-user artwork directory, never symlink-followed."""
    base = Path(data_home) if data_home is not None else Path(
        os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share')
    base = base.absolute()
    if base.is_symlink():
        raise ValueError('Artwork data home is a symlink: ' + str(base))
    return base / 'omabuntu' / 'artwork'


def locked_manifest(root=ROOT):
    path = Path(root) / 'upstream' / 'theme-backgrounds.json'
    record = json.loads(download_backgrounds.safe_path(path).read_text(encoding='utf-8'))
    return download_backgrounds.entries(record), record


def plan(data_home=None, root=ROOT):
    """Read-only completeness report for the private artwork directory."""
    items, record = locked_manifest(root)
    destination = artwork_home(data_home)
    result = download_backgrounds.materialize(destination, record, download=False)
    report = {'schema_version': 1, 'kind': 'omabuntu-user-artwork',
              'root': str(Path(root).absolute()), 'destination': str(destination),
              'source_commit': record['source']['commit'],
              'files': len(items), 'bytes': sum(item['bytes'] for item in items),
              'missing': sorted(result['missing']), 'reused': result['reused'],
              'notice': download_backgrounds.NOTICE,
              'urls': sorted({item['url'] for item in items}),
              'status': 'review-required'}
    report['blockers'] = (['Artwork directory or manifest is unreadable']
                           if destination.is_symlink() else [])
    return report


def apply(reviewed, approval, data_home=None, fetcher=None, root=ROOT):
    if (os.getuid() == 0 or os.environ.get('SUDO_USER')
            or not isinstance(reviewed, dict) or reviewed.get('kind') != 'omabuntu-user-artwork'
            or reviewed.get('schema_version') != 1 or guided.digest(reviewed) != approval):
        raise ValueError('Artwork approval differs or the plan is invalid')
    items, record = locked_manifest(root)
    if (reviewed.get('source_commit') != record['source']['commit']
            or reviewed.get('files') != len(items)
            or reviewed.get('bytes') != sum(item['bytes'] for item in items)
            or sorted(reviewed.get('urls') or []) != sorted({item['url'] for item in items})):
        raise ValueError('Artwork manifest changed; review a new plan')
    destination = artwork_home(data_home)
    if str(destination) != reviewed['destination']:
        raise ValueError('Artwork destination differs; review a new plan')
    if destination.is_symlink():
        raise ValueError('Artwork data home is a symlink')
    report = download_backgrounds.materialize(destination, record, download=True, fetcher=fetcher)
    receipt = {'schema_version': 1, 'kind': 'omabuntu-user-artwork',
                'source_commit': record['source']['commit'],
                'destination': str(destination), 'report': report,
                'notice': download_backgrounds.NOTICE}
    target = destination / 'receipt.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name('.' + target.name + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    target.chmod(0o600)
    report['receipt'] = str(target)
    report['status'] = 'downloaded' if report['downloaded'] else 'reused-complete'
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--download', action='store_true')
    parser.add_argument('--output', type=Path, help='Private artwork directory override')
    args = parser.parse_args(argv)
    try:
        if not (args.check or args.download):
            reviewed = plan(args.output)
            print(json.dumps({'status': reviewed['status'], 'files': reviewed['files'],
                              'bytes': reviewed['bytes'], 'missing': len(reviewed['missing']),
                              'destination': reviewed['destination'],
                              'notice': reviewed['notice']}, indent=2))
            return 0
        if args.check:
            reviewed = plan(args.output)
            print(json.dumps(reviewed, indent=2))
            return 0 if not reviewed['missing'] else 1
        import setup_ui
        reviewed = plan(args.output)
        if reviewed['blockers']:
            print('Artwork blocked: ' + '; '.join(reviewed['blockers']))
            return 1
        if not reviewed['missing']:
            print('Artwork already complete: ' + reviewed['destination'])
            return 0
        print(reviewed['notice'])
        if not setup_ui.confirm('Download the %d missing pinned artwork files into %s?'
                                % (len(reviewed['missing']), reviewed['destination'])):
            print('Cancelled. No artwork download.')
            return 0
        report = apply(reviewed, guided.digest(reviewed), data_home=args.output)
        print(json.dumps(report, sort_keys=True))
        return 0
    except (OSError, ValueError) as error:
        print('Artwork not ready: ' + str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())