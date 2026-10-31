"""User-state schema policy. No migration is registered or performed.

Schema 1 is the only understood state. A newer or older schema needs an explicit
reviewed migration pair before any state file may be rewritten. Rollback is safe
only when both releases use the same schema, or both directions are reviewed.
"""
CURRENT = 1
MIGRATIONS = {}
KNOWN_PATHS = ('settings/weather.json', 'current/workspace-layouts.txt', 'session-config.json',
               'session-activation.json')


class SchemaError(ValueError):
    pass


def decision(installed, incoming):
    if type(incoming) is not int or incoming != CURRENT:
        raise SchemaError('Incoming user-state schema is not the understood schema %s; no state rewrite' % CURRENT)
    if installed is not None and (type(installed) is not int or installed < 1):
        raise SchemaError('Installed user-state schema is not a supported integer')
    if installed in (None, incoming):
        return {'action': 'none', 'from': installed, 'to': incoming, 'rollback_safe': True,
                'writes_state': False, 'registered_migration': False}
    if (installed, incoming) not in MIGRATIONS or (incoming, installed) not in MIGRATIONS:
        raise SchemaError('No reviewed bidirectional migration for user state schema %s -> %s; no state rewrite' % (installed, incoming))
    return {'action': 'reviewed-migration-required', 'from': installed, 'to': incoming,
            'rollback_safe': True, 'writes_state': False, 'registered_migration': True}


def inventory(state):
    """Name existing known state files. Do not read or print their contents."""
    result = []
    if state is None or not state.exists():
        return result
    for relative in KNOWN_PATHS:
        path = state / relative
        if path.is_symlink():
            raise SchemaError('Symlinked user state requires manual review: ' + relative)
        if path.exists():
            if not path.is_file() or path.stat().st_size > 1024 * 1024:
                raise SchemaError('Unexpected user state file: ' + relative)
            result.append({'path': relative, 'bytes': path.stat().st_size})
    return result
