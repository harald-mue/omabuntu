"""Bootstrap package inventory and additive-only approved APT application.

Merge existing runtime/Quickshell plans with compositor, Omasnap and plugin
requests. Reuse the reviewed package simulation/apply engine; never upgrade,
remove, autoremove or add sources here. Dependency closure is not VM-accepted.
"""
import json
import os
from pathlib import Path

import bootstrap_sources
import native_compatibility
import install as guided
import omabuntu
import package_plan
import user_install
import upgrade_policy

ROOT = Path(__file__).resolve().parents[1]


def request_manifest(base_only=False, runtime_only=False, plugin_build_only=False):
    bootstrap = bootstrap_sources.manifest()
    runtime, runtime_names = guided.manifest(wallpaper=True)
    quickshell, build_names = package_plan.load_manifest(ROOT / 'packages/quickshell-plan.json')
    groups = bootstrap.get('package_groups')
    if not isinstance(groups, dict) or set(groups) != {'bootstrap', 'desktop', 'omasnap_build', 'plugin_build'}:
        raise ValueError('Invalid bootstrap package groups')
    names = []
    if sum((base_only, runtime_only, plugin_build_only)) > 1:
        raise ValueError('Package scopes are mutually exclusive')
    if base_only:
        requested = [groups['bootstrap']]
    elif runtime_only:
        requested = [groups['bootstrap'], groups['desktop'], runtime_names]
    elif plugin_build_only:
        requested = [groups['bootstrap'], groups['plugin_build'],
                     ['cmake', 'cpio', 'pkg-config', 'gcc', 'g++', 'make', 'ninja-build']]
    else:
        requested = [groups['bootstrap'], groups['desktop'], groups['omasnap_build'], runtime_names, build_names]
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
    if plugin_build_only:
        # Only this reviewed header/runtime pair may replace a newer candidate.
        manifest['matching_development_versions'] = {'libudev-dev': 'libudev1'}
    inputs = {'bootstrap': guided.digest(bootstrap), 'runtime': guided.digest(runtime),
              'quickshell': guided.digest(quickshell),
              'native_compatibility': guided.digest(native_compatibility.policy())}
    return manifest, inputs


def native_blockers(payload):
    return [row['message'] for row in native_compatibility.package_checks(payload) if not row['ok']]


def prepare(case, run=omabuntu.probe, base_only=False, runtime_only=False, plugin_build_only=False):
    bootstrap_sources.host_check()
    manifest, inputs = request_manifest(base_only, runtime_only, plugin_build_only)
    case = user_install.private_directory(case)
    path = case / 'packages.json'
    user_install.atomic_json(path, manifest)
    payload = guided.package_review(manifest_path=path, run=run)
    decision = upgrade_policy.classify(payload['transaction'])
    native_checks = [] if base_only else native_compatibility.package_checks(payload)
    blockers = [*payload['blockers'], *([] if decision['permitted'] else [decision['reason']]),
                *(row['message'] for row in native_checks if not row['ok'])]
    plan = {'schema_version': 1, 'kind': 'omabuntu-bootstrap-packages', 'case': str(case.absolute()),
            'inputs': inputs, 'base_only': base_only, 'runtime_only': runtime_only,
            'plugin_build_only': plugin_build_only, 'payload': payload, 'native_checks': native_checks,
            'blockers': blockers,
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
    if any(type(plan.get(name)) is not bool for name in ('runtime_only', 'plugin_build_only')):
        raise ValueError('Missing package scope selection; review a fresh plan')
    expected_manifest, inputs = request_manifest(plan['base_only'], plan['runtime_only'], plan['plugin_build_only'])
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
