# Floating-workspace titlebar (hyprbars)

## Purpose and safety

Omarchy's close/maximise/minimise titlebar comes from hyprbars; its dock restores
windows from `special:minimized`. Plugins execute inside the compositor and can
crash the desktop. Building successfully is not functional acceptance.

## Reference build

- Running Hyprland: 0.56.2, commit `efb50993780079460b0cbed1363e2166a2de1d9f`.
- Plugin reference: `hyprwm/hyprland-plugins` at
  `7644cecdb947060682891a0db2a0cdc5c0b9e704` (`v0.56.0`).
- Manually built library: `work/hyprbars-build/build/libhyprbars.so`.
- Copied reference: `~/.local/lib/omabuntu/hyprbars.so`, SHA-256
  `02296a7bdb612345a618402f89af39e3b829b522dcce697d48486c83d5d190db`.

The copy is not the path originally passed to `hyprctl plugin load`. Unloading
requires the exact absolute loaded path, not another copy with identical bytes.
Do not unload the working reference before a replacement has built successfully.

## hyprpm migration: not yet complete

hyprpm is the officially recommended plugin manager. **Run it as the ordinary
session user, never as `sudo hyprpm`.** It may request elevation internally for
specific preparation steps; that does not mean the whole program runs as root.
Earlier project instructions claiming otherwise were incorrect.

The user ran the following without sudo:

```sh
hyprpm update
hyprpm add https://github.com/hyprwm/hyprland-plugins 7644cecdb947060682891a0db2a0cdc5c0b9e704
hyprpm list
```

The initial status check reported **Plugin failed to build** for hyprbars
(and csgo-vulkan-fix). Verbose output identified missing `lua.h`: the build did
not include `/usr/include/lua5.4`, although `liblua5.4-dev` was installed.
The user subsequently rebuilt successfully with
`env CPLUS_INCLUDE_PATH=/usr/include/lua5.4 hyprpm update --force --verbose`.
All four plugins built; the final load-state reconciliation reported hyprbars
unloaded. Build success is not runtime/ABI acceptance. The output used headers
from `/usr/include/hyprland`; their compatibility still needs verification before
loading. Migration is not complete.

Once the build failure is understood and fixed, the controlled handoff is:

1. Verify the replacement build and back up existing manager/configuration state.
2. Unload the reference using its exact absolute loaded path.
3. Run `hyprpm enable hyprbars` and `hyprpm reload -n` as the session user.
4. Check `hyprpm list`, `hyprctl plugin list` and `hyprctl configerrors`.
5. Reapply and test the reviewed titlebar configuration with approval.

Do not manually edit hyprpm's internal checkout to pin a revision. Its
`add <url> [git rev]` interface accepts a revision directly. Compatibility still
needs a successful build and runtime verification.

## Process-scoped build wrapper

`tools/omabuntu_hyprpm.py` is a standalone Python 3 standard-library wrapper.
It appends `/usr/include/lua5.4` to any existing `CPLUS_INCLUDE_PATH` only for
the child process, without duplicating it or modifying the session environment.
It requires `lua.h` and hyprpm to exist, forwards every argument without a shell,
and replaces itself with hyprpm so signals and exit status are preserved.
It never adds sudo, `--force`, update, enable or reload automatically.

Use directly from the repository:

```sh
python3 tools/omabuntu_hyprpm.py update --verbose
```

### Standalone installation (applied with user approval)

Target: `~/.local/bin/omabuntu-hyprpm`. The source does not import project
modules and can be copied there without a Git checkout dependency. Before
installation, inspect the target and parent directories, reject symlinks, record
whether the target exists, and back up any existing target together with its
mode and hash in private state. Copy the reviewed script with mode `0755`, then
verify its hash against the source. Do not overwrite an existing file blindly.
No shell startup files or PATH settings need modification.

After approved installation, use:

```sh
omabuntu-hyprpm update --verbose
```

Use `--force` explicitly only when a rebuild of the unchanged revision is needed.
Even an update can reconcile plugin load state and unload a manually loaded
plugin; this wrapper does not make that operation read-only. The workaround is
not injected into direct `hyprpm` calls or future autostart commands. No wrapper
was added to a release bundle. After separate user approval, the standalone
wrapper was installed at `~/.local/bin/omabuntu-hyprpm`, mode `0755`, with
SHA-256 `947441ebab3e23cbecf3b5b948eefad166efc9d960542e0f044b2ca3cf5dc288`.
The target did not previously exist. Previous directory state and installation
verification are recorded in
`~/.local/state/omabuntu/hyprpm-wrapper-20261025T100916.636919Z/transaction.json`.
No hyprpm command was executed during installation. The agent's shell did not
resolve the short command through PATH; use `~/.local/bin/omabuntu-hyprpm`
explicitly if the same applies in the interactive shell. PATH was not modified.

Rollback of a later installation removes only the matching installed wrapper
and restores any recorded previous target and mode. Global environment files
remain untouched. Remove this workaround once build metadata includes Lua's
include dependency correctly.

## Known functional gaps

