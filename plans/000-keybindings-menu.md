# Keybindings menu for Super+K

Status: display and dispatch are installed. On 2026-10-25 the user approved a
bar-only stop, install, and start of `20261025-local.13`, then one session-only
Super+K binding. The Hyprland configuration file was not rewritten. The binding
does not survive a Hyprland restart.

## Goal

Open a searchable keybindings surface with Super+K, matching the behavior of
Omarchy at commit `03ff1eff3812933f7088484533784d2f63eaf19a`. Selecting a row
runs that existing binding. It does not create or edit bindings. Lock,
suspend, idle, and other session-ending commands stay on their own keys.

## What Omarchy does

`default/hypr/bindings/utilities.lua` binds Super+K to the command
`omarchy-menu-keybindings`. This is not a bar widget and not
`shell/Ui/KeyboardPanel.qml`. The manual `manual/07-hotkeys.md` documents the
same shortcut. Super+Alt+K and Super+Ctrl+K open separate Tmux and Herdr menus
and are out of scope.

`bin/omarchy-menu-keybindings` builds the list and hands the visible lines to
`omarchy-menu-select` at 800 by 500 pixels. The helper is not vendored here and
must not be executed.

The list is built from the running compositor:

- Read plain `hyprctl binds`. The script avoids `hyprctl -j binds` because
  Hyprland 0.56 emits invalid JSON for that request.
- Lua bindings arrive as dispatcher `__lua`. A `lua -E` scan of the Omarchy
  config recovers the key, dispatcher, and argument. That scan loads the user's
  configuration and is not acceptable to port as-is.
- Resolve `code:` and `mouse:` values through the leading XKB layout
  (`xkbcli compile-keymap`) plus a small fallback. Platform-specific printed
  names come from `/usr/share/omarchy-platform/key-names`.
- Hide the Copilot duplicate `code:201` and Lua rows that have no description.
- Join only these interchangeable actions onto one row: Close window,
  Calculator, Toggle scratchpad, and Move window to scratchpad. The first
  declared chord leads. A combined chord wider than 35 characters stays two
  rows.
- Render monospace rows as a 35-character chord field, ` → `, then the
  description. A row may not exceed 78 characters.
- Order rows with a fixed description-priority table, not alphabetically.
  English ordering happens before translation.
- Translate the description from `default/i18n/<language>/keybindings.json`.
  Unknown descriptions, including user-authored ones, stay unchanged.
- Add two static web-app shortcuts (copy URL, download video). Those belong to
  Omarchy extensions and are excluded here.
- Cache the rendered records under `$XDG_CACHE_HOME/omarchy`.
- On selection, dispatch the stored dispatcher: `exec`, `sendshortcut`, a raw
  `hyprctl dispatch` for Lua, or the generic dispatcher plus argument.

The target Hyprland is 0.56.2. Re-check the binds text format against that
version before implementation; do not trust the JSON form without a fixture
from this machine.

## Current Omabuntu gap

`config/hypr/minimal.lua` is a staged 47-binding prototype. It is not installed
and has no Super+K binding. The running desktop uses session bindings and the
user's Hyprland configuration, so the menu must read the live compositor rather
than that prototype.

The app grid already registers a Quickshell `GlobalShortcut` named
`omabuntu:apps`, backed by a session-only Hyprland binding. No equivalent
keybindings surface exists. The vendored shell subset does not contain
`omarchy-menu-keybindings` or `omarchy-menu-select`.

## Constraints

- Do not modify `vendor/omarchy` or run Omarchy installers, menus, or `lua`
  against the user configuration.
- Do not import the Bash menu until its menu, language, and platform
  dependencies are separately licensed and admitted. Reproduce the reviewed
  record behavior in Python instead.
- Show bindings that Hyprland reports. Do not invent the full 248-binding
  Omarchy catalog, and do not present unbound actions as available.
- Dispatch only a dispatcher and argument present in the bind list just read.
  Lock, suspend, idle, and other session-ending commands stay visible and are
  refused. The menu never creates, changes, or removes a binding.
- Super+K is added only after checking that the running compositor does not
  already own it. Prefer one session-only binding, with backup, and ask before
  applying it. Do not rewrite the user's Hyprland configuration.
- The surface follows the original menu's search, column, and selection
  behavior. It may use the existing shell frame, but it must not be a second
  hand-written summary of the hotkey manual.
- No timer may close the surface. Session lifetime follows the normal bar rule.
- English UI text. Do not import the upstream locale catalogs.

## Proposed shape

1. A pure Python formatter accepts fixture `hyprctl binds` text and returns
   display rows plus hidden dispatcher metadata. It implements chord cleanup,
   the 35-column layout, the four alternative-chord merges, Copilot hiding,
   empty-Lua skipping, and the original priority order for descriptions it
   knows. Unresolved `__lua` rows keep their description and are not given a
   guessed command.
2. A derived shell surface, generated or extracted only after its visual parent
   is identified, lists those rows in a searchable 800 by 500 view. Opening
   refreshes from the helper. Closing does not cache machine-specific bind
   dumps in Git.
3. Wire Super+K through the same reviewed session-binding route used for the
   app grid, after the conflict check and explicit approval.
4. Dispatch reissues the selected existing dispatcher through one helper.
   Reject lock, suspend, idle, and any command not present in the just-read
   bind list.

## Out of scope

- Tmux and Herdr binding menus.
- Static web-app shortcuts and platform key-name files.
- Loading user Lua with the system `lua` binary or `dofile` of the home
  configuration. A restricted Lua 5.4 state may record `hl.bind` only. It
  does not run `hl.exec_cmd`, `os`, or `io`.
- Installing the staged minimal profile or adding its missing Omarchy bindings.
- Autostart, a global config rewrite, or a timer-dismissed popup.

## Tasks

- [x] Record the Hyprland 0.56.2 plain `hyprctl binds` record shape. Records
      start with `bind` and use tabbed `modmask`, `submap`, `key`, `keycode`,
      `catchall`, `description`, `dispatcher`, and `arg`. The machine's bind
      list is not stored here.
- [x] Check whether Super+K is already bound in the running session and record
      only the conflict result. Checked 2026-10-25: it was not bound.
- [x] Add Python tests for column width, alternative chords, Copilot hiding,
      empty Lua rows, priority order, and unresolved `__lua` rows.
- [x] Implement the formatter. Tests use fixture text and do not call
      `hyprctl`. The live helper reads plain binds and recovers unlabeled Lua
      binds in a restricted Lua state. `xkbcli` is optional; the US fallback
      remains.
- [x] The vendored shell has no admissible keybindings menu. The surface uses
      the existing shell colors and the original selector size, 800 by 500.
      See `docs/keybindings-menu.md`.
- [x] Show search, keyboard movement, and the monospace chord column in an
      isolated offscreen fixture.
- [x] Ask before adding the session-only Super+K binding and before restarting
      the bar.
- [x] Verify the live shortcut opens the current compositor's bindings and
      that selection runs only an allowlisted existing action. Super+K opened
      and closed the menu. A command absent from the list was refused, as was
      the configured session-ending command. Focus left and focus right were
      the allowlisted actions used for the live dispatch check. The bind list
      itself is not stored here.
- [x] Specify the dispatch allowlist and test it before a row can run a
      command. The test refuses commands that are not in the list just read,
      plus lock, suspend, idle, and the other session-ending commands.
- [x] Update `docs/` and `WORKLOG.md` with the excluded menus and the
      dispatch limits.
