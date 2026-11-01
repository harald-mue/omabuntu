# Review the 0.1.1 source before commit and publication

## Goal and evidence

Review the accumulated installer, package scopes, hyprpm, login, migration and
application-handoff changes after the user reported that the live bar works.
Compare source/tests/docs with the recorded local verification and existing
exact-commit signed publication path. Pins remain Hyprland 0.57.0 commit
0aa6745f705f2c4b0a5004eb019ef76e5bbdb426, plugins
d2427d4d15b36df40468f5a58bbd67cdba19835d and Omarchy reference
03ff1eff3812933f7088484533784d2f63eaf19a. Do not copy private inventories into Git.

## Shape and safety

Inventory intended changed/new files, review mutation/approval/recovery boundaries,
perform limited secret/provenance checks, reconcile release documentation and
add regressions/fix concrete review findings if necessary. Back up each edited
repository path first. Re-run all tests, clean-source and whitespace checks.
Report remaining acceptance limits honestly: one workstation result is not
stock-VM, first/repeat login or generic migration acceptance.

No desktop action, package/manager mutation, private-profile edit, signing-key
access, Git staging/commit/tag/push or publication during this review. Ask for
separate commit and publication consent after presenting the reviewed scope.
A clean-source check or limited pattern scan is not comprehensive secret,
license or security acceptance. Keep raw review output private under work/.

## Tasks

- [x] Inventory intended files and review source/test/approval boundaries.
- [x] Check publication exclusions and limited secret/provenance indicators.
- [x] Resolve concrete findings and add regressions if needed.
- [x] Reconcile release notes/status with verified and unverified behavior.
- [x] Run full verification and present commit/publication scope for approval.

## Findings and verification

Fixed ordinary plugin preparation's live update reconciliation gap: header/build
updates run without the compositor signature, accept exit 1 only after complete
header/global-ABI/repository postconditions, record verified header fingerprints,
recheck state/policy/receipts between commands and refuse malformed/failed output.
Real execution cannot use fixture path overrides. Live enablement is still a
separate approved operation; concurrent external manager commands are unsupported.

Fixed next-login preparation's stale enablement probe. Actual unit state is now
rechecked before writes and service actions. A failed reload/enable attempt is
marked recovery-required rather than fully restored. Failed initial wallpaper
publication restores the new record; unrelated pre-existing lock state is refused.
Updated fixture rehearsal to supply explicit simulated service state, not inspect
the host's unit state.

959 unit tests passed. Clean-source and whitespace checks passed. A fresh
artwork-free reviewed candidate was built and preflighted but not installed.
A limited indicator scan of 453 tracked/intended source files found no matching
private-key/token/workstation-path indicators. No new third-party assets/code
were imported; existing source/license pins remain recorded. Raw reports/backups
and build/runtime inventories remain private under ignored work/.

Stock-VM, first/repeat login and a second distinct live same-target update/rollback
remain unaccepted. Workstation handoff and user-reported visible operation do not
establish generic visual/security acceptance. Publication remains an explicit
later gate; no staging, commit, signing, push or release publication was performed.
