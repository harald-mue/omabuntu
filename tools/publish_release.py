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
import tempfile

import release_archive
import download_release

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'harald-mue/omabuntu'
VERSION = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+')


def run(*args, cwd=ROOT, capture=False, timeout=120):
    # Release output must not stop in less, regardless of personal pager settings.
    environment = {**os.environ, 'GIT_PAGER': 'cat', 'GH_PAGER': 'cat', 'PAGER': 'cat'}
    return subprocess.run(args, cwd=cwd, check=True, text=True, env=environment,
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
    # Verification is repeatable without replacing earlier extraction evidence.
    with tempfile.TemporaryDirectory(prefix='archive-check-', dir=directory) as temporary:
        checked = Path(temporary) / 'unpacked'
        release_archive.extract(archive, checked)
        import user_install
        user_install.verify_bundle(checked / 'bundle')


def review_existing(case, version, commit):
    """Review complete pre-publication artifacts, never rebuild or overwrite them."""
    if case.is_symlink() or not case.is_dir():
        raise ValueError('No safe release workspace to resume')
    archive = case / artifact_name(version)
    record = case / 'release.json'
    sums = case / 'SHA256SUMS'
    source = case / 'source.tar'
    for path in (archive, record, sums, source):
        if path.is_symlink() or not path.is_file():
            raise ValueError('Incomplete or unsafe release artifact: ' + path.name)
    expected = download_release.checksums(sums.read_text())
    if set(expected) != {archive.name, record.name}:
        raise ValueError('Unexpected checksum entries')
    for path in (archive, record):
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[path.name]:
            raise ValueError('Release artifact changed: ' + path.name)
    metadata = json.loads(record.read_text())
    if (metadata.get('schema_version') != 1 or metadata.get('version') != version
            or metadata.get('commit') != commit or metadata.get('archive') != archive.name
            or metadata.get('target') != 'ubuntu-26.04-x86_64'
            or metadata.get('artwork_included') is not False
            or metadata.get('bytes') != archive.stat().st_size
            or metadata.get('sha256') != expected[archive.name]):
        raise ValueError('Existing release metadata does not match version/HEAD/target')
    exported = subprocess.check_output(['git', 'archive', '--format=tar', commit], cwd=ROOT, timeout=120)
    if hashlib.sha256(exported).digest() != hashlib.sha256(source.read_bytes()).digest():
        raise ValueError('Original source export differs from the committed tree')
    # The outer tar must contain exactly the source export, not a modified
    # post-build checkout. Safe extraction and bundle verification follow signing.
    def source_entries(stream, prefix=''):
        result = {}
        for member in stream.getmembers():
            if prefix and not member.name.startswith(prefix):
                continue
            name = member.name[len(prefix):]
            if name in result or not (member.isfile() or member.isdir()):
                raise ValueError('Duplicate or unsupported source archive entry')
            digest = hashlib.sha256(stream.extractfile(member).read()).hexdigest() if member.isfile() else None
            result[name] = (member.type, member.mode, digest)
        return result
    with tarfile.open(source) as original, tarfile.open(archive) as packaged:
        if source_entries(original) != source_entries(packaged, 'source/'):
            raise ValueError('Packaged source differs from the committed export')
    with tempfile.TemporaryDirectory(prefix='resume-check-', dir=case) as temporary:
        checked = Path(temporary) / 'unpacked'
        release_archive.extract(archive, checked)
        import user_install
        release = user_install.verify_bundle(checked / 'bundle')
        if release['version'] != 'release-' + version:
            raise ValueError('Bundle version differs from release version')
        for name in ('backgrounds', 'themes-previews'):
            images = checked / 'bundle/config/menu' / name
            if images.exists() and any(images.rglob('*')):
                raise ValueError('Resume bundle contains theme artwork')
    return archive, record, sums


def sign_artifacts(assets, key, public, case):
    sums = assets[2]
    signature = Path(str(sums) + '.sig')
    if signature.exists() or signature.is_symlink():
        if signature.is_symlink() or not signature.is_file():
            raise ValueError('Unsafe signature file')
        download_release.verify(public, sums, signature, case)
        return
    # Retain failed attempts as evidence; never clobber a previous signature.
    attempt = Path(tempfile.mkdtemp(prefix='signing-', dir=case))
    copied = attempt / 'SHA256SUMS'
    copied.write_bytes(sums.read_bytes())
    run('ssh-keygen', '-Y', 'sign', '-f', key, '-n', 'omabuntu-release', str(copied), timeout=None)
    created = Path(str(copied) + '.sig')
    download_release.verify(public, copied, created, attempt)
    if copied.read_bytes() != sums.read_bytes():
        raise ValueError('Checksums changed during signing')
    with signature.open('xb') as output:
        output.write(created.read_bytes())


def publish_artifacts(args, assets, public, case, commit, resume=False, head=None):
    sign_artifacts(assets, args.signing_key, public, case)
    check_artifacts(assets, public, case)
    tag = 'v' + args.version
    snapshot = {p: hashlib.sha256(p.read_bytes()).digest()
                for p in (*assets, Path(str(assets[2]) + '.sig'))}
    print('Artifacts:', case, '\nCommit:', commit, '\nTag:', tag)
    confirm('Push main and ' + tag + ', then publish these artifacts on GitHub?')
    if run('git', 'rev-parse', 'HEAD', capture=True).strip() != (head or commit):
        raise ValueError('HEAD changed; refusing publication')
    if run('git', 'status', '--porcelain', capture=True).strip():
        raise ValueError('Working tree changed; refusing publication')
    if any(hashlib.sha256(p.read_bytes()).digest() != digest for p, digest in snapshot.items()):
        raise ValueError('Artifacts changed after review')
    run('git', 'tag', '-a', tag, '-m', 'Omabuntu ' + args.version, commit)
    run('git', 'push', '--atomic', 'origin', 'HEAD:refs/heads/main', 'refs/tags/' + tag)
    run('gh', 'release', 'create', tag, '--repo', REPOSITORY, '--verify-tag', '--draft',
        '--title', 'Omabuntu ' + args.version, '--notes',
        'Ubuntu 26.04 x86_64. Native Hyprland ABI requirements still apply. No theme artwork included.',
        *(str(p) for p in (*assets, Path(str(assets[2]) + '.sig'))))
    run('gh', 'release', 'edit', tag, '--repo', REPOSITORY, '--draft=false')
    print('Published ' + tag + '. Local artifacts retained at ' + str(case))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--resume-signing', action='store_true',
                        help='Verify existing artifacts from HEAD or an ancestor, then resume signing/publication; clean checkout required, no commit or build')
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
    actual = run('ssh-keygen', '-y', '-f', args.signing_key, capture=True, timeout=None).strip().split()[:2]
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
    if not args.resume_signing and case.exists():
        raise ValueError('Release workspace already exists; use make release-resume VERSION=' + args.version + ' only for complete pre-publication artifacts')
    run('git', 'fetch', 'origin', 'main', '--tags')
    run('git', 'merge-base', '--is-ancestor', 'origin/main', 'HEAD')
    if run('git', 'tag', '--list', tag, capture=True).strip():
        raise ValueError('Tag already exists')
    if run('git', 'diff', '--name-only', '--diff-filter=U', capture=True).strip():
        raise ValueError('Resolve Git conflicts before releasing')
    if args.resume_signing:
        if run('git', 'status', '--porcelain', capture=True).strip():
            raise ValueError('Review and commit pending fixes before resuming; the existing bundle is not rebuilt')
        head = run('git', 'rev-parse', 'HEAD', capture=True).strip()
        record = case / 'release.json'
        if case.is_symlink() or record.is_symlink() or not record.is_file():
            raise ValueError('No safe release metadata to resume')
        commit = json.loads(record.read_text()).get('commit', '')
        if not isinstance(commit, str) or not re.fullmatch(r'[a-f0-9]{40}', commit):
            raise ValueError('Invalid recorded release commit')
        run('git', 'merge-base', '--is-ancestor', commit, head)
        assets = review_existing(case, args.version, commit)
        print('Existing bundle/tag commit: ' + commit + '\nMain to push: ' + head)
        print('Later committed fixes are pushed to main but NOT included in the existing archive.')
        confirm('Resume signing this verified existing bundle without rebuilding?')
        publish_artifacts(args, assets, public, case, commit, resume=True, head=head)
        return
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
    publish_artifacts(args, assets, public, case, commit)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit('Release stopped: ' + str(error))
