"""Extract original horizontal section geometry, without registry/drag/startup."""
from audio_frontend import between, replace


def derive_frame(data):
    text = data.decode()
    horizontal = between(text, "      Item {\n        anchors.fill: parent\n\n        WidgetPool { id: horizontalPool }", "    Component {\n      id: verticalBar\n")
    # Strip only the Component wrapper's closing brace, not the Item's.
    if not horizontal.endswith("    }\n\n"):
        raise ValueError("Horizontal frame wrapper differs")
    horizontal = horizontal[:-7]
    horizontal = replace(horizontal, "        WidgetPool { id: horizontalPool }\n", "")
    if horizontal.count("          pool: horizontalPool\n") != 4:
        raise ValueError("Horizontal frame pool witnesses differ")
    horizontal = horizontal.replace("          pool: horizontalPool\n", "")
    horizontal = replace(horizontal, "        CenterModules {\n", "        CenterModules {\n          id: centerModules\n")
    horizontal = horizontal.replace("barWindow.centerBesideRight", "root.centerBesideRight")
    horizontal = "\n".join(line[6:] if line.startswith("      ") else line for line in horizontal.splitlines()) + "\n"
    # Retain original center group positioning and its two hanging sections.
    center = between(text, "  component CenterModules: Item {\n", "  // The outline of a dragged widget's room")
    center = replace(center, "    CenterGestureArea { anchors.fill: parent }\n", "")
    center = replace(center, "    CenterSections {\n      anchors.fill: parent", "    readonly property real centerStart: sectionsLayout.centerStart\n    readonly property real centerEnd: sectionsLayout.centerEnd\n\n    CenterSections {\n      id: sectionsLayout\n      anchors.fill: parent")
    center = replace(center, "    id: sections\n", "    id: sections\n    readonly property real centerStart: beginList.x\n    readonly property real centerEnd: endList.x + endList.width\n")
    center = replace(center, "    readonly property bool dragHere: active && !!root.barDragSource && root.sameWindow(root.barDragWindow, window)\n", "")
    center = replace(center, '    readonly property bool dropInto: dragHere && root.barDragRegion === "center"\n', "")
    center = replace(center, "    Component.onCompleted: root.registerCenterBox(box)\n    Component.onDestruction: root.unregisterCenterBox(box)\n", "")
    start = "    DropOutline {\n      visible: box.dragHere\n"
    if center.count(start) != 1 or not center.endswith("  }\n\n"):
        raise ValueError("Center drag outline boundary differs")
    center = center[:center.index(start)] + "  }\n"
    return ('''// Derived from original Omarchy Bar.qml; full upstream MIT notice in LICENSE.
// Original horizontal/center section geometry. Top only; no drag, notch policy,
// plugin registry, commands, file IO or dynamic module URLs are admitted.
import QtQuick
import Quickshell
import qs.Commons

Item {
  id: root
  required property Component leftContent
  required property Component centerContent
  required property Component rightContent
  property Component centerBeginContent: null
  property Component centerEndContent: null
  readonly property bool vertical: false
  readonly property bool centerBesideRight: false
  readonly property int barSize: 26
  readonly property var barWindow: root.QsWindow.window
  readonly property real centerStart: centerModules.centerStart
  readonly property real centerEnd: centerModules.centerEnd
  readonly property var layoutWidgets: ({sections:{
    left:leftContent?[1]:[],right:rightContent?[1]:[],
    center:centerContent?[1]:[],centerBegin:centerBeginContent?[1]:[],centerEnd:centerEndContent?[1]:[]}})

''' + horizontal + '''
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

''' + center + '''
  // Fixed trusted component slots replace the original WidgetPool/registry.
  // No source URL, command module or persistent layout mutation is supported.
  component ModuleList: Loader {
    property var keys: []
    property var window: null
    property var pool: null
    property string region: ""
    property string fixedEdge: ""
    property string firstEdge: ""
    property string lastEdge: ""
    active: keys.length > 0
    sourceComponent: region === "left" ? root.leftContent
      : region === "right" ? root.rightContent
      : region === "centerBegin" ? root.centerBeginContent
      : region === "centerEnd" ? root.centerEndContent : root.centerContent
    readonly property real naturalWidth: item ? item.implicitWidth : 0
    width: region === "left" ? Math.min(naturalWidth, Math.max(0, root.centerStart - 16))
      : region === "right" ? Math.min(naturalWidth, Math.max(0, root.width - root.centerEnd - 16)) : naturalWidth
    height: root.barSize
    clip: region === "left" || region === "right"
  }
}
''').encode()
