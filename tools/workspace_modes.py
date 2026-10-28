#!/usr/bin/env python3
"""Workspace layout switcher derived from the pinned Omarchy widget.

The vendor widget and toggle script stay unchanged and are not executed.
Omarchy's toggle evals o.workspace_mode, notifies through omarchy helpers, and
can reload Hyprland to load the titlebar plugin. None of that is staged.
Dwindle and scrolling use Hyprland's own workspace_rule layout field. Floating
is not a Hyprland layout: all members receive a presentation tag, while only
tiled, non-fullscreen windows receive an ownership tag, are floated and placed
at Omarchy's centered size. Only owned, unpinned windows are tiled on the way
out; all departing windows lose their presentation tag. The title-bar plugin
is not loaded by this eval.
The applied mode is persisted to the state directory (plan 020) so the next
config load re-registers tiled rules and the shell restores floating modes.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDGET = ROOT / "vendor/omarchy/shell/plugins/bar/widgets/Workspaces.qml"
TOGGLE = ROOT / "vendor/omarchy/bin/omarchy-hyprland-workspace-layout-toggle"
MIRROR = ROOT / "config/shell/preview/WorkspaceSwitcher.qml"
MODES = ("dwindle", "scrolling", "floating")
TAG = "omabuntu-mode-floated"
SLOTS = 6
EVAL = r"""local mode = "%MODE%"
local id = "%ID%"
local tag = "omabuntu-mode-floated"
if mode ~= "dwindle" and mode ~= "scrolling" and mode ~= "floating" then
  error("unsupported workspace mode")
end
local cascade = 0
local function place(window)
  local monitor = window.monitor
  if not monitor or not monitor.width then
    return
  end
  local width = math.floor(monitor.width / monitor.scale)
  local height = math.floor(monitor.height / monitor.scale)
  if (monitor.transform or 0) % 2 == 1 then
    width, height = height, width
  end
  local reserved = monitor.reserved or {}
  width = width - (reserved.left or 0) - (reserved.right or 0)
  height = height - (reserved.top or 0) - (reserved.bottom or 0)
  hl.dispatch(hl.dsp.window.resize({
    x = math.min(1100, math.floor(width * 0.64)),
    y = math.min(760, math.floor(height * 0.68)),
    relative = false,
    window = window,
  }))
  hl.dispatch(hl.dsp.window.center({ window = window }))
  cascade = (cascade + 1) % 5
  hl.dispatch(hl.dsp.window.move({
    x = cascade * 24 - 48,
    y = cascade * 24 - 48,
    relative = true,
    window = window,
  }))
end
-- This plugin revision has no workspace_tag option. The named rules hide bars
-- on every window and show them for workspace membership. Refreshing the named
-- rules recomputes that after a tag change without turning bars off globally.
local function refreshFloatedBars()
  if hl.plugin and hl.plugin.hyprbars then
    hl.config({ plugin = { hyprbars = { enabled = true } } })
    hl.window_rule({ name = "omabuntu-hyprbars-hide", enabled = true })
    hl.window_rule({ name = "omabuntu-hyprbars-show-floated", enabled = true })
  end
end
if mode == "floating" then
  local claiming = {}
  for _, window in ipairs(hl.get_workspace_windows(id)) do
    hl.dispatch(hl.dsp.window.tag({ tag = "+omabuntu-floating-workspace", window = window }))
    if not window.floating and (window.fullscreen or 0) == 0 then
      hl.dispatch(hl.dsp.window.tag({ tag = "+" .. tag, window = window }))
      table.insert(claiming, window)
    end
  end
  for _, window in ipairs(claiming) do
    hl.dispatch(hl.dsp.window.float({ action = "on", window = window }))
    place(window)
  end
  refreshFloatedBars()
else
  hl.workspace_rule({ workspace = id, layout = mode })
  local mine = {}
  for _, window in ipairs(hl.get_windows({ tag = tag })) do
    mine[window.address] = true
  end
  for _, window in ipairs(hl.get_workspace_windows(id)) do
    hl.dispatch(hl.dsp.window.tag({ tag = "-omabuntu-floating-workspace", window = window }))
    if mine[window.address] and not window.pinned then
      hl.dispatch(hl.dsp.window.tag({ tag = "-" .. tag, window = window }))
      hl.dispatch(hl.dsp.window.float({ action = "off", window = window }))
    end
  end
  refreshFloatedBars()
