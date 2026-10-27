# Disable the wallpaper daemon's independent splash

## Goal

Remove the reported changing text on every workspace without changing window
management, restarting Hyprland or masking the symptom with another panel.

## Evidence compared

- The user confirms the repaired login now works. The login unit also reports a
  successful hand-off in the new session. The remaining displayed text matches
  `hyprctl splash`, but that alone does not identify its renderer.
- Hyprland 0.56.2 reports splash rendering disabled and a transparent splash
  color. The pinned compositor source gates its own rendering correctly.
- hyprpaper 0.8.4 runs a wallpaper layer on every monitor. Its official tag maps
  to commit `20fc0fa6c2056c388a4cd69cb394a9f989dd27c0`:
  - `src/config/ConfigManager.cpp:57` registers `splash` with default 1.
  - `src/ui/UI.cpp:56-60` queries Hyprland's `/splash` and reads independent
    hyprpaper splash settings.
  - `src/ui/UI.cpp:105-116` creates a text child over each wallpaper when that
    setting is enabled. It does not consult Hyprland's disable flag or color.
  - The config manager allows a missing config file, leaving that default on.
- The target user hyprpaper config is absent. The service has no reload action;
  restarting only that daemon and reapplying the recorded wallpaper is the
  narrow live activation path. That needs separate user approval.
- Omarchy source/behavior is not changed or imported; this is the Ubuntu
  wallpaper daemon's setting, not an Omarchy widget-fidelity change.

## Current gaps and shape

The project only disables the compositor splash. Add a small authored
`config/hypr/hyprpaper.conf` with `splash = false`, record it in future local
release bundles, and document the distinction and explicit backed-up deployment.
Do not replace arbitrary existing wallpaper configuration. The current host file
is absent; recheck that immediately before any approved write. If it appears,
review and preserve its other settings instead of copying the template over it.

## Safety and exclusions

No live writes, package changes, service activation/restart, reload or session
transition during source preparation. Never run Omarchy installers. Do not edit
Hyprland binaries, change the splash string, rebuild packages, stop Omabuntu or
alter windows/monitors. Keep host records and screenshots out of Git. Back up each
affected path and record absence/modes and current wallpaper mappings before an
approved deployment. The background may briefly disappear during a separately
approved hyprpaper restart; reapply it through the bytecode-safe packaged helper
only when its recorded image matches the actual mappings. The deployment precheck
found that the recorded preference is older than the active image, so preserve
the exact active per-output mappings using the same reviewed wallpaper IPC
instead of overwriting them with stale state. Leave the record unchanged.
No automatic service restart is added to packaging or installation.

## Tasks

- [x] Identify the renderer using version-pinned official source and live layers.
- [x] Add the authored daemon config, packaging record and regression contracts.
- [x] Correct the previous unresolved-renderer explanation and update worklog.
- [x] Run the complete unit suite (529 tests passed; no live acceptance claimed).
- [x] Obtain explicit approval before writing the host config and restarting only
      hyprpaper, then reapply the saved wallpaper and request visual confirmation.
- [x] Apply the approved config with a recorded/verified prestate, restart only
      hyprpaper and verify restoration without changing shell/window identity.
- [x] Obtain user confirmation that the text has disappeared.

## Approved deployment result

Rechecked the daemon's actual command line and HOME/XDG config root, the absent
config, selected release integrity and existing shell identity. Recorded config
absence and parent mode, service prestate, exact active wallpaper mappings and
application geometry, and verified a private backup of the background record.
The first precheck stopped before any host change because the saved wallpaper
was older than the current live image. The approved restoration therefore uses
the exact active per-output IPC mappings, not the stale preference.

Created only the reviewed minimal config using exclusive creation (no existing
file overwritten), restarted only the already active hyprpaper service and
restored all three original wallpaper mappings. The shell process identity,
application geometry and background record are unchanged; release verification
passes. The service is active and its new process journal contains no errors.
The installed config matches the reviewed template. No shell/compositor restart,
monitor rule change, config reload, package change or session transition.
Private prestate, rollback guidance and logs are in ignored
`work/wallpaper-splash-*/`; removing the new config would restore its recorded
prior absence. The user subsequently confirmed that the text has disappeared;
visual acceptance for this splash removal is complete.
