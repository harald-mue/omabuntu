"""Derive original bar gestures/feedback with closed Ubuntu persistence seams.

All source fragments come from the existing sealed MIT Bar.qml parent. No
startup, arbitrary commands, tray nesting or bar-edge relocation is admitted.
"""
from audio_frontend import between, replace


def derive_slot(text):
    slot = between(text, '  component ModuleSlot: Item {\n',
                   '  component CustomCommandModule: WidgetButton {\n')
    start = '    // The tray section\'s widgets, drawn inside the tray\'s drawer.'
    slot = replace(slot, between(slot, start, '    MouseArea {\n      id: modulePointer'), '')
    slot = replace(slot, '    readonly property bool panelOpen: root.activePopout === slot.activeItem',
                   '''    readonly property var panelOwner: activeItem && "widget" in activeItem ? activeItem.widget : activeItem
    readonly property bool panelOpen: root.activePopout === slot.panelOwner''')
    slot = replace(slot, 'activeItem && "openPanelIndicatorItem" in activeItem ? activeItem.openPanelIndicatorItem : null',
                   'panelOwner && "openPanelIndicatorItem" in panelOwner ? panelOwner.openPanelIndicatorItem : null')
    slot = replace(slot, '"revealProgress" in activeItem ? activeItem.revealProgress : 0',
                   '"revealProgress" in panelOwner ? panelOwner.revealProgress : 0')
    slot = replace(slot, '      id: modulePointer\n',
                   '      id: modulePointer\n      objectName: "bar-module-pointer"\n')
    slot = replace(slot, 'root.shell && typeof root.shell.mutateShellConfig === "function"',
                   'root.layoutEditor !== null && root.layoutEditor.loaded === true')
    slot = replace(slot, 'enabled: slot.visible && slot.widgetWidth > 0 && slot.widgetHeight > 0',
                   'enabled: canReorder && slot.visible && slot.widgetWidth > 0 && slot.widgetHeight > 0')
    # Keep original bodies, with callable seams for contained event fixtures.
    for signal, method in [('onPressed', 'pointerPressed'), ('onPositionChanged', 'pointerMoved'),
                           ('onReleased', 'pointerReleased'), ('onClicked', 'pointerClicked')]:
        slot = replace(slot, '      %s: function(mouse) {' % signal,
                       '      %s: function(mouse) { %s(mouse) }\n      function %s(mouse) {' % (signal, method, method))
    slot = replace(slot, '      onCanceled: {',
                   '      onCanceled: pointerCanceled()\n      function pointerCanceled() {')
    return slot


