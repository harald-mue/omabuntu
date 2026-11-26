"""Synthetic grant and transaction tests; never use host sessions or providers."""
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import notification_session as session
import notification_deployment as deploy


class GrantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.bundle = self.root / 'bundle'; self.bundle.mkdir()
        (self.bundle / 'native').mkdir(); (self.bundle / 'release.json').write_text('{}')
        (self.bundle / 'native/notification-runtime.json').write_text('{}')
        self.socket = socket.socket(socket.AF_UNIX); self.addCleanup(self.socket.close)
        self.socket.bind(str(self.root / 'wayland-0'))
        self.env = {'WAYLAND_DISPLAY': 'wayland-0', 'XDG_RUNTIME_DIR': str(self.root),
                    'DBUS_SESSION_BUS_ADDRESS': 'unix:path=private-fixture', 'HYPRLAND_INSTANCE_SIGNATURE': 'synthetic'}
        self.identity = {'argv': session.argv(self.bundle), 'start_ticks': '123'}
        self.verify = patch.object(session, 'verify_artifact'); self.verify.start(); self.addCleanup(self.verify.stop)
        self.manager = patch.object(session, 'manager', return_value=SimpleNamespace(identity=lambda pid: self.identity))
        self.manager.start(); self.addCleanup(self.manager.stop)
        self.grant = session.issue(self.bundle, self.root / 'grant', self.env)

    def rewrite(self, change):
        value = json.loads(self.grant.read_text()); change(value)
        self.grant.write_text(json.dumps(value))

    def test_bound_parent_can_claim_exactly_once(self):
        claim = session.admit(self.grant, self.bundle, self.env, 7)
        self.assertEqual(claim['pid'], 7); self.assertEqual(claim['identity'], self.identity)
        with self.assertRaises(FileExistsError): session.admit(self.grant, self.bundle, self.env, 7)

    def test_no_timer_or_autostart_permission(self):
        grant = json.loads(self.grant.read_text())
        self.assertEqual(grant['lifetime'], 'session')
        self.assertNotIn('expires', grant); self.assertNotIn('autostart', grant)

    def test_changed_session_refuses_without_claim(self):
        with self.assertRaises(ValueError): session.admit(self.grant, self.bundle, {**self.env, 'HYPRLAND_INSTANCE_SIGNATURE': 'different'}, 7)
        self.assertFalse((self.grant.parent / 'claim.json').exists())

    def test_missing_socket_refuses(self):
        (self.root / 'wayland-0').unlink()
        with self.assertRaises(ValueError): session.admit(self.grant, self.bundle, self.env, 7)

    def test_wrong_parent_refuses(self):
        self.identity['argv'] = ['/usr/bin/python3', 'not-a-shell']
        with self.assertRaises(ValueError): session.admit(self.grant, self.bundle, self.env, 7)

    def test_artifact_and_proof_changes_refuse(self):
        for name in ('release.json', 'native/notification-runtime.json'):
            p = self.bundle / name; original = p.read_bytes(); p.write_bytes(original + b' ')
            with self.assertRaises(ValueError): session.admit(self.grant, self.bundle, self.env, 7)
            p.write_bytes(original)

    def test_schema_identity_lifetime_and_revocation_refuse(self):
        original = self.grant.read_bytes()
        for key, value in [('schema_version', True), ('scope', 'wrong'), ('lifetime', 'autostart'), ('bundle', '/wrong'), ('argv', []), ('nonce', 'x'), ('revoked', True)]:
            self.grant.write_bytes(original); self.rewrite(lambda row: row.update({key: value}))
            with self.assertRaises(ValueError): session.admit(self.grant, self.bundle, self.env, 7)

    def test_permissions_links_and_bounds_refuse(self):
        self.grant.chmod(0o644)
        with self.assertRaises(ValueError): session.private_json(self.grant)
        self.grant.chmod(0o600); link = self.root / 'link'; link.symlink_to(self.grant)
        with self.assertRaises(ValueError): session.private_json(link)
        os.link(self.grant, self.root / 'hardlink')
        with self.assertRaises(ValueError): session.private_json(self.grant)
        (self.root / 'hardlink').unlink(); self.grant.write_bytes(b' ' * 32769)
        with self.assertRaises(ValueError): session.private_json(self.grant)

    def test_grant_directory_is_fresh_not_overwritten(self):
        old = self.grant.read_bytes()
        with self.assertRaises(FileExistsError): session.issue(self.bundle, self.grant.parent, self.env)
        self.assertEqual(self.grant.read_bytes(), old)


STEPS = ['preflight', 'snapshot', 'stop_owned_shell', 'fence_provider', 'stop_provider', 'install', 'grant', 'start_captured', 'verify_ready', 'complete']


class Fake:
    def __init__(self, fail=None): self.events = []; self.fail = fail
    def __getattr__(self, name):
        def call(*args):
            self.events.append(name)
            if name == self.fail: raise ValueError(name)
            return {'ready': True}
        return call


class OrderingTests(unittest.TestCase):
    def test_single_owner_order_and_success(self):
        ops = Fake(); self.assertEqual(deploy.switch(ops), {'ready': True}); self.assertEqual(ops.events, STEPS)

    def test_preflight_and_backup_failure_never_mutate_live_state(self):
        for step in STEPS[:2]:
            ops = Fake(step)
            with self.assertRaises(ValueError): deploy.switch(ops)
            self.assertEqual(ops.events, STEPS[:STEPS.index(step) + 1])

    def test_each_mutation_failure_recovers_before_error_returns(self):
        for step in STEPS[2:]:
            ops = Fake(step)
            with self.assertRaises(ValueError): deploy.switch(ops)
            self.assertEqual(ops.events, STEPS[:STEPS.index(step) + 1] + ['record_failure', 'recover'])

    def test_recovery_failure_is_not_hidden_or_retried(self):
        ops = Fake('install')
        def recover(): ops.events.append('recover'); raise RuntimeError('recovery')
        ops.recover = recover
        with self.assertRaisesRegex(RuntimeError, 'recovery'): deploy.switch(ops)
        self.assertEqual(ops.events.count('recover'), 1)


if __name__ == '__main__': unittest.main()
