# Review, commit and prepare a local release

## Goal and evidence

Review and commit the pending network-widget and monitor-local workspace changes
under the user's explicit commit approval, without pushing. Then determine the
next local release build inputs and version without publishing. Compare the
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

The user explicitly approves committing and explicitly forbids pushing. Do not
push, publish, create a remote release, change licensing, install packages, alter
Git configuration or hooks, or modify/restart the live desktop. Keep private
reports, source diffs, logs, backups, local artifacts and machine data under ignored
work/. `make release` is excluded because it also tags and publishes. Existing
private installed releases must not be repacked as distributable artifacts.

## Tasks

- [x] Review all pending paths and original-source/generated provenance.
- [x] Record interactive feedback and historical-plan handoff accurately.
- [x] Check sensitive-data candidates, whitespace and the complete test suite.
- [ ] Create the explicitly approved commit without pushing.
- [ ] Confirm the desired release version and build only through a local route.

## Pre-commit checkpoint

The reviewed candidate contains both feature groups and their source notices,
provenance, tests and plans; no ignored work artifacts are intended for staging.
All 1,279 tests pass and source/mirror verification covers 127 staged shell files.
The sensitive-data candidate review found only synthetic test/sandbox home paths,
not real user-home paths, credential material or private inventory dumps. This
bounded review is not a guarantee that pattern matching can detect every secret.

The latest local release tag is v0.2.3. The existing source-build route supports
`--build-release --release-version <version> --skip-artwork --apply` without
publication or desktop deployment. A numbered release build awaits version
confirmation; no publisher, signing-key operation, tag or push is authorized.
