# Remove obsolete release channels

## Goal and evidence

Remove the unused local dev/stable distribution mechanism completely. The current
setup CLI still imports release_channels and exposes schema/writer/resolver
options, while published downloads already select GitHub Releases independently.
Active operator documentation still advertises removed-design compatibility.
Compare setup.py, release_channels.py, the associated tests, release download
entry points, and plans 044/045. No desktop behavior changes; no upstream pin
comparison is required.

## Shape and safety

Remove the channel module, tests and tracked pin file. Remove parser flags,
validation and dispatch; do not reinterpret legacy flags as another operation.
Add regressions ensuring obsolete flags are rejected before work can run.
Update active documentation to describe only checkouts and published releases.
Mark plan 044 superseded and the compatibility parts of plan 045 superseded,
retaining their original historical evidence. Keep current build, signature,
installation and rollback approvals intact. Preserve pending worklog-removal
changes; do not recreate that file. Back up affected paths privately under work/.
No commit, push, publication, downloads or desktop/system changes are authorized.

## Tasks

- [x] Back up affected paths and remove channel files and CLI support.
- [x] Update current documentation and mark superseded plans explicitly.
- [x] Test obsolete-option refusal and run full tests and clean-source checks.

## Verification

802 tests passed; clean-source and whitespace checks passed. Regression tests
verify removed options exit with parser errors before any operation and disappear
from help. Active code and operator documentation no longer reference the removed
mechanism. Remaining mentions are historical plans and negative regression tests.
No release, desktop action, Git commit or push was performed.
