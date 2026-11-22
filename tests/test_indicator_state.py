"""Private synthetic transactions; no host bus, socket or native state actions."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import indicator_state as state
from indicator_native import NativeError, action_key

SCOPE = 'a' * 24


class FakeNative:
    def __init__(self):
        self.states = {'dnd': {'active': False, 'proof': {'owner': ':1.2', 'pid': 3}},
                       'nightlight': {'active': True, 'proof': {'kelvin': 6000, 'gamma': 95, 'owner': 4}}}
        self.writes = []
        self.failure = False
        self.unavailable = set()

    def read(self, kind):
        if kind in self.unavailable:
            raise NativeError('unavailable')
        return copy.deepcopy(self.states[kind])

    def set(self, kind, desired, before):
        self.writes.append((kind, desired))
        self.states[kind]['active'] = desired
        if self.failure:
            raise NativeError('unknown-reply')
        return self.read(kind)


class IndicatorStateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(temporary.cleanup)
        # The repository itself is group-writable. Model private ancestry for
        # this contained fixture only; never chmod the repo or weaken Store.
        original_stat = Path.stat
        ancestors = {ROOT, *ROOT.parents}
        def fixture_stat(path, *args, **kwargs):
            value = original_stat(path, *args, **kwargs)
            if path in ancestors:
                fields = list(value)
                fields[0] &= ~0o022
                return os.stat_result(fields)
            return value
        ancestry = patch.object(Path, 'stat', fixture_stat)
        ancestry.start()
        self.addCleanup(ancestry.stop)
        self.directory = Path(temporary.name) / 'private'
        self.store = state.Store(self.directory)
        self.native = FakeNative()

    def key(self, kind='dnd'):
        return action_key(SCOPE, kind, self.native.read(kind))

    def test_inspect_is_readonly_and_absence_is_unknown_not_inactive(self):
        self.native.unavailable.add('nightlight')
        result = state.inspect(self.native, self.store, SCOPE)
        self.assertFalse(self.directory.exists())
        self.assertEqual(result['states']['nightlight'], {'known': False, 'reason': 'unavailable'})
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['states']['dnd'], {'known': True, 'active': False, 'key': self.key()})
        self.assertFalse(result['blocked'])
        self.assertEqual(self.native.writes, [])

    def test_before_is_durable_before_one_setter_and_receipt_is_private(self):
        original_set = self.native.set
        def setter(kind, desired, before):
            records = self.store.records()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['status'], 'prepared')
            self.assertEqual(records[0]['before'], before)
            return original_set(kind, desired, before)
        self.native.set = setter
        result = state.change(self.native, self.store, SCOPE, 'dnd', self.key(), True)
        self.assertEqual(result['status'], 'confirmed')
        self.assertEqual(self.native.writes, [('dnd', True)])
        record = self.store.records()[0]
        self.assertFalse(record['before']['active'])
        self.assertTrue(record['after']['active'])
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.directory / '00000001.json').stat().st_mode & 0o777, 0o600)

    def test_explicit_return_to_previous_boolean_uses_receipt_after_key_and_refuses_drift(self):
        first = state.change(self.native, self.store, SCOPE, 'dnd', self.key(), True)
        record = self.store.records()[0]
        self.assertEqual(record['after_key'], self.key())
        restored = state.change(self.native, self.store, record['scope'], record['kind'], record['after_key'], record['before']['active'])
        self.assertEqual(restored['status'], 'confirmed')
        self.assertEqual(self.native.writes, [('dnd', True), ('dnd', False)])
        self.native.states['dnd']['proof']['owner'] = ':1.99'
        with self.assertRaises(NativeError):
            state.change(self.native, self.store, record['scope'], record['kind'], record['after_key'], record['before']['active'])
        self.assertEqual(len(self.native.writes), 2)
        self.assertEqual(first['receipt'], '00000001')

    def test_stale_state_owner_kind_or_scope_never_issues_write(self):
        key = self.key()
        for kind, scope in [('nightlight', SCOPE), ('dnd', 'b' * 24)]:
            with self.assertRaises(NativeError):
                state.change(self.native, self.store, scope, kind, key, True)
        self.native.states['dnd']['proof']['owner'] = ':1.9'
        with self.assertRaises(NativeError):
            state.change(self.native, self.store, SCOPE, 'dnd', key, True)
        self.assertEqual(self.native.writes, [])
        self.assertEqual(self.store.records(), [])

    def test_uncertain_write_is_never_replayed_compensated_or_auto_cleared(self):
        self.native.failure = True
        result = state.change(self.native, self.store, SCOPE, 'dnd', self.key(), True)
        self.assertEqual(result['status'], 'uncertain')
        self.assertEqual(self.native.writes, [('dnd', True)])
        self.assertTrue(state.inspect(self.native, self.store, SCOPE)['blocked'])
        with self.assertRaises(NativeError):
            state.change(self.native, self.store, SCOPE, 'nightlight', self.key('nightlight'), False)
        self.assertEqual(self.native.writes, [('dnd', True)])
        ack = self.store.acknowledge(result['receipt'])
        self.assertFalse(ack['restored'])
        self.assertEqual(self.native.writes, [('dnd', True)])
        self.assertFalse(self.store.blocked())

    def test_interrupted_prepared_receipt_blocks_new_actions(self):
        self.native.set = lambda *args: (_ for _ in ()).throw(KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            state.change(self.native, self.store, SCOPE, 'dnd', self.key(), True)
        self.assertEqual(self.store.records()[0]['status'], 'prepared')
        self.assertTrue(self.store.blocked())
        with self.assertRaises(NativeError):
            state.change(FakeNative(), self.store, SCOPE, 'dnd', self.key(), True)

    def test_noop_does_not_allocate_receipt_or_issue_setter(self):
        result = state.change(self.native, self.store, SCOPE, 'dnd', self.key(), False)
        self.assertEqual(result, {'status': 'unchanged'})
        self.assertEqual(self.store.records(), [])
        self.assertEqual(self.native.writes, [])

    def test_corrupt_links_modes_and_unexpected_files_block_actions(self):
        with self.store.lock():
            pass
        link = self.directory / '00000001.json'
        link.symlink_to(self.directory / 'missing')
        self.assertTrue(state.inspect(self.native, self.store, SCOPE)['blocked'])
        with self.assertRaises(NativeError):
            state.change(self.native, self.store, SCOPE, 'dnd', self.key(), True)
        link.unlink()
        link.write_text('{}')
        link.chmod(0o600)
        with self.assertRaises(NativeError):
            self.store.records()
        link.unlink()
        self.directory.chmod(0o755)
        with self.assertRaises(NativeError):
            self.store.records()
        self.assertEqual(self.native.writes, [])

    def test_missing_explicit_cli_grants_never_construct_native_client(self):
        for args in (['inspect'], ['set', '--allow-existing-owner-queries'], ['acknowledge', '--receipt', '00000001']):
            with patch.object(state, 'Native') as native, contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(state.main(args), 1)
            native.assert_not_called()
            self.assertFalse(json.loads(output.getvalue())['ok'])

    def test_invalid_request_shapes_and_nonboolean_state_are_rejected(self):
        for scope, kind, key, desired in [('bad', 'dnd', self.key(), True), (SCOPE, 'sudo', self.key(), True), (SCOPE, 'dnd', 'bad', True), (SCOPE, 'dnd', self.key(), 1)]:
            with self.assertRaises(NativeError):
                state.change(self.native, self.store, scope, kind, key, desired)
        self.assertFalse(self.directory.exists())
        self.assertEqual(self.native.writes, [])

    def test_private_lock_refuses_concurrent_action_without_queue(self):
        with self.store.lock():
            with self.assertRaises(NativeError):
                state.change(self.native, state.Store(self.directory), SCOPE, 'dnd', self.key(), True)
        self.assertEqual(self.native.writes, [])


if __name__ == '__main__':
    unittest.main()
