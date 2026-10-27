# Floating-workspace dock: parity analysis and defect list

Status: Packages A and C are implemented and live (release `20261025-local.6`,
now running as release `20261025-local.19`); Package B (hyprbars titlebar
buttons) is built, loaded in the live session and pending user acceptance.
Package D is decided against: the user chose Omarchy's own indicator (full vs
faded opacity plus the 10 s launch pulse) over any dot addition (2026-10-25).
Source of truth: pinned Omarchy `03ff1eff3812933f7088484533784d2f63eaf19a`
(`shell/plugins/dock/{Dock.qml,DockWindow.qml,DockModel.js,AppGrid.qml}`,
`bin/omarchy-dock`, `bin/omarchy-hyprland-window-minimize`,
`default/hypr/bindings/tiling.lua`, `default/hypr/workspace-modes.lua`).

## Reported symptoms and their actual causes

| Symptom | Cause in this port | Omarchy behaviour |
|---|---|---|
| Dock partly disappears after switching workspaces/screens | `DockWindow.qml:30-48`: `fullscreenMode` reads `lastIpcObject.fullscreen` once; nothing refreshes toplevels/workspaces on a `fullscreen` or `configreloaded` event. A stale "maximized" reading makes `autohide` true and `tucked` hides the content behind the edge trigger | `Dock.qml:335-345` listens to `Hyprland.onRawEvent` and refreshes workspaces and toplevels on `fullscreen`, and re-reads every workspace mode on `configreloaded` |
| Same, second cause | `FloatingDock.qml:34-36` clears the whole slot model on every window change, destroying delegates under the pointer | `Dock.qml:105-117` moves/inserts/removes single rows, so slots survive |
| Same, third cause | `FloatingDock.qml:64-65` keeps only a session grant set by our mode switcher and `readMode` is a no-op; nothing re-checks the workspace after an external layout change | `Dock.qml:284-315` caches each workspace mode and pre-reads all workspaces through the layout helper |
| No window indicator | Running apps only get full opacity (`DockWindow.qml` `windowCount > 0`), and `windows` is frequently empty because of the matching defect below. **Omarchy has no dot indicator either** | Original also has no per-window dots; only full vs. faded opacity and a 10 s launch pulse (`Dock.qml:118-148`) |
| Cannot minimize/maximize windows on a floating workspace | Nothing in this port minimises or maximises at all. `activate()` calls `wayland.activate()` only; there is no `special:minimized` recognition or restore | Omarchy puts minimise/maximise/close on the **hyprbars titlebar buttons** that `workspace-modes.lua:488-501` adds for floating workspaces, plus `SUPER+M` → `omarchy-hyprland-window-minimize`. Minimised windows are moved to `special:minimized` and tagged `omarchy-minimized-from-<id>`; the dock restores them (`Dock.qml:189-215`) |
| Cannot pin or unpin apps | `FloatingDock.qml:45-58`: window classes are matched with `DesktopEntries.byId(class)`, which needs an exact id such as `firefox.desktop`. Keys are then stored **without** `.desktop`, so `entryFor()` returns null: no icon, no launch, and the menu's "Keep in dock"/"Remove from dock" appears to do nothing | `Dock.qml:47-52` uses `DesktopEntries.heuristicLookup(appId)` plus terminal-entry claiming, and stores `entry.id` (with `.desktop`); pins are persisted through `omarchy-dock pinned` |
| No default pins | `pinned` starts as `[]`; Omarchy's default dock has a default pin set | `Dock.qml:58-62` falls back to `defaultDockConfig.dock.pinned` |
| Cannot drag apps from the app panel into the dock | Our app panel is the authored `AppLauncher.qml` with no drag at all; the dock exposes no routing entry point | `AppGrid.qml:85-90` reports pointer position to `dock.moveExternalDrag`/`dropExternalDrag`, which forwards to the dock on that screen and pins at the drop index (`Dock.qml:355-380`) |

## Additional defects found while comparing

1. **No terminal/app-id claiming.** `Dock.qml:47-52` and `DockModel.claimingEntryId` map `--app-id=` and
   `org.omarchy.*` terminal windows to their launcher entry. The port only tries class/startupClass, so
   terminal windows and app-id-launched windows group wrongly or not at all.
2. **Dialogs and hidden entries are not filtered.** Original skips toplevels with a `parent` and marks
   `hasEntry: !entry.noDisplay`. The port marks `hasEntry: true` unconditionally.
3. **Wrong window source.** Original iterates `toplevels[i].wayland` and uses `toplevel.appId`;
   the port parses `lastIpcObject.class || initialClass`, which is empty for some Wayland clients.
4. **No launch pulse.** `isLaunching()` always returns false, so the original starting animation never runs.
5. **No z-order/focus guarantee.** Original raises the target (`alter_zorder top`) and focuses by address;
   the port relies on activation alone, which on multi-window apps can select the wrong window.
