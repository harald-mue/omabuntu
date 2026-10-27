# Installer-managed Hyprland settings (splash and ecosystem text)

## Goal

Remove Hyprland's startup text ("Thanks raf!" and the other random splash
messages) permanently and for every install, through a setting the installer
owns, without hand-editing the user's Hyprland configuration on every change.

## Evidence compared

- The strings live in Hyprland itself
  (`src/helpers/Splashes.hpp` in the v0.56.2 source), not in Omabuntu, the
  shell or the theme assets. `hyprctl splash` prints the current random
  message, which is why it is not evidence that the text is rendered.
- The message is drawn by `IHyprRenderer::renderBackground` and gated by
  `misc:disable_splash_rendering`. The flag is already `true` in
  `~/.config/hypr/hyprland.lua` and `hyprctl getoption` confirms
  `bool: true, set: true`, yet the user reports the text on all three
  monitors. A transparent `misc:col.splash` (`0x00000000`) was therefore tried
  as a workaround. Plan 022 later establishes that the visible renderer is
  hyprpaper's independent overlay; neither this color nor the compositor flag
  can control that separate renderer.
- The same render pass draws the random Hyprland logo wallpaper, gated by
  `misc:disable_hyprland_logo` (already `true`).
- `hyprpaper.service` logged `Monitor ... has no target: no wp will be created`
  for eDP-1, DP-5 and DP-7 at login. While no wallpaper is painted, the
  compositor background - including the splash text - stays visible. Plan 016
  (login wallpaper restore) addresses that half of the cause.
- `ecosystem:no_donation_nag` exists in 0.56.2 and defaults to `false`.
- The installer (`tools/user_install.py`, shipped as `manager.py`) only manages
  releases, `current`, the process record and the autostart unit. It never
  writes `~/.config/hypr/*`, which is why a "installer setting" for this does
  not exist yet.

## Current project gaps

- No managed Hyprland configuration file and no include mechanism in the
  user's `hyprland.lua`.
- Prompting the installer to rewrite arbitrary user configuration would be
  unsafe. Only an additive, verified include line is acceptable.
- No test proves that repeated installs keep a single include line.

## Proposed shape

1. Ship `config/hypr/omabuntu-managed.lua` in the release with the reviewed
   `misc` and `ecosystem` settings:
   - `disable_splash_rendering = true`
   - `disable_hyprland_logo = true`
   - `col.splash = 0x00000000`
   - `ecosystem.no_donation_nag = true`
   The file contains nothing else: no binds, no autostart, no monitors.
2. Add `tools/deploy_hypr_settings.py` with `plan`, `apply` and `remove`, in
   the same style as `tools/deploy_autostart.py`:
   - deploy the managed file to `~/.config/hypr/omabuntu-managed.lua`;
   - ensure exactly one `require("omabuntu-managed")` line in
     `~/.config/hypr/hyprland.lua`;
   - back up `hyprland.lua` before any change and record the previous state;
   - refuse when the config is missing, a symlink, or already contains a
     different variant of the include;
   - `remove` deletes the include only when it is the exact managed line, and
     removes the managed file.
3. Wire the deploy step into the installer entry point as an explicit,
   separate step. `tools/user_install.py` is shipped as `manager.py` inside the
   sealed release and must stay independent of the checkout, so the reviewed
   entry point is the Makefile: `make hypr-settings` prints the plan and then
   applies it. `start`, `stop`, `install` and `update` never touch the
   configuration.
4. Add Makefile targets `hypr-settings` and `hypr-settings-remove`.

## Exclusions

- Do not manage, replace or reformat the user's whole `hyprland.lua`.
- Do not add further options, binds, monitors, autostart or plugin loading to
  the managed file.
- No `hyprctl reload` from the installer and no service or session change.
- No Hyprland rebuild, no package change, no removal of the splash strings.

## Tasks

- [x] Add `config/hypr/omabuntu-managed.lua`.
- [x] Add `tools/deploy_hypr_settings.py` with `plan`/`apply`/`remove`.
- [x] Add tests for idempotent include insertion, backup, refusal cases and
      removal (`tests/test_hypr_settings.py`).
- [x] Wire the opt-in step as the `make hypr-settings` target and document the
      plan/backup/rollback gate.
- [x] Add the `hypr-settings` Makefile target and documentation.
- [x] Run the full unit suite.
- [ ] Ask for approval before applying to this host.
