"""Locked artwork cache contracts; never access the network or desktop."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import download_backgrounds as assets


def fixture(data=b'image fixture'):
    source = 'themes/test/backgrounds/one.webp'
    return {'schema_version': 1,
            'source': {'repository': 'https://github.com/omacom/omarchy', 'commit': assets.COMMIT},
            'files': {'test': {'background/one.webp': {
                'upstream_path': source, 'url': assets.PREFIX + source, 'bytes': len(data),
                'blob_sha': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}}}}


class ArtworkDownloadTests(unittest.TestCase):
    def test_committed_manifest_validates_without_network(self):
        locked = assets.entries(json.loads(assets.MANIFEST.read_text()))
        self.assertEqual(len(locked), 120)
        self.assertEqual(sum(item['bytes'] for item in locked), 64913495)

    def test_default_is_plan_only(self):
        with patch.object(assets, 'fetch') as fetch, patch('builtins.print'):
            self.assertEqual(assets.main([]), 0)
            fetch.assert_not_called()

    def test_offline_check_does_not_create_or_download(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'absent'
            report = assets.materialize(target, fixture(), fetcher=lambda _: self.fail('network'))
            self.assertFalse(report['ok'])
            self.assertEqual(report['missing'], ['backgrounds/test/one.webp'])
            self.assertFalse(target.exists())

    def test_download_verifies_and_reuses_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            record = fixture()
            before = copy.deepcopy(record)
            report = assets.materialize(directory, record, True, lambda _: b'image fixture')
            self.assertTrue(report['ok'])
            self.assertEqual(report['downloaded'], 1)
            reused = assets.materialize(directory, record, True, lambda _: self.fail('redownload'))
            self.assertEqual(reused['reused'], 1)
            self.assertEqual(record, before)
            self.assertEqual(report['files']['backgrounds/test/one.webp']['sha256'],
                             hashlib.sha256(b'image fixture').hexdigest())

    def test_update_reuses_verified_old_cache_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path(directory) / 'old'
            new = Path(directory) / 'new'
            assets.materialize(old, fixture(), True, lambda _: b'image fixture')
            report = assets.materialize(new, fixture(), True, lambda _: self.fail('redownload'), cache_roots=[old])
            self.assertTrue(report['ok'])
            self.assertEqual(report['reused'], 1)
            self.assertEqual(report['downloaded'], 0)
            self.assertEqual((old / 'backgrounds/test/one.webp').read_bytes(), b'image fixture')

    def test_invalid_old_cache_is_not_copied_or_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path(directory) / 'old/backgrounds/test'
            old.mkdir(parents=True)
            (old / 'one.webp').write_bytes(b'modified data')
            report = assets.materialize(Path(directory) / 'new', fixture(), True,
                                        lambda _: b'image fixture', cache_roots=[old.parents[1]])
            self.assertEqual(report['downloaded'], 1)
            self.assertEqual((old / 'one.webp').read_bytes(), b'modified data')

    def test_bad_download_never_installs_a_file(self):
        for data in (b'bad', b'x' * 13, b'image fixturex'):
            with self.subTest(data=data), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(assets.AssetError):
                    assets.materialize(directory, fixture(), True, lambda _: data)
                self.assertFalse((Path(directory) / 'backgrounds').exists())

    def test_modified_and_personal_images_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'backgrounds/test/one.webp'
            target.parent.mkdir(parents=True)
            target.write_bytes(b'personal file')
            extra = target.with_name('my-image.webp')
            extra.write_bytes(b'my image')
            with self.assertRaisesRegex(assets.AssetError, 'Local artwork conflict'):
                assets.materialize(directory, fixture(), True, lambda _: self.fail('download'))
            self.assertEqual(target.read_bytes(), b'personal file')
            self.assertEqual(extra.read_bytes(), b'my image')

    def test_unsafe_source_and_target_are_rejected(self):
        for field, value in [('url', 'https://example.org/image'), ('upstream_path', '../../escape'),
                             ('bytes', assets.MAX_FILE_BYTES + 1), ('blob_sha', 'bad')]:
            record = fixture()
            record['files']['test']['background/one.webp'][field] = value
            with self.subTest(field=field), self.assertRaises(assets.AssetError):
                assets.entries(record)
        record = fixture()
        record['files']['../escape'] = record['files'].pop('test')
        with self.assertRaises(assets.AssetError):
            assets.entries(record)

    def test_symlinked_destination_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'real').mkdir()
            (root / 'link').symlink_to(root / 'real', target_is_directory=True)
            with self.assertRaises(assets.AssetError):
                assets.materialize(root / 'link', fixture(), True)

    def test_redirect_is_refused(self):
        with self.assertRaises(assets.AssetError):
            assets.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.org')

    def test_interrupted_download_can_be_retried_without_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(TimeoutError):
                assets.materialize(directory, fixture(), True,
                                   lambda _: (_ for _ in ()).throw(TimeoutError()))
            report = assets.materialize(directory, fixture(), True, lambda _: b'image fixture')
            self.assertTrue(report['ok'])
            self.assertEqual(len(list(Path(directory).rglob('*.webp'))), 1)


if __name__ == '__main__':
    unittest.main()
