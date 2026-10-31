"""Public release transport tests: no network, publication or live deployment."""
import builtins
import hashlib
import io
import json
import os
import pty
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import download_release as download
import publish_release as publish
import published_install
import release_archive


class ReleaseCommandRunnerTests(unittest.TestCase):
    def test_git_and_github_output_bypass_personal_pagers_without_changing_parent(self):
        settings = {'GIT_PAGER': 'less', 'GH_PAGER': 'more', 'PAGER': 'less -R',
                    'OMABUNTU_TEST_ENV': 'preserved'}
        with patch.dict(os.environ, settings):
            before = dict(os.environ)
            for command in (('git', 'diff', '--stat'), ('gh', 'release', 'list')):
                with self.subTest(command=command), patch.object(publish.subprocess, 'run',
                        return_value=subprocess.CompletedProcess(command, 0, stdout='fixture')) as run:
                    self.assertEqual(publish.run(*command), 'fixture')
                    environment = run.call_args.kwargs['env']
                    for name in ('GIT_PAGER', 'GH_PAGER', 'PAGER'):
                        self.assertEqual(environment[name], 'cat')
                    self.assertEqual(environment['OMABUNTU_TEST_ENV'], 'preserved')
                    self.assertEqual(dict(os.environ), before)

    def test_capture_and_untimed_interactive_operations_remain_supported(self):
        with patch.object(publish.subprocess, 'run',
                          return_value=subprocess.CompletedProcess([], 0, stdout='fixture')) as run:
            publish.run('ssh-keygen', '-y', capture=True, timeout=None)
            self.assertEqual(run.call_args.kwargs['stdout'], subprocess.PIPE)
            self.assertIsNone(run.call_args.kwargs['timeout'])


class TerminalConfirmationTests(unittest.TestCase):
    def confirm_with_reply(self, reply):
        master, slave = pty.openpty()
        modes = []
        def terminal_open(path, mode):
            self.assertEqual(path, '/dev/tty')
            modes.append(mode)
            return builtins.open(os.dup(slave), mode)
        try:
            os.write(master, reply)
            with patch.object(publish, 'open', side_effect=terminal_open):
                publish.confirm('Publish fixture?')
            self.assertEqual(modes, ['w', 'r'])
        finally:
            os.close(master)
            os.close(slave)

    def test_yes_works_with_a_real_nonseekable_terminal(self):
        self.confirm_with_reply(b'yes\n')

    def test_other_answers_cancel_with_a_real_terminal(self):
        for reply in (b'no\n', b'\n', b'y\n'):
            with self.subTest(reply=reply), self.assertRaisesRegex(ValueError, 'Cancelled'):
                self.confirm_with_reply(reply)


