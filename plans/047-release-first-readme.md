# Release-first README

## Goal and evidence

Make the README primarily serve users installing a published GitHub Release with
one curl command. Compare the current README with install.sh, download_release.py,
published_install.py and the Makefile. The README still mixes checkout-only
rollback/build steps with end-user installation and contains obsolete update and
channel wording. No upstream behavior or desktop configuration changes; an
Omarchy pin comparison is not relevant to this documentation request.

## Shape and constraints

Keep the requested wordmark. Put the supported target and curl installation first,
then explain updates using the same command. Preserve honest publication,
compatibility, trust and separate session-activation limitations. Move detailed
build/deployment topics out of the README in favor of existing linked operator
and developer documentation. Remove obsolete channel terminology and commands
from the README, not pending unrelated implementation work. Do not publish,
commit, install, change the desktop or modify private files.

## Tasks

- [x] Rewrite README for release users and keep developer instructions separate.
- [x] Add documentation regressions and verify links and installer consistency.
- [x] Run the full unit suite and update WORKLOG.md.

## Verification

804 tests passed, including new README checks for identical curl install/update
commands, absence of obsolete channel/stage guidance, safety statements and local
link targets. Whitespace checks passed. No real download or installation was
performed; the first-release availability warning remains deliberately visible.
