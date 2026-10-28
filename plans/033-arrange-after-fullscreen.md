# Arrange floating-workspace windows after fullscreen changes

## Goal and evidence compared

Complete the reported maximize/restore/resize path with Omarchy's delayed
window.fullscreen arrangement at pinned commit
03ff1eff3812933f7088484533784d2f63eaf19a. The read-only private reference's
watch() delays arrange({window}) by one millisecond; float_for_mode leaves
maximized/fullscreen windows alone and claims/places eligible tiled windows
when the fullscreen state becomes zero.

The local official Hyprland 0.56.2 source posts the socket event fullscreen with
only 0/1, without an address, for maximized as well as fullscreen state changes.
Its Lua event has an addressed window, but this port already uses Quickshell's
socket event bridge. The pinned Quickshell connection refreshes workspaces on
fullscreen events; do not infer the affected window from focus or stale IPC
fullscreen flags. The existing claim eval checks live Lua window state.

## Current project gaps

The switcher handles openwindow and movewindowv2 but not fullscreen. A window
can acquire a membership titlebar, then leave maximization while still tiled.
A sole tiled window still fills its workspace and cannot resize as floating.
The prior update's automatic startup restore is also unconfirmed; this change
must not silently claim that separate issue is fixed.

## Proposed shape

Coalesce valid fullscreen events through a one-millisecond single-shot timer.
Because the socket event has no address, rescan known toplevels on floating
workspaces through the existing serialized claim queue. The eval rechecks the
destination and live fullscreen/floating state. Never force unmaximize or resize
an already-floating window. Keep normal tiling, special workspaces, ownership
and workspace membership semantics unchanged. Document the broader rescan
adaptation relative to Omarchy's addressed Lua handler.

## Safety and explicit exclusions

Repository preparation only: no window manipulation, desktop deployment,
restart/reload, package action, autostart or commit. Back up edited source paths
under ignored work/ first. Live application needs separate approval. No new
plugin API/configuration, altered button command, forced unmaximize, focus
change, first-frame open rules, unmaximize-others, click-to-focus, shadows or
opacity changes. Keep startup-restore uncertainty explicit.

## Tasks

- [x] Record upstream/event semantics and back up affected source paths.
- [x] Add an executable QML event/timer regression and observe it fail.
- [x] Add the delayed event rescan and regenerate the switcher/integrity hash.
- [x] Exercise maximize/fullscreen exit, placement and already-floating preservation
      with real Lua and mock dispatchers.
- [x] Run all unittests and the isolated QML fixture; update documentation/worklog.

## Verification and deployment boundary

The original handler fails the isolated QML regression with no queued fullscreen
candidates; the new handler passes, including delayed scheduling, serialized
claims, excluding tiled workspaces and revocation before the timer fires.
The fixture includes no-op workspace/toplevel refresh methods for the dock's
existing fullscreen listener and a diagnostic-only watchdog to fail promptly.
Real Lua tests exercise both maximized (1) and fullscreen (2) states followed
by zero, ownership assignment, one placement and preservation on repeated calls.
All 563 unittests pass and the isolated QML fixture passes. The generated mirror
and staged hash match; git diff --check passes. No live eval, window changes,
restart/reload, install or commit occurred for this follow-up. Actual drag,
maximize/restore and pointer resizing require approved deployment and live
observation; the earlier startup-restoration issue remains unconfirmed.

## Approved deployment follow-up

The user explicitly approved installing this follow-up with backups and an
Omabuntu-shell-only restart. Prepare a fresh immutable release, verify relocation,
back up the launcher/process record and record current/previous selectors and
saved workspace modes. Stop only the manager-verified owned shell, install with
the transaction-backed manager and start with its session-lifetime grant.
Do not reload Hyprland, edit compositor configuration, change autostart or plugin
binaries, or manipulate application windows. Retain the previous release and
verify startup logs, installed integrity, configuration errors and saved modes.
Stop and report unexpected ownership/identity failures rather than bypassing them.

- [x] Prepare and verify the new bundle and private deployment backups.
- [x] Install and restart only the verified Omabuntu shell.
- [x] Check integrity/runtime status and document pending live interaction tests.

## Deployment result

The fresh local bundle passed relocation verification and all 563 unittests.
The new installed shell is manager-verified running; startup logs and compositor
configuration checks are clean. The launcher and process record are backed up;
current/previous selection and saved-mode prestate are recorded privately, and
installation has its own transaction backup. Saved modes and compositor config
hashes are unchanged. No Hyprland reload, plugin/config/autostart change, window
manipulation or commit occurred. The existing window was already floating before
this restart and remains so; this is not evidence of a maximize/restore event.
Actual drag, maximize/restore and pointer resize still need user observation,
as does the previously unconfirmed startup-restoration case. Private operation
journals remain under ignored work/fullscreen-arrange-deployment/.
