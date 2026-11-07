# Verify v0.2.2 publication and reconcile documentation

## Goal and evidence

The user reports successful v0.2.2 publication. Compare public GitHub release
state/asset digests, local/remote tag targets and retained signed source/bundle
artifacts with README, operator/release/compatibility documentation and plan 106.
Omarchy components remain pinned to v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; no implementation changes.

## Gaps and proposed shape

Documentation still describes v0.2.2 as preparation, names v0.2.1 as latest and
says compatibility fixes need publication. Verify actual publication before
updating those claims and marking plan 106 complete. Keep fresh-VM, plugin,
lock/recovery, GNOME and real update-pair acceptance explicitly separate.

## Safety and exclusions

Back up each affected document under ignored work/. Public/source verification
is read-only except for private reports and disposable verification extraction.
No private key access, published-artifact replacement, installation, package/
source change, plugin activation, lock/authentication action, desktop/session
operation, commit or push. Preserve immutable prior artifacts and local state.

## Tasks

- [x] Verify release state, local/remote tag, four asset digests and signed artifacts.
- [x] Reconcile release/operator documentation and complete plan 106.
- [x] Run full tests and whitespace checks; retain private evidence and report limits.

## Result

Public non-prerelease v0.2.2 was published on 2026-11-07 at 18:17:35 UTC from
`bb5a20c63bcc4e9e2a295497aba60aa4aadb7043`. Local/remote tags agree. All four
retained assets match GitHub digests/sizes. Publisher signature, original source
export/packaged-source identity, bundle integrity and artwork exclusion verify.
Private evidence and document backups are retained under ignored
`work/release-022-docs-107/`.

README, release/operator/compatibility/dependency/Update documentation now name
the published delivery, with an unused future version in the publisher example.
Plan 106 records completed commit/push/build/publication, retaining preparation
history. All 1158 tests and whitespace checks pass. Native fresh-VM, plugin,
lock/recovery, GNOME/login and actual update-pair acceptance are still open.
No commit, push, published-artifact change or installed-desktop operation was
performed in this documentation follow-up.
