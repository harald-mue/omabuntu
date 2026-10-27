# Load the titlebar plugin at session start

## Goal

Floating workspaces must show the reviewed hyprbars titlebar after a login,
not only when the plugin is loaded by hand.

## Evidence

- `hyprctl plugin list` prints `no plugins loaded` in the running session.
- `hyprpm list` reports `hyprbars` `enabled: true`; the other three plugins
  are disabled. Enabling is manager bookkeeping, not a compositor load.
- `~/.config/hypr/hyprland.lua` line 102 does `require("hyprbars")`. The
  reviewed `~/.config/hypr/hyprbars.lua` returns early when
  `hl.plugin.hyprbars` is absent, so the configuration is inert without the
  plugin.
- The reviewed build artifact exists at
  `~/.local/lib/omabuntu/hyprbars.so`, SHA-256
  `02296a7bdb612345a618402f89af39e3b829b522dcce697d48486c83d5d190db`,
  matching the pinned reference in [hyprbars](../docs/hyprbars.md).
- `hyprctl configerrors` is empty; this is a missing load, not a parse error.
- `docs/hyprbars.md` already states: "No automatic plugin load is configured."
  Plans 012/013 removed all `exec-once` for omabuntu and never added a plugin
  load, so the login leaves the compositor without hyprbars.

## Gaps

- No session-start load of the reviewed artifact.
- hyprpm's enabled state is not reconciled with the running compositor.

## Shape

Two separately approved steps:

1. Runtime: `hyprctl plugin load ~/.local/lib/omabuntu/hyprbars.so` in the
   current session, then verify `hyprctl plugin list`,
   `hyprctl getoption plugin:hyprbars:enabled` and the titlebar on a
   disposable floating window.
2. Persistence: the Lua configuration has no `exec-once` primitive; it uses
   the `hyprland.start` handler. That handler now loads the same pinned
   artifact through `hl.plugin.load` when
   `hl.get_loaded_plugins()` does not list hyprbars. `~/.config/hypr/hyprland.lua`
   was backed up to `hyprland.lua.bak-20261026T203605.579829Z` before the edit.

Loading a plugin calls `HyprlandAPI::reloadConfig()`. That re-reads the
configuration and can drop runtime-only tags, rules and bindings, so the
runtime step is not reload-free and must be done with the session in a known
state.

## Exclusions

No `hyprpm update`, no rebuild, no new plugin, no `hyprpm enable` of another
plugin, no second titlebar implementation and no automatic start of the shell.

## Tasks

- [x] Record the missing-load diagnosis and the artifact hash.
- [x] Ask for approval of the runtime load.
- [x] Load the pinned artifact: `hyprctl plugin list` lists hyprbars, the
      enabled and bar_height options are set, and `hyprctl configerrors` is empty.
- [x] Ask for approval of the persistent load.
- [x] Back up `hyprland.lua` and add the guarded load to the
      `hyprland.start` handler; `hyprctl reload` kept the plugin loaded and
      reported no configuration errors.
- [x] Superseded by plan 020: `hl.plugin.load` only queues a path outside a
      config apply, so the registration moved to the managed snippet, which
      runs at config-load time, and the handler block is removed at deploy.
- [ ] Verify the automatic load after a real logout and login.
- [ ] Native acceptance of close, minimise and maximise on disposable
      floating windows.
