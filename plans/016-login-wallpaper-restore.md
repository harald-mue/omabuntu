# Restore the recorded wallpaper after a login

## Goal

The user's wallpaper must come back after a login without re-selecting the
theme. On 2026-10-26 a login left all three outputs without a wallpaper.

## Evidence

- `hyprpaper.service` is enabled by Ubuntu and running, but
  `~/.config/hypr/hyprpaper.conf` does not exist. The journal shows
  `Monitor eDP-1 has no target: no wp will be created` for eDP-1, DP-5 and
  DP-7.
- `~/.local/state/omabuntu/current/background.json` records
  `applied: true` for the tokyo-night still, and `theme.json` records the
  theme. That state is only written when a theme or background is applied.
- `tools/theme_backend.py` applies the background inside `set_theme`. The
  shipped shell does not apply a background at startup, and the login unit
  only starts the shell. Nothing therefore calls the apply path at login.
- Applying the recorded path manually through
  `hyprctl hyprpaper wallpaper <mon>,<path>` for every monitor succeeded and
  `hyprctl hyprpaper listactive` now lists the still on all outputs.
- `hyprpaper` 0.8.4 is the reviewed version; the legacy
  preload/wallpaper/unload sequence is already handled as a fallback.

## Gaps

- No login-time restore of the recorded background.
- The recorded `theme.json` background path still points at release
  `.22`, so a restore must resolve against the selected release rather than
  trust a stale absolute path.

## Options

1. Write a managed `~/.config/hypr/hyprpaper.conf` with `preload` and
   `wallpaper` lines. Simple, but it duplicates state and must be regenerated
   on every theme change.
2. Add a login step after the shell starts that reads `background.json`,
   resolves the still against the selected release, and applies it through the
   existing reviewed `background_backend` path. Reuses the single owner of the
   background state.
3. Let the shell apply the recorded background itself on startup.

Option 2 keeps one state owner and needs no new daemon or supervision.

## Exclusions

No hyprpaper autostart, no supervision, no video wallpapers, no fit-mode
change, no theme redesign, and no change to Ubuntu's `hyprpaper.service`.

## Tasks

- [x] Reproduce and record the missing target from the hyprpaper journal.
- [x] Re-apply the recorded still manually for the current session.
- [x] Choose an option with the user (Option 2, implemented through plan 020).
- [x] Implement the chosen restore with tests, no start at deploy time:
      `background_backend.restore_background` resolves the recorded still
      against the selected release and applies it per monitor; `omabuntu start`
      calls the packaged helper best-effort.
- [ ] Verify after a real logout and login.
