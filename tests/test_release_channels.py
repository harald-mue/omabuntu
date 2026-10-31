"""Channel pins resolve local releases and never download or publish."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import release_channels as channels
import release_update
import user_install


def bundle(parent, version, text='fixture'):
    directory = parent / version
    directory.mkdir(parents=True)
    for name in user_install.INCOMING:
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + ' ' + name)
        path.chmod(0o755 if name == 'runtime/bin/quickshell' else 0o444)
    meta = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': version,
            'autostart': False, 'lock_activation': False,
            'update_contract': release_update.contract(), 'files': user_install.file_manifest(directory)}
    (directory / 'release.json').write_text(json.dumps(meta))
    return directory


class ChannelTests(unittest.TestCase):
    def test_pin_resolves_exact_release_and_refuses_mismatch(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            base = Path(directory)
            built = bundle(base / 'bundles', 'dev-1')
            record = channels.from_bundle('dev', built)
            path = base / 'channels.json'
            channels.write(path, record)
            resolved = channels.resolve(path, 'dev', base / 'bundles')
            self.assertEqual(resolved['version'], 'dev-1')
            self.assertFalse(resolved['downloaded'])
            self.assertFalse(resolved['published'])
            self.assertFalse(resolved['publisher_signature'])
            (built / 'manager.py').chmod(0o644)
            (built / 'manager.py').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'does not match|differs'):
                channels.resolve(path, 'dev', base / 'bundles')

    def test_channel_file_cannot_claim_a_signature_or_embed_a_url(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            path = Path(directory) / 'channels.json'
            path.write_text(json.dumps({'schema_version': 1, 'kind': 'omabuntu-release-channels',
                                        'publisher_signature': True, 'artwork_included': False,
                                        'channels': {'stable': {'version': 'v1', 'bundle_sha256': 'a' * 64}}}))
            with self.assertRaisesRegex(ValueError, 'signature'):
                channels.load(path)

    def test_symlink_and_unknown_channel_are_refused(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            base = Path(directory)
            target = base / 'real.json'
            target.write_text('{}')
            link = base / 'link.json'
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'Unsafe channel file'):
                channels.load(link)
            with self.assertRaisesRegex(ValueError, 'Unknown channel'):
                channels.from_bundle('latest', base)

    def test_replace_keeps_the_other_channel(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            base = Path(directory)
            first = bundle(base / 'bundles', 'stable-1', 'one')
            second = bundle(base / 'bundles', 'dev-1', 'two')
            path = base / 'channels.json'
            channels.write(path, channels.from_bundle('stable', first))
            updated = channels.from_bundle('dev', second, path)
            channels.write(path, updated, replace=True)
            data = channels.load(path)
            self.assertEqual(set(data['channels']), {'stable', 'dev'})
            self.assertFalse(data['artwork_included'])
