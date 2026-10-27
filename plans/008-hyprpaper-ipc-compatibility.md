# Set theme backgrounds through the installed hyprpaper IPC

## Goal and evidence

A theme selection records its background but never paints it. The user
installed hyprpaper 0.8.4 from Ubuntu resolute/universe after the earlier
report. Read-only inspection showed:

- hyprpaper was not running, so nothing could answer at all; it is now
  started once with a session-lifetime grant (no autostart, no supervision).
- hyprpaper 0.8.4 exposes only one IPC request,
  `hyprctl hyprpaper wallpaper <mon>,<path>[,<fit_mode>]`; `preload`,
  `unload` and `listactive` answer `error: invalid hyprpaper request`.
  `tools/background_backend.py` used the pre-0.8.4
  preload/wallpaper/unload sequence, so every apply failed silently and
  `background.json` stayed `applied: false`.
- The border record `persisted: false` was correct: `hyprland.lua` already
  held the applied theme's accent, so no write was needed.

## Shape

Try the current per-output `wallpaper <mon>,<path>` request first for every
monitor. Only when that request is rejected fall back to the legacy
preload/wallpaper/unload sequence for older daemons. No new daemon
activation, supervision or autostart is added, and no other request shape is
allowed. The state record keeps `applied` false whenever no step succeeded.

## Exclusions

Autostart/hyprpaper supervision, fit-mode configuration, video wallpapers,
theme asset changes, and any Hyprland reload are excluded. Starting
hyprpaper after a login still needs a separate approval.

## Tasks

- [x] Start hyprpaper once with a session-lifetime grant as approved.
- [x] Add failing contracts for the current request and the legacy fallback.
- [x] Implement the version-aware apply sequence.
- [x] Run the verbose unit suite (426 tests pass) and prove a real apply
      records `applied: true` against the running daemon.
- [x] Package a corrected release, install it and restart only the shell
      after explicit user approval (release 20261025-local.23, shell PID
      676881, startup log clean).
