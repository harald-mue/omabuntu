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

-- Title-bar plugin (plan 073): a config-time hl.plugin.load registration is
-- discarded before the compositor creates its plugin system, so it never
-- loaded hyprbars at login on any reviewed Hyprland version. The persistent
-- login load is owned by the separately granted activation file
-- omabuntu-activation.lua (written with --session-activate
-- --enable-plugin-login): its hyprland.start handler execs the release
-- helper that runs the receipt-checked hyprpm reload. Guarded, so a release
-- without that file keeps parsing and loads nothing.
local confighome = (os.getenv("XDG_CONFIG_HOME") or ((os.getenv("HOME") or "") .. "/.config"))
local activation = confighome .. "/hypr/omabuntu-activation.lua"
local granted = io.open(activation, "r")
if granted then
  granted:close()
  dofile(activation)
end

-- Saved workspace layouts (plan 020), written by the switcher eval. Tiled
-- rules are re-registered here, before the first window opens. Floating has
-- no compositor rule: the switcher re-claims its windows from the same file.
local layouts = io.open(((os.getenv("XDG_STATE_HOME") or ((os.getenv("HOME") or "") .. "/.local/state"))
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
