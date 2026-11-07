# Command menu (Super+Space) and system menu (Super+Esc)

Omarchy at commit `03ff1eff3812933f7088484533784d2f63eaf19a` opens the first-party
`omarchy.menu` Quickshell plugin with Super+Space (`{ menu = "root" }`) and
Super+Esc (`{ menu = "system" }`). This is the reviewed Omabuntu reproduction:
`config/shell/preview/CommandMenu.qml` with the pure logic ported in
`config/shell/preview/MenuModel.js`, driven by definitions in
`config/shell/omabuntu-menu.jsonc`. No upstream menu script is imported or
executed.

## Surface

The card keeps the pinned layout: 300 px wide (520 px for the font menu),
centered, 8 px radius, 18 px padding, 34 px header, 50 px rows, 3 px row
spacing. Search is a plain line, the menu title plus an ellipsis at 58%
until the user types. Colors come from the active recorded palette
(background, foreground, accent): the scrim is the background at half
strength, the selected row is the foreground at 8%, and its text and icon
use the accent. JetBrainsMono Nerd Font draws the glyphs at 18 px. Escape
clears the search, then closes; Backspace or Left at an empty filter goes
back one submenu; Up/Down/PageUp/PageDown move; Return or Right activates.
Rows show the pinned Nerd Font glyph, the label, a detail line with the
parent path while searching, and `\u203a` for submenus. A search split between the current
submenu and deeper rows draws the drilldown divider. Nothing closes the card
on a timer.

The surface registers the Quickshell shortcuts `omabuntu:menu` (root route) and
`omabuntu:system` (system route). The approved session binds are Super+Space
and Super+Escape, added with `hyprctl eval` and not written into
`~/.config/hypr/hyprland.lua`. They disappear when Hyprland restarts.
Super+Alt+Space and Super+Shift+Escape were already bound and were left alone.

## Rows and guards

`tools/menu_model.py` parses the JSONC definitions (whole-line `//` comments
only, upstream rule), merges the user overlay
`$XDG_CONFIG_HOME/omabuntu/menu.jsonc` by key, and injects the root row. Kind
is inferred (action/link/menu), and a dotted id defines the tree. `when:`,
`checked:` and `disabled:` are bash conditions batched into one guard script
whose subshells run side by side and report `<id>:<w|c|d>:<0|1>` lines. The
three current-theme/font/background readers start once and share their answer
across sibling rows. `when:` hides a row (and an emptied submenu with it),
`disabled:` dims it and makes it unselectable, `checked:` adds the marker.

Root rows: Apps (opens the app grid), Learn, Trigger, Style, Setup, System. Learn lists the
keybindings menu, the Hyprland wiki and Ubuntu's desktop documentation. Style
holds the Hyprland configuration things: Theme and Background open the image
picker (see [image picker](image-picker.md)), Font stays a provider submenu.
Setup holds Defaults with provider submenus for the default browser and default
terminal. Only installed `.desktop` entries appear; the browser choice uses
`xdg-settings set default-web-browser`, and the terminal choice writes the
Hyprland `xdg-terminals` preference list for `xdg-terminal-exec`. Nothing is
installed from the menu. System (Super+Esc route, upstream order minus the excluded rows):
Suspend and Hibernate (guarded by `/sys/power/state`), Logout, Reboot,
Shutdown. Source now also includes Lock before Suspend, through the existing
installed manager (`omabuntu lock --apply`). Trigger > Capture > Screenshot
uses the existing Omasnap wrapper from plan 031. These menu additions were deployed after approval. Both actions launch detached with no session lifetime limit;
starting a process is not a lock/unlock or screenshot acceptance verdict.
The screensaver remains excluded.

## Providers

- Themes: the 23 upstream palettes recorded as data in `config/menu/themes.json`
  plus the imported preview images under `config/menu/themes-previews/`
  (provenance in `upstream/theme-backgrounds.json`). The current theme gets
  the check glyph. Selecting one records the choice under the state home with
  a backup, applies the border colors live through `hyprctl keyword
  general:col.active_border` and `col.inactive_border`, persists the same two
  color literals in the user's `hyprland.lua` (backup first, shape checked),
  and records and applies that theme's background through the reviewed
  background path.
- Backgrounds: the current theme's imported upstream stills first, then
  Ubuntu's `/usr/share/backgrounds` plus `~/Pictures`; selecting one records
  the choice and backup, and when a hyprpaper daemon is already running it
  sets the still per monitor through the current request
  `hyprctl hyprpaper wallpaper <mon>,<path>` (hyprpaper 0.8.4), falling back
  to the pre-0.8.4 preload/unload sequence only when that request is
  rejected. Installing or autostarting the daemon is a separate
  package/service approval and stays out (the installed package is recorded
  in [dependencies](dependencies.md)).
- Fonts: `fc-list` families, each row rendered in its own family (a reviewed
  Omabuntu deviation; upstream renders every row in the menu font). Selecting
  one records the choice, sets the GTK font through gsettings, writes the
  fontconfig `monospace` prepend in `~/.config/fontconfig/fonts.conf`, and
  rewrites `font-family` in an existing ghostty config with a SIGUSR2 reload
  (both backed up first). The bar reads the family from the watched state
  file, so later changes restyle the bar text without a restart.
