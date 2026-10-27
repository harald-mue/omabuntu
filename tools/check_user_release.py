#!/usr/bin/env python3
"""Check a relocated local release in Bubblewrap, with no host buses/display."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess

import check_runtime
import user_install

ROOT = Path(__file__).resolve().parents[1]
PROBE = '''import QtQuick
import Quickshell
import Quickshell.Bluetooth as Blue
import Quickshell.Services.UPower as Power
import Quickshell.Services.Pipewire as Audio
import Quickshell.Services.SystemTray as Tray
import Quickshell.Hyprland as WM
import "TrialPolicy.js" as Policy
ShellRoot {
  property Blue.BluetoothAdapter adapterType: null
  property Power.UPowerDevice batteryType: null
  property Audio.PwNode audioType: null
  property Tray.SystemTrayItem trayType: null
  Timer { interval:1; running:true; onTriggered: {
    var grant = Policy.prepare('{"schema_version":1,"scope":"bar-session-v1","lifetime":"session"}');
    if (!grant) { console.error("RELOCATED_POLICY_FAILED"); Qt.exit(43); return; }
    console.log("OMABUNTU_RELOCATED_IMPORTS_OK"); Qt.quit();
  } }
}
'''


def check(bundle):
    meta = user_install.verify_bundle(bundle)
    bundle = Path(bundle).absolute()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    case = ROOT / 'work/user-release-checks' / stamp
    for name in ('probe', 'home/runtime', 'home/config', 'home/cache', 'home/state', 'home/data'):
        (case / name).mkdir(mode=0o700, parents=True, exist_ok=True)
    (case / 'probe/shell.qml').write_text(PROBE)
    (case / 'probe/TrialPolicy.js').write_bytes((bundle / 'shell/TrialPolicy.js').read_bytes())
    (case / 'probe/fonts.conf').write_text('<fontconfig><dir>/usr/share/fonts</dir></fontconfig>')
    relocated = '/relocated/omabuntu/runtime'
    argv = check_runtime.sandbox_command(bundle / 'runtime', case,
        [relocated + '/bin/quickshell', '--no-color', '--path', '/probe/shell.qml'])
    # Deliberately do NOT mount the original compiled /opt prefix. This catches
    # accidental absolute runtime dependencies hidden by the normal build probe.
    argv[argv.index(check_runtime.PREFIX)] = relocated
    argv[argv.index('QML_IMPORT_PATH') + 1] = relocated + '/lib/qt6/qml'
    result = subprocess.run(argv, capture_output=True, text=True, timeout=25, check=False)
    output = result.stdout + result.stderr
    (case / 'output.log').write_text(output)
    bad = ('ERROR', 'FATAL', 'CRITICAL', 'not found', 'TypeError:', 'ReferenceError:')
    passed = (result.returncode == 0 and 'OMABUNTU_RELOCATED_IMPORTS_OK' in output
              and not any(word in output for word in bad))
    unchanged = user_install.verify_bundle(bundle) == meta
    report = {'status': 'isolated-relocation-passed' if passed and unchanged else 'failed',
              'version': meta['version'], 'returncode': result.returncode, 'bundle_unchanged': unchanged,
              'limits': 'Runtime/linkage/module relocation and session-grant parsing only. No native surfaces, host services, lock, login, installation activation or daily-use acceptance.'}
    (case / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Private relocated release check:', case / 'report.json')
    if not passed:
        print('\n'.join(line for line in output.splitlines() if any(word in line for word in bad)))
    return 0 if passed and unchanged else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    try:
        raise SystemExit(check(args.bundle))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
