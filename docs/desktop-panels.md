# Bluetooth, Display, Power and floating-workspace dock

## Source and scope

The experimental `TrialShell` mounts source-derived original Omarchy panels,
not substitute panels and not the original full shell. Source is pinned to
`omacom/omarchy@ac2690cd7be4f47e4a255f5e2e78d904d436b068`
(v4.5.0 stable, MIT).
`upstream/clock-preview.json` records each unchanged vendor parent, hash, blob
identity and staged transform. `tools/desktop_frontends.py` uses unique splice
witnesses and refuses residual helper/IPC dependencies. Generated mirrors must
match the derivation before staging. The production catalog remains empty.

Original Bluetooth/monitor/power button, hero, sections, controls and device rows
are retained. The original `DockWindow.qml` and pure `DockModel.js` retain app
slots, window cycling, drag ordering, running indicators and context menus.
Passive styling tokens supply missing heading/display sizes and dock spacing.
English labels are selected from the same pinned `default/i18n/en/shell.json`.
No original Style, Color, translations service or shell startup is activated.

## Ubuntu boundaries and explicit deviations

- **Bluetooth:** native Quickshell BlueZ adapter/device objects power the radio,
  connect, disconnect, pair and forget. The upstream primitive-only device-row
  projection and grouping are retained. A shared discovery lease prevents one
  trial bar from stopping another bar's scan and never adopts a preexisting
  external scan. Pairing waits for the native paired state before connecting,
  with a bounded 30-second pending indication. An existing BlueZ pairing agent
  may be required for authentication; this trial does not register one. There
  is no rfkill manipulation, service restart, automatic trust or audio routing.
  The original phrase list is retained but not animated. Native action errors
  are not fully surfaced by Quickshell; a pairing timeout is shown explicitly.
- **Brightness:** `tools/display_backend.py` reads the laptop's actual backlight
  and calls logind's system-bus session `auto` `SetBrightness`. No sysfs writes,
  brightnessctl dependency, Arch helper or brightness OSD. Slider release and
  five-percent wheel/keyboard steps submit bounded argv-only requests.
- **Scaling:** only the focused connected output's runtime `hl.monitor` scale is
  changed. Existing monitor-rule fields are preserved. Inputs must be one of
  the displayed presets, produce integral logical pixels and not overlap any
  other active output. Unsafe requests fail with a panel error, not a layout
  rearrangement. No config writes or reload. Output inventory is read-only;
  monitor disabling, topology editing, global font-size changes and text-size
  controls are explicitly excluded. Brightness/scale writes are click-driven;
  panel startup and polling only read status.
- **Power:** native UPower supplies battery percentage, capacity, charge rate
  and estimated time. Quickshell's native `PowerProfiles` interface talks to
  Ubuntu's existing power-profiles-daemon, avoiding a powerprofilesctl subprocess
  entirely. Available profile choices respect performance-profile support.
  Previous profiles are retained in session memory before changing them. Cycles
  and charge-limit readings unavailable through this adapter display a dash.
  Percentage preference persists through the shared Appearance store. No system-stat helper, session menu,
  lock, idle, suspend, shutdown, charge-limit write or management action.
- **Dock:** visibility follows `TrialDesktopState`'s confirmed floating grants
  and saved-mode restoration, not an arbitrary floating window or optimistic
  glyph. Installed desktop entries launch via `DesktopEntry.execute()`; native
  Wayland toplevel handles activate/close windows. Position, autohide, pins and
  pinned order persist in `~/.config/omabuntu/dock.json`. App-grid drag handoff,
  launch pulse, TUI entry claiming and native minimize/restore are implemented;
  see [dock parity](dock-parity.md). The app grid opens from the command menu
  and floating dock, not the top bar. Upstream management helpers and the
  screen-remap component remain excluded. The context menu closes on selection,
  workspace change or an outside click through `HyprlandFocusGrab`. Plan 114
  adds serialized/coalesced edits and visible request errors. That repair was
  locally deployed under plan 117 and is included in published
  [v0.2.4](releases.md#v024-release-scope); native pointer/persistence acceptance
  is still separate.
- **Launch notice:** the app grid and the dock share the one-second "Launching …"
  overlay documented in `docs/launch-feedback.md`. It is not a notification
  daemon and not the dock icon pulse. A source change reaches the running bar
  only through a separately approved restart.
- **Clock:** left click opens the original calendar popup (month grid, ISO
  weeks, year progress, birth-year rail, week-start toggle, keyboard and
  wheel month stepping). Right click cycles the label format. Label format
  already persists through Appearance. Plan 114 adds shared transactional
  calendar fields (week start, birth year, life expectancy and alternate format
  settings), without replacing the host's shared binding. This repair is in
  the local installation following plan 117's backed-up bar-only restart;
  native interactive persistence acceptance remains pending. Middle click does
  not change the system timezone.
  There is no shell IPC and no calendar hotkey. The sealed offscreen label
  stays read-only and is not this popup.

Plan 114 also repairs tray pin/hide persistence in the shared Appearance store,
display request prioritization over polling, original display section navigation
and fixed-registry Tab/Shift+Tab switching within each output's center/right
panel group. See [repair status](widget-preference-repairs.md). The registry
admits only already mounted widgets; it is not arbitrary plugin loading.

## Version checks, backup and recovery

Monitor behavior was checked against the official Hyprland monitor, mode and
positioning documentation and, for version fidelity, the v0.56.2
`src/config/lua/bindings/LuaBindingsConfigRules.cpp` implementation of
`hl.monitor`. It starts with the existing output rule before applying fields.
Logical pixel and overlap restrictions follow the official positioning docs.

Before brightness or scaling mutation the helper stores the previous complete
monitor/backlight readings with mode 0600 in ignored `work/desktop-actions/`.
The saved brightness percent and scale can be selected again from the panel;
no restore operation runs automatically. The saved Hyprland configuration is
never modified. Each helper subprocess has an eight-second timeout and returns
an explicit failure instead of claiming success. No component lifetime timer,
autostart, service activation or package installation is introduced.

## Verification and acceptance

Run:

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_desktop_panels.py --run --build-dir work/builds/<build-id>
```

The isolated QML check uses original visible content with synthetic layer
ownership, BlueZ and UPower. It compiles the dock content, constructs each panel
including the clock calendar, checks mock device action routing, shared discovery
leases, profile selection, the six-week grid, and floating-grant
ownership/revocation. It has no host buses or displays.
A separate native compilation check can establish type availability but is not
visual or functional acceptance. Neither check proves real pairing, logind
permission, rendered scaling, native popup focus or pointer interaction.

Live replacement is gated on the source seals, Python contracts, isolated QML
check and native type compilation. Native interactive acceptance remains a
separate record, not implied by successful startup.
