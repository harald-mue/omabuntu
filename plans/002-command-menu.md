# Command menu for Super+Space and the system menu for Super+Esc

Status: implemented and applied. The user approved the live gates on
2026-10-25: package and restart the bar, session-only Super+Space and
Super+Escape, and the logout, reboot, shutdown, and hibernate gates.
Applied as release `20261025-local.15`; rollback is `.14`. Hibernate is
included before the resume path is verified; the user will test that later.
Suspend stays without a gate. Live theme, font, and background application
was not approved.
A plan is not approval to edit the desktop, bind keys, install, restart, or commit.

## Goal

Reproduce Omarchy's command menu at commit `03ff1eff3812933f7088484533784d2f63eaf19a`
(v4.5.0-rc1) as an Omabuntu surface:

- Super+Space opens the root menu (Apps, Learn, Style, Setup, About, System).
- The Style section carries the Hyprland configuration things the user asked
  for: theme, background, and font.
- Super+Esc opens the same surface at the `system` route (screensaver, lock,
  suspend, hibernate, logout, reboot, shutdown), which upstream binds with
  `{ menu = "system" }` in `default/hypr/bindings/utilities.lua`.
- Remaining root entries are adapted to Ubuntu where a reviewed backend
  exists; every excluded entry is documented below.

## Evidence compared (pinned upstream commit)

Analyzed from the pinned tree, fetched read-only into ignored
`work/menu-analysis/03ff1eff/`:

- `default/hypr/bindings/utilities.lua`: `SUPER+SPACE` -> `{ menu = "root" }`,
  `SUPER+ESCAPE` -> `{ menu = "system" }`, `XF86PowerOff` -> system menu.
- `bin/omarchy-menu`: thin IPC wrapper; the menu is the first-party
  Quickshell plugin `omarchy.menu` summoned with `{ menu: <route> }`.
- `shell/plugins/menu/Menu.qml` (64 KB) and `MenuModel.js` (28 KB):
  searchable card (~300 px wide, 520 px for font menus), dotted-id tree,
  submenu headers, guards (`when`/`checked`/`disabled`) batched into one
  bash process emitting `<id>:<w|c|d>:<0|1>` lines, providers map
  (`fonts`, `power-profiles`, `languages`) with `label\tvalue\tcurrent`
  rows, search across label/id-segment/aliases/description, Escape
  back-out, checkmarks, dmenu select/input modes.
- `default/omarchy/omarchy-menu.jsonc` (68 KB): entry schema (icon, label,
  title, action, target, provider, aliases, description, guards), root
  order apps/learn/trigger/style/setup/install/remove/update/about/system,
  `system.*` rows, `style.*` rows.
- `docs/menu.md`: schema, merge rules, guard batching, providers, routes.
- `themes/<name>/colors.toml` (23 shipped themes): palette data
  (mode, accent, background/foreground ramp, 8 accents). Backgrounds are
  `.webp` image assets; root MIT is not blanket clearance for images, so
  no background asset is imported.
- System rows run `omarchy-system` helpers or `systemctl suspend` /
  `systemctl hibernate`; hibernate is guarded by availability probes.

Live machine facts (recorded 2026-10-25, not stored):

- Hyprland 0.56.2; 32 binds; Super+Space and Super+Esc are both unbound;
  Super+Alt+Space opens the existing app grid.
- UWSM session active (`wayland-session@hyprland.desktop.target`), so
  upstream logout maps to `uwsm stop`.
- `/sys/power/state` contains `disk`; an 8G swap file exists; the resume
  path is unverified, so hibernate stays guarded and unverified.
- No wallpaper daemon is running (no swww, hyprpaper, or swaybg).
- The installed bar is release `20261025-local.13`, session lifetime.

## Current Omabuntu gaps

- No command menu surface; AppLauncher (Super+Alt+Space) and KeybindingsMenu
  (Super+K) exist as TrialShell surfaces with registered global shortcuts.
- No theme, font, or background backend, no palette state, and the shell's
  Style.qml colors are fixed.
- No power-action surface; `tools/keybindings_menu.py` deliberately refuses
  session-ending commands, which stays true for that surface.
- No route to open a surface at a submenu route; only toggle-style
  GlobalShortcuts exist.

## Safety constraints

- Derive the surface from the pinned `Menu.qml`/`MenuModel.js` with narrow,
  reviewed Ubuntu backend adaptations; record provenance for the imported
  parts in `upstream/` (MIT notice retained). No new hand-authored
  replacement panel.
- No upstream image assets, fonts, locale catalogs, or executable scripts
  are imported or run. Backgrounds come from Ubuntu's own
  `/usr/share/backgrounds` and explicit user directories.
- Dispatch goes through one Python helper with an allowlist built from the
  definitions file; anything absent from the definitions is refused.
- Session-ending actions are explicit gates: rows for reboot, shutdown, and
  logout may run only after the user approves wiring them; suspend,
  hibernate, lock, and screensaver rows additionally wait for the
  authentication-and-recovery gate from the global instructions. Until a
  gate passes, those rows render disabled with a guard, not hidden.
- Config writes (theme, font, background state, live Hyprland keywords) go
  through the backup-and-manifest contract; the user's Hyprland
  configuration file is not rewritten for persistence without a separate
  approval. Live application uses `hyprctl keyword`; persistence across
  Hyprland restarts stays a documented gap until approved.
