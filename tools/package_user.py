#!/usr/bin/env python3
"""Prepare a verified local user release under ignored work/, never install it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

import check_clock_preview as preview
import check_runtime
import user_install

ROOT = Path(__file__).resolve().parents[1]


def stage_local_images(root, destination):
    """Optionally stage local images, never require or download private assets.

    Local bundles containing these files are not cleared for redistribution.
    Reject symlinks and non-image files before copying any asset directory.
    """
    sources = []
    for name in ('backgrounds', 'themes-previews'):
        source = root / 'config/menu' / name
        for parent in (root / 'config', root / 'config/menu', source):
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise ValueError('Unsafe local image directory: ' + str(parent))
        if not source.exists():
            continue
        for path in source.rglob('*'):
            if path.is_symlink() or (not path.is_dir() and
                    (not path.is_file() or path.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'))):
                raise ValueError('Unexpected local image input: ' + str(path))
        sources.append((name, source))
    for name, source in sources:
        target = destination / 'config/menu' / name
        shutil.copytree(source, target)
        for path in target.rglob('*'):
            path.chmod(0o555 if path.is_dir() else 0o444)
        target.chmod(0o555)
    return [name for name, _ in sources]


def prepare(version, candidate):
    if not isinstance(version, str) or not user_install.VERSION.fullmatch(version):
        raise ValueError('Invalid release version')
    files, profile = preview.verified_sources(ROOT)
    build, runtime, _ = check_runtime.verify_stage(ROOT, candidate)
    output = user_install.private_directory(ROOT / 'work/user-releases') / version
    if output.exists():
        raise ValueError('Release directory already exists; use a new version')
    temporary = output.with_name('.incoming-' + user_install.stamp())
    temporary.mkdir(mode=0o700)
    try:
        shutil.copytree(runtime, temporary / 'runtime', symlinks=True)
        alias = temporary / 'runtime/bin/qs'
        if not alias.is_symlink() or os.readlink(alias) != '/opt/omabuntu-runtime/bin/quickshell':
            raise ValueError('Runtime alias differs from the reviewed stage')
        alias.unlink()
        alias.symlink_to('quickshell')
        for name, data in files.items():
            path = temporary / 'shell' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(0o444)
        for name in ('network_nm.py', 'display_backend.py', 'qrcodegen.py', 'dock_state.py',
                     'keybindings_menu.py', 'menu_model.py', 'menu_common.py',
                     'theme_backend.py', 'font_backend.py', 'background_backend.py',
                     'power_actions.py', 'elsewhen_probe.py'):
            target = temporary / 'helpers' / name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes((ROOT / 'tools' / name).read_bytes())
            target.chmod(0o444)
        menu_data = ((temporary / 'shell/omabuntu-menu.jsonc', ROOT / 'config/shell/omabuntu-menu.jsonc'),
                     (temporary / 'menu/themes.json', ROOT / 'config/menu/themes.json'))
        for target, source in menu_data:
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(source.read_bytes())
            target.chmod(0o444)
        # Theme background stills and preview images (plan 006). The staged
        # helpers resolve these through their ROOT default
        # (config/menu/backgrounds, config/menu/themes-previews); provenance
        # and the image license caveat live in upstream/theme-backgrounds.json.
        local_images = stage_local_images(ROOT, temporary)
        # Record deployable managed configuration with each immutable release.
        # Deployment remains an explicit Make step, never implicit on start.
        for name in ('hypr/omabuntu-managed.lua', 'hypr/hyprpaper.conf',
                     'systemd/omabuntu-shell.service',
                     'systemd/omabuntu-shell-wait.py'):
            target = temporary / 'config' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / 'config' / name).read_bytes())
            target.chmod(0o444)
        (temporary / 'manager.py').write_bytes((ROOT / 'tools/user_install.py').read_bytes())
        (temporary / 'manager.py').chmod(0o444)
        lock_dir = temporary / 'lock'
        lock_dir.mkdir()
        lock_conf = lock_dir / 'hyprlock.conf'
        lock_conf.write_bytes((ROOT / 'config/lock/hyprlock.conf').read_bytes())
        lock_conf.chmod(0o444)
        lock_helper = temporary / 'helpers' / 'lock_session.py'
        lock_helper.write_bytes((ROOT / 'tools/lock_session.py').read_bytes())
        lock_helper.chmod(0o444)
        source_lock = json.loads((ROOT / 'upstream/source-lock.json').read_text())
        sources = build / 'sources'
        quickshell = next(sources.glob('quickshell-*'))
        cpptrace = next(sources.glob('cpptrace-*'))
        licenses = {
            'Omarchy-MIT.txt': ROOT / 'licenses/Omarchy-MIT.txt',
            'Omabuntu-MIT.txt': ROOT / 'LICENSE',
            'Quickshell-LGPL.txt': quickshell / 'LICENSE',
            'Quickshell-GPL.txt': quickshell / 'LICENSE-GPL',
            'cpptrace-MIT.txt': cpptrace / 'LICENSE',
        }
        (temporary / 'licenses').mkdir()
        for name, path in licenses.items():
            data = path.read_bytes()
            if not data or len(data) > 100000:
                raise ValueError('Invalid runtime license')
            (temporary / 'licenses' / name).write_bytes(data)
        (temporary / 'PROVENANCE.json').write_text(json.dumps({
            'omarchy': profile['source'], 'runtime_sources': source_lock,
            'profile_sha256': hashlib.sha256((ROOT / 'upstream/clock-preview.json').read_bytes()).hexdigest(),
            'runtime_alias_adaptation': 'bin/qs uses a relative quickshell target for relocation',
            'distribution': 'Local private installation only; no remote publication approval.',
            'local_image_directories': local_images,
        }, indent=2) + '\n')
        metadata = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': version,
                    'autostart': False, 'lock_activation': False,
                    'files': user_install.file_manifest(temporary)}
        (temporary / 'release.json').write_text(json.dumps(metadata, indent=2) + '\n')
        user_install.verify_bundle(temporary)
        temporary.rename(output)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)  # Only the unselected output created by this call.
        raise
    print('Prepared local release:', output)
    print('Not installed, started, published or enabled for autostart.')
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--build-dir', type=Path, required=True,
                        help="Explicit verified directory under this project's work/builds")
    args = parser.parse_args(argv)
    os.umask(0o077)
    prepare(args.version, args.build_dir)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, check_runtime.builder.BuildError) as error:
        raise SystemExit(str(error))
