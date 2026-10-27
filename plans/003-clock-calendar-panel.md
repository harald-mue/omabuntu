# Clock calendar popup

Status: implementation in this change. This plan does not approve a bar
restart, a release installation, a Hyprland binding, package installation, or
execution of any Omarchy helper.

## Goal

Left-clicking the clock in the live trial bar opens Omarchy's calendar popup
from commit `03ff1eff3812933f7088484533784d2f63eaf19a`: the month grid with ISO
week numbers, the year-progress rail, the optional life rail, and month
stepping. The sealed read-only clock label stays unchanged.

## Evidence compared

Pinned manual `manual/05-the-top-bar.md`: left click is the calendar, right
click cycles the label, middle click is the timezone picker. The popup source
is `shell/plugins/panels/clock/Panel.qml` (791 lines, MIT). It is a read-out,
not a date picker. Today is outlined. Chevrons, the wheel, and the arrow keys
step the month. The grid is always six rows. `W` toggles the week start.
Double-tapping the year rail edits a birth year and a life expectancy.

`BarWidget.qml` loads that panel from an always-active Loader. Right click
walks `Model.js` formats and writes the choice through `updateEntryInline`.
Middle click runs `omarchy-menu-timezone`, which calls `sudo timedatectl
set-timezone`. `ShellIpc` exposes open, close, and toggle. The hotkey
`Super+Ctrl+Alt+D` is a Hyprland binding, not part of the panel file.

This project already vendors `Panel.qml` and `BarWidget.qml` unchanged, and
`Model.js` is the tested date math. The live clock in `TrialPanel.qml` is the
`readonly-clock-v1` label with `enabled: false`. That extraction deletes the
Loader, IPC, persistence, and every pointer action. `Ui/Panel.qml` (the IPC
base) is not vendored. Passive `Style` was missing `spacing.hairline` and
`normalBorderFor`, which the grid uses for today's outline.

## Current project gaps

1. No calendar surface is staged, so a click cannot open one.
2. The live clock button is disabled.
3. The clock's bar object cannot host a popup: no `foreground`, `position`,
   popout coordination, or click-target list. Right-side panels use a separate
   owner, so one click cannot switch between them and the clock.
4. English clock strings and two passive border tokens are absent.

## Safety constraints

- Vendor parents stay byte-identical. The generated mirrors are not hand-edited.
- Do not stage `ShellIpc`, `Quickshell.Io`, `omarchy-menu-timezone`, or any
  `sudo timedatectl` invocation.
- Do not write `shell.json`. Week start, label format, and birth year stay in
  the trial process.
- Do not add a Hyprland binding for `Super+Ctrl+Alt+D`.
- The sealed `readonly-clock-v1` label, its offscreen checks, and the empty
  production catalog stay as they are.
- No package install, bar restart, or release. Those need a separate approval.

## Proposed shape

1. `tools/clock_frontend.py` derives `CalendarPanel.qml` from `Panel.qml`.
   The root becomes an `Item` with the local open/close controller that
   `Ui/Panel` would have provided. The original hero, rails, grid, keys, and
   wheel stay. `updateEntryInline` remains the guarded call already in the
   source; the trial bar stores that object in memory only.
2. The same module derives `ClockControlView.qml` from `BarWidget.qml`: keep
   the Loader, left-click toggle, right-click format cycle, and `SystemClock`;
   point the Loader at `CalendarPanel.qml`; drop IPC and the middle-click
   helper.
3. Register both as `clock-calendar-v1` and `clock-calendar-host-v1` in
   `upstream/clock-preview.json`.
4. Add the missing passive tokens and the pinned English `clock.*` labels.
5. Give the trial panel one shared popout bus. The clock and the tray owner
   both use it, so opening one panel closes the other. The clock bar supplies
   `foreground`, `position`, click forwarding, and a session-only settings
   object.

## Explicit exclusions

- System timezone changes (`omarchy-menu-timezone`, `timedatectl`, sudo).
- Shell IPC and the calendar hotkey binding.
- Writing `shell.json` or any config file. Choices do not survive a bar restart,
  and a format change is applied on the screen that was clicked; the shared
  session object updates the other screens.
- The open-panel dot under the clock. The derived bar frame does not draw it.
- Tabbing into a neighboring panel. The trial bar has no `switchPanelFrom`.
- Weather and Elsewhen. They are separate bar widgets.
- Replacing the sealed read-only label used by the offscreen preview.

## Tasks

- [x] Derive the calendar surface and the interactive host with unique witnesses.
- [x] Register provenance, staged hashes, and mirror checks. Leave `readonly-clock-v1` in place.
- [x] Add `hairline`, `normalBorderFor`, and the English clock labels.
- [x] Wire `ClockControlView` into the trial bar with a shared session popout bus.
- [x] Add Python contracts for the mirrors, the forbidden routes, and the sealed label.
- [x] Extend the isolated desktop compile to construct the grid. No host session.
- [x] Update the bar-port status, desktop-panel boundaries, and `WORKLOG.md`.
- [x] Package a release and restart the bar only after a separate approval.
      Installed and started as `20261025-local.14` after that approval.
