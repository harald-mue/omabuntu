import QtQuick
import Quickshell
import Quickshell.Io

// An environment path only locates a private proof, never grants the role.
// The helper validates the artifact, session and exact shell parent, and claims
// the grant once. Ordinary manager launches supply no proof and stay inactive.
Item {
  id: root
  property bool initialized: false
  property bool deploymentApproved: false
  property bool exclusiveRuntimeVerified: false
  property var legacyDnd: null
  property var shellContext: null
  property string menuHelper: Quickshell.env("OMABUNTU_MENU_HELPER")
  readonly property string storageHelper: menuHelper.endsWith("/menu_model.py")
    ? menuHelper.slice(0, -"menu_model.py".length) + "notification_state.py" : ""
  readonly property string sessionFile: Quickshell.env("OMABUNTU_NOTIFICATION_SESSION_FILE")
  readonly property string sessionHelper: storageHelper
    ? storageHelper.slice(0, -"notification_state.py".length) + "notification_session.py" : ""
  readonly property bool ready: !!service && service.storeReady && service.liveLoaded
    && service.historyLoaded && service.quietLoaded
  readonly property bool requested: deploymentApproved && exclusiveRuntimeVerified
  readonly property var service: owner.item
  readonly property var dnd: requested ? originalDnd : legacyDnd
  readonly property string errorText: requested && owner.status === Loader.Error
    ? "Original notification service unavailable; no provider fallback was started" : ""
  QtObject {
    id: originalDnd
    readonly property bool known: !!root.service && root.service.storeReady
    readonly property bool writable: known && root.service.quietLoaded
    readonly property bool doNotDisturb: known ? root.service.doNotDisturb : false
    function setDoNotDisturb(value) {
      if (!writable || typeof value !== "boolean") return false
      root.service.setDoNotDisturb(value)
      return true
    }
  }
  function load() {
    if (requested && storageHelper) owner.setSource("Notifications/Service.qml",
      {shell: shellContext, storageHelper: storageHelper})
    else owner.source = ""
  }
  onRequestedChanged: if (initialized) load()
  Component.onCompleted: {
    initialized = true
    load()
    if (sessionFile) {
      if (!sessionHelper) { console.error("OMABUNTU_NOTIFICATION_ADMISSION_FAILED"); Qt.exit(1) }
      else admission.running = true
    }
  }
  Process {
    id: admission
    command: ["/usr/bin/python3", "-B", root.sessionHelper, "admit", root.sessionFile]
    stdout: StdioCollector { id: admissionOutput }
    onExited: function(code) {
      if (code !== 0 || admissionOutput.text.trim() !== "OMABUNTU_NOTIFICATION_SESSION_ADMITTED_V1") {
        console.error("OMABUNTU_NOTIFICATION_ADMISSION_FAILED")
        Qt.exit(1)
        return
      }
      root.deploymentApproved = true
      root.exclusiveRuntimeVerified = true
    }
  }
  IpcHandler {
    target: "omabuntuNotificationRole"
    function status(): string {
      return JSON.stringify({admitted: root.requested, ready: root.ready,
        quiet: root.ready ? root.service.doNotDisturb : null})
    }
  }
  Loader {
    id: owner
    active: root.requested
    onStatusChanged: if (root.requested && status === Loader.Error) {
      console.error("OMABUNTU_NOTIFICATION_ADMISSION_FAILED")
      Qt.exit(1)
    }
  }
}