The v0.56.0 plugin lacks `workspace_tag` and `button_rounding`. It does register
the dynamic window effect `hyprbars:no_bar`. `config/hypr/hyprbars.lua` now
defines two named rules: every window gets `no_bar`, and windows tagged
`omabuntu-floating-workspace` override that because the later rule replaces the
effect. This membership tag follows Omarchy's separation from the ownership tag
`omabuntu-mode-floated`: already-floating windows get bars without being claimed
for later tiling. The rule keeps its historical `show-floated` name.
Both rules match `class = ".*"`; the show rule additionally requires membership. This shared class matcher is essential on Hyprland 0.56.2. Title changes
emit `RULE_PROP_TITLE | RULE_PROP_CLASS`. Its custom-effect reset removes
`hyprbars:no_bar` without adding that effect to the dependent-rule recheck set.
With a class-only hide rule and a tag-only show rule, title changes therefore
reapplied only the hide rule. The plugin then correctly read `no_bar = 1`, set
`m_hidden = true`, and received zero-sized geometry despite the tag remaining.

The diagnostic trace reproduced this on an ordinary Ghostty. A controlled
three-title probe failed before the matcher correction (`hidden=true`, 0x0) and
passed afterward (`hidden=false`, 1100x30 at every sampled title). Evidence:
`work/hyprbars-render-trace/title-red.json` and `title-green.json`. The correction
changes the named rule's matchers only; it does not patch plugin rendering or
append effects/buttons. Native visual acceptance is still separate.

The workspace switcher no longer turns the plugin off. It only re-enables the
named rules so Hyprland recomputes them. Redefining the effect from the switcher
would append a duplicate, so the switcher must not repeat the effect values.

A tag-only update does not reapply a class-only rule. The live check confirmed
this: after removing the tag, the test window kept the 30px bar until the named
rules were refreshed. With that refresh, the tagged window stayed 30px shorter
and the untagged windows on the other monitors returned to their previous height.
Google Chrome's height did not change in that check, so its bar behaviour is not
established.

hyprbars v0.56.0 does not substitute `%WINDOW%`. Titlebar buttons therefore use
the Lua selector `window = "activewindow"` after the bar focuses the owner,
`hl.dsp.window.close` for close, and
`~/.local/bin/omabuntu-hyprland-window-minimize` for minimise. Legacy
`hyprctl dispatch closewindow activewindow` is invalid under this Lua compositor. That
helper mirrors the pinned Omarchy script: it tags
`omabuntu-minimized-from-<workspace>`, moves to `special:minimized` without
following, then focuses the origin workspace so another real window stays active.
Install the helper from `tools/omabuntu_hyprland_window_minimize.py` into
`~/.local/bin` before testing titlebar buttons.

The snippet was applied once to the running compositor with `hyprctl eval`.
It is still not included from the user's `hyprland.lua`. hyprbars has no
`remove_button`, and `add_button` appends on every eval: repeating the eval
renders x/square/dash multiple times. Resetting requires an actual plugin
unload/load (e.g. `hyprctl plugin unload` and `hyprctl plugin load` on the hyprpm
artifact, or `hyprpm disable`/`enable` plus `hyprpm reload` in an interactive
terminal; `hyprpm reload` alone does not unload an unchanged, already-loaded
plugin). After such a reload, eval the snippet exactly once. Native acceptance of close, minimise,
maximise, and dock restore on disposable windows remains required. The dock's
Minimize/Maximize menu remains an intentional deviation until titlebar acceptance.

Autostart and persistent configuration remain separate backed-up approval gates.
No automatic plugin load is configured. **Loading this pinned plugin itself calls
`HyprlandAPI::reloadConfig()`**, even when invoked through `hyprctl plugin load`.
Plugin replacement therefore requires configuration-reload approval and recovery
of runtime-only bindings, tags and rules; it is not a reload-free operation.
See [dependencies](dependencies.md) for build prerequisites.

## Verification and rollback limitations

```sh
hyprpm list
hyprctl plugin list
hyprctl configerrors
hyprctl getoption plugin:hyprbars:enabled
```

Test close/maximise/minimise on disposable windows, dock restore, ordinary
workspace switches and simultaneous mixed-mode monitors. Static tests and a
responsive compositor do not establish these behaviours.

For a successfully manager-loaded plugin, normal rollback uses
`hyprpm disable hyprbars` followed by `hyprpm reload` as the session user.
This does not guarantee recovery from a crashed compositor. A TTY can help repair
future startup configuration, but cannot restore unsaved applications lost in a
compositor crash. Do not purge the manager cache as routine rollback.

## Client-side decoration buttons (Chrome/GTK, session setting)

Chrome/Chromium and GTK CSD apps draw their own min/max/close buttons from
the GNOME `org.gnome.desktop.wm.preferences button-layout` key; the Ubuntu
default `appmenu:minimize,maximize,close` made Chrome paint all three in
tiling. The pinned Omarchy commit ships no handling for this (no windowrule,
no button-layout write in `omarchy-theme-set-gnome`), so on 2026-10-25 the
session value was set to `appmenu` at the user's request. The empty right
side removes those buttons in every CSD app of this Hyprland session, not
only Chrome; windows close via keybinds, and floating workspaces will get
server-side titlebar buttons from hyprbars once it is loaded (see above).
The previous value and the restore command are recorded in
`work/window-buttons/20261025T221259Z/record.json`. No Hyprland config file
was touched.
