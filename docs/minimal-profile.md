# Minimal Hyprland profile

## Status

The independently authored [profile](../config/hypr/minimal.lua) is a staged
evaluation artifact, not an installed desktop or an accepted Omarchy replacement.
The native Hyprland 0.56.2 configuration verifier accepted it on the development
target. No interactive window-management test has been performed.

Do not copy it over a working configuration or add it as a source yet.
The prototype has no locker integration and is not a security-accepted work session.

## Included behavior

- Preferred/automatic monitor fallback, without source desktop output names.
- Hyprland logo/default background disabled by default via
  `misc.disable_hyprland_logo = true`. The Lua option location is verified
  against the [official v0.56.2 example](https://github.com/hyprwm/Hyprland/blob/v0.56.2/example/hyprland.lua).
  This does not start a wallpaper daemon or apply a theme background.
- Dwindle, gaps 2/10, border 2, rounding 8, blur off, shadow on.
- German input, repeat 40/250, Num Lock, and initial touchpad settings.
- 47 generated core bindings:
  - Super+Return: Ghostty.
  - Super+W or Q: close; Super+T: floating; Super+F: fullscreen.
  - Super+J: split; Super+P: pseudo tiling.
  - Super+arrows: focus; Super+Shift+arrows: swap.
  - Super+physical number row: workspaces 1-10.
  - Add Shift to move a window, Shift+Alt to move without following.
  - Super+S: scratchpad; Super+Alt+S: send a window to it.

Bindings are staged, not proven functional. Terminal launch occurs only on
keypress; there is no autostart.

## Deliberate evaluation-only differences

- Global workspaces 1-10 instead of the original per-monitor workspace helper.
- No persistent floating workspace 11.
- No custom Shift+Caps Compose extension.
- No titlebar plugin, shell IPC, launcher, notifications, or theme assets.
- No complete animation, window-rule, grouping, resize, or mouse-binding parity.
- No hardware-specific NVIDIA, gaming, or fixed source-monitor rules.
- No power, suspend, lock, idle, or provisioning commands.

These are explicit prototype limits, not approved final reductions in scope.

## Reproduce the parser check

```sh
python3 tools/omabuntu.py check-profile
```

The tool checks the installed binary's version and exact clean commit first.
It then copies only the bundled profile into a new private work/profile-check/
directory, records its SHA-256, isolates HOME and XDG paths, removes live display/
D-Bus environment access, and invokes Hyprland --verify-config.

Unknown builds, missing binaries, and nonzero/timeout validation do not pass.
Logs and profile snapshots stay private and ignored by Git.
This is environment isolation, not a security sandbox: Lua is executable code.
Only the reviewed bundled profile is supported, not arbitrary configuration input.

A parser pass does not prove keybindings, application launch, display behavior,
authentication, or safety. Applying the profile still requires target backup,
an exact changes/rollback manifest, approval, and interactive tests.