- Default browsers and terminals: discovered from installed `.desktop` files
  through `tools/defaults_backend.py`. Duplicate vendor ids collapse to one
  row. The current browser or terminal gets the check glyph.

Row ids are `<menuId>.<slug>` with `-` appended on collision, exactly the
upstream merge rule. Provider rows are re-derived by id inside the helper on
dispatch; the surface never sends a value to run.

## Dispatch and gates

Selection goes to `tools/menu_model.py run <rowId>`. An id absent from the
definitions or no longer enumerated by its provider is refused. Static actions
match a fixed registry only: `omabuntu-open:apps|keybindings` (surface-internal,
refused inside the helper), `xdg-open:https://...`, `systemctl:<verb>` and
`uwsm:stop`, and exact `omabuntu-session:lock|screenshot` tokens. The last two
launch only the installed manager or packaged screenshot wrapper, never an
arbitrary shell command. Appearance bar/dock actions additionally match the
closed `omabuntu-appearance:<key>:<choice>` registry and write only owned
preferences with prestate receipts; see [Appearance controls](appearance-controls.md)
for scope, recovery and the separate deployment gate. Anything else is refused.

Every session-ending action goes through `tools/power_actions.py`.
Logout/reboot/shutdown (including the `poweroff` alias) need no extra application
consent flag. This also repairs older installations when the packaged helper is
updated: old missing/false ordinary-action flags are ignored, not rewritten.
Ubuntu authorization and inhibitors remain unchanged; no polkit or sudo grant
is installed. A click still explicitly requests the action; installation/update
never executes it.

Logout validates the current Hyprland/Wayland sockets, unique instance and owned
compositor PID. When that compositor belongs to a UWSM `wayland-wm@` service,
it checks MainPID and stops only that exact service, preserving UWSM's ordered
shutdown. Otherwise it uses the supported `hl.dsp.exit()` dispatcher for that
current instance. GNOME, TTY, stale/ambiguous instances and service identity drift
are refused; no wildcard service stop, broad user termination or forced window
closing. Missing commands, timeouts and command refusals have visible messages.

Suspend and hibernate still require separate explicit grants in
`current/power-gates.json` (`enable <verb>`) and kernel power states (`mem` or
`freeze`, and `disk`). They are not enabled by this repair. An enabled hibernate
gate does not validate the resume path. All commands have a closed argument
shape with no shell or arbitrary argv; failure keeps the menu open.

## Application updates

Update > Omabuntu preserves the original Update root placement before System.
Its closed `omabuntu-update:review` action opens a separate interactive terminal;
menu loading/guards do not perform update checks. See
[Application Update menu](application-update-menu.md) for signed verification,
local-version refusal, confirmation stages, packaging and deployment boundaries.
The menu addition and updater payload were locally deployed after explicit
approval with a bar-only restart. Startup/menu definitions and preserved
preferences were verified. The user subsequently confirmed terminal invocation
and cancellation before network access. A separately approved metadata-only
check verified the public v0.2.0 signature/metadata and correctly blocked automatic
replacement of the local derivative; no bundle was downloaded and selection/
running identity were unchanged. Real update-switch acceptance remains outstanding.

## Not included

- Upstream Install/Remove and the rest of Update (pacman-based; an apt adaptation is
  a separate plan), the rest of Setup beyond default browser/terminal, the
  rest of Trigger beyond Screenshot, About, dmenu select/input modes, locale catalogs, upstream theme
  background images, and the font/background providers' live daemon work.
- Autostart, and any persistence of the Super+Space/Super+Esc binds across a
  Hyprland restart without an approved user-config edit.

## Evidence

Python contracts: `tests/test_menu_model.py` (parser, merge, routes, guard
batch, allowlist), `tests/test_menu_backends.py` (theme/font/background/power
backends against fixtures; no live gsettings, hyprctl or systemctl in tests),
`tests/test_command_menu.py` (fixture derivation witnesses), and
`tests/test_appearance_controls.py` (read-only guards, persisted bar/dock choices,
session refusal, transaction/rollback safety, helper closure and shared bindings).
The extended contained fixture also checks the real shared Appearance adapter,
queued writes and Hide/Show recovery using a synthetic session identity inside
its private sandbox, not the live desktop.

Offscreen report: `work/menu-port/20261025T203721.360444Z/report.json`
(`isolated-menu-fixtures-passed`). The derived fixture copy replaces PanelWindow
with a plain Window and removes the GlobalShortcut registrations, exactly like
the reviewed keybindings fixture; all model/rebuild/search/guard/provider logic
runs unchanged against the real helper inside bwrap: definitions, guard batch,
root rows, navigation, the system route with guard-driven row counts, the power
gate refusal, hidden/disabled/checked overlay rows, cursor skip, the apps
route, search with the drilldown divider, 23 theme provider rows with the
check glyph, and a theme apply recording state plus backup. The theme's live
hyprctl application fails by design in the sandbox (no compositor socket), so
live color application is not covered; no font/background provider run,
native focus, or visual acceptance is claimed.

Historical live-session evidence, not acceptance of plan 109: Super+Space and
Super+Escape were bound to `omabuntu:menu` and `omabuntu:system` outside the
personal `hyprland.lua`. Historical ordinary-action grants are no longer
necessary after deploying the repaired helper. Suspend/hibernate still require
explicit safety grants; hibernate's resume path was not verified. No actual
logout, reboot, shutdown or sleep action was exercised for this repair.
