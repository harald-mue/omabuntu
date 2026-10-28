-- Omabuntu floating-workspace titlebar (hyprbars, plugins v0.56.0).
--
-- Omarchy puts close/maximise/minimise on the titlebar of windows on floating
-- workspaces. hyprland-plugins v0.56.0 has no workspace_tag option. It does
-- support the dynamic window effect hyprbars:no_bar. The first named rule hides
-- bars on every window; the second, registered after it, clears that effect for
-- windows carrying omabuntu-floating-workspace, independently of float ownership. A later rule overwrites the effect.
-- The workspace switcher only refreshes these names. It must not redefine them,
-- because repeating an effect appends another copy.
--
-- Applied to the running compositor for testing. It is not yet included from
-- the user's hyprland.lua, and there is no autostart.

if not hl.plugin.hyprbars then
  return
end

-- hyprbars v0.56.0 has no per-button window placeholder; focus happens first.
local window = [[window = "activewindow"]]
local minimize_cmd = (os.getenv("HOME") or "") .. "/.local/bin/omabuntu-hyprland-window-minimize"

hl.window_rule({
  name = "omabuntu-hyprbars-hide",
  match = { class = ".*" },
  ["hyprbars:no_bar"] = "1",
})
hl.window_rule({
  name = "omabuntu-hyprbars-show-floated",
  -- Title updates emit TITLE|CLASS in Hyprland 0.56.2. Both overrides must
  -- match CLASS: custom effects do not trigger dependent-rule reevaluation.
  match = { class = ".*", tag = "omabuntu-floating-workspace" },
  ["hyprbars:no_bar"] = "0",
})

hl.config({
  plugin = {
    hyprbars = {
      enabled = true,
      bar_height = 30,
      bar_color = "rgba(101315ee)",
      ["col.text"] = "rgba(caccccee)",
      bar_text_font = "JetBrainsMono Nerd Font",
      bar_text_size = 12,
      bar_text_weight = "normal",
      bar_text_align = "left",
      bar_buttons_alignment = "right",
      bar_part_of_window = true,
      bar_precedence_over_border = true,
      bar_padding = 10,
      bar_button_padding = 8,
      icon_on_hover = false,
      on_double_click = "hyprctl dispatch 'hl.dsp.window.fullscreen({ mode = \"maximized\", action = \"toggle\", " .. window .. " })'",
    },
  },
})

for _, button in ipairs({
  { icon = "×", action = "hyprctl dispatch 'hl.dsp.window.close({ " .. window .. " })'" },
  { icon = "□", action = "hyprctl dispatch 'hl.dsp.window.fullscreen({ mode = \"maximized\", action = \"toggle\", " .. window .. " })'" },
  { icon = "−", action = minimize_cmd },
}) do
  hl.plugin.hyprbars.add_button({
    bg_color = "rgba(101315ff)",
    fg_color = "rgba(caccccff)",
    size = 20,
    icon = button.icon,
    action = button.action,
  })
end
