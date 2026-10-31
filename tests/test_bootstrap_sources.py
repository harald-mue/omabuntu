"""PPA key/signature/source safety tests; no network, sudo or real APT writes."""
import copy
import datetime
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bootstrap_sources as sources
import install as guided

KEY_LISTING = ('pub:-:4096:1:KEY:1604493618:::-:::scSC:\n'
               'fpr:::::::::' + sources.FINGERPRINT + ':\n')
RELEASE = b'''-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Origin: LP-PPA-cppiber-hyprland
Suite: resolute
Codename: resolute
Date: Wed, 28 Oct 2026 19:08:42 UTC
Architectures: amd64 arm64
Components: main
-----BEGIN PGP SIGNATURE-----
fixture
'''


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.apt = self.base / 'apt'
        self.case = self.base / 'case'

    def download(self, url, limit):
        if url == sources.API:
            return json.dumps({'reference': sources.REFERENCE, 'private': False,
                               'signing_key_fingerprint': sources.FINGERPRINT}).encode()
        if 'keyserver.ubuntu.com' in url:
            return b'fixture key'
        return RELEASE

    def gpg(self, command, data=None):
        if '--show-keys' in command:
            return KEY_LISTING.encode()
        if '--dearmor' in command:
            return b'binary key'
        return b''

    def prepare(self):
        return sources.prepare(self.case, self.apt, self.download, self.gpg, check_host=lambda: None)

    def test_prepare_is_private_and_verifies_without_system_apply(self):
        with patch.object(sources.subprocess, 'run') as execute:
            plan = self.prepare()
        execute.assert_not_called()
        self.assertFalse(self.apt.exists())
        self.assertFalse(plan['blockers'])
        self.assertEqual(plan['verified']['fingerprint'], sources.FINGERPRINT)
        text = plan['source']
        self.assertIn('Signed-By: /etc/apt/keyrings/omabuntu-hyprland.gpg', text)
        self.assertNotIn('trusted=yes', text)

    def test_wrong_multiple_or_expired_key_is_refused(self):
        for listing in (KEY_LISTING.replace(sources.FINGERPRINT, 'A' * 40),
                        KEY_LISTING + KEY_LISTING, KEY_LISTING.replace('pub:-:', 'pub:r:'),
                        KEY_LISTING.replace('1604493618:::', '1604493618:1::')):
            with self.subTest(listing=listing), self.assertRaises(sources.SourceError):
                sources.validate_key_listing(listing)

    def test_key_or_signature_failure_stops_preparation(self):
        def failed(command, data=None):
            if command[0] == '/usr/bin/gpgv':
                raise sources.SourceError('bad signature')
            return self.gpg(command, data)
        with self.assertRaises(sources.SourceError):
            sources.prepare(self.case, self.apt, self.download, failed, check_host=lambda: None)
        self.assertFalse(self.apt.exists())

    def test_wrong_signed_suite_and_expired_metadata_are_refused(self):
        for release in (RELEASE.replace(b'Codename: resolute', b'Codename: noble'),
                        RELEASE.replace(b'Architectures: amd64 arm64', b'Architectures: arm64'),
                        RELEASE.replace(b'Date:', b'Valid-Until: Wed, 01 Jan 2020 00:00:00 UTC\nDate:')):
            with self.subTest(release=release[:80]), self.assertRaises(sources.SourceError):
                sources.validate_release(release, now=datetime.datetime(2026, 10, 29, tzinfo=datetime.timezone.utc))

    def test_redirects_are_rejected(self):
        with self.assertRaises(sources.SourceError):
            sources.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.org')

    def test_unmanaged_duplicate_is_blocked(self):
        directory = self.apt / 'sources.list.d'
        directory.mkdir(parents=True)
        (directory / 'existing.list').write_text('deb http://ppa.launchpad.net/cppiber/hyprland/ubuntu resolute main\n')
        plan = self.prepare()
        self.assertTrue(plan['blockers'])
        self.assertEqual(len(plan['duplicates']), 1)

    def test_local_conflicting_managed_file_is_preserved(self):
        target = self.apt / 'sources.list.d' / sources.SOURCE_NAME
        target.parent.mkdir(parents=True)
        target.write_text('my existing source')
        self.assertTrue(self.prepare()['blockers'])
        self.assertEqual(target.read_text(), 'my existing source')

    def test_symlinked_source_path_is_rejected(self):
        directory = self.apt / 'sources.list.d'
        directory.mkdir(parents=True)
        (directory / sources.SOURCE_NAME).symlink_to(self.base / 'elsewhere')
        with self.assertRaises(ValueError):
            self.prepare()

    def system_apply(self, plan, execute):
        plan = copy.deepcopy(plan)
        plan['apt_root'] = '/etc/apt'
        paths = sources.destinations(self.apt)
        with patch.object(sources, 'destinations', return_value=paths), \
             patch.object(sources, 'conflicts', return_value=[]):
            return sources.apply(plan, guided.digest(plan), execute=execute,
                                 check_host=lambda: None, verify=lambda case: plan['verified'])

    def executor(self, commands, fail_update=False):
        def execute(command):
            commands.append(command)
            if command[:3] == ['sudo', 'apt-get', 'update']:
                return 1 if fail_update else 0
            if '-d' in command:
                Path(command[-1]).mkdir(parents=True, exist_ok=True)
            else:
                shutil.copyfile(command[-2], command[-1])
                Path(command[-1]).chmod(0o644)
            return 0
        return execute

    def test_apply_uses_scoped_install_and_metadata_update_not_package_install(self):
        plan = self.prepare()
        commands = []
        result = self.system_apply(plan, self.executor(commands))
        self.assertEqual(result['status'], 'source-installed-metadata-refreshed')
        self.assertEqual(commands[-1], ['sudo', 'apt-get', 'update'])
        self.assertTrue(all(command[:2] == ['sudo', 'install'] for command in commands[:-1]))
        self.assertFalse(result['packages_installed'])

    def test_failed_refresh_keeps_journal_without_deleting_sources(self):
        plan = self.prepare()
        commands = []
        with self.assertRaises(sources.SourceError):
            self.system_apply(plan, self.executor(commands, fail_update=True))
        journal = json.loads((self.case / 'apply.json').read_text())
        self.assertEqual(journal['status'], 'incomplete-review-required')
        self.assertTrue((self.apt / 'sources.list.d' / sources.SOURCE_NAME).is_file())
        self.assertFalse(any('rm' in command for command in commands))

    def test_source_drift_after_review_blocks_before_sudo(self):
        plan = self.prepare()
        target = self.apt / 'sources.list.d' / sources.SOURCE_NAME
        target.parent.mkdir(parents=True)
        target.write_text('other administrator edit')
        with self.assertRaises(sources.SourceError):
            self.system_apply(plan, lambda _: self.fail('Unexpected sudo'))
        self.assertEqual(target.read_text(), 'other administrator edit')

    def test_symlinked_unmanaged_source_requires_review(self):
        directory = self.apt / 'sources.list.d'
        directory.mkdir(parents=True)
        target = self.base / 'real.list'
        target.write_text('deb https://example.org stable main')
        (directory / 'managed-elsewhere.list').symlink_to(target)
        with self.assertRaises(sources.SourceError):
            self.prepare()

    def test_changed_approval_is_refused_before_sudo(self):
        plan = self.prepare()
        with patch.object(sources, 'host_check'), self.assertRaises(sources.SourceError):
            sources.apply(plan, 'wrong', execute=lambda _: self.fail('sudo'))
