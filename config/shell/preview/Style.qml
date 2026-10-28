pragma Singleton
import QtQuick
import qs.Commons

// Passive Ubuntu port tokens. No file watchers, probes, or configuration
// writes of its own: the font family binds to the watched state in
// Commons.Color (upstream reads it from its reviewed shell configuration).
QtObject {
  readonly property int cornerRadius: 8
  readonly property int gapsOut: 10
  readonly property real fontScale: 1
  readonly property color hoverFill: Qt.rgba(0.792, 0.800, 0.800, 0.08)
  readonly property bool reduceMotion: false
  readonly property var styleOverrides: Object.freeze({})
  readonly property int normalBorderWidth: 1
  readonly property int hoverBorderWidth: 1
  readonly property int focusBorderWidth: 1
  readonly property int selectedBorderWidth: 0
  readonly property real normalBorderAlpha: 0.4
  readonly property real hoverBorderAlpha: 0.25
  readonly property real focusBorderAlpha: 0.6
  readonly property real selectedBorderAlpha: 0
  readonly property QtObject font: QtObject {
    readonly property string family: Color.fontFamily
    readonly property int body: 12
    readonly property int bodySmall: 11
    readonly property int subtitle: 13
    readonly property int caption: 10
    readonly property int title: 14
    readonly property int display: 24
    readonly property int displayLarge: 32
    readonly property int heading: 18
    readonly property int icon: 14
  }
  readonly property QtObject spacing: QtObject {
    readonly property int popupPadding: 14
    readonly property int controlPaddingX: 10
    readonly property int controlPaddingY: 6
    readonly property int controlGap: 8
    readonly property int controlHeight: 28
    readonly property int xxs: 2
    readonly property int xs: 3
    readonly property int popupRowHeight: 28
    readonly property int sm: 4
    readonly property int md: 6
    readonly property int xl: 10
    readonly property int lg: 8
    readonly property int panelGap: 14
    readonly property int rowGap: 8
    readonly property int rowPaddingX: 12
    readonly property int labelGap: 4
    readonly property int inputPaddingY: 7
    readonly property int hairline: 1
  }
  readonly property QtObject bar: QtObject {
    readonly property int sizeHorizontal: 26
    readonly property int iconSlot: 26
    readonly property int iconCanvas: 26
    readonly property int iconSize: 12
    readonly property int iconFont: 12
    readonly property int statusSlot: 21
  }
  function alpha(color, opacity) { return Qt.rgba(color.r, color.g, color.b, opacity); }
  function normalStateColor(foreground, accent, urgent) { return foreground; }
  function normalBorderFor(foreground, accent, urgent) { return alpha(normalStateColor(foreground, accent, urgent), normalBorderAlpha); }
  function focusStateColor(foreground, accent, urgent) { return foreground; }
  function hoverStateColor(foreground, accent, urgent) { return foreground; }
  function selectedStateColor(foreground, accent, urgent) { return foreground; }
  function normalFillFor(foreground, accent) { return alpha(foreground, 0.04); }
  function pressedFillFor(foreground, accent) { return alpha(foreground, 0.12); }
  function focusFillFor(foreground, accent) { return alpha(foreground, 0.08); }
  function hoverFillFor(foreground, accent) { return alpha(foreground, 0.08); }
  function selectedFillFor(foreground, accent) { return alpha(foreground, 0.18); }
  function selectionFillFor(foreground, accent) { return alpha(foreground, 0.35); }
  function controlFill(focused, hot, foreground, accent) {
    if (focused) return focusFillFor(foreground, accent);
    if (hot) return hoverFillFor(foreground, accent);
    return normalFillFor(foreground, accent);
  }
  function space(value) { return Math.round(value); }
  function spaceReal(value) { return value; }
  function duration(value) { return reduceMotion ? 0 : value; }
}
