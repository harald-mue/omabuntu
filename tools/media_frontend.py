"""Closed source extractions for original media ownership and optional controls."""
from network_frontend import block, between, replace

FUNCTIONS = (
    'isProxyPlayer', 'hasMetadata', 'hasTrackMetadata', 'playerCanControl',
    'playerHasPlaybackStream', 'playerKey', 'playerOrder', 'syncPlayingOrder',
    'orderedSourcePlayers', 'oldestPlayingPlayer', 'selectActivePlayer', 'labelFor',
)


def derive_selection(data):
    source = data.decode()
    functions = []
    for name in FUNCTIONS:
        prefix = '  function ' + name + '('
        lines = [line for line in source.splitlines() if line.startswith(prefix)]
        if len(lines) != 1:
            raise ValueError('Original media selection function witness differs: ' + name)
        functions.append(block(source, lines[0]))
    observer = between(source, '  // Recompute play-order reactively instead of polling every 500ms.\n',
                       '  Timer {\n    id: trackOsdTimer\n')
    result = '''// Derived from the original media Service.qml; complete upstream MIT notice
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

''' + '\n\n'.join(functions) + '\n\n' + derive_dispatch(source) + '\n' + observer + '}\n'
    for forbidden in ('Quickshell.Io', 'ShellIpc', 'Process {', 'switchSource(',
                      'scheduleOsd(', '.audio.volume =', '.audio.muted =', 'SizedImage'):
        if forbidden in result:
            raise ValueError('Active path remains in read-only media extraction')
    return result.encode()


def dispatch_branches(source):
    action = block(source, '  function runAction(action, showFeedback, targetKey) {')
    core = between(action, '    if (action === "next") {\n', '    if (handled && key) preferredPlayerKey = key\n')
    # Only feedback labels/icons are removed; native conditions/calls remain.
    labels = [line for line in core.splitlines() if line.strip().startswith(('actionLabel =', 'iconName ='))]
    if len(labels) != 10:
        raise ValueError('Original media dispatch feedback witnesses differ')
    return '\n'.join(line for line in core.splitlines() if line not in labels) + '\n'


def derive_dispatch(source):
    return '''  function sameTarget(a, b) { return Identity.same(a, b) }
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
    if (showFeedback !== false || !player || !player.canControl || !MediaModel.canHandleAction(player, action)) {
      errorText = "Media target changed or action is unavailable"
      return false
    }
    var key = playerKey(player)
    var handled = false
    try {
''' + dispatch_branches(source) + '''    } catch (error) {
      errorText = "Media request outcome is uncertain; inspect playback before retrying"
      return false
    }
    if (handled && transport.resolve(players, targetKey) === player) preferredPlayerKey = key
    errorText = handled ? "" : "Media action is unavailable"
    return handled // Request issued, not asynchronous server acceptance.
  }
'''


def derive_widget(data):
    text = data.decode()
    text = replace(text, '  readonly property var mediaService: bar?.shell?.firstPartyServiceFor("omarchy.media")',
                   '  readonly property var mediaService: Commons.MediaSelection')
    text = replace(text, 'mediaService ? mediaService.activePlayer : null', 'mediaService ? mediaService.state.active : null')
    text = replace(text, 'mediaService ? mediaService.sourcePlayers : []', 'mediaService ? mediaService.state.players : []')
    text = replace(text, '!root.bar.barHidden', '!("barHidden" in root.bar && root.bar.barHidden)')
    art = block(text, '          SizedImage {\n')
    text = replace(text, '''          // Decode the art at the size it is drawn, not the size the player
          // serves it at. The popup is built on every monitor at startup.
''' + art, '          // Artwork loader excluded: no local/remote URL access.')
    text = replace(text, 'visible: !root.activePlayer || !root.activePlayer.trackArtUrl', 'visible: true')
    text = replace(text, '''root.mediaService.playerKey(root.activePlayer) === root.mediaService.playerKey(player)''',
                   'root.mediaService.sameTarget(root.activePlayer.transportKey, player.transportKey)')
    target = 'root.mediaService.playerKey(root.activePlayer)'
    if text.count(target) != 3:
        raise ValueError('Original transport target witnesses differ')
    text = text.replace(target, 'root.activePlayer.transportKey')
    text = replace(text, 'root.mediaService.playerKey(sourceRow.player)', 'sourceRow.player.transportKey')
    for capability in ('canGoPrevious', 'canGoNext'):
        text = replace(text, 'enabled: root.activePlayer && root.activePlayer.' + capability,
                       'enabled: root.activePlayer && root.activePlayer.canControl && root.activePlayer.' + capability)
    text = replace(text, 'enabled: root.activePlayer && (root.activePlayer.canTogglePlaying',
                   'enabled: root.activePlayer && root.activePlayer.canControl && (root.activePlayer.canTogglePlaying')
    mouse = block(text, '\n  MouseArea {\n')
    adapted = mouse
    handlers = []
    for signal, argument, method in [('onClicked', 'mouse', 'pointerClicked'), ('onWheel', 'wheel', 'pointerWheel')]:
        header = '    ' + signal + ': function(' + argument + ') {'
        body = block(mouse, header)
        function = replace(body, header, '    function ' + method + '(' + argument + ') {')
        for action in ('next', 'previous', 'playPause'):
            token = 'runAction("' + action + '", false)'
            if token in function:
                function = replace(function, token, 'runAction("' + action + '", false, root.activePlayer.transportKey)')
        handlers.append('\n'.join(line[2:] if line.startswith('  ') else line for line in function.splitlines()))
        adapted = replace(adapted, body, header + ' root.' + method + '(' + argument + ') }')
    text = replace(text, mouse, adapted)
    text = replace(text, '  property real maxLabelWidth: 180\n', '''  property real maxLabelWidth: 180
  onHasMediaChanged: if (!hasMedia) close()
  Connections {
    target: root.bar
    ignoreUnknownSignals: true
    function onBarHiddenChanged() { if (root.bar.barHidden) root.close() }
  }

''' + '\n\n'.join(handlers) + '\n')
    text = replace(text, '      PanelSeparator {\n        visible: root.sourcePlayers.length > 1', '''      Text {
        visible: root.mediaService.errorText !== ""
        textFormat: Text.PlainText
        text: root.mediaService.errorText
        color: root.bar.foreground
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.bodySmall
        width: parent.width
        wrapMode: Text.Wrap
      }

      PanelSeparator {
        visible: root.sourcePlayers.length > 1''')
    if any(token in text for token in ('SizedImage {', 'firstPartyServiceFor(', 'trackArtUrl', 'execDetached', 'Process {')):
        raise ValueError('Excluded media widget path remains')
    return ('// Derived original media widget; full upstream MIT notice in LICENSE.\n'
            '// Primitive targets, guarded native actions, no artwork/OSD/startup.\n' + text).encode()
