"""Shared-library upgrade decision: not required, and not permitted.

The additive installer may add missing packages. It does not upgrade or remove
installed packages. Native compositor/Qt/lock packages can never be upgraded
here, even if a future caller passes a name list.
"""
NATIVE = {'hyprland', 'libqt6core6t64', 'hyprlock'}


def classify(transaction, allow=()):
    if not isinstance(transaction, dict):
        raise ValueError('Package transaction is missing')
    upgrades = transaction.get('upgraded_or_changed') or []
    removals = transaction.get('removed') or []
    if any(not isinstance(name, str) for name in [*upgrades, *removals]):
        raise ValueError('Package transaction names are invalid')
    names = [name.split(':', 1)[0] for name in upgrades]
    if removals:
        return {'required': False, 'permitted': False, 'upgrades': upgrades,
                'reason': 'Removals are refused and are not a shared-library upgrade policy'}
    if not upgrades:
        return {'required': False, 'permitted': True, 'upgrades': [],
                'reason': 'No installed package changes; a shared-library upgrade policy is not required'}
    if any(name in NATIVE for name in names) or any(name not in set(allow) for name in names):
        return {'required': True, 'permitted': False, 'upgrades': upgrades,
                'reason': 'Installed package upgrades remain refused; no shared-library upgrade is approved'}
    return {'required': True, 'permitted': False, 'upgrades': upgrades,
            'reason': 'A name list is not approval to upgrade shared libraries'}
