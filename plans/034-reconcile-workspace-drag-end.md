# Reconcile a tiled window after a cross-workspace drag ends

## Goal and evidence

A normally tiled window moved onto a floating workspace should become a
comfortably sized floating window without a maximize/restore round trip.
Preserve existing floating geometry and intentional maximized/fullscreen state.
The behavioral reference remains Omarchy commit
03ff1eff3812933f7088484533784d2f63eaf19a, float_for_mode/place and delayed
window.move_to_workspace arrangement. No new upstream import is planned.

The local official Hyprland 0.56.2 DragController.cpp temporarily floats a tiled
drag target and can tile it again in dragEnd. LayoutManager.cpp emits
changefloatingmode as address,0/1. The socket provides no explicit drag-end
signal; the supported Lua event set also has no mouse-button/drag-end callback.
The current shell only claims after move and fullscreen events.

## Current gaps and safety constraints

A move-time claim can see temporary floating and skip placement; a later native
retile may not get another claim. Confirm the actual event ordering before
choosing a targeted correlation rule. An indiscriminate floating-mode listener
would also undo an intentional manual tiling action and is not acceptable.
Do not force unmaximize, resize preexisting floating windows, infer completion
from a fixed mouse-drag timeout, change bindings or patch compositor/plugin ABI.
No live window manipulation, deployment, reload/restart, packages or commit.
Any approved passive trace is filtered to event names, addresses, numeric states
and workspace ids under ignored work/; do not collect titles or input contents.
Back up affected source paths before implementation. Desktop application remains
a separate approval gate.

## Proposed shape and exclusions

Use native event evidence to select a narrowly correlated, deferred recheck for
the moved window after drag-end retile. Reuse the serialized claim queue and
live Lua destination/fullscreen checks. Do not guess a correlation that could
silently override unrelated manual floating choices. If supported events cannot
reliably distinguish the required cases, report that limitation before changing
semantics or adding native input/plugin integration.

## Tasks

- [x] Compare pinned upstream arrangement and local versioned drag/event sources.
- [x] Capture a reduced native move/drop event sequence and establish correlation.
- [x] Back up edited source paths and add a failing event-sequence regression.
- [x] Implement the approved floating-workspace retile policy; regenerate mirror/hash.
- [x] Test the recorded drag sequence, preexisting float, fullscreen,
      stale/closed/moved-again candidates, manual retile and disabled/revoked grants;
      run all unittests and QML fixtures.
- [x] Update documentation and WORKLOG.md with verified limits and deployment gate.

## Current investigation boundary

The first filtered trace collected no matching events. A second, coordinated
reproduction captured floating-on, move-to-floating-workspace, and floating-off
for the same addressed window, with several seconds between move and release.
Before the drag it was tiled and non-fullscreen; afterwards it was still tiled
and non-fullscreen, with workspace membership but no mode ownership. This is
retile-at-drop, not actual maximization. Private addresses/geometry/timing remain
only under ignored work/drag-end-observation/.

The supported event stream does not report why floating changed. A manual
float-on, move, then manual float-off can produce the same sequence. Even an
address-correlated one-shot watcher could undo that later intentional action;
a time cutoff would instead fail a held drag. Therefore do not implement the
previously proposed automatic correlation as if it preserved all manual choices.
No implementation or live state change has been made. Ask the user before
changing the policy to automatically keep non-fullscreen windows floating on
floating workspaces (manual tiling there would be overridden). Retaining manual
tiling requires separately investigated reliable drag-completion integration,
not an assumed socket signal.

## Approved policy revision

The user subsequently approved keeping normal windows floating on a floating
workspace, including correcting intentional manual tiling there. This is an
explicit policy extension beyond Omarchy's addressed move/fullscreen handlers,
not a claim that the socket can distinguish a drag from manual toggles.
On a valid addressed changefloatingmode event with state zero, look up that
window's workspace and defer a claim only if it is a granted positive floating
workspace. Deduplicate candidates and reuse the serialized queue. Recheck the
grant when the timer fires and the live destination/state in Lua. Ignore state
one so the corrective float does not create a feedback loop. Do not infer a
maximum drag duration, force unmaximize, or resize an already-floating window.
Claims are also blocked during active/queued workspace-mode changes away from
floating, so native floating-off events from that change do not undo it.
Tiling/scrolling and special workspaces remain outside this policy. Unknown or
closed candidates are ignored; a moved-again candidate cannot alter the stale
destination. Source preparation is approved; live deployment remains separate.

## Implementation verification

Source backups include per-path hashes and modes under ignored work/.
The isolated QML replay failed without the new handler because drop queued no
correction. It now passes the native move/drop sequence, duplicate and malformed
events, unknown/special/tiling candidates, manual-retile policy, disabled/revoked
grants and suppression during a workspace-mode switch, including an older queued
claim. Real Lua exercises move-time floating, native retile, corrective ownership
and placement, duplicate preservation, fullscreen guards and moved-again
rejection; existing tests cover closed windows and both fullscreen modes.
All 565 unittests pass, the final isolated QML fixture passes, generated mirror
and integrity hash match, and git diff --check passes. No desktop deployment,
window manipulation, reload/restart or commit was performed for this policy.
Actual native drag/drop placement and resize acceptance require a later approved
deployment and user observation.

## Approved deployment follow-up

The user explicitly approved installation with backups and an owned-shell-only
restart. Prepare a fresh immutable local bundle and verify relocation. Back up
the launcher/process record and saved modes, record selector prestate, and use
the transaction-backed installer. Verify manager ownership before stopping,
then install/start and check integrity, startup logs and configuration errors.
Do not reload Hyprland, alter config/bindings/autostart/plugin binaries, or
manipulate application windows for acceptance. Keep the previous release for
rollback; stop and ask on unverified process identity rather than repairing it
without a new approval.

- [x] Prepare/verify the new bundle and target backups.
- [x] Install and restart the manager-verified owned shell.
- [x] Verify installed state and record pending native drag/resize acceptance.

## Deployment result

The new bundle passed isolated relocation verification and all 565 unittests.
The retile-policy release is manager-verified running with clean startup logs
and no compositor configuration errors. The launcher, process record and saved
workspace modes are backed up; selector prestate and transaction recovery are
recorded privately under ignored work/retile-policy-deployment/. Saved modes
and compositor config hashes are unchanged. Only the owned shell was restarted;
no Hyprland reload, config/binding/autostart/plugin change, synthetic live event,
application test manipulation or commit occurred during deployment.

## User feedback and deferred behavior

The user confirmed that basic native drag/drop correction works. A brief position
change at mouse release remains consistent with the shared resize/center/cascade
placement path. The user explicitly chose to leave this behavior unchanged for
now; preserving the drop geometry is deferred, not implemented. Manual-retile
behavior and pointer resizing have isolated test coverage but were not separately
live-accepted. Startup restoration remains a separate unconfirmed case.
