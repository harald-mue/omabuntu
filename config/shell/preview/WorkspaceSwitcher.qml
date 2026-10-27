import QtQuick
import Quickshell.Hyprland
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons

// Derived from Omarchy Workspaces.qml; upstream MIT notice is in LICENSE.
// The workspace each monitor shows carries its layout: a square tiles, a
// circle scrolls, and a triangle floats. Clicking it cycles to the next one,
// as Super + L does.
// Per-monitor workspace blocks, o.workspaces.focus, Omarchy layout scripts,
// ShellIpc, notifications, the title-bar plugin and a compositor reload are not staged.
// Global slots 1-10 match this session. The active slot shows the original glyph.
Item {
  id: root
  property int activeId: -1
  property bool liveModes: false
  property string activeMode: "dwindle"
  signal focusRequested(int workspaceId)
  implicitWidth: row.implicitWidth
  implicitHeight: 26
  width: implicitWidth

  function modeGlyph(mode) {
    if (mode === "scrolling") return "󰝥"
    if (mode === "floating") return "󰔶"
    return "󱓻"
  }

  function nextMode(mode) {
    if (mode === "dwindle") return "scrolling"
    if (mode === "scrolling") return "floating"
    return "dwindle"
  }

  function occupied(id) {
    var values = Hyprland.workspaces ? Hyprland.workspaces.values : []
    for (var i = 0; i < values.length; i++) {
      if (values[i].id !== id) continue
      var tops = values[i].toplevels
      return !!(tops && tops.values && tops.values.length > 0)
    }
    return false
  }

  function readMode(id) {
    // Plan 020: a fresh login has no tags or runtime rules yet; the saved
    // layout decides the symbol and the cycle order until a press changes it.
    var saved = TrialDesktopState.savedMode(String(id))
    if (saved) return saved
    var layout = "dwindle"
    var values = Hyprland.workspaces ? Hyprland.workspaces.values : []
    for (var i = 0; i < values.length; i++) {
      if (values[i].id !== id) continue
      var ipc = values[i].lastIpcObject
      if (ipc && ipc.tiledLayout) layout = String(ipc.tiledLayout)
      var tops = values[i].toplevels ? values[i].toplevels.values : []
      for (var j = 0; j < tops.length; j++) {
        var tags = tops[j].lastIpcObject ? tops[j].lastIpcObject.tags : null
        if (!tags) continue
        for (var k = 0; k < tags.length; k++) {
          var name = String(tags[k])
          if (name === "omabuntu-mode-floated" || name === "omabuntu-mode-floated*") return "floating"
        }
      }
    }
    return layout
  }

  // The compositor call is asynchronous. The symbol follows the press at once.
  // A later press is kept and sent when the current call ends; it is not dropped.
  // Reading tiledLayout here would put the old symbol back, because that value
  // is still the previous layout when the call returns.
  property var modes: ({})
  property int requestSerial: 0

  function cachedOrRead(id) {
    var cached = root.modes[id]
    return cached !== undefined ? cached : root.readMode(id)
  }

  function remember(id, mode) {
    var copy = {}
    for (var key in root.modes) copy[key] = root.modes[key]
    copy[id] = mode
    root.modes = copy
    if (id === root.activeId) root.activeMode = mode
  }

  function forget(id) {
    var copy = {}
    for (var key in root.modes) {
      if (Number(key) !== id) copy[key] = root.modes[key]
    }
    root.modes = copy
    if (id === root.activeId) root.activeMode = root.readMode(id)
  }

  function syncActive() {
    if (!root.liveModes || root.activeId < 1) return
    root.activeMode = root.cachedOrRead(root.activeId)
  }

  onActiveIdChanged: syncActive()
  onLiveModesChanged: { syncActive(); restoreFloating() }
  Component.onCompleted: { syncActive(); restoreFloating() }

  Connections {
    target: TrialDesktopState
    function onSavedModesChanged() { root.syncActive() }
    function onFloatingWorkspacesChanged() { root.restoreFloating() }
  }
  Connections {
    target: Hyprland.toplevels
    function onValuesChanged() { root.restoreFloating() }
  }

  readonly property string layoutEval: "local mode = \"%MODE%\"\nlocal id = \"%ID%\"\nlocal tag = \"omabuntu-mode-floated\"\nif mode ~= \"dwindle\" and mode ~= \"scrolling\" and mode ~= \"floating\" then\n  error(\"unsupported workspace mode\")\nend\nlocal cascade = 0\nlocal function place(window)\n  local monitor = window.monitor\n  if not monitor or not monitor.width then\n    return\n  end\n  local width = math.floor(monitor.width / monitor.scale)\n  local height = math.floor(monitor.height / monitor.scale)\n  if (monitor.transform or 0) % 2 == 1 then\n    width, height = height, width\n  end\n  local reserved = monitor.reserved or {}\n  width = width - (reserved.left or 0) - (reserved.right or 0)\n  height = height - (reserved.top or 0) - (reserved.bottom or 0)\n  hl.dispatch(hl.dsp.window.resize({\n    x = math.min(1100, math.floor(width * 0.64)),\n    y = math.min(760, math.floor(height * 0.68)),\n    relative = false,\n    window = window,\n  }))\n  hl.dispatch(hl.dsp.window.center({ window = window }))\n  cascade = (cascade + 1) % 5\n  hl.dispatch(hl.dsp.window.move({\n    x = cascade * 24 - 48,\n    y = cascade * 24 - 48,\n    relative = true,\n    window = window,\n  }))\nend\n-- This plugin revision has no workspace tag. The named rules hide bars on\n-- every window and show them again only for this tag. Refreshing the named\n-- rules recomputes that after a tag change without turning bars off globally.\nlocal function refreshFloatedBars()\n  if hl.plugin and hl.plugin.hyprbars then\n    hl.config({ plugin = { hyprbars = { enabled = true } } })\n    hl.window_rule({ name = \"omabuntu-hyprbars-hide\", enabled = true })\n    hl.window_rule({ name = \"omabuntu-hyprbars-show-floated\", enabled = true })\n  end\nend\nif mode == \"floating\" then\n  local claiming = {}\n  for _, window in ipairs(hl.get_workspace_windows(id)) do\n    if not window.floating and (window.fullscreen or 0) == 0 and not window.pinned then\n      hl.dispatch(hl.dsp.window.tag({ tag = \"+\" .. tag, window = window }))\n      table.insert(claiming, window)\n    end\n  end\n  for _, window in ipairs(claiming) do\n    hl.dispatch(hl.dsp.window.float({ action = \"on\", window = window }))\n    place(window)\n  end\n  refreshFloatedBars()\nelse\n  hl.workspace_rule({ workspace = id, layout = mode })\n  for _, window in ipairs(hl.get_windows({ tag = tag })) do\n    local workspace = window.workspace and tostring(window.workspace.id) or \"\"\n    if workspace == id and not window.pinned then\n      hl.dispatch(hl.dsp.window.float({ action = \"off\", window = window }))\n      hl.dispatch(hl.dsp.window.tag({ tag = \"-\" .. tag, window = window }))\n    end\n  end\n  refreshFloatedBars()\nend\n\n-- Plan 020: persist the mode so the next config load and the shell restore\n-- it. Dwindle is the default layout, so reaching it drops this workspace's\n-- line, and an empty file is removed, like Omarchy's toggle script.\nlocal statedir = (os.getenv(\"XDG_STATE_HOME\") or ((os.getenv(\"HOME\") or \"\") .. \"/.local/state\")) .. \"/omabuntu/current\"\nlocal modespath = statedir .. \"/workspace-layouts.txt\"\nlocal merged = {}\nlocal saved, readerr, readcode = io.open(modespath, \"r\")\nif not saved and readcode ~= 2 then\n  error(\"Could not save workspace mode: \" .. tostring(readerr))\nend\nif saved then\n  for line in saved:lines() do\n    local lid, lmode = line:match(\"^%s*(%d+)%s+([%a]+)%s*$\")\n    if lid and lmode and lid ~= id then merged[#merged + 1] = lid .. \" \" .. lmode end\n  end\n  saved:close()\nend\nif mode ~= \"dwindle\" then merged[#merged + 1] = id .. \" \" .. mode end\ntable.sort(merged)\nif #merged > 0 then\n  local temporary = modespath .. \".new\"\n  local out, err = io.open(temporary, \"w\")\n  if not out then error(\"Could not save workspace mode: \" .. tostring(err)) end\n  local written, writeerr = out:write(table.concat(merged, \"\\n\"), \"\\n\")\n  local closed, closeerr = out:close()\n  if not written or not closed then\n    os.remove(temporary)\n    error(\"Could not save workspace mode: \" .. tostring(writeerr or closeerr))\n  end\n  local renamed, renameerr = os.rename(temporary, modespath)\n  if not renamed then\n    os.remove(temporary)\n    error(\"Could not save workspace mode: \" .. tostring(renameerr))\n  end\nelse\n  local removed, err, code = os.remove(modespath)\n  if not removed and code ~= 2 then\n    error(\"Could not save workspace mode: \" .. tostring(err))\n  end\nend"

  function program(id, mode) {
    if (!(id >= 1) || (mode !== "dwindle" && mode !== "scrolling" && mode !== "floating")) return ""
    return root.layoutEval.replace("%MODE%", mode).replace("%ID%", String(id))
  }

  function launch(id, mode, serial) {
    var script = root.program(id, mode)
    if (script === "") return
    applyProc.requestId = id
    applyProc.requestMode = mode
    applyProc.requestSerial = serial
    applyProc.exec(["hyprctl", "eval", script])
  }

  function apply(mode) {
    var id = root.activeId
    if (!root.liveModes || root.program(id, mode) === "") return
    root.requestSerial += 1
    root.remember(id, mode)
    if (applyProc.running) {
      applyProc.queuedId = id
      applyProc.queuedMode = mode
      applyProc.queuedSerial = root.requestSerial
      return
    }
    root.launch(id, mode, root.requestSerial)
  }

  Process {
    id: applyProc
    property int requestId: -1
    property string requestMode: ""
    property int requestSerial: 0
    property int queuedId: -1
    property string queuedMode: ""
    property int queuedSerial: 0
    stdout: StdioCollector {
      id: applyOut
    }
    onExited: function(code) {
      var serial = requestSerial
      var id = requestId
      var ok = code === 0 && applyOut.text.trim() === "ok"
      if (ok) TrialDesktopState.applied(id, requestMode)
      if (!ok) console.warn("Workspace mode apply/save failed: " + applyOut.text.trim())
      if (!ok && serial === root.requestSerial) root.forget(id)
      if (queuedSerial > serial) {
        var nextId = queuedId
        var nextMode = queuedMode
        var nextSerial = queuedSerial
        queuedSerial = 0
        root.launch(nextId, nextMode, nextSerial)
      }
    }
  }

  // Restore windows that mapped before the shell/state file was ready, too.
  // Claims are serialized: an open-window burst must not drop all but one.
  // A window moved onto a floating workspace uses the same claim. A window
  // this mode floated, moved onto a tiling workspace, is tiled and untagged.
  // movewindowv2 is posted before the move returns, so that change waits one
  // millisecond, the same pause as Omarchy's move handler.
  property int claimCascade: 0
  property var claimQueue: []
  property var moveQueue: []
  readonly property string claimEval: "local id = \"%ID%\"\nlocal tag = \"omabuntu-mode-floated\"\nlocal target = \"address:%ADDRESS%\"\nlocal window = hl.get_window(target)\nif not window then\n  return\nend\nif window.workspace and tostring(window.workspace.id) ~= id then\n  return\nend\nif window.floating or (window.fullscreen or 0) ~= 0 or window.pinned then\n  return\nend\nhl.dispatch(hl.dsp.window.tag({ tag = \"+\" .. tag, window = target }))\nhl.dispatch(hl.dsp.window.float({ action = \"on\", window = target }))\nlocal cascade = %CASCADE%\nlocal monitor = window.monitor\nif not monitor or not monitor.width then\n  return\nend\nlocal width = math.floor(monitor.width / monitor.scale)\nlocal height = math.floor(monitor.height / monitor.scale)\nif (monitor.transform or 0) % 2 == 1 then\n  width, height = height, width\nend\nlocal reserved = monitor.reserved or {}\nwidth = width - (reserved.left or 0) - (reserved.right or 0)\nheight = height - (reserved.top or 0) - (reserved.bottom or 0)\nhl.dispatch(hl.dsp.window.resize({\n  x = math.min(1100, math.floor(width * 0.64)),\n  y = math.min(760, math.floor(height * 0.68)),\n  relative = false,\n  window = target,\n}))\nhl.dispatch(hl.dsp.window.center({ window = target }))\nhl.dispatch(hl.dsp.window.move({\n  x = cascade * 24 - 48,\n  y = cascade * 24 - 48,\n  relative = true,\n  window = target,\n}))\nif hl.plugin and hl.plugin.hyprbars then\n  hl.config({ plugin = { hyprbars = { enabled = true } } })\n  hl.window_rule({ name = \"omabuntu-hyprbars-hide\", enabled = true })\n  hl.window_rule({ name = \"omabuntu-hyprbars-show-floated\", enabled = true })\nend"
  readonly property string releaseEval: "local id = \"%ID%\"\nlocal tag = \"omabuntu-mode-floated\"\nlocal target = \"address:%ADDRESS%\"\nlocal window = hl.get_window(target)\nif not window then\n  return\nend\nif window.workspace and tostring(window.workspace.id) ~= id then\n  return\nend\nlocal function listed(name)\n  return name == tag or name == tag .. \"*\"\nend\nlocal function ours(candidate)\n  for _, other in ipairs(hl.get_windows({ tag = tag })) do\n    if other.address == candidate.address then\n      return true\n    end\n  end\n  local tags = candidate.tags\n  if type(tags) == \"string\" then\n    return listed(tags)\n  end\n  if type(tags) == \"table\" then\n    for _, name in ipairs(tags) do\n      if listed(name) then\n        return true\n      end\n    end\n  end\n  return false\nend\nif not ours(window) or window.pinned then\n  return\nend\nhl.dispatch(hl.dsp.window.tag({ tag = \"-\" .. tag, window = target }))\nhl.dispatch(hl.dsp.window.float({ action = \"off\", window = target }))\nif hl.plugin and hl.plugin.hyprbars then\n  hl.config({ plugin = { hyprbars = { enabled = true } } })\n  hl.window_rule({ name = \"omabuntu-hyprbars-hide\", enabled = true })\n  hl.window_rule({ name = \"omabuntu-hyprbars-show-floated\", enabled = true })\nend"

  function restoreFloating() {
    if (!root.liveModes) return
    var tops = Hyprland.toplevels.values
    for (var i = 0; i < tops.length; i++) {
      var workspace = tops[i].workspace
      if (!workspace) continue
      var ipc = tops[i].lastIpcObject
      if (ipc && ipc.floating) continue
      var address = String(tops[i].address || "")
      if (address.slice(0, 2) !== "0x") address = "0x" + address
      root.claimWindow(address, workspace.id)
    }
  }

  function claimWindow(address, workspaceId) {
    if (!root.liveModes || !(workspaceId >= 1) || !TrialDesktopState.isFloating(workspaceId)) return
    if (!/^0x[0-9a-fA-F]+$/.test(address)) return
    var queue = root.claimQueue.slice()
    for (var i = 0; i < queue.length; i++) {
      if (queue[i].address === address && queue[i].id === workspaceId) return
    }
    queue.push({ address: address, id: workspaceId })
    root.claimQueue = queue
    root.drainClaims()
  }

  function releaseWindow(address, workspaceId) {
    if (!root.liveModes || !(workspaceId >= 1) || TrialDesktopState.isFloating(workspaceId)) return
    if (!/^0x[0-9a-fA-F]+$/.test(address)) return
    var queue = root.claimQueue.slice()
    for (var i = 0; i < queue.length; i++) {
      if (queue[i].release && queue[i].address === address && queue[i].id === workspaceId) return
    }
    queue.push({ address: address, id: workspaceId, release: true })
    root.claimQueue = queue
    root.drainClaims()
  }

  function noteMove(address, workspaceId) {
    if (!root.liveModes || !(workspaceId >= 1)) return
    if (!/^0x[0-9a-fA-F]+$/.test(address)) return
    var pending = root.moveQueue.slice()
    pending.push({ address: address, id: workspaceId })
    root.moveQueue = pending
    moveTimer.restart()
  }

  function drainClaims() {
    if (claimProc.running || !root.liveModes) return
    var queue = root.claimQueue.slice()
    while (queue.length > 0) {
      var claim = queue.shift()
      root.claimQueue = queue
      var floating = TrialDesktopState.isFloating(claim.id)
      var script = ""
      if (claim.release) {
        if (floating) continue
        script = root.releaseEval
          .replace("%ADDRESS%", claim.address)
          .replace("%ID%", String(claim.id))
      } else {
        if (!floating) continue
        script = root.claimEval
          .replace("%ADDRESS%", claim.address)
          .replace("%ID%", String(claim.id))
          .replace("%CASCADE%", String(root.claimCascade))
        root.claimCascade = (root.claimCascade + 1) % 5
      }
      claimProc.exec(["hyprctl", "eval", script])
      return
    }
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (!event) return
      var name = String(event.name)
      var raw = String(event.data || "")
      if (name === "openwindow") {
        var data = raw.split(",")
        if (data.length < 2) return
        var opened = parseInt(data[1], 10)
        if (String(opened) !== data[1]) return
        root.claimWindow("0x" + data[0], opened)
        return
      }
      if (name !== "movewindowv2") return
      var first = raw.indexOf(",")
      var second = first < 0 ? -1 : raw.indexOf(",", first + 1)
      if (first < 1 || second < 0) return
      var idText = raw.slice(first + 1, second)
      var moved = parseInt(idText, 10)
      if (String(moved) !== idText) return
      root.noteMove("0x" + raw.slice(0, first), moved)
    }
  }

  Timer {
    id: moveTimer
    interval: 1
    repeat: false
    onTriggered: function() {
      var pending = root.moveQueue
      root.moveQueue = []
      for (var i = 0; i < pending.length; i++) {
        var item = pending[i]
        if (TrialDesktopState.isFloating(item.id)) root.claimWindow(item.address, item.id)
        else root.releaseWindow(item.address, item.id)
      }
    }
  }

  Process {
    id: claimProc
    onExited: root.drainClaims()
  }

  Row {
    id: row
    spacing: 1
    Repeater {
      model: 6
      delegate: Item {
        id: slot
        required property int index
        readonly property int workspaceId: index + 1
        readonly property bool shown: workspaceId === root.activeId
        width: 20
        height: 26
        clip: true
        opacity: shown || root.occupied(workspaceId) ? 1 : 0.5
        Rectangle {
          anchors.fill: parent
          radius: 3
          color: mouse.containsMouse ? Qt.rgba(0.792, 0.800, 0.800, 0.08)
               : slot.shown ? Qt.rgba(0.792, 0.800, 0.800, 0.18) : "transparent"
        }
        Text {
          anchors.centerIn: parent
          text: slot.shown && root.liveModes ? root.modeGlyph(root.activeMode)
               : slot.workspaceId
          color: Commons.Color.bar.text
          font.family: "JetBrainsMono Nerd Font"
          font.pixelSize: 12
          renderType: Text.NativeRendering
        }
        MouseArea {
          id: mouse
          anchors.fill: parent
          hoverEnabled: true
          cursorShape: Qt.PointingHandCursor
          preventStealing: true
          onPressed: function(mouse) {
            mouse.accepted = true
            if (slot.shown && root.liveModes) root.apply(root.nextMode(root.activeMode))
            else root.focusRequested(slot.workspaceId)
          }
        }
      }
    }
  }
}
