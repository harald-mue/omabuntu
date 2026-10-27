# Workspace layout switcher

The active workspace slot uses the glyphs from Omarchy's `Workspaces.qml` at
commit `03ff1eff3812933f7088484533784d2f63eaf19a`. A square is tiling
(`dwindle`), a circle is scrolling, and a triangle is floating. Clicking the
active slot cycles in the same order as Omarchy's default toggle: tiling,
scrolling, floating. Clicking another slot focuses it. The number row shows
global workspaces 1-6. Omarchy shows ten slots and labels the tenth `0`; this
bar stops at six and labels that slot `6`.

## What is original

`vendor/omarchy/shell/plugins/bar/widgets/Workspaces.qml` is the unchanged
upstream widget. `tools/workspace_modes.py` copies its `modeGlyph` function and
follows the click rule that the active slot cycles and any other slot focuses.
The cycle order is checked against
`vendor/omarchy/bin/omarchy-hyprland-workspace-layout-toggle`. That script is
not staged and is not executed.

## Ubuntu adaptation

This Hyprland session uses one global set of workspaces, not Omarchy's
per-monitor blocks of ten. The block file, `o.workspaces.focus`, ShellIpc and
the Omarchy helper commands are not used.

Hyprland 0.56.2 can store `dwindle` or `scrolling` on a workspace rule. It has
no floating workspace layout, and `workspaceopt` is deprecated. Floating
therefore follows the Omarchy idea without its Lua module: tag tiled,
unpinned, non-fullscreen windows with `omabuntu-mode-floated`, float those
windows, and on the way back to a tiled layout tile and untag only those
windows. The call is `hyprctl eval` of Hyprland's own `hl.workspace_rule`,
`hl.get_workspace_windows`, `hl.dsp.window.tag` and `hl.dsp.window.float`.

A window this mode floats is then sized the way Omarchy's `place()` does.
The usable monitor size is the scaled, rotated size minus reserved edges,
including this bar. The window becomes at most 1100 by 760 pixels, and at
most 64 percent of that width and 68 percent of that height, then centered.
Each further window on the same switch steps 24 pixels, through five
positions, so the windows do not stack exactly. Windows that were already
floating, fullscreen, or pinned keep their own size. New windows on a floating
workspace join the same placement path; the eval itself loads no title-bar plugin.

A window moved from one workspace to another is arranged after the move lands.
Hyprland 0.56.2 posts `movewindowv2` as `{address},{id},{name}` before
`moveToWorkspace` returns. The shell waits one millisecond, the same pause as
Omarchy's `window.move_to_workspace` handler, then uses the destination id.
A tiled window arriving on a floating workspace takes the existing claim path.
A window that leaves for a tiling workspace is tiled and untagged only when it
carries `omabuntu-mode-floated` and is not pinned. A window floated on its own,
with Super+T or its own rule, keeps floating. Special workspaces, whose ids are
negative, are left alone, as in Omarchy's `arrange()`.

Still different from that Omarchy module, and not part of this move:

- Omarchy also tags every window on a floating workspace and hangs title bars,
  shadows, and full opacity on that second tag. This port only tags windows
  the mode itself floated, then refreshes the existing named title-bar rules.
- New windows there float from the first frame by a window rule, excluding
  modals and apps that float on their own. Here a new window is claimed after
  `openwindow`, so it can appear tiled for a moment. There is no catalog of
  apps that float on their own.
- Leaving fullscreen on a floating workspace does not float the window again.
- Other maximized windows on a floating workspace are not cleared.
- `follow_mouse` is not switched to click-to-focus while a floating workspace
  is active.
- Floating is not the default for workspaces without a saved mode. Dwindle is.
- Per-monitor blocks of ten, Omarchy notifications, and the original shell
  refresh stay excluded.

A press on the active symbol applies the next layout once and changes the
symbol immediately. Presses that arrive while that call is still running are
kept as the latest layout and sent when the call ends, rather than ignored.
The symbol is not read back from Hyprland at that moment: the reported
tiled layout is still the previous one, which made one press look like it
had done nothing.

Not staged: Omarchy notifications, `omarchy-shell` refresh, per-monitor workspace
renumbering, and the wheel scroll between workspaces. A press does not edit
`hyprland.lua`. Runtime rules alone last only until the next Hyprland reload;
the managed snippet restores the saved scrolling overrides on config load.

## Login restore (plan 020)

A press now persists the applied mode to
`~/.local/state/omabuntu/current/workspace-layouts.txt` (one `<id> <mode>`
line per non-default workspace; reaching dwindle drops the line and an empty
file is removed, like Omarchy's toggle). At config load the managed snippet
`config/hypr/omabuntu-managed.lua` re-registers the saved `scrolling` rules
before the first window opens. Floating has no compositor rule: the shell
singleton `Commons/TrialDesktopState.qml` watches the same file, seeds the
floating workspaces and glyphs at login, and the claim path floats new
windows on them. The saved mode also wins in the switcher's `readMode`
until a press changes it.

## Persistence corrections (plan 021)

The first implementation was not functional: ordinary Python string escaping
turned the Lua newline separators into literal newlines inside quoted strings,
so the entire eval failed to parse. The generated program now retains the Lua
escapes. Executable Lua tests exercise all three modes, a new config load,
multiple workspace ids, and failure paths; substring checks alone were not
sufficient.

Saving uses a temporary sibling and rename, preserving the previous file on
write/replace failure. Save/delete failures are explicit eval errors and logged
by the switcher, not silently reported as saved. Dwindle remains the default:
its absence from the file means tiling. The manager prepares
`current/` before starting the shell, even on first login. New directories are
private; existing owned child-directory modes are preserved under the private
state parent rather than rejecting legacy menu state or changing its permissions.

The shell reads `OMABUNTU_STATE_HOME` (set by the manager), with an
`XDG_STATE_HOME`/home fallback, rather than hard-coding the home state path.
Successful presses update its saved-mode map immediately. Loading saved state
updates the active glyph; floating restore scans windows already mapped when
the shell or state file becomes ready, not just future `openwindow` events.
A later move uses `movewindowv2`: the same claim when the destination is
floating, and a release eval when a tagged window arrives on a tiling workspace.
Claims are queued and rechecked against the current floating grant so simultaneous
window opens are not dropped and revoked workspaces do not consume old claims.
The isolated QML fixture tests delayed state loading and queued claims without
access to a real compositor. The corrected release has also been deployed with
approval and checked on an existing empty workspace: scrolling and floating
persist, floating survives an Omabuntu-only restart, and tiling removes the saved
override. The probe restores the original effective layout and state-file
existence without changing application geometry. Actual fresh-login and visual
window-placement acceptance still require a real user login/observation; the
empty-workspace check does not establish either.

The clock weekday uses Omarchy's English `formatLocale` (`en-US`), not the
system keyboard layout.
