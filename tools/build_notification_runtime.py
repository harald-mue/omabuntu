#!/usr/bin/env python3
"""Build an isolated exclusive-notification variant; never install or activate it."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

import build_runtime as builder
import check_runtime

ROOT = Path(__file__).resolve().parents[1]
PIN = 'upstream/notification-runtime.json'
STATUS = 'exclusive-notification-candidate-built'


def inputs(root):
    pin = json.loads((root / PIN).read_text())
    _, sources = builder.load_inputs(root)
    if (pin.get('schema_version') != 1 or pin.get('quickshell_commit') != sources['quickshell']['commit']
            or pin.get('source_path') != 'src/services/notifications/server.cpp'
            or pin.get('patch') != 'native/notification-exclusive.patch'
            or pin.get('activation') != 'blocked-until-reviewed-exclusive-runtime-and-deployment'
            or builder.digest(root / pin['patch']) != pin.get('patch_sha256')):
        raise builder.BuildError('Require the exact exclusive notification patch/source pin')
    return pin, sources


def patch_source(root, source, pin):
    path = source / pin['source_path']
    if path.is_symlink() or builder.digest(path) != pin['source_sha256']:
        raise builder.BuildError('Notification source differs from the exact pinned parent')
    result = subprocess.run(['patch', '--batch', '--fuzz=0', '--forward', '-p1', '-d', str(source),
                             '-i', str(root / pin['patch'])], capture_output=True, text=True, timeout=15)
    if result.returncode or builder.digest(path) != pin.get('patched_source_sha256'):
        raise builder.BuildError('Exclusive notification patch did not produce reviewed bytes')


def build(root, baseline, jobs=2):
    pin, sources = inputs(root)
    original, runtime, evidence = check_runtime.verify_stage(root, baseline)
    # Only locked cached source bytes are used; this tool never downloads.
    spec = sources['quickshell']
    cache = root / 'work/source-cache'
    archive = cache / (spec['name'] + '-' + spec['commit'] + '.tar.gz')
    if archive.is_symlink() or not archive.is_file():
        raise builder.BuildError('Locked local source archive required; no download fallback')
    archive = builder.fetch_archive(spec, cache)
    parent = builder.private_directory(root / 'work/notification-runtime-builds')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    case = builder.private_directory(parent / stamp)
    for name in ('sources', 'build', 'home', 'logs'):
        builder.private_directory(case / name)
    # Reuse only the verified staged cpptrace/runtime inputs, never cached
    # compiler objects. Quickshell is configured and compiled from clean source.
    shutil.copytree(original / 'stage', case / 'stage', symlinks=True)
    report = {'schema_version': 1, 'status': 'running', 'baseline': str(original),
              'baseline_report_sha256': builder.digest(original / 'report.json'),
              'baseline_artifacts': evidence['artifacts'], 'source_lock': sources,
              'patch_sha256': pin['patch_sha256'], 'patched_source_sha256': pin['patched_source_sha256'],
              'pin_sha256': builder.digest(root / PIN), 'steps': [],
              'limits': 'Separate variant; no host bus/session, installation, runtime replacement or live deployment grant.'}
    report_path = case / 'report.json'

    def save():
        report_path.write_text(json.dumps(report, indent=2) + '\n')

    def step(name, command, environment=None, timeout=1200):
        args = builder.sandbox_command(case, command, case / 'sources', environment)
        entry = {'name': name, 'command': args, 'status': 'running'}
        report['steps'].append(entry);save()
        log = case / 'logs' / (name + '.log')
        print('Running ' + name + '; private log: ' + str(log), flush=True)
        with log.open('x') as stream:
            try:
                result = builder.run_with_heartbeat(name, lambda: subprocess.run(
                    args, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout, check=False))
                entry.update(returncode=result.returncode, status='passed' if result.returncode == 0 else 'failed')
            except subprocess.TimeoutExpired:
                entry.update(returncode=None, status='timeout')
        entry['log_sha256'] = builder.digest(log);save()
        if entry['status'] != 'passed':
            raise builder.BuildError('Variant step failed: ' + name)

    save()
    try:
        source = builder.extract_source(archive, case / 'sources', spec)
        patch_source(root, source, pin)
        manifest, _ = builder.load_inputs(root)
        step('sandbox-preflight', ['/usr/bin/true'], timeout=15)
        step('quickshell-configure', builder.cmake_command('quickshell', spec, manifest['proposed_cmake_options']['quickshell']), timeout=180)
        step('quickshell-build', ['cmake', '--build', '/build/quickshell', '--parallel', str(jobs)])
        step('quickshell-stage', ['cmake', '--install', '/build/quickshell'], {'DESTDIR': '/stage'}, timeout=120)
        step('quickshell-version', ['/stage' + builder.PREFIX + '/bin/quickshell', '--version'], timeout=30)
        assessed = builder.assess_outputs(case)
        report.update(assessed)
        report['status'] = STATUS
        report['baseline_unchanged'] = builder.artifact_manifest(original / 'stage') == evidence['artifacts']
        if not report['baseline_unchanged']:
            raise builder.BuildError('Baseline artifacts changed')
        report['binary_sha256'] = builder.digest(case / 'stage' / builder.PREFIX.lstrip('/') / 'bin/quickshell')
        report['native_source_sha256'] = builder.digest(source / pin['source_path'])
        report['builder_sha256'] = builder.digest(Path(__file__))
    except (OSError, ValueError, builder.BuildError, subprocess.SubprocessError) as error:
        report.update(status='failed', error=str(error));save();raise
    save()
    print('Variant built, not installed: ' + str(case), flush=True)
    return case


def verify(root, candidate):
    pin, sources = inputs(root)
    candidate = Path(candidate)
    if candidate.is_symlink() or (root / 'work').is_symlink() or (root / 'work/notification-runtime-builds').is_symlink():
        raise builder.BuildError('Refuse symlinked candidate parents')
    case = candidate.resolve()
    if case.parent != (root / 'work/notification-runtime-builds').resolve():
        raise builder.BuildError('Choose a direct private notification-runtime build')
    report_path = case / 'report.json'
    if report_path.is_symlink() or not report_path.is_file() or report_path.stat().st_size > 2_000_000:
        raise builder.BuildError('Require bounded real variant report')
    report = json.loads(report_path.read_text())
    if (report.get('schema_version') != 1 or report.get('status') != STATUS
            or report.get('source_lock') != sources or report.get('patch_sha256') != pin['patch_sha256']
            or report.get('patched_source_sha256') != pin['patched_source_sha256']
            or report.get('native_source_sha256') != pin['patched_source_sha256']
            or report.get('pin_sha256') != builder.digest(root / PIN)
            or report.get('builder_sha256') != builder.digest(Path(__file__))
            or report.get('baseline_unchanged') is not True or not report.get('shaders')
            or [s.get('name') for s in report.get('steps', [])] !=
                ['sandbox-preflight', 'quickshell-configure', 'quickshell-build', 'quickshell-stage', 'quickshell-version']
            or any(s.get('status') != 'passed' for s in report['steps'])):
        raise builder.BuildError('Require completed exact-source exclusive variant')
    stage = case / 'stage'
    if stage.is_symlink() or builder.artifact_manifest(stage) != report.get('artifacts'):
        raise builder.BuildError('Variant artifacts changed')
    runtime = stage / builder.PREFIX.lstrip('/')
    if builder.digest(runtime / 'bin/quickshell') != report.get('binary_sha256'):
        raise builder.BuildError('Variant binary changed')
    return case, runtime, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--jobs', type=int, default=2, choices=range(1, 5))
    args = parser.parse_args(argv)
    if not args.build:
        print('Plan only: clean offline exclusive-notification variant; never installs or activates')
        return 0
    if args.baseline is None:
        parser.error('--build requires --baseline')
    os.umask(0o077)
    build(ROOT, args.baseline, args.jobs)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
