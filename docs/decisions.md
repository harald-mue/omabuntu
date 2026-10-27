# Decisions

## Accepted

- Ubuntu 26.04 is the target; Ubuntu remains the managed operating system.
- This repository is intended for eventual public publication.
- Original Omabuntu code and documentation use the MIT License, approved by the user.
- All project files and code are written in English.
- The private reference package is not copied into this repository.
- The original Quickshell desktop is the preferred target where compatible.
- Diagnostics precede deployment; no automatic package or session changes.
- Python standard library is sufficient for the initial diagnostic tooling.
- No automatic fallback to a visually similar but functionally different shell.
- The user approved the development target's simulated dependency transaction and
  pinned workspace-only cpptrace/Quickshell builds, retaining crash handling.
  This approval does not extend to other machines or desktop activation.
- Prefer native Hyprland Lua: the installed binary reports the same upstream
  commit as the reference. Do not upgrade or translate by default.
- Investigate the exact source-reference Quickshell commit against Ubuntu Qt
  before considering any separate Qt stack or replacement shell.
- Original Omarchy source is pinned by matching all 249 captured shell files;
  retain the complete MIT notice and separately review component/asset notices.
- The independent nonvisual loading prototype ships with an empty catalog,
  validates the entire fixture plan before creation, and makes reload revocation
  sticky per host instance. This is not integration into the original shell.
- Import only the unchanged, reviewed pure clock model with its full upstream
  MIT notice and pinned file hashes. Test date/format math in contained Qt;
  stock bar/clock/spacer QML closures remain blocked, not implicitly admitted.
- Separately admit the unchanged spacer/base only to a sealed, non-rendering
  diagnostic profile with authored passive geometry API/Style and narrow module
  maps. Atomic creation/rebind is tested; the production catalog remains empty.
- Admit a derived read-only clock label, not the original calendar/IPC parent,
  to a sealed offscreen bar-frame preview. Keep the prepared Wayland trial entry
  default-deny and separate from host activation.
- Admit the derived clock calendar popup to the live trial bar. Keep shell IPC,
  configuration writes, the privileged timezone picker, and the calendar hotkey
  out. The sealed read-only label stays unchanged.

## Pending

- Attribution and license compliance for any future third-party imports.
- Public hosting provider, repository URL, and initial publication approval.
- Package-source and build approval on any additional target machine.
- Required optional features and application defaults.
- Per-feature Hyprland runtime acceptance and exact Quickshell/Qt requirements.
- Original Quickshell recipe identified by the captured buildinfo hash; keep its
  QtQuick 6.11 patch out of the Qt 6.10.2 build pending full-shell compatibility
  checks. Source pin and root MIT notice are now recorded; complete component and
  asset clearance still precedes further runtime code imports; the individually
  reviewed clock model, sealed spacer/base profile, derived read-only clock
  preview, and derived calendar popup are the current selected-source exceptions.
  The original clock parent and calendar file are vendored for provenance and are
  not runnable unmodified imports.
- Assess remaining upstream/Qt warnings and live service behavior after successful
  isolated linkage/import checks (28 modules, 24 representative types).
- A fail-closed loader must gate services, panels, shared startup objects,
  third-party discovery, command dispatch, reloads and fallback configurations;
  an empty plugins list or a hidden widget is insufficient. The tested fixture
  host demonstrates lifecycle policy only; original startup integration and
  sealed runtime dependency-closure verification are still pending. Static
  references for bar/clock/spacer are reviewed; the catalog remains empty.
- Graphical and complete shell acceptance after the successful pinned workspace
  builds and nonvisual probes; no service or rendering acceptance is implied.
- Corporate lock/authentication policy and approved recovery path.
- Deployment paths, update strategy, and supported version ranges.

The installed third-party package source is evidence only, not a new dependency
or an approval to add it to other machines.