- Wallpaper daemon choice (hyprpaper, swww, swaybg, or another) needs a
  package/service approval before any activation; the background backend
  first ships list/set state only, tested offscreen.
- Super+Space and Super+Esc are added only as session-only bindings through
  the already reviewed route, after the conflict check and explicit
  approval. No timer may close the surface; session lifetime follows the
  normal bar rule. English UI text only.

## Proposed shape

1. `config/shell/omabuntu-menu.jsonc`: authored definitions in the upstream
   schema, covering the routes: `root` (apps, learn, style, setup, about,
   system), `system` (all seven rows with guards), `style` (theme, background,
   font, plus a Hyprland config-file editor entry), `learn` (keybindings,
   Hyprland manual, Ubuntu documentation). Excluded root sections are absent
   and documented here.
2. A derived surface `config/shell/preview/CommandMenu.qml` plus a ported
   `MenuModel.js` subset: route opening (not just toggle), search, submenu
   headers, guard-driven visibility and checkmarks, one provider hook for
   fonts. Registered shortcuts: `omabuntu:menu` (opens root) and
   `omabuntu:system` (opens the system route). TrialShell mounts it like the
   other surfaces. No dmenu modes, no i18n, no providers beyond fonts.
3. Python helpers (stdlib only):
   - `tools/menu_model.py`: JSONC subset parser (whole-line `//` comments,
   trailing commas), tree build, merge, route resolution, guard batching in
   one helper process with `GUARD_READERS`-style single evaluation,
   provider row emission for fonts (fc-list) and backgrounds.
   - `tools/theme_backend.py`: bundled palette data recorded from the pinned
   `themes/*/colors.toml` values with provenance; `list`/`current`/`set`
   subcommands; `set` backs up and writes state under
   `~/.local/state/omabuntu/current/`, applies live Hyprland color keywords
   through `hyprctl`, and records the shell palette for the next bar start.
   - `tools/font_backend.py`: list via fc-list, set state, apply the shell
   font and the GTK font through gsettings (backup + manifest).
   - `tools/background_backend.py`: list Ubuntu backgrounds and user-picked
   files, set state; daemon activation excluded until approved.
   - `tools/power_actions.py`: logout (`uwsm stop`), reboot
   (`systemctl reboot`), shutdown (`systemctl poweroff`), suspend and
   hibernate guards; each action refuses to run unless its gate flag is
   present in the grant file.
4. Tests: parser and merge contracts, guard batching, allowlisted dispatch,
   theme/font/background backends against fixtures (no live gsettings,
   hyprctl, or systemctl in tests), system-route guard behavior, and an
   offscreen fixture for search, navigation, checkmarks, and route opening.
5. Gated live steps, each with explicit ask-first approval: bar stop/package/
   start for the new surface, session-only Super+Space and Super+Esc binds
   (conflict re-check first), live theme/font/background application, and
   the power-action gates.

## Explicit exclusions

- Install, Remove, and Update root sections (pacman-based upstream); an apt
  adaptation is a separate request and plan.
- Trigger section and its toggles (bar position, dock, animations, gaps,
  corners, transparency, workspace layout, nightlight, screensaver, crash
  capture): none of these backends exist yet; they are not stubbed.
- Setup section beyond a config-file editor entry and the language provider;
  plugins, security, direct boot, reset, DNS, and defaults menus are out.
- Dmenu `select`/`input` modes, multi-select, and the tempfile handshake.
- Upstream `style.unlock` (Plymouth), screensaver branding, and About image
  editing.
- Locale catalogs (`default/i18n/*/menu.json`); English is fixed.
- Upstream theme background images and any other upstream assets.
- Persistence of theme/background/font across a Hyprland restart without an
  approved user-config edit.

## Tasks

- [x] Record the pinned `Menu.qml` layout facts needed for the derived
      surface (card width, row heights, header, search line, escape/back
      behavior, checkmark rendering) in the implementation notes.
- [x] Author `config/shell/omabuntu-menu.jsonc` with the root, system, style,
      and learn routes and guard entries.
- [x] Implement `tools/menu_model.py` with tests: parser, merge, routes,
      guard batching, allowlist build.
- [x] Implement `tools/theme_backend.py` with palette provenance recorded in
      `upstream/` and tests against fixtures; live `hyprctl` application
      behind the reviewed dispatch helper only.
- [x] Implement `tools/font_backend.py` and `tools/background_backend.py`
      with tests; no daemon activation.
- [x] Implement `tools/power_actions.py` with gate flags and refusal tests.
- [x] Derive `CommandMenu.qml` and port the needed `MenuModel.js` logic;
      mount in TrialShell with `omabuntu:menu` and `omabuntu:system`
      shortcuts; no key bound yet.
- [x] Pass the offscreen fixture for search, navigation, route opening,
      guards, checkmarks, and the system route; run the full unittest suite.
- [x] Ask before: packaging and restarting the bar, adding the session-only
      Super+Space and Super+Esc bindings (conflict re-check), and enabling the
      reboot/shutdown/logout/hibernate rows. Hibernate was included at the
      user's request before resume verification.
- [ ] Ask before any live theme, font, or background application.
- [x] Update `docs/` (menu surface, backends, exclusions) and `WORKLOG.md`.
