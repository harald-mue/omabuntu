.pragma library

// Tokens identify observed player objects within this shell instance only.
// They are neither durable preferences nor DBus unique-owner/security proofs.
function valid(key) {
  return !!key && typeof key === "object" && !Array.isArray(key)
    && Object.keys(key).length === 2 && typeof key.name === "string"
    && /^org\.mpris\.MediaPlayer2\.[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$/.test(key.name)
    && Number.isSafeInteger(key.generation) && key.generation > 0;
}

function createAuthority() {
  var identities = new WeakMap();
  var serial = 0;
  function capture(player) {
    if (!player || typeof player.dbusName !== "string") return null;
    var previous = identities.get(player);
    if (previous && previous.name === player.dbusName) return previous;
    if (serial >= Number.MAX_SAFE_INTEGER) return null;
    var key = Object.freeze({name:player.dbusName, generation:++serial});
    if (!valid(key)) return null;
    identities.set(player, key);
    return key;
  }
  function resolve(players, key) {
    if (!valid(key)) return null;
    var found = null;
    for (var i = 0; i < players.length; ++i) {
      var player = players[i];
      if (player && player.dbusName === key.name) {
        if (found) return null; // Ambiguous native model state never selects a target.
        found = player;
      }
    }
    if (!found) return null;
    var current = capture(found);
    return current && current.generation === key.generation ? found : null;
  }
  return Object.freeze({capture:capture, resolve:resolve});
}

function same(a, b) {
  return valid(a) && valid(b) && a.name === b.name && a.generation === b.generation;
}
