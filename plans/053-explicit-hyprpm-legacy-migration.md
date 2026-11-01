# Explicit migration of the known mixed Hyprpm legacy state

## Goal and evidence

Provide a review-only migration plan and separately confirmed application for the
known official hyprland-plugins legacy state: old 0.56 source pin, successful
0.57 build metadata, enabled hyprbars, stale global manager ABI and no Omabuntu
receipt. Do not fabricate ownership or trust the old binary as a new build.
Compare official Hyprland 0.57.0 commit
0aa6745f705f2c4b0a5004eb019ef76e5bbdb426, previous 0.56.2 commit
efb50993780079460b0cbed1363e2166a2de1d9f, and plugin revisions
d2427d4d15b36df40468f5a58bbd67cdba19835d and
7644cecdb947060682891a0db2a0cdc5c0b9e704. Omarchy behavior remains compared
against 03ff1eff3812933f7088484533784d2f63eaf19a.

Review the pinned manager disable/remove/add/load-state implementations and state
serialization before coding. Evidence remains private under work/. Notably,
disable writes enablement before load-state reconciliation and can return 1 for
outdated headers; this must not be blindly treated as success or ignored.

## Gaps and shape

Normal preparation rightly refuses an unowned enabled or differently pinned
repository. Add an explicit migration action, not weaker normal guards. Require
a clean supported 0.57 installed/running pair with matching ABI, no loaded
plugins, exactly the known official repository, safe filenames and no unrelated
enabled plugin or existing ownership receipt. Refuse unknown source/build pairs.
Back up/cache global pkg-config bytes and ownership/modes before changes; journal
each command and intermediate postconditions under the existing control lock.

Use official commands: disable hyprbars, explicitly remove/re-register the one
reviewed repository, refresh headers with no registered repositories, and add
the pinned 0.57 source. No direct TOML edits, force options or cache purge.
Repository replacement needs an additional exact interactive confirmation.
Header refresh uses the installed binary and runs with the compositor signature
removed only from its child environment. The official final load-state phase then
returns 1 before IPC; accept that only after proving exact fresh header/global ABI
postconditions. Do not permit a long-running refresh to unload a plugin that
appears concurrently.
Recognize a nonzero disable result only for the source-proven stale-ABI case,
after proving that the sole expected enablement change actually occurred and
that nothing loaded or otherwise drifted. Any other failure stops with retained
manual-recovery evidence. Verify new header/global ABI and pinned disabled build
before writing a receipt. Do not automatically restore old enablement, load a
plugin, retry a failed operation or delete backups.

## Safety and exclusions

Implementation/testing only: no actual package install, sudo, manager commands,
plugin load/unload, configuration changes, services or session transitions.
No private-profile adoption, old bundled-library handoff, commit, push or
publication. Review-only migration must not invoke even hyprpm list, because
manager queries can initialize privileged state. Live activation remains a
separate approval after successful migration. Native/VM acceptance is separate.

## Tasks

- [x] Review pinned disable/remove semantics and define narrow eligibility.
- [x] Add migration plans, double consent and guarded journaled application.
- [x] Test expected disable partial failure, drift, failure and ownership guards.
- [x] Document operator/recovery commands and remaining native acceptance.
- [x] Run full unit tests, clean-source verification and whitespace checks.

## Verification and operator gates

896 unit tests passed; clean-source verification and whitespace checks passed.
The local read-only review recognizes the supported mixed state and reports the
still-missing direct build prerequisites. It invokes no manager command, not
even list. Package installation and a real migration were not performed.

Fixtures cover archive-byte verification (including owner/group/mode), exact
replacement consent, normal-guard preservation, stale-header disable convergence,
isolated header-refresh convergence, rejected nonconvergent errors, unknown pins,
foreign plugins, executable/package/source drift, inter-step changes, missing
prerequisites and refusal of real execution for fixture path overrides. The real
executor is bound to the reviewed root-owned Hyprland-package-owned system
binary; its hash/metadata are rechecked. A newly completed receipt remains
inactive and normal activation is still separately reviewed.

- [ ] Separately approve/install the reviewed additive prerequisite transaction.
- [ ] Run the real interactive migration and verify its retained journal/results.
- [ ] Separately approve live plugin loading, titlebar/private-loader handoff and
  any subsequent persistent login integration; establish native/VM acceptance.

No real package or manager mutation, plugin load/unload, private configuration
change, service/session action, commit, push or publication was performed.
