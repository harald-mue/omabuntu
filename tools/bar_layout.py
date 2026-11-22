"""Closed widget registry and layout validation; no discovery or desktop IO.

The five visible regions are the original BarModel sections except the tray's
nested drawer. Only already reviewed Components are admitted; layout entries
cannot carry URLs, commands, inline settings, clones or arbitrary plugin ids.
"""
REGIONS = ('left', 'centerBegin', 'center', 'centerEnd', 'right')
DEFAULT = {
    'left': ['omabuntu.menu', 'omarchy.workspaces'],
    'centerBegin': [],
    'center': ['omarchy.clock'],
    'centerEnd': ['omarchy.elsewhen', 'omarchy.weather'],
    'right': ['omarchy.tray', 'omarchy.keyboard-layout', 'omarchy.bluetooth',
              'omarchy.network', 'omarchy.audio', 'omarchy.monitor', 'omarchy.power'],
}
WIDGETS = frozenset(name for entries in DEFAULT.values() for name in entries) | {'omarchy.media', 'omarchy.indicators'}


def validate(value):
    """Return detached lists; reject unknown regions, entries and duplicate ids."""
    if not isinstance(value, dict) or set(value) != set(REGIONS):
        raise ValueError('Expected the five supported bar layout sections')
    seen = set()
    result = {}
    for region in REGIONS:
        entries = value[region]
        if not isinstance(entries, list) or len(entries) > len(WIDGETS):
            raise ValueError('Invalid bar layout section')
        for name in entries:
            if not isinstance(name, str) or name not in WIDGETS or name in seen:
                raise ValueError('Unknown or repeated bar widget')
            seen.add(name)
        result[region] = list(entries)
    return result


def validate_edit(value):
    """A conditional replacement, never an arbitrary operation or field patch."""
    if not isinstance(value, dict) or set(value) != {'expected', 'layout'}:
        raise ValueError('Expected previous and replacement bar layouts')
    return {key: validate(value[key]) for key in ('expected', 'layout')}


def media_visible(layout):
    return any('omarchy.media' in entries for entries in validate(layout).values())


def with_media(layout, enabled):
    if not isinstance(enabled, bool):
        raise ValueError('Expected boolean media visibility')
    result = validate(layout)
    if enabled:
        if not media_visible(result):
            result['centerBegin'].append('omarchy.media')
    else:
        result = {region: [entry for entry in entries if entry != 'omarchy.media']
                  for region, entries in result.items()}
    return validate(result)


def indicators_visible(layout):
    return any('omarchy.indicators' in entries for entries in validate(layout).values())


def with_indicators(layout, enabled):
    if not isinstance(enabled, bool):
        raise ValueError('Expected boolean indicator visibility')
    result = validate(layout)
    if enabled:
        if not indicators_visible(result):
            result['centerBegin'].append('omarchy.indicators')
    else:
        result = {region: [entry for entry in entries if entry != 'omarchy.indicators']
                  for region, entries in result.items()}
    return validate(result)


def optional_visible(layout, key):
    if key not in ('bar-media', 'bar-indicators'):
        raise ValueError('Unsupported optional widget')
    return (media_visible if key == 'bar-media' else indicators_visible)(layout)


def with_optional(layout, key, enabled):
    if key not in ('bar-media', 'bar-indicators'):
        raise ValueError('Unsupported optional widget')
    return (with_media if key == 'bar-media' else with_indicators)(layout, enabled)


def defaults():
    return validate(DEFAULT)
