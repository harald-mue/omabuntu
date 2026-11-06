# Research supported Chrome and Edge decoration isolation

## Goal and evidence

Find a supported, process-local way to remove browser window-control buttons in
Hyprland tiling while retaining Omabuntu titlebars in floating workspaces and
normal GNOME behavior. Limit this request to Chrome and Edge. Compare recorded
browser versions, exact Chromium source, official vendor documentation and the
current Omabuntu titlebar template. Omarchy baseline remains v4.5.0 commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`; plan 086 does not establish upstream
browser-button suppression.

## Current gaps and proposed shape

Browser CSD and hyprbars are independent. Plans 081–084 were rolled back by
plan 085. Global GNOME layout changes are unsafe; GTK_MODULES was explicitly
filtered by the tested Chrome build. Native minimize is not equivalent to the
Omabuntu helper. Trace supported Linux UI/backend and decoration-selection
paths, distinguish source switches from supported public interfaces, and verify
Edge separately rather than assuming Chrome behavior applies. Record negative
results and missing vendor evidence honestly. Save raw public research under
ignored work/ and write a concise repository report.

## Safety and exclusions

Read-only host diagnosis and public-source research; repository plan/report
writes only. No browser launch/restart, profile/history/policy inspection,
gsettings writes, module injection, preload, package installation, desktop
configuration, reload, service activation or deployment. Do not retry the failed
GTK module, restore browser exceptions, switch browser profiles or convert to
XWayland. No reference-package changes, source imports, commit or publication.
A supported candidate still requires separately approved native acceptance.

## Tasks

- [x] Establish recorded/current package versions without launching browsers.
- [x] Review exact Chromium decoration, GTK/backend and command-line paths.
- [x] Check official Edge documentation and delimit unverified vendor behavior.
- [x] Document supported candidates or blockers without deployment.
- [x] Run the full unit suite and diff checks after repository changes.

## Outcome

Package metadata confirms Chrome 156.0.8078.79 and Edge 156.0.4314.58.
Exact Chrome source establishes a supported system-titlebar UI preference and
an explicit custom-frame fallback when the compositor lacks server-side
window decoration support. This is a capability-dependent ordinary-window
candidate, not a process-local preference or a verified Edge/PWA/GNOME fix.
Web apps and picture-in-picture retain custom-frame paths. The official Edge
policy catalog supplies no identified applicable Linux isolation policy; vendor
implementation and native UI remain unverified. No supported process-local
button-layout override for both browsers was established.

Findings and the separately gated minimal test are documented in
`docs/chrome-edge-decoration-research.md`. No browser/profile/desktop changes
were made. Public raw sources, hashes, failed requests and test log remain in
ignored `work/research/browser-decoration-087/`. All 1079 unit tests pass and
`git diff --check` passes. Existing uncommitted research was left intact.
