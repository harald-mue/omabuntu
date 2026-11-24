"""Artwork admission uses generated images and private temporary caches only."""
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import audio_artwork as art


def png(width=1, height=1):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\0\xff\xff\xff')) + chunk(b'IEND', b''))


class ArtworkTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=ROOT / 'work'); self.addCleanup(temp.cleanup)
        self.home = Path(temp.name); self.cache = self.home / 'cache'; self.cache.mkdir(mode=0o700)
        self.path = self.cache / 'player.png'; self.path.write_bytes(png()); self.path.chmod(0o600)

    def test_generated_png_copies_once_to_private_content_addressed_cache(self):
        url = art.admit(self.path.as_uri(), self.cache)
        target = self.cache / 'omabuntu/audio-art' / (hashlib.sha256(png()).hexdigest() + '.png')
        self.assertEqual(url, target.as_uri()); self.assertEqual(target.read_bytes(), png())
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(target.parent.stat().st_mode & 0o777, 0o700)
        before = target.stat().st_mtime_ns
        self.assertEqual(art.admit(self.path.as_uri(), self.cache), url)
        self.assertEqual(target.stat().st_mtime_ns, before)

    def test_remote_data_credentials_authority_query_fragment_and_parent_urls_refused(self):
        for url in ('https://example.invalid/cover.png', 'http://127.0.0.1/secret', 'data:image/png;base64,AA',
                    'file://localhost' + str(self.path), self.path.as_uri() + '?token=private',
                    self.path.as_uri() + '#fragment', (self.cache / '..' / 'outside.png').as_uri(),
                    (self.cache / '%2e%2e' / 'outside.png').as_uri().replace('%252e', '%2e')):
            with self.subTest(url=url), self.assertRaises(ValueError): art.admit(url, self.cache)
        self.assertFalse((self.cache / 'omabuntu').exists())

    def test_arbitrary_home_image_outside_cache_is_not_read(self):
        other = self.home / 'private.png'; other.write_bytes(png())
        with patch.object(art.os, 'open', wraps=os.open) as opened, self.assertRaises(ValueError):
            art.admit(other.as_uri(), self.cache)
        opened.assert_not_called()

    def test_source_symlink_parent_symlink_and_hardlink_refused(self):
        link = self.cache / 'alias.png'; link.symlink_to(self.path)
        with self.assertRaises((ValueError, OSError)): art.admit(link.as_uri(), self.cache)
        parent = self.cache / 'alias'; parent.symlink_to(self.home, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)): art.admit((parent / 'cache/player.png').as_uri(), self.cache)
        hard = self.cache / 'hard.png'; os.link(self.path, hard)
        with self.assertRaises((ValueError, OSError)): art.admit(hard.as_uri(), self.cache)

    def test_fifo_and_nonprivate_directories_are_not_consumed(self):
        fifo = self.cache / 'fifo'; os.mkfifo(fifo, 0o600)
        with self.assertRaises(ValueError): art.admit(fifo.as_uri(), self.cache)
        self.cache.chmod(0o777)
        with self.assertRaises(ValueError): art.admit(self.path.as_uri(), self.cache)

    def test_oversized_encoded_file_dimensions_bad_crc_and_svg_refused(self):
        for data in (png(2049), png(height=4096), b'<svg width="1" height="1"/>',
                     png()[:29] + b'\0\0\0\0' + png()[33:], b'not an image', b'x' * (art.MAX_BYTES + 1)):
            self.path.write_bytes(data)
            with self.subTest(length=len(data)), self.assertRaises(ValueError): art.admit(self.path.as_uri(), self.cache)
        self.assertFalse((self.cache / 'omabuntu').exists())

    def test_jpeg_header_limits_and_truncation(self):
        jpeg = b'\xff\xd8\xff\xc0' + struct.pack('>HBHHB', 8, 8, 20, 30, 1)
        self.assertEqual(art.dimensions(jpeg), '.jpg')
        for data in (b'\xff\xd8', jpeg[:7], jpeg.replace(b'\x00\x1e', b'\xff\xff'), b'\xff\xd8\xff\xc0\x00\x01'):
            with self.assertRaises(ValueError): art.dimensions(data)

    def test_changed_existing_cache_object_is_never_overwritten(self):
        target = Path(art.admit(self.path.as_uri(), self.cache).removeprefix('file://'))
        target.write_bytes(b'drift')
        with self.assertRaises(ValueError): art.admit(self.path.as_uri(), self.cache)
        self.assertEqual(target.read_bytes(), b'drift')

    def test_cache_entry_quota_has_no_automatic_eviction(self):
        target = self.cache / 'omabuntu/audio-art'; target.mkdir(parents=True, mode=0o700)
        for i in range(64): (target / str(i)).write_bytes(b'x')
        with self.assertRaisesRegex(ValueError, 'artwork-cache-limit'): art.admit(self.path.as_uri(), self.cache)
        self.assertEqual(len(list(target.iterdir())), 64)

    def test_cli_grant_and_malformed_shapes_have_bounded_failure(self):
        for packet in ([], None, {'url': self.path.as_uri()}, {'url': self.path.as_uri(), 'key': True},
                       {'url': self.path.as_uri(), 'key': 1, 'command': 'bad'}):
            output = io.StringIO()
            with patch.object(sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(json.dumps(packet).encode()))), \
                    patch.object(sys, 'stdout', output):
                self.assertEqual(art.main(['--allow-local-artwork']), 1)
            self.assertFalse(json.loads(output.getvalue())['ok'])
        with patch.object(art, 'admit') as admit, patch.object(sys, 'stdout', io.StringIO()), \
                patch.object(sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(b'{}'))):
            self.assertEqual(art.main([]), 1); admit.assert_not_called()


if __name__ == '__main__': unittest.main()