class ArchiveTests(unittest.TestCase):
    def archive(self, base, entries):
        archive = base / 'test.tar.gz'
        with tarfile.open(archive, 'w:gz') as stream:
            for name, kind, value in entries:
                item = tarfile.TarInfo(name)
                if kind == 'file':
                    data = value.encode()
                    item.size = len(data)
                    stream.addfile(item, io.BytesIO(data))
                else:
                    item.type = tarfile.SYMTYPE if kind == 'link' else tarfile.FIFOTYPE
                    item.linkname = value
                    stream.addfile(item)
        return archive

    def test_runtime_alias_and_files_extract(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            archive = self.archive(base, [('bundle/runtime/bin/quickshell', 'file', 'binary'),
                                          ('bundle/runtime/bin/qs', 'link', 'quickshell')])
            release_archive.extract(archive, base / 'out')
            self.assertEqual((base / 'out/bundle/runtime/bin/qs').read_text(), 'binary')

    def test_unsafe_entries_rejected_before_creating_destination(self):
        for entry in (('../outside', 'file', 'x'), ('/absolute', 'file', 'x'),
                      ('source/link', 'link', '/etc'), ('fifo', 'fifo', ''),
                      ('bundle/runtime/bin/qs', 'link', '/etc/passwd')):
            with self.subTest(entry=entry), tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                archive = self.archive(base, [entry])
                with self.assertRaises(ValueError):
                    release_archive.extract(archive, base / 'out')
                self.assertFalse((base / 'out').exists())

    def test_readonly_and_executable_file_modes_survive_transport(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            archive = base / 'modes.tar'
            with tarfile.open(archive, 'w') as stream:
                for name, mode in (('bundle/readonly', 0o444), ('bundle/executable', 0o755)):
                    item = tarfile.TarInfo(name)
                    item.mode = mode
                    item.size = 1
                    stream.addfile(item, io.BytesIO(b'x'))
            release_archive.extract(archive, base / 'out')
            self.assertEqual((base / 'out/bundle/readonly').stat().st_mode & 0o777, 0o444)
            self.assertEqual((base / 'out/bundle/executable').stat().st_mode & 0o777, 0o755)

    def test_paths_below_the_runtime_alias_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            archive = self.archive(base, [('bundle/runtime/bin/qs', 'link', 'quickshell'),
                                          ('bundle/runtime/bin/qs/extra', 'file', 'x')])
            with self.assertRaises(ValueError):
                release_archive.extract(archive, base / 'out')
            self.assertFalse((base / 'out').exists())

    def test_duplicate_paths_and_size_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            archive = self.archive(base, [('same', 'file', 'x'), ('same', 'file', 'y')])
            with self.assertRaises(ValueError):
                release_archive.extract(archive, base / 'out')
            archive = self.archive(base, [('large', 'file', 'too much')])
            with patch.object(release_archive, 'MAX_BYTES', 2), self.assertRaises(ValueError):
                release_archive.extract(archive, base / 'out')


class DownloadTests(unittest.TestCase):
    def test_checksum_parser_rejects_paths_duplicates_and_bad_hashes(self):
        digest = 'a' * 64
        self.assertEqual(download.checksums(digest + '  archive.tar.gz\n'), {'archive.tar.gz': digest})
        for text in ('oops', digest + '  ../bad', (digest + '  same\n') * 2):
            with self.assertRaises(ValueError):
                download.checksums(text)

    def test_redirects_reject_insecure_or_foreign_targets(self):
        handler = download.HTTPSRedirects()
        for url in ('http://github.com/test', 'https://example.com/test'):
            with self.assertRaises(ValueError):
                handler.redirect_request(None, None, 302, '', {}, url)

    def test_fetch_rejects_non_release_origins_before_network(self):
        for url in ('file:///tmp/a', 'http://github.com/a', 'https://example.com/a'):
            with self.assertRaises(ValueError):
                download.fetch(url, Path('unused'), 10)

    @unittest.skipUnless(shutil.which('ssh-keygen'), 'OpenSSH SSH signing required')
    def test_real_signature_accepts_only_matching_key_and_unchanged_checksums(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            key = base / 'fixture-key'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True)
            sums = base / 'SHA256SUMS'
            sums.write_text('a' * 64 + '  fixture.tar.gz\n')
            subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n',
                            'omabuntu-release', str(sums)], check=True, capture_output=True)
            signature = Path(str(sums) + '.sig')
            download.verify(Path(str(key) + '.pub'), sums, signature, base)
            sums.write_text('b' * 64 + '  fixture.tar.gz\n')
            with self.assertRaises(subprocess.CalledProcessError):
                download.verify(Path(str(key) + '.pub'), sums, signature, base)

    def test_download_verifies_before_extract_or_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            archive = b'not executed'
            name = publish.artifact_name('0.1.0')
            meta = json.dumps({'version': '0.1.0', 'archive': name,
                               'target': 'ubuntu-26.04-x86_64', 'bytes': len(archive),
                               'sha256': hashlib.sha256(archive).hexdigest()}).encode()
            assets = {name: archive, 'release.json': meta}
            assets['SHA256SUMS'] = ''.join(hashlib.sha256(data).hexdigest() + '  ' + item + '\n'
                                          for item, data in assets.items()).encode()
            assets['SHA256SUMS.sig'] = b'signature'
            assets['latest'] = json.dumps({'tag_name': 'v0.1.0'}).encode()
            def fetch(url, path, limit):
                path.write_bytes(assets[url.rsplit('/', 1)[-1]])
            with patch.object(sys, 'argv', ['download', '--public-key', str(base / 'key')]), \
                 patch.object(download.os, 'getuid', return_value=1000), \
                 patch.object(download.platform, 'machine', return_value='x86_64'), \
                 patch.object(Path, 'read_text', autospec=True, side_effect=lambda p, **kw:
                              'ID=ubuntu\nVERSION_ID="26.04"\n' if str(p) == '/etc/os-release'
                              else p.read_bytes().decode()), \
                 patch.object(download, 'fetch', side_effect=fetch), \
                 patch.object(download, 'verify', side_effect=ValueError('bad signature')), \
                 patch.object(download.release_archive, 'extract') as extract, \
                 patch.object(download.subprocess, 'run') as execute:
                with self.assertRaisesRegex(ValueError, 'bad signature'):
                    download.main()
                extract.assert_not_called()
                execute.assert_not_called()


