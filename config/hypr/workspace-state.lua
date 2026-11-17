-- SPDX-License-Identifier: MIT
-- Ubuntu adapter for Omarchy's workspace ID changes. Embedded by the generator.
-- Only an explicitly loaded monitor policy calls this module; no startup action.
local State = {}
local state_home = os.getenv("OMABUNTU_STATE_HOME")
  or ((os.getenv("XDG_STATE_HOME") or ((os.getenv("HOME") or "") .. "/.local/state")) .. "/omabuntu")
local modes_path = state_home .. "/current/workspace-layouts.txt"

local function read_modes()
  local file, message, code = io.open(modes_path, "r")
  if not file then
    if code == 2 then return {} end
    error("Could not read workspace layouts: " .. tostring(message))
  end
  local modes = {}
  for line in file:lines() do
    local id, mode = line:match("^(%d+)%s+([%a]+)$")
    assert(id and tonumber(id) > 0 and tonumber(id) <= 2147483647
      and (mode == "scrolling" or mode == "floating") and not modes[tonumber(id)],
      "Invalid workspace layout state; migration requires review")
    modes[tonumber(id)] = mode
  end
  file:close()
  return modes
end

-- The installer/deployment creates and validates the private state directories.
-- Never hide a monitor-state write failure or truncate the previous state file.
function State.atomic_text(path, text)
  local temporary = path .. ".monitor-new"
  local file = assert(io.open(temporary, "w"), "Could not prepare workspace state write")
  local ok, message = file:write(text)
  local closed, close_message = file:close()
  if not ok or not closed then
    os.remove(temporary)
    error("Could not save workspace layouts: " .. tostring(message or close_message))
  end
  local renamed, rename_message = os.rename(temporary, path)
  if not renamed then
    os.remove(temporary)
    error("Could not replace workspace state: " .. tostring(rename_message))
  end
end

local function save_modes(modes)
  local ids, lines = {}, {}
  for id in pairs(modes) do ids[#ids + 1] = id end
  table.sort(ids)
  for _, id in ipairs(ids) do lines[#lines + 1] = id .. " " .. modes[id] .. "\n" end
  State.atomic_text(modes_path, table.concat(lines))
end

-- Keep saved layouts and minimized restoration tags attached to the workspace,
-- not the global number it used to have. Preflight before any compositor change.
function State.renumber(workspace, id, change)
  local old = workspace.id
  assert(old > 0 and id > 0 and old ~= id, "Invalid workspace renumber")
  assert(not hl.get_workspace(id), "Workspace destination is occupied")
  local before = read_modes()
  assert(not before[id], "Destination has a saved layout; migration requires review")
  local next_modes = {}
  for key, value in pairs(before) do next_modes[key] = value end
  next_modes[id], next_modes[old] = before[old], nil
  -- A failed file write must never renumber an occupied workspace.
  save_modes(next_modes)
  local ok, message = pcall(change)
  local moved = hl.get_workspace(id)
  if not ok or not moved or moved.id ~= id or hl.get_workspace(old) then
    save_modes(before)
    error("Workspace renumber failed: " .. tostring(message))
  end
  -- A later workspace created under the old number must not inherit its layout.
  hl.workspace_rule({ workspace = tostring(old), layout = "dwindle" })
  hl.workspace_rule({ workspace = tostring(id), layout = before[old] == "scrolling" and "scrolling" or "dwindle" })
  for _, window in ipairs(hl.get_windows()) do
    for _, tag in ipairs(window.tags or {}) do
      local clean = tag:gsub("%*$", "")
      if clean == "omabuntu-minimized-from-" .. old then
        local target = "address:" .. window.address
        hl.dispatch(hl.dsp.window.tag({ tag = "-" .. clean, window = target }))
        hl.dispatch(hl.dsp.window.tag({ tag = "+omabuntu-minimized-from-" .. id, window = target }))
      end
    end
  end
end

return State
