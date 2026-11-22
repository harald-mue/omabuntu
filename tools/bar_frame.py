"""Extract original section geometry and keyed widget ownership, never startup."""
from audio_frontend import between, replace
import bar_drag


def derive_ownership(text):
    """Original pool/host borrowing; only prebound trusted Components admitted."""
    pool = between(text, '  component WidgetPool: Item {\n',
                   '  // One widget on a bar surface, loaded from its entry,')
    host = between(text, '  component WidgetHost: Item {\n',
                   "  // A widget's place in its section.")
    choices = between(host, '    readonly property string customType:',
                      '    readonly property real widgetWidth:')
    host = replace(host, choices, '''    readonly property var registryComponent: root.componentForId(moduleName)
    readonly property bool registered: registryComponent !== null
    readonly property var activeItem: registryLoader.item
''')
    host = replace(host, between(host, '    Loader {\n      id: componentLoader',
                                '    Loader {\n      id: registryLoader'), '')
    host = replace(host, between(host, '    Loader {\n      id: qmlLoader',
                                '    onActiveItemChanged:'), '')
    injection = between(host, '    function injectProps() {',
                        '    Component {\n      id: customCommandModuleComponent')
    host = replace(host, injection, '''    function injectProps() {
      var target = activeItem
      // Components bind their reviewed API/settings in the trusted registry.
      // Do not replace those bindings or admit inline settings/command entries.
      if (target && "fixedEdge" in target) target.fixedEdge = fixedEdge
    }

''')
    host = replace(host, '''    Component {
      id: customCommandModuleComponent
      CustomCommandModule { entry: host.entry }
    }
''', '')
    return pool + host + bar_drag.derive_slot(text)


def derive_fullscreen(data):
    """Original observer/refresh, not whole bar startup or compositor dispatch."""
    text = data.decode()
    state = between(text, '    readonly property bool underFullscreen: {\n',
                    '    // Idle, only the strip takes input,')
    state = replace(state, 'var monitor = Hyprland.monitorFor(screen)',
                    'var monitor = screen ? Hyprland.monitorFor(screen) : null')
    refresh = between(text, "  // Hyprland's window list does not follow fullscreen on its own,",
                      '  Variants {\n    model: Quickshell.screens\n\n    delegate: Component {\n      BarPanel {')
    refresh = replace(refresh, '  Connections {\n', '  property Connections eventConnection: Connections {\n')
    refresh = replace(refresh, '    target: Hyprland\n',
                      '    target: Hyprland\n    enabled: root.refreshEvents\n')
    return ('''// Derived from original Omarchy Bar.qml; full MIT notice is in LICENSE.
// Nonvisual fullscreen input ownership only, not visual fade/peek policy.
import QtQuick
import Quickshell.Hyprland
import "Port/BarModel.js" as BarModel

QtObject {
  id: root
  property var screen: null
  property var dragFrame: null
  property bool hidden: false
  property bool refreshEvents: false
  readonly property bool suppressed: hidden || underFullscreen
  // Suppression must win over drag input: never retain an invisible full grab.
  function maskFor(dragging, strip, empty) { return suppressed ? empty : (dragging ? null : strip) }
  function cancelSuppressedDrag() {
    if (suppressed && dragFrame && typeof dragFrame.clearBarDrag === "function") dragFrame.clearBarDrag()
  }
  onSuppressedChanged: cancelSuppressedDrag()
  onDragFrameChanged: cancelSuppressedDrag()
  Component.onCompleted: cancelSuppressedDrag()
''' + state + refresh + '}\n').encode()


def derive_peek(data):
    """Original cross-output tally, API flag and leave hysteresis, no surface."""
    text = data.decode()
    properties = between(text, '  property int barHoverCount: 0\n',
                         '  property int barConfigSerial: 0\n')
    state = between(text, '  function setBarHovered(hovered) {\n',
                    '  function run(command) {\n')
    state = replace(state, '  Timer {\n', '  property Timer leaveDelay: Timer {\n')
    return ('// Derived from pinned MIT Omarchy Bar.qml; full notice in licenses/Omarchy-MIT.txt.\n'
            'import QtQuick\n\nQtObject {\n  id: root\n' + properties + state + '}\n').encode()


