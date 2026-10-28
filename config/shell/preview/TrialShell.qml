//@ pragma IgnoreSystemSettings
import QtQml
import Quickshell
import "TrialPolicy.js" as Policy

// Separate experimental entry: the production catalog remains empty.
// No live configuration, IPC handlers, arbitrary paths or original shell startup.
ShellRoot {
  id: root
  property string configurationJson: Quickshell.env("OMABUNTU_CLOCK_TRIAL")
  property bool initialized: false
  property bool revoked: false
  property var panel: null
  property var launcher: null
  property var dock: null
  property var launchFeedback: null
  property var keybindings: null
  property var commandMenu: null
  property var imagePicker: null
  property int lifetimeMs: 0

  function stop(reason) {
    revoked = true;
    expiry.stop();
    if (keybindings !== null) { keybindings.destroy(); keybindings = null; }
    if (imagePicker !== null) { imagePicker.destroy(); imagePicker = null; }
    if (commandMenu !== null) { commandMenu.destroy(); commandMenu = null; }
    if (dock !== null) { dock.destroy(); dock = null; }
    if (launcher !== null) {
      launcher.destroy();
      launcher = null;
    }
    if (launchFeedback !== null) { launchFeedback.destroy(); launchFeedback = null; }
    if (panel !== null) {
      var surfaces = panel.instances;
      if (surfaces) {
        for (var index = 0; index < surfaces.length; ++index)
          surfaces[index].visible = false;
      }
      panel.destroy();
      panel = null;
    }
    console.log("OMABUNTU_TRIAL_STOP", reason);
    Qt.callLater(function() { Qt.quit(); });
  }
  onConfigurationJsonChanged: if (initialized) stop("configuration changed")
  Component.onCompleted: {
    initialized = true;
    var snapshot = Policy.prepare(configurationJson);
    if (snapshot === null || revoked) { stop("missing or invalid grant"); return; }
    if (Quickshell.env("QT_QPA_PLATFORM") !== "wayland") { stop("Wayland-only trial"); return; }
    var factory = Qt.createComponent(Qt.resolvedUrl("TrialPanel.qml"), Component.PreferSynchronous);
    if (factory.status !== Component.Ready) {
      console.error("OMABUNTU_TRIAL_COMPONENT_FAILED", factory.errorString());
      factory.destroy(); Qt.exit(43); return;
    }
    panel = factory.createObject(root);
    factory.destroy();
    if (!panel) { console.error("OMABUNTU_TRIAL_CREATE_FAILED"); Qt.exit(43); return; }
    var appsFactory = Qt.createComponent(Qt.resolvedUrl("AppLauncher.qml"), Component.PreferSynchronous);
    if (appsFactory.status !== Component.Ready) {
      console.error("OMABUNTU_TRIAL_APPS_FAILED", appsFactory.errorString());
      appsFactory.destroy(); Qt.exit(43); return;
    }
    launcher = appsFactory.createObject(root);
    appsFactory.destroy();
    if (!launcher) { console.error("OMABUNTU_TRIAL_APPS_CREATE_FAILED"); Qt.exit(43); return; }
    var dockFactory = Qt.createComponent(Qt.resolvedUrl("FloatingDock.qml"), Component.PreferSynchronous);
    if (dockFactory.status !== Component.Ready) {
      console.error("OMABUNTU_TRIAL_DOCK_FAILED", dockFactory.errorString());
      dockFactory.destroy(); Qt.exit(43); return;
    }
    dock = dockFactory.createObject(root, {openApps: function() { launcher.toggle(); }});
    dockFactory.destroy();
    if (!dock) { console.error("OMABUNTU_TRIAL_DOCK_CREATE_FAILED"); Qt.exit(43); return; }
    launcher.dock = dock;
    var launchFactory = Qt.createComponent(Qt.resolvedUrl("LaunchFeedback.qml"), Component.PreferSynchronous);
    if (launchFactory.status !== Component.Ready) {
      console.error("OMABUNTU_TRIAL_LAUNCH_FAILED", launchFactory.errorString());
      launchFactory.destroy(); Qt.exit(43); return;
    }
    launchFeedback = launchFactory.createObject(root);
    launchFactory.destroy();
    if (!launchFeedback) { console.error("OMABUNTU_TRIAL_LAUNCH_CREATE_FAILED"); Qt.exit(43); return; }
    launcher.launchFeedback = launchFeedback;
    dock.launchFeedback = launchFeedback;
    var keysFactory = Qt.createComponent(Qt.resolvedUrl("KeybindingsMenu.qml"), Component.PreferSynchronous);
    if (keysFactory.status !== Component.Ready) {
      console.error("OMABUNTU_TRIAL_KEYS_FAILED", keysFactory.errorString());
      keysFactory.destroy(); Qt.exit(43); return;
    }
    keybindings = keysFactory.createObject(root);
    keysFactory.destroy();
    if (!keybindings) { console.error("OMABUNTU_TRIAL_KEYS_CREATE_FAILED"); Qt.exit(43); return; }
    var menuFactory = Qt.createComponent(Qt.resolvedUrl("CommandMenu.qml"), Component.PreferSynchronous);
    if (menuFactory.status !== Component.Ready) {
      console.error("OMABUNTU_TRIAL_MENU_FAILED", menuFactory.errorString());
      menuFactory.destroy(); Qt.exit(43); return;
    }
    var pickerFactory = Qt.createComponent(Qt.resolvedUrl("ImagePicker.qml"), Component.PreferSynchronous);
    if (pickerFactory.status !== Component.Ready) {
      console.error("OMABUNTU_TRIAL_PICKER_FAILED", pickerFactory.errorString());
      pickerFactory.destroy(); Qt.exit(43); return;
    }
    imagePicker = pickerFactory.createObject(root);
    pickerFactory.destroy();
    if (!imagePicker) { console.error("OMABUNTU_TRIAL_PICKER_CREATE_FAILED"); Qt.exit(43); return; }
    commandMenu = menuFactory.createObject(root, {
      openApps: function() { launcher.toggle(); },
      openKeybindings: function() { keybindings.toggle(); },
      openThemes: function() { imagePicker.toggleThemes(); },
      openBackgrounds: function() { imagePicker.toggleBackgrounds(); }
    });
    menuFactory.destroy();
    if (!commandMenu) { console.error("OMABUNTU_TRIAL_MENU_CREATE_FAILED"); Qt.exit(43); return; }
    panel.openMenu = function() { commandMenu.toggleRoute("root"); };
    lifetimeMs = snapshot.scope === "bar-session-v1" ? 0 : snapshot.duration_seconds * 1000;
    if (lifetimeMs > 0) expiry.start();
    else console.log("OMABUNTU_BAR_SESSION_NO_EXPIRY");
    console.log("OMABUNTU_TRIAL_STARTED");
  }
  Timer { id: expiry; interval: root.lifetimeMs; repeat: false; onTriggered: root.stop("expired") }
}
