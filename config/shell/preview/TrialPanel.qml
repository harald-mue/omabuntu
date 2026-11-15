import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "Elsewhen"
import "Weather"
import "BarRun.js" as BarRun

// One top bar per screen, with source-derived original section geometry.
// Registry, gestures, theme IO and per-monitor workspace policy are not loaded.
Variants {
  id: bars
  // Left-edge menu button route opener, wired by TrialShell to CommandMenu.
  property var openMenu: null
  property var appearance: null
  // Shared persistent clock entry when the preference adapter is available.
  // Persisted updates retain the shared binding on every screen.
  property var clockSettings: appearance && appearance.loaded
    ? Object.assign({}, appearance.bar.clock_settings, {format: appearance.bar.clock_format})
    : ({format: "dddd HH:mm"})
  // Bar background look, read from the reviewed state file
  // (~/.local/state/omabuntu/current/bar.json): opaque, glassy or none.
  // The shared adapter writes through the reviewed transactional helper.
  property string backgroundLook: appearance && appearance.loaded ? appearance.bar.background : "opaque"
  // Mirrors the on-disk bar-off flag so the user can hide the bar without
  // killing the shell. Hidden bars park off-screen without an exclusion
  // zone (upstream Bar.qml probe and toggles-directory watch).
  property bool legacyBarHidden: false
  readonly property bool barHidden: appearance && appearance.loaded ? appearance.bar.hidden : legacyBarHidden

  function applyBarState(raw) {
    if (appearance) { appearance.refresh(); return }
    var parsed = null
    try { parsed = JSON.parse(String(raw || "")) } catch (e) { return }
    if (!parsed || parsed.schema_version !== 1) return
    var look = String(parsed.background || "")
    if (look === "opaque" || look === "glassy" || look === "none") backgroundLook = look
  }

  property FileView barStateFile: FileView {
    path: (Quickshell.env("OMABUNTU_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state/omabuntu")) + "/current/bar.json"
    watchChanges: true
    printErrors: false
    onLoaded: bars.applyBarState(text())
    // Removing a newly created preference file is a valid exact rollback.
    // Refresh even when reloading that now-absent file fails.
    onLoadFailed: if (bars.appearance) bars.appearance.refresh()
    onFileChanged: reload()
  }

  // Presence of the bar-off flag = bar hidden. Watching the parent toggles
  // directory because FileView cannot observe a file that does not exist yet.
  property Process barHiddenProbe: Process {
    command: ["bash", "-c", "[[ -f $HOME/.local/state/omabuntu/toggles/bar-off ]] && echo yes || echo no"]
    stdout: StdioCollector { onStreamFinished: {
      bars.legacyBarHidden = String(text || "").trim() === "yes"
      if (bars.appearance) bars.appearance.refresh()
    } }
    running: true
  }
  property FileView togglesDirFile: FileView {
    path: Quickshell.env("HOME") + "/.local/state/omabuntu/toggles"
    watchChanges: true
    printErrors: false
    onFileChanged: bars.barHiddenProbe.running = true
    onLoadFailed: {}
  }

  model: Quickshell.screens
  PanelWindow {
    required property var modelData
    screen: modelData
    anchors { top: true; left: true; right: true }
    implicitHeight: 26
    // Hiding parks the bar just past the screen edge instead of unmapping
    // it, so a reveal is a margin change (upstream BarPanel behavior).
    margins { top: bars.barHidden ? -26 : 0 }
    exclusionMode: bars.barHidden ? ExclusionMode.Ignore : ExclusionMode.Auto
    // Preferences load after creation. Keep an alpha buffer even when the
    // initial Opaque default would otherwise permanently select an opaque surface.
    surfaceFormat.opaque: false
    color: clockBar.transparentBar ? "transparent" : (clockBar.glassy ? clockBar.glassBackground : clockBar.themeBackground)
    WlrLayershell.namespace: "omabuntu-clock-trial"
    WlrLayershell.layer: WlrLayer.Top
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand

    QtObject {
      id: barBus
      property var activePopout: null
      property var clickTargets: []
      property var panels: ({})
      readonly property var panelGroups: [
        ["clock", "elsewhen", "weather"],
        ["bluetooth", "network", "audio", "display", "power"]
      ]
      function registerPanel(key, item) {
        if (!panelGroups.some(function(group) { return group.indexOf(key) >= 0 })) return
        var next = Object.assign({}, panels)
        next[key] = item
        panels = next
      }
      function unregisterPanel(key, item) {
        if (panels[key] !== item) return
        var next = Object.assign({}, panels)
        delete next[key]
        panels = next
      }
      function switchPanelFrom(owner, direction) {
        for (var g = 0; g < panelGroups.length; g++) {
          var candidates = panelGroups[g].map(function(key) { return panels[key] }).filter(function(item) {
            return item && item.visible && item.enabled && item.width > 0 && item.height > 0
              && typeof item.open === "function" && typeof item.close === "function"
          })
          var index = candidates.indexOf(owner)
          if (index < 0) continue
          if (candidates.length < 2) return false
          candidates[(index + (direction < 0 ? -1 : 1) + candidates.length) % candidates.length].open()
          return true
        }
        return false
      }
      // Stable Bar.qml card handoff, scoped to the fixed trusted sections.
      property var popoutCard: null
      function notePopoutCard(card, section) {
        popoutCard = card ? { screen: String(card.screen || ""), section: section,
          x: Number(card.x) || 0, y: Number(card.y) || 0,
          width: Number(card.width) || 0, height: Number(card.height) || 0 } : null
      }
      function popoutCardFor(section) {
        var card = popoutCard
        if (!card || card.section !== section) return null
        return { screen: card.screen, x: card.x, y: card.y, width: card.width, height: card.height }
      }
    }
    QtObject {
      id: clockBar
      readonly property bool vertical: false
      readonly property int barSize: 26
      readonly property string position: "top"
      readonly property string fontFamily: Commons.Color.fontFamily
      // Theme palette through the watched Commons.Color singleton; the
      // 250 ms OutCubic transitions mirror stable upstream Bar.qml.
      property color themeBackground: Commons.Color.bar.background
      property color foreground: Commons.Color.bar.text
      property color barForeground: foreground
      property color urgent: Commons.Color.bar.active
      readonly property color glassBackground: Qt.rgba(themeBackground.r, themeBackground.g, themeBackground.b, Math.min(themeBackground.a, 0.35))
      // Glassy keeps the theme background faintly; a transparent bar wins
      // over it. No blur is managed here: Hyprland 0.56 has no live layerrule
      // removal, so blur behind the bar stays the user's own global setting.
      readonly property bool glassy: bars.backgroundLook === "glassy"
      readonly property bool transparentBar: bars.backgroundLook === "none"
      readonly property color background: themeBackground
      readonly property bool foregroundAnimationEnabled: true
      readonly property var activePopout: barBus.activePopout
      readonly property var clickTargets: barBus.clickTargets
      readonly property string preferenceError: bars.appearance ? bars.appearance.errorText : ""
      readonly property QtObject shell: QtObject {
        readonly property bool persistAppearance: bars.appearance !== null
        function updateClockSettings(values) {
          if (bars.appearance) bars.appearance.setClock(values)
          else bars.clockSettings = Object.assign({}, bars.clockSettings, values)
        }
        function updateEntryInline(id, entry) {
          if (id !== "omarchy.clock" || !entry) return
          var values = Object.assign({}, entry)
          delete values.id
          updateClockSettings(values)
        }
      }
      function registerClickTarget(target) {
        if (target && barBus.clickTargets.indexOf(target) === -1)
          barBus.clickTargets = barBus.clickTargets.concat([target])
      }
      function unregisterClickTarget(target) {
        barBus.clickTargets = barBus.clickTargets.filter(function(item) { return item !== target })
      }
      function switchPanelFrom(owner, direction) { return barBus.switchPanelFrom(owner, direction) }
      function requestPopout(key) {
        var previous = barBus.activePopout
        barBus.activePopout = key
        if (previous && previous !== key && typeof previous.close === "function") previous.close()
      }
      function releasePopout(key) {
        if (barBus.activePopout === key) barBus.activePopout = null
      }
      function notePopoutCard(card) { barBus.notePopoutCard(card, "center") }
      function popoutCardFor(owner) { return barBus.popoutCardFor("center") }
      function itemContainsPoint(target, source, x, y) {
        if (!target || !target.contains(target.mapFromItem(source, x, y))) return false
        for (var item = target; item; item = item.parent) {
          if (!item.visible || item.opacity === 0 || !item.enabled) return false
          if (item.clip && !item.contains(item.mapFromItem(source, x, y))) return false
        }
        return true
      }
      function showTooltip(item, text) { clockTips.showTooltip(item, text) }
      function hideTooltip(item) { clockTips.hideTooltip(item) }
      // The only command path: every ';'-separated segment must pass the
      // BarRun allowlist (keyboard-layout cycling, terminal). Executed
      // detached exactly like upstream Util.execDetached.
      function run(command) {
        if (!BarRun.allowed(command)) {
          console.warn("OMABUNTU_BAR_RUN_REFUSED", String(command))
          return
        }
        Quickshell.execDetached(["bash", "-lc", command])
      }

      Behavior on foreground { ColorAnimation { duration: Style.duration(250); easing.type: Easing.OutCubic } }
      Behavior on barForeground { ColorAnimation { duration: Style.duration(250); easing.type: Easing.OutCubic } }
      Behavior on urgent { ColorAnimation { duration: Style.duration(250); easing.type: Easing.OutCubic } }
      Behavior on themeBackground { ColorAnimation { duration: Style.duration(250); easing.type: Easing.OutCubic } }
    }
    BarTooltipHost {
      id: clockTips
      position: "top"
      fontFamily: clockBar.fontFamily
    }
    BarTooltip { host: clockTips }
    AudioOutputProvider { id: audioProvider }
    BarFrame {
      id: frame
      anchors.fill: parent
      leftContent: Component {
        Row {
          spacing: 0
          MenuButton {
            id: menuButton
            bar: clockBar
            openMenu: bars.openMenu
          }
          LiveStatus {
            liveModes: true
            maximumWidth: Math.max(0, frame.centerStart - 16 - menuButton.implicitWidth)
          }
        }
      }
      centerContent: Component {
        ClockControlView {
          id: clockWidget
          bar: clockBar
          settings: bars.clockSettings
          Component.onCompleted: barBus.registerPanel("clock", clockWidget)
          Component.onDestruction: if (barBus) barBus.unregisterPanel("clock", clockWidget)
        }
      }
      centerEndContent: Component {
        Row {
          spacing: 0
          ElsewhenPanel {
            id: elsewhenWidget
            bar: clockBar
            Component.onCompleted: barBus.registerPanel("elsewhen", elsewhenWidget)
            Component.onDestruction: if (barBus) barBus.unregisterPanel("elsewhen", elsewhenWidget)
          }
          WeatherWidget {
            id: weatherWidget
            bar: clockBar
            settings: ({unit: "metric"})
            Component.onCompleted: barBus.registerPanel("weather", weatherWidget)
            Component.onDestruction: if (barBus) barBus.unregisterPanel("weather", weatherWidget)
          }
        }
      }
      rightContent: Component {
        Row {
          spacing: 0
          PortTrayHost { id: trayHost; appearanceSettings: bars.appearance; popoutState: barBus; width: implicitWidth; height: implicitHeight }
          KeyboardLayout {
            bar: clockBar
            width: implicitWidth
            height: implicitHeight
          }
          BluetoothControlView {
            id: bluetoothWidget
            Component.onCompleted: barBus.registerPanel("bluetooth", bluetoothWidget)
            Component.onDestruction: if (barBus) barBus.unregisterPanel("bluetooth", bluetoothWidget)
            bar: trayHost.ownerApi
            width: implicitWidth
            height: implicitHeight
          }
          NetworkControlView {
            id: networkWidget
            Component.onCompleted: barBus.registerPanel("network", networkWidget)
            Component.onDestruction: if (barBus) barBus.unregisterPanel("network", networkWidget)
            bar: trayHost.ownerApi
            width: implicitWidth
            height: implicitHeight
          }
          AudioOutputView {
            id: audioWidget
            Component.onCompleted: barBus.registerPanel("audio", audioWidget)
            Component.onDestruction: if (barBus) barBus.unregisterPanel("audio", audioWidget)
            bar: trayHost.ownerApi
            backend: audioProvider
            width: implicitWidth
            height: implicitHeight
          }
          DisplayControlView {
            id: displayWidget
            Component.onCompleted: barBus.registerPanel("display", displayWidget)
            Component.onDestruction: if (barBus) barBus.unregisterPanel("display", displayWidget)
            bar: trayHost.ownerApi
            width: implicitWidth
            height: implicitHeight
          }
          PowerControlView {
            id: powerWidget
            Component.onCompleted: barBus.registerPanel("power", powerWidget)
            Component.onDestruction: if (barBus) barBus.unregisterPanel("power", powerWidget)
            appearanceSettings: bars.appearance
            bar: trayHost.ownerApi
            width: implicitWidth
            height: implicitHeight
          }
        }
      }
    }
  }
}
