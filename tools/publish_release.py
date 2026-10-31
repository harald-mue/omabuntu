#!/usr/bin/env python3
"""Build a committed tree and explicitly publish a signed GitHub Release."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

import release_archive
import download_release

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'harald-mue/omabuntu'
VERSION = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+')


def run(*args, cwd=ROOT, capture=False, timeout=120):
    return subprocess.run(args, cwd=cwd, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          timeout=timeout).stdout


def confirm(message):
    # A terminal is not seekable: buffered r+ fails before showing the prompt.
    with open('/dev/tty', 'w') as output, open('/dev/tty', 'r') as terminal:
        output.write(message + ' Type yes: ')
        output.flush()
        if terminal.readline().strip() != 'yes':
            raise ValueError('Cancelled; no further actions performed')


def artifact_name(version):
    if not VERSION.fullmatch(version):
        raise ValueError('Use a numeric release VERSION, for example 0.1.0')
    return 'omabuntu-' + version + '-ubuntu-26.04-x86_64.tar.gz'


def package(tree, bundle, destination, version, commit):
    import sys
    sys.path.insert(0, str(tree / 'tools'))
    import user_install
    user_install.verify_bundle(bundle)
    for name in ('backgrounds', 'themes-previews'):
        directory = bundle / 'config/menu' / name
        if directory.exists() and any(directory.rglob('*')):
            raise ValueError('Public releases must not contain theme artwork')
    archive = destination / artifact_name(version)
    with tarfile.open(archive, 'w:gz') as stream:
        # Repack the original Git export, not the post-build tree (__pycache__,
        # reports and generated files may have appeared there during compilation).
        with tarfile.open(destination / 'source.tar', 'r:') as source:
            for member in source.getmembers():
                item = copy.copy(member)
                item.name = 'source/' + member.name
                stream.addfile(item, source.extractfile(member) if member.isfile() else None)
        stream.add(bundle, arcname='bundle')
    metadata = {'schema_version': 1, 'version': version, 'commit': commit,
                'target': 'ubuntu-26.04-x86_64', 'archive': archive.name,
                'bytes': archive.stat().st_size,
                'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'artwork_included': False}
    record = destination / 'release.json'
    record.write_text(json.dumps(metadata, indent=2) + '\n')
    sums = destination / 'SHA256SUMS'
    sums.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n'
                            for p in (archive, record)))
    return archive, record, sums


def check_artifacts(assets, public_key, directory):
    """Exercise the downloader's signature and extraction gates before uploading."""
    archive, record, sums = assets
    download_release.verify(public_key, sums, Path(str(sums) + '.sig'), directory)
    for name, expected in download_release.checksums(sums.read_text()).items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Artifact changed before publication: ' + name)
    checked = directory / 'archive-check'
    release_archive.extract(archive, checked)
    import user_install
    user_install.verify_bundle(checked / 'bundle')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--signing-key', default=os.environ.get('OMABUNTU_RELEASE_SIGNING_KEY'))
    args = parser.parse_args()
    artifact_name(args.version)
    if os.getuid() == 0:
        raise ValueError('Run as your normal user, not root')
    for command in ('git', 'gh', 'ssh-keygen'):
        if not shutil.which(command):
            raise ValueError('Required command missing: ' + command)
    public = ROOT / 'config/release-signing-key.pub'
    if not args.signing_key or not public.is_file():
        raise ValueError('Configure config/release-signing-key.pub and OMABUNTU_RELEASE_SIGNING_KEY first; see docs/releases.md')
    actual = run('ssh-keygen', '-y', '-f', args.signing_key, capture=True).strip().split()[:2]
    if not actual or actual[0] != 'ssh-ed25519':
        raise ValueError('Use an Ed25519 publisher signing key')
    if actual != public.read_text().strip().split()[:2]:
        raise ValueError('Signing key does not match the tracked publisher public key')
    if run('git', 'branch', '--show-current', capture=True).strip() != 'main':
        raise ValueError('Release from main only')
    if run('git', 'remote', 'get-url', 'origin', capture=True).strip() not in (
            'https://github.com/' + REPOSITORY, 'https://github.com/' + REPOSITORY + '.git',
            'git@github.com:' + REPOSITORY + '.git'):
        raise ValueError('Unexpected origin; refusing publication')
    tag = 'v' + args.version
    case = ROOT / 'work/publish' / tag
    if case.exists():
        raise ValueError('Release workspace already exists; review it manually: ' + str(case))
    run('git', 'fetch', 'origin', 'main', '--tags')
    run('git', 'merge-base', '--is-ancestor', 'origin/main', 'HEAD')
    if run('git', 'tag', '--list', tag, capture=True).strip():
        raise ValueError('Tag already exists')
    if run('git', 'diff', '--name-only', '--diff-filter=U', capture=True).strip():
        raise ValueError('Resolve Git conflicts before releasing')
    status = run('git', 'status', '--short', capture=True)
    print(status or 'Clean working tree.')
    untracked = run('git', 'ls-files', '--others', '--exclude-standard', capture=True)
    if untracked:
        raise ValueError('Review and stage intended new files first; untracked files are never auto-added')
    run('git', 'diff', 'HEAD', '--stat')
    confirm('Commit all tracked changes for ' + tag + ', download/build without artwork, and sign locally? Review git diff HEAD first.')
    run('python3', '-m', 'unittest', 'discover', '-s', 'tests', '-v', timeout=600)
    run('git', 'diff', '--check')
    if status:
        run('git', 'add', '-u')
        run('git', 'commit', '-m', 'chore(release): prepare ' + tag)
    if run('git', 'status', '--porcelain', capture=True).strip():
        raise ValueError('Working tree changed during preparation; inspect before retrying')
    commit = run('git', 'rev-parse', 'HEAD', capture=True).strip()
    case.mkdir(parents=True, mode=0o700)
    run('git', 'archive', '--format=tar', '-o', str(case / 'source.tar'), commit)
    tree = case / 'tree'
    release_archive.extract(case / 'source.tar', tree)
    code = ('import sys; from pathlib import Path; sys.path.insert(0,"tools"); '
            'import bootstrap_build as b, install as g; '
            'p=b.create_plan(Path.cwd(), artwork=False, version=sys.argv[1]); '
            'b.apply(p,g.digest(p))')
    # This isolated tree contains no workstation configuration or cached artifacts.
    run('python3', '-c', code, 'release-' + args.version, cwd=tree, timeout=14400)
    assets = package(tree, tree / 'work/user-releases' / ('release-' + args.version),
                     case, args.version, commit)
    run('ssh-keygen', '-Y', 'sign', '-f', args.signing_key, '-n', 'omabuntu-release', str(assets[2]))
    check_artifacts(assets, public, case)
    print('Artifacts:', case, '\nCommit:', commit, '\nTag:', tag)
    confirm('Push main and ' + tag + ', then publish these artifacts on GitHub?')
    if (run('git', 'rev-parse', 'HEAD', capture=True).strip() != commit
            or run('git', 'status', '--porcelain', capture=True).strip()):
        raise ValueError('HEAD or working tree changed; refusing publication')
    run('git', 'tag', '-a', tag, '-m', 'Omabuntu ' + args.version, commit)
    run('git', 'push', '--atomic', 'origin', 'HEAD:refs/heads/main', 'refs/tags/' + tag)
    run('gh', 'release', 'create', tag, '--repo', REPOSITORY, '--verify-tag', '--draft',
        '--title', 'Omabuntu ' + args.version, '--notes',
        'Ubuntu 26.04 x86_64. Native Hyprland ABI requirements still apply. No theme artwork included.',
        *(str(p) for p in (*assets, Path(str(assets[2]) + '.sig'))))
    run('gh', 'release', 'edit', tag, '--repo', REPOSITORY, '--draft=false')
    print('Published ' + tag + '. Local artifacts retained at ' + str(case))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit('Release stopped: ' + str(error))
