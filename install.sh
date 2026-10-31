#!/bin/sh
# Checkout entry point or HTTPS bootstrap for signed GitHub Releases.
# Never run the whole installer as root. Interactive pipe installs use /dev/tty.
set -eu

if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Omabuntu needs Python 3. Install python3 using Ubuntu, then retry.' >&2
    exit 1
fi
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -f "$0" ] && [ -f "$ROOT/tools/setup.py" ] && [ "${1:-}" != '--download-release' ]; then
    exec python3 -B "$ROOT/tools/setup.py" "$@"
fi
if [ "${1:-}" = '--download-release' ]; then
    shift
fi
if [ "$#" -ne 0 ]; then
    printf '%s\n' 'Remote installer takes no arguments; checkout options require a checkout.' >&2
    exit 2
fi
if [ "$(id -u)" = 0 ]; then
    printf '%s\n' 'Run as your normal user, not root.' >&2
    exit 1
fi
if ! command -v curl >/dev/null 2>&1 || ! command -v ssh-keygen >/dev/null 2>&1; then
    printf '%s\n' 'The release bootstrap needs curl and ssh-keygen (openssh-client).' >&2
    exit 1
fi
# Initial bootstrap trust is GitHub HTTPS, just like this script. Release archives
# additionally require the publisher signature. A pinned bootstrap ref is supported.
REF=${OMABUNTU_BOOTSTRAP_REF:-main}
case "$REF" in *[!A-Za-z0-9._-]*|'') echo 'Invalid bootstrap ref' >&2; exit 2;; esac
BASE="https://raw.githubusercontent.com/harald-mue/omabuntu/$REF"
TEMP=$(mktemp -d)
trap 'rm -rf -- "$TEMP"' EXIT HUP INT TERM
for FILE in tools/download_release.py tools/release_archive.py config/release-signing-key.pub; do
    curl --fail --silent --show-error --proto '=https' --proto-redir '=https' \
        --connect-timeout 15 --max-time 120 "$BASE/$FILE" -o "$TEMP/$(basename "$FILE")"
done
# stdin may be the curl pipe. Python and all approval prompts read the terminal.
python3 -B "$TEMP/download_release.py" --public-key "$TEMP/release-signing-key.pub" </dev/tty
