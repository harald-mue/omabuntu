#!/bin/sh
# Omabuntu setup entry point. Run as a normal user, never via sudo.
# Default is read-only. Prepared local releases require explicit --bundle/--apply.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Omabuntu needs Python 3. Install python3 using Ubuntu, then retry.' >&2
    exit 1
fi
exec python3 -B "$ROOT/tools/setup.py" "$@"
