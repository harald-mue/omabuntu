"""Bounded release archive extraction; never follow archive links."""
from pathlib import Path, PurePosixPath
import tarfile

MAX_BYTES = 4 * 1024**3
MAX_FILES = 50000


def extract(archive, destination):
    destination = Path(destination)
    if destination.exists():
        raise ValueError('Extraction destination must not exist')
    with tarfile.open(archive, 'r:*') as stream:
        members = stream.getmembers()
        if len(members) > MAX_FILES or sum(m.size for m in members) > MAX_BYTES:
            raise ValueError('Archive exceeds extraction limits')
        seen = set()
        for member in members:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or '..' in path.parts or not path.parts
                    or member.name in seen):
                raise ValueError('Unsafe or duplicate archive path')
            seen.add(member.name)
            # The runtime intentionally contains exactly this relative alias.
            alias = (member.issym() and member.name == 'bundle/runtime/bin/qs'
                     and member.linkname == 'quickshell')
            if not (member.isfile() or member.isdir() or alias):
                raise ValueError('Unsupported archive entry: ' + member.name)
            if member.mode & 0o7000:
                raise ValueError('Privileged archive mode')
        destination.mkdir(mode=0o700, parents=True)
        stream.extractall(destination, members=members, filter='data')
