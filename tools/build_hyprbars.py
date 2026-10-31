#!/usr/bin/env python3
"""Build the hyprbars Hyprland plugin against the Hyprland source at our commit.

Pinned sources, private build directory, no package install, no config edit, no
reload and no plugin activation. The PPA's installed headers do not match the
running binary, so the plugin is built against a source checkout of the exact
commit with freshly generated Wayland protocol headers, as hyprpm does.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_REPO = 'https://github.com/hyprwm/hyprland-plugins'
PLUGIN_COMMIT = '7644cecdb947060682891a0db2a0cdc5c0b9e704'  # hyprland-plugins v0.56.0
HYPRLAND_REPO = 'https://github.com/hyprwm/Hyprland'
HYPRLAND_COMMIT = 'efb50993780079460b0cbed1363e2166a2de1d9f'
WORK = ROOT / 'work'
HEADERS = WORK / 'hyprland-headers' / 'hyprland'
PCDIR = WORK / 'hyprland-pc'
REQUIRED = ('hyprland', 'libdrm', 'libinput', 'libudev', 'pixman-1', 'wayland-server', 'xkbcommon')
GLSLANG = Path('/usr/include/glslang/Include/glslang_c_interface.h')
APT_HINT = ('sudo apt-get --no-install-recommends install glslang-dev '
            'libhyprlang-dev libhyprutils-dev libhyprcursor-dev libhyprgraphics-dev '
            'libaquamarine-dev libcairo2-dev libpango1.0-dev libegl-dev libxcb1-dev '
            'libxcb-xfixes0-dev libxcb-icccm4-dev libxcb-composite0-dev libxcb-res0-dev '
            'libxcb-errors-dev libxcb-shape0-dev hyprwayland-scanner')


def run(argv, cwd=None, env=None, timeout=1800):
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True,
                            timeout=timeout, check=False)
    if result.returncode:
        raise ValueError('Command failed: ' + ' '.join(argv) + '\n' + (result.stdout + result.stderr)[-3000:])
    return result.stdout


def installed_version():
    """Exit-only binary metadata; a first install need not have a live session."""
    text = json.loads(run(['Hyprland', '--version-json'], timeout=15))
    if not isinstance(text, dict) or text.get('dirty') is not False:
        raise ValueError('Require a clean installed Hyprland build')
    return text


def hyprland_version():
    text = installed_version()
    return text.get('version'), text.get('commit'), text.get('abiHash')


def generate_protocols():
    destination = HEADERS / 'protocols'
    if (destination / 'color-management-v1.hpp').is_file() and (destination / 'wayland.hpp').is_file():
        return
    wayland = Path(pkgdir('wayland-scanner')) / 'wayland.xml'
    protocols = Path(pkgdir('wayland-protocols'))
    run(['hyprwayland-scanner', '--wayland-enums', str(wayland), str(destination) + '/'])
    for group in ('stable', 'unstable', 'staging'):
        for xml in sorted((protocols / group).glob('*/*.xml')):
            subprocess.run(['hyprwayland-scanner', str(xml), str(destination) + '/'],
                           capture_output=True, check=False)
    for xml in sorted(destination.glob('*.xml')):
        subprocess.run(['hyprwayland-scanner', str(xml), str(destination) + '/'],
                       capture_output=True, check=False)
    if not (destination / 'color-management-v1.hpp').is_file():
        raise ValueError('Wayland protocol headers could not be generated')


def pkgdir(module):
    return run(['pkg-config', '--variable=pkgdatadir', module]).strip()


def ensure_headers():
    if not (HEADERS / '.git').is_dir():
        HEADERS.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        run(['git', 'clone', '--quiet', '--filter=blob:none', HYPRLAND_REPO, str(HEADERS)])
    run(['git', 'checkout', '--quiet', HYPRLAND_COMMIT], cwd=HEADERS)
    if run(['git', 'rev-parse', 'HEAD'], cwd=HEADERS).strip() != HYPRLAND_COMMIT:
        raise ValueError('Hyprland checkout differs from the reviewed commit')
    generate_protocols()
    write_version_header()
    requires = run(['pkg-config', '--print-requires', 'hyprland']).strip()
    PCDIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    (PCDIR / 'hyprland.pc').write_text(
        'prefix=' + str(HEADERS.parent) + '\n'
        'Name: Hyprland\nURL: https://github.com/hyprwm/Hyprland\n'
        'Description: Hyprland source headers at the reviewed commit\nVersion: 0.56.2\n'
        'Requires: ' + ' '.join(requires.replace('\n', ' ').split()) + ' lua5.4\n'
        'Cflags: -I${prefix} -I${prefix}/hyprland/protocols -I${prefix}/hyprland/src\n')
    return PCDIR


def module_version(module):
    return run(['pkg-config', '--modversion', module]).strip()


def write_version_header():
    """Hyprland generates src/version.h during its own build; plugins need it."""
    template = (HEADERS / 'src/version.h.in').read_text()
    version = installed_version()
    values = {
        'GIT_COMMIT_HASH': version.get('commit', ''),
        'GIT_BRANCH': version.get('branch', ''),
        'GIT_COMMIT_MESSAGE': version.get('commit_message', ''),
        'GIT_COMMIT_DATE': version.get('commit_date', ''),
        'GIT_DIRTY': 'false' if not version.get('dirty') else 'true',
        'GIT_TAG': version.get('tag', ''),
        'GIT_COMMITS': str(version.get('commits', '')),
        'AQUAMARINE_VERSION': module_version('aquamarine'),
        'HYPRLANG_VERSION': module_version('hyprlang'),
        'HYPRUTILS_VERSION': module_version('hyprutils'),
        'HYPRCURSOR_VERSION': module_version('hyprcursor'),
        'HYPRGRAPHICS_VERSION': module_version('hyprgraphics'),
    }
    parts = (values['AQUAMARINE_VERSION'] + '.0.0').split('.')[:3]
    values.update({'AQUAMARINE_VERSION_MAJOR': parts[0], 'AQUAMARINE_VERSION_MINOR': parts[1],
                   'AQUAMARINE_VERSION_PATCH': parts[2]})
    for key, value in values.items():
        template = template.replace('@' + key + '@', str(value))
    if '@' in template:
        raise ValueError('Unresolved placeholder in the generated version header')
    (HEADERS / 'src/version.h').write_text(template)


def missing_modules():
    missing = []
    for module in REQUIRED:
        if subprocess.run(['pkg-config', '--exists', module], check=False).returncode:
            missing.append(module)
    if not GLSLANG.is_file():
        missing.append('glslang-dev')
    return missing


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Fresh private build directory; existing paths are never overwritten')
    args = parser.parse_args(argv)
    version, commit, abi = hyprland_version()
    if version != '0.56.2' or commit != HYPRLAND_COMMIT or not abi:
        raise ValueError('Installed Hyprland differs from the reviewed build: ' + str(commit))
    missing = missing_modules()
    if missing:
        print('Missing build requirements:', ', '.join(missing))
        print('Install (approved, user-run):', APT_HINT)
        return 2
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = args.output or WORK / 'hyprbars-builds' / stamp
    if '..' in output.parts or any(part.is_symlink() for part in (output, *output.parents)):
        raise ValueError('Refusing symlinked or traversing build directory')
    if output.exists():
        raise ValueError('Choose a fresh build directory; existing contents are retained')
    source = output / 'source'
    output.mkdir(mode=0o700, parents=True)
    run(['git', 'clone', '--quiet', '--no-checkout', PLUGIN_REPO, str(source)])
    run(['git', 'checkout', '--quiet', PLUGIN_COMMIT], cwd=source)
    if run(['git', 'rev-parse', 'HEAD'], cwd=source).strip() != PLUGIN_COMMIT:
        raise ValueError('Plugin checkout differs from the pinned commit')
    pc = ensure_headers()
    env = {**os.environ, 'PKG_CONFIG_PATH': str(pc) + ':' + os.environ.get('PKG_CONFIG_PATH', '')}
    build = output / 'build'
    install = output / 'install'
    run(['cmake', '-S', str(source / 'hyprbars'), '-B', str(build), '-G', 'Ninja',
         '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_INSTALL_PREFIX=' + str(install)], env=env)
    run(['cmake', '--build', str(build), '--target', 'hyprbars'], env=env)
    run(['cmake', '--install', str(build)], env=env)
    library = next(install.rglob('hyprbars.so'), None) or next(build.glob('libhyprbars.so'), None)
    if library is None or library.is_symlink() or library.stat().st_size < 10000:
        raise ValueError('Built plugin library is missing or implausible')
    if hyprland_version() != (version, commit, abi):
        raise ValueError('Installed Hyprland changed during the build; artifact was not loaded')
    report = {'status': 'built-not-loaded', 'plugin_commit': PLUGIN_COMMIT,
              'hyprland_version': version, 'hyprland_commit': commit, 'abi_hash': abi,
              'hyprland_headers': str(HEADERS), 'library': str(library),
              'library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
              'loaded': False, 'config_applied': False,
              'limits': 'Built only. Loading needs an explicit plugin load or config include '
                        'plus a Hyprland reload, which are separate approvals.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Built hyprbars for Hyprland', version, '(abi', abi + ')')
    print('Library:', library)
    print('Not loaded. No config file was written and Hyprland was not reloaded.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        raise SystemExit(str(error))
