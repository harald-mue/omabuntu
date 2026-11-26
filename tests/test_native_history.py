"""Synthetic state/diagnostic checks; never starts native notification processes."""
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import check_native_history as native
import notification_state as state


def require(ok,message):
    if not ok:raise AssertionError(message)


class NativeHistoryTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(dir=ROOT/'work');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.directory=state.prepare(self.base/'state')

    def nodes(self,*names,**extra):
        tree=ast.parse(native.DRIVER)
        nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
        self.assertEqual(len(nodes),len(names))
        env={'STATE':self.directory,'state':state,'require':require,'json':json,'re':re,'Path':Path,
             'CANARY':'73182649','MARKER':'FixtureSecretSentinel'}
        env.update(extra);exec(compile(ast.Module(body=nodes,type_ignores=[]),'synthetic-history-functions','exec'),env)
        return env

    def row(self,history=False,redacted=False):
        row={k:'' for k in state.STRING_FIELDS};row.update({k:0 for k in state.NUMBER_FIELDS})
        row.update(key='fixture',app='Fixture',summary='Ordinary fixture',body='Synthetic body')
        if history:row.update(closed_ts=1,closed_reason='dismissed')
        if redacted:
            for key in state.STRING_FIELDS:row[key]=''
            row.update(key='fixture',summary='Verification notification',body='[redacted]')
        return row

    def test_default_is_plan_only(self):
        with patch.object(native,'run') as run,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(native.main([]),0);run.assert_not_called();self.assertIn('Plan only',out.getvalue())

    def test_explicit_run_requires_private_inputs(self):
        with patch.object(native,'run') as run,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):native.main(['--run'])
            run.assert_not_called()

    def test_read_store_validates_without_writing(self):
        (self.directory/'history.json').write_text(json.dumps([self.row(True)]))
        before={p.name:p.read_bytes() for p in self.directory.iterdir()}
        result=self.nodes('read_store')['read_store']()
        self.assertEqual(result['history.json'][0]['key'],'fixture')
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.directory.iterdir()})

    def test_missing_state_is_not_recreated(self):
        path=self.directory/'live.json';path.unlink()
        with self.assertRaises(OSError):self.nodes('read_store')['read_store']()
        self.assertFalse(path.exists())

    def test_public_symlinked_or_hardlinked_files_refuse(self):
        path=self.directory/'quiet.json';path.chmod(0o644)
        with self.assertRaises(ValueError):self.nodes('read_store')['read_store']()
        path.chmod(0o600);other=self.base/'quiet-copy';other.hardlink_to(path)
        with self.assertRaises(ValueError):self.nodes('read_store')['read_store']()
        other.unlink();path.rename(other);path.symlink_to(other)
        with self.assertRaises(ValueError):self.nodes('read_store')['read_store']()

    def test_extra_capability_fields_and_overlong_history_refuse(self):
        path=self.directory/'history.json';row=self.row(True);row['image']='synthetic'
        path.write_text(json.dumps([row]))
        with self.assertRaises(AssertionError):self.nodes('read_store')['read_store']()
        path.write_text(json.dumps([self.row(True)]*101))
        with self.assertRaises(AssertionError):self.nodes('read_store')['read_store']()

    def test_quiet_schema_is_exact(self):
        for value in ({'dnd':0},{'dnd':False,'extra':True},[],None):
            (self.directory/'quiet.json').write_text(json.dumps(value))
            with self.subTest(value=value),self.assertRaises(AssertionError):self.nodes('read_store')['read_store']()

    def test_redaction_requires_placeholder_and_cleared_metadata(self):
        check=self.nodes('redacted')['redacted'];row=self.row(redacted=True);self.assertTrue(check(row))
        for field in ('app','appIcon','source','groupKey','glyph','execArgv','execActions','rawBody'):
            bad=dict(row);bad[field]='synthetic-canary'
            with self.subTest(field=field):self.assertFalse(check(bad))
        self.assertFalse(check(self.row()))

    def test_canary_scan_refuses_active_bytes_without_echoing_contents(self):
        check=self.nodes('no_canary')['no_canary'];check()
        for token in ('73182649','FixtureSecretSentinel'):
            (self.directory/'live.json').write_text(json.dumps([{'body':token}]))
            with self.assertRaises(AssertionError) as error:check()
            self.assertNotIn(token,str(error.exception))

    def test_binding_loop_is_a_hidden_failure_not_an_allowed_warning(self):
        log='  WARN: $HYPRLAND_INSTANCE_SIGNATURE is unset. Cannot connect to hyprland.\nDEBUG: llvmpipe\n'
        path=Mock();path.read_text.return_value=log
        function=self.nodes('diagnostic_records',Path=Mock(return_value=path),generation=1)['diagnostic_records']
        record=function()[0];self.assertEqual(len(record['warnings']),1);self.assertFalse(record['hidden_failure'])
        path.read_text.return_value=log+'  WARN scene: Binding loop detected for property "layout":\n'
        record=function()[0];self.assertTrue(record['hidden_failure']);self.assertEqual(len(record['warnings']),2)
        self.assertIn("require(all(len(r['warnings'])==1",native.DRIVER)
        self.assertIn("report['status']='failed'",Path(native.__file__).read_text())

    def test_phase_counters_do_not_convert_warnings_into_pass(self):
        records=Mock(return_value=[{'warnings':['expected','Binding loop']}])
        env=self.nodes('PhaseChecks',diagnostic_records=records)
        checks=env['PhaseChecks']();checks.append({'name':'functional-case','passed':True})
        self.assertEqual(checks[0]['diagnostic_counts'],[2])

    def test_private_seeding_refuses_while_service_is_running(self):
        env=self.nodes('write_seed',shell=Mock(poll=Mock(return_value=None)))
        before=(self.directory/'live.json').read_bytes()
        with self.assertRaises(AssertionError):env['write_seed']({'live.json':[]})
        self.assertEqual((self.directory/'live.json').read_bytes(),before)

    def test_fixture_retains_real_service_and_native_gates(self):
        compile(native.DRIVER,'native-history-driver','exec')
        self.assertIn('Notifications.Service {',native.QML)
        for forbidden in ('NotificationServer {','PanelWindow {','pointerEntered(','keyboardPressed('):self.assertNotIn(forbidden,native.QML)
        for required in ("'transient': <true>","ipc('showHistory')",'86401',"len(s['history.json'])==100",'no_canary()',
                         'checkpoints','children_reaped','GetConnectionUnixProcessID'):
            self.assertIn(required,native.DRIVER)
        for forbidden in ('wl-copy','wl-paste','setDnd','timedatectl','/usr/bin/c++'):self.assertNotIn(forbidden,native.DRIVER)
        self.assertNotIn('servicedir',native.ownership.BUS)

    def test_notification_closure_remains_exact(self):
        files,_=native.preview.verified_sources(ROOT)
        for name,data in native.notification_frontend.sources(ROOT).items():self.assertEqual(files[name],data,name)
        self.assertIn(b'Variants {',files['Notifications/Service.qml'])
        self.assertIn(b'MultiEffect',files['Notifications/Toast.qml'])


if __name__=='__main__':unittest.main()
