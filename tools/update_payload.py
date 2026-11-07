"""Stage the reviewed updater import closure and data without running it."""
import ast
from pathlib import Path

RESOURCES = ('config/release-signing-key.pub', 'packages/installer-runtime.json', 'upstream/hyprpm.json')


def modules(root):
    pending = ['application_update', 'published_release']
    seen = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        path = root / 'tools' / (name + '.py')
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing/linked updater module: ' + name)
        seen.add(name)
        for node in ast.walk(ast.parse(path.read_text())):
            names = ([alias.name.split('.')[0] for alias in node.names] if isinstance(node, ast.Import)
                     else [node.module.split('.')[0]] if isinstance(node, ast.ImportFrom) and node.module else [])
            pending.extend(n for n in names if (root / 'tools' / (n + '.py')).exists() and n not in seen)
    return sorted(seen)


def stage(root, destination):
    paths = ['tools/' + name + '.py' for name in modules(root)] + list(RESOURCES)
    for name in paths:
        source = root / name
        if source.is_symlink() or not source.is_file():
            raise ValueError('Missing/linked updater input: ' + name)
        target = destination / 'updater' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        target.chmod(0o444)
