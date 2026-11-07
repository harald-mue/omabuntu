"""Shared stable native-family admission, separate from plugin ABI acceptance.

Build baselines are not exact host package locks. These bounds admit patch
versions to further runtime/configuration checks; they do not certify every
future patch or authorize package upgrades, plugin loading or authentication.
"""
import json
import re

FAMILIES = {
    'hyprland': ((0, 57, 0), (0, 58, 0)),
    'qt': ((6, 10, 2), (6, 11, 0)),
    'hyprlock': ((0, 9, 6), (0, 10, 0)),
}
# Version-specific regressions can be excluded without widening other families.
EXCLUDED = {name: {} for name in FAMILIES}
PACKAGES = {'hyprland': 'hyprland', 'libqt6core6t64': 'qt', 'hyprlock': 'hyprlock'}
NUMBER = r'(?:0|[1-9][0-9]*)'
STABLE = re.compile(
    r'(?:[0-9]+:)?(?P<version>' + NUMBER + r'\.' + NUMBER + r'\.' + NUMBER + r')'
    r'(?:\+(?:dfsg|ds)(?:[0-9]+|\.[0-9]+)?)?(?:-[0-9][A-Za-z0-9.+~]*)?\Z')


def version_text(value):
    return '.'.join(map(str, value))


def policy():
    return {'schema_version': 1, 'families': {
        name: {'minimum': version_text(bounds[0]), 'before': version_text(bounds[1]),
               'excluded': dict(EXCLUDED[name])} for name, bounds in FAMILIES.items()}}


def parse(value):
    match = STABLE.fullmatch(value) if isinstance(value, str) else None
    if not match:
        return None
    return tuple(map(int, match['version'].split('.')))


def assess(component, value, source, *, failure=None):
    minimum, before = FAMILIES[component]
    parsed = parse(value)
    normalized = version_text(parsed) if parsed is not None else None
    expected = '>=' + version_text(minimum) + ', <' + version_text(before)
    reason = failure
    if reason is None:
        if value in (None, '', '(none)'):
            reason = 'No installed version or APT candidate was available.'
        elif parsed is None:
            reason = 'Not a recognized stable version; development/prerelease or malformed versions are not admitted.'
        elif normalized in EXCLUDED[component]:
            reason = 'Known incompatible version: ' + EXCLUDED[component][normalized]
        elif not minimum <= parsed < before:
            reason = 'Outside the supported API family or below its minimum version.'
    ok = reason is None
    next_step = ('Continue with runtime checks; plugin ABI and lock recovery remain separate gates.' if ok else
                 'Check the detected package/probe and use a supported stable family. '
                 'New families need compatibility review; do not force an install or downgrade.')
    shown = json.dumps(value, ensure_ascii=True) if isinstance(value, str) else 'unavailable'
    message = '%s: %s detected %s; supported %s. %s' % (
        component, source, shown, expected, 'Family admitted.' if ok else reason)
    if not ok:
        message += ' Next: ' + next_step
    return {'component': component, 'source': source, 'detected': value, 'upstream': normalized,
            'supported': expected, 'ok': ok, 'reason': reason, 'next_step': next_step, 'message': message}


def hyprland_binary(probe):
    """Hyprland --version-json exits before starting a compositor."""
    source = 'installed Hyprland binary (--version-json)'
    if probe.get('status') != 'ok':
        return assess('hyprland', None, source,
                      failure='Binary metadata probe failed: ' + str(probe.get('status', 'unknown')) + '.')
    try:
        native = json.loads(probe.get('stdout', ''))
    except (ValueError, TypeError):
        native = None
    return hyprland_metadata(native, source)


def hyprland_metadata(native, source):
    if not isinstance(native, dict):
        return assess('hyprland', None, source, failure='Invalid or missing binary JSON metadata.')
    failure = None
    if native.get('dirty') is not False or not re.fullmatch(r'[a-f0-9]{40}', str(native.get('commit', ''))):
        failure = 'A clean build with valid commit metadata is required; no plugin ABI was inferred.'
    return assess('hyprland', native.get('version'), source, failure=failure)


def hyprlock_binary(probe):
    source = 'installed Hyprlock binary (--version)'
    if probe.get('status') != 'ok':
        return assess('hyprlock', None, source,
                      failure='Binary version probe failed: ' + str(probe.get('status', 'unknown')) + '.')
    text = probe.get('stdout', '') + probe.get('stderr', '')
    matches = re.findall(r'(?m)^Hyprlock version v([^\s]+)(?:\s|$)', text)
    return assess('hyprlock', matches[0] if len(matches) == 1 else None, source)


def package_checks(payload):
    # Local imports avoid a dependency cycle with the installer/package planner.
    import install as guided
    import package_plan
    candidates = package_plan.parse_policy(payload['policy'])
    checks = []
    for package, component in PACKAGES.items():
        installed = guided.package_version(payload['before'], package)
        candidate = candidates.get(package, {}).get('candidate')
        row = assess(component, installed or candidate, 'installed package' if installed else 'APT candidate')
        checks.append(dict(row, package=package, installed=installed, candidate=candidate))
    return checks
