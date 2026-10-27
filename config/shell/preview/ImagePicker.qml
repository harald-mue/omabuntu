import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtQuick.Shapes
import QtQuick.Effects
import qs.Commons
import qs.Commons as Commons
import "ImagePickerModel.js" as ImagePickerModel

// Omabuntu image picker: the theme app, derived from Omarchy's pinned
// shell/plugins/image-picker/ImagePicker.qml at commit
// 03ff1eff3812933f7088484533784d2f63eaf19a (MIT; notice preserved in
// licenses/Omarchy-MIT.txt). Ubuntu adaptations, each documented: rows come
// from the reviewed menu helper instead of the upstream switcher and
// listing scripts; theme previews use the imported upstream preview images
// (per-file provenance in upstream/theme-backgrounds.json) with the recorded
// palette chips as the fallback when a theme has no preview; applying
// routes through the helper allowlist instead of detached shell commands;
// no video thumbnails, no theme deletion, no PreviewHold decode warming, no
// background intro or transition snapshots, and keyboard focus is OnDemand
// like the other reviewed surfaces rather than upstream's exclusive grab.
// Nothing closes this picker on a timer.
PanelWindow {
  id: root

  property bool shown: false
  property string mode: ""
  property var imageArray: []
  property int selectedIndex: 0
  property bool imagesLoaded: false
  property bool layoutSettled: false
  property bool neighborImagesEnabled: false
  property string filterText: ""
  property string note: ""
  property int requestSerial: 0
  property string pendingKind: ""
  property var pendingExtra: []
  property string pendingProviderMenu: ""

  // Paint, from the watched theme singleton: the dim color tints
  // unselected slices and text outlines, like upstream's [image-picker].
  readonly property color dimColor: Commons.Color.background
  readonly property color foreground: Commons.Color.foreground
  readonly property color selectedBorder: Commons.Color.accent
  readonly property color unselectedBorder: Commons.Style.alpha(Commons.Color.foreground, 0.4)
  readonly property color noteColor: Commons.Color.urgent
  readonly property string pickerFont: Commons.Style.font.family

  // Carousel geometry from the pinned picker.
  readonly property int expandedWidth: 768
  readonly property int expandedHeight: 475
  readonly property int sliceWidth: 108
  readonly property int sliceHeight: 432
  readonly property int sliceSpacing: -30
  readonly property int skewOffset: 28
  readonly property bool showLabels: true
  readonly property bool filterable: true
  readonly property int bottomChromeHeight: showLabels ? (filterable ? 104 : 74) : (filterable ? 60 : 30)
  readonly property int previewRadius: Math.max(1, Math.min(16,
      Math.ceil((width - expandedWidth) / (2 * (sliceWidth + sliceSpacing))) + 1))
  readonly property var matchingImageIndices: ImagePickerModel.matchingIndices(imageArray, filterText)

  onPreviewRadiusChanged: updateVisibleItems()
  onMatchingImageIndicesChanged: updateVisibleItems()
  onSelectedIndexChanged: updateVisibleItems()
  onShownChanged: if (!shown) {
    layoutSettled = false
    neighborImagesEnabled = false
  }

  visible: shown
  anchors { top: true; bottom: true; left: true; right: true }
  color: "transparent"
  exclusionMode: ExclusionMode.Normal
  exclusiveZone: 0
  WlrLayershell.namespace: "omabuntu-picker"
  WlrLayershell.layer: WlrLayer.Overlay
  WlrLayershell.keyboardFocus: shown ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

  function helperPath() {
    var value = Quickshell.env("OMABUNTU_MENU_HELPER")
    if (value === undefined || value === null) return ""
    var text = String(value)
    if (text.indexOf("/menu_model.py") !== text.length - 14 || text.indexOf(" ") !== -1) return ""
    return text
  }

  function queryHelper(kind, extra) {
    var helper = helperPath()
    if (helper === "") { root.note = "Menu helper is not configured."; return }
    if (proc.running) { root.pendingKind = kind; root.pendingExtra = extra || []; return }
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

  // Upstream loadRows, adapted: rows arrive as JSON from the reviewed
  // helper (label, value, current, colors, image) instead of path tab
  // thumbnail lines. The filter logic in ImagePickerModel stays unchanged
  // and matches against the row value (theme id or file name). In themes
  // mode the thumbnail is the imported theme preview image; a theme
  // without one falls back to the palette chips.
  function loadProviderRows(rows) {
    var entries = []
    var seen = ({})
    var list = Array.isArray(rows) ? rows : []
    for (var i = 0; i < list.length; i++) {
      var row = list[i]
      if (!row || !row.id) continue
      var filePath = String(row.value || "")
      if (!filePath || seen[filePath]) continue
      seen[filePath] = true
      entries.push({
        filePath: filePath,
        fileName: String(row.label || ImagePickerModel.labelForPath(filePath)),
        thumbnailPath: root.mode === "themes" ? String(row.image || "") : filePath,
        rowId: String(row.id),
        current: row.current === true,
        colors: (row.colors && typeof row.colors === "object") ? row.colors : ({})
      })
    }
    root.imageArray = entries
    var next = 0
    for (var j = 0; j < entries.length; j++) if (entries[j].current) { next = j; break }
    root.selectedIndex = ImagePickerModel.nextSelectedIndexForFilter(entries, next, root.filterText)
    root.imagesLoaded = true
    root.layoutSettled = false
    root.neighborImagesEnabled = false
    root.updateVisibleItems()
    Qt.callLater(function() { root.maybeReveal() })
  }

  function finishHelper(kind, serial, text) {
    if (serial !== root.requestSerial || !root.shown) { root.pump(); return }
    var payload = null
    try { payload = JSON.parse(String(text || "")) } catch (error) { payload = null }
    if (!payload || payload.ok !== true) {
      if (kind === "run" && payload && payload.error === "gate")
        root.note = payload.message || "That action is not enabled yet."
      else if (kind === "run")
        root.note = payload && payload.message ? payload.message : "That action did not run."
      else root.note = "The picker could not read its rows."
      root.pump()
      return
    }
    if (kind === "providers") {
      root.loadProviderRows(payload.rows || [])
    } else if (kind === "run") {
      // A theme apply recolors the bar live, so it closes like upstream.
      // A background apply closes once a wallpaper daemon accepted it. Only
      // an unapplied choice keeps the picker open with the recording note.
      if (root.mode === "backgrounds" && payload.applied !== true)
        root.note = "Background recorded. No wallpaper daemon answered (is hyprpaper running?)."
      else root.close()
    }
    root.pump()
  }

  function openMode(nextMode) {
    root.requestSerial += 1
    root.mode = nextMode
    root.filterText = ""
    root.note = ""
    root.imageArray = []
    root.selectedIndex = 0
    root.imagesLoaded = false
    root.layoutSettled = false
    root.neighborImagesEnabled = false
    root.shown = true
    root.updateVisibleItems()
    root.queryHelper("providers", [nextMode === "themes" ? "style.theme" : "style.background"])
    Qt.callLater(function() { if (root.shown) carousel.forceActiveFocus() })
  }

  function openThemes() { root.openMode("themes") }
  function openBackgrounds() { root.openMode("backgrounds") }

  function close() {
    root.requestSerial += 1
    root.shown = false
    root.filterText = ""
    root.note = ""
  }

  function toggleThemes() {
    if (root.shown && root.mode === "themes") root.close()
    else root.openThemes()
  }

  function toggleBackgrounds() {
    if (root.shown && root.mode === "backgrounds") root.close()
    else root.openBackgrounds()
  }

  // Upstream select and selectAdjacent, unchanged.
  function select(index) {
    if (imageArray.length === 0) return
    if (index < 0) index = 0
    else if (index >= imageArray.length) index = imageArray.length - 1
    if (!ImagePickerModel.itemMatches(imageArray, index, filterText)) return
    if (index === selectedIndex) return
    selectedIndex = index
  }

  function selectAdjacent(direction) {
    var count = imageArray.length
    if (count === 0) return
    var index = selectedIndex
    for (var i = 0; i < count; i++) {
      index = (index + direction + count) % count
      if (ImagePickerModel.itemMatches(imageArray, index, filterText)) {
        select(index)
        return
      }
    }
  }

  function updateFilter(nextFilterText) {
    filterText = nextFilterText
    if (!ImagePickerModel.itemMatches(imageArray, selectedIndex, filterText)) {
      var first = ImagePickerModel.nextSelectedIndexForFilter(imageArray, selectedIndex, filterText)
      selectedIndex = Math.max(0, first)
    }
  }

  function applySelected() {
    if (selectedIndex < 0 || selectedIndex >= imageArray.length) return
    var entry = imageArray[selectedIndex]
    if (!entry) return
    root.queryHelper("run", [entry.rowId])
  }

  function updateVisibleItems() {
    ImagePickerModel.syncWindow(visibleImages,
        ImagePickerModel.visibleWindow(matchingImageIndices, selectedIndex, previewRadius))
  }

  // Upstream reveal contract, without its two-frame proof and PreviewHold
  // warming (both documented exclusions): the card renders at opacity 0
  // until every visible preview has settled, with the same 400 ms fallback
  // so a slow decode can not hold a hidden picker.
  function allPreviewsSettled() {
    if (!shown || !imagesLoaded || layoutSettled || imageArray.length === 0 || imageCards.count === 0) return false
    for (var i = 0; i < imageCards.count; i++) {
      var item = imageCards.itemAt(i)
      if (!item || !item.previewSettled) return false
    }
    return true
  }

  function settleReveal() {
    if (!shown || !imagesLoaded || layoutSettled) return
    root.layoutSettled = true
    carousel.forceActiveFocus()
  }

  function maybeReveal() {
    if (!allPreviewsSettled()) return
    Qt.callLater(function() { if (root.allPreviewsSettled()) root.settleReveal() })
  }

  function currentLabel() {
    if (imageArray.length === 0 || !ImagePickerModel.itemMatches(imageArray, selectedIndex, filterText))
      return filterText ? "No matches" : (imagesLoaded ? "Nothing here" : "")
    var entry = imageArray[selectedIndex]
    return entry.fileName
  }

  function handleKey(event) {
    if (event.key === Qt.Key_Escape) {
      if (root.filterText) root.updateFilter("")
      else root.close()
      return true
    }
    if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
      if (root.layoutSettled) root.applySelected()
      return true
    }
    if (event.key === Qt.Key_Left || (event.key === Qt.Key_Tab && (event.modifiers & Qt.ShiftModifier)) || event.key === Qt.Key_Backtab) {
      root.selectAdjacent(-1)
      return true
    }
    if (event.key === Qt.Key_Right || event.key === Qt.Key_Tab) {
      root.selectAdjacent(1)
      return true
    }
    if (event.key === Qt.Key_Backspace) {
      root.updateFilter(root.filterText.slice(0, -1))
      return true
    }
    if (event.text && event.text.length === 1 && event.text.charCodeAt(0) >= 32) {
      root.updateFilter(root.filterText + event.text)
      return true
    }
    return false
  }

  ListModel { id: visibleImages }

  Process {
    id: proc
    property string kind: ""
    property int serial: -1
    stdout: StdioCollector { id: out }
    onExited: function(code) { root.finishHelper(kind, serial, out.text) }
  }

  Rectangle {
    anchors.fill: parent
    color: root.dimColor
    opacity: 0.5
  }

  MouseArea {
    anchors.fill: parent
    onClicked: root.close()
  }

  // The 400 ms upstream fallback: a preview stuck decoding must not hold an
  // invisible picker.
  Timer {
    interval: 400
    running: root.shown && root.imagesLoaded && !root.layoutSettled && root.imageArray.length > 0
    onTriggered: root.settleReveal()
  }

  Item {
    id: card
    visible: root.shown && root.imagesLoaded
    opacity: root.layoutSettled ? 1 : 0
    width: Math.min(parent.width - 80,
        root.expandedWidth + 13 * (root.sliceWidth + root.sliceSpacing) + 40)
    height: root.expandedHeight + Commons.Style.space(30) + root.bottomChromeHeight
    anchors.centerIn: parent

    MouseArea { anchors.fill: parent; enabled: root.layoutSettled; onClicked: function() {} }

    Item {
      id: carousel
      anchors.top: parent.top
      anchors.topMargin: Commons.Style.space(30)
      anchors.bottom: parent.bottom
      anchors.bottomMargin: root.bottomChromeHeight
      anchors.horizontalCenter: parent.horizontalCenter
      width: root.expandedWidth + 13 * (root.sliceWidth + root.sliceSpacing)
      clip: false
      focus: true

      readonly property real itemStep: root.sliceWidth + root.sliceSpacing
      readonly property real previewX: (width - root.expandedWidth) / 2

      Keys.priority: Keys.BeforeItem
      Keys.onPressed: function(event) {
        if (root.handleKey(event)) event.accepted = true
      }

      Component.onCompleted: forceActiveFocus()

      Repeater {
        id: imageCards
        model: visibleImages
        onCountChanged: root.maybeReveal()

        delegate: Item {
          id: item
          required property int imageIndex
          required property int relativeIndex

          readonly property var imageData: root.imageArray[imageIndex]
          readonly property string filePath: imageData ? imageData.filePath : ""
          readonly property string fileName: imageData ? imageData.fileName : ""
          readonly property string thumbnailPath: imageData ? imageData.thumbnailPath : ""
          readonly property var colors: imageData ? imageData.colors : ({})
          readonly property bool selected: imageIndex === root.selectedIndex
          readonly property bool previewReady: image.status === Image.Ready || image.status === Image.Error
          readonly property bool previewSettled: !thumbnailPath || previewReady
          onPreviewSettledChanged: if (previewSettled) root.maybeReveal()
          onSelectedChanged: if (selected && previewReady) root.neighborImagesEnabled = true

          readonly property real readingX: selected ? carousel.previewX
            : (relativeIndex < 0
               ? carousel.previewX + relativeIndex * carousel.itemStep
               : carousel.previewX + root.expandedWidth + root.sliceSpacing + (relativeIndex - 1) * carousel.itemStep)
          x: readingX
          width: selected ? root.expandedWidth : root.sliceWidth
          height: selected ? root.expandedHeight : root.sliceHeight
          y: selected ? 0 : (root.expandedHeight - root.sliceHeight) / 2
          z: selected ? 100 : 50 - Math.min(Math.abs(relativeIndex), 40)

          readonly property real skAbs: Math.abs(root.skewOffset)
          readonly property real topLeft: root.skewOffset >= 0 ? skAbs : 0
          readonly property real topRight: root.skewOffset >= 0 ? width : width - skAbs
          readonly property real bottomRight: root.skewOffset >= 0 ? width - skAbs : width
          readonly property real bottomLeft: root.skewOffset >= 0 ? 0 : skAbs

          Item {
            id: maskShape
            anchors.fill: parent
            visible: false
            layer.enabled: true

            Shape {
              anchors.fill: parent
              antialiasing: true
              preferredRendererType: Shape.CurveRenderer
              ShapePath {
                fillColor: "white"
                strokeColor: "transparent"
                startX: item.topLeft; startY: 0
                PathLine { x: item.topRight; y: 0 }
                PathLine { x: item.bottomRight; y: item.height }
                PathLine { x: item.bottomLeft; y: item.height }
                PathLine { x: item.topLeft; y: 0 }
              }
            }
          }

          Item {
            anchors.fill: parent
            layer.enabled: true
            layer.smooth: true
            layer.effect: MultiEffect {
              maskEnabled: true
              maskSource: maskShape
              maskThresholdMin: 0.3
              maskSpreadAtMin: 0.3
            }

            // The palette rectangle stays the base layer: a theme without
            // an imported preview shows it behind the palette chips, and a
            // background image paints over it once decoded.
            Rectangle {
              anchors.fill: parent
              color: item.colors && item.colors.background
                     ? item.colors.background : root.dimColor
            }

            Image {
              id: image
              visible: item.thumbnailPath !== ""
              anchors.fill: parent
              source: (item.selected || root.neighborImagesEnabled) && item.thumbnailPath
                       ? "file://" + item.thumbnailPath : ""
              sourceSize.width: Math.ceil(root.expandedWidth * Screen.devicePixelRatio)
              sourceSize.height: Math.ceil(root.expandedHeight * Screen.devicePixelRatio)
              fillMode: Image.PreserveAspectCrop
              asynchronous: true
              cache: false
              smooth: true
              opacity: status === Image.Ready ? 1 : 0
              onStatusChanged: if (item.selected && (status === Image.Ready || status === Image.Error))
                root.neighborImagesEnabled = true
            }

            // Palette chips: the fallback theme preview in data form for a
            // theme without an imported preview image.
            Row {
              visible: root.mode === "themes" && !item.thumbnailPath && item.colors && item.colors.accent
              anchors.centerIn: parent
              anchors.verticalCenterOffset: item.selected ? -18 : 0
              spacing: item.selected ? 10 : 3
              property real chipSize: item.selected ? 34 : Math.max(5, Math.floor((item.width - 20) / 15))
              Repeater {
                model: ["accent", "blue", "green", "yellow", "red", "magenta", "cyan"]
                delegate: Rectangle {
                  required property string modelData
                  width: parent.chipSize
                  height: parent.chipSize
                  radius: parent.chipSize / 2
                  color: (item.colors && item.colors[modelData]) ? item.colors[modelData] : root.dimColor
                  border.width: 1
                  border.color: Commons.Style.alpha("#ffffff", 0.12)
                }
              }
            }

            Text {
              visible: root.mode === "themes" && item.selected
              anchors.horizontalCenter: parent.horizontalCenter
              anchors.bottom: parent.bottom
              anchors.bottomMargin: 34
              width: parent.width - 32
              text: item.fileName
              color: (item.colors && item.colors.foreground) ? item.colors.foreground : root.foreground
              font.family: root.pickerFont
              font.pixelSize: 24
              font.weight: Font.DemiBold
              horizontalAlignment: Text.AlignHCenter
              elide: Text.ElideRight
            }

            Rectangle {
              visible: root.mode === "themes"
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.bottom: parent.bottom
              height: 10
              color: (item.colors && item.colors.accent) ? item.colors.accent : root.selectedBorder
            }

            Rectangle {
              anchors.fill: parent
              color: root.dimColor
              opacity: item.selected ? 0 : 0.42
            }
          }

          Shape {
            anchors.fill: parent
            antialiasing: true
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
              fillColor: "transparent"
              strokeColor: item.selected ? root.selectedBorder : root.unselectedBorder
              strokeWidth: item.selected ? 3 : 1
              startX: item.topLeft; startY: 0
              PathLine { x: item.topRight; y: 0 }
              PathLine { x: item.bottomRight; y: item.height }
              PathLine { x: item.bottomLeft; y: item.height }
              PathLine { x: item.topLeft; y: 0 }
            }
          }

          MouseArea {
            anchors.fill: parent
            enabled: root.layoutSettled
            cursorShape: Qt.PointingHandCursor
            onClicked: item.selected ? root.applySelected() : root.select(item.imageIndex)
          }
        }
      }
    }

    Text {
      id: selectedLabel
      visible: root.showLabels
      anchors.top: carousel.bottom
      anchors.topMargin: Commons.Style.space(16)
      anchors.horizontalCenter: carousel.horizontalCenter
      width: root.expandedWidth
      text: root.note ? root.note : root.currentLabel()
      color: root.note ? root.noteColor : root.foreground
      style: Text.Outline
      styleColor: Commons.Style.alpha(root.dimColor, 0.7)
      font.family: root.pickerFont
      font.pixelSize: Commons.Style.font.display
      font.weight: Font.DemiBold
      horizontalAlignment: Text.AlignHCenter
      elide: Text.ElideRight
    }

    Text {
      visible: root.filterable && root.filterText && !root.note
      anchors.top: selectedLabel.bottom
      anchors.topMargin: Commons.Style.space(8)
      anchors.horizontalCenter: carousel.horizontalCenter
      width: root.expandedWidth
      text: root.filterText
      color: root.foreground
      opacity: 0.85
      style: Text.Outline
      styleColor: Commons.Style.alpha(root.dimColor, 0.7)
      font.family: root.pickerFont
      font.pixelSize: Commons.Style.font.title
      horizontalAlignment: Text.AlignHCenter
      elide: Text.ElideRight
    }
  }
}
