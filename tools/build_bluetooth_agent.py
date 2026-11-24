"""Build a closed QtDBus helper privately; never install dependencies or run it live."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'native/bluetooth_agent.cpp'


def build(output, *, testing=False):
    output = Path(output).absolute()
    if not output.resolve().is_relative_to(ROOT / 'work'):
        raise ValueError('Build output must remain under ignored work/')
    if output.exists() or output.is_symlink():
        raise ValueError('Use a new build output; never replace existing evidence')
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if any(not os.access(program, os.X_OK) for program in ('/usr/bin/c++', '/usr/bin/pkg-config')):
        raise ValueError('Compiler/pkg-config unavailable; no dependency installation attempted')
    try:
        flags = subprocess.run(['/usr/bin/pkg-config', '--cflags', '--libs', 'Qt6Core', 'Qt6DBus'],
                               capture_output=True, text=True, timeout=10, check=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ValueError('Qt6Core/Qt6DBus probe failed or timed out; no installation attempted') from error
    command = ['/usr/bin/c++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-fPIC',
               '-fstack-protector-strong', '-D_FORTIFY_SOURCE=2', '-Wl,-z,relro,-z,now']
    if testing:
        command.append('-DOMABUNTU_BLUETOOTH_TEST_BUS')
    command += [str(SOURCE), '-o', str(output), *shlex.split(flags.stdout)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    output.with_suffix('.build.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise ValueError('Bluetooth helper build failed; inspect private build log')
    output.chmod(0o500)
    record = {'schema_version': 1, 'testing': testing, 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'binary_sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'command': command,
              'qt': subprocess.run(['/usr/bin/pkg-config', '--modversion', 'Qt6Core', 'Qt6DBus'],
                                   capture_output=True, text=True, timeout=10, check=True).stdout.splitlines(),
              'installed': False, 'native_actions': False}
    output.with_suffix('.json').write_text(json.dumps(record, indent=2) + '\n')
    return output


def verify(output):
    output = Path(output)
    if output.is_symlink() or not output.is_file():
        raise ValueError('Missing regular Bluetooth helper; build explicitly, no installation attempted')
    binary = output.read_bytes()
    if (not binary.startswith(b'\x7fELF') or b'--test-bus=' in binary
            or b'OMABUNTU_TEST_OPERATION_MS' in binary):
        raise ValueError('Bluetooth artifact is not a production ELF or exposes test capabilities')
    record = json.loads(output.with_suffix('.json').read_text())
    if (record.get('schema_version') != 1 or record.get('testing') is not False
            or record.get('source_sha256') != hashlib.sha256(SOURCE.read_bytes()).hexdigest()
            or record.get('binary_sha256') != hashlib.sha256(output.read_bytes()).hexdigest()):
        raise ValueError('Bluetooth build is stale, changed or a test build; refusing packaging')
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--testing', action='store_true', help='Private fake-bus test build; never package')
    args = parser.parse_args(argv)
    print(build(args.output, testing=args.testing))


if __name__ == '__main__':
    main()
