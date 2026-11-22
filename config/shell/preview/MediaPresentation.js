.pragma library

// A whitelist projection, not a native-player proxy. No methods, arbitrary
// metadata, URLs or QObjects reach the audio rows; discovery never issues actions.
function playerSnapshot(player, authority) {
  if (!player) return null;
  var key = authority ? authority.capture(player) : null;
  return Object.freeze({
    dbusName:String(player.dbusName || ""),
    desktopEntry:String(player.desktopEntry || ""),
    identity:String(player.identity || ""),
    trackTitle:String(player.trackTitle || ""),
    trackArtist:String(player.trackArtist || ""),
    trackAlbum:String(player.trackAlbum || ""),
    isPlaying:!!player.isPlaying,
    canControl:!!player.canControl && !!key,
    canPlay:!!player.canPlay,
    canPause:!!player.canPause,
    canTogglePlaying:!!player.canTogglePlaying,
    canGoNext:!!player.canGoNext,
    canGoPrevious:!!player.canGoPrevious,
    transportKey:key
  });
}

function snapshot(players, active, authority) {
  var rows = [];
  for (var i = 0; i < players.length; ++i) {
    if (players[i]) rows.push(playerSnapshot(players[i], authority));
  }
  return Object.freeze({players:Object.freeze(rows), active:playerSnapshot(active, authority)});
}
