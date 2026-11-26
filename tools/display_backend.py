#!/usr/bin/env python3
"""Original monitor controls with bounded, backed-up Ubuntu actions.

No shell commands, compositor reloads, profile application or provisioning.
Text size is shell-local. Output switches retain the last-active-output guard;
owner/topology readback and private backups are not server-side atomicity.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

import display_common

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


def control_key(monitors, owner):
    fields = ('name', 'make', 'model', 'serial', 'disabled', 'width', 'height',
              'refreshRate', 'x', 'y', 'scale', 'transform', 'mirrorOf')
    outputs = sorted(({k: m.get(k) for k in fields} for m in monitors),
                     key=lambda m: m['name'])
    return hashlib.sha256(json.dumps({'owner': owner, 'outputs': outputs},
                         sort_keys=True, allow_nan=False).encode()).hexdigest()


def status(native=None):
    native = native or display_common.Native()
    monitors = native.inventory()
    if not isinstance(monitors, list):
        raise ValueError('Unexpected monitor report')
    return {'displays': monitors, 'backlight': backlight(),
            'control_key': control_key(monitors, native.owner)}


def toggle_program(monitors, output, enabled):
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', output) or type(enabled) is not bool:
        raise ValueError('Unsupported output or enabled state')
    if any(type(m.get('disabled', False)) is not bool for m in monitors):
        raise ValueError('Invalid output state')
    matches = [m for m in monitors if m['name'] == output]
    if len(matches) != 1 or (not matches[0].get('disabled', False)) != enabled:
        raise ValueError('Output changed; refresh before switching')
    if enabled and sum(not m.get('disabled', False) for m in monitors) <= 1:
        raise ValueError('Refusing to disable the last active output')
    # Same partial update as the original panel. Do not validate/rewrite the
    # full layout: existing gaps are not an error in normal monitor controls.
    return ('hl.monitor({ output = ' + json.dumps(output) + ', disabled = '
            + str(enabled).lower() + ' }); return "ok"')


def toggle(native, guard, output, enabled, expected):
    if not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected):
        raise ValueError('Missing display observation; refresh before switching')
    with guard.lock():
        guard.idle()
        before = status(native)
        if before['control_key'] != expected:
            raise ValueError('Display state or compositor owner changed; refresh before switching')
        program = toggle_program(before['displays'], output, enabled)
        backup = save_previous({'action': 'toggle', 'before': before,
                                'owner': native.owner, 'output': output,
                                'observed_enabled': enabled})
        try:
            if native.run(['eval', program]).strip() != 'ok':
                raise ValueError('Output switch was not acknowledged; check the displays')
            deadline = time.monotonic() + 3
            while True:
                after = status(native)
                matches = [m for m in after['displays'] if m['name'] == output]
                if len(matches) != 1:
                    raise ValueError('Output disappeared; switch outcome is uncertain')
                if (not matches[0].get('disabled', False)) == (not enabled):
                    if not any(not m.get('disabled', False) for m in after['displays']):
                        raise ValueError('No active output observed; external state changed')
                    display_common.put(backup.with_suffix('.outcome.json'),
                                         {'status': 'observed', 'after': after})
                    return after
                if time.monotonic() >= deadline:
                    raise ValueError('Output switch not observed; check the displays')
                time.sleep(.1)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            display_common.put(backup.with_suffix('.outcome.json'),
                                 {'status': 'uncertain', 'error': str(error)[:256]})
            raise


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
    # Fields/merge verified against Hyprland 0.57.0 LuaBindingsConfigRules.cpp.
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
        json.dump(state, stream, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'brightness', 'scale', 'text', 'toggle'))
    parser.add_argument('values', nargs='*')
    args = parser.parse_args(argv)
    state = status() if args.action in ('status', 'brightness', 'scale') else None
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
        # Cooperate with profile confirmation/recovery and automation; never let
        # the older scale slider bypass a pending profile transaction.
        guard = display_common.State()
        with guard.lock():
            guard.idle()
            state = status()
            program = scale_program(state['displays'], args.values[0], scale)
            save_previous(state)
            if run(['hyprctl', 'eval', program]).strip() != 'ok':
                raise ValueError('Runtime scale was not acknowledged')
    elif args.action == 'text':
        if len(args.values) != 1 or not re.fullmatch(r'\d{1,2}', args.values[0]):
            raise ValueError('Expected shell text size')
        native = display_common.Native()
        display_common.State().set_text(int(args.values[0]))
        state = status(native)
    elif args.action == 'toggle':
        if len(args.values) != 3 or args.values[1] not in ('true', 'false'):
            raise ValueError('Expected output, observed enabled state and observation key')
        state = toggle(display_common.Native(), display_common.State(),
                       args.values[0], args.values[1] == 'true', args.values[2])
    elif args.values:
        raise ValueError('Status takes no arguments')
    print(json.dumps(state if args.action in ('status', 'toggle', 'text') else status()))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(json.dumps({'error': str(error)}))
        raise SystemExit(1)
