"""Original Network surface, passive details and request ownership; no live network."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from test_widget_preferences import qml_function

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check_clock_preview as preview
import network_frontend
import network_nm as nm

NODE = shutil.which('node')


class NetworkDetailsTests(unittest.TestCase):
    def collector(self, row=None, gateway='192.0.2.1\n', speed=2500):
        calls = []
        row = row if row is not None else {
            'ifname': 'fixture0', 'address': '02:00:00:00:00:01',
            'addr_info': [{'family': 'inet6', 'local': '2001:db8::2', 'scope': 'global'},
                          {'family': 'inet', 'local': '192.0.2.2', 'scope': 'global'}],
            'stats64': {'rx': {'bytes': 12345}, 'tx': {'bytes': 9876}}}

        def run(argv, timeout):
            calls.append((argv, timeout))
            if argv[0] == 'ip':
                return 0, json.dumps([row])
            return 0, gateway
        result = nm.details(run, 'fixture0', speed_reader=lambda iface: speed, counter_reader=lambda iface: {})
        return result, calls

    def test_exact_interface_ip_gateway_counters_and_link_speed(self):
        result, calls = self.collector()
        self.assertEqual(result['details'], {'iface': 'fixture0', 'ip': '192.0.2.2',
                         'gateway': '192.0.2.1', 'rx_bytes': 12345, 'tx_bytes': 9876, 'speed': 2500})
        self.assertEqual(result['missing'], [])
        self.assertEqual(calls[0][0], ['ip', '-j', '-s', 'address', 'show', 'dev', 'fixture0'])
        self.assertTrue(all(timeout == 5 for _, timeout in calls))
        for argv, _ in calls:
            self.assertFalse(set(argv) & {'ping', 'curl', 'modify', 'up', '--show-secrets', 'wifi'})

    def test_ipv6_partial_readings_and_zero_counters_are_distinguished(self):
        row = {'ifname': 'fixture0', 'addr_info': [{'scope': 'global', 'family': 'inet6', 'local': '2001:db8::2'}],
               'stats64': {'rx': {'bytes': 0}, 'tx': {'bytes': -1}}}
        result, _ = self.collector(row, gateway=r'fe80\:\:1', speed='')
        self.assertEqual(result['details']['ip'], '2001:db8::2')
        self.assertEqual(result['details']['gateway'], 'fe80::1')
        self.assertEqual(result['details']['rx_bytes'], 0)
        self.assertNotIn('tx_bytes', result['details'])
        self.assertEqual(result['missing'], ['tx_bytes', 'speed'])

    def test_missing_iproute_statistics_use_validated_read_only_counter_fallback(self):
        def run(argv, timeout):
            return (0, '[{"ifname":"fixture0"}]') if argv[0] == 'ip' else (0, '')
        result = nm.details(run, 'fixture0', speed_reader=lambda iface: '',
                            counter_reader=lambda iface: {'rx_bytes': 0, 'tx_bytes': 500, 'unknown': 1})
        self.assertEqual(result['details']['rx_bytes'], 0)
        self.assertEqual(result['details']['tx_bytes'], 500)
        self.assertNotIn('unknown', result['details'])
        self.assertEqual(result['missing'], ['ip', 'gateway', 'speed'])

    def test_missing_ip_is_never_replaced_with_hardware_address(self):
        result, _ = self.collector({'ifname': 'fixture0', 'address': '02:00:00:00:00:01'}, gateway='', speed='')
        self.assertEqual(result['details']['ip'], '')
        self.assertEqual(result['missing'], ['ip', 'gateway', 'rx_bytes', 'tx_bytes', 'speed'])

    def test_invalid_interface_and_mismatched_or_oversized_data_fail_closed(self):
        for iface in ('../net', '-help', '.', 'a' * 16, 'x;echo'):
            with self.subTest(iface=iface), self.assertRaises(nm.CommandError):
                nm.details(lambda *args: self.fail('invalid interface executed'), iface)
        for raw in ('not json', '[{}]', '[' + ' ' * 1_048_577 + ']'):
            with self.subTest(raw=raw[:10]), self.assertRaises(nm.CommandError):
                nm.details(lambda *args: (0, raw), 'fixture0', speed_reader=lambda iface: '')

    def test_missing_command_timeout_and_failed_copy_are_explicit(self):
        for token in ('missing', 'timeout'):
            def fail(*args):
                raise nm.CommandError(token)
            self.assertEqual(nm.dispatch(['nm', 'details', 'fixture0'], fail), {'ok': False, 'error': token})
        self.assertFalse(nm.dispatch(['nm', 'copy-address', '192.0.2.2'], lambda *args: (1, ''))['ok'])

    def test_copy_is_address_only_argv_without_shell(self):
        calls = []
        def run(argv, timeout):
            calls.append((argv, timeout))
            return 0, ''
        self.assertTrue(nm.dispatch(['nm', 'copy-address', '2001:db8::1'], run)['ok'])
        self.assertEqual(calls, [(['wl-copy', '--', '2001:db8::1'], 5)])
        self.assertFalse(nm.dispatch(['nm', 'copy-address', 'not an address'], run)['ok'])
        self.assertEqual(len(calls), 1)

    def test_qr_is_pinned_has_quiet_zone_and_never_returns_plaintext_secret(self):
        from test_network_nm import Fake, base_replies, UUID
        replies = base_replies()
        replies.update({
            ('nmcli', '-g', '802-11-wireless.ssid', 'connection', 'show', UUID): (0, 'Fixture'),
            ('nmcli', '-g', '802-11-wireless-security.key-mgmt', 'connection', 'show', UUID): (0, 'wpa-psk'),
            ('nmcli', '--show-secrets', '-g', '802-11-wireless-security.psk', 'connection', 'show', UUID): (0, 'fixture-only-secret'),
        })
        fake = Fake(replies)
        result = nm.qr(fake, 'wlan0')
        self.assertEqual(result['iface'], 'wlan0')
        self.assertEqual(result['ssid'], 'Fixture')
        self.assertTrue(result['secured'])
        self.assertNotIn('fixture-only-secret', json.dumps(result))
        size = result['size']
        rows = [result['modules'][i * size:(i + 1) * size] for i in range(size)]
        self.assertTrue(all(row == '0' * size for row in rows[:4] + rows[-4:]))
        self.assertTrue(all(row[:4] + row[-4:] == '0' * 8 for row in rows))
        fake = Fake(replies)
        with self.assertRaises(nm.CommandError):
            nm.qr(fake, 'other0')
        self.assertFalse(any('--show-secrets' in argv for argv in fake.calls))

    def test_speed_phase_is_bounded_and_uses_only_its_direction(self):
        for phase, key in [('down', '%{speed_download}'), ('up', '%{speed_upload}')]:
            calls = []
            def run(argv, timeout):
                calls.append((argv, timeout))
                self.assertIn(key, argv)
                if phase == 'up':
                    body = Path(argv[argv.index('--data-binary') + 1][1:])
                    self.assertEqual(body.stat().st_size, 512 * 1024)
                return 0, '1250000'
            with patch.object(nm.tempfile, 'tempdir', str(ROOT / 'work')):
                result = nm.speed_phase(run, phase)
            self.assertEqual(result, {'ok': True, 'phase': phase, 'value': 10.0})
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1], 12)
            self.assertEqual(calls[0][0][calls[0][0].index('--max-time') + 1], '8')
        for bad in ('inf', 'nan', '-1'):
            with self.assertRaises(nm.CommandError):
                nm.megabits(bad)

    @unittest.skipUnless(os.name == 'posix', 'POSIX owned-process cancellation')
    def test_dismissed_measurement_reaps_owned_fake_curl_without_network(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            home = Path(directory)
            fake = home / 'curl'
            marker = home / 'child.pid'
            fake.write_text('#!' + sys.executable + '\nimport os,time\nfrom pathlib import Path\n'
                            'Path(os.environ["FIXTURE_PID"]).write_text(str(os.getpid()))\ntime.sleep(30)\n')
            fake.chmod(0o700)
            env = dict(os.environ, PATH=str(home), FIXTURE_PID=str(marker))
            parent = subprocess.Popen([sys.executable, str(ROOT / 'tools/network_nm.py'), 'speed-phase', 'down'],
                                      env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 5
                while not marker.exists() and parent.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(marker.exists(), parent.communicate(timeout=2) if parent.poll() is not None else '')
                child = int(marker.read_text())
                parent.terminate()
                out, err = parent.communicate(timeout=5)
                self.assertEqual(out, '')
                self.assertEqual(err, '')
                with self.assertRaises(ProcessLookupError):
                    os.kill(child, 0)
            finally:
                if parent.poll() is None:
                    parent.terminate()
                    parent.communicate(timeout=5)


    @unittest.skipUnless(sys.platform == 'linux', 'Linux owned-child parent-death guard')
    def test_killed_measurement_helper_cannot_leave_fake_curl_running(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            home = Path(directory)
            fake, marker = home / 'curl', home / 'heartbeat'
            fake.write_text('#!' + sys.executable + '\nimport os,time\nfrom pathlib import Path\n'
                            'p=Path(os.environ["FIXTURE_HEARTBEAT"])\n'
                            'for i in range(1500):\n p.with_suffix(".tmp").write_text(str(os.getpid())+":"+str(i));p.with_suffix(".tmp").replace(p);time.sleep(0.02)\n')
            fake.chmod(0o700)
            env = dict(os.environ, PATH=str(home), FIXTURE_HEARTBEAT=str(marker))
            parent = subprocess.Popen([sys.executable, str(ROOT / 'tools/network_nm.py'), 'speed-phase', 'down'],
                                      env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            child = None
            try:
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if marker.exists() and ':' in marker.read_text():
                        child = int(marker.read_text().split(':')[0])
                        break
                    time.sleep(0.02)
                self.assertIsNotNone(child)
                parent.kill()
                parent.communicate(timeout=5)
                time.sleep(0.15)
                stopped = marker.read_text()
                time.sleep(0.15)
                self.assertEqual(marker.read_text(), stopped, 'Owned curl survived its helper')
            finally:
                if parent.poll() is None:
                    parent.terminate()
                    parent.communicate(timeout=5)
                if child is not None:
                    try:
                        os.killpg(child, 9)  # This fixture created and owns this group.
                    except ProcessLookupError:
                        pass


class NetworkOriginalSurfaceTests(unittest.TestCase):
    def test_original_grid_components_and_phrase_animation_are_retained(self):
        files, _ = preview.verified_sources(ROOT)
        source = (ROOT / 'vendor/omarchy/shell/plugins/panels/network/Panel.qml').read_text()
        view = files['NetworkControlView.qml'].decode()
        grid = network_frontend.between(source, '      // Connection details:', '      // Wi-Fi band selection.')
        self.assertIn(grid, view)
        components = source[source.index('  component DetailValue: InfoValue {\n'):source.rfind('}\n')]
        self.assertIn(components, view)
        phrases = network_frontend.between(source, '  Timer {\n    id: connectionPhraseTimer\n',
                                          '  Timer {\n    id: actionTimeout\n')
        self.assertIn(phrases, view)
        self.assertLess(view.index('// Connection details:'), view.index('// Wi-Fi band selection.'))
        self.assertIn('blocked: root.passwordSsid !== "" || root.customDnsOpen', view)
        self.assertNotIn('root.qrModules', view)
        self.assertNotIn('root.speedDown', view)

    def test_original_destinations_and_nonexclusive_policy_are_sealed(self):
        files, meta = preview.verified_sources(ROOT)
        for target in preview.NETWORK_TRANSFORMS:
            self.assertEqual(meta['upstream'][target]['source_modifications'], [])
            self.assertIn(b'OnDemand' if target.startswith('Ui/') else b'Controller', files[target])
        qr = files['WifiQrView.qml'].decode()
        speed = files['Ui/SpeedTestOverlay.qml'].decode()
        self.assertIn('color: "white"', qr)
        self.assertIn('LayoutMirroring.enabled: false', qr)
        self.assertNotIn('togglePassword', qr)
        self.assertNotIn('passwordVisible', qr)
        self.assertIn('component SpeedDial: Item', speed)
        self.assertIn('property string unit: "Mbps"', speed)
        self.assertNotIn('WlrKeyboardFocus.Exclusive', speed)
        controller = files['NetworkPanelController.qml'].decode()
        self.assertNotIn('device.address', controller)
        self.assertIn('Model.headerDetail(info, I18n.formatNumber)', controller)
        self.assertIn('readonly property bool hasInternetPing: false', controller)

    def test_profile_additions_are_collapsed_bounded_and_opt_in(self):
        view = (ROOT / 'config/shell/preview/NetworkControlView.qml').read_text()
        for kind in ('ethernet', 'vpn'):
            self.assertIn('visible: root.profilesOpen && root.' + kind + 'Profiles.length > 0', view)
            self.assertIn('id: ' + kind + 'ProfilesList', view)
        self.assertEqual(view.count('height: Math.min(contentHeight, Style.space(144))'), 2)
        self.assertIn('positionViewAtIndex(currentIndex, ListView.Contain)', view)
        self.assertIn('onClicked: root.toggleProfiles()', view)
        self.assertIn('root.profilesOpen && root.ethernetProfiles.length', view)


@unittest.skipUnless(NODE, 'Node required for actual-source JavaScript regressions')
class NetworkRequestTests(unittest.TestCase):
    def script(self, path, names, setup, assertions):
        source = (ROOT / path).read_text()
        code = '\n'.join(qml_function(source, name) for name in names)
        js = '''const assert=require('assert');let later=[],calls=[];
const Qt={callLater:fn=>later.push(fn)};const I18n={t:key=>key};
const console={warn:()=>{}};
''' + setup + '\nwith(root){\n' + code + '\nObject.assign(root,{' + ','.join(names) + '});}\n' + assertions
        result = subprocess.run([NODE, '-e', js], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def queue(self, assertions):
        setup = '''const root={queue:[],inFlight:null,finishing:false,opened:false,signalGeneration:0,
 nativeIface:'fixture0',serviceNote:'',dnsProvider:'DHCP',bandSelected:'auto',bandAvailable:[],
 networkHelper:()=>'/fixture/network_nm.py',applyDetails:payload=>calls.push(['details',payload]),
 applyActiveApSignal:()=>{},nmProc:{running:false,exec:args=>{calls.push(args);root.nmProc.running=true;}}};'''
        self.script('config/shell/preview/NetworkPanelController.qml',
                    ['pendingChoice', 'requestNm', 'pumpNm', 'finishNm', 'setBand', 'setDns'], setup, assertions)

    def test_band_and_dns_survive_busy_read_and_mutations_precede_poll(self):
        self.queue('''root.requestNm('status',[]);root.setBand('5');root.setDns('Google');root.requestNm('status',[]);
assert.deepEqual(root.queue.map(x=>x.kind),['band-set','dns-set','status']);
assert.equal(root.pendingChoice('band-set'),'5');
root.nmProc.running=false;root.finishNm('status',0,JSON.stringify({ok:true}));later.shift()();
assert.deepEqual(calls[1].slice(2),['band-set','5']);
root.nmProc.running=false;root.finishNm('band-set',0,JSON.stringify({ok:true}));later.shift()();
assert.equal(root.bandSelected,'5');assert.equal(root.pendingChoice('band-set'),'');
assert.deepEqual(calls[2].slice(2),['dns-set','Google']);''')

    def test_older_ack_cannot_confirm_newer_dns_and_failed_projection_reverts(self):
        self.queue('''root.setDns('Google');root.setDns('Cloudflare');
root.nmProc.running=false;root.finishNm('dns-set',0,JSON.stringify({ok:true}));
assert.equal(root.dnsProvider,'Google');assert.equal(root.pendingChoice('dns-set'),'Cloudflare');
later.shift()();root.nmProc.running=false;root.finishNm('dns-set',1,JSON.stringify({ok:true}));
assert.equal(root.dnsProvider,'Google');assert.equal(root.pendingChoice('dns-set'),'');assert.ok(root.serviceNote);''')

    def test_absolute_edits_coalesce_but_profile_order_and_bounds_are_preserved(self):
        self.queue('''root.requestNm('status',[]);root.setBand('2.4');root.setBand('5');
assert.equal(root.queue.length,1);assert.equal(root.queue[0].args[0],'5');
root.requestNm('connect',['one']);root.requestNm('disconnect',['one']);
assert.deepEqual(root.queue.map(x=>x.kind),['band-set','connect','disconnect']);
while(root.queue.length<64)root.requestNm('connect',['fixture']);
assert.equal(root.requestNm('disconnect',['overflow']),false);assert.equal(root.queue.length,64);''')

    def test_old_interface_and_nonzero_exit_cannot_publish_details(self):
        self.queue('''root.requestNm('details',['fixture0']);root.signalGeneration=1;
root.nmProc.running=false;root.finishNm('details',0,JSON.stringify({ok:true,details:{iface:'fixture0'}}));
assert.equal(calls.length,1);later.shift()();
root.requestNm('details',['fixture0']);root.nmProc.running=false;
root.finishNm('details',1,JSON.stringify({ok:true,details:{iface:'fixture0'}}));assert.equal(calls.length,2);''')

    def test_secondary_profile_rows_follow_vertical_keyboard_order(self):
        self.script('config/shell/preview/NetworkPanelController.qml', ['moveProfileCursor'], '''
const root={profilesOpen:true,focusSection:'ethernet',profileIndex:0,ethernetProfiles:[{},{}],
 vpnProfiles:[{},{}],wifiNetworks:[{}],selectedIndex:-1};
''', '''root.moveProfileCursor(1);assert.equal(root.profileIndex,1);
root.moveProfileCursor(1);assert.equal(root.focusSection,'vpn');assert.equal(root.profileIndex,0);
root.moveProfileCursor(-1);assert.equal(root.focusSection,'ethernet');assert.equal(root.profileIndex,1);
root.focusSection='vpn';root.profileIndex=1;root.moveProfileCursor(1);
assert.equal(root.focusSection,'wifi');assert.equal(root.selectedIndex,0);
root.profilesOpen=false;root.focusSection='vpn';root.moveProfileCursor(1);assert.equal(root.focusSection,'dns');''')

    def test_original_rate_logic_header_and_missing_sample_recovery(self):
        model = json.dumps(str(ROOT / 'vendor/omarchy/shell/plugins/panels/network/Model.js'))
        setup = '''let clock=100;const Date={now:()=>clock*1000};const Model=require(''' + model + ''');
const root={nativeIface:'fixture0',kind:'ethernet',connectionDetails:{},detailsMissing:[],prevIface:'',
 prevRxBytes:0,prevTxBytes:0,prevSampleTime:0,downloadRate:0,uploadRate:0};
Object.defineProperty(root,'info',{get:()=>Object.assign({ssid:''},root.connectionDetails)});
I18n.formatNumber=(v,d)=>d===undefined?String(v):Number(v).toFixed(d);
'''
        self.script('config/shell/preview/NetworkPanelController.qml', ['applyDetails', 'headerDetail'], setup, '''
root.applyDetails({details:{iface:'fixture0',speed:2500,rx_bytes:1000,tx_bytes:500}});
assert.equal(root.headerDetail(),'2.5gbit');assert.equal(root.downloadRate,0);
clock=102;root.applyDetails({details:{iface:'fixture0',rx_bytes:3048,tx_bytes:1524}});
assert.equal(root.downloadRate,1024);assert.equal(root.uploadRate,512);
clock=104;root.applyDetails({details:{iface:'fixture0'}});assert.equal(root.prevSampleTime,0);
clock=106;root.applyDetails({details:{iface:'fixture0',rx_bytes:900000,tx_bytes:900000}});
assert.equal(root.downloadRate,0); // No huge spike after a missing counter sample.
''')

    def test_qr_close_and_generation_guards_drop_late_or_wrong_interface_output(self):
        self.script('config/shell/preview/WifiQrController.qml', ['close', 'applyResult'], '''
const root={opened:true,generation:4,loading:true,iface:'fixture0',ssid:'Fixture',qrSize:0,qrRows:[],
 error:'',pendingShow:false,secured:false,backend:{running:false}};
''', '''const good={ok:true,iface:'fixture0',ssid:'Fixture',size:29,modules:'0'.repeat(29*29)};
root.applyResult(0,JSON.stringify(good),4);assert.equal(root.qrSize,29);
root.close();root.applyResult(0,JSON.stringify(good),4);assert.equal(root.qrSize,0);assert.deepEqual(root.qrRows,[]);
root.opened=true;root.iface='fixture1';root.applyResult(0,JSON.stringify(good),root.generation);
assert.equal(root.qrSize,0);assert.ok(root.error);
root.iface='fixture0';good.modules='1'+'0'.repeat(29*29-1);
root.applyResult(0,JSON.stringify(good),root.generation);assert.equal(root.qrSize,0);''')

    def test_speed_phases_and_close_do_not_publish_stale_results(self):
        self.script('config/shell/preview/NetworkSpeedController.qml', ['close', 'applyResult'], '''
const root={opened:true,generation:2,running:true,phase:'down',pendingRun:false,
 downloadMbps:'',uploadMbps:'',error:'',backend:{running:false}};
''', '''root.applyResult(0,JSON.stringify({ok:true,phase:'down',value:55}),2,'down');
assert.equal(root.phase,'up');assert.equal(root.downloadMbps,'55');assert.equal(root.pendingRun,true);
root.applyResult(0,JSON.stringify({ok:true,phase:'up',value:11}),2,'up');assert.equal(root.running,false);
assert.equal(root.uploadMbps,'11');root.close();
root.applyResult(0,JSON.stringify({ok:true,phase:'down',value:999}),2,'down');assert.equal(root.downloadMbps,'55');''')


if __name__ == '__main__':
    unittest.main()
