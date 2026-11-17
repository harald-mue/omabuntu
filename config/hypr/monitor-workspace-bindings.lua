-- SPDX-License-Identifier: MIT
-- Explicit opt-in bindings for the original monitor policy, not auto-loaded.
-- Derived from Omarchy v4.5.0 bindings/tiling.lua at ac2690cd (MIT).
-- Replace old absolute workspace binds; never layer this over duplicate chords.
local workspaces = assert(omabuntu_workspaces, "Load the monitor workspace policy first")
local function bind(keys, description, action)
  hl.bind(keys, action, { description = description })
end
for workspace = 1, 10 do
  local key = "code:" .. tostring(workspace + 9)
  bind("SUPER + " .. key, "Switch to workspace " .. workspace, workspaces.focus(workspace))
  bind("SUPER + SHIFT + " .. key, "Move window to workspace " .. workspace, workspaces.move_window(workspace))
  bind("SUPER + SHIFT + ALT + " .. key, "Move window silently to workspace " .. workspace,
    workspaces.move_window(workspace, false))
end
bind("SUPER + TAB", "Next workspace", hl.dsp.focus({ workspace = "m+1" }))
bind("SUPER + SHIFT + TAB", "Previous workspace", hl.dsp.focus({ workspace = "m-1" }))
bind("SUPER + CTRL + TAB", "Former workspace", hl.dsp.focus({ workspace = "previous_per_monitor" }))
for _, direction in ipairs({ {"LEFT", "l"}, {"RIGHT", "r"}, {"UP", "u"}, {"DOWN", "d"} }) do
  bind("SUPER + SHIFT + ALT + " .. direction[1], "Move workspace to " .. direction[2] .. " monitor",
    workspaces.move_to_monitor(direction[2]))
  bind("SUPER + SHIFT + CTRL + " .. direction[1], "Move window to " .. direction[2] .. " monitor",
    workspaces.move_window_to_monitor(direction[2]))
end
bind("CTRL + ALT + TAB", "Focus on next monitor", hl.dsp.focus({ monitor = "+1" }))
bind("CTRL + ALT + SHIFT + TAB", "Focus on previous monitor", hl.dsp.focus({ monitor = "-1" }))
bind("SUPER + mouse_down", "Scroll active workspace forward", hl.dsp.focus({ workspace = "m+1" }))
bind("SUPER + mouse_up", "Scroll active workspace backward", hl.dsp.focus({ workspace = "m-1" }))
