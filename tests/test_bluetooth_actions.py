"""Exercise actual QML action functions with fake devices, never system BlueZ."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from network_frontend import block
import check_desktop_panels as desktop


class BluetoothActionTests(unittest.TestCase):
    def source(self):
        return (ROOT / 'config/shell/preview/BluetoothActions.qml').read_text()

    def test_pending_is_not_success_and_has_bounded_ownership(self):
        text = self.source()
        for contract in ('device.dbusPath', 'adapter.dbusPath', 'devices.indexOf(device)',
                         'deadline:Date.now() + 30000', 'Date.now() >= record.deadline',
                         'record.phase === "pairing"', '!found.pairing', 'onAdapterChanged:',
                         'onDevicesChanged: syncPendingActions()', 'found.connect()'):
            self.assertIn(contract, text)
        self.assertNotIn('pairingAddress', text)
        for forbidden in ('trusted =', 'wakeAllowed =', 'Pipewire', 'Process {', 'execDetached', 'registerAgent'):
            self.assertNotIn(forbidden, text)

    def test_isolated_desktop_fixture_covers_async_failure_paths(self):
        for marker in ('Pair first without claiming connection', 'Duplicate pair rejected',
                       'Pair followup issued once, not marked successful', 'Deadline reports uncertainty',
                       'Removed device is never replayed', 'Adapter ownership loss clears pending',
                       'Invocation failure is not completion', 'OMABUNTU_BLUETOOTH_ACTION_OWNERSHIP_OK'):
            self.assertIn(marker, desktop.PROBE)

    @unittest.skipUnless(shutil.which('node'), 'Node required for pure-JS action checks')
    def test_actual_action_bodies_with_fake_native_api(self):
        text = self.source()
        names = ('pendingAction', 'resolveDevice', 'beginDeviceAction', 'connectDevice',
                 'disconnectDevice', 'forgetDevice', 'syncPendingActions')
        functions = []
        for name in names:
            start = next(line for line in text.splitlines() if line.startswith('  function ' + name + '('))
            functions.append(block(text, start))
        program = '\n'.join(functions) + '''
const assert=require('assert');
let adapter={enabled:true,dbusPath:'/adapter'},pendingRecords={},errorText='';
const d={address:'AA',dbusPath:'/device',connected:false,paired:false,bonded:false,trusted:false,
  pairing:true,blocked:false,pairs:0,connects:0,pair(){this.pairs++},connect(){this.connects++}};
let devices=[d];
assert(connectDevice(d));assert.strictEqual(d.pairs,1);assert.strictEqual(pendingAction('AA'),'connecting');
assert(!connectDevice(d));assert.strictEqual(d.pairs,1);
syncPendingActions();assert.strictEqual(d.connects,0);
d.paired=true;d.pairing=false;syncPendingActions();syncPendingActions();
assert.strictEqual(d.connects,1);assert.strictEqual(pendingAction('AA'),'connecting');
d.connected=true;syncPendingActions();assert.strictEqual(pendingAction('AA'),'');
d.connected=false;assert(connectDevice(d));pendingRecords.AA.deadline=0;syncPendingActions();
assert.strictEqual(pendingAction('AA'),'');assert(errorText);
assert(connectDevice(d));devices=[];syncPendingActions();assert.strictEqual(pendingAction('AA'),'');
assert(!connectDevice(d));devices=[d];
assert(connectDevice(d));adapter={enabled:true,dbusPath:'/other'};syncPendingActions();
assert.strictEqual(pendingAction('AA'),'');
assert(connectDevice(d));adapter.enabled=false;syncPendingActions();
assert.strictEqual(pendingAction('AA'),'');assert(!connectDevice(d));adapter.enabled=true;
d.connect=function(){throw Error('fixture');};
assert(!connectDevice(d));assert.strictEqual(pendingAction('AA'),'');
assert(!beginDeviceAction(d,'unreviewed'));
console.log(JSON.stringify({passed:true}));
'''
        result = subprocess.run(['node', '-e', program], capture_output=True, text=True,
                                timeout=10, check=True)
        self.assertEqual(json.loads(result.stdout), {'passed': True})


if __name__ == '__main__':
    unittest.main()
