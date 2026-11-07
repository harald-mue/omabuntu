# Reconcile documentation after the v0.2.0 publication

## Goal and evidence

Update README, release scope and plans 090/091 to reflect the completed v0.2.0
publication without modifying its immutable tag or artifacts. Compare GitHub
release state/assets, local/remote tag commit and retained signed build metadata.
The included Omarchy component baseline remains v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; no component or configuration changes
are part of this documentation request.

## Gaps and shape

README still calls v0.1.9 current and v0.2.0 upcoming. Release documentation says
publication is pending, and plans retain open preparation/recovery tasks. Preserve
historical initial observations with explicit labels, then record the verified
outcome. Document the private-work-root build fix in release scope and use a
clearly illustrative future version in the publisher example. Do not invent a
next-version commitment or claim new native/security acceptance.

## Safety and exclusions

Back up affected repository paths before editing. Read-only release checks,
private validation reports and repository documentation writes only. No signing
key access, build, desktop changes, commit, push, retagging, release editing or
artifact replacement. Published source remains unchanged; this is a post-release
source-documentation follow-up requiring separate commit approval.

## Tasks

- [x] Verify published release, tag/source identity and retained artifact integrity.
- [x] Back up and update README, release scope and completed plans.
- [x] Run full unit tests and diff checks; record remaining acceptance limits.

## Outcome

Verified public non-prerelease v0.2.0 at source commit
`9537b211a02fa5f74c40558f3f31f218e0427ec2`, published 2026-11-07 at
00:02:56 UTC. All four expected asset hashes match GitHub's digests; retained
signature, source-export, bundle-integrity and artwork-exclusion checks pass.
No private signing key was accessed and no release asset/tag was modified.

README now identifies v0.2.0 as current and labels its future release-command
version as an example, not a commitment. Release scope includes the private-root
build fix. Plans 090/091 retain historical diagnosis/preflight and record completed
publication/recovery without promoting that result to native/security acceptance.
All 1086 unit tests and `git diff --check` pass. Backups, validation report and
logs remain under ignored `work/release-020-docs-092/`. No commit or push occurred.
