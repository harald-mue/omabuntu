// Derived from the original media Service.qml; complete upstream MIT notice
// is preserved in LICENSE. Original selection and explicit guarded transport.
// No volume commands, IPC, art loading, OSD or external helpers.
pragma Singleton
import QtQuick
import Quickshell.Services.Mpris
import Quickshell.Services.Pipewire
import "../Port/MediaModel.js" as MediaModel
import "../MediaPresentation.js" as Presentation
import "../MediaIdentity.js" as Identity
import "../AudioActions.js" as Actions

Item {
  id: root
  property string preferredPlayerKey: ""
  property var playerStartedAt: ({})
  property int playSerial: 0
  readonly property var transport: Identity.createAuthority()
  property string errorText: ""
  property QtObject feedback: null
  property QtObject artwork: null
  readonly property string artSource: artwork ? artwork.source : ""
  // One shared observer owns playing order across outputs. Bind playback nodes
  // before reading their properties; native objects stay behind this boundary.
  readonly property var playbackStreams: {
    var values = Pipewire.nodes ? Pipewire.nodes.values : [];
    return values.filter(Actions.playbackStream);
  }
  PwObjectTracker { objects: root.playbackStreams }
  readonly property var players: Mpris.players ? Mpris.players.values : []
  readonly property var sourcePlayers: orderedSourcePlayers()
  readonly property var activePlayer: selectActivePlayer()
  readonly property var state: Presentation.snapshot(sourcePlayers, activePlayer, transport)

  function isProxyPlayer(player) {
    return MediaModel.isProxyPlayer(player)
  }

  function hasMetadata(player) {
    return MediaModel.hasMetadata(player)
  }

  function hasTrackMetadata(player) {
    return MediaModel.hasTrackMetadata(player)
  }

  function playerCanControl(player) {
    return MediaModel.playerCanControl(player)
  }

  function playerHasPlaybackStream(player) {
    return MediaModel.playerHasPlaybackStream(player, playbackStreams)
  }

  function playerKey(player) {
    return MediaModel.playerKey(player)
  }

  function playerOrder(player, fallback) {
    var key = playerKey(player)
    var value = key ? playerStartedAt[key] : undefined
    return value === undefined ? fallback : value
  }

  function syncPlayingOrder() {
    var next = {}
    var alive = {}
    var serial = playSerial

    for (var i = 0; i < players.length; i++) {
      var p = players[i]
      var key = playerKey(p)
      if (!key) continue

      alive[key] = true
      if (!p.isPlaying) continue

      if (playerStartedAt[key] === undefined) {
        serial += 1
        next[key] = serial
      } else {
        next[key] = playerStartedAt[key]
      }
    }

    if (preferredPlayerKey && !alive[preferredPlayerKey]) preferredPlayerKey = ""

    playSerial = serial
    playerStartedAt = next
  }

  function orderedSourcePlayers() {
    var list = []
    for (var i = 0; i < players.length; i++) {
      var p = players[i]
      if (hasMetadata(p)) list.push(p)
    }

    list.sort(function(a, b) {
      if (!!a.isPlaying !== !!b.isPlaying) return a.isPlaying ? -1 : 1
      if (isProxyPlayer(a) !== isProxyPlayer(b)) return isProxyPlayer(a) ? 1 : -1
      if (a.isPlaying && b.isPlaying) {
        var orderDelta = playerOrder(a, 1000) - playerOrder(b, 1000)
        if (orderDelta !== 0) return orderDelta
      }
      return labelFor(a).localeCompare(labelFor(b))
    })

    return list
  }

  function oldestPlayingPlayer(requirePlaybackStream) {
    var oldest = null
    var oldestOrder = 0
    var playingProxy = null
    var proxyOrder = 0

    for (var i = 0; i < players.length; i++) {
      var p = players[i]
      if (!p) continue

      var proxyPlayer = isProxyPlayer(p)
      if (p.isPlaying) {
        if (requirePlaybackStream && !playerHasPlaybackStream(p)) continue

        var order = playerOrder(p, i + 1000)
        if (!proxyPlayer && (!oldest || order < oldestOrder)) {
          oldest = p
          oldestOrder = order
        } else if (proxyPlayer && (!playingProxy || order < proxyOrder)) {
          playingProxy = p
          proxyOrder = order
        }
      }
    }

    return oldest || playingProxy || null
  }

  function selectActivePlayer() {
    var preferred = null
    for (var i = 0; i < players.length; i++) {
      var p = players[i]
      if (p && preferredPlayerKey && playerKey(p) === preferredPlayerKey && hasMetadata(p)) preferred = p
    }

    if (preferred && preferred.isPlaying) return preferred
    return oldestPlayingPlayer(true) || oldestPlayingPlayer(false) || MediaModel.idlePlayer(players, preferred, playerHasPlaybackStream)
  }

  function labelFor(player) {
    return MediaModel.labelFor(player)
  }

  function sameTarget(a, b) { return Identity.same(a, b) }
  function selectPlayer(key) {
    var player = transport.resolve(players, key)
    if (!player || !hasMetadata(player)) {
      errorText = "Media source changed; selection refused"
      return false
    }
    preferredPlayerKey = playerKey(player)
    errorText = ""
    return true
  }
  function runAction(action, showFeedback, targetKey) {
    var player = transport.resolve(players, targetKey)
    if ((showFeedback !== undefined && typeof showFeedback !== "boolean")
        || (showFeedback !== false && (typeof feedback === "undefined" || !feedback))
        || !player || !player.canControl || !MediaModel.canHandleAction(player, action)) {
      errorText = "Media target changed or action is unavailable"
      return false
    }
    var key = playerKey(player)
    var feedbackTitle = String(player.trackTitle || "")
    var handled = false
    var iconName = "media"
    try {
    if (action === "next") {
      iconName = "media-next"
      if (player && player.canGoNext) {
        player.next()
        handled = true
      }
    } else if (action === "previous") {
      iconName = "media-previous"
      if (player && player.canGoPrevious) {
        player.previous()
        handled = true
      }
    } else if (action === "play") {
      iconName = "media-play"
      if (player && player.canPlay) {
        player.play()
        handled = true
      } else if (player && player.canTogglePlaying && !player.isPlaying) {
        player.togglePlaying()
        handled = true
      }
    } else if (action === "pause") {
      iconName = "media-pause"
      if (player && player.canPause) {
        player.pause()
        handled = true
      } else if (player && player.canTogglePlaying && player.isPlaying) {
        player.togglePlaying()
        handled = true
      }
    } else if (action === "playPause") {
      iconName = player && player.isPlaying ? "media-pause" : "media-play"
      if (player && player.isPlaying && player.canPause) {
        player.pause()
        handled = true
      } else if (player && !player.isPlaying && player.canPlay) {
        player.play()
        handled = true
      } else if (player && player.canTogglePlaying) {
        player.togglePlaying()
        handled = true
      }
    }

    } catch (error) {
      errorText = "Media request outcome is uncertain; inspect playback before retrying"
      return false
    }
    if (handled && transport.resolve(players, targetKey) === player) preferredPlayerKey = key
    errorText = handled ? "" : "Media action is unavailable"
    if (handled && showFeedback !== false && feedback) feedback.media(action, feedbackTitle, iconName)
    return handled // Request issued, not asynchronous server acceptance.
  }

  // Recompute play-order reactively instead of polling every 500ms.
  // syncPlayingOrder only depends on the set of players and each player's
  // isPlaying state: onPlayersChanged covers players appearing/disappearing,
  // and the Instantiator wires isPlayingChanged for each live player.
  Component.onCompleted: root.syncPlayingOrder()
  onPlayersChanged: root.syncPlayingOrder()

  Instantiator {
    model: root.players
    delegate: Connections {
      required property var modelData
      target: modelData
      function onIsPlayingChanged() { root.syncPlayingOrder() }
    }
  }

}
