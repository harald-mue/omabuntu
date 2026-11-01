-- SPDX-License-Identifier: MIT
-- Managed by the Omabuntu installer (plan 018); a later install overwrites
-- this file. It is loaded from hyprland.lua through exactly one
-- require("omabuntu-managed") line. It contains no binds, autostart,
-- monitors or window rules of its own.
--
-- Disable the compositor's own splash and logo. hyprpaper 0.8.4 draws a
-- separate overlay using the same message; these settings cannot disable it.
-- Its independent switch is splash = false in hyprpaper.conf (plan 022).

hl.config({
  misc = {
    disable_splash_rendering = true,
    disable_hyprland_logo = true,
    col = { splash = 0x00000000 },
  },
  -- Suppress the two Hyprland notification popups: the twice-a-year donation
  -- nag and the update-news window. hyprland-update-screen renders through
  -- Hyprtoolkit/EGL, which segfaults without hardware GL (plan 067).
  ecosystem = { no_donation_nag = true, no_update_news = true },
})

-- Title-bar plugin (plan 020): registering the path during the config load is
-- what makes Hyprland load it. A hyprland.start handler only queues a path
-- that no later pass reads. The load triggers one config reload; the next
-- pass finds the plugin options (docs/hyprbars.md). Guarded, so a release
-- without the artifact keeps parsing.
local home = os.getenv("HOME") or ""
local titlebars = home .. "/.local/lib/omabuntu/hyprbars.so"
local artifact = io.open(titlebars, "r")
if artifact then
  artifact:close()
  hl.plugin.load(titlebars)
end

-- Saved workspace layouts (plan 020), written by the switcher eval. Tiled
-- rules are re-registered here, before the first window opens. Floating has
-- no compositor rule: the switcher re-claims its windows from the same file.
local layouts = io.open(((os.getenv("XDG_STATE_HOME") or (home .. "/.local/state"))
  .. "/omabuntu/current/workspace-layouts.txt"), "r")
if layouts then
  for line in layouts:lines() do
    local id, mode = line:match("^%s*(%d+)%s+([%a]+)%s*$")
    if id and mode == "scrolling" then
      hl.workspace_rule({ workspace = id, layout = "scrolling" })
    end
  end
  layouts:close()
end
