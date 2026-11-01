"""User artwork stays private, pinned and never overwrites conflicts."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import download_backgrounds
import install as guided
import user_artwork


def fake_manifest(tmp):
    """Two tiny valid files with correct git blob hashes."""
    data = {'backgrounds/tokyo/0-still.webp': b'fixture-artwork-bytes',
            'themes-previews/tokyo.png': b'fixture-preview'}
    files = {}
    for target, payload in data.items():
        source = ('themes/tokyo/preview.png' if target.startswith('themes-previews')
                  else 'themes/tokyo/backgrounds/0-still.webp')
        key = ('preview/tokyo.png' if target.startswith('themes-previews')
               else 'background/0-still.webp')
        blob = download_backgrounds.hashlib.sha1(
            b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
        files[key] = {'upstream_path': source, 'url': download_backgrounds.PREFIX + source,
                      'bytes': len(payload), 'blob_sha': blob, 'sha256': None}
    record = {'schema_version': 1,
              'source': {'repository': 'https://github.com/omacom/omarchy',
                         'commit': download_backgrounds.COMMIT},
              'files': {'tokyo': files}}
    path = tmp / 'upstream' / 'theme-backgrounds.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(record))
    return {'data': data, 'root': path.parents[1]}


class UserArtworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.fixture = fake_manifest(self.base / 'source')
        self.data = self.base / 'data'
        patch.dict(os.environ, {'XDG_DATA_HOME': str(self.data)}).start()
        self.addCleanup(patch.stopall)

    def plan(self, root=None):
        return user_artwork.plan(data_home=self.data, root=root or self.fixture['root'])

    def apply(self, reviewed, fetcher=None, root=None, approval=None, progress=None):
        return user_artwork.apply(reviewed, approval or guided.digest(reviewed),
                                   data_home=self.data, fetcher=fetcher,
                                   root=root or self.fixture['root'], progress=progress)

    def test_plan_is_read_only_and_reports_missing_files(self):
        before = sorted(str(p) for p in self.base.rglob('*'))
        reviewed = self.plan()
        self.assertEqual(reviewed['status'], 'review-required')
        self.assertEqual(len(reviewed['missing']), 2)
        self.assertEqual(reviewed['reused'], 0)
        self.assertFalse(reviewed['blockers'])
        self.assertEqual(sorted(str(p) for p in self.base.rglob('*')), before)

    def test_apply_downloads_verified_bytes_atomically_with_receipt(self):
        fetches = []
        seen = []

        def fetcher(item):
            fetches.append(item['url'])
            return next(data for key, data in self.fixture['data'].items() if item['target'] == key)

        def progress(position, total, item):
            seen.append((position, total, item['target']))
        reviewed = self.plan()
        report = self.apply(reviewed, fetcher, progress=progress)
        self.assertEqual(report['downloaded'], 2)
        self.assertEqual(fetches, sorted(fetches))
        self.assertEqual(sorted(seen), [(1, 2, 'backgrounds/tokyo/0-still.webp'),
                                         (2, 2, 'themes-previews/tokyo.png')])
        still = self.data / 'omabuntu/artwork/backgrounds/tokyo/0-still.webp'
        self.assertEqual(still.read_bytes(), b'fixture-artwork-bytes')
        receipt = json.loads((self.data / 'omabuntu/artwork/receipt.json').read_text())
        self.assertEqual(receipt['source_commit'], download_backgrounds.COMMIT)
        self.assertEqual(receipt['report']['files']['backgrounds/tokyo/0-still.webp']['bytes'], 21)
        self.assertEqual((self.data / 'omabuntu/artwork/receipt.json').stat().st_mode & 0o777, 0o600)
        self.assertFalse(self.plan()['missing'])
        self.assertEqual(self.plan()['reused'], 2)

    def test_wrong_digest_changed_manifest_or_destination_is_refused(self):
        reviewed = self.plan()
        with self.assertRaisesRegex(ValueError, 'approval differs'):
            user_artwork.apply(reviewed, 'wrong', data_home=self.data,
                               fetcher=lambda item: b'', root=self.fixture['root'])
        with self.assertRaisesRegex(ValueError, 'destination differs'):
            user_artwork.apply(reviewed, guided.digest(reviewed), data_home=self.base / 'other',
                               fetcher=lambda item: b'x', root=self.fixture['root'])
        changed = json.loads(Path(self.fixture['root'] / 'upstream/theme-backgrounds.json').read_text())
        changed['files']['tokyo']['background/0-still.webp']['bytes'] = 3
        Path(self.fixture['root'] / 'upstream/theme-backgrounds.json').write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, 'manifest changed'):
            self.apply(reviewed, lambda item: b'x')

    def test_conflicting_existing_file_blocks_instead_of_overwriting(self):
        conflict = self.data / 'omabuntu/artwork/backgrounds/tokyo/0-still.webp'
        conflict.parent.mkdir(parents=True)
        conflict.write_bytes(b'user file')
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.plan()
        self.assertEqual(conflict.read_bytes(), b'user file')

    def test_bad_bytes_wrong_hash_or_redirect_never_lands(self):
        reviewed = self.plan()
        with self.assertRaisesRegex(ValueError, 'hash differs|length differs'):
            self.apply(reviewed, lambda item: b'evil')
        self.assertFalse((self.data / 'omabuntu/artwork/backgrounds').exists())

    def test_cli_plan_and_check_modes_never_download(self):
        with patch.object(sys, 'argv', ['user_artwork']), patch('builtins.print') as out:
            self.assertEqual(user_artwork.main(), 0)
        self.assertIn('missing', json.dumps([c.args[0] for c in out.call_args_list]))
        with patch.object(sys, 'argv', ['user_artwork', '--check']), patch('builtins.print'):
            self.assertEqual(user_artwork.main(), 1)


if __name__ == '__main__':
    unittest.main()