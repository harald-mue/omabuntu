# Arrange windows moved between floating and tiling workspaces

## Goal

When a window is moved from a floating workspace onto a tiling one, tile it
again only if this mode floated it. A tiled window moved onto a floating
workspace joins that mode. Match Omarchy's `arrange()` for that move, at
commit `03ff1eff3812933f7088484533784d2f63eaf19a`, without taking the other
workspace-mode behaviors listed below.

## Evidence compared

Omarchy `default/hypr/workspace-modes.lua` listens for
`window.move_to_workspace`. The handler waits one millisecond, because the
move is still being committed and changing the floating state underneath it
drops the move. `arrange()` then floats a tiled, non-fullscreen window that
arrives on a floating workspace, and tiles a window that leaves only when it
carries the mode tag and is not pinned. A window floated on its own stays
floating.

Hyprland 0.56.2 posts socket event `movewindowv2` as
`{address},{workspaceId},{workspaceName}` from `CWindow::moveToWorkspace`,
before that function returns. The same build's Lua stub names
`window.move_to_workspace` and `hl.timer`. This port has no config-load Lua
watcher. The shell already claims new windows from the `openwindow` socket
event through one serialized `hyprctl eval`.

The current claim path ignores moves. A window this mode floated therefore
stays floating, at the floating size, after it is dragged to a tiling
workspace.

## Current project gaps

- No handler for `movewindowv2`.
- No eval that removes `omabuntu-mode-floated` and clears floating.
- The running bar still serves the installed shell, so a source change is not
  visible until a later approved bar restart.

## Safety constraints

- Do not change input, fullscreen, maximize, idle, lock, or Hyprland config.
- Do not load Omarchy's title-bar buttons or call `hyprctl reload`.
- Do not start a lock or move a live window from the agent.
- The shell update that would show this on the bar stays a separate approval.

## Proposed shape

1. Add a release eval. It tiles and untags the addressed window only when
   that window is on the destination workspace, carries the mode tag, and is
   not pinned. It then refreshes the existing named title-bar rules.
2. On `movewindowv2`, wait one millisecond, then queue the existing claim when
   the destination is floating and the release eval when it is not. Keep the
   claim queue serialized, and keep `openwindow` immediate.
3. Regenerate `WorkspaceSwitcher.qml` from the generator and record the new
   staged hash. Cover the eval with executable Lua.

## Explicit exclusions

These Omarchy behaviors stay out of this change:

- The second tag on every window of a floating workspace, and the title-bar,
  shadow, and opacity rules that follow it.
- Window rules that float a new window on its first frame, and the catalog of
  apps that float on their own.
- Arranging a window again when it leaves fullscreen.
- Clearing maximized state on the other windows of a floating workspace.
- Setting `follow_mouse` to click-to-focus while a floating workspace is active.
- A floating default for every workspace that has no saved mode.
- Per-monitor blocks of ten, notifications, and the original shell refresh.

## Tasks

- [x] Record the move difference and the excluded behaviors.
- [x] Add the release eval and the delayed `movewindowv2` handler.
- [x] Regenerate the switcher mirror and its review hash.
- [x] Cover the release with executable Lua and the existing queue strings.
- [x] Document the move and the remaining differences.
