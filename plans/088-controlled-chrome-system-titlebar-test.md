# Controlled Chrome system-titlebar test

## Goal and evidence

Test the approved ordinary-Chrome system-titlebar candidate from plan 087 on
Hyprland, preserving Edge, GNOME and existing browser work. Compare the observed
backend/window type and original visible setting with Chromium 156.0.8078.79
source and the existing floating-workspace titlebar rules. Omarchy baseline is
v4.5.0 at `ac2690cd7be4f47e4a255f5e2e78d904d436b068`; it does not establish
browser CSD suppression. Source prediction is not native acceptance.

## Gaps and proposed shape

The current Chrome preference has not been inspected and the setting may
already be enabled. Collect only narrow read-only compositor facts without
window titles or URLs. Use Chrome's normal settings UI, with user assistance if
no safe UI control interface is available. Record the original visible toggle
state in a private test record before any change. That record is the backup of
the single affected logical preference; do not copy unrelated profile data.
Only if disabled and the original state is recorded, enable it once through the
UI. Stop if enabled already or absent. Keep rollback through the same UI.

## Safety and exclusions

No direct edit of live Preferences JSON, profile copy, credentials/history or
policy inspection, remote-debugging activation, code injection, synthetic input
into unidentified windows, browser restart, new profile, global setting change,
plugin reload, service activation or Edge modification. No destructive close,
minimize or workspace transition on an existing work window. Later interaction
checks require a coordinated disposable window and original state recording.
GNOME login and PWA acceptance remain separate. No commit or publication.

## Tasks

- [x] Record narrow current session/browser/compositor facts.
- [ ] Inspect and record the original Chrome UI toggle before any change.
- [ ] If disabled, perform one reversible UI toggle; otherwise stop and diagnose.
- [ ] Verify ordinary-window appearance and document rollback/acceptance limits.
- [x] Run full unit tests and diff checks after repository changes.

## Preflight and pending user-assisted inspection

The observed ordinary Chrome client is native Wayland, tiled and not fullscreen.
hyprbars is loaded and configerrors has zero nonempty entries. The diagnostic
`wayland-info` command is absent; no installation was attempted. No desktop UI
control tool is available, so inspection will use the user's visible Chrome
settings UI rather than unsafe live profile edits or remote-debugging changes.
The original toggle remains unobserved and no preference has changed. Ask the
user to open `chrome://settings/appearance` and report the system-titlebar toggle
without changing it first; record that original state before proceeding.

Private preflight evidence and unit log are under ignored
`work/research/chrome-system-titlebar-088/`. All 1079 unit tests and
`git diff --check` pass. Appearance, rollback and GNOME acceptance remain pending.
