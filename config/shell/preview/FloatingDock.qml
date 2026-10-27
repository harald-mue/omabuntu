import QtQuick
import Quickshell
import Quickshell.Hyprland
import qs.Commons
import "Port/DockModel.js" as Model

// Source-derived Omarchy dock behaviour: entry claiming, minimised windows,
// launch pulse, pins/order, restore-with-focus and app-panel drop routing.
// No helper execution, IPC, configuration service or Arch command.
Scope {
  id: root
  property var openApps: null
  property var launchFeedback: null
  readonly property var prefs: preferences
  DockState { id: preferences }
  readonly property string position: prefs.position
  readonly property bool vertical: Model.isVertical(position)
  readonly property bool autohide: prefs.autohide
  property var order: []
  readonly property var itemModel: model
  readonly property var terminalEntries: {
    var values = DesktopEntries.applications.values
    var out = []
    for (var i = 0; i < values.length; i++) {
      var entry = values[i]
      if (entry.runInTerminal || String(entry.execString || "").indexOf("--app-id=") >= 0)
        out.push({ id: entry.id, execString: entry.execString, command: entry.command, runInTerminal: entry.runInTerminal })
    }
    return out
  }
  function entryForAppId(appId) {
    if (!appId) return null
    var entry = DesktopEntries.heuristicLookup(appId)
    if (entry) return entry
    var id = Model.claimingEntryId(appId, root.terminalEntries)
    return id ? DesktopEntries.byId(id) : null
  }
  readonly property var windows: {
    var rows = []
    var tops = Hyprland.toplevels.values
    for (var i = 0; i < tops.length; i++) {
      var toplevel = tops[i].wayland
      if (!toplevel || !toplevel.appId || toplevel.parent) continue
      var entry = root.entryForAppId(toplevel.appId)
      var workspace = tops[i].workspace
      rows.push({ key: entry ? entry.id : String(toplevel.appId),
        hasEntry: !!entry && !entry.noDisplay,
        workspaceId: workspace ? workspace.id : -1,
        workspaceName: workspace ? String(workspace.name || "") : "",
        minimized: !!workspace && Model.isMinimizedWorkspace(workspace.name),
        activated: !!tops[i].activated, address: String(tops[i].address || "") })
    }
    return rows
  }
  readonly property var installedPins: prefs.pinned.filter(function(id) { return !!DesktopEntries.byId(id) })
  readonly property var items: Model.orderItems(Model.buildItems(installedPins, windows), order)
  readonly property var itemsByKey: {
    var byKey = {}
    for (var i = 0; i < items.length; i++) byKey[items[i].key] = items[i]
    return byKey
  }
  ListModel { id: model }
  onItemsChanged: syncItemModel()
  function shownKeys() { return items.map(function(item) { return item.key }) }
  // Slots are moved, inserted and removed, never rebuilt: a delegate must not be
  // destroyed under the pointer.
  function syncItemModel() {
    var keys = shownKeys()
    for (var i = 0; i < keys.length; i++) {
      if (i < model.count && model.get(i).key === keys[i]) continue
      var found = -1
      for (var j = i + 1; j < model.count; j++) if (model.get(j).key === keys[i]) { found = j; break }
      if (found >= 0) model.move(found, i, 1)
      else model.insert(i, { key: keys[i] })
    }
    if (model.count > keys.length) model.remove(keys.length, model.count - keys.length)
    settleLaunches()
    // Keep the remembered order in step with the visible slots, after this
    // binding pass, so writing it cannot feed back into the same evaluation.
    Qt.callLater(adoptOrder)
  }
  function adoptOrder() {
    var keys = shownKeys()
    if (JSON.stringify(keys) !== JSON.stringify(order)) order = keys
  }
  property var launches: ({})
  readonly property int launchTimeout: 10000
  function isLaunching(key) { return launches[key] !== undefined }
  function settleLaunches() {
    var next = {}
    var changed = false
    var now = Date.now()
    for (var key in launches) {
      var launch = launches[key]
      var item = itemsByKey[key]
      if ((item ? item.windows.length : 0) > launch.windows || now - launch.at > launchTimeout) changed = true
      else next[key] = launch
    }
    if (changed) launches = next
  }
  Timer {
    interval: 1000
    repeat: true
    running: Object.keys(root.launches).length > 0
    onTriggered: root.settleLaunches()
  }
  function itemFor(key) { return itemsByKey[key] || null }
  function entryFor(item) { return item ? DesktopEntries.byId(item.key) : null }
  function iconFor(item) {
    var entry = entryFor(item)
    var icon = entry && entry.icon ? entry.icon : (item ? String(item.key).replace(/\.desktop$/, "") : "")
    return String(icon).charAt(0) === "/" ? "file://" + icon : Quickshell.iconPath(icon, true)
  }
  function launch(item) {
    var entry = entryFor(item)
    if (!entry) return
    var next = Object.assign({}, launches)
    next[item.key] = { at: Date.now(), windows: item.windows.length }
    launches = next
    if (root.launchFeedback) root.launchFeedback.begin(String(entry.name || ""))
    entry.execute()
  }
  function isFloating(id) { return TrialDesktopState.isFloating(id) }
  function readMode(id) {} // Ownership is granted only by this trial's mode switch.
  function isPinned(key) { return prefs.pinned.indexOf(key) >= 0 }
  function setPosition(value) { prefs.setPosition(value) }
  function setAutohide(value) { prefs.setAutohide(value) }
  function saveOrder(keys) { order = keys }
  function placeAt(key, index) {
    if (!key) return
    var keys = Model.orderWithKeyAt(shownKeys(), key, index)
    order = keys
    prefs.setPinned(Model.pinsInOrder(keys, pinnedMap(key), prefs.pinned))
  }
  function pinnedMap(extra) {
    var map = {}
    for (var i = 0; i < prefs.pinned.length; i++) map[prefs.pinned[i]] = true
    if (extra) map[extra] = true
    return map
  }
  function setPinned(key, pinned) {
    if (!key) return
    if (pinned) { placeAt(key, shownKeys().length); return }
    order = shownKeys().filter(function(other) { return other !== key })
    prefs.setPinned(prefs.pinned.filter(function(other) { return other !== key }))
  }
  function moveItem(fromIndex, toIndex) {
    if (fromIndex === toIndex) return
    placeAt(shownKeys()[fromIndex], toIndex)
  }
  function pinAt(key, index) {
    var from = shownKeys().indexOf(key)
    placeAt(key, from >= 0 && from < index ? index - 1 : index)
  }
  // Native window object for a dock entry that only carries primitives.
  function nativeWindow(address) {
    var tops = Hyprland.toplevels.values
    for (var i = 0; i < tops.length; i++) if (String(tops[i].address || "") === address) return tops[i].wayland
    return null
  }
  function windowAddress(window) {
    var address = String(window.address || "")
    return address.indexOf("0x") === 0 ? address : "0x" + address
  }
  function dispatch(script, fallback) {
    if (Hyprland.usingLua) Hyprland.dispatch(script)
    else if (fallback) Hyprland.dispatch(fallback)
  }
  function focusWindow(window) {
    var target = 'window = "address:' + windowAddress(window) + '"'
    dispatch("hl.dsp.focus({ " + target + " })", "focuswindow address:" + windowAddress(window))
    dispatch("hl.dsp.window.alter_zorder({ mode = \"top\", " + target + " })",
             "alterzorder top,address:" + windowAddress(window))
  }
  function restoreMinimized(window) {
    var workspace = Hyprland.focusedWorkspace
    if (!workspace || !(workspace.id >= 1)) return false
    var target = 'window = "address:' + windowAddress(window) + '"'
    dispatch("hl.dsp.window.set_prop({ prop = \"no_anim\", value = \"1\", " + target + " })")
    dispatch("hl.dsp.window.move({ workspace = \"" + workspace.id + "\", " + target + " })",
             "movetoworkspacesilent " + workspace.id + ",address:" + windowAddress(window))
    dispatch("hl.dsp.window.set_prop({ prop = \"no_anim\", value = \"unset\", " + target + " })")
    var tags = window.tags || []
    for (var i = 0; i < tags.length; i++)
      if (String(tags[i]).indexOf("omabuntu-minimized-from-") === 0)
        dispatch("hl.dsp.window.tag({ tag = \"-" + tags[i] + "\", " + target + " })")
    return true
  }
  function activate(item) {
    if (!item) return
    if (item.windows.length === 0) { launch(item); return }
    var workspace = Hyprland.focusedWorkspace
    var index = Model.pickWindow(item.windows.map(function(window) {
      return { workspaceId: window.workspaceId, minimized: window.minimized, activated: window.activated }
    }), workspace ? workspace.id : -1)
    var window = item.windows[index]
    if (!window) return
    if (window.minimized && !restoreMinimized(window)) return
    focusWindow(window)
  }
  // Floating workspaces only, mirroring the upstream minimised-workspace tag.
  function minimize(item) {
    if (!item) return
    var workspace = Hyprland.focusedWorkspace
    if (!workspace || !isFloating(workspace.id)) return
    for (var i = 0; i < item.windows.length; i++) {
      var window = item.windows[i]
      if (window.minimized) continue
      var target = 'window = "address:' + windowAddress(window) + '"'
      dispatch("hl.dsp.window.tag({ tag = \"+omabuntu-minimized-from-" + workspace.id + "\", " + target + " })")
      dispatch("hl.dsp.window.move({ workspace = \"special:minimized\", follow = false, " + target + " })",
               "movetoworkspacesilent special:minimized,address:" + windowAddress(window))
      break
    }
    var current = Hyprland.focusedWorkspace
    if (current && current.id >= 1) dispatch("hl.dsp.focus({ workspace = " + current.id + " })", "workspace " + current.id)
  }
  function toggleMaximized(item) {
    if (!item || item.windows.length === 0) return
    var window = item.windows[0]
    var target = 'window = "address:' + windowAddress(window) + '"'
    dispatch("hl.dsp.window.fullscreen({ mode = \"maximized\", action = \"toggle\", " + target + " })")
    focusWindow(window)
  }
  function quit(item) {
    if (!item) return
    var windows = item.windows.slice()
    for (var i = 0; i < windows.length; i++) {
      var window = nativeWindow(windows[i].address)
      if (window) window.close()
    }
  }
  function dockOn(screen) {
    var windows = docks.instances
    for (var i = 0; i < windows.length; i++) if (windows[i].screen === screen) return windows[i]
    return null
  }
  function moveExternalDrag(screen, x, y) {
    var windows = docks.instances
    for (var i = 0; i < windows.length; i++) {
      if (windows[i].screen === screen) windows[i].moveExternalDrag(x, y)
      else windows[i].endExternalDrag()
    }
  }
  function dropExternalDrag(screen, x, y, key) {
    var target = dockOn(screen)
    if (target) target.dropExternalDrag(x, y, key)
    endExternalDrag()
  }
  function endExternalDrag() {
    var windows = docks.instances
    for (var i = 0; i < windows.length; i++) windows[i].endExternalDrag()
  }
  // Upstream keeps the dock's visibility current through compositor events.
  Connections {
    target: Hyprland
    function onRawEvent(event) {
      var name = event ? String(event.name) : ""
      if (name === "fullscreen" || name === "configreloaded") {
        Hyprland.refreshWorkspaces()
        Hyprland.refreshToplevels()
      }
    }
  }
  Variants {
    id: docks
    model: Quickshell.screens
    DockWindow { required property var modelData; screen: modelData; dock: root }
  }
}