class PublishedInstallerTests(unittest.TestCase):
    def test_published_install_never_builds_and_requires_restart_consent(self):
        with patch.object(sys, 'argv', ['published', '--bundle', '/fixture/bundle']), \
             patch.object(published_install.user_install, 'verify_bundle'), \
             patch.object(published_install.setup_guide, 'ppa_stage', return_value={'status': 'done'}), \
             patch.object(published_install.setup_guide, 'packages_stage', return_value={'status': 'done'}), \
             patch.object(published_install.setup_guide, 'font_stage', return_value={'status': 'done'}), \
             patch.object(published_install.user_install, 'Installation') as factory, \
             patch.object(published_install, 'ask', return_value=True) as ask, \
             patch.object(published_install.setup, 'main', return_value=0) as main:
            factory.return_value.selected.return_value = 'releases/old'
            factory.return_value.running.return_value = {'pid': 1}
            published_install.main()
            ask.assert_called_once()
            main.assert_called_once_with(['--bundle', '/fixture/bundle', '--apply', '--update', '--restart-bar'])

    def test_refused_prerequisites_never_deploy(self):
        with patch.object(sys, 'argv', ['published', '--bundle', '/fixture/bundle']), \
             patch.object(published_install.user_install, 'verify_bundle'), \
             patch.object(published_install.setup_guide, 'ppa_stage', return_value={'status': 'command'}), \
             patch.object(published_install, 'ask', return_value=False), \
             patch.object(published_install.setup, 'main') as main:
            with self.assertRaises(SystemExit):
                published_install.main()
            main.assert_not_called()


