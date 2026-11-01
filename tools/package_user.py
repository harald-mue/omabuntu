#!/usr/bin/env python3
"""Prepare a verified local user release under ignored work/, never install it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import re

import check_clock_preview as preview
import check_runtime
import user_install
import release_update
import build_omasnap
import build_plugin
import desktop_font
import plugin_manager

ROOT = Path(__file__).resolve().parents[1]


def stage_local_images(root, destination, assets=None):
    """Optionally stage local images, never require or download private assets.

    Local bundles containing these files are not cleared for redistribution.
    Reject symlinks and non-image files before copying any asset directory.
    """
    sources = []
    asset_root = user_install.safe_parents(root / 'config/menu' if assets is None else Path(assets).absolute())
    for name in ('backgrounds', 'themes-previews'):
        source = asset_root / name
        for parent in (asset_root, source):
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


def stage_screenshot(root, destination, candidate):
    """Attach only a verified, relocatable Omasnap stage and its notices."""
    _, prefix, report = build_omasnap.verify_stage(root, candidate)
    data = (prefix / 'bin/omasnap').read_bytes()
    relative = build_omasnap.PREFIX.lstrip('/') + '/bin/omasnap'
    expected = next(item['sha256'] for item in report['artifacts'] if item['path'] == relative)
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Omasnap binary changed while packaging')
    target = destination / 'runtime/bin/omasnap'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    target.chmod(0o755)
    notices = destination / 'licenses/omasnap'
    notices.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(prefix / 'share/licenses/omasnap', notices)
    for _, record in build_omasnap.notices(report['source_pin']):
        copied = notices / Path(record['notice_path']).name
        if hashlib.sha256(copied.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Omasnap notice changed while packaging')
    return report


def stage_plugin(root, destination, candidate):
    """Package an ABI-checked library as inert data; never load it."""
    _, prefix, report = build_plugin.verify_stage(root, candidate)
    relative = build_plugin.PREFIX.lstrip('/') + '/lib/libhyprbars.so'
    expected = next(item['sha256'] for item in report['artifacts'] if item['path'] == relative)
    data = (prefix / 'lib/libhyprbars.so').read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Plugin library changed while packaging')
    target = destination / 'native'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'hyprbars.so').write_bytes(data)
    (target / 'hyprbars.so').chmod(0o444)
    (target / 'hyprbars.json').write_text(json.dumps(build_plugin.descriptor(report, expected), indent=2) + '\n')
    (target / 'hyprbars.json').chmod(0o444)
    notices = destination / 'licenses/hyprbars'
    notices.parent.mkdir(parents=True, exist_ok=True)
    notices.mkdir()
    notice_hashes = {Path(item['license']['notice_path']).name: item['license']['sha256']
                     for item in report['source_pin']['sources']}
    notice_hashes['Protocol-notices.txt'] = report['protocol_notices_sha256']
    for name, expected in notice_hashes.items():
        data = (prefix / 'licenses' / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Plugin notice changed while packaging')
        copied = notices / name
        copied.write_bytes(data)
        copied.chmod(0o444)
    return report


def stage_manager_policy(root, destination):
    data = plugin_manager.policy(root)
    path = destination / 'native/hyprpm.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')
    path.chmod(0o444)
    return data


# The legacy titlebar load belongs to legacy bundles (native/hyprbars.so).
# Manager bundles record the hyprpm policy instead; loading there is owned by
# the explicit activation/login grant (tools/plugin_login.py). The private
# `home` binding must survive the replacement: the saved-workspace loader
# below the block uses it.
LEGACY_TITLEBAR_LOAD = (
    '-- Title-bar plugin (plan 020): registering the path during the config load is\n'
    '-- what makes Hyprland load it. A hyprland.start handler only queues a path\n'
    '-- that no later pass reads. The load triggers one config reload; the next\n'
    '-- pass finds the plugin options (docs/hyprbars.md). Guarded, so a release\n'
    '-- without the artifact keeps parsing.\n'
    'local home = os.getenv("HOME") or ""\n'
    'local titlebars = home .. "/.local/lib/omabuntu/hyprbars.so"\n'
    'local artifact = io.open(titlebars, "r")\n'
    'if artifact then\n'
    '  artifact:close()\n'
    '  hl.plugin.load(titlebars)\n'
    'end\n'
)
MANAGER_TITLEBAR_NOTE = (
    '-- Title-bar plugin: manager bundles record the reviewed hyprpm policy\n'
    '-- instead of a bundled artifact path. Loading stays with the explicit\n'
    '-- activation/login grant (docs/plugin-management.md); nothing is loaded\n'
    '-- here. The home binding stays; the workspace loader below uses it.\n'
    'local home = os.getenv("HOME") or ""\n'
)


def managed_snippet(data, *, manager):
    """Render the managed snippet for one bundle mode; never load anything."""
    if not manager:
        return data
    text = data.decode()
    if text.count(LEGACY_TITLEBAR_LOAD) != 1:
        raise ValueError('Managed snippet legacy load witness differs')
    return text.replace(LEGACY_TITLEBAR_LOAD, MANAGER_TITLEBAR_NOTE).encode()


def prepare(version, candidate, screenshot_build=None, image_assets=None, build_inputs=None, font_file=None, plugin_build=None):
    if not isinstance(version, str) or not user_install.VERSION.fullmatch(version):
        raise ValueError('Invalid release version')
    files, profile = preview.verified_sources(ROOT)
    build, runtime, _ = check_runtime.verify_stage(ROOT, candidate)
    screenshot = build_omasnap.verify_stage(ROOT, screenshot_build) if screenshot_build is not None else None
    if build_inputs is not None and (not isinstance(build_inputs, str) or not re.fullmatch(r'[a-f0-9]{64}', build_inputs)):
        raise ValueError('Invalid bootstrap input digest')
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
                     'defaults_backend.py', 'power_actions.py', 'elsewhen_probe.py',
                     'capture_screenshot.py', 'weather_probe.py', 'omabuntu_hyprland_window_minimize.py', 'plugin_login.py'):
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
        local_images = stage_local_images(ROOT, temporary, assets=image_assets)
        # Record deployable managed configuration with each immutable release.
        # Deployment remains an explicit Make step, never implicit on start.
        # The managed snippet is rendered per bundle mode (plan 071): manager
        # bundles ship no legacy artifact load.
        manager_bundle = plugin_build is None
        for name in ('hypr/omabuntu-managed.lua', 'hypr/hyprpaper.conf', 'hypr/session-template.lua.in', 'hypr/titlebars.lua.in',
                     'systemd/omabuntu-shell.service',
                     'systemd/omabuntu-shell-wait.py'):
            target = temporary / 'config' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            data = (ROOT / 'config' / name).read_bytes()
            if name == 'hypr/omabuntu-managed.lua':
                data = managed_snippet(data, manager=manager_bundle)
            target.write_bytes(data)
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
        if screenshot:
            stage_screenshot(ROOT, temporary, screenshot_build)
        plugin = stage_plugin(ROOT, temporary, plugin_build) if plugin_build is not None else None
        if plugin is None:
            stage_manager_policy(ROOT, temporary)
        font_pin = desktop_font.stage(ROOT, temporary, font_file) if font_file is not None else None
        (temporary / 'PROVENANCE.json').write_text(json.dumps({
            'omarchy': profile['source'], 'runtime_sources': source_lock,
            'profile_sha256': hashlib.sha256((ROOT / 'upstream/clock-preview.json').read_bytes()).hexdigest(),
            'runtime_alias_adaptation': 'bin/qs uses a relative quickshell target for relocation',
            'distribution': 'Local private installation only; no remote publication approval.',
            'local_image_directories': local_images,
            'bootstrap_input_sha256': build_inputs,
            'omasnap_source': screenshot[2]['source_pin'] if screenshot else None,
            'desktop_font': font_pin,
            'hyprbars_source': plugin['source_pin'] if plugin else None,
            'hyprbars_native_target': plugin['native_target'] if plugin else None,
        }, indent=2) + '\n')
        metadata = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': version,
                    'autostart': False, 'lock_activation': False,
                    'update_contract': release_update.contract(),
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
