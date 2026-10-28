# Separate floating-workspace membership from mode ownership

## Goal and evidence

Match Omarchy's two-tag arrange semantics for the reported workspace drag and
its titlebar: every window on a floating workspace receives a membership tag,
but only a window floated by the mode receives the ownership tag. Compare
`default/hypr/workspace-modes.lua` at pinned Omarchy commit
`03ff1eff3812933f7088484533784d2f63eaf19a` (private read-only reference under
work/reference), especially float_for_mode, tile_for_mode and arrange.
Existing upstream MIT provenance is recorded in upstream/omarchy-source.json.
No upstream files are imported or modified by this change.

## Current gaps

The claim eval returns for an already-floating window before tagging it.
The titlebar rule uses ownership instead of membership. Restore skips floating
windows, and release cannot remove presentation from unowned windows. Switching
a whole workspace must also add/remove membership on every member.

## Proposed shape

Keep omabuntu-mode-floated for ownership and introduce
omabuntu-floating-workspace for membership, following the original separation.
Update apply, claim, release and restore, retaining the serialized queue,
delayed move and special-workspace exclusion. Refresh named plugin rules even
when only membership changes. Preserve preexisting floating size and ownership.
Use membership for the existing hyprbars show rule; keep its stable name for
compatibility. Cover the actual Lua effects, not only generated strings.

## Safety and exclusions

Repository preparation only: no live eval, reload, window moves, installation,
service/session changes or commit. Back up edited source paths under ignored
work/ before implementation. A backed-up desktop deployment needs separate
approval. Keep the existing Ubuntu backend and pinned hyprbars compatibility.
Check version-appropriate official Lua/config references before changing rules.
This request covers the two-tag workspace/titlebar semantics, not wholesale
workspace-mode parity: first-frame open rules, fullscreen-exit arranging,
unmaximizing other windows, click-to-focus, opacity/shadow changes, floating as
the default, per-monitor numbering and notifications remain excluded.
Live drag/drop geometry and button acceptance require a later user test.

## Tasks

- [x] Check upstream semantics and version-appropriate configuration references.
- [x] Back up affected repository paths and record their previous state privately.
- [x] Add executable regressions and observe failure before implementation.
- [x] Implement separate membership across apply, claim, release and restore.
- [x] Regenerate the switcher and update its staged integrity hash.
- [x] Update documentation and WORKLOG.md; run the full unittest suite.

## Verification

Checked the local official Hyprland 0.56.2 example's Lua window-rule syntax and
the pinned hyprbars README's dynamic no_bar effect and Lua configuration API.
Backups include per-path hashes and modes under ignored work/. Regression tests
failed for missing arrival/departure membership before the implementation and
pass afterwards. All 561 unittests pass. The isolated desktop QML fixture also
passes with an already-floating restore candidate, without compositor access.
The real drag/drop interaction and button rendering remain unaccepted until
user observation.

## Approved deployment follow-up

The user approved applying this change to the running desktop with backups, and
then explicitly approved reconciling the malformed process-identity record.
Reconciliation requires unchanged PID/start ticks, current-user ownership, the
exact selected-release argv, and a saved original record. Do not relax the
manager's process checks or terminate an unverified process.
Prepare and verify a fresh local release. Back up the titlebar configuration,
process record and release/launcher selection state before changes. Stop only
the verified owned shell, install the release, update the matching titlebar
configuration, reload Hyprland configuration (not the compositor), check errors
and start the new shell with its session-lifetime grant. Do not change autostart,
packages, plugin binaries, unrelated configuration or applications. Retain the
old release and backups for recovery. Record private operational evidence under
ignored work/ and only a public summary here and in WORKLOG.md.

- [x] Prepare and verify a fresh local release and target backups.
- [x] Reconcile the approved malformed process record and restart the owned shell
      with the new release and membership-based titlebar rule.
- [x] Verify the installed release, runtime membership and configuration errors;
      record remaining visual acceptance.

## Deployment result and limits

The relocated bundle check and all 561 unittests pass. The backed-up, explicitly
approved record reconciliation restored the manager's normal ownership check.
The new shell is verified running and Hyprland reports no configuration errors.
No systemd/autostart change, package action, plugin replacement or commit occurred.
The existing floating window did not acquire membership automatically after this
startup. Applying the reviewed claim eval directly returned ok and added membership
while preserving float ownership. This confirms the compositor-side operation,
not automatic restore or the move-event path. Those remain pending live
confirmation along with titlebar rendering and buttons; do not count this
installation as complete functional acceptance. Private backup and operation
journals are retained under ignored work/floating-membership-deployment/.
