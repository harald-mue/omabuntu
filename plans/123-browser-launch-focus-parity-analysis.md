# Analyze browser launch/focus parity

## Goal and evidence

Explain why selecting an already running browser in the application grid may
leave the user on an unchanged workspace. Compare the current Omabuntu launcher,
dock and launch feedback with original Omarchy v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`, especially AppLibrary launch dispatch,
browser wrappers and existing-window activation. Check the pinned Quickshell
DesktopEntry implementation where needed; distinguish source behavior from the
unobserved native browser outcome.

## Current gap and proposed shape

The reported symptom could involve single-instance browser behavior, application
identity matching, launch arguments or workspace activation. Trace each route
before proposing a change; app-grid launch and dock focus may intentionally have
different semantics. Record precise original behavior and any omitted adapters,
then explain whether a source-aligned repair or an explicit behavior choice is
needed. No implementation is authorized by this comparison request.

## Safety and exclusions

Read repository/cached upstream sources or retrieve pinned upstream files only
into ignored private work/. Do not modify the separate reference package. No
real application launch, window focus/move, workspace switch, browser/profile or
installed configuration edits, process/service changes, reload, install, commit
or push. Do not inspect browser history, tabs, credentials or private profiles.
Keep raw diagnostic material under ignored work/.

## Tasks

- [x] Verify the pinned original app-grid/AppLibrary/browser launch routes.
- [x] Trace Omabuntu's app-grid, dock and DesktopEntry execution behavior.
- [x] Compare focus/workspace/single-instance handling and document limits.
- [x] Explain the discrepancy and a narrowly scoped next step without live changes.

## Result

The original grid launches through AppLibrary/GTK/UWSM, not the dock's existing-
window activation function. Original look-and-feel explicitly enables
`misc.focus_on_activate`; Omabuntu's templates omit it and the read-only runtime
probe confirmed the default false/unset state. Reviewed Hyprland source shows
that this can reject an existing window's eligible focus request, consistent
with the symptom. Browser/request/token behavior was not exercised live.

Eleven retrieved original source files matched their pinned Git blob identities.
The trace and global-versus-grid-only repair boundary are documented in
`docs/browser-launch-focus-parity.md`; raw evidence stays under ignored work/.
All 1,279 tests pass. No desktop behavior or installed configuration was changed.
