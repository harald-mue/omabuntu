# Prepare and publish Omabuntu v0.2.1

## Goal and evidence

Prepare the user-requested signed artwork-free v0.2.1 through the existing
publisher. Compare the v0.2.0 baseline, local Appearance commit, uncommitted
Update implementation, publisher packaging and acceptance evidence. Admitted
Omarchy components remain pinned to v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; no upstream update scripts are added.

## Initial gaps and proposed shape (historical)

Main contains the unpublished Appearance commit plus uncommitted Update work.
The publisher creates bundle versions `release-VERSION`, but the new updater
currently treats these as private versions and compares incoming bundle names
directly to numeric signed metadata. Correct both comparisons with narrow
canonical public-version normalization, keeping strict signed metadata parsing,
local-adaptation refusal and downgrade blocking. Exercise real publisher-style
bundle names in temporary transaction/recovery tests before publication.

Record bounded 0.2.1 scope in release documentation without claiming it is
already published. Review the full candidate files and provenance, run unit,
clean-source and relevant contained checks, then request commit approval.
Use the committed source export and existing interactive publisher for build,
signing and separate public push/release confirmation. User enters any key
passphrase privately; never request or record it.

## Safety and exclusions

Back up changed existing paths under ignored work/. Do not modify the installed
release to fix repository code or bypass its local-release safety. No desktop
restart/deployment, preferences, wallpaper, GNOME/session transition, package
installation, privileged action, service/plugin activation, key/config changes,
force push, tag/artifact replacement or license change. Preserve prior releases
and failed evidence. Exclude private source evidence, inventories, backups and
artwork from publication. Ask before committing; signing and publishing retain
the publisher's explicit interactive gates. Public release preparation does not
establish a real version-pair update/recovery or generic native/security acceptance.

## Tasks

- [x] Inspect branch, worktree, publisher and local/remote v0.2.1 availability.
- [x] Fix and regression-test publisher bundle-version compatibility.
- [x] Prepare release scope documentation and review publication candidate.
- [x] Run full tests, clean-source and contained menu checks.
- [x] Obtain approval and commit reviewed preparation.
- [x] Build fresh isolated artwork-free artifacts and sign/verify interactively.
- [x] Publish after confirmation and verify remote tag/assets/signature.

## Initial preflight (historical)

Local main is at the unpublished Appearance commit. Remote main remains at the
v0.2.0 documentation follow-up. No local/remote v0.2.1 tag, GitHub release or
publication workspace was found. Required publisher commands and the signing-key
path environment setting are present; no private key was read. v0.2.0 remains
the latest public release until v0.2.1 is actually published.

## Prepared source and verification

The new publisher-style bundle regression fixtures failed against the original
updater, confirming both installed-version and candidate-version mismatches.
The correction normalizes only the exact `release-` prefix followed by a strict
numeric public version. Incoming signed metadata stays strictly numeric; nested
prefixes, local suffixes, local-adaptation markers, mismatched candidate versions
and downgrades remain refused. Transaction and startup-failure recovery fixtures
now use `release-VERSION` bundles. All 1132 unit tests pass.

README and release documentation describe v0.2.1 as preparation, retaining
v0.2.0 as the published release. Scope is Appearance controls/rendering fixes
plus the application-only Update menu, not the rejected desktop gesture.
Clean-source and contained command-menu checks pass, as does whitespace review.
The 20-file uncommitted candidate was reviewed alongside the already committed
Appearance scope. A limited private-key/token/machine-home pattern check found
no matches; this is not a comprehensive secret/history or license certification.
No new third-party code/assets were imported. Backups, negative-control failures,
candidate inventory and check logs are private under ignored
`work/release-021-preparation/`.

At the end of preparation, commit approval was still pending; no staging,
commit, build, signing, push, tag, publication or desktop change had occurred.

## Completed publication

The user approved the preparation commit `26e9ca4`
(`chore(release): prepare v0.2.1`) and subsequently completed the interactive
publisher. Public [v0.2.1](https://github.com/harald-mue/omabuntu/releases/tag/v0.2.1)
was published on 2026-11-07 at 15:47:10 UTC, neither draft nor prerelease. Local
and remote tags resolve to `26e9ca4dca0752569bbd17b7a717a1210445e85e`.

Post-release verification under plan 103 confirms all four expected assets,
retained hashes/sizes matching GitHub asset digests, valid publisher signature,
original source export/packaged-source identity, bundle integrity and excluded
theme artwork. Private verification evidence remains under ignored
`work/release-021-docs-103/`. These checks establish publication, not fresh-machine,
GNOME, real public-version update-pair/self-restart or native recovery/security
acceptance. Published tags/assets and the running private desktop are unchanged
by documentation follow-up.
