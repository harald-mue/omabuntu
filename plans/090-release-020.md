# Build and publish Omabuntu 0.2.0

## Goal and evidence

Build, sign and publish an artwork-free GitHub Release v0.2.0 using the existing
reviewed publisher. Compare docs/releases.md, the publication checklist,
Makefile and tools/publish_release.py against the clean committed main tree,
current remote metadata and the v0.1.9 baseline. Included Omarchy components are
pinned to v4.5.0 stable commit `ac2690cd7be4f47e4a255f5e2e78d904d436b068`.
The user explicitly requested building and public release publication.

## Gaps and proposed shape

At planning time, README named 0.1.10 as the next release. Record 0.2.0 preparation and scope:
stable admitted Omarchy components, preserved fullscreen HDR behavior and manual
Chrome titlebar guidance. Keep fresh-machine, GNOME/browser and native acceptance
limits explicit. Ask before the preparation commit. Use the committed export,
not the live installation or a private development bundle. Run tests and clean-
source checks, review provenance/exclusions, then use the existing build,
package, SSH signing, verification, annotated-tag, atomic push and draft-to-
public release flow. Preserve failed build/signing evidence rather than overwrite.

## Safety and exclusions

User approval covers release build/downloads and publication to the existing
harald-mue/omabuntu remote, not desktop deployment. No package installation,
privileged action, service/plugin/compositor reload, browser/profile change,
key generation, credential printing, Git configuration change, force push or
license change. Private signing key contents must not be read or copied into
workspace/logs. Interactive passphrase entry remains with the user. Do not
replace existing tags/releases/artifacts. Keep private inputs, theme artwork,
logs and backups out of source and release archives. Obtain explicit preparation
commit approval; do not bypass publisher integrity or confirmation gates.

## Tasks

- [x] Review publisher documentation, tools, clean tree, branch, origin and version availability.
- [x] Prepare version/scope documentation and obtain preparation commit approval.
- [x] Run full tests, clean-source checks and publication/provenance review.
- [x] Commit reviewed preparation after approval and build fresh isolated artifacts.
- [x] Sign and verify checksums, source/bundle integrity and artwork exclusion.
- [x] Publish v0.2.0 and verify remote tag, release state and expected assets.

## Initial preflight (historical)

Main is clean at `078b654`; origin/main currently precedes the two local desktop
and installer commits. GitHub's latest release is v0.1.9. No local v0.2.0 tag,
remote v0.2.0 tag, GitHub release or same-version publication workspace was found.
GitHub CLI authentication and required publisher tools are available. The
publisher signing-key path environment variable is configured; no private key
was read during this preflight. No build, signing, commit, push or publication
has occurred yet.

Preparation updates README's next-version label to v0.2.0 while keeping v0.1.9
as the latest published release, and adds the bounded 0.2.0 scope to
`docs/releases.md`. All 1082 unit tests, isolated clean-source checks and
`git diff --check` pass. Logs/backups remain under ignored
`work/release-020-preparation/`. The user subsequently approved the preparation
commit `49828f5`; the publisher's passphrase entry remained with the user.

## Completed publication

The first isolated build exposed a private-directory ordering bug. Plan 091
records its tested fix and preservation of the failed workspace. The user then
ran the interactive publisher, which committed the fix as `9537b21`, built a
fresh export and published [v0.2.0](https://github.com/harald-mue/omabuntu/releases/tag/v0.2.0)
on 2026-11-07 at 00:02:56 UTC. Local and remote tags resolve to
`9537b211a02fa5f74c40558f3f31f218e0427ec2`.

Post-release verification confirms public/non-prerelease state and all four
expected assets. Retained artifact hashes match GitHub asset digests; signature,
source-export identity, bundle integrity and artwork-exclusion checks pass.
The corrected source passes all 1086 unit tests and isolated clean-source checks.
Private verification evidence is under ignored `work/release-020-docs-092/`.

This completes publication, not fresh-machine, GNOME/PWA, all-button-action or
native/security acceptance. No desktop deployment was part of the release.
Documentation follow-up leaves the published tag and artifacts unchanged.
