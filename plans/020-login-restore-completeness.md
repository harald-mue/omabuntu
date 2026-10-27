# Login restore completeness: plugin load, wallpaper, workspace modes

## Goal

Fix the four reported login defects with evidence from the live session, the
Hyprland 0.56.2 sources and Omarchy at commit
`03ff1eff3812933f7088484533784d2f63eaf19a`:
1. hyprbars is not loaded at login.
2. The recorded wallpaper is not applied at login.
3. A random Hyprland splash text is visible on every workspace.
4. A workspace switched to floating falls back to tiling after login.

## Evidence

- Plugin (proven): the `hyprland.start` handler ran at the 22:17 login
  (`ghostty` started at 22:17:04), but `hyprctl plugin list` reports
  `no plugins loaded` and `configerrors` is empty. In 0.56.2,
  `hlPluginLoad` (`src/config/lua/bindings/LuaBindingsConfigRules.cpp`)
  only appends the path to `m_registeredPlugins`; the actual load happens in
  `CConfigManager::handlePluginLoads` → `PluginSystem::updateConfigPlugins`
  during the config apply. A call from an event handler after the load never
  reaches it: the path is registered, nothing loads, and no error appears.
  Omarchy loads its titlebars at config-load time: `default/hypr/workspace-modes.lua`
  `titlebars()` calls `hl.plugin.load(TITLEBARS)` and
  `default/hypr/workspace-layouts.lua` is required during the config load.
  The load at commit triggers `reload()`, and the second pass finds the plugin
  options (`hyprbars.lua`).
- Wallpaper (proven): `hyprpaper.service` started at 22:17:05 and logged
  `Monitor ... has no target: no wp will be created` for eDP-1, DP-5 and DP-7;
  `background.json` was written at 22:19:32, that is a manual re-apply after
  login. Nothing applies the recorded background at login; plan 016 Option 2
  was designed but never implemented or deployed.
- Workspace modes (proven difference from Omarchy): Omabuntu's toggle
  (`tools/workspace_modes.py`) evaluates runtime `hl.workspace_rule`/tag/float
  statements only; the runtime rule is lost at the next login. Omarchy persists
  the mode per workspace id: `omarchy-hyprland-workspace-layout-toggle` writes
  `~/.local/state/omarchy/workspace-layouts/<id>.lua` containing the
  `o.workspace_mode({...})` apply statement, and `default/hypr/workspace-layouts.lua`
  (required during every config load) puts the state directory on `package.path`,
  loads every saved file and then runs `workspace_modes.apply()`.
- Splash (not proven): `hyprctl splash` returns the session's random message
  (`"stop playing league loser" - hyprBot`, `src/helpers/Splashes.hpp:54`).
  `misc:disable_splash_rendering` and `misc.col.splash` are set
  (`bool: true / int: 0`), and the only render consumer of `m_currentSplash`
  is `renderSplash` behind the `PNOSPLASH` gate in `renderBackground`.
  No shell, dock, clock, welcome or donation component references the splash.
  The renderer of the visible text is unidentified; it needs one observation
  or an approved live probe (below).

## Current project gaps

- The deployed `~/.config/hypr/hyprland.lua` carries the ineffective
  `hyprland.start`-handler plugin load (plan 017, superseded by this plan).
- No login-time background application exists anywhere in the manager.
- No workspace-mode persistence exists; the switcher keeps modes in memory.

## Proposed shape

1. Plugin: move the registration to config-load time, Omarchy-style. The
   managed snippet `config/hypr/omabuntu-managed.lua` gains a top-level
   `hl.plugin.load(<home>/.local/lib/omabuntu/hyprbars.so)`; the broken
   handler block in the user's `hyprland.lua` is removed with a backup
   (`hl.exec_cmd("ghostty")` stays as the autostart). The deployer from plan
   018 ships the snippet through `make hypr-settings` / `make dev-update`.
   `tools/deploy_hypr_settings.py` updates are re-tested.
2. Wallpaper: `omabuntu start` (`tools/user_install.py`) applies the recorded
   `background.json` per connected monitor through `background_backend`
   after the shell hand-off, best-effort with logged failures, guarded by
   the existing instance/readiness checks. Plan 016 Option 2.
3. Workspace modes: `tools/workspace_modes.py` writes
   `~/.local/state/omabuntu/workspace-layouts/<id>.lua` with the mode-apply
   statement, and removes the file when cycling back to the default. The
   managed Lua snippet loads every saved file during the config load
   (Omarchy's `workspace-layouts.lua` design) so tiled rules exist before
   the first window opens; the floating claim path of the switcher reads
   the saved mode instead of memory.
4. Splash: after approval, one live probe: set `misc:col.splash` to a bright
   colour and re-apply the monitor rules to force a fresh splash texture.
   If the text colours, the render path ignores the flags in this build; if
   not, the text comes from a window or layer and the observation (position,
   still visible with wallpaper painted?) decides where to look next.
   Settings are restored afterwards.

## Exclusions

- No Hyprland rebuild, package change, plugin rebuild or hyprpm state change.
- No new autostart unit, no Restart=, no supervision.
- No import of Omarchy Lua modules beyond the reviewed design above.
- No logout, compositor restart or login binding in any of this.

## Tasks

- [x] Write the managed-snippet plugin registration and its tests.
- [x] Fix the user's `hyprland.lua` (remove the handler load) with a backup
      (checkout change; the host edit is the approved deploy step).
- [x] Implement the login background application with tests
      (`background_backend.restore_background`, `omabuntu start`).
- [x] Implement workspace-mode persistence and restore with tests
      (switcher eval, `TrialDesktopState` seeding, managed-snippet loader).
- [x] Update plan 012/016/017 docs and the WORKLOG.
- [x] Run `python3 -m unittest discover -s tests -v` (515 tests passed).
- [ ] Ask for approval before each host deployment step (deploy managed
      snippet, remove the handler block, prepare and install a new release
      with the new shell, reload, restart the shell).
- [ ] Verify after a real logout and login: plugin, wallpaper, saved
      layouts, and the splash observation from the open questions.

## Result

The managed snippet now registers the titlebar plugin at config-load time
(guarded by artifact presence) and re-registers saved `scrolling` workspace
rules from `current/workspace-layouts.txt`. The switcher eval persists each
applied mode to that file and removes it when cycling back to dwindle;
`TrialDesktopState` watches the file and seeds floating modes and glyphs at
login. `omabuntu start` applies the recorded background per monitor through
the packaged helper, best-effort. Host deployment is not done; the splash
renderer question from the observation section is still open at this stage.

Subsequent findings: plan 021 deploys and verifies the corrected login and
workspace persistence paths. Plan 022 identifies the remaining text renderer:
hyprpaper 0.8.4 independently draws the same splash and requires its own switch;
the compositor's flags and color cannot disable that overlay.