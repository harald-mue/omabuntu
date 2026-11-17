#!/usr/bin/env python3
"""Read-only preview of global -> original Omarchy monitor-local workspaces.

Never installs, edits host state, dispatches, or reloads. Reports omit window
content/titles. Save reports only to an ignored private workspace directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

SCHEMA = 'omarchy-monitor-local-v1'

LEGACY_BINDINGS = '''for i = 1, 10 do
    local key = i % 10
    hl.bind("SUPER + " .. key, hl.dsp.focus({ workspace = i }), { description = "Switch to workspace " .. i })
    hl.bind("SUPER + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }), { description = "Move window to workspace " .. i })
end'''


def configuration_patch(text):
    """Propose the reviewed legacy-loop replacement, never write a host file.

    Unknown syntax is not an invitation to broadly rewrite an unowned profile.
    Keep geometry, application, clipboard and security configuration byte-exact.
    """
    if (text.count(LEGACY_BINDINGS) != 1 or 'omabuntu-monitor-workspaces' in text
            or 'omabuntu-workspace-bindings' in text or 'omabuntu_workspaces' in text):
        raise ValueError('Workspace configuration differs; exact manual review required')
    return text.replace(LEGACY_BINDINGS,
        '-- Original monitor-local workspaces; installed only through approved migration.\n'
        'require("omabuntu-monitor-workspaces")\n'
        'require("omabuntu-workspace-bindings")', 1)


def parse_layouts(text):
    modes = {}
    for line in text.splitlines():
        fields = line.split()
        if (len(fields) != 2 or not fields[0].isascii() or not fields[0].isdigit()
                or not 1 <= int(fields[0]) <= 2147483647 or fields[1] not in ('scrolling', 'floating')
                or int(fields[0]) in modes):
            raise ValueError('Invalid or duplicate saved workspace layout')
        modes[int(fields[0])] = fields[1]
    return modes


def parse_blocks(text):
    blocks, current = {}, {}
    for line in text.splitlines():
        fields = line.split('\t')
        if (len(fields) != 3 or not fields[0].isascii() or not fields[0].isdigit()
                or not fields[2] or fields[2] in blocks or int(fields[0]) in blocks.values()
                or (fields[1] and fields[1] in current)):
            raise ValueError('Invalid or duplicate monitor block assignment')
        blocks[fields[2]] = int(fields[0])
        if fields[1]:
            current[fields[1]] = fields[2]
    return blocks, current


def preview(monitors, workspaces, layouts='', assignments=''):
    """Preview a collision-free adoption preserving outputs, slots and modes.

    Block ambiguous initial migrations instead of predicting a destructive
    rearrangement. Post-migration hotplug reconciliation belongs to upstream Lua.
    """
    modes = parse_layouts(layouts)
    blocks, current = parse_blocks(assignments)
    monitors = [dict(m) for m in monitors if m.get('mirrorOf', 'none') in ('none', '', None)]
    names = [m['name'] for m in monitors]
    if len(set(names)) != len(names) or not monitors:
        raise ValueError('Expected distinct connected monitor names')
    monitors.sort(key=lambda m: (not m['name'].startswith(('eDP', 'LVDS', 'DSI')), m['id']))
    identities, taken = {}, set()
    for m in monitors:
        identity = current.get(m['name'])
        described = m.get('description') or m['name']
        # Same duplicate-identity convention as the original module.
        import re
        if identity and identity not in taken and re.sub(r' #\d+$', '', identity) == described:
            identities[m['name']] = identity
            taken.add(identity)
    for m in sorted(monitors, key=lambda m: m['name']):
        if m['name'] not in identities:
            base = m.get('description') or m['name']
            identity, count = base, 1
            while identity in taken:
                count += 1
                identity = f'{base} #{count}'
            identities[m['name']] = identity
            taken.add(identity)
    by_connector = {}
    for m in monitors:
        identity = identities[m['name']]
        if identity not in blocks:
            block = 0
            while block in blocks.values():
                block += 1
            blocks[identity] = block
        by_connector[m['name']] = blocks[identity]
    regular = [w for w in workspaces if type(w.get('id')) is int and w['id'] > 0]
    occupied_ids = {w['id'] for w in regular}
    if len(occupied_ids) != len(regular):
        raise ValueError('Duplicate workspace IDs')
    blockers = []
    mapping = {}
    for w in sorted(regular, key=lambda w: w['id']):
        if w.get('monitor') not in by_connector:
            blockers.append('Workspace has no unambiguous connected monitor')
            continue
        target = by_connector[w['monitor']] * 10 + (w['id'] - 1) % 10 + 1
        if target != w['id'] and (target in occupied_ids or target in modes):
            blockers.append(f'Workspace {w["id"]} destination {target} is occupied or has saved state')
        if target in mapping.values():
            blockers.append(f'Multiple workspaces would target {target}')
        mapping[w['id']] = target
    for wid in modes:
        if wid not in mapping:
            blockers.append(f'Saved layout {wid} has no current workspace; explicit attribution required')
    new_modes = {mapping[wid]: mode for wid, mode in modes.items() if wid in mapping}
    result = {
        'schema_version': 1, 'policy': SCHEMA, 'status': 'blocked' if blockers else 'preview-only',
        'blockers': blockers, 'activation': 'separate-approval-required',
        'monitors': [{'connector': m['name'], 'identity': identities[m['name']],
                      'block': by_connector[m['name']]} for m in monitors],
        'workspaces': [{'old_id': w['id'], 'new_id': mapping.get(w['id']),
                        'monitor': w.get('monitor'), 'windows': w.get('windows', 0),
                        'mode': modes.get(w['id'], 'dwindle')} for w in regular],
        'layouts_after': ''.join(f'{wid} {new_modes[wid]}\n' for wid in sorted(new_modes)),
    }
    # Include only the inputs relevant to migration, not titles or raw IPC.
    relevant = {'monitors': monitors, 'workspaces': regular, 'layouts': layouts, 'assignments': assignments}
    result['snapshot_sha256'] = hashlib.sha256(json.dumps(relevant, sort_keys=True).encode()).hexdigest()
    return result


def bounded_text(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Refusing linked state/configuration file')
    if not path.exists():
        return ''
    if not path.is_file() or path.stat().st_uid != os.getuid() or path.stat().st_size > 131072:
        raise ValueError('Expected bounded owned regular state/configuration file')
    return path.read_text()


def query(kind):
    try:
        result = subprocess.run(['hyprctl', '-j', kind], capture_output=True, text=True, timeout=5, check=False)
    except FileNotFoundError as error:
        raise ValueError('Missing hyprctl') from error
    except subprocess.TimeoutExpired as error:
        raise ValueError('Timed out querying ' + kind) from error
    if result.returncode:
        raise ValueError('Failed querying ' + kind)
    data = json.loads(result.stdout)
    if not isinstance(data, list):
        raise ValueError('Invalid compositor reply for ' + kind)
    return data


def inspect(state):
    # Strip names/titles/addresses before retaining or hashing any IPC input.
    monitors = [{k: m.get(k) for k in ('id', 'name', 'description', 'mirrorOf')} for m in query('monitors')]
    workspaces = [{k: w.get(k) for k in ('id', 'monitor', 'windows')} for w in query('workspaces')]
    return preview(monitors, workspaces, bounded_text(state / 'current/workspace-layouts.txt'),
                   bounded_text(state / 'monitor-workspaces'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, required=True, help='Explicit approved Omabuntu state directory')
    args = parser.parse_args(argv)
    try:
        result = inspect(args.state_dir)
    except (ValueError, OSError) as error:
        parser.exit(1, 'Workspace preview failed: ' + str(error) + '\n')
    print(json.dumps(result, indent=2))
    return 1 if result['blockers'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
