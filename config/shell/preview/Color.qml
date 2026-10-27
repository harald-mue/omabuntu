pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Palette for the reviewed port closure. The fixed tokens are the fallback;
// the reviewed theme state written by tools/theme_backend.py under
// ~/.local/state/omabuntu/current/theme.json is loaded at startup and
// watched, so an approved theme change recolors the bar without a restart.
// The applied font family (current/font.txt, written by tools/font_backend.py)
// is watched the same way, so an approved font change restyles the bar text.
// No original Color startup probes, TOML parsing, or user shell.toml layer.
QtObject {
  id: root
  property color foreground: "#cacccc"
  property color background: "#101315"
  property color accent: "#cacccc"
  property color urgent: "#ee8888"
  property color muted: "#707880"

  function hexColor(palette, key, fallback) {
    var value = palette ? palette[key] : undefined
    return (typeof value === "string" && /^#[0-9A-Fa-f]{6}$/.test(value)) ? value : fallback
  }

  function applyTheme(raw) {
    var parsed = null
    try { parsed = JSON.parse(String(raw || "")) } catch (e) { return }
    if (!parsed || parsed.schema_version !== 1 || !parsed.palette) return
    foreground = hexColor(parsed.palette, "foreground", foreground)
    background = hexColor(parsed.palette, "background", background)
    accent = hexColor(parsed.palette, "accent", accent)
    urgent = hexColor(parsed.palette, "red", urgent)
    muted = hexColor(parsed.palette, "muted", muted)
  }

  property FileView themeFile: FileView {
    path: Quickshell.env("HOME") + "/.local/state/omabuntu/current/theme.json"
    watchChanges: true
    printErrors: false
    onLoaded: root.applyTheme(text())
    onLoadFailed: {}
    onFileChanged: reload()
  }

  // The applied font family; the fallback is the upstream default family.
  // One text line; anything longer than a family name is ignored.
  property string fontFamily: "JetBrainsMono Nerd Font"

  function applyFont(raw) {
    var text = String(raw || "").split("\n")[0].replace(/^\s+|\s+$/g, "")
    if (text && text.length <= 128) fontFamily = text
  }

  property FileView fontFile: FileView {
    path: Quickshell.env("HOME") + "/.local/state/omabuntu/current/font.txt"
    watchChanges: true
    printErrors: false
    onLoaded: root.applyFont(text())
    onLoadFailed: {}
    onFileChanged: reload()
  }

  readonly property var shellValues: Object.freeze({})
  readonly property QtObject bar: QtObject {
    readonly property color text: root.foreground
    readonly property color background: root.background
    readonly property color active: root.urgent
  }
  readonly property QtObject popups: QtObject {
    readonly property color text: root.foreground
    readonly property color background: root.background
    readonly property color border: Qt.rgba(0.792, 0.800, 0.800, 0.45)
  }
  readonly property QtObject tooltip: QtObject {
    readonly property color background: root.background
    readonly property color text: root.foreground
    readonly property color border: root.foreground
  }
}