def derive_drag(text):
    state = between(text, '  property var barDragSource: null\n', '  property bool barMoveActive: false\n')
    state += '  property var barDragExpected: null\n  property var centerBoxes: []\n'
    state += '  readonly property bool traySectionDragActive: false\n'
    state += '  onLayoutWidgetsChanged: if (barDragSource && JSON.stringify(layoutWidgets.sections) !== barDragKeys) Qt.callLater(clearBarDrag)\n'
    helpers = between(text, '  function registerCenterBox(box) {\n', '  function debugBarGeometry() {\n')
    helpers += between(text, '  function sameScreen(left, right) {\n', '  function sameWindow(left, right) {\n')
    helpers += between(text, '  function clearBarDrag() {\n', '  // Split the screen along its diagonals')
    helpers = replace(helpers, '    barDragKeys = ""\n', '    barDragKeys = ""\n    barDragExpected = null\n')
    helpers += between(text, '  function captureBarDragGhost(slot) {\n', '  function requestPopout(owner) {\n')
    drop = between(text, '  function moduleDropAtScene(scenePoint, sourceSlot) {\n',
                   '  // Where a drop lands in the tray\'s drawer section on a bar surface,')
    drop = replace(drop, '''    var drawer = BarModel.traySectionDropTarget(candidates, root.traySectionDropRect(traySlot, sourceWindow), scenePoint, root.vertical, sourceSlot)
    if (drawer) return drawer
''', '    // Nested tray entries are not admitted by the closed Ubuntu registry.\n')
    core = between(text, '  function beginBarDrag(sourceSlot, pressX, pressY) {\n',
                   '  // Writes a layout edit to shell.json.')
    core = replace(core, '    commitBarRemoval()\n', '''    commitBarRemoval()
    if (!layoutEditor || layoutEditor.loaded !== true || !sourceSlot || !sourceSlot.activeItem || moduleSlots.indexOf(sourceSlot) === -1) return
    barDragExpected = JSON.parse(JSON.stringify(layoutConfig))
''')
    core = replace(core, 'targetWindow(sourceSlot.activeItem) || targetWindow(sourceSlot)', 'slotWindow(sourceSlot)')
    core = replace(core, '      keys: barDragKeys\n', '      keys: barDragKeys, expected: barDragExpected\n')
    core = replace(core, '      BarModel.moveEntry(config, move, function(entry) { return Util.normalizeLayoutEntry(entry) })\n    })',
                   '      return BarModel.moveEntry(config, move)\n    }, move.expected)')
    write = between(text, '  function writeLayout(expected, edit) {\n',
                    '  // How far past the bar the drag point sits,')
    write = replace(write, 'function writeLayout(expected, edit)', 'function writeLayout(expected, edit, sourceLayout)')
    write = replace(write, '    if (!root.shell || typeof root.shell.mutateShellConfig !== "function") return',
                    '    if (!layoutEditor || !sourceLayout || typeof layoutEditor.editLayout !== "function") return false')
    write = replace(write, '      root.shell.mutateShellConfig(edit)', '''      var config = {bar: {layout: JSON.parse(JSON.stringify(sourceLayout))}}
      if (!edit(config)) return false
      return layoutEditor.editLayout(sourceLayout, config.bar.layout)''')
    removal = between(text, '  function moduleRemoveDistance(screenPoint) {\n',
                      '  function moduleTargetClickable(target) {\n')
    removal = replace(removal, 'barRemoval = { key: sourceSlot.widgetKey, region: sourceSlot.region, id: entryId(sourceSlot.entry) }',
                      'barRemoval = { key: sourceSlot.widgetKey, region: sourceSlot.region, id: entryId(sourceSlot.entry), expected: barDragExpected }')
    removal = replace(removal, '      BarModel.removeEntry(config, { region: removal.region, index: index, id: removal.id }, function(entry) { return Util.normalizeLayoutEntry(entry) })\n    })',
                      '      return BarModel.removeEntry(config, { region: removal.region, index: index, id: removal.id })\n    }, removal.expected)')
    clicks = between(text, '  function moduleTargetClickable(target) {\n', '  function colorHex(colorValue) {\n')
    clicks = replace(clicks, 'Util.itemContainsPoint(target, slot, localX, localY)',
                     'root.itemContainsPoint(target, slot, localX, localY)')
    outlines = between(text, '  component RoomOutline: BorderSurface {\n', '  component CenterGestureArea: MouseArea {\n')
    ghost = between(text, '  component DragGhostPanel: PanelWindow {\n', '  component BarMoveGhostPanel: PanelWindow {\n')
    ghost = replace(ghost, 'WlrLayershell.namespace: "omarchy-bar-drag-ghost"',
                    'WlrLayershell.namespace: "omabuntu-bar-drag-ghost"')
    ghost = ghost.replace('Util.clamp(', 'root.clamp(')
    ghost += '''  Loader {
    active: root.layoutEditor !== null && root.barWindow !== null && root.barWindow.screen !== null
    sourceComponent: Component {
      DragGhostPanel {
        ghostScreen: root.barWindow ? root.barWindow.screen : null
        screen: ghostScreen
      }
    }
  }
'''
    return state + helpers + drop + core + write + removal + clicks + outlines + ghost
