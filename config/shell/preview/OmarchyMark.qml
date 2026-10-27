import QtQuick
import QtQuick.Shapes

// The Omarchy menu mark: U+E900 extracted from the pinned upstream
// omarchy.ttf (commit 03ff1eff) with tools/extract_menu_mark.py. The path
// data and its provenance are recorded in upstream/omarchy-mark.json. The
// binary font is not imported; the outline is drawn as a vector shape so
// the mark follows the bar foreground like the upstream font glyph.
// Path coordinate space: x 0..1024, y -1024..0 (font units, y flipped).
Item {
  id: root
  property color color: "#cacccc"

  // The mark fills its em square, so the square edge drives the scale.
  readonly property real markScale: Math.min(width, height) / 1024

  Shape {
    width: 1024
    height: 1024
    transformOrigin: Item.TopLeft
    scale: root.markScale
    // Center the 1024-unit square inside the item.
    x: (root.width - 1024 * root.markScale) / 2
    y: (root.height - 1024 * root.markScale) / 2 + 1024 * root.markScale

    ShapePath {
      fillColor: root.color
      strokeColor: "transparent"
      strokeWidth: 0
      PathSvg {
        path: "M 70 -70 L 549 -70 L 549 0 L 0 0 L 0 -1024 L 1024 -1024 L 1024 0 L 626 0 L 626 -70 L 954 -70 L 954 -954 L 70 -954 Z M 884 -140 L 140 -140 L 140 -884 L 551 -884 L 551 -814 L 210 -814 L 210 -210 L 814 -210 L 814 -814 L 736 -814 L 736 -884 L 884 -884 Z M 471 -140 L 549 -140 L 549 -70 L 471 -70 Z M 473 -954 L 551 -954 L 551 -884 L 473 -884 Z M 0 -551 L 210 -551 L 210 -473 L 0 -473 Z"
      }
    }
  }
}
