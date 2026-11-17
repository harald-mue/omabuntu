#!/usr/bin/env python3
"""Review/apply/recover a backed-up existing-user monitor-workspace migration.

Default operation is read-only. Apply needs the exact plan digest, a verified
installed candidate and explicit desktop approval. Never installs a release,
changes services, logs out, or modifies monitor geometry. Reports are private.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import session_config
import user_install
import workspace_migration as migration

KIND = 'omabuntu-monitor-workspace-deployment-v1'
CONFIG_NAMES = {'entry': 'hyprland.lua', 'policy': 'omabuntu-monitor-workspaces.lua',
                'bindings': 'omabuntu-workspace-bindings.lua'}
STATE_NAMES = {'marker': 'monitor-workspaces-policy', 'layouts': 'current/workspace-layouts.txt',
               'blocks': 'monitor-workspaces', 'merged': 'monitor-workspaces-merged'}
ARTIFACTS = ('config/hypr/monitor-workspaces.lua', 'config/hypr/monitor-workspace-bindings.lua',
             'shell/MonitorWorkspaces.qml', 'shell/LiveStatus.qml', 'shell/Commons/TrialDesktopState.qml')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def paths_for(config, state):
    return {**{key: Path(config) / name for key, name in CONFIG_NAMES.items()},
            **{key: Path(state) / name for key, name in STATE_NAMES.items()}}


def read(path):
    user_install.safe_parents(path.parent)
    return migration.bounded_text(path)


def file_state(path):
    text = read(path)
    if not path.exists():
        return {'existed': False}
    return {'existed': True, 'sha256': hashlib.sha256(text.encode()).hexdigest(),
            'mode': path.stat().st_mode & 0o777}


def binding_chord(row):
    code = int(row.get('keycode') or 0)
    key = str(row.get('key', '')).lower()
    if code:
        key = 'code:' + str(code)
    elif key in '1234567890' and len(key) == 1:
        key = 'code:' + str('1234567890'.index(key) + 10)
    return int(row['modmask']), key


def target_chords():
    result = {(mods, 'code:' + str(code)) for mods in (64, 65, 73) for code in range(10, 20)}
    result.update((mods, direction) for mods in (69, 73) for direction in ('left', 'right', 'up', 'down'))
    result.update((mods, 'tab') for mods in (64, 65, 68, 12, 13))
    result.update((64, key) for key in ('mouse_up', 'mouse_down'))
    return result


def binding_blockers(rows):
    legacy = {(mods, 'code:' + str(slot + 9)): label + str(slot)
              for mods, label in ((64, 'Switch to workspace '), (65, 'Move window to workspace '))
              for slot in range(1, 11)}
    seen, blockers, desired = set(), [], target_chords()
    for row in rows:
        if row.get('submap') and not row.get('submap_universal'):
            continue
        chord = binding_chord(row)
        if row.get('catch_all') and chord[0] in {mods for mods, _ in desired}:
            blockers.append('A catch-all binding needs manual review before workspace migration')
        if chord in desired:
            if chord in seen or row.get('description') != legacy.get(chord) or chord not in legacy:
                blockers.append('An existing binding conflicts with the monitor-local workspace chords')
            seen.add(chord)
    if not set(legacy).issubset(seen):
        blockers.append('The live legacy numeric bindings differ from the reviewed configuration')
    return blockers


class Host:
    def command(self, *args):
        try:
            result = subprocess.run(['hyprctl', *args], capture_output=True, text=True, timeout=15, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired) as error:
            raise ValueError('Missing/timed-out compositor command: ' + args[0]) from error
        if result.returncode:
            raise ValueError('Compositor command failed: ' + args[0])
        return result.stdout.strip()

    def evaluate(self, script):
        if self.command('eval', script + '\nreturn "ok"') != 'ok':
            raise ValueError('Compositor rejected workspace migration eval')

    def autoreload(self):
        data = json.loads(self.command('-j', 'getoption', 'misc:disable_autoreload'))
        if type(data.get('bool')) is not bool:
            raise ValueError('Unknown disable_autoreload option representation')
        return data['bool']

    def set_autoreload(self, disabled):
        self.evaluate('hl.config({ misc = { disable_autoreload = ' + str(disabled).lower() + ' } })')
        if self.autoreload() != disabled:
            raise ValueError('Automatic config reload guard was not applied')

    def bindings(self):
        rows = json.loads(self.command('-j', 'binds'))
        keys = ('modmask', 'key', 'keycode', 'description', 'dispatcher', 'submap',
                'submap_universal', 'catch_all', 'release', 'repeat', 'locked', 'mouse')
        # Arguments may contain private application commands; retain only hashes.
        return sorted(({key: row.get(key) for key in keys} |
                       {'arg_sha256': hashlib.sha256(str(row.get('arg', '')).encode()).hexdigest()}
                       for row in rows), key=lambda row: json.dumps(row, sort_keys=True))

    def state_home(self):
        # 0.57.0 eval reports only success/errors; repl also returns values.
        return self.command('repl', 'return os.getenv("OMABUNTU_STATE_HOME") or '
                            '((os.getenv("XDG_STATE_HOME") or ((os.getenv("HOME") or "") .. "/.local/state")) .. "/omabuntu")')

    def errors(self):
        return self.command('configerrors')

    def reload(self):
        if self.command('reload') not in ('ok', ''):
            raise ValueError('Unexpected config reload response')
        if self.errors():
            raise ValueError('Reload reported configuration errors')

    def snapshot(self):
        version = json.loads(self.command('-j', 'version'))
        if (version.get('version') != '0.57.0' or version.get('commit') != '0aa6745f705f2c4b0a5004eb019ef76e5bbdb426'
                or version.get('dirty') is not False):
            raise ValueError('Live workspace migration requires the reviewed Hyprland 0.57.0 API')
        monitors = [{key: m.get(key) for key in ('id', 'name', 'description', 'mirrorOf', 'x', 'y',
                     'width', 'height', 'scale', 'transform')} for m in json.loads(self.command('-j', 'monitors'))]
        workspaces = [{key: w.get(key) for key in ('id', 'monitor', 'windows', 'tiledLayout')}
                      for w in json.loads(self.command('-j', 'workspaces')) if w.get('id', 0) > 0]
        clients = [{key: w.get(key) for key in ('address', 'monitor', 'floating', 'fullscreen', 'tags')}
                   | {'workspace': (w.get('workspace') or {}).get('id')}
                   for w in json.loads(self.command('-j', 'clients'))]
        return {'monitors': sorted(monitors, key=lambda m: m['name']),
                'workspaces': sorted(workspaces, key=lambda w: w['id']),
                'clients': sorted(clients, key=lambda w: w['address'])}

    def preflight_inverse(self, before, mapping):
        self.evaluate(inverse_program(before, mapping, validate_only=True))

    def inverse(self, before, mapping):
        self.evaluate(inverse_program(before, mapping))


def inverse_program(before, mapping, validate_only=False):
    """Validate all original memberships before undoing any ID; no window moves."""
    checks, changes = [], []
    clients = before['clients']
    for row in mapping['workspaces']:
        old, new = row['old_id'], row['new_id']
        if old == new:
            continue
        addresses = sorted(w['address'] for w in clients if w['workspace'] == old)
        # Empty out-of-block workspaces are not accepted by the initial plan.
        checks.append('''do
  local old, new = %d, %d
  local source = hl.get_workspace(new)
  local original = hl.get_workspace(old)
  assert(not (source and original), "Rollback destination occupied")
  local actual = source or original
  assert(actual and actual.monitor and actual.monitor.name == %s, "Rollback output changed")
  local expected = %s
  local found = {}
  for _, window in ipairs(hl.get_workspace_windows(actual.id)) do found[#found+1] = window.address end
  table.sort(found)
  assert(#found == #expected, "Rollback membership changed")
  for i, address in ipairs(expected) do assert(found[i] == address, "Rollback window identity changed") end
end''' % (old, new, json.dumps(row['monitor']), '{' + ','.join(json.dumps(a) for a in addresses) + '}'))
        changes.append('''if hl.get_workspace(%d) then
  hl.dispatch(hl.dsp.workspace.change_id({ workspace = "%d", id = %d }))
  assert(hl.get_workspace(%d) and not hl.get_workspace(%d), "Inverse renumber failed")
end''' % (new, new, old, old, new))
        changes.append('''for _, window in ipairs(hl.get_windows()) do
  for _, tag in ipairs(window.tags or {}) do
    local clean = tag:gsub("%%*$", "")
    if clean == "omabuntu-minimized-from-%d" then
      local target = "address:" .. window.address
      hl.dispatch(hl.dsp.window.tag({ tag = "-" .. clean, window = target }))
      hl.dispatch(hl.dsp.window.tag({ tag = "+omabuntu-minimized-from-%d", window = target }))
    end
  end
end''' % (new, old))
    return '\n'.join(checks if validate_only else checks + changes)


def plan(app, config, bundle=None, host=None):
    host = host or Host()
    app.require_settled()
    selected = app.selected()
    if selected is None:
        raise ValueError('No installed application release')
    release = Path(bundle) if bundle is not None else app.root / selected
    meta = user_install.verify_bundle(release, installed=bundle is None)
    if any(name not in meta['files'] for name in ARTIFACTS):
        raise ValueError('Candidate lacks sealed monitor workspace artifacts')
    paths = paths_for(Path(config).absolute(), app.state)
    before = {key: file_state(path) for key, path in paths.items()}
    if before['policy']['existed'] or before['bindings']['existed'] or before['marker']['existed']:
        raise ValueError('Existing workspace policy requires ownership/recovery review, not another migration')
    if host.errors():
        raise ValueError('Resolve current compositor configuration errors first')
    snapshot = host.snapshot()
    if host.snapshot() != snapshot:
        raise ValueError('Desktop state changed during inspection; review again')
    # Check errors/version before repl: the official evaluator clears its error list.
    if host.state_home() != str(app.state):
        raise ValueError('Compositor and shell workspace state directories differ')
    if read(paths['merged']).strip():
        raise ValueError('Existing merged workspace history needs explicit attribution before initial migration')
    bindings = host.bindings()
    layouts, blocks = read(paths['layouts']), read(paths['blocks'])
    mapped = migration.preview(snapshot['monitors'], snapshot['workspaces'], layouts, blocks)
    mapped['blockers'].extend(binding_blockers(bindings))
    for row in mapped['workspaces']:
        if row['old_id'] != row['new_id'] and not row['windows']:
            mapped['blockers'].append('Empty out-of-block workspace must be attributed or closed before migration')
    payload = {'entry': migration.configuration_patch(read(paths['entry'])),
               'policy': read(release / ARTIFACTS[0]), 'bindings': read(release / ARTIFACTS[1]),
               'marker': 'monitor-local-v1\n'}
    return {'kind': KIND, 'schema_version': 1, 'config': str(Path(config).absolute()),
            'state': str(app.state), 'release_digest': digest(meta),
            'paths': {key: str(path) for key, path in paths.items()}, 'before': before,
            'snapshot': snapshot, 'bindings_snapshot': bindings, 'mapping': mapped, 'payload': payload,
            'autoreload_disabled': host.autoreload(), 'shell_was_running': bool(app.running()),
            'blockers': mapped['blockers'], 'status': 'blocked' if mapped['blockers'] else 'review-required'}


def require_release(app, reviewed):
    selected = app.selected()
    if selected is None or digest(user_install.verify_bundle(app.root / selected, installed=True)) != reviewed['release_digest']:
        raise ValueError('Install the exact reviewed candidate through the standard release transaction first')


def checkpoint(record, journal, **updates):
    journal.update(updates)
    user_install.atomic_json(record, journal)


def validate_journal(app, journal):
    reviewed = journal['plan']
    if (journal.get('schema_version') != 1 or reviewed.get('kind') != KIND or reviewed['state'] != str(app.state)
            or reviewed['paths'] != {k: str(p) for k, p in paths_for(reviewed['config'], app.state).items()}
            or digest(reviewed) != journal['approval']):
        raise ValueError('Invalid workspace deployment journal')
    return reviewed


def allowed_layouts(text, original, mapping):
    """Accept only original modes transferred across recorded, collision-free IDs."""
    current = migration.parse_layouts(text)
    old = migration.parse_layouts(original)
    ids = {r['old_id']: r['new_id'] for r in mapping['workspaces']}
    used = set()
    for wid, mode in old.items():
        found = [key for key in {wid, ids[wid]} if key in current]
        if len(found) != 1 or current[found[0]] != mode:
            return False
        used.add(found[0])
    return used == set(current)


def restore(app, record, host):
    journal = user_install.read_json(record)
    reviewed = validate_journal(app, journal)
    paths = {k: Path(p) for k, p in reviewed['paths'].items()}
    for key, prior in reviewed['before'].items():
        if prior['existed']:
            backup = record.parent / key
            if backup.is_symlink() or hashlib.sha256(backup.read_bytes()).hexdigest() != prior['sha256']:
                raise ValueError('Workspace backup differs; manual recovery required')
    # Never overwrite edited config or unrelated saved modes during recovery.
    for key in ('entry', 'policy', 'bindings', 'marker'):
        current = file_state(paths[key])
        expected_mode = 0o600 if key == 'marker' else reviewed['before'][key].get('mode', 0o644)
        if current != reviewed['before'][key] and (not current['existed'] or current['mode'] != expected_mode or
                current['sha256'] != hashlib.sha256(reviewed['payload'][key].encode()).hexdigest()):
            raise ValueError('Concurrent configuration edits require manual recovery: ' + key)
    original_layouts = (record.parent / 'layouts').read_text() if reviewed['before']['layouts']['existed'] else ''
    if not allowed_layouts(read(paths['layouts']), original_layouts, reviewed['mapping']):
        raise ValueError('Concurrent layout edits require manual recovery')
    # Only this policy may have produced the assignment file while the shell was stopped.
    original_blocks = (record.parent / 'blocks').read_text() if reviewed['before']['blocks']['existed'] else ''
    current_blocks = read(paths['blocks'])
    expected_blocks = {m['identity']: m['block'] for m in reviewed['mapping']['monitors']}
    old_assignment, _ = migration.parse_blocks(original_blocks)
    assignments = old_assignment | expected_blocks
    connectors = {m['identity']: m['connector'] for m in reviewed['mapping']['monitors']}
    expected_text = ''.join(str(block) + '\t' + connectors.get(identity, '') + '\t' + identity + '\n'
                            for identity, block in sorted(assignments.items(), key=lambda item: item[1]))
    if current_blocks not in (original_blocks, expected_text):
        raise ValueError('Monitor assignment edits require manual recovery')
    if file_state(paths['merged']) != reviewed['before']['merged']:
        raise ValueError('Merged monitor history changed; manual recovery required')
    if host.snapshot()['monitors'] != reviewed['snapshot']['monitors']:
        raise ValueError('Monitor identities/geometry changed; manual recovery required')
    host.preflight_inverse(reviewed['snapshot'], reviewed['mapping'])
    app.stop()
    checkpoint(record, journal, status='restoring')
    host.set_autoreload(True)
    # The inverse eval validates every membership before its first renumber.
    # A concurrent runtime change leaves the journal recoverable, never forced.
    for key in ('entry', 'policy', 'bindings', 'layouts', 'blocks', 'merged', 'marker'):
        prior = reviewed['before'][key]
        if prior['existed']:
            session_config.write(paths[key], (record.parent / key).read_bytes(), prior['mode'])
        elif paths[key].exists():
            paths[key].unlink()
    host.reload()
    host.inverse(reviewed['snapshot'], reviewed['mapping'])
    assert_membership(reviewed, host.snapshot(), inverse=True)
    host.set_autoreload(reviewed['autoreload_disabled'])
    if reviewed['shell_was_running']:
        app.start(restore_background=False)
    checkpoint(record, journal, status='restored', applications_untouched=True)
    return {'status': 'restored', 'journal': str(record)}


def assert_membership(reviewed, actual, inverse=False):
    before = reviewed['snapshot']
    if actual['monitors'] != before['monitors']:
        raise ValueError('Monitor geometry/identity changed during migration')
    mapping = {r['old_id']: r['new_id'] for r in reviewed['mapping']['workspaces']}
    expected = []
    for window in before['clients']:
        item = dict(window)
        if not inverse and item['workspace'] > 0:
            item['workspace'] = mapping[item['workspace']]
        tags = []
        for tag in item.get('tags') or []:
            match = re.fullmatch(r'omabuntu-minimized-from-(\d+)(\*)?', tag)
            if match and not inverse:
                tag = 'omabuntu-minimized-from-' + str(mapping.get(int(match[1]), int(match[1]))) + (match[2] or '')
            tags.append(tag)
        item['tags'] = sorted(tags)
        expected.append(item)
    received = [dict(w, tags=sorted(w.get('tags') or [])) for w in actual['clients']]
    if received != expected:
        raise ValueError('Window identity, membership, floating/fullscreen or minimized state differs')
    by_id = {w['id']: w for w in actual['workspaces']}
    for row in reviewed['mapping']['workspaces']:
        wid = row['old_id'] if inverse else row['new_id']
        if row['windows'] and (wid not in by_id or by_id[wid]['monitor'] != row['monitor']):
            raise ValueError('An occupied workspace changed output')
        original = next(w for w in before['workspaces'] if w['id'] == row['old_id'])
        if row['windows'] and by_id[wid]['tiledLayout'] != original['tiledLayout']:
            raise ValueError('An occupied workspace changed its compositor layout')


def apply(app, reviewed, approval, host=None):
    host = host or Host()
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Workspace migration is per-user; never use sudo')
    if digest(reviewed) != approval or reviewed.get('kind') != KIND or reviewed['blockers']:
        raise ValueError('Workspace approval differs or migration is blocked')
    require_release(app, reviewed)
    user_install.private_directory(app.state)
    lockfd = os.open(app.state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lockfd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        parent = user_install.private_directory(app.state / 'workspace-transactions')
        for pending in parent.glob('*/transaction.json'):
            if user_install.read_json(pending).get('status') not in ('completed', 'restored'):
                raise ValueError('An interrupted workspace transaction needs explicit recovery')
        fresh = plan(app, reviewed['config'], host=host)
        if fresh != reviewed:
            raise ValueError('Configuration, release or desktop changed; review again')
        folder = user_install.private_directory(parent / user_install.stamp())
        record = folder / 'transaction.json'
        paths = {key: Path(path) for key, path in reviewed['paths'].items()}
        for key, path in paths.items():
            if reviewed['before'][key]['existed']:
                shutil.copy2(path, folder / key)
                (folder / key).chmod(0o600)
        journal = {'schema_version': 1, 'status': 'prepared', 'approval': approval, 'plan': reviewed}
        user_install.atomic_json(record, journal)
        try:
            app.stop()
            if host.snapshot() != reviewed['snapshot']:
                raise ValueError('Window/monitor state changed while stopping the bar')
            checkpoint(record, journal, status='staging')
            host.set_autoreload(True)
            for key in ('policy', 'bindings', 'entry'):
                if file_state(paths[key]) != reviewed['before'][key]:
                    raise ValueError('Configuration changed before write')
                session_config.write(paths[key], reviewed['payload'][key].encode(),
                                     reviewed['before'][key].get('mode', 0o644))
            checkpoint(record, journal, status='reloading')
            host.reload()
            assert_membership(reviewed, host.snapshot())
            if read(paths['layouts']) != reviewed['mapping']['layouts_after']:
                raise ValueError('Saved layout migration differs from the reviewed mapping')
            session_config.write(paths['marker'], reviewed['payload']['marker'].encode(), 0o600)
            host.set_autoreload(reviewed['autoreload_disabled'])
            if reviewed['shell_was_running']:
                app.start(restore_background=False)
            checkpoint(record, journal, status='completed', applications_untouched=True)
        except BaseException as error:
            checkpoint(record, journal, status='recovery-required', failure=type(error).__name__)
            try:
                app.stop()
                restore(app, record, host)
            except BaseException as recovery_error:
                checkpoint(record, journal, status='recovery-required', recovery_failure=type(recovery_error).__name__)
            raise ValueError('Workspace deployment failed; inspect/recover ' + str(record)) from error
        return {'status': 'completed', 'journal': str(record), 'shell_running': bool(app.running())}


def recover(app, record, host=None):
    user_install.safe_parents(record.parent)
    expected = app.state / 'workspace-transactions'
    if record.name != 'transaction.json' or record.parent.parent != expected:
        raise ValueError('Recovery requires a journal in this installation workspace-transactions')
    lockfd = os.open(app.state / 'control.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lockfd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        journal = user_install.read_json(record)
        validate_journal(app, journal)
        if journal['status'] == 'restored':
            return {'status': 'already-restored'}
        return restore(app, record, host or Host())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'apply', 'recover'))
    parser.add_argument('--config-dir', type=Path, required=True)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--launcher', type=Path, required=True)
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--review-out', type=Path, help='Explicit private destination for the complete read-only plan')
    parser.add_argument('--approval')
    parser.add_argument('--journal', type=Path)
    parser.add_argument('--apply', action='store_true', dest='consent')
    args = parser.parse_args(argv)
    app = user_install.Installation(args.data_dir, args.state_dir, args.launcher)
    os.umask(0o077)
    if args.action == 'plan':
        reviewed = plan(app, args.config_dir, args.bundle)
        if args.review_out is not None:
            destination = args.review_out.absolute()
            user_install.private_directory(destination.parent)
            if destination.exists() or destination.is_symlink():
                parser.error('Review destination already exists; use a new path')
            user_install.atomic_json(destination, reviewed)
            destination.chmod(0o600)
        # Full configuration and private window IDs belong only in the explicitly
        # requested private report, never in the default terminal summary.
        result = {'approval': digest(reviewed), 'status': reviewed['status'],
                  'blockers': reviewed['blockers'], 'review': str(args.review_out) if args.review_out else None,
                  'workspaces': reviewed['mapping']['workspaces'],
                  'changed_paths': [reviewed['paths'][key] for key in reviewed['payload']]}
    else:
        if not args.consent:
            parser.error('Desktop changes require --apply and explicit approval')
        if args.action == 'apply':
            if args.review is None or args.approval is None:
                parser.error('apply requires --review and --approval')
            reviewed = user_install.read_json(args.review)
            if reviewed.get('config') != str(args.config_dir.absolute()):
                parser.error('Review targets a different configuration directory')
            result = apply(app, reviewed, args.approval)
        else:
            if args.journal is None:
                parser.error('recover requires --journal')
            if user_install.read_json(args.journal)['plan'].get('config') != str(args.config_dir.absolute()):
                parser.error('Journal targets a different configuration directory')
            result = recover(app, args.journal)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
