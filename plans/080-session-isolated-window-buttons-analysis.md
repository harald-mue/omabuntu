# Analyze session-isolated application window buttons

## Goal and evidence

Explain native browser/GTK window controls in Hyprland tiling and their apparent
duplication alongside hyprbars on floating workspaces, while preserving normal
GNOME window controls. Compare the current read-only button-layout and window
backend probes, titlebar templates, plans 074/075, official toolkit/browser
behavior and Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068` where relevant.

## Current gap and proposed shape

Plan 074 deliberately restored the shared user-level GNOME button-layout after
an earlier global suppression broke GNOME. Hyprbars controls compositor-side
bars, not buttons painted inside application content. Plan 075's duplicate
hyprbars registration is a distinct problem. Identify safe alternatives and
separate verified facts from untested per-application/session mechanisms.
Record an analysis and recommended next verification step, not a desktop fix.

## Safety and exclusions

Read-only desktop probes only; store filtered machine evidence privately under
ignored work/. Do not inspect browser history, cookies, credentials or full
profiles. No gsettings/dconf write, GTK config edit, browser launch/restart,
window-state change, service activation, package install or Hyprland reload.
No user-global setting toggles at login/logout, corporate browser policy edits,
separate persistent browser profile, compositor masking/cropping, or commit.
Any eventual implementation/deployment needs separate approval and backups.

## Tasks

- [x] Establish the current shared setting and affected client backends.
- [x] Compare existing titlebar/GNOME-isolation behavior with official sources.
- [x] Document cause, isolation constraints, options and recommended next test.
- [x] Run the full unit suite after repository documentation changes.

## Outcome

`docs/window-buttons-session-isolation.md` distinguishes application CSD from
hyprbars, the previously repaired global GNOME setting, and the separate duplicate
plugin-registration issue. Official Chromium source matching the installed Chrome
version and GTK3 Wayland source confirm the decoration-layout path. No floating
window or fresh GNOME session was exercised; the visual duplication remains the
user's observation. Edge-specific behavior is not source-verified independently.

The lowest-risk duplicate-row remedy is a Hyprland-only hyprbars exception for
selected CSD applications; that would retain app buttons in tiling. The stronger
button-free tiling goal requires a genuinely process-scoped application mechanism,
which has not yet been established as a deployable fix. Global setting toggles,
shared GTK configuration and blanket GTK_CSD claims are rejected. Native/browser
single-instance/GNOME acceptance gates are explicit. All 1079 tests pass and
`git diff --check` is clean. Only repository documentation and private research
files were written; no desktop settings, processes or services were changed.
