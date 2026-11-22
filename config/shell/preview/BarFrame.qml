// Derived from original Omarchy Bar.qml; full upstream MIT notice in LICENSE.
// Original horizontal geometry and keyed WidgetPool/WidgetHost ownership.
// Original gestures/feedback with guarded layout writes; no custom modules/startup.
import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import QtQml.Models
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "Port/BarModel.js" as BarModel

Item {
  id: root
  required property var widgetComponents
  required property var layoutConfig
  property var layoutEditor: null
  readonly property bool vertical: false
  readonly property bool centerBesideRight: false
  readonly property int barSize: 26
  property var barWindow: root.QsWindow.window
  property var barApi: null
  property QtObject peekState: null
  property bool peekSuppressed: false
  property real peekEdge: 0
  property var peekOwner: null
  property bool peekHovered: false
  readonly property bool centerSectionRevealHeld: peekState ? peekState.centerSectionRevealHeld : false
  // Idempotent handoff preserves the original tally even on owner replacement
  // or teardown without a pointer leave. No persistence or native action.
  function setPeekHovered(hovered) {
    peekHovered = !!hovered && !peekSuppressed
    var next = peekHovered ? peekState : null
    if (peekOwner === next) return
    var previous = peekOwner
    peekOwner = next
    if (previous && typeof previous.setBarHovered === "function") previous.setBarHovered(false)
    if (next) next.setBarHovered(true)
  }
  onPeekStateChanged: setPeekHovered(peekHovered)
  onPeekSuppressedChanged: if (peekSuppressed) setPeekHovered(false)
  readonly property string position: "top"
  readonly property bool transparent: barApi ? barApi.transparentBar : false
  readonly property color background: barApi ? barApi.background : Commons.Color.bar.background
  readonly property color barForeground: barApi ? barApi.barForeground : Commons.Color.bar.text
  readonly property var activePopout: barApi ? barApi.activePopout : null
  readonly property var clickTargets: barApi ? barApi.clickTargets : []
  function clamp(value, low, high) { return Math.max(low, Math.min(high, value)) }
  function thicknessFor(screen) { return barSize }
  function hideTooltip(owner) { if (barApi) barApi.hideTooltip(owner) }
  function itemContainsPoint(target, source, x, y) {
    return barApi !== null && barApi.itemContainsPoint(target, source, x, y)
  }
  readonly property real centerStart: centerModules.centerStart
  readonly property real centerEnd: centerModules.centerEnd
  property var widgetMemo: ({})
  property var moduleSlots: []
  property var widgetHosts: []
  readonly property var layoutWidgets: BarModel.layoutWidgets(layoutConfig, widgetMemo)
  function entryId(entry) { return BarModel.entryId(entry) }
  function entrySettings(entry) { return BarModel.entrySettings(entry) }
  function componentForId(id) {
    return Object.prototype.hasOwnProperty.call(widgetComponents, id) ? widgetComponents[id] : null
  }
  // Original pure-model edits, submitted with their detached source layout.
  // Pointer/ghost surfaces are not admitted by this API prerequisite.
  function applyLayoutEdit(edit) {
    if (!layoutEditor || typeof layoutEditor.editLayout !== "function") return false
    var expected = JSON.parse(JSON.stringify(layoutConfig))
    var config = {bar: {layout: JSON.parse(JSON.stringify(expected))}}
    if (!edit(config)) return false
    return layoutEditor.editLayout(expected, config.bar.layout)
  }
  function layoutRegion(region) { return region !== "tray" && BarModel.sections.indexOf(region) !== -1 }
  function moveWidget(move) {
    if (!move || !move.from || !move.to || !layoutRegion(move.from.region) || !layoutRegion(move.to.region) || componentForId(move.from.id) === null) return false
    return applyLayoutEdit(function(config) { return BarModel.moveEntry(config, move) })
  }
  function removeWidget(from) {
    if (!from || !layoutRegion(from.region) || componentForId(from.id) === null) return false
    return applyLayoutEdit(function(config) { return BarModel.removeEntry(config, from) })
  }
  function slotWindow(slot) { return slot ? slot.window : null }
  function sameWindow(a, b) {
    if (!a || !b) return false
    return a === b || sameScreen(a.screen, b.screen)
  }
  function widgetForId(id) {
    for (var i = 0; i < widgetHosts.length; i++)
      if (widgetHosts[i].moduleName === id) return widgetHosts[i].activeItem
    return null
  }

  function layoutEntries(region) {
    var entries = layoutConfig ? layoutConfig[region] : null
    return Array.isArray(entries) ? entries : []
  }

  // Tab order for the panels in one bar region, with the three center
  // sections taken as one. Scoped to a single bar surface so tabbing walks the
  // bar the open panel belongs to instead of hopping the panel to another
  // monitor's copy of the same widget.
  function panelNavigationSlots(region, window) {
    var regions = BarModel.navigationRegions(region)
    var slots = []
    for (var r = 0; r < regions.length; r++) {
      var entries = layoutEntries(regions[r])
      for (var i = 0; i < entries.length; i++) {
        var id = entryId(entries[i])
        for (var j = 0; j < moduleSlots.length; j++) {
          var slot = moduleSlots[j]
          if (!slot || slot.region !== regions[r] || slot.moduleName !== id) continue
          if (window && !sameWindow(slotWindow(slot), window)) continue
          var item = slot.activeItem
          if (!item || item.visible !== true || item.enabled === false || slot.visible !== true || slot.width <= 0 || slot.height <= 0) continue
          if (typeof item.open !== "function" || typeof item.close !== "function" || item.opened === undefined) continue
          slots.push(slot)
          break
        }
      }
    }
    return slots
  }

  function switchPanelFrom(owner, direction) {
    if (!owner) return false

    var currentSlot = null
    for (var i = 0; i < moduleSlots.length; i++) {
      var slot = moduleSlots[i]
      if (slot && slot.activeItem === owner) {
        currentSlot = slot
        break
      }
    }
    if (!currentSlot) return false

    var slots = panelNavigationSlots(currentSlot.region, slotWindow(currentSlot))
    if (slots.length < 2) return false

    var currentIndex = -1
    for (var j = 0; j < slots.length; j++) {
      if (slots[j] === currentSlot) {
        currentIndex = j
        break
      }
    }
    if (currentIndex < 0) return false

    var step = direction < 0 ? -1 : 1
    var nextSlot = slots[(currentIndex + step + slots.length) % slots.length]
    if (!nextSlot || !nextSlot.activeItem || nextSlot.activeItem === owner) return false

    nextSlot.activeItem.open()
    return true
  }

  function registerModuleSlot(slot) {
    if (!slot || moduleSlots.indexOf(slot) !== -1) return
    var next = moduleSlots.slice()
    next.push(slot)
    moduleSlots = next
  }

  function unregisterModuleSlot(slot) {
    var next = moduleSlots.filter(function(item) { return item !== slot })
    moduleSlots = next
  }

  function registerWidgetHost(host) {
    if (!host || widgetHosts.indexOf(host) !== -1) return
    widgetHosts = widgetHosts.concat([host])
  }

  function unregisterWidgetHost(host) {
    widgetHosts = widgetHosts.filter(function(item) { return item !== host })
  }

  function popoutSectionOf(owner) {
    for (var i = 0; i < moduleSlots.length; i++) {
      var slot = moduleSlots[i]
      if (slot && (slot.activeItem === owner || (slot.activeItem && "widget" in slot.activeItem && slot.activeItem.widget === owner))) return BarModel.navigationRegions(slot.region).join(" ")
    }
    return ""
  }

  HoverHandler {
    id: peekHover
    readonly property bool peeking: !root.peekSuppressed && hovered && BarModel.peeksAt(point.position, root.peekEdge, root.vertical)
    onPeekingChanged: root.setPeekHovered(peeking)
    // Unplugging a monitor destroys its bar without a leave event, which
    // would strand this surface's tally and hold the peek open for good.
    Component.onDestruction: root.setPeekHovered(false)
  }
Item {
  anchors.fill: parent

  WidgetPool { id: horizontalPool }

  CenterModules {
    id: centerModules
    anchors.fill: parent
    window: barWindow
    pool: horizontalPool
    drawn: !root.centerBesideRight
  }

  LeftModules {
    window: barWindow
    pool: horizontalPool
    anchors.left: parent.left
    anchors.leftMargin: Style.space(8)
    anchors.verticalCenter: parent.verticalCenter
  }

  RightModules {
    window: barWindow
    pool: horizontalPool
    id: rightModules
    anchors.right: parent.right
    anchors.rightMargin: Style.space(8)
    anchors.verticalCenter: parent.verticalCenter
  }

  // Where a display notch covers the middle of the bar, the center
  // sections run on just left of the right one. They keep their regions,
  // so settings pushes, drag and drop, and panel routing still address
  // them. The gap lets a drop at the seam land in the section the pointer
  // is nearer to.
  CenterSections {
    window: barWindow
    pool: horizontalPool
    active: root.centerBesideRight
    besideRight: true
    anchors.right: rightModules.left
    anchors.rightMargin: Style.space(4)
    anchors.top: parent.top
    anchors.bottom: parent.bottom
  }
}
  component LeftModules: ModuleList {
    keys: root.layoutWidgets.sections.left
    region: "left"
    fixedEdge: "start"
  }

  component RightModules: ModuleList {
    keys: root.layoutWidgets.sections.right
    region: "right"
    fixedEdge: "end"
  }

  // The gesture area under the whole bar, with the center sections drawn over
  // it in the middle of it.
  component CenterModules: Item {
    id: centerRoot

    property var window: null
    property var pool: null
    // False where a display notch has moved the center sections beside the
    // right one.
    property bool drawn: true


    readonly property real centerStart: sectionsLayout.centerStart
    readonly property real centerEnd: sectionsLayout.centerEnd

    CenterSections {
      id: sectionsLayout
      anchors.fill: parent
      window: centerRoot.window
      pool: centerRoot.pool
      active: centerRoot.drawn
    }
  }

  // The center box and the two sections hanging off its edges. In the middle
  // of the bar the box is centered, and centerBegin and centerEnd grow away
  // from it. Beside the right section the three run on as one, growing toward
  // the start of the bar. Placed by hand rather than by a Row or Column, which
  // cannot center one child and hang the others off it.
  component CenterSections: Item {
    id: sections
    readonly property real centerStart: beginList.x
    readonly property real centerEnd: endList.x + endList.width

    property var window: null
    property var pool: null
    // Only one set of center sections per bar surface is active; the other
    // shows nothing.
    property bool active: true
    property bool besideRight: false

    implicitWidth: root.vertical ? root.barSize : beginList.width + centerBox.width + endList.width
    implicitHeight: root.vertical ? beginList.height + centerBox.height + endList.height : root.barSize

    // Both placements sit at the bar surface's origin or anchor off its edge,
    // so the box's start in the sections is its start on the surface.
    readonly property real boxStart: root.vertical ? y + centerBox.y : x + centerBox.x
    onBoxStartChanged: syncPeekEdge()
    onActiveChanged: syncPeekEdge()
    onWindowChanged: syncPeekEdge()
    Component.onCompleted: syncPeekEdge()

    function syncPeekEdge() {
      if (active && window) root.peekEdge = BarModel.nextPeekEdge(root.peekEdge, boxStart, root.centerSectionRevealHeld)
    }

    Connections {
      target: root
      function onCenterSectionRevealHeldChanged() { sections.syncPeekEdge() }
    }

    ModuleList {
      id: beginList
      keys: sections.active ? root.layoutWidgets.sections.centerBegin : []
      window: sections.active ? sections.window : null
      pool: sections.pool
      region: "centerBegin"
      fixedEdge: "end"
      x: root.vertical ? Math.round((sections.width - width) / 2) : centerBox.x - width
      y: root.vertical ? centerBox.y - height : Math.round((sections.height - height) / 2)
    }

    ModuleList {
      id: endList
      keys: sections.active ? root.layoutWidgets.sections.centerEnd : []
      window: sections.active ? sections.window : null
      pool: sections.pool
      region: "centerEnd"
      fixedEdge: sections.besideRight ? "end" : "start"
      x: root.vertical ? Math.round((sections.width - width) / 2) : centerBox.x + centerBox.width
      y: root.vertical ? centerBox.y + centerBox.height : Math.round((sections.height - height) / 2)
    }

    CenterBox {
      id: centerBox
      window: sections.window
      pool: sections.pool
      active: sections.active
      fixedEdge: sections.besideRight ? "end" : "center"
      crossSize: root.vertical ? sections.width : sections.height
      x: root.vertical ? 0 : (sections.besideRight ? beginList.width : Math.round((sections.width - width) / 2))
      y: root.vertical ? Math.round((sections.height - height) / 2) : 0
    }
  }

  // The middle of the bar: the center section's widgets, centered as one
  // group. Empty, it takes no room and the sections beside it meet in the
  // middle of the bar. During a drag on its bar it is outlined like the
  // widgets, around what it holds, a spacer for the dragged widget included,
  // and empty it shows as a line across the bar. A drop lands in it anywhere
  // within the bar's thickness of its middle (BarModel.centerDropZone).
  component CenterBox: Item {
    id: box

    property var window: null
    property var pool: null
    property bool active: true
    property string fixedEdge: "center"
    // The bar's thickness: the least length along the bar a drop into the
    // box reaches.
    property real crossSize: 0
    readonly property bool dragHere: active && !!root.barDragSource && root.sameWindow(root.barDragWindow, window)
    readonly property bool dropInto: dragHere && root.barDragRegion === "center"
    readonly property real extent: root.vertical ? boxList.height : boxList.width

    width: root.vertical ? crossSize : extent
    height: root.vertical ? extent : crossSize

    Component.onCompleted: root.registerCenterBox(box)
    Component.onDestruction: root.unregisterCenterBox(box)

    ModuleList {
      id: boxList
      keys: box.active ? root.layoutWidgets.sections.center : []
      window: box.active ? box.window : null
      pool: box.pool
      region: "center"
      fixedEdge: box.fixedEdge
      firstEdge: box.fixedEdge === "center" ? "end" : ""
      lastEdge: box.fixedEdge === "center" ? "start" : ""
      x: Math.round((box.width - width) / 2)
      y: Math.round((box.height - height) / 2)
    }

    DropOutline {
      visible: box.dragHere
      length: box.extent
      dropInto: box.dropInto
      x: root.vertical ? Math.round((box.width - across) / 2) : 0
      y: root.vertical ? 0 : Math.round((box.height - across) / 2)
    }
  }

  component ModuleList: GridLayout {
    id: moduleListRoot

    // The widgets the list shows, by their keys (root.layoutWidgets).
    property var keys: []
    property string region: ""
    // The edge of each module that stays put when the module grows: the side
    // this list is anchored by. The centered box grows both ways.
    property string fixedEdge: "center"
    // The edges the first and last of several modules grow from instead, if
    // not the list's own: the centered box's outer modules grow away from the
    // middle of the bar, as centerBegin's and centerEnd's do
    // (BarModel.slotEdge).
    property string firstEdge: ""
    property string lastEdge: ""
    // The bar surface the list is drawn on, where a drag opens room in it.
    // Null for a list that isn't drawn.
    property var window: null
    // The bar surface's widgets, which the list's slots show (WidgetPool).
    property var pool: null
    // Kept between updates, so a row stays the same object for as long as it
    // is shown (BarModel.sectionRows).
    property var rowMemo: ({})
    readonly property var listRows: BarModel.sectionRows(keys, root.sectionSpacers(region, window), rowMemo)

    visible: listRows.length > 0
    flow: root.vertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
    rowSpacing: 0
    columnSpacing: 0
    readonly property real naturalWidth: implicitWidth
    width: region === "left" ? Math.min(naturalWidth, Math.max(0, root.centerStart - 16))
      : region === "right" ? Math.min(naturalWidth, Math.max(0, root.width - root.centerEnd - 16)) : naturalWidth
    height: root.barSize
    clip: region === "left" || region === "right"

    Repeater {
      // Keyed rows, so a config change or a drag only adds, moves and removes
      // the slots and spacers that changed. A list makes no slots while it is
      // hidden, where they would hold their widgets out of sight, or before it
      // has the pool its slots take their widgets from, as the tray's drawer
      // section until its slot hands it one.
      model: ScriptModel {
        objectProp: "key"
        values: moduleListRoot.visible && moduleListRoot.pool ? moduleListRoot.listRows : []
      }

      delegate: DelegateChooser {
        role: "kind"

        DelegateChoice {
          roleValue: "spacer"

          DragSpacer {
            region: moduleListRoot.region
            window: moduleListRoot.window
          }
        }

        DelegateChoice {
          ModuleSlot {
            required property var modelData
            widgetKey: modelData.key
            region: moduleListRoot.region
            fixedEdge: BarModel.slotEdge(moduleListRoot.keys.length, moduleListRoot.keys.indexOf(modelData.key), moduleListRoot.fixedEdge, moduleListRoot.firstEdge, moduleListRoot.lastEdge)
            pool: moduleListRoot.pool
            window: moduleListRoot.window
          }
        }
      }
    }
  }

  component WidgetPool: Item {
    id: widgetPool

    // Key -> its WidgetHost, and the ModuleSlot showing it.
    property var hosts: ({})
    property var slots: ({})

    width: 0
    height: 0
    clip: true

    // A slot for a key takes its widget, from the pool or from the slot that
    // had it, whichever of the two lists changes first.
    function claim(slot) {
      var key = slot.widgetKey
      var last = slots[key]
      if (last && last !== slot) last.host = null
      slots[key] = slot
      var host = hosts[key] || null
      slot.host = host
      if (host) host.owner = slot
    }

    function release(slot) {
      var key = slot.widgetKey
      if (slots[key] !== slot) return
      delete slots[key]
      slot.host = null
      if (hosts[key]) hosts[key].owner = null
    }

    function addHost(host) {
      hosts[host.key] = host
      var slot = slots[host.key] || null
      host.owner = slot
      if (slot) slot.host = host
    }

    function removeHost(host) {
      if (hosts[host.key] !== host) return
      delete hosts[host.key]
      var slot = slots[host.key]
      if (slot) slot.host = null
    }

    // Keys alone, in a fixed order: a widget's row never moves or changes,
    // and is added and removed with its entry.
    Instantiator {
      model: ScriptModel { values: root.layoutWidgets.keys }
      delegate: WidgetHost { pool: widgetPool }
    }
  }

  component WidgetHost: Item {
    id: host

    required property string modelData
    property var pool: null
    readonly property string key: modelData
    readonly property var entry: root.layoutWidgets.entries[key] || null
    // The slot showing it, set by the pool; null while it waits there.
    property var owner: null
    // Whether a slot has held it yet. The widget is loaded only then, so it
    // knows the edge its section grows from before it has a bar.
    property bool placed: false
    readonly property bool dragSource: !!owner && owner.dragSource
    // The edge it grows from, as the slot that last held it says.
    property string fixedEdge: "center"
    readonly property string moduleName: root.entryId(entry)
    readonly property var moduleSettings: root.entrySettings(entry)
    readonly property var registryComponent: root.componentForId(moduleName)
    readonly property bool registered: registryComponent !== null
    readonly property var activeItem: registryLoader.item
    readonly property real widgetWidth: activeItem && activeItem.visible ? (root.vertical ? root.barSize : activeItem.implicitWidth) : 0
    readonly property real widgetHeight: activeItem && activeItem.visible ? activeItem.implicitHeight : 0

    parent: owner ? owner.widgetHolder : pool
    width: widgetWidth
    height: widgetHeight

    Component.onCompleted: {
      if (pool) pool.addHost(host)
      root.registerWidgetHost(host)
    }
    Component.onDestruction: {
      if (pool) pool.removeHost(host)
      root.unregisterWidgetHost(host)
    }

    // Waiting in the pool, it keeps the edge it had, so a widget handed from
    // one section to another hears only of the edge it lands with.
    onOwnerChanged: {
      if (!owner) {
        unplaced.restart()
        return
      }
      fixedEdge = owner.fixedEdge
      placed = true
    }
    // One no slot takes up again by the time the update is over, as one in
    // the tray's drawer while the tray is off the bar, is unloaded rather
    // than left running where nothing shows it, and loaded again when a slot
    // holds it.
    Timer {
      id: unplaced
      interval: 0
      onTriggered: if (!host.owner) host.placed = false
    }
    Connections {
      target: host.owner
      function onFixedEdgeChanged() { host.fixedEdge = host.owner.fixedEdge }
    }

    Loader {
      id: registryLoader
      active: host.placed && host.registered
      sourceComponent: host.registered ? host.registryComponent : null
      width: host.widgetWidth
      height: host.widgetHeight
      opacity: host.dragSource ? 0.22 : 1.0
      onLoaded: {
        host.injectProps()
        Qt.callLater(host.injectProps)
      }
    }

    onActiveItemChanged: Qt.callLater(injectProps)
    onModuleSettingsChanged: injectProps()
    onFixedEdgeChanged: injectProps()

    function injectProps() {
      var target = activeItem
      // Components bind their reviewed API/settings in the trusted registry.
      // Do not replace those bindings or admit inline settings/command entries.
      if (target && "fixedEdge" in target) target.fixedEdge = fixedEdge
    }

  }

  component ModuleSlot: Item {
    id: slot

    property string widgetKey: ""
    property string region: ""
    property string fixedEdge: "center"
    property var pool: null
    // The bar surface its section is drawn on.
    property var window: null
    // The widget, while the slot holds it (WidgetPool.claim).
    property var host: null
    readonly property var entry: host ? host.entry : null
    readonly property string moduleName: host ? host.moduleName : ""
    readonly property var activeItem: host ? host.activeItem : null
    readonly property bool hovered: moduleHover.hovered
    readonly property bool dragSource: root.barDragSource === slot
    // A widget let go of past the removal threshold leaves the bar the
    // moment its poof starts, though its entry stays in the layout until
    // the poof has played.
    readonly property bool removalPending: root.isPendingRemoval(widgetKey)
    readonly property var panelOwner: activeItem && "widget" in activeItem ? activeItem.widget : activeItem
    readonly property bool panelOpen: root.activePopout === slot.panelOwner
    // Modules bigger than the mark they want (a text label in a padded slot,
    // a multi-line stack on a vertical bar) can say how long the open-panel
    // dot should be along the bar, so it tracks what the module paints
    // instead of a fraction of whatever slot it happens to fill.
    readonly property real panelIndicatorExtent: {
      var mark = panelIndicatorItem
      if (mark) return Math.max(Style.space(10), Math.round((root.vertical ? mark.height : mark.width) * 0.55))
      var key = root.vertical ? "openPanelIndicatorHeight" : "openPanelIndicatorWidth"
      var hint = activeItem && key in activeItem ? activeItem[key] : undefined
      if (hint !== undefined && hint !== null && hint > 0) return Math.round(hint)
      return Math.max(Style.space(10), Math.round((root.vertical ? slot.widgetHeight : slot.widgetWidth) * 0.55))
    }
    // A module holding several things a panel can open from (the tray's
    // icons) names the one whose panel is open, and the mark sits under it
    // rather than under the middle of the module.
    readonly property Item panelIndicatorItem: panelOwner && "openPanelIndicatorItem" in panelOwner ? panelOwner.openPanelIndicatorItem : null
    readonly property real panelIndicatorCenter: {
      var mark = panelIndicatorItem
      if (!mark) return (root.vertical ? widgetArea.height : widgetArea.width) / 2
      // A menu opened while the drawer is still sliding open moves with it;
      // mapToItem alone would not re-run as the item moves.
      var reveal = "revealProgress" in panelOwner ? panelOwner.revealProgress : 0
      var point = mark.mapToItem(widgetArea, mark.width / 2, mark.height / 2)
      return root.vertical ? point.y : point.x
    }
    // The tray, or a clone of it, hosts the tray section in its drawer; one
    // inside the drawer does not, so the section never holds itself.
    readonly property bool hostsTraySection: region !== "tray" && !!activeItem && "sectionHost" in activeItem
    // Its drawer section is outlined while a widget that could go in it is
    // dragged on this bar, as the center box is.
    readonly property bool traySectionShown: hostsTraySection && root.traySectionDragActive && root.sameWindow(root.barDragWindow, window)
    // The part of the section the drawer shows, in the slot's widget area,
    // or null while the drawer hides all of it (the tray's sectionShown).
    readonly property var traySectionGeometry: {
      var shown = hostsTraySection ? activeItem.sectionShown : null
      if (!shown) return null
      return { x: holder.x + shown.x, y: holder.y + shown.y, width: shown.width, height: shown.height }
    }
    // Where the section is now, for a drop: as traySectionGeometry, or for a
    // tray cloned before trays said how much of it shows, the whole section.
    function traySectionNow() {
      if (!hostsTraySection) return null
      if ("sectionShown" in activeItem) return traySectionGeometry
      var area = activeItem.sectionHost
      if (!area) return null
      var point = area.mapToItem(widgetArea, 0, 0)
      return { x: point.x, y: point.y, width: area.width, height: area.height }
    }

    function traySectionContains(x, y) {
      var area = hostsTraySection ? activeItem.sectionHost : null
      if (!area || !area.visible || area.width <= 0 || area.height <= 0) return false
      var point = slot.mapToItem(area, x, y)
      return point.x >= 0 && point.y >= 0 && point.x <= area.width && point.y <= area.height
    }
    readonly property real widgetWidth: host ? host.widgetWidth : 0
    readonly property real widgetHeight: host ? host.widgetHeight : 0
    // Its length along the bar. The dragged widget keeps its place's share
    // of the room: all of it until the room moves away.
    readonly property real alongLength: removalPending ? 0 : dragSource
      ? (root.barDragLengths[root.barDragHome] || 0)
      : (root.vertical ? widgetHeight : widgetWidth)

    // Where the dragged widget lands when it goes back where it was.
    readonly property Item widgetRoom: widgetArea
    // Where the pool puts the widget.
    readonly property Item widgetHolder: holder
    // The section's layout sizes the slot by these, and lines slots up at
    // their start across the bar rather than centering them.
    // Handed to it as preferred sizes, since a layout left to read a size
    // that drops from a fraction of a pixel to nothing keeps the old size,
    // leaving a hole where a widget hid itself.
    implicitWidth: root.vertical ? widgetWidth : alongLength
    implicitHeight: root.vertical ? alongLength : widgetHeight
    Layout.preferredWidth: implicitWidth
    Layout.preferredHeight: implicitHeight
    Layout.alignment: Qt.AlignLeft | Qt.AlignTop
    z: modulePointer.dragging ? 100 : 0

    Component.onCompleted: {
      if (pool) pool.claim(slot)
      root.registerModuleSlot(slot)
    }
    Component.onDestruction: {
      // Later, since a slot goes while its section's model is being changed,
      // which the drag's room feeds.
      if (root.barDragSource === slot) Qt.callLater(root.clearBarDrag)
      if (pool) pool.release(slot)
      root.unregisterModuleSlot(slot)
    }

    HoverHandler { id: moduleHover }

    // The widget at its own size. Lifted out by a drag, it folds away with
    // its room.
    Item {
      id: widgetArea

      width: root.vertical ? slot.widgetWidth : slot.alongLength
      height: root.vertical ? slot.alongLength : slot.widgetHeight
      clip: slot.dragSource || slot.removalPending

      RoomOutline { visible: slot.dragSource }

      // Folding away under a drag, the slot keeps the widget centred, like
      // the copy in the room it opens (DragSpacer).
      Item {
        id: holder
        anchors.centerIn: parent
        width: slot.widgetWidth
        height: slot.widgetHeight
      }

      // The tray section's outline, as the center box's: around what it
      // holds, the room for the dragged widget included, or a line where it
      // holds nothing. Drawn over the tray rather than in its drawer, whose
      // clip would hide an empty section's line.
      DropOutline {
        readonly property var section: slot.traySectionGeometry || { x: 0, y: 0, width: 0, height: 0 }

        visible: slot.traySectionShown && !!slot.traySectionGeometry
        length: root.vertical ? section.height : section.width
        dropInto: root.barDragRegion === "tray"
        x: root.vertical ? Math.round((parent.width - across) / 2) : section.x
        y: root.vertical ? section.y : Math.round((parent.height - across) / 2)
        z: 40
      }

      Rectangle {
        id: openPanelIndicator

        readonly property int inset: Style.space(2)

        visible: opacity > 0
        opacity: slot.panelOpen && !slot.dragSource ? 0.9 : 0
        color: Commons.Color.accent
        radius: Math.min(width, height) / 2
        width: root.vertical ? Style.space(2) : slot.panelIndicatorExtent
        height: root.vertical ? slot.panelIndicatorExtent : Style.space(2)
        // The mark sits on the module's inner edge — the one facing the
        // desktop — so it underlines a top bar, overlines a bottom one, and
        // points inward from a left or right one. It reads as pointing at the
        // panel that opens on that side.
        // Snap toward the start of the slot, matching native glyph rendering.
        x: root.vertical
          ? (root.position === "left" ? parent.width - width - inset : inset)
          : Math.floor(slot.panelIndicatorCenter - width / 2)
        y: root.vertical
          ? Math.floor(slot.panelIndicatorCenter - height / 2)
          : (root.position === "top" ? parent.height - height - inset : inset)
        z: 50

        Behavior on opacity {
          NumberAnimation { duration: Style.duration(120); easing.type: Easing.OutCubic }
        }
      }
    }

    MouseArea {
      id: modulePointer
      objectName: "bar-module-pointer"

      property bool dragging: false
      property bool suppressClick: false
      // This area sits over the slot's widget and takes its press, so the
      // widget never sees itself held; it's told, for its press feedback.
      property var heldTarget: null
      property real pressedX: 0
      property real pressedY: 0
      readonly property bool canReorder: root.layoutEditor !== null && root.layoutEditor.loaded === true
      readonly property real dragThreshold: Style.space(4)

      anchors.fill: parent
      acceptedButtons: Qt.LeftButton
      // Sized by the widget, not the slot, which a drag can shrink to nothing
      // under the pointer that holds it.
      enabled: canReorder && slot.visible && slot.widgetWidth > 0 && slot.widgetHeight > 0
      propagateComposedEvents: true
      // Only the hovered slot needs the hit test; without the guard every
      // slot on every monitor re-ran it on each click target change.
      cursorShape: moduleHover.hovered && root.moduleClickTargetAt(slot, mouseX, mouseY) ? Qt.PointingHandCursor : Qt.ArrowCursor
      // Do not assign drag.target here: the section's layout places
      // ModuleSlot, and moving slot.x/slot.y by hand fights it. The ghost
      // follows the pointer instead.

      onPressed: function(mouse) { pointerPressed(mouse) }
      function pointerPressed(mouse) {
        // A press on a widget in the tray's drawer belongs to that widget's
        // own slot, underneath this one, so it drags that widget, not the tray.
        if (slot.traySectionContains(mouse.x, mouse.y)) {
          mouse.accepted = false
          return
        }
        dragging = false
        suppressClick = false
        pressedX = mouse.x
        pressedY = mouse.y
        hold(root.moduleClickTargetAt(slot, mouse.x, mouse.y), mouse.button)
        root.finishBarSettle()
        root.clearBarDrag()
      }

      function hold(target, button) {
        if (heldTarget && heldTarget !== target && "heldButtons" in heldTarget) heldTarget.heldButtons = Qt.NoButton
        heldTarget = target && "heldButtons" in target ? target : null
        if (heldTarget) heldTarget.heldButtons = button
      }

      onPositionChanged: function(mouse) { pointerMoved(mouse) }
      function pointerMoved(mouse) {
        if (!canReorder || !(mouse.buttons & Qt.LeftButton)) return

        var distance = Math.abs(mouse.x - pressedX) + Math.abs(mouse.y - pressedY)
        if (distance >= dragThreshold) {
          if (!dragging) root.beginBarDrag(slot, pressedX, pressedY)
          dragging = true
          hold(null)
          root.hideTooltip(slot.activeItem)
        }

        // A drag let go of from elsewhere (onLayoutWidgetsChanged) stays let
        // go of until the button comes up.
        if (dragging && root.barDragSource === slot) {
          var scenePoint = slot.mapToItem(null, mouse.x, mouse.y)
          var screenPoint = root.barDragScreenPoint(scenePoint)
          root.barDragSceneX = scenePoint.x
          root.barDragSceneY = scenePoint.y
          root.barDragScreenX = screenPoint.x
          root.barDragScreenY = screenPoint.y

          var drop = root.moduleDropAtScene(scenePoint, slot)
          root.barDragTarget = drop
          root.moveDragRoom(drop)
          root.setBarDragRemoveArmed(!drop && root.moduleRemoveDistance(screenPoint) >= root.barDragRemoveDistance)
        }
      }

      onReleased: function(mouse) { pointerReleased(mouse) }
      function pointerReleased(mouse) {
        var wasDragging = dragging
        hold(null)

        dragging = false

        if (wasDragging) {
          suppressClick = true
          if (root.barDragSource === slot && root.barDragRemoveArmed) root.removeBarDrag(slot)
          else if (root.barDragSource === slot) root.settleBarDrag(slot)
          mouse.accepted = true
        } else {
          root.clearBarDrag()
          mouse.accepted = false
        }
      }

      onCanceled: pointerCanceled()
      function pointerCanceled() {
        dragging = false
        suppressClick = false
        hold(null)
        root.clearBarDrag()
      }

      onClicked: function(mouse) { pointerClicked(mouse) }
      function pointerClicked(mouse) {
        if (suppressClick) {
          suppressClick = false
          mouse.accepted = true
          return
        }

        if (!root.pressModuleClickTarget(slot, mouse.button, mouse.x, mouse.y)) mouse.accepted = false
      }
    }
  }

  property var barDragSource: null
  // Where the dragged widget would land: { slot, after } beside a widget, or
  // { region, after } at an end of a section (see BarModel.centerDropTarget
  // and BarModel.traySectionDropTarget).
  property var barDragTarget: null
  readonly property string barDragRegion: barDragTarget ? (barDragTarget.slot ? barDragTarget.slot.region : barDragTarget.region) : ""
  // Where room is open for the dragged widget (BarModel.dropRoom), and that
  // room's length along the bar.
  property var barDragRoom: null
  property real barDragExtent: 0
  // The room as the dragged widget's ghost draws it: its length along the
  // bar, and across it the widget's own size, as its spacers have.
  readonly property real barDragGhostWidth: vertical ? (barDragSource ? barDragSource.widgetWidth : 0) : barDragExtent
  readonly property real barDragGhostHeight: vertical ? barDragExtent : (barDragSource ? barDragSource.widgetHeight : 0)
  // How much of the room each place holds, keyed "region:index"
  // (BarModel.fadeShares), and so its length there in whole pixels
  // (BarModel.roomLengths). The places holding some of it, as one string,
  // change only as a place opens or closes, so a section's rows aren't worked
  // out again on every frame of a move. The dragged widget's own place is
  // `barDragHome`, where it keeps its room in its slot.
  property var barDragShares: ({})
  readonly property var barDragLengths: BarModel.roomLengths(barDragExtent, barDragShares)
  readonly property string barDragPlaces: Object.keys(barDragShares).filter(function(place) { return barDragShares[place] > 0 }).sort().join(",")
  property string barDragHome: ""
  // The keys each section showed as the drag started (layoutWidgets). They
  // hold while no widget moves about.
  property string barDragKeys: ""
  // The spacers a drag has put in the sections, where a released widget can
  // land (DragSpacer).
  property var dragSpacers: []
  // A released widget's ghost gliding from the pointer to where it lands
  // (settleBarDrag), and how far along it is.
  property var barSettle: null
  property real barSettleProgress: 0
  property var barDragWindow: null
  property var barDragScreen: null
  property url barDragImageUrl: ""
  property real barDragSceneX: 0
  property real barDragSceneY: 0
  property real barDragScreenX: 0
  property real barDragScreenY: 0
  property real barDragOffsetX: 0
  property real barDragOffsetY: 0
  // True once the drag has pulled far enough off the bar that letting go
  // removes the widget instead of moving it. Its room closes meanwhile, as
  // though it were gone already (fadeDragRoom).
  property bool barDragRemoveArmed: false
  // Pulling a widget this far past the bar arms its removal. Generous enough
  // that overshooting a drop keeps reading as a move.
  readonly property real barDragRemoveDistance: Style.spaceReal(48)
  // A widget let go of past that, until its entry is written out of the
  // layout once its poof has played: { key, region, id }.
  property var barRemoval: null
  // The poof a removed widget vanishes in, while it plays: { screen, x, y,
  // width, height, image, seed }, the ghost as it was let go (its center,
  // size and picture) and a seed that lays each poof out a little
  // differently.
  property var barPoof: null
  property var barDragExpected: null
  property var centerBoxes: []
  readonly property bool traySectionDragActive: false
  onLayoutWidgetsChanged: if (barDragSource && JSON.stringify(layoutWidgets.sections) !== barDragKeys) Qt.callLater(clearBarDrag)
  function registerCenterBox(box) {
    if (!box || centerBoxes.indexOf(box) !== -1) return
    centerBoxes = centerBoxes.concat([box])
  }

  function unregisterCenterBox(box) {
    centerBoxes = centerBoxes.filter(function(item) { return item !== box })
  }

  // The center box drawn on a bar surface. Each surface declares one in the
  // middle of the bar and one beside the right section, and draws one of them.
  function centerBoxFor(window) {
    for (var i = 0; i < centerBoxes.length; i++) {
      var box = centerBoxes[i]
      if (box && box.active && root.sameWindow(box.window, window)) return box
    }
    return null
  }

  // Where a drop lands in the box, in scene coordinates. During a drag it
  // takes in any room the box has opened for the dragged widget, so a drop
  // that lands in the box keeps landing there until the pointer leaves that
  // room, and it reaches the bar's thickness at least, so an empty box,
  // which takes no room, can still be hit.
  function centerBoxDropRect(box) {
    if (!box) return null
    try {
      var point = box.mapToItem(null, 0, 0)
      return BarModel.centerDropZone({ x: point.x, y: point.y, width: box.width, height: box.height }, box.crossSize, root.vertical)
    } catch (e) {
      return null
    }
  }

  function sameScreen(left, right) {
    if (!left || !right) return false
    if (left === right) return true
    return !!left.name && !!right.name && left.name === right.name
  }

  function clearBarDrag() {
    barDragSource = null
    barDragWindow = null
    barDragScreen = null
    barDragImageUrl = ""
    barDragTarget = null
    barDragRoom = null
    barDragExtent = 0
    barDragKeys = ""
    barDragExpected = null
    barDragRemoveArmed = false
    barDragRegrab.stop()
    barSettle = null
    barSettleAnimation.stop()
    // The room closes at once: a drop now fills it, and anything else is
    // already back in place.
    barDragShares = {}
    barDragHome = ""
    roomFader.stop()
    barDragSceneX = 0
    barDragSceneY = 0
    barDragScreenX = 0
    barDragScreenY = 0
    barDragOffsetX = 0
    barDragOffsetY = 0
  }

  function windowScreenPoint(scenePoint, window) {
    var x = scenePoint ? scenePoint.x : 0
    var y = scenePoint ? scenePoint.y : 0
    if (!window || !window.screen) return { x: x, y: y }

    if (root.position === "bottom")
      y += Math.max(0, window.screen.height - window.height)
    else if (root.position === "right")
      x += Math.max(0, window.screen.width - window.width)

    return { x: x, y: y }
  }

  function barDragScreenPoint(scenePoint) {
    return windowScreenPoint(scenePoint, barDragWindow)
  }

  function captureBarDragGhost(slot) {
    var item = slot && slot.activeItem ? slot.activeItem : null
    if (!item || typeof item.grabToImage !== "function") return

    var grabWidth = Math.max(1, Math.ceil(slot.widgetWidth))
    var grabHeight = Math.max(1, Math.ceil(slot.widgetHeight))
    item.grabToImage(function(result) {
      if (root.barDragSource !== slot || !result || !result.url) return
      root.barDragImageUrl = result.url
    }, Qt.size(grabWidth, grabHeight))
  }

  function moduleDropAtScene(scenePoint, sourceSlot) {
    var sourceWindow = root.slotWindow(sourceSlot) || root.barDragWindow
    // A drop lands only over the bar strip. The window spans its whole
    // screen, so its own bounds are not the bar's.
    if (moduleRemoveDistance(windowScreenPoint(scenePoint, sourceWindow)) > 0) return null

    // The tray cannot go into its own drawer.
    var intoTraySection = !sourceSlot || !sourceSlot.hostsTraySection
    var traySlot = null
    // Each widget's own room; spacers are not widgets. The dragged widget
    // counts too: over its own room it would land back there, and folded
    // away, it still answers at the point it left, which the section's layout
    // keeps placing.
    var candidates = []
    for (var i = 0; i < moduleSlots.length; i++) {
      var slot = moduleSlots[i]
      if (!slot || !slot.visible || slot.widgetWidth <= 0 || slot.widgetHeight <= 0) continue
      if (sourceWindow && !root.sameWindow(root.slotWindow(slot), sourceWindow)) continue
      if (slot.region === "tray" && !intoTraySection) continue
      if (intoTraySection && slot.hostsTraySection) traySlot = slot

      var slotPoint = { x: slot.x, y: slot.y }
      try {
        slotPoint = slot.mapToItem(null, 0, 0)
      } catch (e) {
      }

      candidates.push({
        slot: slot,
        region: slot.region,
        x: slotPoint.x,
        y: slotPoint.y,
        width: slot.width,
        height: slot.height
      })
    }

    // The tray's drawer section works as the center box does: over it, a
    // drop lands among the widgets in it, or in it, and off it they are out
    // of reach.
    // Nested tray entries are not admitted by the closed Ubuntu registry.
    var onBar = candidates.filter(function(row) { return row.region !== "tray" })
    var box = sourceWindow ? root.centerBoxFor(sourceWindow) : null
    return BarModel.centerDropTarget(onBar, root.centerBoxDropRect(box), scenePoint, root.vertical, sourceSlot)
  }

  function beginBarDrag(sourceSlot, pressX, pressY) {
    // A widget still poofing away is written out first, so the drag starts
    // from the layout as it will be.
    commitBarRemoval()
    if (!layoutEditor || layoutEditor.loaded !== true || !sourceSlot || !sourceSlot.activeItem || moduleSlots.indexOf(sourceSlot) === -1) return
    barDragExpected = JSON.parse(JSON.stringify(layoutConfig))
    var item = sourceSlot.activeItem
    if (item && item.opened === true && typeof item.close === "function") item.close()
    barDragWindow = slotWindow(sourceSlot)
    barDragScreen = barDragWindow ? barDragWindow.screen : null
    barDragOffsetX = pressX
    barDragOffsetY = pressY
    captureBarDragGhost(sourceSlot)
    barDragExtent = Math.ceil(vertical ? sourceSlot.widgetHeight : sourceSlot.widgetWidth)
    startDragRoom(sourceSlot)
    barDragSource = sourceSlot
  }

  // A dragged widget that changes size, as a clock ticking over or the
  // indicator peek does, takes its room and its ghost with it. The ghost's
  // copy of it is taken again once the size settles, rather than on every
  // frame of a widget animating its size.
  function resizeBarDrag() {
    var slot = barDragSource
    if (!slot) return
    var extent = Math.ceil(vertical ? slot.widgetHeight : slot.widgetWidth)
    if (extent === barDragExtent) return
    barDragExtent = extent
    barDragRegrab.restart()
  }

  Timer {
    id: barDragRegrab
    interval: 120
    onTriggered: root.captureBarDragGhost(root.barDragSource)
  }

  Connections {
    target: root.barDragSource
    function onWidgetWidthChanged() { root.resizeBarDrag() }
    function onWidgetHeightChanged() { root.resizeBarDrag() }
  }

  // The room opens where the dragged widget is, which keeps all of it until
  // the room moves away.
  function startDragRoom(sourceSlot) {
    barDragKeys = JSON.stringify(layoutWidgets.sections)
    barDragRoom = BarModel.dropRoom(null, { key: sourceSlot.widgetKey, region: sourceSlot.region }, layoutWidgets.sections, drawnKeys(barDragWindow))
    barDragHome = dragShareKey(barDragRoom)
    var shares = {}
    shares[barDragHome] = 1
    barDragShares = shares
  }

  // Moves the room for the dragged widget to where a drop would land. The
  // place it leaves hands its room over to the new one (fadeDragRoom).
  function moveDragRoom(drop) {
    var source = barDragSource
    if (!source) return
    var next = BarModel.dropRoom(drop, { key: source.widgetKey, region: source.region }, layoutWidgets.sections, drawnKeys(barDragWindow))
    var last = barDragRoom
    barDragRoom = next
    // A widget showing itself just before the dragged one moves where home is.
    if (next.home) barDragHome = dragShareKey(next)
    if (!next || (last && dragShareKey(last) === dragShareKey(next))) return
    fadeDragRoom(0)
    roomFader.start()
  }

  // The keys of the widgets a bar surface draws, as they are now.
  function drawnKeys(window) {
    var drawn = {}
    for (var i = 0; i < moduleSlots.length; i++) {
      var slot = moduleSlots[i]
      if (slot && slot.visible && slot.widgetWidth > 0 && slot.widgetHeight > 0 && sameWindow(slotWindow(slot), window)) drawn[slot.widgetKey] = true
    }
    return drawn
  }

  function dragShareKey(room) {
    return room ? room.region + ":" + room.index : ""
  }

  // A frame of the room moving, at an even pace: a place hands over the
  // whole room in 120ms.
  // Armed for removal, there is no target: every place gives its room up.
  function fadeDragRoom(seconds) {
    var duration = Style.duration(120)
    var step = duration > 0 ? seconds * 1000 / duration : 1
    var target = barDragRemoveArmed ? "" : dragShareKey(barDragRoom)
    barDragShares = BarModel.fadeShares(barDragShares, target, step)
    if (target ? barDragShares[target] >= 1 : Object.keys(barDragShares).length === 0) roomFader.stop()
  }

  FrameAnimation {
    id: roomFader
    onTriggered: root.fadeDragRoom(frameTime)
  }

  // Where a section's list on a bar surface opens room for the dragged
  // widget, while it is dragged on that surface: each place holding some of
  // the room but the dragged widget's own, which keeps its room in its slot.
  function sectionSpacers(region, window) {
    if (!barDragSource || !barDragPlaces || !window || !sameWindow(barDragWindow, window)) return []
    var places = []
    var held = barDragPlaces.split(",")
    for (var i = 0; i < held.length; i++) {
      var split = held[i].lastIndexOf(":")
      if (held[i] !== barDragHome && held[i].slice(0, split) === region) places.push(Number(held[i].slice(split + 1)))
    }
    return places
  }

  function registerDragSpacer(spacer) {
    dragSpacers = dragSpacers.concat([spacer])
  }

  function unregisterDragSpacer(spacer) {
    dragSpacers = dragSpacers.filter(function(item) { return item !== spacer })
  }

  // Where a released widget lands: the room its drop opened, or its own room
  // when it goes back where it was.
  function dropLandingItem(sourceSlot, room) {
    if (!sourceSlot) return null
    if (!room || room.home) return sourceSlot.widgetRoom
    var sourceWindow = slotWindow(sourceSlot) || barDragWindow
    for (var i = 0; i < dragSpacers.length; i++) {
      var spacer = dragSpacers[i]
      if (spacer && spacer.region === room.region && spacer.place === room.index && sameWindow(spacer.window, sourceWindow)) return spacer
    }
    return null
  }

  // Where letting go of the dragged widget now would move its entry
  // (BarModel.moveEntry): to before the widget the room is before, or the end
  // of the section. Null when it would go back where it was.
  function dragMove() {
    var room = barDragRoom
    var source = barDragSource
    if (!room || room.home || !source) return null
    var sections = layoutWidgets.sections
    var count = (sections[room.region] || []).length
    return {
      key: source.widgetKey,
      from: { region: source.region, index: (sections[source.region] || []).indexOf(source.widgetKey), id: entryId(source.entry) },
      to: { region: room.region, index: room.index < count ? room.index : -1 },
      keys: barDragKeys, expected: barDragExpected
    }
  }

  // Lets go of a dragged widget: its ghost glides from the pointer into where
  // it lands, and the move is written once it gets there, so the widget takes
  // its place from where it was let go rather than sliding in from the side.
  function settleBarDrag(sourceSlot) {
    var move = dragMove()
    if (Style.duration(180) === 0) {
      landBarDrag(move)
      return
    }
    barSettle = { source: sourceSlot, move: move, room: move ? barDragRoom : null, fromX: barDragScreenX, fromY: barDragScreenY }
    barSettleProgress = 0
    barSettleAnimation.restart()
  }

  // The ghost follows the landing as it moves, so it arrives where the room
  // ends up even while the room is still moving there. Until the room
  // reaches the landing place, which has no spacer yet, it holds still.
  onBarSettleProgressChanged: {
    var settle = barSettle
    if (!settle) return
    var landing = dropLandingItem(settle.source, settle.room)
    if (!landing) return
    var center = null
    try {
      center = barDragScreenPoint(landing.mapToItem(null, landing.width / 2, landing.height / 2))
    } catch (e) {
      return
    }
    var toX = center.x - barDragGhostWidth / 2 + barDragOffsetX
    var toY = center.y - barDragGhostHeight / 2 + barDragOffsetY
    barDragScreenX = settle.fromX + (toX - settle.fromX) * barSettleProgress
    barDragScreenY = settle.fromY + (toY - settle.fromY) * barSettleProgress
  }

  NumberAnimation {
    id: barSettleAnimation
    target: root
    property: "barSettleProgress"
    from: 0
    to: 1
    duration: Style.duration(180)
    easing.type: Easing.OutCubic
    onFinished: root.finishBarSettle()
  }

  // Lands a settling widget now: when its ghost arrives, or when a new press
  // can't wait for it.
  function finishBarSettle() {
    var settle = barSettle
    if (!settle) return
    barSettle = null
    barSettleAnimation.stop()
    landBarDrag(settle.move)
  }

  // Writes where a dragged widget landed, unless widgets have moved about
  // since the drag started: a write from elsewhere that the drag hasn't let
  // go for yet (onLayoutWidgetsChanged) would put it in the wrong place. Every
  // widget keeps its own instance through the move, the dragged one too,
  // whatever else shares its id (BarModel.layoutWidgets).
  function landBarDrag(move) {
    clearBarDrag()
    if (!move || JSON.stringify(layoutWidgets.sections) !== move.keys) return
    var expected = JSON.parse(move.keys)
    var into = expected[move.to.region]
    var before = move.to.index >= 0 ? into[move.to.index] : null
    expected[move.from.region].splice(move.from.index, 1)
    into.splice(before ? into.indexOf(before) : into.length, 0, move.key)
    writeLayout(expected, function(config) {
      return BarModel.moveEntry(config, move)
    }, move.expected)
  }

  function writeLayout(expected, edit, sourceLayout) {
    if (!layoutEditor || !sourceLayout || typeof layoutEditor.editLayout !== "function") return false
    widgetMemo.expected = expected
    try {
      var config = {bar: {layout: JSON.parse(JSON.stringify(sourceLayout))}}
      if (!edit(config)) return false
      return layoutEditor.editLayout(sourceLayout, config.bar.layout)
    } finally {
      widgetMemo.expected = null
    }
  }

  function moduleRemoveDistance(screenPoint) {
    var screen = barDragScreen
    if (!screen) return 0
    var thickness = thicknessFor(screen)
    var x = screenPoint.x
    var y = screenPoint.y
    if (vertical) {
      if (position === "right") x -= Math.max(0, screen.width - thickness)
      return BarModel.dragDistanceOutside({ x: x, y: y }, thickness, screen.height)
    }
    if (position === "bottom") y -= Math.max(0, screen.height - thickness)
    return BarModel.dragDistanceOutside({ x: x, y: y }, screen.width, thickness)
  }

  // Arming closes the dragged widget's room, and disarming opens it again
  // where a drop would land, as a move of the room does (moveDragRoom).
  function setBarDragRemoveArmed(armed) {
    if (barDragRemoveArmed === armed) return
    barDragRemoveArmed = armed
    fadeDragRoom(0)
    roomFader.start()
  }

  // Lets go of a widget pulled off the bar. It vanishes in a poof where it
  // was let go, its slot closing at once (ModuleSlot.removalPending), and
  // its entry leaves the layout once the poof has played.
  function removeBarDrag(sourceSlot) {
    barRemoval = { key: sourceSlot.widgetKey, region: sourceSlot.region, id: entryId(sourceSlot.entry), expected: barDragExpected }
    // Up before the drag clears, so the ghost's surface never unmaps
    // between the ghost and the poof.
    playPoof()
    clearBarDrag()
    if (!barPoof) commitBarRemoval()
  }

  // Writes a removed widget out of the layout. Every other widget keeps its
  // instance through the write (BarModel.layoutWidgets), as with a move.
  function commitBarRemoval() {
    var removal = barRemoval
    barRemoval = null
    if (!removal) return
    var expected = JSON.parse(JSON.stringify(layoutWidgets.sections))
    var list = expected[removal.region] || []
    var index = list.indexOf(removal.key)
    if (index < 0) return
    list.splice(index, 1)
    writeLayout(expected, function(config) {
      return BarModel.removeEntry(config, { region: removal.region, index: index, id: removal.id })
    }, removal.expected)
  }

  // Bursts out of the ghost where it was let go, so it runs before
  // clearBarDrag wipes the drag. With motion reduced there is nothing to play.
  function playPoof() {
    if (Style.duration(620) === 0) return
    barPoof = {
      screen: barDragScreen,
      x: barDragScreenX - barDragOffsetX + barDragGhostWidth / 2,
      y: barDragScreenY - barDragOffsetY + barDragGhostHeight / 2,
      width: barDragGhostWidth,
      height: barDragGhostHeight,
      image: barDragImageUrl,
      seed: Math.random()
    }
    poofTimer.restart()
  }

  // Outlives the poof's animation a little so its last frames aren't cut
  // off by the ghost's surface unmapping, and only then writes the removal:
  // persisting shell.json stalls the render loop for long enough to swallow
  // a poof still playing.
  Timer {
    id: poofTimer
    interval: Style.duration(620)
    onTriggered: {
      root.barPoof = null
      root.commitBarRemoval()
    }
  }

  function isPendingRemoval(key) {
    return !!barRemoval && barRemoval.key === key
  }

  function moduleTargetClickable(target) {
    return target
      && target.visible !== false
      && target.opacity !== 0
      && target.interactive !== false
      && target.pressable !== false
      && target.concealed !== true
      && typeof target.triggerPress === "function"
  }

  function moduleClickTargetAt(slot, localX, localY) {
    for (var i = clickTargets.length - 1; i >= 0; i--) {
      var target = clickTargets[i]
      if (!moduleTargetClickable(target)) continue

      if (root.itemContainsPoint(target, slot, localX, localY)) {
        return target
      }
    }

    if (moduleTargetClickable(slot.activeItem)) return slot.activeItem
    return null
  }

  function pressModuleClickTarget(slot, button, localX, localY) {
    var target = moduleClickTargetAt(slot, localX, localY)
    if (!target) return false

    target.triggerPress(button)
    return true
  }

  component RoomOutline: BorderSurface {
    anchors.fill: parent
    anchors.margins: Style.space(1)
    color: root.transparent ? "transparent" : root.background
    borderSpec: Border.flat(root.barForeground, 1)
    radius: Math.min(Style.cornerRadius, Math.min(width, height) / 2)
    opacity: root.transparent ? 0.22 : 0.32
  }

  // The outline of a section a drop can go into, the center box or the tray
  // section, during a drag: as wide across the bar as the dragged widget's
  // outline, and `length` along it, or a line where that is nothing.
  component DropOutline: BorderSurface {
    property real length: 0
    property bool dropInto: false
    readonly property real across: Math.max(1, (root.vertical ? root.barDragGhostWidth : root.barDragGhostHeight) - Style.space(1) * 2)

    width: root.vertical ? across : Math.max(1, length)
    height: root.vertical ? Math.max(1, length) : across
    color: "transparent"
    borderSpec: Border.flat(dropInto ? Commons.Color.accent : root.barForeground, 1)
    radius: Math.min(Style.cornerRadius, Math.min(width, height) / 2)
    opacity: dropInto ? 1 : 0.5
  }

  // A section's share of the room a drag has opened at one place, with a
  // faint copy of the dragged widget in it. It lives in the section's model
  // only while the room covers its place, and its length follows the room.
  component DragSpacer: Item {
    id: spacer

    required property var modelData
    property string region: ""
    property var window: null
    readonly property int place: modelData.place
    readonly property var dragged: root.barDragSource
    // How much of the room is open here, along the bar.
    readonly property real length: dragged ? (root.barDragLengths[region + ":" + place] || 0) : 0

    clip: true
    implicitWidth: root.vertical ? (dragged ? dragged.widgetWidth : 0) : length
    implicitHeight: root.vertical ? length : (dragged ? dragged.widgetHeight : 0)
    Layout.preferredWidth: implicitWidth
    Layout.preferredHeight: implicitHeight
    Layout.alignment: Qt.AlignLeft | Qt.AlignTop

    Component.onCompleted: root.registerDragSpacer(spacer)
    Component.onDestruction: root.unregisterDragSpacer(spacer)

    RoomOutline {}

    Image {
      anchors.centerIn: parent
      width: spacer.dragged ? spacer.dragged.widgetWidth : 0
      height: spacer.dragged ? spacer.dragged.widgetHeight : 0
      source: root.barDragImageUrl
      fillMode: Image.Stretch
      smooth: true
      opacity: 0.22
    }
  }

  component DragGhostPanel: PanelWindow {
    id: ghostWindow

    required property var ghostScreen
    readonly property bool active: !!root.barDragSource && root.sameScreen(root.barDragScreen, ghostScreen)
    readonly property var sourceItem: root.barDragSource ? root.barDragSource.activeItem : null
    readonly property bool poofShown: !!root.barPoof && root.sameScreen(root.barPoof.screen, ghostScreen)

    visible: (active && sourceItem !== null) || poofShown
    color: "transparent"
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "omabuntu-bar-drag-ghost"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

    anchors {
      top: true
      bottom: true
      left: true
      right: true
    }

    // Visual-only drag feedback. Keep the input region empty so the ghost can
    // sit under the cursor without stealing the MouseArea's active pointer grab.
    mask: Region {}

    // The widget at its size in the bar, outlined like the room it leaves
    // and the room it would land in (DragSpacer).
    Item {
      visible: ghostWindow.active && ghostWindow.sourceItem !== null
      x: Math.round(root.barDragScreenX - root.barDragOffsetX)
      y: Math.round(root.barDragScreenY - root.barDragOffsetY)
      width: root.barDragGhostWidth
      height: root.barDragGhostHeight
      // Pulled past the removal threshold, the ghost shrinks and dims: let
      // go now and the widget poofs away instead of moving.
      scale: root.barDragRemoveArmed ? 0.82 : 1
      opacity: root.barDragRemoveArmed ? 0.55 : 1

      Behavior on scale { NumberAnimation { duration: Style.duration(140); easing.type: Easing.OutCubic } }
      Behavior on opacity { NumberAnimation { duration: Style.duration(140); easing.type: Easing.OutCubic } }

      RoomOutline { opacity: root.transparent ? 0.45 : 0.94 }

      Image {
        anchors.fill: parent
        source: root.barDragImageUrl
        fillMode: Image.Stretch
        smooth: true
        opacity: 0.84
      }
    }

    // The puff of smoke a widget pulled off the bar vanishes in. Its ghost
    // pops, swelling as it fades, while a cloud billows out of the space it
    // filled and thins away, throwing off a few specks. The cloud takes the
    // widget's own footprint, so a wide widget leaves a wide cloud, and is
    // laid out afresh for each poof so no two look alike.
    Item {
      id: poof

      // 0 to 1 through the poof. Each part runs on its own stretch of it.
      property real progress: 1
      // The poof playing here, kept through its last frames.
      property var spec: ({ x: 0, y: 0, width: 0, height: 0, image: "", seed: 0 })

      readonly property real spanX: Math.max(Style.spaceReal(16), poof.spec.width / 2)
      readonly property real spanY: Math.max(Style.spaceReal(16), poof.spec.height / 2)
      readonly property real puffSize: root.clamp(Math.min(poof.spec.width, poof.spec.height) * 1.1, Style.spaceReal(16), Style.spaceReal(34))
      // Room around the puffs at their furthest, so the blur isn't clipped.
      readonly property real margin: puffSize * 1.4 + Style.spaceReal(16)

      // A steady pseudo-random 0 to 1 for part n of this poof.
      function noise(n) {
        var v = Math.sin(n * 12.9898 + poof.spec.seed * 78.233) * 43758.5453
        return v - Math.floor(v)
      }
      // How far along a part starting `from` and ending `to` is.
      function phase(from, to) {
        return root.clamp((progress - from) / (to - from), 0, 1)
      }
      function outCubic(t) { return 1 - Math.pow(1 - t, 3) }
      function outBack(t) { return 1 + 2.4 * Math.pow(t - 1, 3) + 1.4 * Math.pow(t - 1, 2) }

      visible: ghostWindow.poofShown
      x: Math.round(poof.spec.x)
      y: Math.round(poof.spec.y)

      Connections {
        target: root
        function onBarPoofChanged() {
          if (!root.barPoof || !root.sameScreen(root.barPoof.screen, ghostWindow.ghostScreen)) return
          poof.spec = root.barPoof
          poofAnimation.restart()
        }
      }

      NumberAnimation {
        id: poofAnimation
        target: poof
        property: "progress"
        from: 0
        to: 1
        duration: Style.duration(560)
      }

      // The ghost, picking up as the drag left it.
      Image {
        readonly property real t: poof.outCubic(poof.phase(0, 0.3))

        width: poof.spec.width
        height: poof.spec.height
        x: -width / 2
        y: -height / 2
        source: poof.spec.image
        fillMode: Image.Stretch
        smooth: true
        scale: 0.82 + 0.45 * t
        opacity: 0.84 * 0.55 * (1 - t)
      }

      // Overlapping puffs blurred into one soft cloud, ringed faintly in the
      // bar's background so it reads over light windows and dark alike.
      Item {
        id: cloud

        width: (poof.spanX + poof.margin) * 2
        height: (poof.spanY + poof.margin) * 2
        x: -width / 2
        y: -height / 2
        // Built with the ghost's surface rather than at the release, which
        // would cost the poof its first frames while the effect sets up.
        // Until the poof plays the cloud holds nothing to draw.
        layer.enabled: ghostWindow.visible
        layer.effect: MultiEffect {
          blurEnabled: true
          blur: 0.6
          blurMax: 20
          shadowEnabled: true
          shadowColor: root.background
          shadowBlur: 0.9
          shadowOpacity: 0.7
          shadowHorizontalOffset: 0
          shadowVerticalOffset: 0
        }

        Repeater {
          model: 14

          Rectangle {
            required property int index
            // The first sits in the middle; the rest ring it unevenly.
            readonly property real angle: Math.PI * 2 * (index + poof.noise(index) * 0.7) / 13
            readonly property real reach: index === 0 ? 0 : 0.3 + 0.7 * poof.noise(index + 20)
            readonly property real begin: index === 0 ? 0 : 0.1 * poof.noise(index + 40)
            readonly property real end: 0.82 + 0.18 * poof.noise(index + 60)
            readonly property real t: poof.phase(begin, end)
            // Billows out fast, overshooting a touch, then drifts, rises and
            // swells as it thins, the way smoke spreads.
            readonly property real grow: poof.outBack(Math.min(1, t / 0.4))
            readonly property real size: poof.puffSize * (index === 0 ? 1.25 : 0.6 + 0.55 * poof.noise(index + 80)) * (0.3 + 0.8 * grow + 0.4 * t)
            readonly property real drift: 0.55 + 0.55 * poof.outCubic(t)

            width: size
            height: size
            radius: size / 2
            x: cloud.width / 2 + Math.cos(angle) * poof.spanX * reach * drift - size / 2
            y: cloud.height / 2 + Math.sin(angle) * poof.spanY * reach * drift - Style.spaceReal(10) * poof.outCubic(t) - size / 2
            color: root.barForeground
            // In at once, holding while it billows, thinning away after.
            opacity: Math.min(1, t / 0.08) * (1 - Math.pow(Math.max(0, t - 0.3) / 0.7, 1.4)) * 0.9
          }
        }
      }

      Repeater {
        model: 7

        Rectangle {
          required property int index
          readonly property real angle: Math.PI * 2 * (index + 0.5 + poof.noise(index + 100) * 0.6) / 7
          readonly property real reach: 1.15 + 0.6 * poof.noise(index + 120)
          readonly property real t: poof.phase(0.04, 0.7 + 0.2 * poof.noise(index + 140))
          readonly property real fly: poof.outCubic(t)
          readonly property real size: Style.spaceReal(2) + Style.spaceReal(1.5) * poof.noise(index + 160)

          width: size
          height: size
          radius: size / 2
          x: Math.cos(angle) * (poof.spanX + poof.puffSize * 0.6) * reach * fly - size / 2
          y: Math.sin(angle) * (poof.spanY + poof.puffSize * 0.6) * reach * fly - size / 2
          color: root.barForeground
          opacity: (t > 0 ? 1 : 0) * (1 - t) * 0.9
        }
      }
    }
  }

  Loader {
    active: root.layoutEditor !== null && root.barWindow !== null && root.barWindow.screen !== null
    sourceComponent: Component {
      DragGhostPanel {
        ghostScreen: root.barWindow ? root.barWindow.screen : null
        screen: ghostScreen
      }
    }
  }
}
