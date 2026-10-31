"""Bootstrap package inventory and additive-only approved APT application.

Merge existing runtime/Quickshell plans with compositor, Omasnap and plugin
requests. Reuse the reviewed package simulation/apply engine; never upgrade,
remove, autoremove or add sources here. Dependency closure is not VM-accepted.
"""
import json
import os
from pathlib import Path

import bootstrap_sources
import install as guided
import omabuntu
import package_plan
import user_install
import upgrade_policy

ROOT = Path(__file__).resolve().parents[1]
NATIVE_VERSIONS = {'hyprland': '0.56.2', 'libqt6core6t64': '6.10.2', 'hyprlock': '0.9.6'}


def request_manifest(base_only=False):
    bootstrap = bootstrap_sources.manifest()
    runtime, runtime_names = guided.manifest(wallpaper=True)
    quickshell, build_names = package_plan.load_manifest(ROOT / 'packages/quickshell-plan.json')
    groups = bootstrap.get('package_groups')
    if not isinstance(groups, dict) or set(groups) != {'bootstrap', 'desktop', 'omasnap_build', 'plugin_build'}:
        raise ValueError('Invalid bootstrap package groups')
    names = []
    requested = [groups['bootstrap']] if base_only else [*groups.values(), runtime_names, build_names]
    for values in requested:
        if not isinstance(values, list) or not values:
            raise ValueError('Empty bootstrap package group')
        for name in values:
            if not isinstance(name, str) or not package_plan.PACKAGE_NAME.fullmatch(name):
                raise ValueError('Invalid bootstrap package name')
            if name not in names:
                names.append(name)
    manifest = {'schema_version': 1, 'name': 'omabuntu-local-bundle',
                'target': runtime['target'], 'groups': {'runtime': names, 'wallpaper': ['hyprpaper']},
                'limitations': bootstrap['limitations']}
    inputs = {'bootstrap': guided.digest(bootstrap), 'runtime': guided.digest(runtime),
              'quickshell': guided.digest(quickshell)}
    return manifest, inputs


def native_blockers(payload):
    candidates = package_plan.parse_policy(payload['policy'])
    blockers = []
    for name, expected in NATIVE_VERSIONS.items():
        value = guided.package_version(payload['before'], name) or candidates.get(name, {}).get('candidate')
        actual = (value or '').split(':')[-1].split('+')[0].split('-')[0]
        if actual != expected:
            blockers.append('Native target differs: ' + name + ' requires ' + expected)
    return blockers


def prepare(case, run=omabuntu.probe, base_only=False):
    bootstrap_sources.host_check()
    manifest, inputs = request_manifest(base_only)
    case = user_install.private_directory(case)
    path = case / 'packages.json'
    user_install.atomic_json(path, manifest)
    payload = guided.package_review(manifest_path=path, run=run)
    decision = upgrade_policy.classify(payload['transaction'])
    blockers = [*payload['blockers'], *([] if decision['permitted'] else [decision['reason']]),
                *([] if base_only else native_blockers(payload))]
    plan = {'schema_version': 1, 'kind': 'omabuntu-bootstrap-packages', 'case': str(case.absolute()),
            'inputs': inputs, 'base_only': base_only, 'payload': payload, 'blockers': blockers,
            'status': 'blocked' if blockers else 'review-required'}
    user_install.atomic_json(case / 'package-plan.json', plan)
    return plan


def apply(plan, approval, run=omabuntu.probe, execute=guided.terminal_install):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise ValueError('Run as a normal user; only approved package commands use sudo')
    bootstrap_sources.host_check()
    if (guided.digest(plan) != approval or plan.get('kind') != 'omabuntu-bootstrap-packages'
            or plan.get('blockers')):
        raise ValueError('Bootstrap package approval differs or is blocked')
    if type(plan.get('base_only')) is not bool:
        raise ValueError('Missing bootstrap package scope')
    expected_manifest, inputs = request_manifest(plan['base_only'])
    if plan['inputs'] != inputs:
        raise ValueError('Bootstrap package inputs changed; review again')
    case = user_install.safe_parents(Path(plan['case']))
    path = case / 'packages.json'
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 262144:
        raise ValueError('Unsafe generated package manifest')
    if user_install.read_json(path) != expected_manifest:
        raise ValueError('Generated package manifest changed')
    fresh = guided.package_review(manifest_path=path, run=run)
    if fresh != plan['payload'] or fresh['blockers'] or (not plan['base_only'] and native_blockers(fresh)):
        raise ValueError('APT policy/state changed; review a new package plan')
    saved = guided.seal('omabuntu-package-plan', fresh)
    guided_path = case / 'approved-guided-plan.json'
    user_install.atomic_json(guided_path, saved)
    # The inner implementation repeats state/policy/simulation and journals
    # the before/after transaction. Failed APT never triggers purge/removal.
    evidence = guided.apply_packages(guided_path, saved['approval'], run=run,
                                     execute=execute, manifest_path=path)
    return {'status': 'packages-verified', 'evidence': str(evidence),
            'sources_changed': False, 'desktop_started': False}
