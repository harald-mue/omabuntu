# Manual screen-lock shortcut

## Goal

Bind one manual screen-lock chord in the live Hyprland session. The chord
runs the already accepted `omabuntu lock --apply` helper and nothing else.

## Evidence compared

- Hyprland 0.56.2 (commit `efb509937800`) is the running compositor. Live
  binds use `hl.bind` and `hl.dsp.exec_cmd` in `~/.config/hypr/hyprland.lua`.
  That is the version's Lua bind API already in use on this machine. The
  legacy `bind =` config syntax is not used here.
- A read of the live binds found 43 bindings. No chord uses the L key, and
  no description or argument mentions a lock. `SUPER+CTRL` is already used
  for the calculator (`SUPER+CTRL+Q`, modmask 68) and does not collide with L.
- Upstream Omarchy at the pinned commit treats `SUPER+CTRL+L` as the lock
  chord. Plan 006 left that chord out on purpose.
- The supervised lock on 2026-10-25 accepted explicit `lock --apply`,
  unlock, all three outputs, and a clean locker exit. See
  `docs/lock-readiness.md`. The helper refuses a second Hyprlock, a
  non-Hyprland session, and any config other than the reviewed static file.
- `tools/keybindings_menu.py` lists session-ending rows and refuses to launch
  them, including any argument whose token is `lock`. Logout already works
  that way: the key runs it, the menu does not.
- `config/hypr/omabuntu-managed.lua` is installer-owned and must not gain
  binds (plan 018). The staged `config/hypr/minimal.lua` profile is not the
  installed configuration.

## Current project gaps

- The accepted lock has no key. The user has to run the manager by hand.
- Gate 3 in `docs/lock-readiness.md` still says the shortcut is future work.

## Safety constraints

- The user approved this chord (`ja` to binding `SUPER+CTRL+L`).
- Back up `~/.config/hypr/hyprland.lua` before editing it. Do not rewrite
  the rest of the file.
- The command is the installed manager with `lock --apply`. Do not call
  `hyprlock` directly, `loginctl`, or a shell snippet.
- No idle timer, lid switch, DPMS, suspend, autostart, or PAM change.
- Do not press the chord from the agent. Binding is not a new lock test.
- The keybindings menu keeps refusing the row. The key itself is the only
  launcher.

## Proposed shape

Add one bind next to the existing logout bind. The command is a string
literal: the absolute path of the installed launcher plus `lock --apply`.
Do not call `os.getenv` in that expression. The keybindings menu loads this
file in a restricted Lua state with no `os` library, and a missing global
stops the scan, so every later bind would disappear from Super+K.

`Lock system` is the label the keybindings menu already ranks. Reload the
compositor config after the edit and check that the bind exists once and
that `hyprctl` reports no new config error. Update the lock-readiness note,
the capability matrix, and this plan's tasks. Add a unit assertion that the
menu still refuses that command string.

## Exclusions

- Wrong-password, hotplug, DPMS, fingerprint, and corporate PAM sign-off.
- Idle, screen-off, lid, and suspend.
- Launching the lock from the Super+K menu.
- Putting the bind in the installer-managed Lua file or in `minimal.lua`.
- A new lock/unlock acceptance claim from this change alone.

## Tasks

- [x] Back up `~/.config/hypr/hyprland.lua` under ignored `work/`.
- [x] Add the single `SUPER+CTRL+L` bind.
- [x] Reload and confirm one matching bind and no new config error.
- [x] Keep the keybindings menu from launching the lock command.
- [x] Update lock readiness, the capability matrix, and `WORKLOG.md`.
- [x] Run the unit suite.
