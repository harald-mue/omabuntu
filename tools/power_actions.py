#!/usr/bin/env python3
"""Normal session actions; explicit grants only for suspend/hibernate.

Logout/reboot/shutdown need no application-only grant, including legacy
installations. Ubuntu authorization and inhibitors remain in force. Logout
validates the current Hyprland socket and targets only that compositor or
its exact UWSM unit. No broad user termination or forced window closing.

CLI: power_actions.py <verb> | enable <verb> | gates
Legacy ordinary-action flags remain readable but no longer control availability.
An enabled hibernate gate does not establish a working resume path.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import menu_common


VERBS = ('suspend', 'hibernate', 'logout', 'reboot', 'shutdown')
ALIASES = {'poweroff': 'shutdown'}
SLEEP_VERBS = ('suspend', 'hibernate')
UWSM_UNIT = re.compile(r'wayland-wm@[A-Za-z0-9_.@\\\-]+\.service\Z')
EXIT = ['hyprctl', 'dispatch', 'hl.dsp.exit()']


def logout_command(run, env=None, proc_root='/proc', runtime_root=None):
    """Validate the current instance; honor ordered UWSM shutdown when managed.

    UWSM documents stopping the exact wayland-wm@ instance. Identify it from
    the compositor's cgroup, not an inherited flag or another active session.
    """
    env = os.environ if env is None else env
    signature = env.get('HYPRLAND_INSTANCE_SIGNATURE', '')
    display = env.get('WAYLAND_DISPLAY', '')
    runtime = Path(runtime_root) if runtime_root is not None else Path('/run/user') / str(os.getuid())
    if ('hyprland' not in env.get('XDG_CURRENT_DESKTOP', '').lower().split(':')
            or not re.fullmatch(r'[A-Za-z0-9_.-]+', signature)
            or not re.fullmatch(r'wayland-\d+', display)
            or env.get('XDG_RUNTIME_DIR', str(runtime)) != str(runtime)
            or not (runtime / display).is_socket()
            or not (runtime / 'hypr' / signature / '.socket.sock').is_socket()):
        raise ValueError('Logout requires the current live Hyprland session, not GNOME or a TTY.')
    code, output = run(['hyprctl', 'instances', '-j'])
    instances = json.loads(output) if code == 0 else None
    if not isinstance(instances, list):
        raise ValueError('Could not verify the current Hyprland instance.')
    matches = [i for i in instances if isinstance(i, dict) and i.get('instance') == signature
               and i.get('wl_socket') == display]
    if len(matches) != 1 or type(matches[0].get('pid')) is not int or matches[0]['pid'] <= 1:
        raise ValueError('Logout environment does not match one live Hyprland instance.')
    pid = matches[0]['pid']
    process = Path(proc_root) / str(pid)
    if process.stat().st_uid != os.getuid():
        raise ValueError('Logout compositor is not owned by this user.')
    units = {part for line in (process / 'cgroup').read_text().splitlines()
             for part in line.split(':', 2)[-1].split('/') if UWSM_UNIT.fullmatch(part)}
    if len(units) > 1:
        raise ValueError('Ambiguous compositor service; logout was not attempted.')
    if units:
        unit = units.pop()
        code, output = run(['systemctl', '--user', 'show', unit, '--property=MainPID', '--value'])
        if code != 0 or output.strip() != str(pid):
            raise ValueError('UWSM service identity changed; logout was not attempted.')
        return ['systemctl', '--user', 'stop', unit]
    return list(EXIT)


def canonical(verb):
    """Map the menu's poweroff action onto the shutdown gate."""
    if not isinstance(verb, str):
        return verb
    return ALIASES.get(verb, verb)


def _commands(verb, run=None):
    """Exact command list per verb; logout is resolved after session validation."""
    if verb == 'suspend':
        return ['systemctl', 'suspend']
    if verb == 'hibernate':
        return ['systemctl', 'hibernate']
    if verb == 'logout':
        return logout_command(run)
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
    """Run an ordinary action, or a sleep action after its explicit gate.

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
    if verb in SLEEP_VERBS and not gates(root).get(verb):
        return {'ok': False, 'error': 'gate',
                'message': verb.capitalize() + ' requires a separate safety/recovery approval.'}
    if run is None:
        run = live_run
    try:
        command = _commands(verb, run)
        code, output = run(command)
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'timeout', 'message': verb.capitalize() + ' command timed out.'}
    except (OSError, ValueError) as error:
        return {'ok': False, 'error': 'failed', 'message': str(error)[:600]}
    if code != 0 or (command == EXIT and str(output).strip().lower() not in ('', 'ok')):
        detail = ' '.join(str(output).split())[:500]
        return {'ok': False, 'error': 'failed',
                'message': verb.capitalize() + ' failed' + (': ' + detail if detail else '.')}
    return {'ok': True}


def live_run(argv, timeout=10):
    """Run one reviewed power command; the argument list is fixed above."""
    fixed = [['systemctl', verb] for verb in ('suspend', 'hibernate', 'reboot', 'poweroff')]
    fixed += [EXIT, ['hyprctl', 'instances', '-j']]
    unit_command = (isinstance(argv, list) and len(argv) >= 4 and argv[:2] == ['systemctl', '--user']
                    and UWSM_UNIT.fullmatch(argv[3]) and
                    ((len(argv) == 4 and argv[2] == 'stop') or
                     (len(argv) == 6 and argv[2] == 'show' and argv[4:] == ['--property=MainPID', '--value'])))
    if not isinstance(argv, list) or (argv not in fixed and not unit_command):
        raise ValueError('Refused power command: %r' % (argv,))
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    return completed.returncode, (completed.stdout or '') + (completed.stderr or '')


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
