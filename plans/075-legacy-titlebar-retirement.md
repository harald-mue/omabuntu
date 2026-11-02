# Retire the legacy private titlebar wiring (double buttons)

## Goal

After plan 073's login load worked, floating workspaces showed six titlebar
buttons: two rule sources registered the same three buttons in one config
pass. The private `~/.config/hypr/hyprland.lua` wires
`require("hyprbars")` (the private rules file `~/.config/hypr/hyprbars.lua`,
2026-10-28) and a dead `hyprland.start` handler that calls
`hl.plugin.load` on the hyprpm artifact; since the gate finding, handler-time
loads are queued into a Lua state that `reinitLuaState()` discards before
any pass reads it. The installer-managed carrier now dofies the granted
release titlebars, so the private wiring duplicates them and must be
retired — on this machine and for every public `install.sh` user with the
same legacy wiring.

## Evidence compared

- Live session 2026-11-02 (0.57.0): plugin loaded at login, workspace 3
  floating, both windows showed doubled min/max/close rows.
- `~/.config/hypr/hyprland.lua`: lines with `require("hyprbars")` and the
  `hl.on("hyprland.start", …)` block (body: `local loaded = false`, a
  `hl.get_loaded_plugins` scan for `hyprbars`, and one
  `hl.plugin.load("<manager artifact>")` line). Exact bytes recorded in
  `work/` during implementation.
- `~/.config/hypr/hyprbars.lua` (2603 bytes, 2026-10-28) registers the same
  two named rules plus the same three buttons as the release
  `omabuntu-titlebars.lua` (plan 073 carrier) — it predates the
  once-per-Lua-state guard.
- `docs/hyprbars.md` plan-073 section: the handler-time registration is
  discarded before the compositor's plugin system exists; the handler is
  dead code. The private rules file has no carrier role left.

## Shape

- New `tools/retire_legacy_titlebars.py` (review/apply/rollback):
  - `review()` reports, read-only, whether the entry carries the exact
    legacy require line, the known handler shape (exact lines with a
    pattern for the `plugin.load` path), whether the managed include and
    the granted activation file exist, and the private rules file.
  - `apply()` backs up the entry and rules file (`.bak-<stamp>`), removes
    the require line and the handler block from the entry, and retires
    the rules file by renaming it to `.bak-<stamp>`. It refuses unknown
    shapes, a missing managed include or activation file (removing the
    wiring would leave no titlebar rules at all), and symlinked paths.
    It never reloads Hyprland.
  - `rollback()` restores the newest entry backup and renames the rules
    backup back.
- `tools/session_activation.py`: in the private-profile path, an entry
  with a foreign `require("hyprbars")` line blocks the activation grant
  with a precise instruction, so a curl install cannot create the
  double-button state.
- `tools/published_install.py`: `offer_legacy_titlebars_retirement()`
  after the GNOME-buttons offer: silent when nothing matches, explicit
  confirmation otherwise.
- Makefile targets `legacy-titlebars`, `legacy-titlebars-plan`,
  `legacy-titlebars-rollback`; tests
  `tests/test_retire_legacy_titlebars.py` and an extended
  `tests/test_session_activation.py`; docs update in `docs/hyprbars.md`.
- Live repair on this machine with the new tool, then `hyprctl reload`,
  then user-verified single button row.

## Explicit exclusions

- No change to the release bundle, `plugin_login.py`, the activation
  template or the managed snippet; those are correct.
- No new rules source: after retirement the carrier is the only one.
- No automatic edit of arbitrary private Lua beyond the two exact matched
  blocks; unknown shapes are refused, not guessed.
- Commit/push/release remain separate approvals.

## Tasks

- [x] Implement `tools/retire_legacy_titlebars.py` with backups.
- [x] Add the session-activation blocker and the install.sh offer;
      Makefile targets.
- [x] Tests for all three (1067 total); full suite + clean-source; docs
      update.
- [x] Live repair on this machine, `hyprctl reload`, visual verification.
      Applied 2026-11-02 17:04: entry backup
      `hyprland.lua.bak-20261102T170438.748763Z`, rules retired to
      `hyprbars.lua.bak-20261102T170438.749474Z`; 21 matched lines removed.
      `hyprctl reload` kept the plugin loaded, `configerrors` empty. The
      user confirmed the floating-workspace bar shows a single button row.