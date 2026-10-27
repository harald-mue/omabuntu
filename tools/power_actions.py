#!/usr/bin/env python3
"""Gated session-ending actions for the Omabuntu system menu.

Omarchy's system menu runs `systemctl suspend`, `systemctl hibernate`,
`omarchy-system logout/reboot/shutdown` directly (pinned commit 03ff1eff,
bin/omarchy-system). This Ubuntu adaptation keeps the same five actions but
refuses every one until its gate flag is present in the state file
`current/power-gates.json` (schema {"gates": {"suspend": true, ...}}). Gates
are granted only by an explicit user-approved step; the menu never writes
this file. Suspend and hibernate additionally require the kernel to report
the power state, mirroring upstream's availability guards. The shutdown
row's action is `systemctl:poweroff`; that name is the same gate as
`shutdown`. An enabled hibernate gate is the approval to run hibernate;
this helper does not inspect the resume path.

CLI: power_actions.py <verb>            run one gated action (if approved)
      power_actions.py enable <verb>     record a gate flag (explicit user step)
      power_actions.py gates             print the current gate state as JSON
"""
import json
import subprocess
import sys

import menu_common


VERBS = ('suspend', 'hibernate', 'logout', 'reboot', 'shutdown')
ALIASES = {'poweroff': 'shutdown'}


def canonical(verb):
    """Map the menu's poweroff action onto the shutdown gate."""
    if not isinstance(verb, str):
        return verb
    return ALIASES.get(verb, verb)


def _commands(verb, run=None):
    """Exact command list per verb; the UWSM session maps logout to uwsm stop."""
    if verb == 'suspend':
        return ['systemctl', 'suspend']
    if verb == 'hibernate':
        return ['systemctl', 'hibernate']
    if verb == 'logout':
        return ['uwsm', 'stop']
    if verb == 'reboot':
        return ['systemctl', 'reboot']
    if verb == 'shutdown':
        return ['systemctl', 'poweroff']
    return None


def power_states(path='/sys/power/state'):
    try:
        return Path_read(path)
    except OSError:
        return ''


def Path_read(path):
    with open(path, encoding='ascii') as stream:
        return stream.read()


def can_suspend(states=None):
    states = power_states() if states is None else states
    return 'mem' in states.split() or 'freeze' in states.split()


def can_hibernate(states=None):
    states = power_states() if states is None else states
    return 'disk' in states.split()


def gates(root=None):
    payload = menu_common.read_json(menu_common.state_home(root) / 'current' / 'power-gates.json')
    if not isinstance(payload, dict) or not isinstance(payload.get('gates'), dict):
        return {}
    return {name: bool(value) for name, value in payload['gates'].items() if isinstance(name, str)}


def enable(verb, root=None):
    verb = canonical(verb)
    if verb not in VERBS:
        raise ValueError('Unknown power action: %s' % verb)
    home = menu_common.state_home(root)
    path = home / 'current' / 'power-gates.json'
    payload = menu_common.read_json(path) or {'schema_version': 1, 'gates': {}}
    if not isinstance(payload, dict) or not isinstance(payload.get('gates'), dict):
        payload = {'schema_version': 1, 'gates': {}}
    payload['gates'][verb] = True
    menu_common.backup_and_write(path, lambda target: menu_common.write_json(target, payload))
    menu_common.record('power-gate-enable', verb)
    return {'ok': True, 'verb': verb}


def perform(verb, run=None, root=None, states=None):
    """Run one session-ending action after its gate. Returns a result dict.

    run(argv) -> (returncode, stdout) defaults to the restricted live runner;
    tests inject a fake. Refusals are {'ok': False, 'error': ...} and never
    execute anything.
    """
    verb = canonical(verb)
    if verb not in VERBS:
        return {'ok': False, 'error': 'refused', 'message': 'Unknown power action.'}
    if verb == 'suspend' and not can_suspend(states):
        return {'ok': False, 'error': 'refused', 'message': 'Suspend is not available.'}
    if verb == 'hibernate' and not can_hibernate(states):
        return {'ok': False, 'error': 'refused', 'message': 'Hibernate is not available.'}
    if not gates(root).get(verb):
        return {'ok': False, 'error': 'gate',
                'message': 'Power actions are not enabled yet.'}
    command = _commands(verb)
    if run is None:
        run = live_run
    code, _ = run(command)
    return {'ok': code == 0} if code == 0 else {'ok': False, 'error': 'failed'}


def live_run(argv, timeout=10):
    """Run one reviewed power command; the argument list is fixed above."""
    if not isinstance(argv, list) or len(argv) != 2 or argv[0] not in ('systemctl', 'uwsm') \
            or argv[1] not in ('suspend', 'hibernate', 'reboot', 'poweroff', 'stop') \
            or (argv[0] == 'systemctl') != (argv[1] != 'stop'):
        raise ValueError('Refused power command: %r' % (argv,))
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    return completed.returncode, completed.stdout


def main(argv):
    if len(argv) == 2 and argv[0] == 'enable':
        print(json.dumps(enable(argv[1])))
        return 0
    if len(argv) == 1 and argv[0] == 'gates':
        print(json.dumps({'ok': True, 'gates': gates()}))
        return 0
    if len(argv) == 1 and canonical(argv[0]) in VERBS:
        print(json.dumps(perform(argv[0])))
        return 0
    print(json.dumps({'ok': False, 'error': 'usage'}))
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