6. **Context-menu grab restored.** The upstream `HyprlandFocusGrab` is kept: an outside click clears
   the grab and closes the context menu. Only the monitor-remap guard (`ScreenMoveRemap`) remains
   excluded; the derived surface is always mapped.
7. **No persistent position/autohide/pins.** Original persists them through `omarchy-dock` (shell.json);
   the port keeps them in memory and drops them at every bar restart. Persisting them needs an approved
   user-config path, because a shell helper is excluded.
8. **Minimised windows are invisible to the port.** `FloatingDock.qml:24-29` requires
   `workspaceId >= 1`; a window on the `special:minimized` workspace reports a special-workspace id and is
   dropped instead of being shown as minimised (original `DockModel.isDockWindow` keeps minimised windows
   even without an entry).

## What "correct" would require

Ordered by dependency, smallest first:

1. **Fix window→entry mapping**: `hyprland` toplevel `wayland.appId`, `DesktopEntries.heuristicLookup`,
   terminal claiming, `.desktop` ids preserved, `noDisplay`/dialog filtering. This unblocks icons, launch,
   quit, pin/unpin and the running opacity.
2. **Incremental slot sync** instead of `model.clear()`.
3. **Refresh on `fullscreen`/`configreloaded`** and mode re-read, so visibility is not stale.
4. **Minimise support**: mark `special:minimized` windows, restore on activation (move back to the current
   workspace, raise, focus), and a way to minimise a floating window. Omarchy's minimise trigger is
   `SUPER+M` plus hyprbars buttons; hyprbars is not built here and needs its own plugin/ABI review.
5. **Pin/unpin semantics**: original behaviour restores pins to the default set, orders them by the dock
   order and persists them. Without a persistence decision, pins stay session-scoped.
6. **External drag from the app panel**: needs an app-panel API and cross-surface hit testing; only then can
   the original drop-index preview work.
7. **Window indicator**: *not an Omarchy feature*. If wanted, it is an authored addition (for example one dot
   per window) and must be recorded as a deliberate deviation, not as parity.

## Decisions needed before implementation

- Minimise/maximise surface on floating workspaces: (a) dock context-menu entries plus reviewed keybindings,
  (b) a substitute titlebar, or (c) build and admit the original hyprbars plugin. Option (c) needs a plugin
  build, an ABI check against Hyprland 0.56.2, a config reload and a rollback plan — all separately approved.
- Persistence of dock position, autohide and pins: session-only, or an approved user config file with backup.
- Whether to add a window indicator beyond Omarchy, and in which form.

No dock behaviour, keybinding, plugin, configuration or service has been changed by this analysis.

## Proposal: reaching Omarchy behaviour

"Same as Omarchy" splits into two very different work packages.

### Package A — dock defects (no new dependencies, no reload)

1. Window→entry mapping: `wayland.appId`, `DesktopEntries.heuristicLookup`, terminal
   `--app-id=`/`org.omarchy.*` claiming, keep `.desktop` ids, skip dialogs (`parent`)
   and `noDisplay` entries. Unblocks icons, launch, quit, pin/unpin and running opacity.
2. Incremental slot sync instead of `model.clear()`.
3. Refresh toplevels/workspaces on `fullscreen` and re-read workspace modes on
   `configreloaded`; grant stays tied to a successful switch plus a fresh check.
4. Minimised-window support: recognise `special:minimized`, keep those windows in the
   dock and restore them on activation with focus plus z-order, as `bringForward` does.
5. Launch pulse and default pins.
6. Persist position/autohide/pins in `~/.config/omabuntu/dock.json` (backed up,
   versioned schema) instead of the Arch helper. Same user-visible behaviour, no
   `omarchy-dock`.

This package fixes every reported symptom except the titlebar buttons, and needs no
plugin, package install or Hyprland reload.

### Package B — original titlebar buttons (hyprbars)

Omarchy's floating-workspace ×/□/− buttons are **not** dock code: they come from the
Hyprland plugin hyprbars, shipped there as `omarchy-hyprland-titlebars` and configured
by `workspace-modes.lua:456-502`. Without that plugin Omarchy itself only offers
`SUPER+M` (`omarchy-hyprland-window-minimize`).

Feasibility measured on this host:

- Hyprland 0.56.2, commit `efb50993…`, abiHash `efb50993…_aq_0.15_hu_0.14_hg_0.5_hc_0.1_hlg_0.6`.
- Matching headers are already installed: `/usr/include/hyprland`, `hyprland.pc` 0.56.2.
- hyprbars source: `hyprwm/hyprland-plugins/hyprbars` (needs `hyprland` pkg-config only).
- Build dependencies: PPA `hyprland-plugin-deps` would add **59 packages and upgrade
  `libhyprutils13` 0.14.2 → 0.14.3**, a library Hyprland is currently linked against.
  That upgrade is the main risk; installing only the truly missing build packages, or
  deferring the upgrade to the next session start, is safer.
- Loading requires a `plugin { hyprbars { … } }` entry, i.e. a **config edit plus a
  reload**, and a reload re-reads configuration and drops our runtime workspace tags —
  they must be re-applied and verified afterwards.
