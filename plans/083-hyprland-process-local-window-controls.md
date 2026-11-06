# Investigate and implement process-local Hyprland window controls

> **Closed by plan 085 rollback:** the unsupported module research was archived,
> never installed or persisted. The browser exclusion was also rolled back.

## Goal and evidence

Replace the variant-1 browser exclusion with the requested behavior: app controls
hidden for supported Hyprland clients, compositor hyprbars on floating workspaces,
and normal GNOME controls unchanged. Baseline: Omarchy v4.5.0 stable commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`, Hyprland 0.57.0 and the installed
Chrome/Edge 156 family. Plans 080–082 identify shared-setting leakage, native
minimize limitations and the incomplete acceptance of variant 1.

## Proposed shape and current gaps

Investigate an officially supported process-local toolkit setting override,
including GTK3 module initialization if necessary; Python alone cannot set a
property in another application's GtkSettings object. First verify installed
browser toolkit usage without profile/history inspection and official module/API
support. Any native shim must be small, authored, compiled without new packages,
reviewed and tested in a contained process before installation. No preload
interposition or shared settings backend/profile substitution.

Only deploy a mechanism with demonstrated process-local behavior and a strict
Hyprland-session guard. Preserve other toolkit settings and client state. Restore
the original hyprbars show matcher with ownership checks and backups only when
supported client controls can actually be hidden. Integrate future source builds
and document unsupported clients/toolkits. Existing running browser processes
cannot be assumed to inherit a new startup setting.

## Safety and exclusions

No global GNOME/GTK/dconf writes, browser policy/profile edits, alternate user
profiles, LD_PRELOAD, service-manager environment changes, security/sandbox
weakening, package installation, plugin reload, compositor restart, logout,
commit or publication. Diagnose before each change. Back up every deployment
path and receipt; retain rollback. Do not terminate/restart real browser sessions
or inject code into existing processes without separate approval. User approval
of the desired feature does not prove toolkit or native acceptance.

## Tasks

- [x] Verify installed toolkit usage and official process-local extension behavior.
- [x] Implement and test a narrowly bounded mechanism if viable; otherwise report the blocker without changing the desktop.
- [x] Validate GNOME/no-session refusal, settings preservation and runtime dependencies.
- [x] Deploy only verified scope with backups and restore the corresponding hyprbars behavior, or document why deployment is blocked.
- [x] Run unit/source checks and document runtime/restart and acceptance limits.

## Subsequent real-browser result

Plan 084's separately approved Chrome restart did not load the module. Exact
Chromium 156.0.8078.79 initialization source explicitly unsets GTK_MODULES and
filters GTK module settings. The generic GTK-only proof below is not Chrome
compatibility. This candidate is rejected for browser deployment; do not install
it or bypass the browser's filtering. No persistent startup integration or
hyprbars restoration was performed. See docs/process-local-window-controls.md.

## Original candidate outcome and deployment blocker

The observed Chrome/Edge processes load GTK3. The authored MIT module in
`native/gtk3_window_controls.c` uses GTK3's documented module-init interface and
sets only the current process's GtkSettings decoration layout. An explicit
workspace-only builder compiled it against existing libraries/GLib headers,
without installing development packages or changing browser security policy.

Pure GObject execution tests cover the real module code without GTK/display/
settings-service access. Separate no-window GTK3 probes on the existing display
confirmed the local override and notification guard. GNOME/mixed-desktop
identifier probes retained the baseline layout; theme/font/icon property hashes
were unchanged. This is not a fresh GNOME login or browser rendering acceptance.
The full suite passes 1086 tests and clean-source verification passes.

Deployment is deliberately blocked on controlled full browser exit/relaunch and
real browser acceptance. Existing single-instance processes cannot inherit a new
startup module; no code will be injected into them and no unsaved browser work
will be terminated without separate coordination. No module installation,
startup integration, browser restart or hyprbars restoration was performed.
Variant 1 remains active. `docs/process-local-window-controls.md` records the
candidate, GTK4/Qt/confinement exclusions and the exact remaining deployment
sequence. Private source/probe/build evidence remains under ignored work/.
The live shared GNOME layout and owned shell process are unchanged; no commit
or publication occurred. The controlled browser launch and persistent integration
remain pending follow-up tasks, not completed native acceptance.
