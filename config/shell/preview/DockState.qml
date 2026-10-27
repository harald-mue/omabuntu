import QtQuick
import Quickshell
import Quickshell.Io

// Private dock preferences through one reviewed helper (never a shell).
// Session defaults apply until the stored file has been read.
QtObject {
  id: root
  property string helper: Quickshell.env("OMABUNTU_DOCK_HELPER")
  property string position: "bottom"
  property bool autohide: false
  property var pinned: []
  property bool loaded: false
  signal changed()

  function request(kind, args) {
    if (backend.running) return;
    if (!helper || !helper.endsWith("/dock_state.py") || helper.indexOf(" ") >= 0) return;
    backend.exec(["python3", helper, kind].concat(args));
  }
  Component.onCompleted: request("get", [])
  function setPosition(value) {
    if (["top", "bottom", "left", "right"].indexOf(value) < 0 || value === position) return;
    position = value;
    request("set-position", [value]);
  }
  function setAutohide(value) {
    if (autohide === !!value) return;
    autohide = !!value;
    request("set-autohide", [autohide ? "on" : "off"]);
  }
  function setPinned(ids) {
    var next = [];
    for (var i = 0; i < ids.length; i++) {
      // Quickshell entry ids are desktop-file ids without the .desktop suffix.
      // Keep the suffix tolerated so stored files stay readable.
      var id = typeof ids[i] === "string" ? ids[i] : "";
      if (id.length > 0 && id.indexOf(" ") < 0 && next.indexOf(id) < 0) next.push(id);
    }
    pinned = next;
    request("set-pinned", next);
  }
  property Process backend: Process {
    id: backend
    stdout: StdioCollector { id: output }
    onExited: function(code) {
      try {
        var data = JSON.parse(output.text);
        if (code !== 0 || data.error) return;
        if (["top", "bottom", "left", "right"].indexOf(data.position) >= 0) root.position = data.position;
        root.autohide = data.autohide === true;
        if (Array.isArray(data.pinned)) root.pinned = data.pinned.filter(function(id) { return typeof id === "string"; });
        if (!root.loaded) { root.loaded = true; root.changed(); }
      } catch (error) {}
    }
  }
}
