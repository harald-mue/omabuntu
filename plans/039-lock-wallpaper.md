# Blurred recorded wallpaper on the Hyprlock surface

## Goal and evidence

Make the existing Hyprlock surface follow the Omarchy lock look the user asked for: the current wallpaper, softly blurred, with no clock and no wordmark. Keep Hyprlock 0.9.6 and `config/lock/hyprlock.conf`. Do not import Omarchy's `shell/plugins/lock` plugin. That plugin owns PAM, fingerprint, and the session lock.

Pinned Omarchy `03ff1eff` has no `hyprlock.conf`. Its lock view reads `~/.local/state/omarchy/current/background`, blurs that still, and shows the password field without a clock or a product name. Omabuntu's reviewed config is still a flat `rgb(16, 19, 21)` plus a `$TIME` label and an `Omabuntu` label. The password field stays.

Hyprlock 0.9.6 loads `background:path` through `absolutePath`, which expands `~`. `blur_passes` defaults to 0; the packaged sample uses 3, and the other blur knobs (size, noise, contrast, brightness, vibrancy) then use Hyprlock's own defaults. `color` remains the fallback when the image is missing. `path = screenshot` and `reload_cmd` are not used: the sample screenshot path is tied to command-running configs, and `reload_cmd` would execute a program from the lock config. The reviewed helper rejects `cmd[`, `onclick`, `exec`, `source`, `script`, and `sleep` in active lines, and it rejects a PAM override.

The current still is recorded in `background.json` by `tools/background_backend.py`. Hyprlock cannot parse that JSON. A symlink at `~/.local/state/omabuntu/current/lock-background` is the one static path. `set` and `restore` replace it after the still has already passed the existing directory allowlist. The image is read when Hyprlock starts, so no lock-time reload is required.

## Gap and proposed shape

Point the background block at that tilde path, set `blur_passes = 3`, and keep `color = rgb(16, 19, 21)`. Remove both label blocks. Leave the password field and the package PAM service unchanged. Publish the symlink from `set_background` and `restore_background` only. Do not install the release and do not start Hyprlock.

## Safety and exclusions

No lock activation, authentication attempt, PAM edit, fingerprint, idle timer, screenshot, `reload_cmd`, compositor reload, package install, or session restart. No original Quickshell lock plugin. A regular file already occupying the symlink path is left untouched. Installing the new config into the active release is a separate approval. This edit is not a lock or unlock test.

## Tasks

- [x] Point the reviewed Hyprlock config at the state symlink and remove the clock and wordmark.
- [x] Publish that symlink from background set and restore, without a lock-time command.
- [x] Cover the config and the symlink with unit tests.
- [x] Update the readiness note, capability matrix, and work log.
- [x] Run the unit suite. Do not install the release and do not lock the session.