end

-- Plan 020: persist the mode so the next config load and the shell restore
-- it. Dwindle is the default layout, so reaching it drops this workspace's
-- line, and an empty file is removed, like Omarchy's toggle script.
local statedir = (os.getenv("XDG_STATE_HOME") or ((os.getenv("HOME") or "") .. "/.local/state")) .. "/omabuntu/current"
local modespath = statedir .. "/workspace-layouts.txt"
local merged = {}
local saved, readerr, readcode = io.open(modespath, "r")
if not saved and readcode ~= 2 then
  error("Could not save workspace mode: " .. tostring(readerr))
end
if saved then
  for line in saved:lines() do
    local lid, lmode = line:match("^%s*(%d+)%s+([%a]+)%s*$")
    if lid and lmode and lid ~= id then merged[#merged + 1] = lid .. " " .. lmode end
  end
  saved:close()
end
if mode ~= "dwindle" then merged[#merged + 1] = id .. " " .. mode end
table.sort(merged)
if #merged > 0 then
  local temporary = modespath .. ".new"
  local out, err = io.open(temporary, "w")
  if not out then error("Could not save workspace mode: " .. tostring(err)) end
  local written, writeerr = out:write(table.concat(merged, "\n"), "\n")
  local closed, closeerr = out:close()
  if not written or not closed then
    os.remove(temporary)
    error("Could not save workspace mode: " .. tostring(writeerr or closeerr))
  end
  local renamed, renameerr = os.rename(temporary, modespath)
  if not renamed then
    os.remove(temporary)
    error("Could not save workspace mode: " .. tostring(renameerr))
  end
else
  local removed, err, code = os.remove(modespath)
  if not removed and code ~= 2 then
    error("Could not save workspace mode: " .. tostring(err))
  end
end
"""

# A window opened on a workspace this session set floating joins the mode:
# tag, float, cascade placement, and the same named-rule refresh. The mode
# eval claims only windows that existed at switch time; this one claims each
# new window as it maps, which is Omarchy's per-workspace layout behaviour.
CLAIM = """local id = "%ID%"
local tag = "omabuntu-mode-floated"
local target = "address:%ADDRESS%"
local window = hl.get_window(target)
if not window then
  return
end
if window.workspace and tostring(window.workspace.id) ~= id then
  return
end
local function refreshFloatedBars()
  if hl.plugin and hl.plugin.hyprbars then
    hl.config({ plugin = { hyprbars = { enabled = true } } })
    hl.window_rule({ name = "omabuntu-hyprbars-hide", enabled = true })
    hl.window_rule({ name = "omabuntu-hyprbars-show-floated", enabled = true })
  end
end
hl.dispatch(hl.dsp.window.tag({ tag = "+omabuntu-floating-workspace", window = target }))
if window.floating or (window.fullscreen or 0) ~= 0 then
  refreshFloatedBars()
  return
end
hl.dispatch(hl.dsp.window.tag({ tag = "+" .. tag, window = target }))
hl.dispatch(hl.dsp.window.float({ action = "on", window = target }))
refreshFloatedBars()
local cascade = %CASCADE%
local monitor = window.monitor
if not monitor or not monitor.width then
  return
end
local width = math.floor(monitor.width / monitor.scale)
local height = math.floor(monitor.height / monitor.scale)
if (monitor.transform or 0) % 2 == 1 then
  width, height = height, width
end
local reserved = monitor.reserved or {}
width = width - (reserved.left or 0) - (reserved.right or 0)
height = height - (reserved.top or 0) - (reserved.bottom or 0)
hl.dispatch(hl.dsp.window.resize({
  x = math.min(1100, math.floor(width * 0.64)),
  y = math.min(760, math.floor(height * 0.68)),
  relative = false,
  window = target,
}))
hl.dispatch(hl.dsp.window.center({ window = target }))
hl.dispatch(hl.dsp.window.move({
  x = cascade * 24 - 48,
  y = cascade * 24 - 48,
  relative = true,
  window = target,
}))
"""

# Omarchy's tile_for_mode: a window moved onto a tiling workspace gives up the
# floating this mode gave it. A window floated on its own has no tag and stays
# floating. A pinned window is left alone, because tiling it would unpin it.
# The move event is delivered before Hyprland finishes the move, so the shell
# waits one millisecond before running this, matching that handler's oneshot.
RELEASE = """local id = "%ID%"
local tag = "omabuntu-mode-floated"
local target = "address:%ADDRESS%"
local window = hl.get_window(target)
if not window then
  return
end
if window.workspace and tostring(window.workspace.id) ~= id then
  return
end
local function listed(name)
  return name == tag or name == tag .. "*"
end
local function ours(candidate)
  for _, other in ipairs(hl.get_windows({ tag = tag })) do
    if other.address == candidate.address then
      return true
    end
  end
  local tags = candidate.tags
  if type(tags) == "string" then
    return listed(tags)
  end
  if type(tags) == "table" then
    for _, name in ipairs(tags) do
      if listed(name) then
        return true
      end
    end
  end
  return false
end
hl.dispatch(hl.dsp.window.tag({ tag = "-omabuntu-floating-workspace", window = target }))
if ours(window) and not window.pinned then
  hl.dispatch(hl.dsp.window.tag({ tag = "-" .. tag, window = target }))
  hl.dispatch(hl.dsp.window.float({ action = "off", window = target }))
end
if hl.plugin and hl.plugin.hyprbars then
  hl.config({ plugin = { hyprbars = { enabled = true } } })
  hl.window_rule({ name = "omabuntu-hyprbars-hide", enabled = true })
  hl.window_rule({ name = "omabuntu-hyprbars-show-floated", enabled = true })
end
"""


def between(text, start, end):
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("Workspace switcher extraction witness differs")
    left, right = text.index(start), text.index(end)
    if left >= right:
        raise ValueError("Workspace switcher extraction boundaries reversed")
    return text[left:right]


def next_mode(mode):
    """Same order as the toggle script's default direction, not its back direction."""
    if mode == "dwindle":
        return "scrolling"
    if mode == "scrolling":
        return "floating"
    return "dwindle"


def next_modes_from_toggle(text):
    marker = "else\n  case"
    if text.count(marker) != 1:
        raise ValueError("Workspace toggle next-direction witness differs")
    body = text[text.index(marker):text.index("esac", text.index(marker))]
    found = {}
    for line in body.splitlines():
        line = line.strip()
        if not line.endswith(";;") or "NEW_MODE=" not in line:
            continue
        source, destination = line[:-2].split("NEW_MODE=", 1)
        found[source.strip().rstrip(")")] = destination.strip()
    if found.get("dwindle") != "scrolling" or found.get("scrolling") != "floating" or found.get("*") != "dwindle":
        raise ValueError("Workspace toggle cycle differs")
    return found


def program(workspace_id, mode):
    if type(workspace_id) is not int or isinstance(workspace_id, bool) or not 1 <= workspace_id <= 2147483647:
        raise ValueError("Workspace id is not a positive Hyprland id")
    if mode not in MODES:
        raise ValueError("Workspace mode is not dwindle, scrolling, or floating")
    if "%MODE%" not in EVAL or "%ID%" not in EVAL:
        raise ValueError("Workspace eval placeholders differ")
    script = EVAL.replace("%MODE%", mode).replace("%ID%", str(workspace_id))
    for forbidden in ("omarchy-", "hyprctl", "reload", "titlebars", "notify", "exec", "os.execute"):
        if forbidden in script:
            raise ValueError("Workspace eval contains an excluded Omarchy route")
    return script


def claim_program(address, workspace_id, cascade=0):
    """Eval script that brings one new window into a floating workspace."""
    if type(workspace_id) is not int or isinstance(workspace_id, bool) or not 1 <= workspace_id <= 2147483647:
        raise ValueError("Workspace id is not a positive Hyprland id")
    if not isinstance(address, str) or not address.startswith("0x") or len(address) <= 2:
        raise ValueError("Window address is not a Hyprland address")
    if type(cascade) is not int or isinstance(cascade, bool) or not 0 <= cascade <= 4:
        raise ValueError("Cascade slot is out of range")
    for placeholder in ("%ID%", "%ADDRESS%", "%CASCADE%"):
        if placeholder not in CLAIM:
            raise ValueError("Workspace claim placeholders differ")
    script = (CLAIM.replace("%ID%", str(workspace_id))
                  .replace("%ADDRESS%", address)
                  .replace("%CASCADE%", str(cascade)))
    for forbidden in ("omarchy-", "hyprctl", "reload", "titlebars", "notify", "exec", "os.execute"):
        if forbidden in script:
            raise ValueError("Workspace claim contains an excluded Omarchy route")
    return script


def release_program(address, workspace_id):
    """Eval script that tiles one window this mode floated, after it leaves."""
    if type(workspace_id) is not int or isinstance(workspace_id, bool) or not 1 <= workspace_id <= 2147483647:
        raise ValueError("Workspace id is not a positive Hyprland id")
    if not isinstance(address, str) or not address.startswith("0x") or len(address) <= 2:
        raise ValueError("Window address is not a Hyprland address")
    for placeholder in ("%ID%", "%ADDRESS%"):
        if placeholder not in RELEASE:
            raise ValueError("Workspace release placeholders differ")
    script = RELEASE.replace("%ID%", str(workspace_id)).replace("%ADDRESS%", address)
    for forbidden in ("omarchy-", "hyprctl", "reload", "titlebars", "notify", "exec", "os.execute"):
        if forbidden in script:
            raise ValueError("Workspace release contains an excluded Omarchy route")
    return script


def derive_workspaces(data):
    text = data.decode()
    glyph = between(text, "  function modeGlyph(mode) {\n", "\n\n  // A layout only changes")
    press = between(text, "        onPressed: function() {\n", "        onWheelMoved:")
    if "root.cycleLayout()" not in press or "root.focusWorkspace(modelData)" not in press:
        raise ValueError("Workspace click witness differs")
    if "omarchy-hyprland-workspace-layout-toggle" not in text:
        raise ValueError("Workspace source no longer delegates layout changes")
    comment = between(text, "  // The workspace each monitor shows carries its layout:", "  property string activeMode:")
    extracted = []
    for line in comment.strip().splitlines():
        line = line.strip()
        if line.startswith("//"):
            line = line[2:].strip()
        if line:
            extracted.append("// " + line)
    comment_block = "\n".join(extracted)
    lua = EVAL.replace("`", "")
    if "`" in lua or "${" in lua:
        raise ValueError("Workspace eval cannot be embedded")
    qml = f"""import QtQuick
import Quickshell.Hyprland
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons

// Derived from Omarchy Workspaces.qml; upstream MIT notice is in LICENSE.
{comment_block}
// Per-monitor workspace blocks, o.workspaces.focus, Omarchy layout scripts,
// ShellIpc, notifications, the title-bar plugin and a compositor reload are not staged.
// Global slots 1-10 match this session. The active slot shows the original glyph.
Item {{
  id: root
  property int activeId: -1
  property bool liveModes: false
  property string activeMode: "dwindle"
  signal focusRequested(int workspaceId)
  implicitWidth: row.implicitWidth
  implicitHeight: 26
  width: implicitWidth

{glyph}

  function nextMode(mode) {{
    if (mode === "dwindle") return "scrolling"
    if (mode === "scrolling") return "floating"
    return "dwindle"
  }}

  function occupied(id) {{
    var values = Hyprland.workspaces ? Hyprland.workspaces.values : []
    for (var i = 0; i < values.length; i++) {{
      if (values[i].id !== id) continue
      var tops = values[i].toplevels
      return !!(tops && tops.values && tops.values.length > 0)
    }}
    return false
  }}

  function readMode(id) {{
    // Plan 020: a fresh login has no tags or runtime rules yet; the saved
    // layout decides the symbol and the cycle order until a press changes it.
    var saved = TrialDesktopState.savedMode(String(id))
    if (saved) return saved
    var layout = "dwindle"
    var values = Hyprland.workspaces ? Hyprland.workspaces.values : []
    for (var i = 0; i < values.length; i++) {{
      if (values[i].id !== id) continue
      var ipc = values[i].lastIpcObject
      if (ipc && ipc.tiledLayout) layout = String(ipc.tiledLayout)
      var tops = values[i].toplevels ? values[i].toplevels.values : []
      for (var j = 0; j < tops.length; j++) {{
        var tags = tops[j].lastIpcObject ? tops[j].lastIpcObject.tags : null
        if (!tags) continue
        for (var k = 0; k < tags.length; k++) {{
          var name = String(tags[k])
          if (name === "{TAG}" || name === "{TAG}*") return "floating"
        }}
      }}
    }}
    return layout
  }}

  // The compositor call is asynchronous. The symbol follows the press at once.
  // A later press is kept and sent when the current call ends; it is not dropped.
  // Reading tiledLayout here would put the old symbol back, because that value
  // is still the previous layout when the call returns.
  property var modes: ({{}})
  property int requestSerial: 0

  function cachedOrRead(id) {{
    var cached = root.modes[id]
    return cached !== undefined ? cached : root.readMode(id)
  }}

  function remember(id, mode) {{
    var copy = {{}}
    for (var key in root.modes) copy[key] = root.modes[key]
    copy[id] = mode
    root.modes = copy
    if (id === root.activeId) root.activeMode = mode
  }}

  function forget(id) {{
    var copy = {{}}
    for (var key in root.modes) {{
      if (Number(key) !== id) copy[key] = root.modes[key]
    }}
    root.modes = copy
    if (id === root.activeId) root.activeMode = root.readMode(id)
  }}

  function syncActive() {{
    if (!root.liveModes || root.activeId < 1) return
    root.activeMode = root.cachedOrRead(root.activeId)
  }}

  onActiveIdChanged: syncActive()
  onLiveModesChanged: {{ syncActive(); restoreFloating() }}
  Component.onCompleted: {{ syncActive(); restoreFloating() }}

  Connections {{
    target: TrialDesktopState
    function onSavedModesChanged() {{ root.syncActive() }}
    function onFloatingWorkspacesChanged() {{ root.restoreFloating() }}
  }}
  Connections {{
    target: Hyprland.toplevels
    function onValuesChanged() {{ root.restoreFloating() }}
  }}

  readonly property string layoutEval: {json.dumps(lua.rstrip())}

  function program(id, mode) {{
    if (!(id >= 1) || (mode !== "dwindle" && mode !== "scrolling" && mode !== "floating")) return ""
    return root.layoutEval.replace("%MODE%", mode).replace("%ID%", String(id))
  }}

  function launch(id, mode, serial) {{
    var script = root.program(id, mode)
    if (script === "") return
    applyProc.requestId = id
    applyProc.requestMode = mode
    applyProc.requestSerial = serial
    applyProc.exec(["hyprctl", "eval", script])
  }}

  function apply(mode) {{
    var id = root.activeId
    if (!root.liveModes || root.program(id, mode) === "") return
    root.requestSerial += 1
    root.remember(id, mode)
    if (applyProc.running) {{
      applyProc.queuedId = id
      applyProc.queuedMode = mode
      applyProc.queuedSerial = root.requestSerial
      return
    }}
    root.launch(id, mode, root.requestSerial)
  }}

  Process {{
    id: applyProc
    property int requestId: -1
    property string requestMode: ""
    property int requestSerial: 0
    property int queuedId: -1
    property string queuedMode: ""
    property int queuedSerial: 0
    stdout: StdioCollector {{
      id: applyOut
    }}
    onExited: function(code) {{
      var serial = requestSerial
      var id = requestId
      var ok = code === 0 && applyOut.text.trim() === "ok"
      if (ok) TrialDesktopState.applied(id, requestMode)
      if (!ok) console.warn("Workspace mode apply/save failed: " + applyOut.text.trim())
      if (!ok && serial === root.requestSerial) root.forget(id)
      if (queuedSerial > serial) {{
        var nextId = queuedId
        var nextMode = queuedMode
        var nextSerial = queuedSerial
        queuedSerial = 0
        root.launch(nextId, nextMode, nextSerial)
      }}
    }}
  }}

  // Restore windows that mapped before the shell/state file was ready, too.
  // Claims are serialized: an open-window burst must not drop all but one.
  // A window moved onto a floating workspace uses the same claim. A window
  // this mode floated, moved onto a tiling workspace, is tiled and untagged.
  // movewindowv2 is posted before the move returns, so that change waits one
  // millisecond, the same pause as Omarchy's move handler.
  property int claimCascade: 0
  property var claimQueue: []
  property var moveQueue: []
  property var retileQueue: []
  readonly property string claimEval: {json.dumps(CLAIM.rstrip())}
  readonly property string releaseEval: {json.dumps(RELEASE.rstrip())}

  function restoreFloating() {{
    if (!root.liveModes) return
    var tops = Hyprland.toplevels.values
    for (var i = 0; i < tops.length; i++) {{
      var workspace = tops[i].workspace
      if (!workspace) continue
      var address = String(tops[i].address || "")
      if (address.slice(0, 2) !== "0x") address = "0x" + address
      root.claimWindow(address, workspace.id)
    }}
  }}

  function claimAllowed(workspaceId) {{
    if (!root.liveModes || !(workspaceId >= 1) || !TrialDesktopState.isFloating(workspaceId)) return false
    // A switch away from floating emits its own floating-off events before
    // the async apply/save finishes. Do not undo that approved mode change.
    if (applyProc.running && applyProc.requestId === workspaceId && applyProc.requestMode !== "floating") return false
    if (applyProc.running && applyProc.queuedSerial > applyProc.requestSerial &&
        applyProc.queuedId === workspaceId && applyProc.queuedMode !== "floating") return false
    return true
  }}

  function claimWindow(address, workspaceId) {{
    if (!root.claimAllowed(workspaceId)) return
    if (!/^0x[0-9a-fA-F]+$/.test(address)) return
    var queue = root.claimQueue.slice()
    for (var i = 0; i < queue.length; i++) {{
      if (queue[i].address === address && queue[i].id === workspaceId) return
    }}
    queue.push({{ address: address, id: workspaceId }})
    root.claimQueue = queue
    root.drainClaims()
  }}

  function releaseWindow(address, workspaceId) {{
    if (!root.liveModes || !(workspaceId >= 1) || TrialDesktopState.isFloating(workspaceId)) return
    if (!/^0x[0-9a-fA-F]+$/.test(address)) return
    var queue = root.claimQueue.slice()
    for (var i = 0; i < queue.length; i++) {{
      if (queue[i].release && queue[i].address === address && queue[i].id === workspaceId) return
    }}
    queue.push({{ address: address, id: workspaceId, release: true }})
    root.claimQueue = queue
    root.drainClaims()
  }}

  function noteMove(address, workspaceId) {{
    if (!root.liveModes || !(workspaceId >= 1)) return
    if (!/^0x[0-9a-fA-F]+$/.test(address)) return
    var pending = root.moveQueue.slice()
    pending.push({{ address: address, id: workspaceId }})
    root.moveQueue = pending
    moveTimer.restart()
  }}

  // Hyprland temporarily floats tiled drag targets, then tiles them at drop.
  // Approved policy: correct any retile on a floating workspace, including a
  // manual toggle. State-one events are ignored to avoid a corrective loop.
  function noteRetile(address) {{
    if (!root.liveModes || !/^0x[0-9a-fA-F]+$/.test(address)) return
    var tops = Hyprland.toplevels.values
    for (var i = 0; i < tops.length; i++) {{
      var candidate = String(tops[i].address || "")
      if (candidate.slice(0, 2) !== "0x") candidate = "0x" + candidate
      if (candidate !== address) continue
      var workspace = tops[i].workspace
      if (!workspace || !root.claimAllowed(workspace.id)) return
      var queue = root.retileQueue.slice()
      for (var j = 0; j < queue.length; j++) {{
        if (queue[j].address === address && queue[j].id === workspace.id) return
      }}
      queue.push({{ address: address, id: workspace.id }})
      root.retileQueue = queue
      retileTimer.restart()
      return
    }}
  }}

  function drainClaims() {{
    if (claimProc.running || !root.liveModes) return
    var queue = root.claimQueue.slice()
    while (queue.length > 0) {{
      var claim = queue.shift()
      root.claimQueue = queue
      var floating = TrialDesktopState.isFloating(claim.id)
      var script = ""
      if (claim.release) {{
        if (floating) continue
        script = root.releaseEval
          .replace("%ADDRESS%", claim.address)
          .replace("%ID%", String(claim.id))
      }} else {{
        if (!root.claimAllowed(claim.id)) continue
        script = root.claimEval
          .replace("%ADDRESS%", claim.address)
          .replace("%ID%", String(claim.id))
          .replace("%CASCADE%", String(root.claimCascade))
        root.claimCascade = (root.claimCascade + 1) % 5
      }}
      claimProc.exec(["hyprctl", "eval", script])
      return
    }}
  }}

  Connections {{
    target: Hyprland
    function onRawEvent(event) {{
      if (!event) return
      var name = String(event.name)
      var raw = String(event.data || "")
      if (name === "changefloatingmode") {{
        var state = raw.split(",")
        if (state.length === 2 && state[1] === "0" && /^[0-9a-fA-F]+$/.test(state[0]))
          root.noteRetile("0x" + state[0])
        return
      }}
      // The fullscreen socket event has only 0/1, not a window address. It
      // covers maximization too. Recheck candidates after the change lands;
      // the Lua claim decides from live state, never an IPC snapshot or focus.
      if (name === "fullscreen") {{
        if (root.liveModes && (raw === "0" || raw === "1")) fullscreenTimer.restart()
        return
      }}
      if (name === "openwindow") {{
        var data = raw.split(",")
        if (data.length < 2) return
        var opened = parseInt(data[1], 10)
        if (String(opened) !== data[1]) return
        root.claimWindow("0x" + data[0], opened)
        return
      }}
      if (name !== "movewindowv2") return
      var first = raw.indexOf(",")
      var second = first < 0 ? -1 : raw.indexOf(",", first + 1)
      if (first < 1 || second < 0) return
      var idText = raw.slice(first + 1, second)
      var moved = parseInt(idText, 10)
      if (String(moved) !== idText) return
      root.noteMove("0x" + raw.slice(0, first), moved)
    }}
  }}

  Timer {{
    id: retileTimer
    interval: 1
    repeat: false
    onTriggered: function() {{
      var pending = root.retileQueue
      root.retileQueue = []
      for (var i = 0; i < pending.length; i++) {{
        var item = pending[i]
        root.claimWindow(item.address, item.id)
      }}
    }}
  }}

  Timer {{
    id: fullscreenTimer
    interval: 1
    repeat: false
    onTriggered: root.restoreFloating()
  }}

  Timer {{
    id: moveTimer
    interval: 1
    repeat: false
    onTriggered: function() {{
      var pending = root.moveQueue
      root.moveQueue = []
      for (var i = 0; i < pending.length; i++) {{
        var item = pending[i]
        if (TrialDesktopState.isFloating(item.id)) root.claimWindow(item.address, item.id)
        else root.releaseWindow(item.address, item.id)
      }}
    }}
  }}

  Process {{
    id: claimProc
    onExited: root.drainClaims()
  }}

  Row {{
    id: row
    spacing: 1
    Repeater {{
      model: {SLOTS}
      delegate: Item {{
        id: slot
        required property int index
        readonly property int workspaceId: index + 1
        readonly property bool shown: workspaceId === root.activeId
        width: 20
        height: 26
        clip: true
        opacity: shown || root.occupied(workspaceId) ? 1 : 0.5
        Rectangle {{
          anchors.fill: parent
          radius: 3
          color: mouse.containsMouse ? Qt.rgba(0.792, 0.800, 0.800, 0.08)
               : slot.shown ? Qt.rgba(0.792, 0.800, 0.800, 0.18) : "transparent"
        }}
        Text {{
          anchors.centerIn: parent
          text: slot.shown && root.liveModes ? root.modeGlyph(root.activeMode)
               : slot.workspaceId
          color: Commons.Color.bar.text
          font.family: "JetBrainsMono Nerd Font"
          font.pixelSize: 12
          renderType: Text.NativeRendering
        }}
        MouseArea {{
          id: mouse
          anchors.fill: parent
          hoverEnabled: true
          cursorShape: Qt.PointingHandCursor
          preventStealing: true
          onPressed: function(mouse) {{
            mouse.accepted = true
            if (slot.shown && root.liveModes) root.apply(root.nextMode(root.activeMode))
            else root.focusRequested(slot.workspaceId)
          }}
        }}
      }}
    }}
  }}
}}
"""
    if "omarchy-hyprland" in qml or "hyprctl reload" in qml or "titlebars" in qml:
        raise ValueError("Derived workspace switcher retained an excluded route")
    if qml.count("import Quickshell.Hyprland\n") != 1:
        raise ValueError("Workspace switcher Hyprland import witness differs")
    return qml.encode()


def main():
    data = derive_workspaces(WIDGET.read_bytes())
    next_modes_from_toggle(TOGGLE.read_text())
    MIRROR.write_bytes(data)
    print(MIRROR)


if __name__ == "__main__":
    main()