class SigningResumeTests(unittest.TestCase):
    def fixture(self, base):
        import user_install
        tree = base / 'tree'
        tree.mkdir()
        (tree / 'README.md').write_text('committed source')
        with tarfile.open(base / 'source.tar', 'w') as source:
            source.add(tree / 'README.md', arcname='README.md')
        bundle = tree / 'work/user-releases/release-1.0.0'
        bundle.mkdir(parents=True)
        (bundle / 'release.json').write_text('{}')
        with patch.object(user_install, 'verify_bundle'):
            return publish.package(tree, bundle, base, '1.0.0', 'a' * 40)

    def test_complete_unsigned_archive_can_be_reviewed_without_rebuilding(self):
        import user_install
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            assets = self.fixture(base)
            with patch.object(publish.subprocess, 'check_output', return_value=(base / 'source.tar').read_bytes()), \
                 patch.object(user_install, 'verify_bundle', return_value={'version': 'release-1.0.0'}):
                self.assertEqual(publish.review_existing(base, '1.0.0', 'a' * 40), assets)
                with self.assertRaisesRegex(ValueError, 'metadata'):
                    publish.review_existing(base, '1.0.0', 'b' * 40)
                assets[0].write_bytes(b'corrupted')
                with self.assertRaisesRegex(ValueError, 'changed'):
                    publish.review_existing(base, '1.0.0', 'a' * 40)

    def test_resume_refuses_a_different_git_export(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            self.fixture(base)
            with patch.object(publish.subprocess, 'check_output', return_value=b'other commit'):
                with self.assertRaisesRegex(ValueError, 'source export'):
                    publish.review_existing(base, '1.0.0', 'a' * 40)

    def test_signing_has_no_interactive_timeout_and_reuses_verified_signature(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            assets = self.fixture(base)
            def sign(*args, **kwargs):
                self.assertIsNone(kwargs['timeout'])
                Path(args[-1] + '.sig').write_bytes(b'fixture signature')
            with patch.object(publish, 'run', side_effect=sign) as run, \
                 patch.object(publish.download_release, 'verify') as verify:
                publish.sign_artifacts(assets, '/private/key', base / 'key.pub', base)
                self.assertEqual(Path(str(assets[2]) + '.sig').read_bytes(), b'fixture signature')
                publish.sign_artifacts(assets, '/private/key', base / 'key.pub', base)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(verify.call_count, 2)

    def test_resume_accepts_an_ancestor_commit_without_commit_or_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'config').mkdir()
            (root / 'config/release-signing-key.pub').write_text('ssh-ed25519 fixture')
            case = root / 'work/publish/v1.0.0'
            case.mkdir(parents=True)
            (case / 'release.json').write_text(json.dumps({'commit': 'a' * 40}))
            calls = []
            def run(*args, **kwargs):
                calls.append(args)
                if args[:2] == ('ssh-keygen', '-y'):
                    self.assertIsNone(kwargs['timeout'])
                    return 'ssh-ed25519 fixture'
                if args[:3] == ('git', 'branch', '--show-current'):
                    return 'main'
                if args[:3] == ('git', 'remote', 'get-url'):
                    return 'https://github.com/' + publish.REPOSITORY
                if args[:3] == ('git', 'rev-parse', 'HEAD'):
                    return 'b' * 40
                return ''
            with patch.object(sys, 'argv', ['publish', '--version', '1.0.0', '--signing-key', '/private/key', '--resume-signing']), \
                 patch.object(publish, 'ROOT', root), \
                 patch.object(publish.os, 'getuid', return_value=1000), \
                 patch.object(publish.shutil, 'which', return_value='/fixture'), \
                 patch.object(publish, 'run', side_effect=run), \
                 patch.object(publish, 'confirm'), \
                 patch.object(publish, 'review_existing', return_value=('archive', 'metadata', 'sums')) as review, \
                 patch.object(publish, 'publish_artifacts') as finish:
                publish.main()
                review.assert_called_once_with(case, '1.0.0', 'a' * 40)
                self.assertEqual(finish.call_args.kwargs['head'], 'b' * 40)
                self.assertTrue(finish.call_args.kwargs['resume'])
            self.assertIn(('git', 'merge-base', '--is-ancestor', 'a' * 40, 'b' * 40), calls)
            self.assertFalse(any(c[:2] in (('python3', '-c'), ('git', 'commit')) for c in calls))

    def test_timeout_keeps_original_artifacts_and_no_final_signature(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            assets = self.fixture(base)
            before = {p: p.read_bytes() for p in assets}
            with patch.object(publish, 'run', side_effect=subprocess.TimeoutExpired('fixture', 1)):
                with self.assertRaises(subprocess.TimeoutExpired):
                    publish.sign_artifacts(assets, '/private/key', base / 'key.pub', base)
            self.assertFalse(Path(str(assets[2]) + '.sig').exists())
            self.assertTrue(all(p.read_bytes() == data for p, data in before.items()))


class PublisherTests(unittest.TestCase):
    def test_artifact_name_requires_numeric_version(self):
        self.assertEqual(publish.artifact_name('1.2.3'), 'omabuntu-1.2.3-ubuntu-26.04-x86_64.tar.gz')
        for version in ('dev', '../bad', '1.2', '1.2.3;echo bad'):
            with self.assertRaises(ValueError):
                publish.artifact_name(version)

    def test_package_excludes_work_and_creates_matching_checksums(self):
        import user_install
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            tree = base / 'tree'
            tree.mkdir()
            (tree / 'README.md').write_text('tracked source')
            with tarfile.open(base / 'source.tar', 'w') as source:
                source.add(tree / 'README.md', arcname='README.md')
            (tree / 'generated.pyc').write_bytes(b'not tracked')
            bundle = tree / 'work/user-releases/release-1.0.0'
            bundle.mkdir(parents=True)
            (bundle / 'release.json').write_text('{}')
            (tree / 'work/private.txt').write_text('must not be published')
            with patch.object(user_install, 'verify_bundle'):
                archive, metadata, sums = publish.package(tree, bundle, base, '1.0.0', 'a' * 40)
            for filename, digest in download.checksums(sums.read_text()).items():
                self.assertEqual(hashlib.sha256((base / filename).read_bytes()).hexdigest(), digest)
            self.assertEqual(json.loads(metadata.read_text())['commit'], 'a' * 40)
            with tarfile.open(archive) as stream:
                self.assertNotIn('source/work/private.txt', stream.getnames())
                self.assertNotIn('source/generated.pyc', stream.getnames())
            release_archive.extract(archive, base / 'checked')

    def test_package_refuses_theme_artwork(self):
        import user_install
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            bundle = base / 'bundle'
            images = bundle / 'config/menu/backgrounds'
            images.mkdir(parents=True)
            (images / 'private.jpg').write_bytes(b'image')
            with patch.object(user_install, 'verify_bundle'), self.assertRaisesRegex(ValueError, 'artwork'):
                publish.package(base, bundle, base, '1.0.0', 'a' * 40)

    def test_publisher_builds_before_push_and_uploads_draft_before_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'config').mkdir()
            (root / 'config/release-signing-key.pub').write_text('ssh-ed25519 fixture')
            calls = []
            def run(*args, **kwargs):
                calls.append(args)
                if args[:2] == ('ssh-keygen', '-y'):
                    return 'ssh-ed25519 fixture'
                if args[:3] == ('git', 'branch', '--show-current'):
                    return 'main'
                if args[:3] == ('git', 'remote', 'get-url'):
                    return 'https://github.com/' + publish.REPOSITORY
                if args[:3] == ('git', 'rev-parse', 'HEAD'):
                    return 'a' * 40
                return ''
            def extract(archive, tree):
                tree.mkdir()
            def package(tree, bundle, case, version, commit):
                assets = tuple(case / name for name in ('archive.tar.gz', 'release.json', 'SHA256SUMS'))
                for path in (*assets, Path(str(assets[2]) + '.sig')):
                    path.write_bytes(b'fixture')
                return assets
            with patch.object(sys, 'argv', ['publish', '--version', '0.1.0', '--signing-key', '/private/key']), \
                 patch.object(publish, 'ROOT', root), \
                 patch.object(publish.os, 'getuid', return_value=1000), \
                 patch.object(publish.shutil, 'which', return_value='/fixture'), \
                 patch.object(publish, 'run', side_effect=run), \
                 patch.object(publish, 'confirm') as confirm, \
                 patch.object(publish.release_archive, 'extract', side_effect=extract), \
                 patch.object(publish, 'package', side_effect=package), \
                 patch.object(publish, 'check_artifacts'), \
                 patch.object(publish, 'sign_artifacts'):
                publish.main()
            self.assertEqual(confirm.call_count, 2)
            build = next(i for i, call in enumerate(calls) if call[:2] == ('python3', '-c'))
            push = next(i for i, call in enumerate(calls) if call[:2] == ('git', 'push'))
            draft = next(i for i, call in enumerate(calls) if call[:3] == ('gh', 'release', 'create'))
            public = next(i for i, call in enumerate(calls) if call[:3] == ('gh', 'release', 'edit'))
            self.assertLess(build, push)
            self.assertLess(push, draft)
            self.assertLess(draft, public)
            self.assertIn('--atomic', calls[push])
            self.assertIn('--draft', calls[draft])
            self.assertIn('--draft=false', calls[public])

    def test_missing_key_fails_before_any_git_or_publication(self):
        with patch.object(sys, 'argv', ['publish', '--version', '0.1.0']), \
             patch.object(publish.os, 'getuid', return_value=1000), \
             patch.object(publish.shutil, 'which', return_value='/usr/bin/fixture'), \
             patch.dict(publish.os.environ, {}, clear=True), \
             patch.object(publish, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Configure'):
                publish.main()
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
