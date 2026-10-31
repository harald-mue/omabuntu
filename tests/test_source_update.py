"""Pinned source acquisition: no checkout changes, redirects or execution."""
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import source_update as sources


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class SourceUpdateTests(unittest.TestCase):
    def test_review_lists_exact_pins_without_network_or_checkout_changes(self):
        with patch.object(sources.urllib.request, 'urlopen', side_effect=AssertionError('network')), \
             patch.object(sources.urllib.request, 'build_opener', side_effect=AssertionError('network')):
            reviewed = sources.review(ROOT)
        self.assertFalse(reviewed['checkout_reset'])
        self.assertFalse(reviewed['builds'])
        self.assertFalse(reviewed['publisher_signature'])
        commits = {item['name']: item['commit'] for item in reviewed['sources']}
        self.assertEqual(commits['quickshell'], '2b4501a282689792b62e94f3fb30d8f512324fe6')
        self.assertEqual(commits['omarchy'], '03ff1eff3812933f7088484533784d2f63eaf19a')
        self.assertFalse(next(item['fetch'] for item in reviewed['sources'] if item['name'] == 'omarchy'))
        self.assertTrue(all(item['archive_url'] is None or item['commit'] in item['archive_url'] for item in reviewed['sources']))

    def test_fetch_reuses_matching_cache_and_retains_conflicts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            cache = Path(directory)
            item = next(pin for pin in sources.pins(ROOT) if pin['name'] == 'cpptrace')
            path = cache / (item['name'] + '-' + item['commit'] + '.tar.gz')
            path.write_bytes(b'user cache')
            with self.assertRaisesRegex(ValueError, 'retained'):
                sources.fetch_one(item, cache, None)
            self.assertEqual(path.read_bytes(), b'user cache')

    def test_apply_fetches_only_reviewed_archives_and_never_executes(self):
        reviewed = sources.review(ROOT)
        calls = []
        def fetch_one(item, cache, opener):
            calls.append(item['archive_url'])
            self.assertIn(item['commit'], item['archive_url'])
            return {'name': item['name'], 'status': 'fetched', 'executed': False}
        with patch.object(sources, 'review', return_value=reviewed), \
             patch.object(sources, 'fetch_one', side_effect=fetch_one):
            result = sources.apply(reviewed, sources.guided.digest(reviewed), object())
        self.assertEqual(result['status'], 'archives-verified')
        self.assertFalse(result['checkout_reset'])
        self.assertFalse(result['builds'])
        self.assertEqual(len(calls), 5)
        self.assertNotIn(None, calls)

    def test_fetch_one_publishes_exact_bytes_without_replacing_a_collision(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            cache = Path(directory)
            data = b'pinned-bytes'
            item = {'name': 'fixture', 'commit': 'a' * 40, 'archive_bytes': len(data),
                    'archive_sha256': hashlib.sha256(data).hexdigest(),
                    'archive_url': 'https://codeload.github.com/example/fixture/tar.gz/' + 'a' * 40}
            class Opener:
                def open(self, request, timeout):
                    self.url = request.full_url
                    return FakeResponse(data)
            opener = Opener()
            result = sources.fetch_one(item, cache, opener)
            self.assertEqual(result['status'], 'fetched')
            self.assertEqual(opener.url, item['archive_url'])
            self.assertEqual((cache / ('fixture-' + 'a' * 40 + '.tar.gz')).read_bytes(), data)
            collision = cache / '.download-fixture-collision'
            collision.write_text('keep')
            with patch.object(sources.user_install, 'stamp', return_value='collision'), self.assertRaises(FileExistsError):
                sources.fetch_one(dict(item, commit='b' * 40), cache, opener)
            self.assertEqual(collision.read_text(), 'keep')

    def test_redirects_are_refused(self):
        self.assertIsNone(sources.NoRedirect().redirect_request(None, None, 302, 'moved', {}, 'https://example.invalid'))

    def test_unpinned_archive_shape_is_refused(self):
        with self.assertRaises(ValueError):
            sources.archive_pin({'name': 'latest', 'repository': 'https://github.com/example/demo',
                                 'commit': 'main', 'archive_url': 'https://example.invalid/latest',
                                 'archive_root': 'demo-main', 'archive_bytes': 1, 'archive_sha256': 'a' * 64})
