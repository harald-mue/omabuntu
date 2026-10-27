pragma Singleton
import QtQml
import Quickshell
import Quickshell.Io

// Session-only provenance: never infer ownership from arbitrary floating windows.
// Plan 020: the saved layouts (current/workspace-layouts.txt, written by the
// switcher's eval) are loaded here at startup, so a fresh login restores the
// floating workspaces, their glyphs and the new-window claim path. The file
// is watched: a switch to the default removes it and clears the saved modes.
QtObject {
  id: root
  property var floatingWorkspaces: ({})
  property var savedModes: ({})
  function applied(id, mode) {
    var saved = Object.assign({}, savedModes)
    if (mode === "dwindle") delete saved[id]
    else saved[id] = mode
    savedModes = saved
    var next = Object.assign({}, floatingWorkspaces);
    if (mode === "floating") next[id] = true;
    else delete next[id];
    floatingWorkspaces = next;
  }
  function isFloating(id) { return floatingWorkspaces[id] === true }
  function savedMode(id) { return savedModes[id] }
  function applySaved(raw) {
    var modes = {}
    var lines = String(raw || "").split("\n")
    for (var i = 0; i < lines.length; i++) {
      var parts = lines[i].trim().split(/\s+/)
      if (parts.length !== 2) continue
      if (!/^[1-9][0-9]*$/.test(parts[0])) continue
      if (parts[1] !== "scrolling" && parts[1] !== "floating") continue
      modes[parts[0]] = parts[1]
    }
    savedModes = modes
    var floating = {}
    for (var key in modes) if (modes[key] === "floating") floating[key] = true
    floatingWorkspaces = floating
  }
  property FileView layoutsFile: FileView {
    path: (Quickshell.env("OMABUNTU_STATE_HOME") ||
      ((Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/omabuntu"))
      + "/current/workspace-layouts.txt"
    watchChanges: true
    printErrors: false
    onLoaded: root.applySaved(text())
    onLoadFailed: root.applySaved("")
    onFileChanged: reload()
  }
}