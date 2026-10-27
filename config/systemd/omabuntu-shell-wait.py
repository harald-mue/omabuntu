#!/usr/bin/env python3
"""Wait until Hyprland's instance lock is visible to hyprctl.

Hyprland 0.56.2 imports WAYLAND_DISPLAY before it writes hyprland.lock, and
`hyprctl instances -j` prints a lone ']' when that list is empty. Login
autostart can observe that window. This polls until the live instance is
listed. It does not start the shell, and the deadline is not a shell lifetime.
"""
import json
import os
import re
import subprocess
import sys
import time

ATTEMPTS = 40
PAUSE_SECONDS = 0.25


def parse_instances(stdout):
    """Return a list of instance objects, or None when hyprctl output is not one."""
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if type(parsed) is not list or any(type(item) is not dict for item in parsed):
        return None
    return parsed


def instance_visible(instances, signature, display):
    return any(item.get('instance') == signature and item.get('wl_socket') == display for item in instances)


def query_instances(command=('hyprctl', 'instances', '-j')):
    return subprocess.run(command, capture_output=True, text=True, timeout=2, check=False)


def wait_for_instance(signature, display, run=query_instances, attempts=ATTEMPTS, pause=PAUSE_SECONDS):
    """Poll until signature/display match. Invalid JSON is not ready, not fatal."""
    if not signature or not re.fullmatch(r'wayland-\d+', display or ''):
        raise ValueError('Hyprland session environment is not ready')
    last = None
    for attempt in range(attempts):
        query = run()
        if query.returncode == 0:
            last = parse_instances(query.stdout)
            if last is not None and instance_visible(last, signature, display):
                return last
        if attempt + 1 < attempts and pause:
            time.sleep(pause)
    if last is None:
        raise ValueError('Hyprland instance list was not ready')
    raise ValueError('Hyprland session environment does not match its live socket')


def main():
    try:
        wait_for_instance(os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', ''),
                          os.environ.get('WAYLAND_DISPLAY', ''))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
