"""Public source must not depend on private images or implicit local stages."""
import importlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import package_user
import install


class PublicationCleanupTests(unittest.TestCase):
    def test_local_image_directories_are_ignored(self):
        text = (ROOT / '.gitignore').read_text()
        self.assertIn('/config/menu/backgrounds/', text)
        self.assertIn('/config/menu/themes-previews/', text)
        if not (ROOT / '.git').exists():
            return  # Still validate rules in source exports with no Git metadata.
        result = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin'], cwd=ROOT,
                                input='config/menu/backgrounds/example/a.jpg\nconfig/menu/themes-previews/example.png\n',
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout.splitlines()), 2)

    def test_image_packaging_accepts_an_asset_free_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'
            output = Path(directory) / 'bundle'
            root.mkdir(); output.mkdir()
            self.assertEqual(package_user.stage_local_images(root, output), [])
            self.assertFalse((output / 'config/menu/backgrounds').exists())

    def test_local_images_are_preserved_and_staged_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'; output = Path(directory) / 'bundle'
            image = root / 'config/menu/backgrounds/example/a.jpg'
            image.parent.mkdir(parents=True); image.write_bytes(b'fixture')
            output.mkdir()
            self.assertEqual(package_user.stage_local_images(root, output), ['backgrounds'])
            staged = output / image.relative_to(root)
            self.assertEqual(staged.read_bytes(), b'fixture')
            self.assertEqual(image.read_bytes(), b'fixture')
            self.assertEqual(staged.stat().st_mode & 0o777, 0o444)

    def test_image_packaging_refuses_symlinked_or_non_image_inputs(self):
        for kind in ('symlink', 'non-image'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / 'source'; output = Path(directory) / 'bundle'
                images = root / 'config/menu/backgrounds'; images.mkdir(parents=True)
                output.mkdir()
                if kind == 'symlink':
                    (images / 'a.jpg').symlink_to(root / 'elsewhere')
                else:
                    (images / '.env').write_text('synthetic fixture')
                with self.assertRaises(ValueError):
                    package_user.stage_local_images(root, output)

    def test_local_image_packaging_refuses_symlinked_ancestors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'; output = Path(directory) / 'bundle'
            root.mkdir(); output.mkdir()
            target = Path(directory) / 'private'; target.mkdir()
            (root / 'config').symlink_to(target)
            with self.assertRaises(ValueError):
                package_user.stage_local_images(root, output)

    def test_clean_source_export_refuses_symlinks(self):
        import check_clean_source
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'link.md').symlink_to(root / 'missing.md')
            with patch.object(check_clean_source.subprocess, 'run',
                              return_value=subprocess.CompletedProcess([], 0, b'link.md\0', b'')):
                with self.assertRaises(ValueError):
                    check_clean_source.candidate_files(root)

    def test_clean_source_run_refuses_symlinked_work_parent(self):
        import check_clean_source
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'work').mkdir()
            target = root / 'elsewhere'; target.mkdir()
            (root / 'work/clean-source').symlink_to(target)
            with self.assertRaises(ValueError):
                check_clean_source.run(root)
            self.assertEqual(list(target.iterdir()), [])

    def test_runtime_probe_uses_authored_webp_without_imported_images(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'bundle'; case = Path(directory) / 'case'
            bundle.mkdir(); case.mkdir()
            calls = []
            def run(command, timeout):
                calls.append(command)
                return {'status': 'ok', 'stdout': 'libQt6Core libQt6Qml libQt6Quick Configuration Loaded OMABUNTU_INSTALL_WEBP_READY', 'stderr': ''}
            with patch.object(install.user_install, 'verify_bundle'), \
                 patch.object(install.check_runtime, 'sandbox_command', side_effect=lambda r, c, a: a):
                result = install.runtime_probe(bundle, case, run=run)
            self.assertEqual(result['status'], 'passed')
            probe = (case / 'probe/still.webp').read_bytes()
            self.assertEqual(probe[:4], b'RIFF')
            self.assertEqual(probe[8:12], b'WEBP')
            # The smaller valid 38-byte fixture failed the native Qt decode.
            self.assertGreaterEqual(len(probe), 64)
            self.assertEqual(int.from_bytes(probe[4:8], 'little') + 8, len(probe))
            self.assertEqual(len(calls), 2)

    def test_clean_source_checker_is_plan_only_by_default(self):
        import check_clean_source
        with patch.object(check_clean_source, 'run') as run:
            self.assertEqual(check_clean_source.main([]), 0)
        run.assert_not_called()

    def test_clean_source_export_excludes_even_tracked_private_inputs(self):
        import check_clean_source
        payload = b'README.md\0work/private.json\0config/menu/backgrounds/a.jpg\0config/menu/themes-previews/a.png\0'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'README.md').write_text('fixture')
            with patch.object(check_clean_source.subprocess, 'run',
                              return_value=subprocess.CompletedProcess([], 0, payload, b'')):
                self.assertEqual(check_clean_source.candidate_files(root), [Path('README.md')])

    def test_make_refuses_missing_build_before_packaging_or_deployment(self):
        for target in ('package', 'dev-update'):
            result = subprocess.run(['make', '--no-print-directory', target,
                                     'VERSION=fixture', 'BUILD_DIR='],
                                    cwd=ROOT, text=True, capture_output=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('BUILD_DIR is required', result.stderr)

    def test_runtime_commands_require_explicit_build_before_side_effects(self):
        for name in ('package_user', 'check_command_menu', 'check_image_picker', 'check_desktop_panels', 'bar_session'):
            with self.subTest(name=name):
                module = importlib.import_module(name)
                args = ['--version', 'fixture'] if name == 'package_user' else ['start'] if name == 'bar_session' else ['--run']
                with patch.object(module, 'run', create=True) as run, \
                     patch.object(module, 'prepare', create=True) as prepare, \
                     patch.object(module, 'start', create=True) as start:
                    with self.assertRaises(SystemExit) as error:
                        module.main(args)
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called(); prepare.assert_not_called(); start.assert_not_called()
