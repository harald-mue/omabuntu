#!/usr/bin/env python3
"""Minimal sealed notification overlay and explicit, recoverable switch ordering.

No action runs on import. Live operations are supplied by the reviewed runner;
this module never discovers/kills processes or enables background supervision.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil

import notification_admission as capability
import user_install as deployment


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Notification integration witness differs')
    return text.replace(old, new)


def write_preserved(path, text):
    mode = path.stat().st_mode & 0o777
    path.chmod(mode | 0o200)
    try:
        path.write_text(text)
    finally:
        path.chmod(mode)


def copy_replacing(source, target):
    if target.exists():
        if target.is_symlink() or not target.is_file():
            raise ValueError('Unexpected overlay destination type')
        target.unlink()  # Only a file in this call's new, unselected clone.
    shutil.copy2(source, target)


def prepare(base, review, output, version):
    base, review, output = map(lambda p: Path(p).absolute(), (base, review, output))
    before = deployment.verify_bundle(base, installed=True)
    deployment.verify_bundle(review); capability.verify(review)
    if not deployment.VERSION.fullmatch(version) or output.exists():
        raise ValueError('Require a fresh valid overlay version')
    old_runtime = {r['path']: r for r in capability.runtime_manifest(base)}
    new_runtime = {r['path']: r for r in capability.runtime_manifest(review)}
    extra = set(old_runtime) - set(new_runtime)
    if extra != {'runtime/bin/omasnap'} or set(new_runtime) - set(old_runtime):
        raise ValueError('Unreviewed runtime attachment delta')
    if any(old_runtime[p] != new_runtime[p] for p in new_runtime if p != 'runtime/bin/quickshell'):
        raise ValueError('Unreviewed runtime baseline delta')
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    shutil.copytree(base, output, symlinks=True)
    # Preserve the already installed screenshot binary, not an attachment to the
    # exact private-bus-tested notification runtime. Only its manager path moves.
    (output / 'runtime/bin/omasnap').rename(output / 'helpers/omasnap')
    copy_replacing(review / 'runtime/bin/quickshell', output / 'runtime/bin/quickshell')
    manager = (output / 'manager.py').read_text()
    if manager.count("'runtime/bin/omasnap'") != 2:
        raise ValueError('Screenshot manager path witness differs')
    manager = manager.replace("'runtime/bin/omasnap'", "'helpers/omasnap'")
    write_preserved(output / 'manager.py', manager)
    copied = {'shell/' + p for p in capability.SOURCE_NAMES}
    copied.update('helpers/' + p for p in ('notification_state.py', 'notification_admission.py', 'notification_session.py'))
    copied.update(str(p.relative_to(review)) for p in (review / 'native').rglob('*') if p.is_file() and p.name.startswith('notification'))
    copied.update(capability.EVIDENCE.values()); copied.add(capability.DESCRIPTOR)
    for name in copied:
        source = capability.regular(review, name)
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True)
        copy_replacing(source, target)
    panel_path = output / 'shell/TrialPanel.qml'; panel = panel_path.read_text()
    reviewed_panel = (review / 'shell/TrialPanel.qml').read_text()
    block = '  property QtObject notificationContext:' + reviewed_panel.split('  property QtObject notificationContext:', 1)[1].split('  function hasAudioWidget', 1)[0]
    panel = replace_once(panel, '  function hasAudioWidget', block + '  function hasAudioWidget')
    panel = replace_once(panel, 'DndIndicator { backend: bars.indicatorState.dnd }', 'DndIndicator { backend: bars.notificationHost.dnd }')
    panel = replace_once(panel, '"Dnd": bars.indicatorState.dnd.known', '"Dnd": bars.notificationHost.dnd && bars.notificationHost.dnd.known')
    write_preserved(panel_path, panel)
    color = (review / 'shell/Commons/Color.qml').read_text()
    block = color[color.index('  // Original notification role defaults;'):color.index('  readonly property QtObject tooltip:')]
    if color.replace(block, '') != (base / 'shell/Commons/Color.qml').read_text():
        raise ValueError('Unrelated palette delta')
    labels = (review / 'shell/Commons/I18n.qml').read_text()
    begin = labels.index('"notifications.minutesAgo"'); end = labels.index('"bar.allowNotifications"', begin)
    if labels[:begin] + labels[end:] != (base / 'shell/Commons/I18n.qml').read_text():
        raise ValueError('Unrelated translation delta')
    for name in ('Commons/Color.qml', 'Commons/I18n.qml'):
        copy_replacing(review / 'shell' / name, output / 'shell' / name)
    proof = {'schema_version': 1, 'scope': 'omabuntu-notification-minimal-overlay-v1',
             'base_release_sha256': capability.digest(base / 'release.json'),
             'review_release_sha256': capability.digest(review / 'release.json'),
             'screenshot_relocation': {'from': 'runtime/bin/omasnap', 'to': 'helpers/omasnap',
                                       'sha256': old_runtime['runtime/bin/omasnap']['sha256']},
             'deployment_approved': False, 'session_grant_required': True}
    provenance = json.loads((output / 'PROVENANCE.json').read_text())
    provenance['notification_overlay'] = proof
    write_preserved(output / 'PROVENANCE.json', json.dumps(provenance, indent=2) + '\n')
    actual = deployment.file_manifest(output)
    allowed = copied | {'runtime/bin/omasnap', 'helpers/omasnap', 'runtime/bin/quickshell', 'manager.py',
                        'shell/TrialPanel.qml', 'shell/Commons/Color.qml', 'shell/Commons/I18n.qml', 'PROVENANCE.json'}
    changed = {n for n in set(actual) | set(before['files']) if actual.get(n) != before['files'].get(n)}
    if not changed <= allowed:
        raise ValueError('Unrelated overlay delta')
    proof['changed_paths'] = sorted(changed)
    (output / 'native/notification-overlay.json').write_text(json.dumps(proof, indent=2) + '\n')
    meta = dict(before, version=version, files=deployment.file_manifest(output))
    write_preserved(output / 'release.json', json.dumps(meta, indent=2) + '\n')
    deployment.verify_bundle(output); capability.verify(output)
    return proof


def validate_acceptance(bundle):
    proof = capability.load(bundle, 'native/notification-acceptance.json')
    profile = capability.load(bundle, capability.EVIDENCE['profile'])
    names = {'history', 'render', 'input', 'process', 'host'}
    if (proof.get('scope') != 'omabuntu-notification-live-prerequisites-v1'
            or proof.get('passed') is not True or proof.get('sources') != profile['staged']
            or set(proof.get('reports', {})) != names):
        raise ValueError('Incomplete native admission evidence')
    for name in sorted(names):
        relative = 'native/notification-acceptance/' + name + '.json'
        path = capability.regular(bundle, relative)
        if capability.digest(path) != proof['reports'][name]:
            raise ValueError('Native admission receipt changed')
        row = capability.load(bundle, relative)
        status = 'native-original-notifications-passed' if name == 'render' else 'passed'
        if (row.get('status') != status or row.get('inputs_unchanged') is not True
                or row.get('notification_sources') != profile['staged'] or 'variant' in row
                or row.get('runtime_sha256') != capability.digest(bundle / 'runtime/bin/quickshell')):
            raise ValueError('Native admission receipt failed or has different source')
        if name == 'render':
            if len(row.get('cases', [])) != 2 or any(c.get('status') != 'passed' or c.get('returncode') != 0 or c.get('children_reaped') is not True or c.get('inputs_unchanged') is not True for c in row['cases']):
                raise ValueError('Native rendering case incomplete')
        elif row.get('returncode') != 0 or row.get('children_reaped') is not True:
            raise ValueError('Native admission cleanup/exit failed')
        digest_key = 'admission_checker_sha256' if name == 'host' else 'checker_sha256'
        if row.get(digest_key) != capability.digest(capability.regular(bundle, 'native/notification-acceptance/' + name + '-checker.py')):
            raise ValueError('Native admission checker changed')
        if name == 'host' and (row.get('fixture_kind') != 'native-session-host-admission'
                or row.get('session_helper_sha256') != capability.digest(bundle / 'helpers/notification_session.py')
                or row.get('claim_verified') is not True or len(row.get('checks', [])) != 4):
            raise ValueError('Native parent admission missing')
        checks = row.get('checks', []) if name != 'render' else [c for case in row['cases'] for c in case['checks']]
        if not checks or any(c.get('passed') is not True for c in checks):
            raise ValueError('Native assertions incomplete')
    return proof


def switch(ops):
    """Explicit transaction; recovery is sequential, never a concurrent fallback.

    Each operation must be identity checked/idempotent and journal its mutations.
    Snapshot/preflight failure performs no live mutation. Any subsequent failure
    invokes recovery; a recovery failure is surfaced rather than hidden/retried.
    """
    ops.preflight()
    ops.snapshot()
    try:
        ops.stop_owned_shell()
        ops.fence_provider()
        ops.stop_provider()
        ops.install()
        ops.grant()
        ops.start_captured()
        result = ops.verify_ready()
        ops.complete(result)
        return result
    except BaseException as error:
        try:
            ops.record_failure(type(error).__name__)
        finally:
            ops.recover()
        raise
