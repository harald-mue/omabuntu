"""Pinned desktop Nerd Font: local staging and explicitly approved user install.

No global font configuration, GTK/terminal preference edits, or system files.
Old content-addressed versions are retained for rollback; no font is removed.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import bootstrap_sources
import install as guided
import user_install

ROOT = Path(__file__).resolve().parents[1]
COMMIT = 'fa7b859994228a9c8759f99c55a8d31ee92a1b5e'
FILENAME = 'JetBrainsMonoNerdFont-Regular.ttf'
URL = ('https://raw.githubusercontent.com/ryanoasis/nerd-fonts/' + COMMIT
       + '/patched-fonts/JetBrainsMono/Ligatures/Regular/' + FILENAME)


def inputs(root=ROOT):
    pin = user_install.read_json(root / 'upstream/desktop-font.json')
    if (pin.get('schema_version') != 1 or pin.get('commit') != COMMIT or pin.get('url') != URL
            or pin.get('family') != 'JetBrainsMono Nerd Font' or pin.get('filename') != FILENAME
            or pin.get('bytes') != 2469104 or pin.get('license') != 'OFL-1.1'
            or pin.get('sha256') != '0ec29a68b539ece7078fc714cebff0c0accb2f4948f8f7963d9f5e86633b12d9'
            or pin.get('required_glyphs') != ['f011', 'f030', 'f488', 'f01e9']):
        raise ValueError('Desktop font pin differs')
    expected = {'licenses/Desktop-JetBrainsMonoNerd-OFL.txt', 'licenses/Desktop-Nerd-Fonts-LICENSE.txt'}
    if {item.get('path') for item in pin.get('notices', [])} != expected:
        raise ValueError('Desktop font notice set differs')
    user_install.safe_parents(root / 'licenses')
    for record in pin['notices']:
        path = root / record['path']
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Desktop font license notice differs')
    return pin


def verify_bytes(path, pin):
    user_install.safe_parents(path.parent)
    if path.is_symlink() or not path.is_file() or path.stat().st_size != pin['bytes']:
        raise ValueError('Desktop font file missing or changed')
    if hashlib.sha256(path.read_bytes()).hexdigest() != pin['sha256']:
        raise ValueError('Desktop font checksum differs')


def run(command, timeout=15):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise ValueError('Font probe/cache command failed: ' + command[0])
    return result.stdout


def charset_contains(text, points):
    ranges = []
    try:
        for item in text.split():
            fields = item.split('-')
            if len(fields) not in (1, 2):
                return False
            lower, upper = int(fields[0], 16), int(fields[-1], 16)
            if lower > upper:
                return False
            ranges.append((lower, upper))
        return all(any(lower <= int(point, 16) <= upper for lower, upper in ranges) for point in points)
    except ValueError:
        return False


def verify_font(path, pin, execute=run):
    verify_bytes(path, pin)
    family = execute(['fc-scan', '--format=%{family[0]}\n', str(path)]).strip()
    charset = execute(['fc-query', '--format=%{charset}\n', str(path)])
    if family != pin['family'] or not charset_contains(charset, pin['required_glyphs']):
        raise ValueError('Desktop font family or required icon glyphs differ')


def obtain(root=ROOT, fetch=bootstrap_sources.fetch, execute=run):
    pin = inputs(root)
    cache = user_install.private_directory(root / 'work/font-cache' / pin['sha256'])
    path = cache / FILENAME
    if path.is_symlink():
        raise ValueError('Symlinked cached font refused')
    if not path.exists():
        data = fetch(pin['url'], pin['bytes'])
        if len(data) != pin['bytes'] or hashlib.sha256(data).hexdigest() != pin['sha256']:
            raise ValueError('Downloaded desktop font differs')
        temporary = cache / ('.font-' + user_install.stamp())
        try:
            with temporary.open('xb') as stream:
                stream.write(data)
            os.link(temporary, path)  # Publish without replacing a local/concurrent file.
        finally:
            temporary.unlink(missing_ok=True)
    verify_font(path, pin, execute)
    return path


def stage(root, destination, file, execute=run):
    pin = inputs(root)
    verify_font(file, pin, execute)
    output = user_install.safe_parents(destination / 'assets/fonts')
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(file, output / FILENAME)
    (output / FILENAME).chmod(0o444)
    notices = user_install.safe_parents(destination / 'licenses/desktop-font')
    notices.mkdir(parents=True, exist_ok=True)
    for record in pin['notices']:
        copied = notices / Path(record['path']).name
        shutil.copyfile(root / record['path'], copied)
        if hashlib.sha256(copied.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Font notice changed while packaging')
        copied.chmod(0o444)
    verify_bytes(output / FILENAME, pin)
    return pin


def locations(home=None):
    home = Path.home() if home is None else Path(home)
    data = Path(os.environ.get('XDG_DATA_HOME') or home / '.local/share')
    state = Path(os.environ.get('XDG_STATE_HOME') or home / '.local/state')
    if not data.is_absolute() or not state.is_absolute():
        raise ValueError('XDG font/state paths must be absolute')
    return data, state / 'omabuntu'


def file_state(path):
    user_install.safe_parents(path.parent)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('Unsafe user font path')
    if not path.exists():
        return {'existed': False}
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Existing font file exceeds limit')
    return {'existed': True, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'mode': path.stat().st_mode & 0o777}


def plan(root=ROOT, home=None):
    pin = inputs(root)
    data, state = locations(home)
    target = data / 'fonts/omabuntu' / pin['sha256'][:16]
    expected = {FILENAME: pin['sha256'],
                **{Path(item['path']).name: item['sha256'] for item in pin['notices']}}
    before = {name: file_state(target / name) for name in expected}
    blockers = ['User font file conflicts: ' + name for name, item in before.items()
                if item['existed'] and item['sha256'] != expected[name]]
    return {'schema_version': 1, 'kind': 'omabuntu-user-font', 'root': str(root.absolute()),
            'home': str((Path.home() if home is None else Path(home)).absolute()),
            'target': str(target), 'state': str(state), 'pin_digest': guided.digest(pin),
            'before': before, 'blockers': blockers,
            'status': 'blocked' if blockers else 'review-required'}


def apply(reviewed, approval, fetch=bootstrap_sources.fetch, execute=run):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Install the user font as your normal user, not via sudo')
    if guided.digest(reviewed) != approval or reviewed.get('kind') != 'omabuntu-user-font' or reviewed.get('blockers'):
        raise ValueError('Font approval differs or local files conflict')
    root = Path(reviewed['root'])
    if plan(root, Path(reviewed['home'])) != reviewed:
        raise ValueError('Font destination/state changed; review again')
    source = obtain(root, fetch, execute)
    # Download/probes can take time. Preserve edits made during that time.
    if plan(root, Path(reviewed['home'])) != reviewed:
        raise ValueError('User font changed during download; no installation performed')
    pin = inputs(root)
    state = user_install.private_directory(Path(reviewed['state']))
    journal_dir = user_install.private_directory(state / 'font-transactions' / user_install.stamp())
    record = {'status': 'prepared', 'plan': reviewed, 'preferences_changed': False}
    journal = journal_dir / 'transaction.json'
    for name, before in reviewed['before'].items():
        if before['existed']:
            shutil.copyfile(Path(reviewed['target']) / name, journal_dir / name)
    user_install.atomic_json(journal, record)
    try:
        target = user_install.safe_parents(Path(reviewed['target']))
        target.mkdir(parents=True, exist_ok=True)
        files = {FILENAME: source, **{Path(item['path']).name: root / item['path'] for item in pin['notices']}}
        expected = {FILENAME: pin['sha256'], **{Path(item['path']).name: item['sha256'] for item in pin['notices']}}
        for name, input_file in files.items():
            if not reviewed['before'][name]['existed']:
                data = input_file.read_bytes()
                if hashlib.sha256(data).hexdigest() != expected[name]:
                    raise ValueError('Font input changed before installation')
                with (target / name).open('xb') as stream:
                    stream.write(data)
                (target / name).chmod(0o644)
        verify_bytes(target / FILENAME, pin)
        execute(['fc-cache', '-f', str(target)], timeout=60)
        family = execute(['fc-match', '--format=%{family[0]}\n', pin['family']]).strip()
        charset = execute(['fc-match', '--format=%{charset}\n', pin['family']])
        if family != pin['family'] or not charset_contains(charset, pin['required_glyphs']):
            raise ValueError('Font files installed but fontconfig did not resolve the expected family/glyphs')
        record['status'] = 'installed-and-resolved'
    except BaseException as error:
        record.update(status='incomplete-review-required', error=type(error).__name__)
        user_install.atomic_json(journal, record)
        raise
    user_install.atomic_json(journal, record)
    return {'status': record['status'], 'journal': str(journal), 'preferences_changed': False,
            'desktop_restarted': False}
