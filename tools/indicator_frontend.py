"""Closed original indicator derivations; native IO stays in a shared owner."""
from audio_frontend import between, replace


def derive_indicator(data):
    text = data.decode()
    text = replace(text, between(text, '  function extractData(raw) {\n',
                                '  function syncIndicatorOpacity() {\n'), '')
    return text.encode()


def derive_native(data, kind):
    if kind not in ('Dnd', 'NightLight'):
        raise ValueError('Unknown native indicator parent')
    text = data.decode()
    name, service = ('notificationService', 'notifications') if kind == 'Dnd' else ('nightlightService', 'nightlight')
    text = replace(text, '  readonly property var ' + name + ': bar?.shell?.firstPartyServiceFor("omarchy.' + service + '")',
                   '  required property var backend\n'
                   '  enabled: !!backend && backend.known === true\n'
                   '  pressable: !!backend && backend.known === true && backend.writable === true\n'
                   '  onTooltipTextChanged: if (tooltipHovered) Qt.callLater(function() {\n'
                   '    if (root.tooltipHovered && root.bar) root.bar.showTooltip(root, root.tooltipText)\n'
                   '  })\n'
                   '  readonly property var ' + name + ': backend && backend.known === true ? backend : null')
    if 'firstPartyServiceFor' in text or 'Process {' in text:
        raise ValueError('Unadmitted native service seam remains')
    return text.encode()


def derive_dnd(data):
    return derive_native(data, 'Dnd')


def derive_nightlight(data):
    return derive_native(data, 'NightLight')


def derive_indicators(data):
    text = data.decode()
    text = replace(text, 'import Quickshell.Io\n', '')
    text = replace(text, '  readonly property var defaultIndicatorEntries: [ "PasswordlessSudo", "ScreenRecording", "RemoteSession", "Reminder", "NightLight", "Dnd", "StayAwake" ]',
                   '''  // Only a reviewed caller's prebound Components can be instantiated.
  // No native backends/default indicator entries are admitted by this UI slice.
  required property var indicatorComponents
  readonly property var defaultIndicatorEntries: []
  function indicatorComponentForId(id) {
    return indicatorComponents && Object.prototype.hasOwnProperty.call(indicatorComponents, id)
      ? indicatorComponents[id] : null
  }
  function plainObject(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false
    var proto = Object.getPrototypeOf(value)
    return proto === Object.prototype || proto === null
  }''')
    if text.count('Util.isPlainObject(') != 2:
        raise ValueError('Indicator plain-object witnesses differ')
    text = text.replace('Util.isPlainObject(', 'plainObject(')
    text = replace(text, '      if (id !== "") result.push(item)',
                   '      if (id !== "" && indicatorComponentForId(id) !== null) result.push(item)')
    text = replace(text, between(text, '  ShellIpc {\n', '  Timer {\n    id: indicatorHideTimer'), '')
    text = replace(text, '  readonly property bool revealInactiveIndicators: alwaysShowIndicators ||',
                   '  // Native control slots opt in; generic original grouping remains the default.\n'
                   '  readonly property bool stableControls: setting("stableControls", false) === true\n'
                   '  readonly property bool revealInactiveIndicators: stableControls || alwaysShowIndicators ||')
    text = replace(text, '    if (inactiveIndicatorsMirrored === fixedAtStart) return',
                   '    var mirror = !stableControls && fixedAtStart\n'
                   '    if (inactiveIndicatorsMirrored === mirror) return')
    text = replace(text, '    inactiveIndicatorsMirrored = fixedAtStart',
                   '    inactiveIndicatorsMirrored = mirror')
    text = replace(text, '  onFixedAtStartChanged: syncInactiveIndicatorModel()',
                   '  onFixedAtStartChanged: syncInactiveIndicatorModel()\n'
                   '  onStableControlsChanged: {\n'
                   '    if (stableControls) {\n'
                   '      activeIndicatorIds = []\n'
                   '      indicatorActiveStates = ({})\n'
                   '      syncActiveIndicatorModel()\n'
                   '    }\n'
                   '    syncInactiveIndicatorModel()\n'
                   '  }')
    if text.count('          indicatorBlock: "inactive"') != 2:
        raise ValueError('Original inactive-block witnesses differ')
    text = text.replace('          indicatorBlock: "inactive"',
                        '          indicatorBlock: root.stableControls ? "single" : "inactive"')
    # The active model stays empty in stable mode; reuse only the original
    # ordered block, slot sizing, loader, glyph, dimming and tooltip components.
    for orientation in ('!root.vertical', 'root.vertical'):
        witness = '          reportActiveState: ' + orientation
        if text.count(witness) != 1:
            raise ValueError('Original inactive-report witness differs')
        text = replace(text, witness, witness + ' && !root.stableControls')
    text = replace(text, '      source: indicatorSlot.indicatorId ? Qt.resolvedUrl("../indicators/" + indicatorSlot.indicatorId + ".qml") : ""',
                   '      sourceComponent: root.indicatorComponentForId(indicatorSlot.indicatorId)')
    text = replace(text, '      onStatusChanged: if (status === Loader.Error) console.warn("Indicator loader error", indicatorSlot.indicatorId, source)\n', '')
    for forbidden in ('Quickshell.Io', 'ShellIpc', 'Qt.resolvedUrl', 'source:', 'Process {', 'execDetached', 'PasswordlessSudo'):
        if forbidden in text:
            raise ValueError('Unadmitted indicator loader/helper remains')
    return text.encode()
