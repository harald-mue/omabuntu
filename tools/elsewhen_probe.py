#!/usr/bin/env python3
"""Read-only zone offsets for Elsewhen. No network and no timezone changes."""
import os
import re
import subprocess
import sys

ZONE = re.compile(r"^[A-Za-z0-9_+\-/]+$")
MAX_ZONES = 2000
DATE = "/usr/bin/date"
TIMEDATECTL = "/usr/bin/timedatectl"


def run(argv, env=None, timeout=3):
    return subprocess.run(argv, check=False, capture_output=True, text=True, timeout=timeout, env=env)


def probe(args):
    local = False
    zones = []
    for arg in args:
        if arg == "--local" and not local and not zones:
            local = True
            continue
        if not ZONE.fullmatch(arg):
            return 2
        zones.append(arg)
        if len(zones) > MAX_ZONES:
            return 2
    if local:
        shown = run([TIMEDATECTL, "show", "-p", "Timezone", "--value"])
        name = shown.stdout.strip() if shown.returncode == 0 else ""
        if ZONE.fullmatch(name):
            print("LOCAL|" + name)
            if name not in zones:
                zones.insert(0, name)
    for zone in zones:
        env = os.environ.copy()
        env["TZ"] = zone
        result = run([DATE, "+" + zone + "|%Z|%z"], env=env)
        line = result.stdout.strip()
        if result.returncode == 0 and line.startswith(zone + "|"):
            print(line)
    return 0


def zones():
    result = run([TIMEDATECTL, "list-timezones"], timeout=8)
    if result.returncode != 0:
        return 1
    for line in result.stdout.splitlines():
        if ZONE.fullmatch(line):
            print(line)
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return 2
    command, rest = argv[0], argv[1:]
    if command == "probe":
        return probe(rest)
    if command == "zones" and not rest:
        return zones()
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.SubprocessError):
        raise SystemExit(1)
