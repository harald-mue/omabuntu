# Diagnose browser-native minimize and restore on floating workspaces

## Goal and evidence

Investigate the user's report that browser-owned minimize and restore-from-
maximized buttons do not work after the approved hyprbars exception. Compare
read-only client/internal fullscreen state, active profile rules, installed
Omabuntu workspace reconciliation/minimize helper and official Hyprland 0.57.0
Wayland request handling. Component baseline remains Omarchy v4.5.0 stable,
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`.

## Current gap and shape

Removing duplicate decorations does not establish that client-side buttons
invoke the same compositor-specific actions as hyprbars. Establish native
minimize handling separately from maximize/unmaximize requests and internal/
client fullscreen-state synchronization. Look for suppress-event policy and
workspace reconciliation before proposing a change. Distinguish static-source
findings from a reproduced click/event trace.

## Safety and exclusions

Read-only diagnosis; private filtered evidence under ignored work/. No window
movement, minimize/maximize dispatch, browser restart, shared GNOME/GTK setting
write, compositor/plugin reload, session transition, profile/policy change or
commit. Do not read page titles, URLs, credentials or full browser profiles.
Any controlled interactive reproduction or configuration fix needs separate
approval. Preserve GNOME, current user state and recorded deployment rollback.

## Tasks

- [x] Inspect client/fullscreen state and the relevant workspace/minimize code.
- [ ] Check version-specific native requests and relevant profile policy.
- [x] Document confirmed causes, remaining uncertainty and the next bounded test.

## Findings and remaining uncertainty

Official Hyprland v0.57.0 source forwards native Wayland minimize requests through
XDGShell/WaylandBackend, but CWindow::onUpdateState does not consume the minimized
field. It handles only fullscreen/maximized requests. The Omabuntu minimize
helper is a separate compositor-dispatch path; client controls are not functionally
equivalent to hyprbars. This confirms the native minimize gap, not a click trace.

Maximize requests have special client/internal state handling; a snapshot showed
no internal/client maximization at collection time. The exact restore failure
and complete effective per-window policy have not been reproduced, so that part
of the diagnosis remains open. The subsequent user choice in plan 083 is to use
compositor-side controls and hide supported client controls process-locally.
`docs/process-local-window-controls.md` records the source findings and required
browser/floating interaction checks. No desktop changes were made in this analysis.
