# Sealed read-only clock and bar preview

## Result and limits

The initial sealed preview described below is historical. The current live
trial has 26px bars, workspace clicks, an app grid and the original tray.
See [current bar port and remaining work](bar-port.md). The sealed clock
checks still do not construct the native tray or connect to a host session.

## Live calendar

The sealed checks below still use the read-only label. The live trial bar does
not. Left click opens `CalendarPanel.qml`, derived from the pinned
`shell/plugins/panels/clock/Panel.qml` (MIT). The month grid, ISO weeks, year
progress, birth-year rail, week-start toggle, and month stepping are that
surface. Week start, label format, and birth year stay in session memory.
Nothing writes `shell.json`. Middle click does not open the timezone picker,
because that picker changes the system timezone with privilege. There is no
shell IPC and no calendar hotkey. See [desktop panels](desktop-panels.md).

A derived, read-only clock label and the unchanged original spacer now form one
authored 32-pixel bar frame. Five contained checks pass, including one private
software offscreen image. This is not a host Wayland session, not the original
Omarchy bar, and not the complete original clock.

The production guard and its empty catalog are unchanged. The sealed checker
never supplies the trial grant or a real display socket. A later, separately
approved Hyprland run used the same entry once. It showed one 32-pixel bar on
the 3440-pixel-wide output and then stopped itself. That run did not place a
bar on the other connected outputs, because the panel had no screen assignment.

Final evidence: `work/clock-preview/20261024T110510.803898Z/report.json`.

The render case produced a 960 by 32 PNG with 347 pixels that differ from the
flat background, confined to the clock region. That shows text was painted by
Qt's software renderer. It is not color, font, spacing, or multi-monitor parity.

## What is original, derived, and authored

Pinned public commit `03ff1eff3812933f7088484533784d2f63eaf19a`. Per-file hashes
and the exact staged extraction are in [clock-preview.json](../upstream/clock-preview.json).
The complete MIT notice remains [vendor/omarchy/LICENSE](../vendor/omarchy/LICENSE).

Unchanged and staged:

- `shell/Ui/BarWidget.qml`
- `shell/Ui/WidgetButton.qml`
- `shell/Ui/OpticalGlyph.qml`
- `shell/plugins/bar/widgets/Spacer.qml`
- `shell/plugins/panels/clock/Model.js`

The original `shell/plugins/panels/clock/BarWidget.qml` is kept unchanged for
provenance and is **not** staged as a runnable component. A fixed extraction,
`readonly-clock-v1`, removes the calendar Loader, calendar forwarding, IPC,
refresh/persistence, and pointer actions before any component is prepared. It
keeps the original `formatted` and ISO-week logic, `SystemClock`, and the
original button/glyph presentation. The button is not interactive.

Authored inputs now include passive Style, Color and I18n singletons, the
trial frame/policy/entry, LiveStatus, AppLauncher and PortTrayHost. The live
application launcher has an explicit DesktopEntry execution route; the original
tray has application-owned DBus menu actions. Neither is a read-only boundary.
The sealed clock cases do not construct those live paths.

The module maps additionally export the reviewed original tray UI dependencies
and original Border singleton/geometry. Original Style/Color/I18n, watched theme
files, helper commands and full-shell startup remain excluded. Exact current
maps and hashes are enforced by upstream/clock-preview.json.

## Trial policy

[TrialPolicy.js](../config/shell/preview/TrialPolicy.js) accepts only:

```json
{"schema_version":1,"scope":"clock-bar-trial-v1","duration_seconds":60}
```

For explicitly timed diagnostics, duration must be an integer from 5 through
3600. Normal approved desktop runs instead use the separate exact grant
`{"schema_version":1,"scope":"bar-session-v1","lifetime":"session"}`.
That mode never starts the expiry timer. Mixed, ambiguous or unknown lifetime
fields and legacy plugin configuration are rejected. See
[session lifecycle](bar-session.md). The shell stops before preparing
its fixed panel URL when the grant is missing or changes after startup. It also
requires QT_QPA_PLATFORM=wayland before that preparation. The panel follows
the pinned Quickshell Variants API: model Quickshell.screens creates one
PanelWindow per connected screen, with screen set to modelData. Each window is
uses keyboard focus OnDemand so pointer clicks work. Its exclusion mode is
Auto, so Hyprland reserves the bar height and tiled windows start below it.
The application overlay keeps an exclusive zone of zero. Those properties are not a lock-screen
or input-isolation guarantee. Screen assignment is not proof that every output
has rendered the bar.

## Checks

```sh
python3 tools/check_clock_preview.py
# Plan only.

python3 tools/check_clock_preview.py --run --build-dir work/builds/<timestamp>
```

The runner accepts no external QML, catalog, or reference path. It verifies the
closed file set, hashes, Git blobs, extraction, and both complete notices before
any process, then reuses the established Bubblewrap runtime: read-only probe and
stage, private namespaces, no host session, real buses, GPU, display, compositor,
or network. There is no less-isolated fallback.

Ordinary cases require exit 0, `Configuration Loaded`, one success marker, and
zero warnings or errors. They also require that `OMABUNTU_TRIAL_STARTED` does
not appear. The denied-entry case must stop on a missing grant. The assertion
control must exit 42 with its specific error and no success marker.

The content case checks English weekday/time shape, spacer width 12, a disabled
clock, and the original formatter against fixed dates, including an ISO week.
The render case grabs the private offscreen window; the checker reconstructs the
PNG and rejects a blank image, unexpected size, or paint outside the clock region.

## Visible session boundary

The first visible run was one explicit process in the already running uwsm
Hyprland session. It did not edit Hyprland configuration, autostart, login, or
services. Recovery was the process timer, with timeout as the external stop for
that exact process. Super+Shift+Escape still stops the whole Hyprland session
through the existing configuration. Lock, idle, and suspend stay out of this
milestone. The follow-up, work/clock-trial/20261024T114251.682735Z, created
three omabuntu-clock-trial layers from one process: 1280 pixels on eDP-1, 3440
on DP-7, and 1920 on DP-9. Hyprland's current layout places DP-7 at x=1280, so
it overlaps eDP-1 and the laptop layer is narrower than that panel. This is
compositor layer evidence, not theme, font, or original-bar acceptance.
The next visible slice adds an authored workspace strip for the existing global
workspaces 1 through 10 and the active window title. It is not the original
per-monitor workspace widget and does not run helpers or close windows.
Keyboard focus None also kept pointer clicks off that strip. The follow-up uses
WlrKeyboardFocus.OnDemand so a workspace number can send the workspace
dispatcher. A click now sends `hl.dsp.focus({ workspace = N })`,
the same call as Super+number, and keeps `workspace N` only when Hyprland is
not using Lua. The application list is a separate overlay, namespace
omabuntu-apps. It lists installed Application desktop entries and starts the
selected entry through DesktopEntry.execute(). Super+Alt+Space is registered as
the Hyprland global shortcut omabuntu:apps. The shortcut binding is added to
the running session only; the Hyprland configuration file stays unchanged. The strip uses the
installed JetBrainsMono Nerd Font, Omarchy's default foreground #cacccc on
#101315, slot 10 labeled 0, and a faint selected fill instead of the layout
glyph. The glyph depends on the unrun layout helper.
