#!/usr/bin/env python3
"""Minimize a Hyprland window to special:minimized with dock restore tags.

Mirrors the pinned Omarchy helper without omarchy-* binaries. Titlebar buttons
run this through hyprbars exec; the bar focuses the window before the click.
"""
import json
import subprocess
import sys

TAG_PREFIX = 'omabuntu-minimized-from-'
FLOATED_TAG = 'omabuntu-mode-floated'
MINIMIZED_WORKSPACE = 'special:minimized'


def hyprctl_json(args):
    result = subprocess.run(
        ['hyprctl', *args, '-j'],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def dispatch(expr):
    subprocess.run(
        ['hyprctl', 'dispatch', expr],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def remember_minimized_from(address, workspace_id, tags):
    for tag in tags:
        if not tag.startswith(TAG_PREFIX):
            continue
        if tag == f'{TAG_PREFIX}{workspace_id}':
            continue
        dispatch(
            f'hl.dsp.window.tag({{ tag = "-{tag}", window = "address:{address}" }})'
        )
    dispatch(
        f'hl.dsp.window.tag({{ tag = "+{TAG_PREFIX}{workspace_id}", '
        f'window = "address:{address}" }})'
    )


def resolve_target(address=None):
    if address:
        clients = hyprctl_json(['clients']) or []
        for client in clients:
            if client.get('address') == address:
                workspace = client.get('workspace') or {}
                workspace_id = workspace.get('id')
                if isinstance(workspace_id, int):
                    return address, workspace_id, client.get('tags') or []
        return None
    active = hyprctl_json(['activewindow'])
    if not active:
        return None
    address = active.get('address')
    workspace = active.get('workspace') or {}
    workspace_id = workspace.get('id')
    if not address or not isinstance(workspace_id, int):
        return None
    return address, workspace_id, active.get('tags') or []


def main(argv=None):
    args = list(argv if argv is not None else sys.argv[1:])
    address = args[0] if args else None
    resolved = resolve_target(address)
    if not resolved:
        return 1
    address, workspace_id, tags = resolved
    if FLOATED_TAG not in tags:
        return 0
    remember_minimized_from(address, workspace_id, tags)
    dispatch(
        f'hl.dsp.window.move({{ workspace = "{MINIMIZED_WORKSPACE}", '
        f'follow = false, window = "address:{address}" }})'
    )
    dispatch(f'hl.dsp.focus({{ workspace = "{workspace_id}" }})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
