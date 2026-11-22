"""Two-channel master action contracts; never connect to native PipeWire."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import audio_port_fixtures as fixtures


class AudioMasterTests(unittest.TestCase):
    def source(self, name):
        return (ROOT / 'config/shell/preview' / name).read_text()

    def test_provider_checks_both_defaults_before_any_action(self):
        text = self.source('AudioOutputProvider.qml')
        body = text.split('function toggleAllMuted(', 1)[1].split('\n  }', 1)[0]
        for guard in ('!Pipewire.ready', 'masterDefaultMatches(outputKey, Pipewire.defaultAudioSink)',
                      'masterDefaultMatches(inputKey, Pipewire.defaultAudioSource)'):
            self.assertLess(body.index(guard), body.index('Actions.toggleAllMuted'))
        self.assertNotIn('Component.onCompleted', text)

    def test_hero_is_two_channel_but_section_controls_are_local(self):
        text = self.source('AudioPanelController.qml')
        self.assertIn('|| (hasInput && !inputMuted)', text)
        self.assertIn('backend.toggleAllMuted(current, source)', text)
        self.assertIn('Mute output and microphone', text)
        self.assertIn('Unmute output and microphone', text)
        self.assertIn('backend.toggleSourceMute(source)', text)
        self.assertIn('backend.toggleMute(current)', text)

    def test_both_device_projections_include_serial(self):
        text = self.source('AudioPresentation.js')
        self.assertEqual(text.count('serial:Actions.streamSerial(node)'), 3)

    def test_isolated_cases_have_honest_failure_classification(self):
        for case in ('master-mixed', 'master-single', 'master-guards', 'master-partial'):
            text = fixtures.fixture(case)
            self.assertNotIn('Quickshell.Services.Pipewire', text)
            self.assertIn('master construction reads only', text)
            good = 'Configuration Loaded\n' + fixtures.MARKER + '::' + case + '\n'
            self.assertTrue(fixtures.classify(case, 0, good))
            self.assertFalse(fixtures.classify(case, 0, good + 'WARN unexpected\n'))

    @unittest.skipUnless(shutil.which('node'), 'Node required for pure-JS negative controls')
    def test_actual_actions_with_serial_reuse_and_missing_channel(self):
        source = self.source('AudioActions.js').replace('.pragma library\n', '')
        program = source + '''
const assert = require('assert');
const out = {id:1,name:'speaker',ready:true,isSink:true,isStream:false,
  properties:{'object.serial':'11'},audio:{volume:.4,muted:false}};
const mic = {id:2,name:'mic',ready:true,isSink:false,isStream:false,
  properties:{'object.serial':'12'},audio:{volume:.2,muted:true}};
const a = {id:1,name:'speaker',serial:'11'}, b = {id:2,name:'mic',serial:'12'};
assert.strictEqual(toggleAllMuted([out],[mic],a,b),true);
assert(out.audio.muted && mic.audio.muted);
assert.strictEqual(toggleAllMuted([out],[mic],a,b),true);
assert(!out.audio.muted && !mic.audio.muted);
assert.strictEqual(out.audio.volume,.4);assert.strictEqual(mic.audio.volume,.2);
mic.properties['object.serial']='13';
assert.strictEqual(toggleAllMuted([out],[mic],a,b),false);
assert(!out.audio.muted && !mic.audio.muted);
for (const key of [undefined, false, 0, '', {}, {...b,serial:''}]) {
  assert.strictEqual(toggleAllMuted([out],[mic],a,key),false);
  assert(!out.audio.muted);
}
assert.strictEqual(toggleAllMuted([out],[],a,b),false);
assert.strictEqual(masterDefaultMatches(a,{...out,properties:{'object.serial':'99'}}),false);
assert.strictEqual(masterDefaultMatches(null,mic),false);
assert.strictEqual(masterDefaultMatches(null,null),true);
console.log(JSON.stringify({passed:true}));
'''
        result = subprocess.run(['node', '-e', program], text=True, capture_output=True,
                                timeout=10, check=True)
        self.assertEqual(json.loads(result.stdout), {'passed': True})


if __name__ == '__main__':
    unittest.main()
