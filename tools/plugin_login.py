"""Opt-in next-login reload of an already built, enabled and receipted plugin.

No downloads, compiler, sudo, enable/disable, configuration reload or supervision.
A failure leaves the desktop running without attempting unload or recovery.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def regular(path, limit=2 * 1024 * 1024):
    path = Path(path)
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('Linked login input is not accepted')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError('Login input is not a bounded regular file')
    return path.read_bytes()


def read_json(path):
    value = json.loads(regular(path))
    if not isinstance(value, dict):
        raise ValueError('Invalid login receipt or policy')
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def probe(argv):
    return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, check=True, timeout=30).stdout.strip()


def fingerprint(path, limit=65536):
    data = regular(path, limit)
    info = path.stat()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'uid': info.st_uid,
            'gid': info.st_gid, 'mode': info.st_mode & 0o7777}


def validate_header(data, native):
    macros = dict(re.findall(r'^#define\s+(\w+)\s+"([^"\n]*)"\s*$', data.decode(), re.M))
    if macros.get('GIT_COMMIT_HASH') != native.get('commit') or macros.get('GIT_DIRTY') != 'clean':
        raise ValueError('Installed header commit/clean state differs')
    for macro, field in (('AQUAMARINE_VERSION', 'buildAquamarine'), ('HYPRLANG_VERSION', 'buildHyprlang'),
                         ('HYPRUTILS_VERSION', 'buildHyprutils'), ('HYPRCURSOR_VERSION', 'buildHyprcursor'),
                         ('HYPRGRAPHICS_VERSION', 'buildHyprgraphics')):
        if native.get(field) is not None and macros.get(macro) != native[field]:
            raise ValueError('Installed header dependency version differs: ' + macro)


def validate_pc(data, native, include):
    text = data.decode()
    if (not re.search(r'^Version:\s*' + re.escape(native['version']) + r'\s*$', text, re.M)
            or not re.search(r'^prefix=' + re.escape(str(include)) + r'\s*$', text, re.M)):
        raise ValueError('Installed header pkg-config version/prefix differs')


def system_headers(native, inspect=probe):
    pc = Path('/usr/share/pkgconfig/hyprland.pc')
    header = Path('/usr/include/hyprland/src/version.h')
    files = {}
    for path in (pc, header):
        value = fingerprint(path)
        if value['uid'] != 0 or value['mode'] & 0o022:
            raise ValueError('System header inputs are not protected root-owned files')
        owner = inspect(['dpkg-query', '-S', str(path)]).strip()
        if not re.fullmatch(r'hyprland(?::amd64)?: ' + re.escape(str(path)), owner):
            raise ValueError('System header input is not owned by the Hyprland package')
        files[str(path)] = value
    validate_pc(regular(pc, 65536), native, Path('/usr/include'))
    validate_header(regular(header, 65536), native)
    # Fingerprint the bytes actually validated, not just an earlier snapshot.
    if files != {str(path): fingerprint(path) for path in (pc, header)}:
        raise ValueError('System header inputs changed during validation')
    return {'layout': 'system-package', 'files': files}


def header_state(directory, native, inspect=probe):
    headers = Path(directory) / 'headersRoot'
    for path in (headers, *headers.parents):
        if path.is_symlink():
            raise ValueError('Linked header cache is not accepted')
    if not headers.is_dir():
        raise ValueError('Existing manager header directory is required; no privileged initialization')
    pc = headers / 'share/pkgconfig/hyprland.pc'
    header = headers / 'include/hyprland/src/version.h'
    if not any(headers.iterdir()):
        # Reviewed PPA patch 99-hyprpm-global-headers permits an empty cache.
        # Incomplete/nonempty cache must never fall through to system headers.
        return system_headers(native, inspect)
    files = {str(path): fingerprint(path) for path in (pc, header)}
    validate_pc(regular(pc, 65536), native, headers / 'include')
    validate_header(regular(header, 65536), native)
    if files != {str(path): fingerprint(path) for path in (pc, header)}:
        raise ValueError('Cache headers changed during validation')
    return {'layout': 'cache', 'files': files}


def transaction_complete(journal):
    record = read_json(journal)
    if record.get('status') == 'completed':
        return True
    resolution_path = journal.with_name('resolution.json')
    if not resolution_path.exists():
        return False
    resolution = read_json(resolution_path)
    recovery_path = Path(resolution.get('recovery_journal', ''))
    if (record.get('status') != 'manual-review-required'
            or record.get('plan', {}).get('kind') != 'omabuntu-hyprpm-migration'
            or resolution.get('kind') != 'omabuntu-hyprpm-recovery-resolution'
            or resolution.get('original_sha256') != hashlib.sha256(regular(journal)).hexdigest()
            or not recovery_path.is_absolute() or recovery_path.name != 'transaction.json'
            or recovery_path.parent.parent != journal.parent.parent
            or recovery_path == journal):
        return False
    recovery = read_json(recovery_path)
    origin = recovery.get('plan', {}).get('recovery', {})
    return (recovery.get('status') == 'completed'
            and recovery.get('plan', {}).get('kind') == 'omabuntu-hyprpm-recovery'
            and origin.get('journal') == str(journal)
            and origin.get('sha256') == resolution.get('original_sha256')
            and resolution.get('recovery_sha256') == hashlib.sha256(regular(recovery_path)).hexdigest())


def review(root=ROOT, home=None, directory=None, inspect=probe, require_login=True):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Plugin login is normal-user only')
    home = Path.home() if home is None else Path(home)
    config = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
    state = Path(os.environ.get('XDG_STATE_HOME') or home / '.local/state') / 'omabuntu'
    if not config.is_absolute() or not state.is_absolute():
        raise ValueError('Login XDG paths must be absolute')
    directory = Path('/var/cache/hyprpm') / pwd.getpwuid(os.getuid()).pw_name if directory is None else Path(directory)
    activation = read_json(state / 'session-activation.json')
    if ((require_login and activation.get('plugin_login_enabled') is not True)
            or activation.get('library') is not None):
        raise ValueError('No manager-mode next-login grant')
    if activation.get('release') != 'releases/' + root.name:
        raise ValueError('Login helper and activation release differ')
    files = activation.get('files', {})
    if not isinstance(files, dict):
        raise ValueError('Invalid activation file receipt')
    for name, path in (('activation', config / 'hypr/omabuntu-activation.lua'),
                       ('titlebars', config / 'hypr/omabuntu-titlebars.lua')):
        if hashlib.sha256(regular(path, 65536)).hexdigest() != files.get(name):
            raise ValueError('Owned titlebar/activation configuration changed')
    policy = read_json(root / 'native/hyprpm.json')
    receipt = read_json(state / 'hyprpm.json')
    if (policy.get('manager') != 'hyprpm' or policy.get('plugin') != 'hyprbars'
            or policy.get('repository') != 'https://github.com/hyprwm/hyprland-plugins'
            or receipt.get('policy_digest') != digest(policy) or receipt.get('activated') is not True):
        raise ValueError('No matching successful enabled manager receipt')
    for parent, allowed in (('plugin-transactions', ('completed',)),
                            ('activation-transactions', ('completed', 'restored-after-failure')),
                            ('session-transactions', ('completed', 'restored-after-failure'))):
        for journal in (state / parent).glob('*/transaction.json'):
            complete = (transaction_complete(journal) if parent == 'plugin-transactions'
                        else read_json(journal).get('status') in allowed)
            if not complete:
                raise ValueError('Unresolved plugin/session transaction')
    native = json.loads(inspect(['Hyprland', '--version-json']))
    running = json.loads(inspect(['hyprctl', '-j', 'version']))
    target = policy.get('targets', {}).get(native.get('version'), {})
    expected = receipt.get('native', {})
    if (target.get('apply_reviewed') is not True or native.get('dirty') is not False
            or native.get('commit') != target.get('hyprland_commit')
            or expected != native
            or not isinstance(native.get('abiHash'), str) or not native['abiHash']
            or running.get('abiHash') != native['abiHash']
            or running.get('commit') != native.get('commit')
            or not isinstance(running.get('flags', []), (list, str)) or 'dirty' in running.get('flags', [])):
        raise ValueError('Installed/running/built compositor identities differ')
    # DataState::getGlobalState may create cache directories via sudo if these
    # are missing. Refuse before invoking even the otherwise read-only reload.
    headers = header_state(directory, native, inspect)
    if receipt.get('headers') is not None and receipt['headers'] != headers:
        raise ValueError('Manager header inputs changed')
    global_state = tomllib.loads(regular(directory / 'state.toml').decode())
    if global_state.get('state', {}).get('hash') != native['abiHash']:
        raise ValueError('Manager headers ABI changed')
    repositories = list(directory.glob('*/state.toml'))
    if repositories != [directory / 'hyprland-plugins/state.toml']:
        raise ValueError('Manager repository ownership changed')
    data = tomllib.loads(regular(repositories[0]).decode())
    repository = data.get('repository', {})
    if (repository.get('name') != 'hyprland-plugins' or repository.get('url') != policy['repository']
            or repository.get('rev') != target['plugin_commit']
            or repository.get('hash') != target['plugin_commit']):
        raise ValueError('Manager revision changed')
    enabled = sorted(name for name, item in data.items()
                     if name != 'repository' and isinstance(item, dict) and item.get('enabled'))
    if (enabled != ['hyprbars'] or data['hyprbars'].get('failed') is not False
            or data['hyprbars'].get('filename') != 'hyprbars.so'):
        raise ValueError('Only the successful receipted hyprbars may be enabled')
    library = directory / 'hyprland-plugins/hyprbars.so'
    if (receipt.get('library') != str(library)
            or hashlib.sha256(regular(library, 64 * 1024 * 1024)).hexdigest() != receipt.get('library_sha256')):
        raise ValueError('Manager library changed')
    loaded = json.loads(inspect(['hyprctl', '-j', 'plugin', 'list']))
    if not isinstance(loaded, list) or any(not isinstance(p, dict) or p.get('name') != 'hyprbars' for p in loaded):
        raise ValueError('Unrelated loaded plugins prevent manager reconciliation')
    return {'already_loaded': bool(loaded), 'titlebars': str(config / 'hypr/omabuntu-titlebars.lua'),
            'headers': headers}


def run(root=ROOT, home=None, directory=None, inspect=probe, configure_only=False):
    review(root, home, directory, inspect, require_login=not configure_only)  # Require an existing valid grant before opening its lock.
    home = Path.home() if home is None else Path(home)
    state = Path(os.environ.get('XDG_STATE_HOME') or home / '.local/state') / 'omabuntu'
    lock_path = state / 'control.lock'
    regular(lock_path, 4096)
    fd = os.open(lock_path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return reload_reviewed(root, home, directory, inspect, configure_only)


def reload_reviewed(root, home, directory, inspect, configure_only=False):
    reviewed = review(root, home, directory, inspect, require_login=not configure_only)
    if reviewed['already_loaded'] and not configure_only:
        # The normal activation include already applied the rules in this case.
        return {'status': 'already-loaded', 'configuration_reloaded': False}
    if review(root, home, directory, inspect, require_login=not configure_only) != reviewed:
        raise ValueError('Plugin state changed before titlebar handling')
    if configure_only:
        if not reviewed['already_loaded']:
            raise ValueError('Explicit titlebar application requires an already loaded plugin')
    else:
        inspect(['hyprpm', 'reload'])
        after = review(root, home, directory, inspect)
        if not after['already_loaded']:
            raise ValueError('Manager returned without loading hyprbars')
    program = 'assert(hl.plugin.hyprbars, "hyprbars is not loaded"); dofile(' + json.dumps(reviewed['titlebars'], ensure_ascii=False) + ')'
    if inspect(['hyprctl', 'eval', program]) != 'ok':
        raise ValueError('Titlebar rule application failed')
    return {'status': 'loaded-and-configured', 'configuration_reloaded': False}


if __name__ == '__main__':
    try:
        print(json.dumps(run()))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError) as error:
        raise SystemExit('Omabuntu plugin login refused: ' + type(error).__name__ + ': ' + str(error))
