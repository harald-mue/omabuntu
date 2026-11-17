# Review, commit and prepare a local release

## Goal and evidence

Review and commit the pending network-widget and monitor-local workspace changes
under the user's initial commit approval, without pushing at that checkpoint.
Then determine the next local release build inputs and version without publishing. Compare the
working tree to HEAD, plans 115-120, original-source provenance and generated
mirrors, the test suite, and the existing release/build entry points. Omarchy
behavior remains pinned to v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`.

## Current gaps and proposed shape

Both already prepared feature groups are still uncommitted, including shared
provenance and staging files. Review them together rather than dropping the
network work or splitting shared files without evidence. Record the user's
positive interactive feedback without claiming unobserved hotplug or fresh-login
acceptance. Validate staged paths, notices, sensitive-data candidates and tests,
then create one English Conventional Commit. Identify the nonpublishing build
route; agree on a numeric release version before creating versioned artifacts.

## Safety and exclusions

The initial approval covered committing and forbade pushing. The user later
explicitly authorized a normal main push, then handled publication in their own
shell. Those later permissions do not authorize force-push, license/package,
Git-configuration/hook or live-desktop changes. Keep private reports, source
diffs, logs, backups, local artifacts and machine data under ignored work/.
`make release` was excluded during the agent's local-only build because it also
tags and publishes. Existing private installed releases must not be repacked as
distributable artifacts.

## Tasks

- [x] Review all pending paths and original-source/generated provenance.
- [x] Record interactive feedback and historical-plan handoff accurately.
- [x] Check sensitive-data candidates, whitespace and the complete test suite.
- [x] Create the initially approved commit without pushing.
- [x] Confirm the desired release version and build only through a local route.

## Pre-commit checkpoint

The reviewed candidate contains both feature groups and their source notices,
provenance, tests and plans; no ignored work artifacts are intended for staging.
All 1,279 tests pass and source/mirror verification covers 127 staged shell files.
The sensitive-data candidate review found only synthetic test/sandbox home paths,
not real user-home paths, credential material or private inventory dumps. This
bounded review is not a guarantee that pattern matching can detect every secret.

At the pre-commit checkpoint the latest local release tag was v0.2.3. The existing
source-build route supports
`--build-release --release-version <version> --skip-artwork --apply` without
publication or desktop deployment. A numbered release build awaited version
confirmation at that point; no publisher, signing-key operation, tag or push
was authorized then.

## Completed follow-up

Commit `7fa2760` recorded the reviewed feature changes; all 1,279 tests passed
and the checkout was clean. The user confirmed local v0.2.4 preparation and
subsequently authorized a normal main push. A fresh isolated committed-source
build, archive/source/bundle validation and local signature verification
completed without desktop deployment. Main was pushed and checked against the
built commit, without creating a release tag in that local-only operation.

The maintainer subsequently ran `make release VERSION=0.2.4` in their own shell,
performing a fresh publication build rather than resuming the separate local
candidate. Plan 122 verifies and documents the resulting public release. Its
published archive digest, not the separate local candidate's digest, identifies
the downloadable release.
