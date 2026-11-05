# Disable automatic fullscreen HDR switching

## Goal

Persist the user-accepted fullscreen color workaround and make SDR-stable
fullscreen behavior the Omabuntu default in managed and generic profiles.

## Evidence and gaps

- Hyprland 0.57.0, commit `0aa6745f705f2c4b0a5004eb019ef76e5bbdb426`:
  fullscreen screenshots showed white changing from RGB(255,255,255) to
  RGB(241,241,241). Disabling `render:cm_auto_hdr` corrected the visible issue,
  as confirmed by the user. The exact upstream defect is not established.
- Official version-pinned `src/config/values/ConfigValues.cpp` for both
  v0.56.2 and v0.57.0 defines `cm_auto_hdr` with default 1 and disabled value 0.
  The v0.57.0 `src/render/Renderer.cpp` fullscreen handler also refreshes
  client color-management feedback when this option is enabled. Sources:
  `https://github.com/hyprwm/Hyprland/blob/v0.57.0/src/render/Renderer.cpp`,
  `https://github.com/hyprwm/Hyprland/blob/v0.57.0/src/config/values/ConfigValues.cpp`,
  and the corresponding v0.56.2 config-values file. The wiki variables page
  returned HTTP 403; version-specific official source supplied the setting
  definition instead.
- Omabuntu's managed snippet, generic session template and standalone evaluation
  profile currently inherit automatic switching. The accepted live override
  alone does not survive a configuration reload or login.
- This is an Ubuntu integration default, not an Omarchy behavior import.
  The reference remains pinned at `03ff1eff3812933f7088484533784d2f63eaf19a`;
  no reference package or source-derived shell changes are required.

## Shape and safety

Set `render = { cm_auto_hdr = 0 }` in all three authored Hyprland profiles.
Document the automatic-HDR exclusion, rationale and explicit opt-in value.
Add regression assertions, including mocked Lua execution. Back up affected
existing files and record their state privately under ignored `work/` before
editing. Deploy only the reviewed managed-snippet delta through the existing
backup-producing helper; preserve the user's entry configuration.

The user explicitly approved persistence and inclusion in Omabuntu. This does
not authorize a compositor reload, restart, package installation, service
activation, commit or publication. The already accepted live setting stays 0.
No monitor rules, color depth, explicit HDR monitor modes, browser settings,
GNOME settings, authentication or power policy are changed. Automatic HDR
switching is deliberately excluded by default; HDR acceptance is not claimed.

## Tasks

- [x] Record backups and previous state before edits.
- [x] Update managed, generic and evaluation profiles and regression tests.
- [x] Document SDR-stable default, limitations and rollback/opt-in.
- [x] Run `python3 -m unittest discover -s tests -v` (1068 tests, all passed).
- [x] Review and deploy only the managed snippet with backup; verify saved and live values without reload.

## Outcome

The existing deployment helper backed up and updated only the managed snippet;
the entry configuration already contained its single include and was not edited.
The running option remains 0 and the current config-error query is empty. No
reload or login transition was performed, so next-login acceptance remains
unverified. No commit or publication was made.
