"""Owned, additive activation-focus settings; independent of application switching."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import native_compatibility
import user_install as u

ARTIFACT = 'config/hypr/focus-policy.lua'
NAME = 'omabuntu-focus.lua'
INCLUDE = 'require("omabuntu-focus")'
MARKER = '-- Omabuntu activation focus policy (plan 125).'
PAYLOAD = (MARKER + '\n'
           '-- Match Omarchy v4.5.0 looknfeel.lua at ac2690cd: honor application focus requests.\n'
           '-- This is global, not a browser-only rule; no launch command or profile is changed.\n'
           'hl.config({ misc = { focus_on_activate = true } })\n')
PAYLOAD = '-- SPDX-License-Identifier: MIT\n' + PAYLOAD


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read(path):
    u.safe_parents(path.parent)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('Unsafe focus-policy file')
    if not path.exists():
        return None
    if path.stat().st_uid != os.getuid() or path.stat().st_size > 131072:
        raise ValueError('Focus-policy file must be owned and bounded')
    return path.read_bytes().decode('utf-8')


def state(path):
    text = read(path)
    return ({'existed': False} if text is None else
            {'existed': True, 'sha256': hashlib.sha256(text.encode()).hexdigest(),
             'mode': path.stat().st_mode & 0o777})


def write(path, data, mode):
    u.safe_parents(path.parent)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.omabuntu-focus-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


class Host:
    def command(self, *args):
        try:
            process = subprocess.run(['hyprctl', *args], capture_output=True, text=True, timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError('Compositor focus-policy probe missing or timed out') from error
        if process.returncode:
            raise ValueError('Compositor focus-policy command failed')
        return process.stdout.strip()

    def context(self, recovery=False):
        # Never discover/control an unrelated session from GNOME or another tty.
        process = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'Hyprland'],
                                 capture_output=True, timeout=5, check=False)
        if process.returncode == 1: return {'live': False}
        if process.returncode != 0: raise ValueError('Cannot determine compositor state')
        if ('hyprland' not in os.environ.get('XDG_CURRENT_DESKTOP', '').lower().split(':')
                or not os.environ.get('HYPRLAND_INSTANCE_SIGNATURE')):
            raise ValueError('Hyprland is running outside this terminal; focus configuration deferred')
        version = json.loads(self.command('-j', 'version'))
        if not native_compatibility.hyprland_metadata(version, 'running compositor')['ok']:
            raise ValueError('Unsupported compositor for focus-policy deployment')
        if not recovery and self.command('configerrors'):
            raise ValueError('Resolve compositor configuration errors before focus deployment')
        return {'live': True, 'focus': self.option('misc:focus_on_activate'),
                'autoreload': self.option('misc:disable_autoreload'),
                'signature': os.environ['HYPRLAND_INSTANCE_SIGNATURE']}

    def option(self, name):
        value = json.loads(self.command('-j', 'getoption', name))
        if type(value.get('bool')) is not bool: raise ValueError('Unknown compositor option representation')
        return value['bool']

    def guard(self, disabled):
        result = self.command('eval', 'hl.config({ misc = { disable_autoreload = ' + str(disabled).lower() + ' } })')
        if result != 'ok' or self.option('misc:disable_autoreload') != disabled:
            raise ValueError('Failed to set automatic reload guard')

    def focus(self, enabled):
        if self.command('eval', 'hl.config({ misc = { focus_on_activate = ' + str(enabled).lower() + ' } })') != 'ok':
            raise ValueError('Failed to restore prior focus runtime option')

    def reload(self):
        if self.command('reload') not in ('', 'ok') or self.command('configerrors'):
            raise ValueError('Focus-policy reload failed; inspect private recovery journal')


def paths(app, directory):
    return {'entry': directory / 'hyprland.lua', 'module': directory / NAME}


def plan(app, directory=None, host=None):
    selected = app.selected()
    if not isinstance(selected, str): return {'status': 'not-shipped'}
    bundle = app.root / selected
    meta = u.verify_bundle(bundle, installed=True)
    if not isinstance(meta, dict) or ARTIFACT not in meta.get('files', {}):
        return {'status': 'not-shipped'}
    if read(bundle / ARTIFACT) != PAYLOAD:
        raise ValueError('Unreviewed focus-policy payload in selected bundle')
    if directory is None:
        config = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
        if not config.is_absolute(): raise ValueError('XDG_CONFIG_HOME must be absolute')
        directory = config / 'hypr'
    directory = Path(directory).absolute()
    targets = paths(app, directory)
    before = {key: state(path) for key, path in targets.items()}
    entry, module = read(targets['entry']), read(targets['module'])
    if entry is None: return {'status': 'deferred-no-profile'}
    blockers = []
    if not entry.endswith('\n'): blockers.append('Hyprland entry must end with a newline')
    if module is not None and module != PAYLOAD:
        blockers.append('Existing focus module was edited or is unowned; preserve it for manual review')
    references = [line for line in entry.splitlines() if 'omabuntu-focus' in line]
    if references and references != [INCLUDE]:
        blockers.append('Ambiguous or duplicate focus include; manual review required')
    payload = {'entry': entry if references else entry + '\n' + MARKER + '\n' + INCLUDE + '\n',
               'module': PAYLOAD}
    changes = [key for key in targets if read(targets[key]) != payload[key]]
    runtime = (host or Host()).context()
    reload_needed = runtime['live'] and (bool(changes) or not runtime['focus'])
    return {'kind': 'omabuntu-focus-policy-v1', 'status': 'blocked' if blockers else 'review-required',
            'directory': str(directory), 'state': str(app.state), 'release_digest': digest(meta),
            'paths': {key: str(path) for key, path in targets.items()}, 'before': before,
            'payload': payload, 'changes': changes, 'runtime': runtime,
            'reload': reload_needed, 'blockers': blockers}


def pending(app):
    parent = app.state / 'focus-policy-transactions'
    u.safe_parents(parent)
    return [path for path in parent.glob('*/transaction.json')
            if u.read_json(path).get('status') not in ('completed', 'restored')]


def _recover(app, path, host=None):
    host = host or Host()
    path = Path(path).absolute()
    parent = app.state / 'focus-policy-transactions'
    u.safe_parents(path.parent)
    if path.parent.parent != parent or path.name != 'transaction.json':
        raise ValueError('Focus journal is outside the installation state')
    journal = u.read_json(path)
    reviewed = journal['plan']
    if (reviewed.get('kind') != 'omabuntu-focus-policy-v1' or digest(reviewed) != journal['approval']
            or reviewed['state'] != str(app.state)
            or reviewed['paths'] != {key: str(value) for key, value in paths(app, Path(reviewed['directory'])).items()}):
        raise ValueError('Invalid focus-policy journal')
    saved = {}
    for key in reviewed['changes']:
        target = Path(reviewed['paths'][key]);current = state(target);prior = reviewed['before'][key]
        installed = {'existed': True, 'sha256': hashlib.sha256(reviewed['payload'][key].encode()).hexdigest(),
                     'mode': prior.get('mode', 0o644)}
        if current not in (prior, installed): raise ValueError('Concurrent focus configuration edit; manual recovery required')
        if prior['existed']:
            backup = path.parent / key
            data = read(backup)
            if data is None or hashlib.sha256(data.encode()).hexdigest() != prior['sha256']:
                raise ValueError('Focus backup integrity differs')
            saved[key] = data.encode()
    now = host.context(recovery=True)
    original = reviewed['runtime']
    if now['live'] != original['live'] or (now['live'] and now['signature'] != original['signature']):
        raise ValueError('Session changed; manual focus recovery required')
    journal['status'] = 'restoring';u.atomic_json(path, journal)
    if now['live']: host.guard(True)
    for key in reversed(reviewed['changes']):
        target = Path(reviewed['paths'][key]);prior = reviewed['before'][key]
        if prior['existed']: write(target, saved[key], prior['mode'])
        elif target.exists(): target.unlink()
    if now['live']:
        host.reload()
        host.guard(original['autoreload'])
        if host.option('misc:focus_on_activate') != original['focus']:
            host.focus(original['focus'])
        if host.option('misc:focus_on_activate') != original['focus']:
            raise ValueError('Failed to restore prior runtime focus state')
    journal['status'] = 'restored';u.atomic_json(path, journal)
    return {'status': 'restored', 'journal': str(path)}


def recover(app, path, host=None):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Focus recovery is per-user; never use sudo')
    u.private_directory(app.state)
    with os.fdopen(os.open(app.state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600), 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        app.require_settled()
        return _recover(app, path, host)


def apply(app, reviewed, approval, host=None):
    host = host or Host()
    if os.getuid() == 0 or os.environ.get('SUDO_USER'): raise ValueError('Focus policy is per-user; never use sudo')
    if digest(reviewed) != approval or reviewed.get('blockers') or reviewed.get('kind') != 'omabuntu-focus-policy-v1':
        raise ValueError('Focus policy needs the exact unblocked approval')
    u.private_directory(app.state)
    with os.fdopen(os.open(app.state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600), 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        app.require_settled()
        if pending(app): raise ValueError('Interrupted focus policy requires recovery first')
        if plan(app, reviewed['directory'], host) != reviewed: raise ValueError('Focus inputs changed; review again')
        if not reviewed['changes'] and not reviewed['reload']: return {'status': 'current'}
        parent = u.private_directory(app.state / 'focus-policy-transactions')
        case = u.private_directory(parent / u.stamp())
        for key in reviewed['changes']:
            if reviewed['before'][key]['existed']:
                write(case / key, Path(reviewed['paths'][key]).read_bytes(), 0o600)
        path = case / 'transaction.json'
        journal = {'status': 'prepared', 'plan': reviewed, 'approval': approval}
        u.atomic_json(path, journal)
        try:
            if reviewed['runtime']['live']: host.guard(True)
            # The include is written last, after the complete owned module.
            for key in ('module', 'entry'):
                if key not in reviewed['changes']: continue
                target = Path(reviewed['paths'][key])
                if state(target) != reviewed['before'][key]: raise ValueError('Focus input changed before write')
                write(target, reviewed['payload'][key].encode(), reviewed['before'][key].get('mode', 0o644))
            journal['status'] = 'written';u.atomic_json(path, journal)
            if reviewed['runtime']['live']:
                host.reload()
                if not host.option('misc:focus_on_activate'): raise ValueError('Personal overrides block the focus default')
                host.guard(reviewed['runtime']['autoreload'])
            journal['status'] = 'completed';u.atomic_json(path, journal)
        except BaseException:
            journal['status'] = 'recovery-required';u.atomic_json(path, journal)
            _recover(app, path, host)
            raise
    return {'status': 'applied-live' if reviewed['runtime']['live'] else 'staged-next-login', 'journal': str(path)}


def ensure(app, confirm, emit=print, *, directory=None, host=None):
    """Independent, disclosed follow-up; never roll back a successful app switch."""
    try:
        reviewed = plan(app, directory, host)
        if reviewed['status'] in ('not-shipped', 'deferred-no-profile'):
            if reviewed['status'] == 'deferred-no-profile': emit('Focus policy deferred until a Hyprland profile exists; fresh session defaults enable it.')
            return {'status': reviewed['status']}
        if reviewed['blockers']:
            emit('Focus policy requires manual review: ' + '; '.join(reviewed['blockers']))
            return {'status': 'blocked', 'blockers': reviewed['blockers']}
        if pending(app): raise ValueError('Interrupted focus policy requires recovery before another deployment')
        if not reviewed['changes'] and not reviewed['reload']:
            emit('Original activation focus policy already current; no write or reload.')
            return {'status': 'current'}
        emit('Separate focus-policy stage: eligible applications may focus existing windows, including on hidden workspaces.')
        emit('Adds only a dedicated managed module/include with backups; no browser profile, bindings or monitor changes.')
        question = ('Apply the original activation-focus default and reload this Hyprland configuration?' if reviewed['runtime']['live']
                    else 'Stage the original activation-focus default for the next Hyprland login?')
        if not confirm(question): return {'status': 'deferred-by-user'}
        result = apply(app, reviewed, digest(reviewed), host)
        emit('Focus policy: ' + result['status'])
        return result
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        emit('Application release preserved; focus policy deferred/failed: ' + str(error))
        return {'status': 'failed', 'reason': str(error)}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'apply', 'recover'))
    parser.add_argument('--config-dir', type=Path)
    parser.add_argument('--review-out', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--approval')
    parser.add_argument('--journal', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    app = u.Installation(*u.defaults())
    if args.action == 'plan':
        reviewed = plan(app, args.config_dir)
        if args.review_out:
            destination = args.review_out.absolute()
            u.private_directory(destination.parent)
            if destination.exists() or destination.is_symlink(): parser.error('Review destination exists')
            u.atomic_json(destination, reviewed)
        result = {key: reviewed[key] for key in ('status', 'changes', 'reload', 'blockers') if key in reviewed}
        result['approval'] = digest(reviewed)
    else:
        if not args.apply: parser.error('An explicit --apply grant is required')
        if args.action == 'recover':
            if not args.journal: parser.error('Recovery requires --journal')
            result = recover(app, args.journal)
        else:
            if not args.review or not args.approval: parser.error('Apply requires --review and --approval')
            result = apply(app, u.read_json(args.review), args.approval)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
