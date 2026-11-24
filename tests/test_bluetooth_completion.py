"""Closed owned Bluetooth source contracts; no system bus or real device access."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_bluetooth_agent as builder
import bluetooth_fixtures
import bluetooth_qml_fixtures
import check_clock_preview as preview
from network_frontend import block


class BluetoothCompletionTests(unittest.TestCase):
    def test_sealed_shared_session_has_no_startup_agent_or_default_takeover(self):
        files, meta = preview.verified_sources(ROOT)
        session = files['BluetoothSession.qml'].decode()
        trial = files['TrialPanel.qml'].decode()
        self.assertEqual(trial.count('property BluetoothSession'), 1)
        self.assertIn('session: bars.bluetoothSession', trial)
        self.assertIn('if (ready && rpc.running) issue()', session)
        self.assertIn('devices.indexOf(capturedDevice) >= 0', session)
        self.assertIn('if (value.scope!==scope || !enabled) return', session)
        self.assertIn('value.token!==pending.token', session)
        self.assertNotIn('Component.onCompleted', session)
        self.assertNotIn('RequestDefaultAgent', session)
        self.assertEqual(meta['upstream']['BluetoothControlView.qml']['stage_transform'], 'bluetooth-agent-surface-v2')
        self.assertEqual(meta['upstream']['BluetoothPanelController.qml']['stage_transform'], 'bluetooth-owned-cursor-v2')

    def test_native_boundary_has_fixed_bus_and_no_policy_or_arbitrary_methods(self):
        text = builder.SOURCE.read_text()
        for witness in ('unix:path=/run/dbus/system_bus_socket', 'SO_PEERCRED', 'peer.uid == 0',
                        'serviceOwner("org.bluez")', 'serviceUid(owner)', 'm.service() != owner',
                        'm.signature() != signatures.value(kind)', 'device-identity-lost-at-answer',
                        'setAutoStartService(false)', 'CancelPairing', 'UnregisterAgent',
                        'usedTokens.contains(requestToken)', 'serial != generation', 'cancelled'):
            self.assertIn(witness, text)
        for forbidden in ('RequestDefaultAgent', 'ConnectProfile', 'DisconnectProfile', '"Trusted", true',
                          '"org.freedesktop.DBus.Properties", "Set"', 'qDebug', 'qWarning'):
            self.assertNotIn(forbidden, text)
        self.assertIn('"KeyboardDisplay"', text)
        self.assertNotIn('1115|1116|1117', text)

    def test_pin_ui_is_transient_original_toolkit_and_cannot_accept_hidden_actions(self):
        prompt = (ROOT / 'config/shell/preview/BluetoothPairingPrompt.qml').read_text()
        surface = (ROOT / 'config/shell/preview/BluetoothControlView.qml').read_text()
        for witness in ('Ui.TextField', 'password:true', 'codeInput.clear()', 'Qt.ImhSensitiveData',
                        'rejectButton.forceActiveFocus()', 'session.answer(id,accept,value)', 'session.cancel()'):
            self.assertIn(witness, prompt)
        self.assertIn('(!root.session || !root.session.pending) && root.cursorActive', surface)
        for forbidden in ('console.', 'FileView', 'Process {', 'execDetached'):
            self.assertNotIn(forbidden, prompt)

    def test_build_verification_rejects_test_mode_stale_source_and_changed_bytes(self):
        parent = ROOT / 'work/tests'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            binary = Path(directory) / 'agent'
            binary.write_bytes(b'\x7fELFauthored-production-fixture')
            record = {'schema_version':1, 'testing':False,
                      'source_sha256':hashlib.sha256(builder.SOURCE.read_bytes()).hexdigest(),
                      'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
            meta = binary.with_suffix('.json');meta.write_text(json.dumps(record))
            self.assertEqual(builder.verify(binary), record)
            for key,value in (('testing',True),('source_sha256','0'*64),('binary_sha256','0'*64)):
                bad=dict(record, **{key:value});meta.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):builder.verify(binary)
            meta.write_text(json.dumps(record))
            binary.write_bytes(b'\x7fELF--test-bus=')
            with self.assertRaises(ValueError):builder.verify(binary)
            with mock.patch.object(builder.os, 'access', return_value=False):
                with self.assertRaisesRegex(ValueError, 'no dependency installation attempted'):
                    builder.build(Path(directory)/'missing-compiler')
            for failure in (subprocess.CalledProcessError(1, []), subprocess.TimeoutExpired([], 10)):
                with mock.patch.object(builder.os, 'access', return_value=True), mock.patch.object(builder.subprocess, 'run', side_effect=failure):
                    with self.assertRaisesRegex(ValueError, 'probe failed or timed out; no installation attempted'):
                        builder.build(Path(directory)/'missing-qt')
            alias=Path(directory)/'outside-work';alias.symlink_to(ROOT/'tests', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'ignored work/'):
                builder.build(alias/'must-not-be-created')

    def test_packaging_and_manager_gate_are_explicit(self):
        package = (ROOT/'tools/package_user.py').read_text()
        manager = (ROOT/'tools/user_install.py').read_text()
        self.assertIn('if bluetooth_build is not None:', package)
        self.assertIn('build_bluetooth_agent.verify(bluetooth_build)', package)
        self.assertIn("env['OMABUNTU_BLUETOOTH_HELPER']", manager)
        self.assertIn('not bluetooth_agent.is_symlink()', manager)
        self.assertIn('os.access(bluetooth_agent, os.X_OK)', manager)
        self.assertIn('mode == \'lifecycle\'', bluetooth_fixtures.__loader__.get_source('bluetooth_fixtures'))
        for mode in bluetooth_qml_fixtures.MODES:
            self.assertIn(mode, ('pin','confirm','display','reject','cancel','uncertain','device-loss'))

    @unittest.skipUnless(shutil.which('node'), 'Node needed for source function state checks')
    def test_actual_session_functions_fence_scope_cancel_uncertainty_and_duplicate_writers(self):
        text = (ROOT/'config/shell/preview/BluetoothSession.qml').read_text()
        names = ('freshToken','current','send','begin','issue','fail','cancel','answer','acknowledge','receive')
        functions = []
        for name in names:
            start = next(line for line in text.splitlines() if line.startswith('  function '+name+'('))
            functions.append(block(text,start))
        program = '\n'.join(functions) + '''
const assert=require('assert');
let enabled=true,configured=true,helper='/probe/helpers/bluetooth-agent',scope='a'.repeat(24),ready=false,
 pending=null,prompt=null,capturedDevice=null,capturedAdapter=null,errorText='',uncertain=false;
let adapter={dbusPath:'/adapter'},devices=[{address:'AA',dbusPath:'/device',name:'Fixture',paired:false,connected:false}];
let writes=[],starts=[],completedEvents=[];
let rpc={running:false,stdinEnabled:false,write(v){writes.push(JSON.parse(v))},exec(v){starts.push(v);this.running=true}};
let startup={restart(){},stop(){}},watchdog={restart(){},stop(){}};
function completed(address,status){completedEvents.push({address,status})}
assert(begin(devices[0],adapter,'connecting'));assert.strictEqual(starts.length,1);assert.strictEqual(writes.length,0);
assert(!begin(devices[0],adapter,'connecting'));
receive(JSON.stringify({scope:'old',event:'ready'}));assert.strictEqual(writes.length,0);
receive(JSON.stringify({scope,event:'ready'}));assert.strictEqual(writes.length,1);
receive(JSON.stringify({scope,event:'ready'}));assert.strictEqual(writes.length,1);
let token=pending.token;
receive(JSON.stringify({scope,event:'prompt',token:'old',prompt_id:'1',kind:'RequestPinCode'}));assert.strictEqual(prompt,null);
receive(JSON.stringify({scope,event:'prompt',token,prompt_id:'1',kind:'RequestPinCode'}));assert(prompt);
assert(!answer('old',true,'AB12'));assert(answer('1',true,'AB12'));assert.strictEqual(writes.length,2);
assert(cancel());assert.strictEqual(writes[2].op,'cancel');assert.strictEqual(prompt,null);
receive(JSON.stringify({scope,event:'result',token,status:'uncertain',error:'org.freedesktop.DBus.Error.NoReply'}));
assert(uncertain&&!pending);assert(!begin(devices[0],adapter,'connecting'));
let before=writes.length;assert(acknowledge());assert.strictEqual(writes.length,before);assert(!uncertain);
assert(begin(devices[0],adapter,'connecting'));let old=pending.token;receive(JSON.stringify({scope,event:'result',token:old,status:'cancelled',error:''}));
assert(!pending);receive(JSON.stringify({scope,event:'prompt',token:old,prompt_id:'2',kind:'RequestPinCode'}));assert.strictEqual(prompt,null);
console.log('owned-session-state-ok');'''
        result=subprocess.run(['node','-e',program],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'owned-session-state-ok')

    @unittest.skipUnless(shutil.which('node'), 'Node needed for actual primitive-row resolver')
    def test_stale_row_cannot_retarget_recreated_device_or_different_output(self):
        text=(ROOT/'config/shell/preview/BluetoothActions.qml').read_text()
        functions=[]
        for name in ('resolveDevice','projectDevice','resolveRow'):
            start=next(line for line in text.splitlines() if line.startswith('  function '+name+'('))
            functions.append(block(text,start))
        program='\n'.join(functions)+'''
const assert=require('assert');let adapter={dbusPath:'/adapter'},rowOwner='first',rowCounter={value:0},rowIdentities=new WeakMap();
const DeviceModel={deviceRow(d){return {address:d.address,name:d.name}}};
let device={address:'AA',dbusPath:'/device',name:'Fixture'},devices=[device];
let row={dev:projectDevice(device)};assert.strictEqual(resolveRow(row),device);assert(Object.isFrozen(row.dev.control));
devices=[Object.assign({},device)];assert.strictEqual(resolveRow(row),null);
let fresh={dev:projectDevice(devices[0])};assert.strictEqual(resolveRow(fresh),devices[0]);
rowOwner='second';assert.strictEqual(resolveRow(fresh),null);
console.log('stale-bluetooth-row-ok');'''
        result=subprocess.run(['node','-e',program],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'stale-bluetooth-row-ok')


if __name__=='__main__':unittest.main()
