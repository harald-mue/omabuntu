// Allowlist for the panel bar API's run(). Every ';'-separated segment must
// match exactly one pattern below; anything else is refused and logged by
// the caller. This is the only command path the trial bar exposes.
var SEGMENTS = [
  // Keyboard-layout cycling (Util.shellQuote'd device names, absolute index).
  /^hyprctl switchxkblayout ('[^']*'|"[^"]*"|\S+) [0-9]+$/,
  // The menu button's right-click terminal, as upstream.
  /^xdg-terminal-exec$/
]

function allowed(command) {
  var text = String(command || "")
  if (!text) return false
  var parts = text.split(";")
  if (parts.length === 0) return false
  for (var i = 0; i < parts.length; i++) {
    var segment = parts[i].replace(/^\s+|\s+$/g, "")
    if (!segment) return false
    var ok = false
    for (var j = 0; j < SEGMENTS.length; j++) {
      if (SEGMENTS[j].test(segment)) { ok = true; break }
    }
    if (!ok) return false
  }
  return true
}
