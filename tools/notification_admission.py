#!/usr/bin/env python3
"""Offline capability evidence for an inactive notification package, never a role grant."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

QUICKSHELL = '2b4501a282689792b62e94f3fb30d8f512324fe6'
OMARCHY = 'ac2690cd7be4f47e4a255f5e2e78d904d436b068'
PREFIX = 'opt/omabuntu-runtime/'
DESCRIPTOR = 'native/notification-runtime.json'
ROLE = 'inactive-separate-migration-required'
CHECKS = ('free-name-and-native-notify', 'refuse-replacement', 'conflict-no-queue-no-late-takeover',
          'negative-control-original-late-takeover', 'missing-bus-fails-closed', 'bus-loss-fails-closed')
SOURCE_NAMES = {'NotificationHost.qml', *( 'Notifications/' + name for name in (
    'Service.qml', 'Toast.qml', 'DeedButton.qml', 'Delivery.js', 'Detect.js', 'Icons.js',
    'Layout.js', 'Markup.js', 'Security.js', 'Store.js', 'Actions.js', 'qmldir',
    'Omarchy-MIT.txt', 'Omapager-MIT.txt'))}
EVIDENCE = {name: 'native/notification-runtime/' + file for name, file in (
    ('build', 'build.json'), ('bus', 'private-bus.json'), ('eligibility', 'eligibility.json'),
    ('pin', 'pin.json'), ('profile', 'notifications.json'), ('patch', 'exclusive.patch'))}


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def regular(root, relative, limit=2_000_000):
    part = Path(relative)
    if part.is_absolute() or '..' in part.parts:
        raise ValueError('Unsafe notification proof path')
    path = root / part
    if (any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file()
            or path.stat().st_size > limit or path.stat().st_nlink != 1):
        raise ValueError('Require bounded regular notification proof input')
    return path


def load(root, relative):
    value = json.loads(regular(root, relative).read_bytes())
    if not isinstance(value, dict):
        raise ValueError('Require notification proof object')
    return value


def relocated_artifacts(records):
    """Only the existing qs alias changes when the private prefix is relocated."""
    result = []
    seen = set()
    if not isinstance(records, list) or not records or len(records) > 4096:
        raise ValueError('Require bounded runtime artifact manifest')
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get('path'), str):
            raise ValueError('Malformed notification runtime artifact')
        path = record['path']
        if not path.startswith(PREFIX) or '..' in Path(path).parts or path in seen:
            raise ValueError('Unexpected notification runtime artifact path')
        seen.add(path)
        new = dict(record, path='runtime/' + path[len(PREFIX):])
        if record.get('type') == 'symlink':
            if path != PREFIX + 'bin/qs' or record.get('target') != '/opt/omabuntu-runtime/bin/quickshell':
                raise ValueError('Unexpected notification runtime symlink')
            new['target'] = 'quickshell'
        elif record.get('type') != 'file':
            raise ValueError('Unexpected notification runtime artifact type')
        result.append(new)
    return sorted(result, key=lambda item: item['path'])


def runtime_manifest(bundle):
    runtime = bundle / 'runtime'
    if runtime.is_symlink() or not runtime.is_dir():
        raise ValueError('Require real packaged runtime directory')
    result = []
    for path in sorted(runtime.rglob('*')):
        relative = str(path.relative_to(bundle))
        if path.is_symlink():
            result.append({'path': relative, 'type': 'symlink', 'target': os.readlink(path)})
        elif path.is_dir():
            continue
        else:
            regular(bundle, relative, limit=512_000_000)
            result.append({'path': relative, 'type': 'file', 'sha256': digest(path), 'bytes': path.stat().st_size})
    return result


def verify(bundle):
    """Read only. Local integrity/provenance, not signed attestation or deployment consent."""
    bundle = Path(bundle).absolute()
    proof = load(bundle, DESCRIPTOR)
    if (proof.get('schema_version') != 1 or proof.get('scope') != 'omabuntu-notification-runtime-capability-v1'
            or proof.get('role') != ROLE or proof.get('live_deployment_authorized') is not False
            or proof.get('validator_sha256') != digest(Path(__file__))
            or set(proof.get('evidence', {})) != set(EVIDENCE)):
        raise ValueError('Require inactive artifact-bound notification capability')
    if digest(regular(bundle, 'helpers/notification_admission.py')) != proof['validator_sha256']:
        raise ValueError('Packaged notification verifier changed')
    data = {}
    for key, relative in EVIDENCE.items():
        path = regular(bundle, relative)
        if proof['evidence'][key] != digest(path):
            raise ValueError('Notification evidence changed')
        if key != 'patch':
            data[key] = load(bundle, relative)
    build, bus, eligibility, pin, profile = (data[key] for key in ('build', 'bus', 'eligibility', 'pin', 'profile'))
    hashes = proof['evidence']
    if not all(isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value)
               for value in (pin.get('source_sha256'), pin.get('patched_source_sha256'),
                             build.get('binary_sha256'), bus.get('checker_sha256'))):
        raise ValueError('Require complete notification source/binary/checker digests')
    if (not isinstance(build.get('source_lock'), dict)
            or not isinstance(build['source_lock'].get('quickshell'), dict)
            or not isinstance(bus.get('checks'), list)
            or not all(isinstance(row, dict) for row in bus['checks'])):
        raise ValueError('Malformed notification runtime evidence')
    if (pin.get('schema_version') != 1 or pin.get('quickshell_commit') != QUICKSHELL
            or pin.get('activation') != 'blocked-until-reviewed-exclusive-runtime-and-deployment'
            or pin.get('patch_sha256') != hashes['patch']
            or build.get('schema_version') != 1 or build.get('status') != 'exclusive-notification-candidate-built'
            or build.get('source_lock', {}).get('quickshell', {}).get('commit') != QUICKSHELL
            or build.get('pin_sha256') != hashes['pin']
            or build.get('patch_sha256') != hashes['patch']
            or build.get('native_source_sha256') != pin.get('patched_source_sha256')
            or build.get('patched_source_sha256') != pin.get('patched_source_sha256')
            or build.get('baseline_unchanged') is not True
            or eligibility.get('schema_version') != 1
            or eligibility.get('status') != 'eligible-for-separate-deployment-review'
            or eligibility.get('build_report_sha256') != hashes['build']
            or eligibility.get('test_report_sha256') != hashes['bus']
            or eligibility.get('binary_sha256') != build.get('binary_sha256')
            or eligibility.get('patch_sha256') != hashes['patch']
            or eligibility.get('checker_sha256') != bus.get('checker_sha256')
            or eligibility.get('live_deployment_authorized') is not False
            or bus.get('status') != 'private-bus-checks-passed' or bus.get('returncode') != 0
            or bus.get('host_bus_exposed') is not False or bus.get('artifacts_unchanged') is not True
            or [row.get('name') for row in bus.get('checks', [])] != list(CHECKS)
            or any(row.get('passed') is not True for row in bus['checks'])):
        raise ValueError('Notification runtime evidence is incomplete or inconsistent')
    if (profile.get('schema_version') != 1 or profile.get('commit') != OMARCHY
            or profile.get('activation') != 'separate-exclusive-owner-deployment-required'
            or not isinstance(profile.get('staged'), dict) or set(profile['staged']) != SOURCE_NAMES):
        raise ValueError('Require original notification source closure')
    for name, expected in profile['staged'].items():
        if digest(regular(bundle, 'shell/' + name)) != expected:
            raise ValueError('Packaged notification source differs from its proof')
    if runtime_manifest(bundle) != relocated_artifacts(build.get('artifacts')):
        raise ValueError('Packaged runtime differs from private-bus-tested artifacts')
    binary = regular(bundle, 'runtime/bin/quickshell', limit=512_000_000)
    if digest(binary) != build.get('binary_sha256') or not binary.stat().st_mode & 0o100:
        raise ValueError('Packaged notification executable changed or is not executable')
    return {'runtime_verified': True, 'deployment_approved': False, 'role': ROLE,
            'binary_sha256': build['binary_sha256'], 'patch_sha256': hashes['patch'],
            'notification_profile_sha256': hashes['profile']}


def select_runtime(root, baseline, candidate=None):
    """Repository-only producer: the baseline remains the license/source parent."""
    import check_runtime
    build, runtime, parent = check_runtime.verify_stage(root, baseline)
    if candidate is None:
        return build, runtime, None
    import build_notification_runtime
    import check_notification_runtime
    case, runtime, report = build_notification_runtime.verify(root, candidate)
    check_notification_runtime.eligibility(root, case)
    if (Path(report.get('baseline', '')).resolve() != build
            or report.get('baseline_report_sha256') != digest(build / 'report.json')
            or report.get('baseline_artifacts') != parent['artifacts']):
        raise ValueError('Exclusive runtime does not match the selected baseline')
    return build, runtime, case


def stage(root, destination, case):
    """Repository-only producer. No copying until current source/artifact proof passes."""
    import check_notification_runtime
    import notification_frontend
    check_notification_runtime.eligibility(root, case)
    sources = notification_frontend.sources(root)
    for name, expected in sources.items():
        if regular(destination, 'shell/' + name).read_bytes() != expected:
            raise ValueError('Notification source changed during packaging')
    inputs = {'build': case / 'report.json', 'bus': case / 'private-bus-report.json',
              'eligibility': case / 'eligibility.json', 'pin': root / 'upstream/notification-runtime.json',
              'profile': root / 'upstream/notifications.json', 'patch': root / 'native/notification-exclusive.patch'}
    proof = {'schema_version': 1, 'scope': 'omabuntu-notification-runtime-capability-v1',
             'role': ROLE, 'live_deployment_authorized': False,
             'validator_sha256': digest(Path(__file__)), 'evidence': {}}
    for key, source in inputs.items():
        data = regular(source.parent, source.name).read_bytes()
        target = destination / EVIDENCE[key]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data);target.chmod(0o444)
        proof['evidence'][key] = digest(target)
    descriptor = destination / DESCRIPTOR
    descriptor.write_text(json.dumps(proof, indent=2) + '\n');descriptor.chmod(0o444)
    return verify(destination)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.bundle), indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise SystemExit('Notification capability verification refused: ' + type(error).__name__)