def derive_hover(text):
    hover = between(text, '        HoverHandler {\n          readonly property bool peeking:',
                    '      }\n    }\n\n    PopupWindow {\n      id: tooltipWindow')
    hover = replace(hover, '        HoverHandler {\n', '        HoverHandler {\n          id: peekHover\n')
    hover = replace(hover, 'peeking: hovered &&', 'peeking: !root.peekSuppressed && hovered &&')
    hover = replace(hover, 'barWindow.peekEdge', 'root.peekEdge')
    hover = replace(hover, 'root.setBarHovered(peeking)', 'root.setPeekHovered(peeking)')
    hover = replace(hover, 'if (peeking) root.setBarHovered(false)', 'root.setPeekHovered(false)')
    return '\n'.join(line[6:] if line.startswith('      ') else line for line in hover.splitlines()) + '\n'


def derive_frame(data):
    text = data.decode()
    horizontal = between(text, '      Item {\n        anchors.fill: parent\n\n        WidgetPool { id: horizontalPool }',
                         '    Component {\n      id: verticalBar\n')
    if not horizontal.endswith('    }\n\n'):
        raise ValueError('Horizontal frame wrapper differs')
    horizontal = horizontal[:-7]
    horizontal = replace(horizontal, '        CenterModules {\n',
                         '        CenterModules {\n          id: centerModules\n')
    horizontal = horizontal.replace('barWindow.centerBesideRight', 'root.centerBesideRight')
    horizontal = '\n'.join(line[6:] if line.startswith('      ') else line
                           for line in horizontal.splitlines()) + '\n'
    center = between(text, '  component CenterModules: Item {\n',
                     "  // The outline of a dragged widget's room")
    center = replace(center, '    CenterGestureArea { anchors.fill: parent }\n', '')
    center = replace(center, 'window.peekEdge = BarModel.nextPeekEdge(window.peekEdge,',
                     'root.peekEdge = BarModel.nextPeekEdge(root.peekEdge,')
    center = replace(center, '    CenterSections {\n      anchors.fill: parent',
                     '''    readonly property real centerStart: sectionsLayout.centerStart
    readonly property real centerEnd: sectionsLayout.centerEnd

    CenterSections {
      id: sectionsLayout
      anchors.fill: parent''')
    center = replace(center, '    id: sections\n', '''    id: sections
    readonly property real centerStart: beginList.x
    readonly property real centerEnd: endList.x + endList.width
''')
    sides = between(text, '  component LeftModules: ModuleList {\n',
                    '  component CenterModules: Item {\n')
    modules = between(text, '  component ModuleList: GridLayout {\n',
                      "  // The tray section's list, which the tray's slot draws")
    modules = replace(modules, '    columnSpacing: 0\n', '''    columnSpacing: 0
    readonly property real naturalWidth: implicitWidth
    width: region === "left" ? Math.min(naturalWidth, Math.max(0, root.centerStart - 16))
      : region === "right" ? Math.min(naturalWidth, Math.max(0, root.width - root.centerEnd - 16)) : naturalWidth
    height: root.barSize
    clip: region === "left" || region === "right"
''')
    navigation = between(text, '  function layoutEntries(region) {\n',
                         "  // The Nth panel in a bar region,")
    navigation = replace(navigation, '    var serial = barConfigSerial\n', '')
    navigation = replace(navigation, 'if (!item || item.visible !== true || slot.visible !== true',
                         'if (!item || item.visible !== true || item.enabled === false || slot.visible !== true')
    navigation += between(text, '  function switchPanelFrom(owner, direction) {\n',
                          '  // Every live instance of a widget id.')
    navigation += between(text, '  function registerModuleSlot(slot) {\n',
                          '  function registerCenterBox(box) {\n')
    popout = between(text, '  function popoutSectionOf(owner) {\n',
                     '  // Reported by the open panel.')
    popout = replace(popout, 'slot && slot.activeItem === owner',
                     'slot && (slot.activeItem === owner || (slot.activeItem && "widget" in slot.activeItem && slot.activeItem.widget === owner))')
    return ('''// Derived from original Omarchy Bar.qml; full upstream MIT notice in LICENSE.
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

''' + navigation + popout + derive_hover(text) + horizontal + sides + center + modules + derive_ownership(text) + bar_drag.derive_drag(text) + '}\n').encode()
