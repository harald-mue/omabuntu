// Derived from original Omarchy Bar.qml; full upstream MIT notice in LICENSE.
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

Item {
  anchors.fill: parent


  CenterModules {
    id: centerModules
    anchors.fill: parent
    window: barWindow
    drawn: !root.centerBesideRight
  }

  LeftModules {
    window: barWindow
    anchors.left: parent.left
    anchors.leftMargin: Style.space(8)
    anchors.verticalCenter: parent.verticalCenter
  }

  RightModules {
    window: barWindow
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
    readonly property real extent: root.vertical ? boxList.height : boxList.width

    width: root.vertical ? crossSize : extent
    height: root.vertical ? extent : crossSize


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

  }

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
