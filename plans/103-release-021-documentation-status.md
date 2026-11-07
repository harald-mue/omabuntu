# Reconcile documentation after v0.2.1 publication

## Goal and evidence

The user reports successful v0.2.1 publication and requests documentation updates.
Compare public GitHub release metadata/asset digests, local/remote tag targets,
retained signed artifacts and source export against README, release documentation,
Update availability wording and plan 102. The source remains pinned to Omarchy
v4.5.0 commit `ac2690cd7be4f47e4a255f5e2e78d904d436b068`; no component changes.

## Gaps and proposed shape

README and docs/releases.md still describe v0.2.1 as preparation and name v0.2.0
as latest. Plan 102 still leaves commit/build/publication incomplete. Update menu
documentation says a future release must deliver the feature. Verify publication
and retained artifact integrity, then correct these statements while preserving
historical metadata-check evidence and outstanding native acceptance gates.

## Safety and exclusions

Back up affected documents under ignored work/. Verification is read-only apart
from private reports and disposable verification extraction. Do not change the
published tag/assets, prior release workspaces, installed application, desktop,
preferences, wallpaper, packages, services or signing configuration. Do not read
private keys, request credentials, commit or push. Publication is not real update-
pair, recovery, GNOME, fresh-machine or blanket security acceptance.

## Tasks

- [x] Verify public release state, tag/commit, four asset digests and retained artifacts.
- [x] Update README, release/Update documentation and plan 102 with verified status.
- [x] Run unit tests and whitespace checks; report remaining acceptance limits.

## Result

v0.2.1 is public/non-prerelease, published on 2026-11-07 at 15:47:10 UTC from
`26e9ca4dca0752569bbd17b7a717a1210445e85e`. Local/remote tags match. All four
retained artifact digests/sizes match GitHub. Publisher signature, original Git
source export/packaged-source identity, bundle integrity and artwork exclusion
verify successfully. Evidence and document backups remain private under ignored
`work/release-021-docs-103/`.

README now names v0.2.1 as latest, describes the shipped Update menu and uses
an unused future version in the publishing example. Release/Update documentation
records publication without implying installation or native update-switch
acceptance. Plan 102 is complete, with its prior preparation state kept historical.
All 1132 unit tests and whitespace checks pass. No commit, push, published-artifact
change or desktop deployment was performed.
