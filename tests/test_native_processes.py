"""Synthetic cross-process fixture regressions; never compiles or starts native clients."""
import ast
import contextlib
import io
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import check_native_processes as native


def require(ok,message):
    if not ok:raise AssertionError(message)


class Selector:
    def register(self,*args):pass
    def select(self,*args):return [(None,None)]
    def close(self):pass


class NativeProcessTests(unittest.TestCase):
    def nodes(self,*names,**extra):
        tree=ast.parse(native.DRIVER)
        selected=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names]
        self.assertEqual(len(selected),len(names))
        env={'require':require,'json':json,'time':time,'sender_events':[],
             'selectors':SimpleNamespace(DefaultSelector=Selector,EVENT_READ=1)}
        env.update(extra);exec(compile(ast.Module(body=selected,type_ignores=[]),'synthetic-native-driver','exec'),env)
        return env

    def reader(self,pending=b'',chunks=()):
        source=iter(chunks);read=Mock(side_effect=lambda *args:next(source,b''))
        env=self.nodes('Sender',os=SimpleNamespace(read=read))
        sender=env['Sender'].__new__(env['Sender']);sender.p=SimpleNamespace(stdout=SimpleNamespace(fileno=lambda:77))
        sender.pending=pending;sender.events=[]
        return sender,env,read

    def test_plan_only_never_runs(self):
        with patch.object(native,'run') as run,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(native.main([]),0);run.assert_not_called();self.assertIn('Plan only',out.getvalue())

    def test_explicit_run_requires_private_inputs(self):
        with patch.object(native,'run') as run,contextlib.redirect_stderr(io.StringIO()):
            for args in (['--run'],['--run','--candidate','work/fixture']):
                with self.assertRaises(SystemExit):native.main(args)
            run.assert_not_called()

    def test_exact_dbus_booleans_not_python_literal_guessing(self):
        command=Mock();env=self.nodes('has_owner',command=command)
        for response,expected in (('(true,)',True),('(false,)',False)):
            command.return_value=response;self.assertIs(env['has_owner'](':1.20'),expected)
        self.assertEqual(command.call_args.args[0][-2:],['org.freedesktop.DBus.NameHasOwner',':1.20'])
        for response in ('True','false','(False,)','(true, false)','()'):
            command.return_value=response
            with self.subTest(response=response),self.assertRaises(AssertionError):env['has_owner'](':1.20')

    def test_persistent_reader_returns_own_action_and_retains_other_events(self):
        data=b'{"event":"ignored-action","id":2}\n{"event":"action","id":3,"count":1}\n'
        sender,env,read=self.reader(pending=data)
        self.assertEqual(sender.event('action')['id'],3)
        self.assertEqual(len(sender.events),2);self.assertEqual(sender.events,env['sender_events']);read.assert_not_called()

    def test_reader_handles_partial_owned_pipe_frames(self):
        sender,_,_=self.reader(chunks=[b'{"event":',b'"sent","id":7}\n'])
        self.assertEqual(sender.event('sent')['id'],7)

    def test_reader_closed_pipe_and_failed_sender_refuse(self):
        sender,_,_=self.reader()
        with self.assertRaisesRegex(AssertionError,'closed unexpectedly'):sender.event('ready')
        sender,_,_=self.reader(pending=b'{"event":"failed"}\n')
        with self.assertRaisesRegex(AssertionError,'refused operation'):sender.event('ready')

    def test_reader_bounds_memory_and_event_count(self):
        sender,_,_=self.reader(chunks=[b'x'*8193])
        with self.assertRaisesRegex(AssertionError,'buffer'):sender.event('ready')
        sender,_,_=self.reader(pending=b'{"event":"ignored-close"}\n'*33)
        with self.assertRaisesRegex(AssertionError,'event budget'):sender.event('action')

    def test_reader_malformed_json_refuses(self):
        sender,_,_=self.reader(pending=b'not-json\n')
        with self.assertRaises(ValueError):sender.event('ready')

    def test_only_fixed_sender_verbs_are_written(self):
        env=self.nodes('Sender');sender=env['Sender'].__new__(env['Sender']);stream=io.BytesIO()
        sender.p=SimpleNamespace(stdin=stream)
        for verb in ('notify','replace','status','quit'):sender.send(verb)
        self.assertEqual(stream.getvalue(),b'notify\nreplace\nstatus\nquit\n')
        before=stream.getvalue()
        with self.assertRaises(AssertionError):sender.send('run arbitrary-command')
        self.assertEqual(stream.getvalue(),before)

    def test_service_and_application_are_separate_native_roots(self):
        self.assertIn('Notifications.Service {',native.SERVICE);self.assertNotIn('FloatingWindow {',native.SERVICE)
        self.assertIn('FloatingWindow {',native.APPLICATION);self.assertNotIn('Notifications.Service',native.APPLICATION)
        self.assertIn('nativeApplicationFixture',native.APPLICATION)
        for text in (native.SERVICE,native.APPLICATION):
            for forbidden in ('keyboardPressed(','pointerEntered(','NotificationServer {','PanelWindow {'):
                self.assertNotIn(forbidden,text)

    def test_native_driver_uses_real_process_ids_sender_and_input(self):
        compile(native.DRIVER,'private-cross-process','exec')
        for required in ("'--pid',str(shell.pid)","'--pid',str(application.pid)",'GetConnectionUnixProcessID',
                         'persistent sender Notify','sender.event(\'action\')','second.event(\'ignored-action\')',
                         'cross-process key handoff without refocus','children_reaped','/usr/bin/c++','/usr/lib/qt6/libexec/moc'):
            self.assertIn(required,native.DRIVER)
        self.assertEqual(native.native_input.BOOTSTRAP,native.native_input.notifications.DRIVER.split(native.native_input.BOOTSTRAP_MARKER)[0])
        self.assertNotIn('servicedir',native.ownership.BUS)

    def test_cpp_fixture_is_private_fixed_and_persistent(self):
        source=(ROOT/'tests/fixtures/notification_sender.cpp').read_text()
        for text in ('QSocketNotifier','ActionInvoked','NotificationClosed','message.service() != owner',
                     'id != notice || notice == 0','identifier != "default"','unix:path=/home/probe/runtime/private-bus',
                     'QDBus::Block, 2000','pending.size() > 256','QTimer::singleShot(30000'):
            self.assertIn(text,source)
        for text in ('systemBus(', 'execDetached', 'QProcess','xdg-open'):
            self.assertNotIn(text,source)

    def test_actual_notification_closure_is_still_sealed(self):
        files,_=native.preview.verified_sources(ROOT)
        for name,data in native.notification_frontend.sources(ROOT).items():self.assertEqual(files[name],data,name)
        self.assertIn(b'Variants {',files['Notifications/Service.qml'])
        self.assertIn(b'Quickshell.Hyprland',files['Notifications/Service.qml'])


if __name__=='__main__':unittest.main()
