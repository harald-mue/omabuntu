import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons as Commons
import "MenuModel.js" as MenuModel

// Omabuntu command menu: the derived surface for Super+Space (root menu) and
// Super+Esc (system menu). The structure, geometry, navigation, search,// guard, and provider behavior are derived from Omarchy's pinned
// shell/plugins/menu/Menu.qml at commit 03ff1eff3812933f7088484533784d2f63eaf19a
// (MIT; notice preserved in licenses/Omarchy-MIT.txt). Ubuntu adaptations,
// each documented: the card uses this shell's reviewed palette tokens, the
// definitions come from the reviewed Python helper instead of in-shell
// JSONC file watchers, actions run through that helper's allowlist and gates
// instead of detached shell commands, and the Apps/Keybindings rows route to
// this shell's own surfaces. Nothing closes this card on a timer.
PanelWindow {
  id: root

  // Wiring provided by TrialShell.
  property var openApps: null
  property var openKeybindings: null
  property var openThemes: null
  property var openBackgrounds: null

  property bool shown: false
  property var items: ({})
  property var itemOrder: []
  property var whenResults: ({})
  property var checkedResults: ({})
  property var disabledResults: ({})
  property string activeMenu: "root"
  property string filterText: ""
  property int selectedIndex: 0
  property bool cursorActive: false
  property var navStack: []
  property string note: ""
  property bool loading: false
  property int requestSerial: 0
  property string pendingKind: ""
  property var pendingExtra: []
  property int pendingSerial: 0

  // Geometry and paint from the pinned Menu.qml card. Colors follow the
  // active palette once defs returns; until then they match the bar.
  readonly property int cardWidth: Math.min(activeMenu === "style.font" ? 520 : 300, width - 20)
  readonly property int cornerRadius: 8
  readonly property int contentMargin: 18
  readonly property int headerHeight: 34
  readonly property int baseRowHeight: 50
  readonly property int rowSpacing: 3
  readonly property int rowPeek: Math.round(baseRowHeight * 0.55)
  readonly property int dividerHeight: 17
  property bool searchDivider: false
  property color menuText: "#cacccc"
  property color menuBackground: "#101315"
  property color menuAccent: "#cacccc"
  readonly property color selectedFill: Qt.rgba(menuText.r, menuText.g, menuText.b, 0.08)
  readonly property string rowFont: Commons.Color.fontFamily

  function rowColor(selected) {
    return selected ? root.menuAccent : root.menuText
  }

  visible: shown
  anchors { top: true; bottom: true; left: true; right: true }
  color: "transparent"
  exclusionMode: ExclusionMode.Normal
  exclusiveZone: 0
  WlrLayershell.namespace: "omabuntu-menu"
  WlrLayershell.layer: WlrLayer.Overlay
  WlrLayershell.keyboardFocus: shown ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

  function focusedScreen() {
    var monitor = Hyprland.focusedMonitor
    var screens = Quickshell.screens
    if (!monitor || !screens) return screens ? screens[0] : null
    for (var i = 0; i < screens.length; ++i) {
      var match = Hyprland.monitorFor(screens[i])
      if (match && match.name === monitor.name) return screens[i]
    }
    return screens[0]
  }

  function helperPath() {
    var value = Quickshell.env("OMABUNTU_MENU_HELPER")
    if (value === undefined || value === null) return ""
    var text = String(value)
    if (text.indexOf("/menu_model.py") !== text.length - 14 || text.indexOf(" ") !== -1) return ""
    return text
  }

  function item(id) { return MenuModel.item(root.items, id) }
  function isVisible(entry) { return MenuModel.isVisible(root.items, root.itemOrder, root.whenResults, entry) }
  function isDisabled(entry) { return MenuModel.isDisabled(root.disabledResults, entry) }
  function matchesQuery(entry, query) {
    return MenuModel.matchesQuery(entry, query, root.isVisible(entry) && !root.isDisabled(entry))
  }
  function displayRow(entry, detail, score, section) {
    return MenuModel.displayRow(root.items, root.itemOrder, root.checkedResults, root.disabledResults,
                                entry, detail, score, section)
  }

  function rowSelectable(index) {
    if (index < 0 || index >= displayModel.count) return false
    return !displayModel.get(index).disabled
  }

  function nextSelectable(from, direction) {
    var count = displayModel.count
    if (count === 0) return -1
    var step = direction < 0 ? -1 : 1
    var index = ((from % count) + count) % count
    for (var i = 0; i < count; i++) {
      if (root.rowSelectable(index)) return index
      index = (index + step + count) % count
    }
    return -1
  }

  function settleCursor() {
    var target = root.nextSelectable(root.selectedIndex, 1)
    root.selectedIndex = target >= 0 ? target : 0
    root.cursorActive = target >= 0
  }

  function rebuildDisplay() {
    displayModel.clear()
    root.searchDivider = false
    if (Object.keys(root.items).length === 0) return

    var active = root.item(root.activeMenu) ? root.activeMenu : "root"
    root.activeMenu = active
    var rows = []
    var query = root.filterText.trim()

    if (query) {
      var currentRows = []
      var drilldownRows = []
      for (var i = 0; i < root.itemOrder.length; i++) {
        var entry = root.item(root.itemOrder[i])
        if (!entry || entry.id === "root") continue
        if (!MenuModel.isDescendantOf(root.items, entry.id, active)) continue
        if (!root.matchesQuery(entry, query)) continue
        var detail = MenuModel.parentPathFor(root.items, entry.id)
        var row = root.displayRow(entry, detail, MenuModel.searchScore(root.items, entry, query))
        if (entry.parent === active) currentRows.push(row)
        else drilldownRows.push(row)
      }
      var searchSort = function(a, b) {
        if (a.score !== b.score) return a.score - b.score
        return a.path.localeCompare(b.path)
      }
      currentRows.sort(searchSort)
      drilldownRows.sort(searchSort)
      root.searchDivider = currentRows.length > 0 && drilldownRows.length > 0
      if (root.searchDivider) {
        for (var d = 0; d < drilldownRows.length; d++) drilldownRows[d].section = "drilldown"
      }
      rows = currentRows.concat(drilldownRows)
    } else {
      for (var j = 0; j < root.itemOrder.length; j++) {
        var child = root.item(root.itemOrder[j])
        if (!child || child.parent !== active) continue
        if (!root.isVisible(child)) continue
        rows.push(root.displayRow(child, child.description, child.order))
      }
    }

    for (var k = 0; k < rows.length; k++) displayModel.append(rows[k])
    root.settleCursor()
    Qt.callLater(function() { if (displayModel.count > 0) root.revealCursor() })
  }

  function revealCursor() {
    if (displayModel.count === 0) return
    resultList.positionViewAtIndex(root.selectedIndex, ListView.Contain)
    var listItem = resultList.itemAtIndex(root.selectedIndex)
    if (!listItem) return
    var reach = root.rowPeek + root.rowSpacing
    var maxY = Math.max(resultList.originY, resultList.originY + resultList.contentHeight - resultList.height)
    if (root.selectedIndex < displayModel.count - 1) {
      var overhang = listItem.y + listItem.height + reach - (resultList.contentY + resultList.height)
      if (overhang > 0) resultList.contentY = Math.min(resultList.contentY + overhang, maxY)
    }
    if (root.selectedIndex > 0) {
      var underhang = resultList.contentY - (listItem.y - reach)
      if (underhang > 0) resultList.contentY = Math.max(resultList.contentY - underhang, resultList.originY)
    }
  }

  function select(delta) {
    if (displayModel.count === 0) return
    var from = cursorActive ? selectedIndex + delta : (delta < 0 ? displayModel.count - 1 : 0)
    var target = root.nextSelectable(from, delta)
    if (target < 0) return
    cursorActive = true
    selectedIndex = target
    revealCursor()
  }

  function setFilter(nextFilter) {
    root.filterText = nextFilter
    root.selectedIndex = 0
    root.cursorActive = true
    root.rebuildDisplay()
  }

  function setActiveMenu(id, pushHistory) {
    if (!root.item(id)) id = "root"
    if (pushHistory && id !== root.activeMenu) root.navStack = root.navStack.concat([root.activeMenu])
    root.activeMenu = id
    root.filterText = ""
    root.selectedIndex = 0
    root.cursorActive = true
    root.note = ""
    root.rebuildDisplay()
    if (root.item(id) && root.item(id).provider) root.queryHelper("providers", [id])
  }

  function goBack() {
    if (root.activeMenu === "root") return false
    if (root.navStack.length > 0) {
      var previous = root.navStack[root.navStack.length - 1]
      root.navStack = root.navStack.slice(0, root.navStack.length - 1)
      root.setActiveMenu(previous, false)
      return true
    }
    var active = root.item(root.activeMenu)
    root.setActiveMenu((active && active.parent) ? active.parent : "root", false)
    return true
  }

  function activateIndex(index) {
    if (!root.rowSelectable(index)) return
    var row = displayModel.get(index)
    if (row.kind === "menu" || row.kind === "link") {
      root.setActiveMenu(row.target || row.itemId, true)
    } else if (String(row.action).indexOf("omabuntu-open:") === 0) {
      var route = String(row.action).slice("omabuntu-open:".length)
      if (route === "apps" && root.openApps) root.openApps()
      else if (route === "keybindings" && root.openKeybindings) root.openKeybindings()
      else if (route === "themes" && root.openThemes) root.openThemes()
      else if (route === "backgrounds" && root.openBackgrounds) root.openBackgrounds()
      root.close()
    } else {
      root.queryHelper("run", [row.itemId])
    }
  }

  function handleKey(event) {
    if (event.key === Qt.Key_Escape) {
      if (root.filterText) root.setFilter("")
      else root.close()
      return true
    }
    if (event.key === Qt.Key_Up) { root.select(-1); return true }
    if (event.key === Qt.Key_Down) { root.select(1); return true }
    if (event.key === Qt.Key_PageUp) { root.select(-6); return true }
    if (event.key === Qt.Key_PageDown) { root.select(6); return true }
    if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Right) {
      if (root.cursorActive) root.activateIndex(root.selectedIndex)
      else root.settleCursor()
      return true
    }
    if ((event.key === Qt.Key_Backspace || event.key === Qt.Key_Left) && !root.filterText) {
      root.goBack()
      return true
    }
    if (event.text && event.text.length === 1 && event.text.charCodeAt(0) >= 32) {
      root.setFilter(root.filterText + event.text)
      return true
    }
    if (event.key === Qt.Key_Backspace) {
      root.setFilter(root.filterText.slice(0, -1))
      return true
    }
    return false
  }

  function openRoute(route) {
    root.requestSerial += 1
    root.screen = root.focusedScreen()
    root.filterText = ""
    root.note = ""
    root.navStack = []
    root.activeMenu = MenuModel.resolveRoute(root.items, route)
    if (!root.item(root.activeMenu)) root.activeMenu = "root"
    root.selectedIndex = 0
    root.cursorActive = true
    root.rebuildDisplay()
    root.shown = true
    root.loading = true
    root.queryHelper("defs", [])
    Qt.callLater(function() { if (root.shown) keyCatcher.forceActiveFocus() })
  }

  function toggleRoute(route) {
    var target = MenuModel.resolveRoute(root.items, route)
    if (root.shown && target === root.activeMenu) root.close()
    else root.openRoute(route)
  }

  function close() {
    root.requestSerial += 1
    root.shown = false
    root.filterText = ""
    root.note = ""
    root.navStack = []
  }

  function finishHelper(kind, serial, text) {
    if (serial !== root.requestSerial || !root.shown) { root.pump(); return }
    var payload = null
    try { payload = JSON.parse(String(text || "")) } catch (error) { payload = null }
    if (!payload || payload.ok !== true) {
      if (kind === "run" && payload && payload.error === "gate") root.note = payload.message || "Power actions are not enabled yet."
      else if (kind === "run") root.note = payload && payload.message ? payload.message : "That action did not run."
      else if (kind === "defs") root.note = "Menu definitions could not be read."
      root.pump()
      return
    }
    if (kind === "defs") {
      var palette = payload.palette || ({})
      if (String(palette.background || "").charAt(0) === "#") root.menuBackground = palette.background
      if (String(palette.foreground || "").charAt(0) === "#") root.menuText = palette.foreground
      if (String(palette.accent || "").charAt(0) === "#") root.menuAccent = palette.accent
      root.items = payload.items || ({})
      root.itemOrder = payload.itemOrder || []
      var route = root.activeMenu
      root.activeMenu = "root"
      root.setActiveMenu(MenuModel.resolveRoute(root.items, route), false)
      root.queryHelper("guards", [])
    } else if (kind === "guards") {
      var results = payload.results || {}
      root.whenResults = results.when || ({})
      root.checkedResults = results.checked || ({})
      root.disabledResults = results.disabled || ({})
      root.rebuildDisplay()
    } else if (kind === "providers") {
      root.mergeProviderRows(payload.rows || [], root.pendingProviderMenu)
    } else if (kind === "run") {
      root.close()
    }
    root.pump()
  }

  function queryHelper(kind, extra) {
    var helper = helperPath()
    if (helper === "") { root.note = "Menu helper is not configured."; return }
    if (proc.running) { root.pendingKind = kind; root.pendingExtra = extra || []; root.pendingSerial = root.requestSerial; return }
    var command = ["python3", helper, kind]
    var more = extra || []
    for (var i = 0; i < more.length; ++i) command.push(String(more[i]))
    if (kind === "providers" && more.length > 0) root.pendingProviderMenu = String(more[0])
    proc.kind = kind
    proc.serial = root.requestSerial
    proc.exec(command)
  }

  function pump() {
    if (!root.shown || root.pendingKind === "" || proc.running) return
    var kind = root.pendingKind
    var extra = root.pendingExtra
    root.pendingKind = ""
    root.pendingExtra = []
    root.queryHelper(kind, extra)
  }

  property string pendingProviderMenu: ""

  // Upstream mergeProviderRows, adapted: raw provider rows (label, value,
  // current) become menu entries under the submenu id. The current row gets
  // the check glyph, the others the submenu's own icon. The action stays
  // empty: dispatch re-derives the row by id inside the helper, so the
  // surface never sends a value to run.
  function mergeProviderRows(rawRows, menuId) {
    var spec = root.item(menuId)
    var icon = (spec && spec.icon) || ""
    var taken = ({})
    var providerRows = []
    var rows = Array.isArray(rawRows) ? rawRows : []
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i]
      if (!row || !row.id) continue
      var rowId = row.id
      while (taken[rowId]) rowId += "-"
      taken[rowId] = true
      providerRows.push({
        id: rowId, parent: menuId, kind: "action",
        icon: row.current ? "\u2713" : icon, iconFont: "",
        label: String(row.label || ""), title: "", target: "",
        description: "", action: "", provider: "",
        font: String(row.font || ""),
        aliases: [], searchTerms: [], when: "", checked: "", disabled: "",
        order: 0
      })
    }
    var merged = MenuModel.swapProviderRows(root.items, root.itemOrder, menuId, providerRows)
    root.items = merged.items
    root.itemOrder = merged.itemOrder
    root.rebuildDisplay()
  }

  readonly property string placeholder: {
    var entry = root.item(root.activeMenu)
    var name = (entry && (entry.title || entry.label)) || "Go"
    return name + "\u2026"
  }
  readonly property int contentSpacing: 6
  readonly property int detailRowHeight: 58
  readonly property int maxRowsHeight: Math.floor(height * 0.7)
  readonly property int rowsHeight: Math.min(maxRowsHeight,
      displayModel.count > 0 ? resultList.contentHeight : 0)
  readonly property int cardHeight: Math.min(height - 20,
      contentMargin * 2 + headerHeight + contentSpacing + rowsHeight)

  function rowHeightForDetail(detail) {
    return (root.filterText && detail) ? root.detailRowHeight : root.baseRowHeight
  }

  ListModel { id: displayModel }

  Process {
    id: proc
    property string kind: ""
    property int serial: -1
    stdout: StdioCollector { id: out }
    onExited: function(code) { root.finishHelper(kind, serial, out.text) }
  }

  GlobalShortcut {
    appid: "omabuntu"
    name: "menu"
    description: "Open the command menu"
    onPressed: {
      console.log("OMABUNTU_MENU_PRESSED")
      root.toggleRoute("root")
    }
  }

  GlobalShortcut {
    appid: "omabuntu"
    name: "system"
    description: "Open the system menu"
    onPressed: {
      console.log("OMABUNTU_SYSTEM_PRESSED")
      root.toggleRoute("system")
    }
  }

  Rectangle {
    anchors.fill: parent
    color: root.menuBackground
    opacity: 0.5
  }

  MouseArea {
    anchors.fill: parent
    onClicked: root.close()
  }

  Rectangle {
    id: card
    width: root.cardWidth
    height: root.cardHeight
    anchors.horizontalCenter: parent.horizontalCenter
    y: Math.max(10, Math.round((root.height - height) / 2))
    radius: root.cornerRadius
    color: root.menuBackground
    border.width: 1
    border.color: root.menuText

    MouseArea { anchors.fill: parent; onClicked: function() {} }

    Item {
      id: keyCatcher
      anchors.fill: parent
      focus: true
      Keys.onPressed: function(event) {
        if (root.handleKey(event)) event.accepted = true
      }
    }

    Column {
      anchors.fill: parent
      anchors.margins: root.contentMargin
      spacing: root.contentSpacing

      Rectangle {
        width: parent.width
        height: root.headerHeight
        radius: root.cornerRadius
        color: "transparent"
        Text {
          anchors.fill: parent
          anchors.leftMargin: 10
          anchors.rightMargin: 10
          verticalAlignment: Text.AlignVCenter
          text: root.note ? root.note : (root.filterText || root.placeholder)
          color: root.note ? "#ee8888" : root.menuText
          opacity: root.note || root.filterText ? 1 : 0.58
          font.family: root.rowFont
          font.pixelSize: 16
          elide: Text.ElideRight
        }
      }

      ListView {
        id: resultList
        width: parent.width
        height: root.rowsHeight
        model: displayModel
        clip: true
        spacing: root.rowSpacing
        boundsBehavior: Flickable.StopAtBounds
        section.property: "section"
        section.criteria: ViewSection.FullString
        section.delegate: Item {
          required property string section
          width: ListView.view.width
          height: section === "drilldown" ? root.dividerHeight : 0
          visible: section === "drilldown"
          Rectangle {
            anchors.left: parent.left
            anchors.leftMargin: 4
            anchors.right: parent.right
            anchors.rightMargin: 4
            anchors.verticalCenter: parent.verticalCenter
            height: 1
            color: Qt.rgba(0.792, 0.800, 0.800, 0.2)
          }
        }
        delegate: Rectangle {
          id: row
          required property int index
          required property string itemId
          required property string kind
          required property string icon
          required property string label
          required property string detail
          required property string font
          required property bool disabled
          required property string action
          width: resultList.width
          height: root.rowHeightForDetail(detail)
          radius: root.cornerRadius
          opacity: disabled ? 0.4 : 1
          color: root.cursorActive && root.selectedIndex === row.index
            ? root.selectedFill : "transparent"

          Text {
            visible: row.icon.length > 0
            text: row.icon
            color: root.rowColor(root.cursorActive && root.selectedIndex === row.index)
            font.family: root.rowFont
            font.pixelSize: 18
            width: 36
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            anchors.left: parent.left
            anchors.leftMargin: 8
            anchors.top: parent.top
            anchors.bottom: parent.bottom
          }

          Column {
            anchors.left: parent.left
            anchors.leftMargin: row.icon.length > 0 ? 50 : 18
            anchors.right: parent.right
            anchors.rightMargin: 24
            anchors.verticalCenter: parent.verticalCenter
            spacing: 3
            Text {
              width: parent.width
              text: row.label
              color: root.rowColor(root.cursorActive && root.selectedIndex === row.index)
              font.family: row.font.length > 0 ? row.font : root.rowFont
              font.pixelSize: 16
              font.weight: Font.Medium
              elide: Text.ElideRight
            }
            Text {
              width: parent.width
              visible: root.filterText && row.detail.length > 0
              text: row.detail
              color: root.menuText
              opacity: 0.52
              font.family: root.rowFont
              font.pixelSize: 11
              elide: Text.ElideRight
            }
          }

          Text {
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            visible: row.kind === "menu" || row.kind === "link"
            text: "\u203a"
            color: root.rowColor(root.cursorActive && root.selectedIndex === row.index)
            opacity: 0.36
            font.family: root.rowFont
            font.pixelSize: 16
          }

          MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: row.disabled ? Qt.ArrowCursor : Qt.PointingHandCursor
            onEntered: if (!row.disabled) {
              root.cursorActive = true
              root.selectedIndex = row.index
            }
            onClicked: {
              if (row.disabled) return
              root.cursorActive = true
              root.selectedIndex = row.index
              root.activateIndex(row.index)
            }
          }
        }
      }
    }
  }
}
