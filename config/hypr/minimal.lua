-- SPDX-License-Identifier: MIT
-- Standalone Omabuntu evaluation profile for Hyprland 0.56.2.
-- Not installed or sourced by the user's active configuration.
-- No autostart, shell, plugin, idle, lock, suspend, or provisioning actions.

hl.monitor({
  output = "",
  mode = "preferred",
  position = "auto",
  scale = "auto",
})

hl.config({
  misc = {
    disable_hyprland_logo = true,
  },
  general = {
    layout = "dwindle",
    gaps_in = 2,
    gaps_out = 10,
    border_size = 2,
  },
  decoration = {
    rounding = 8,
    blur = { enabled = false },
    shadow = { enabled = true },
  },
  dwindle = {
    preserve_split = true,
    force_split = 2,
  },
  input = {
    kb_layout = "de",
    kb_variant = "",
    -- The private Omarchy Compose extension is deliberately not assumed.
    kb_options = "",
    repeat_rate = 40,
    repeat_delay = 250,
    numlock_by_default = true,
    follow_mouse = 1,
    touchpad = {
      natural_scroll = false,
      clickfinger_behavior = true,
      scroll_factor = 0.4,
    },
  },
})

local function bind(keys, description, action)
  hl.bind(keys, action, { description = description })
end

-- Only an explicit keypress launches this installed Ubuntu application.
bind("SUPER + RETURN", "Launch terminal", hl.dsp.exec_cmd("ghostty"))
bind("SUPER + W", "Close focused window", hl.dsp.window.close())
bind("SUPER + Q", "Close focused window", hl.dsp.window.close())
bind("SUPER + T", "Toggle floating", hl.dsp.window.float({ action = "toggle" }))
bind("SUPER + F", "Toggle fullscreen", hl.dsp.window.fullscreen({ mode = "fullscreen" }))
bind("SUPER + J", "Toggle split", hl.dsp.layout("togglesplit"))
bind("SUPER + P", "Toggle pseudo tiling", hl.dsp.window.pseudo())

local directions = {
  { key = "LEFT", direction = "l" },
  { key = "RIGHT", direction = "r" },
  { key = "UP", direction = "u" },
  { key = "DOWN", direction = "d" },
}
for _, item in ipairs(directions) do
  bind("SUPER + " .. item.key, "Focus " .. item.direction,
    hl.dsp.focus({ direction = item.direction }))
  bind("SUPER + SHIFT + " .. item.key, "Swap " .. item.direction,
    hl.dsp.window.swap({ direction = item.direction }))
end

-- Deliberate first-stage simplification: global workspaces 1-10, not
-- Omarchy's per-monitor numbering helper. Physical keycodes also work on de.
for workspace = 1, 10 do
  local key = "code:" .. tostring(workspace + 9)
  bind("SUPER + " .. key, "Focus workspace " .. workspace,
    hl.dsp.focus({ workspace = workspace }))
  bind("SUPER + SHIFT + " .. key, "Move to workspace " .. workspace,
    hl.dsp.window.move({ workspace = workspace }))
  bind("SUPER + SHIFT + ALT + " .. key, "Move silently to workspace " .. workspace,
    hl.dsp.window.move({ workspace = workspace, follow = false }))
end

bind("SUPER + S", "Toggle scratchpad", hl.dsp.workspace.toggle_special("scratchpad"))
bind("SUPER + ALT + S", "Move to scratchpad",
  hl.dsp.window.move({ workspace = "special:scratchpad", follow = false }))
