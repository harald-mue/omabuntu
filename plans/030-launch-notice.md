# Show Omarchy's delayed application-launch notice

## Goal

When an application is started from the app grid or the floating dock and no
window has appeared after two seconds, show the short "Launching …" notice
Omarchy shows. Remove it when a window opens or the focused window changes,
and after fifteen seconds at the latest.

## Evidence compared

Pinned Omarchy commit `03ff1eff3812933f7088484533784d2f63eaf19a`.
`shell/services/AppLibrary.qml` `beginLaunchFeedback()` records the toplevel
count and the active toplevel, then starts a 2000 ms delay and a 15000 ms
limit. The delay calls `omarchy-shell osd show` with glyph U+F14DE, message
`appLibrary.launching` ("Launching %1…") or `appLibrary.launchingApp`, and
`duration: 0`. A new toplevel or a changed active toplevel closes it early.
`shell/plugins/osd/Osd.qml` draws that payload at the bottom center of an
overlay whose input mask is empty. The app grid and the dock both call
`AppLibrary.launch()`; a direct key binding does not.

This shell starts those same two surfaces through `DesktopEntry.execute()`.
It has no OSD plugin and no `omarchy-shell` command. The dock's icon pulse is
a separate animation.

## Current project gaps

- Neither launcher records a launch against the toplevel list.
- No overlay draws the launching message.
- The English label catalog has no `appLibrary.launching` entries.

## Safety constraints

- Do not call `omarchy-shell`, `notify-send`, `uwsm-app`, or `hyprctl`.
- Do not add a notification daemon, idle behavior, or a launch on a key chord.
- Do not restart the running bar, reload Hyprland, or start an application.
- Keep the offscreen launcher fixture free of timers and of real execution.

## Proposed shape

1. Add one overlay, `LaunchFeedback.qml`, with the two Omarchy timers, the
   toplevel check, the empty input mask, and no process or shell command.
2. Call it from the app grid and the dock immediately before the existing
   `DesktopEntry.execute()`, and create it from `TrialShell`.
3. Add the two English catalog strings. Record the new authored file and the
   changed source hashes.

## Explicit exclusions

- Volume, brightness, and media OSD.
- The original notification daemon and toast stack.
- `omarchy-launch-tui` and `uwsm-app` launch wrapping.
- Notices for programs started by a key binding rather than the grid or dock.
- A German catalog. The staged shell labels stay English.
- Updating the running bar. That remains a separate approval.

## Tasks

- [x] Add the overlay and wire it to the grid and the dock.
- [x] Add the English strings, the review hashes, and unit checks.
- [x] Document the notice and the exclusions.
