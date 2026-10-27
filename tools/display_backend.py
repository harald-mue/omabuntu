#!/usr/bin/env python3
"""Bounded Ubuntu display adapter: read status, logind brightness, runtime scale.

No configuration files, shell commands, reloads, output disabling or provisioning.
Before each mutation, save the previous readings privately under the installed
state directory, or ignored work/ when running the development trial.
"""
import argparse
import datetime
import json
import math
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCALES = (1, 1.25, 1.5, 1.6, 2, 3, 4)


def run(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=8, check=False)
    if result.returncode:
        raise ValueError("Display backend command failed: " + argv[0])
    return result.stdout


def backlight():
    for path in sorted(Path('/sys/class/backlight').glob('*')):
        maximum = int((path / 'max_brightness').read_text())
        value = int((path / 'brightness').read_text())
        if maximum > 0 and re.fullmatch(r'[A-Za-z0-9_-]+', path.name):
            return {'name': path.name, 'maximum': maximum, 'value': value,
                    'percent': round(value * 100 / maximum)}
    return None


def status():
    monitors = json.loads(run(['hyprctl', 'monitors', 'all', '-j']))
    if not isinstance(monitors, list):
        raise ValueError('Unexpected monitor report')
    return {'displays': monitors, 'backlight': backlight()}


def scale_program(monitors, output, scale):
    if type(scale) not in (int, float) or not re.fullmatch(r'[A-Za-z0-9_.-]+', output) or scale not in SCALES:
        raise ValueError('Unsupported output or scale')
    matches = [m for m in monitors if m['name'] == output and not m.get('disabled')]
    if len(matches) != 1:
        raise ValueError('Output is no longer active')
    monitor = matches[0]
    width, height = monitor['width'], monitor['height']
    if any(abs(n / scale - round(n / scale)) > 0.00001 for n in (width, height)):
        raise ValueError('Scale does not produce integral logical pixels')
    if monitor.get('transform', 0) % 2:
        width, height = height, width
    x, y = monitor['x'], monitor['y']
    for other in monitors:
        if other['name'] == output or other.get('disabled'):
            continue
        ow, oh = other['width'], other['height']
        if other.get('transform', 0) % 2:
            ow, oh = oh, ow
        ox, oy, oscale = other['x'], other['y'], other['scale']
        if (max(x, ox) < min(x + width / scale, ox + ow / oscale)
                and max(y, oy) < min(y + height / scale, oy + oh / oscale)):
            raise ValueError('Scale would overlap another output; layout left unchanged')
    # Fields verified against Hyprland v0.56.2 LuaBindingsConfigRules.cpp.
    # A partial rule preserves the existing mode, position, transform and colors.
    return 'hl.monitor({ output = ' + json.dumps(output) + ', scale = ' + str(scale) + ' }); return "ok"'


def save_previous(state):
    installed_state = os.environ.get('OMABUNTU_STATE_HOME')
    directory = Path(installed_state) / 'desktop-actions' if installed_state else ROOT / 'work/desktop-actions'
    if not directory.is_absolute() or '..' in directory.parts:
        raise ValueError('Invalid display backup directory')
    if any(path.is_symlink() for path in (directory, *directory.parents)):
        raise ValueError('Symlinked display backup directory')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.stat().st_uid != os.getuid() or directory.stat().st_mode & 0o077:
        raise ValueError('Display backup directory must be owned and private')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    path = directory / (stamp + '.json')
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(state, stream)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'brightness', 'scale'))
    parser.add_argument('values', nargs='*')
    args = parser.parse_args(argv)
    state = status()
    if args.action == 'brightness':
        if len(args.values) != 1 or not re.fullmatch(r'\d{1,3}', args.values[0]):
            raise ValueError('Expected brightness percent')
        percent = int(args.values[0])
        light = state['backlight']
        if not 1 <= percent <= 100 or not light:
            raise ValueError('Brightness unavailable or out of range')
        save_previous(state)
        raw = max(1, round(light['maximum'] * percent / 100))
        run(['busctl', '--system', 'call', 'org.freedesktop.login1',
             '/org/freedesktop/login1/session/auto', 'org.freedesktop.login1.Session',
             'SetBrightness', 'ssu', 'backlight', light['name'], str(raw)])
    elif args.action == 'scale':
        if len(args.values) != 2:
            raise ValueError('Expected output and scale')
        scale = float(args.values[1])
        if not math.isfinite(scale):
            raise ValueError('Invalid scale')
        program = scale_program(state['displays'], args.values[0], scale)
        save_previous(state)
        if run(['hyprctl', 'eval', program]).strip() != 'ok':
            raise ValueError('Runtime scale was not acknowledged')
    elif args.values:
        raise ValueError('Status takes no arguments')
    print(json.dumps(status() if args.action != 'status' else state))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(json.dumps({'error': str(error)}))
        raise SystemExit(1)
