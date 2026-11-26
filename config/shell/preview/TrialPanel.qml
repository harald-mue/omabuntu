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
// Only trusted registered Components are admitted; gestures/theme IO and
// arbitrary plugin startup are not loaded. Monitor-local workspaces
// require a separately approved compositor policy and state marker.
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

  // One event-driven read refresh for all outputs, not one per bar.
  property BarFullscreenState fullscreenRefresh: BarFullscreenState { refreshEvents: true }

  property BarPeekState peekState: BarPeekState {}
  property BluetoothSession bluetoothSession: BluetoothSession {
    enabled: !bars.barHidden && bars.hasAudioWidget("omarchy.bluetooth")
  }

  // One native owner, only after explicit optional-widget visibility consent.
  property IndicatorState indicatorState: IndicatorState {
    enabled: !bars.barHidden && !!bars.appearance && bars.appearance.loaded && Object.keys(bars.appearance.bar.bar_layout || {}).some(function(region) {
      return bars.appearance.bar.bar_layout[region].indexOf("omarchy.indicators") >= 0
    })
  }

  property QtObject notificationContext: QtObject {
    readonly property QtObject bar: QtObject {
      readonly property string position: "top"
      readonly property int barSize: 26
      readonly property bool barHidden: bars.barHidden
      function barSizeFor(name) { return 26 }
    }
  }
  property NotificationHost notificationHost: NotificationHost {
    legacyDnd: bars.indicatorState.dnd
    shellContext: bars.notificationContext
  }

  function hasAudioWidget(id) {
    if (!appearance || !appearance.loaded) return id === "omarchy.audio"
    return Object.keys(appearance.bar.bar_layout || {}).some(function(region) {
      return bars.appearance.bar.bar_layout[region].indexOf(id) >= 0
    })
  }
  property AudioFeedback audioFeedback: AudioFeedback {
    enabled: !bars.barHidden && (bars.hasAudioWidget("omarchy.audio") || bars.hasAudioWidget("omarchy.media"))
  }
  property AudioOutputProvider audioProvider: AudioOutputProvider {
    feedback: bars.audioFeedback
  }
  property AudioOsdView audioOsd: AudioOsdView { feedback: bars.audioFeedback }
  property MediaArtwork artwork: MediaArtwork {
    enabled: !bars.barHidden && bars.hasAudioWidget("omarchy.media")
    url: Commons.MediaSelection.activePlayer ? String(Commons.MediaSelection.activePlayer.trackArtUrl || "") : ""
    identity: JSON.stringify(Commons.MediaSelection.state.active)
  }
  property Binding mediaFeedbackBinding: Binding { target: Commons.MediaSelection; property: "feedback"; value: bars.audioFeedback }
  property Binding mediaArtworkBinding: Binding { target: Commons.MediaSelection; property: "artwork"; value: bars.artwork }

  model: Quickshell.screens
  PanelWindow {
    id: barPanel
    required property var modelData
    screen: modelData
    anchors { top: true; left: true; right: true }
    // Original BarPanel policy: a stable full-screen alpha surface keeps
    // the active grab; only the 26px strip reserves space or takes idle input.
    implicitHeight: screen ? screen.height : 26
    // Hiding parks the bar just past the screen edge instead of unmapping
    // it, so a reveal is a margin change (upstream BarPanel behavior).
    margins { top: bars.barHidden ? -barPanel.implicitHeight : 0 }
    exclusiveZone: 26
    exclusionMode: bars.barHidden ? ExclusionMode.Ignore : ExclusionMode.Normal
    property BarFullscreenState fullscreenState: BarFullscreenState {
      screen: barPanel.screen
      hidden: bars.barHidden
      dragFrame: frame
    }
    mask: fullscreenState.maskFor(frame.barDragSource !== null, stripInputRegion, noInputRegion)
    Region { id: stripInputRegion; item: barStrip }
    Region { id: noInputRegion }
    // Preferences load after creation. Keep an alpha buffer even when the
    // initial Opaque default would otherwise permanently select an opaque surface.
    surfaceFormat.opaque: false
    color: "transparent"
    WlrLayershell.namespace: "omabuntu-clock-trial"
    WlrLayershell.layer: WlrLayer.Top
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand

    QtObject {
      id: barBus
      property var activePopout: null
      property var clickTargets: []
      function switchPanelFrom(owner, direction) { return frame.switchPanelFrom(owner, direction) }
      // Stable Bar.qml card handoff, scoped to the fixed trusted sections.
      property var popoutCard: null
      function notePopoutCard(card, section) {
        popoutCard = card ? { screen: String(card.screen || ""), section: section,
          x: Number(card.x) || 0, y: Number(card.y) || 0,
          width: Number(card.width) || 0, height: Number(card.height) || 0 } : null
      }
      function popoutCardFor(section) {
        var card = popoutCard
        if (!card || !section || card.section !== section) return null
        return { screen: card.screen, x: card.x, y: card.y, width: card.width, height: card.height }
      }
    }
    QtObject {
      id: clockBar
      readonly property bool barHidden: bars.barHidden
      readonly property bool centerSectionRevealHeld: bars.peekState.centerSectionRevealHeld
      readonly property bool centerHoverRevealSuppressed: bars.peekState.centerHoverRevealSuppressed
      function setCenterHoverRevealSuppressed(value) { bars.peekState.setCenterHoverRevealSuppressed(value) }
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
      readonly property var layoutConfig: ({tray: []})
      readonly property bool traySectionDragActive: false
      readonly property bool traySectionPopoutOpen: false
      readonly property QtObject shell: QtObject {
        readonly property bool persistAppearance: bars.appearance !== null
        function updateClockSettings(values) {
          if (bars.appearance) bars.appearance.setClock(values)
          else bars.clockSettings = Object.assign({}, bars.clockSettings, values)
        }
        function updateEntryInline(id, entry) {
          if (!entry) return
          if (id === "omarchy.tray") {
            if (bars.appearance && Array.isArray(entry.pinned) && Array.isArray(entry.hidden))
              bars.appearance.setTray({pinned: entry.pinned.slice(), hidden: entry.hidden.slice()})
            return
          }
          if (id !== "omarchy.clock") return
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
      function notePopoutCard(card) { barBus.notePopoutCard(card, frame.popoutSectionOf(barBus.activePopout)) }
      function popoutCardFor(owner) { return barBus.popoutCardFor(frame.popoutSectionOf(owner)) }
      function itemContainsPoint(target, source, x, y) {
        if (!target || !target.contains(target.mapFromItem(source, x, y))) return false
        for (var item = target; item; item = item.parent) {
          if (!item.visible || item.opacity === 0 || !item.enabled) return false
          if (item.clip && !item.contains(item.mapFromItem(source, x, y))) return false
        }
        return true
      }
      function showTooltip(item, text) { clockTips.showTooltip(item, preferenceError || text) }
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
    Component {
      id: menuComponent
      MenuButton { bar: clockBar; openMenu: bars.openMenu }
    }
    Component {
      id: workspacesComponent
      LiveStatus { bar: clockBar; liveModes: true; maximumWidth: Math.max(0, frame.width - 16) }
    }
    Component {
      id: clockComponent
      ClockControlView { bar: clockBar; settings: bars.clockSettings }
    }
    Component {
      id: elsewhenComponent
      ElsewhenPanel { bar: clockBar }
    }
    Component {
      id: weatherComponent
      WeatherWidget { bar: clockBar; settings: ({unit: "metric"}) }
    }
    Component {
      id: trayComponent
      PortTrayHost {
        appearanceSettings: bars.appearance
        popoutState: barBus
        barOverride: clockBar
      }
    }
    Component {
      id: keyboardComponent
      KeyboardLayout { bar: clockBar }
    }
    Component {
      id: bluetoothComponent
      BluetoothControlView { bar: clockBar; session: bars.bluetoothSession }
    }
    Component {
      id: networkComponent
      NetworkControlView { bar: clockBar }
    }
    Component {
      id: audioComponent
      AudioOutputView { bar: clockBar; backend: bars.audioProvider }
    }
    Component {
      id: mediaComponent
      MediaControlView { bar: clockBar }
    }
    Component { id: dndIndicatorComponent; DndIndicator { backend: bars.notificationHost.dnd } }
    Component { id: nightlightIndicatorComponent; NightLightIndicator { backend: bars.indicatorState.nightlight } }
    Component {
      id: indicatorsComponent
      IndicatorsView {
        bar: clockBar
        settings: ({items: ["NightLight", "Dnd"], stableControls: true})
        indicatorComponents: ({
          "Dnd": bars.notificationHost.dnd && bars.notificationHost.dnd.known ? dndIndicatorComponent : null,
          "NightLight": bars.indicatorState.nightlight.known ? nightlightIndicatorComponent : null
        })
        onRefreshRequested: bars.indicatorState.refresh()
      }
    }
    Component {
      id: displayComponent
      DisplayControlView { bar: clockBar }
    }
    Component {
      id: powerComponent
      PowerControlView { bar: clockBar; appearanceSettings: bars.appearance }
    }
    Rectangle {
      id: barStrip
      width: parent.width
      height: 26
      color: clockBar.transparentBar ? "transparent" : (clockBar.glassy ? clockBar.glassBackground : clockBar.themeBackground)
    }
    Connections {
      target: bars
      function onBarHiddenChanged() { frame.clearBarDrag() }
    }
    BarFrame {
      id: frame
      width: parent.width
      height: 26
      barWindow: barPanel
      barApi: clockBar
      peekState: bars.peekState
      peekSuppressed: fullscreenState.suppressed
      // The closed Python registry validates persisted values; Components and
      // their API/settings bindings are authored here, never loaded from URLs.
      layoutEditor: bars.appearance
      layoutConfig: bars.appearance && bars.appearance.loaded && bars.appearance.bar.bar_layout
        ? bars.appearance.bar.bar_layout
        : ({left: ["omabuntu.menu", "omarchy.workspaces"], centerBegin: [],
            center: ["omarchy.clock"], centerEnd: ["omarchy.elsewhen", "omarchy.weather"],
            right: ["omarchy.tray", "omarchy.keyboard-layout", "omarchy.bluetooth",
                    "omarchy.network", "omarchy.audio", "omarchy.monitor", "omarchy.power"]})
      widgetComponents: ({
        "omabuntu.menu": menuComponent, "omarchy.workspaces": workspacesComponent,
        "omarchy.clock": clockComponent, "omarchy.elsewhen": elsewhenComponent,
        "omarchy.weather": weatherComponent, "omarchy.tray": trayComponent,
        "omarchy.keyboard-layout": keyboardComponent, "omarchy.bluetooth": bluetoothComponent,
        "omarchy.network": networkComponent, "omarchy.audio": audioComponent,
        "omarchy.media": mediaComponent, "omarchy.indicators": indicatorsComponent,
        "omarchy.monitor": displayComponent, "omarchy.power": powerComponent
      })
    }
  }
}