- hyprpm runs as the session user and may request elevation internally; never run `sudo hyprpm`. Migration currently reports a hyprbars build failure; see `hyprbars.md`.

Proposed sequence for Package B: pin the plugin commit, build out-of-tree against the
installed 0.56.2 headers in a private directory, verify `abiHash` acceptance and a
dry load on a spare session first, add a reviewed Lua snippet (buttons ×/□/− with
`hl.dsp.window.close`, `fullscreen({mode="maximized",action="toggle"})` and a minimise
action of our own), then reload with a config backup, re-apply and verify workspace
modes, and keep a one-command rollback (disable plugin, restore config, reload).

### Package C — drag from the app panel

Port the original drag handshake: the app panel reports pointer position to
`dock.moveExternalDrag`/`dropExternalDrag`, the dock on that screen previews the
insert position and pins at the drop index. Needs a drag source in `AppLauncher.qml`
and cross-surface hit testing; depends on Package A step 1 and 6.

### Package D — window indicator

Omarchy has none. Recording it as an authored deviation (one dot per window under the
icon) is the only option; it must not be described as parity.

Decision (2026-10-25): rejected by the user. The dock keeps Omarchy's own
signal instead — running apps at full opacity, pinned non-running apps faded
to `idleOpacity` 0.7, and a launch pulse for ten seconds after a dock click.
That behavior is implemented: `DockWindow.qml` stages the original opacity
binding and pulse animation unchanged, and the launch tracking in
`FloatingDock.qml` mirrors upstream `Dock.qml` (10 s timeout, settles when a
new window appears, 1 s recheck timer). The reason it was not visible earlier
was a stale bar process running pre-Package-A dock code with an
`isLaunching()` stub; the release-`20261025-local.19` bar carries the real
chain. Native visual acceptance still belongs to the user.

Recommended order: A (fixes all reported bugs), then B (visual parity), then C, and D
only if explicitly wanted. Each package ends with its own acceptance record; B needs a
separate approval for dependency installation, config edit and reload.


## Implementation record (Packages A and C)

Shipped in release `20261025-local.6`, running as PID 887748:

- **Entry claiming:** `wayland.appId` → `DesktopEntries.heuristicLookup` → terminal
  `--app-id=`/`org.omarchy.*` claiming; ids keep `.desktop`; `noDisplay` entries and
  dialogs (`toplevel.parent`) are skipped. Icons, launch, quit, pin/unpin and running
  opacity now resolve.
- **Slots:** `model.move/insert/remove` instead of `model.clear()`.
- **Visibility:** `Hyprland.onRawEvent` refreshes workspaces and toplevels on
  `fullscreen`/`configreloaded`; ownership still comes from the trial switch only.
- **Minimise/restore:** `special:minimized` is recognised, minimised windows stay in
  the dock, and activation restores them (`no_anim` move, focus, `alter_zorder`) and
  strips the `omabuntu-minimized-from-<id>` tag.
- **Launch pulse** (10 s) and **pin/order persistence** through one reviewed helper,
  `helpers/dock_state.py` → `~/.config/omabuntu/dock.json` (0600 file, 0700 directory,
  atomic replace, one `.previous` copy, strict schema, installed `.desktop` ids only).
- **Drag from the app panel:** the panel reports the pointer to the dock of that
  screen (`moveExternalDrag`/`dropExternalDrag`), the dock previews the insert slot and
  pins at the drop index — the original handshake.
- **Temporary deviation:** the dock context menu now offers Minimize and Maximize,
  because the Omarchy titlebar buttons need hyprbars (Package B). Remove them once the
  titlebar is active.

Verification: 301 Python tests (includes a 16-case dock suite and the state helper),
isolated QML compile/construct check, relocated release check. No Hyprland reload, no
config edit, no plugin, no new package. Native pointer/window acceptance is the user's
next test.

## Package B preparation

- `tools/build_hyprbars.py` pins `hyprwm/hyprland-plugins@d2427d4d…` and refuses any
  Hyprland other than commit `efb50993…`; it builds out of tree and explicitly does
  not load, edit config or reload.
- Current blocker measured: the plugin's `pkg-config` set is incomplete
  (`hyprland`'s own `.pc` requires the missing hyprutils/hyprlang/cairo/pango
  development files). Minimal install, simulated: 20 new packages plus
  `libhyprutils13` 0.14.2 → 0.14.3, no removals.
- `config/hypr/hyprbars.lua` holds the reviewed snippet: close/maximise/minimise on
  our `omabuntu-mode-floated` tag, quoted dispatchers only, guarded by
  `hl.plugin.hyprbars`. It parses with the installed binary
  (`Hyprland --verify-config` → `config ok`) and is **not** installed or included.
- Remaining steps for B: install the development packages, run the build tool, load
  the plugin in an isolated try, then include the snippet from the user's Hyprland
  config, reload with a backup, re-apply workspace modes and verify, with a documented
  one-command rollback.
