"""Private native input fixture guards and in-memory wire tests; no real input/socket."""
import contextlib
import io
import os
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import native_pointer_fixture as pointer
import check_native_input as native


class WireSocket:
    def __init__(self,protocol=True,error=False):
        self.pending=b'';self.sent=[];self.closed=False;self.protocol=protocol;self.error=error

    def settimeout(self,value):self.timeout=value
    def connect(self,value):self.path=value
    def close(self):self.closed=True

    def sendall(self,data):
        self.sent.append(data);target,header=struct.unpack('=II',data[:8]);opcode=header&65535
        if target==1 and opcode==1 and self.protocol:
            payload=pointer.words(9)+pointer.string('zwlr_virtual_pointer_manager_v1')+pointer.words(2)
            self.pending+=pointer.packet(2,0,payload)
        if target==1 and opcode==0:
            callback,=struct.unpack('=I',data[8:])
            self.pending+=pointer.packet(1,0,pointer.words(0,0,0)) if self.error else pointer.packet(callback,0,pointer.words(1))

    def recv(self,size):
        data=self.pending[:size];self.pending=self.pending[size:];return data


class NativeInputTests(unittest.TestCase):
    def client(self,wire=None):
        wire=wire or WireSocket()
        with patch.dict(os.environ,{'XDG_RUNTIME_DIR':'/home/probe/runtime','WAYLAND_DISPLAY':'wayland-0','PRIVATE_OUTPUT_COUNT':'1'},clear=True),patch.object(Path,'is_socket',return_value=True),patch.object(Path,'is_symlink',return_value=False),patch.object(pointer.socket,'socket',return_value=wire):
            client=pointer.Pointer()
        self.addCleanup(client.close)
        return client,wire

    def test_plan_only_never_executes(self):
        with patch.object(native,'run') as run,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(native.main([]),0);run.assert_not_called();self.assertIn('Plan only',out.getvalue())

    def test_explicit_run_requires_private_inputs(self):
        with patch.object(native,'run') as run,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):native.main(['--run'])
            run.assert_not_called()

    def test_host_environment_refuses_before_socket_creation(self):
        for env in ({},{'XDG_RUNTIME_DIR':'/run/user/1000','WAYLAND_DISPLAY':'wayland-0','PRIVATE_OUTPUT_COUNT':'1'},
                    {'XDG_RUNTIME_DIR':'/home/probe/runtime','WAYLAND_DISPLAY':'../host','PRIVATE_OUTPUT_COUNT':'1'},
                    {'XDG_RUNTIME_DIR':'/home/probe/runtime','WAYLAND_DISPLAY':'wayland-0','PRIVATE_OUTPUT_COUNT':'2'}):
            with self.subTest(env=env),patch.dict(os.environ,env,clear=True),patch.object(pointer.socket,'socket') as socket:
                with self.assertRaises(ValueError):pointer.Pointer()
                socket.assert_not_called()

    def test_symlink_or_missing_private_socket_refuses(self):
        with patch.dict(os.environ,{'XDG_RUNTIME_DIR':'/home/probe/runtime','WAYLAND_DISPLAY':'wayland-0','PRIVATE_OUTPUT_COUNT':'1'},clear=True),patch.object(pointer.socket,'socket') as socket:
            for is_socket,is_link in ((False,False),(True,True)):
                with patch.object(Path,'is_socket',return_value=is_socket),patch.object(Path,'is_symlink',return_value=is_link):
                    with self.assertRaises(ValueError):pointer.Pointer()
            socket.assert_not_called()

    def test_registry_binding_and_new_ids_are_contiguous(self):
        client,wire=self.client()
        self.assertEqual(wire.path,'/home/probe/runtime/wayland-0');self.assertEqual(wire.timeout,2)
        self.assertEqual(struct.unpack('=I',wire.sent[0][8:]),(2,))
        self.assertEqual(struct.unpack('=I',wire.sent[1][8:]),(3,))
        self.assertEqual(struct.unpack('=I',wire.sent[2][-4:]),(4,))
        self.assertEqual(struct.unpack('=II',wire.sent[3][8:]),(0,5))
        self.assertEqual(client.pointer,5)

    def test_missing_protocol_or_server_error_closes_owned_socket(self):
        for wire in (WireSocket(protocol=False),WireSocket(error=True)):
            with self.subTest(protocol=wire.protocol,error=wire.error),self.assertRaises(ValueError):self.client(wire)
            self.assertTrue(wire.closed)

    def test_move_frames_and_button_requests_use_persistent_socket(self):
        client,wire=self.client();before=len(wire.sent)
        with patch.object(pointer.time,'sleep'):client.move(900,60);client.click(273)
        requests=[(struct.unpack('=II',data[:8])[0],struct.unpack('=II',data[:8])[1]&65535,data[8:]) for data in wire.sent[before:]]
        self.assertEqual(requests[0][0:2],(client.pointer,1))
        self.assertEqual(struct.unpack('=IIIII',requests[0][2])[1:],(900,60,1280,720))
        buttons=[struct.unpack('=III',payload)[1:] for target,opcode,payload in requests if target==client.pointer and opcode==2]
        self.assertEqual(buttons,[(273,1),(273,0)])
        self.assertEqual(sum(target==client.pointer and opcode==4 for target,opcode,_ in requests),3)
        self.assertFalse(wire.closed)

    def test_bad_coordinates_and_buttons_send_nothing(self):
        client,wire=self.client();before=len(wire.sent)
        for args in ((-1,0),(1280,0),(0,720),(1.0,2),(True,2),(1,2,2560,720),(1,2,1280.0,720)):
            with self.subTest(args=args),self.assertRaises(ValueError):client.move(*args)
        for button in (0,274,272.0,True):
            with self.assertRaises(ValueError):client.click(button)
        self.assertEqual(len(wire.sent),before)

    def test_destroy_and_close_are_idempotent(self):
        client,wire=self.client();client.close();before=len(wire.sent);client.close()
        self.assertTrue(wire.closed);self.assertEqual(len(wire.sent),before)
        self.assertTrue(any(struct.unpack('=II',data[:8])==(5,(8<<16)|8) for data in wire.sent))

    def test_invalid_packet_bounds_refuse(self):
        for target,opcode,payload in ((0,0,b''),(1,65536,b''),(1,0,b'x'),(1,0,b'x'*65528)):
            with self.subTest(target=target,opcode=opcode),self.assertRaises(ValueError):pointer.packet(target,opcode,payload)

    def test_bad_event_and_closed_stream_refuse(self):
        client,wire=self.client();wire.pending=pointer.words(2,(7<<16))
        with self.assertRaisesRegex(ValueError,'Invalid private Wayland event'):client.sync()
        wire.pending=b''
        with self.assertRaisesRegex(ValueError,'connection closed'):client.exact(8)

    def test_id_budget_is_bounded(self):
        client,wire=self.client();client.next_id=1000
        with self.assertRaisesRegex(ValueError,'budget'):client.new_id()
        client.next_id=10

    def test_native_fixture_counts_real_events_without_replacing_service(self):
        compile(native.DRIVER,'private-native-input','exec')
        self.assertIn('Notifications.Service {',native.QML)
        self.assertIn('FloatingWindow {',native.QML)
        self.assertIn('onClicked:bg.clicks++',native.QML)
        self.assertIn('Qt.Key_A)bg.aKeys++',native.QML)
        for absent in ('PanelWindow {','keyboardPressed(','pointerEntered(','NotificationServer {'):
            self.assertNotIn(absent,native.QML)
        for required in ('Pointer()','pointer.click(273)',"pointer.click()",'time.sleep(5.3)',
                         'original lifetime resumes','ActionInvoked','without refocus','children_reaped'):
            self.assertIn(required,native.DRIVER)
        self.assertNotIn('servicedir',native.ownership.BUS)

    def test_native_bootstrap_is_exact_and_dependency_remains_explicit(self):
        self.assertEqual(native.BOOTSTRAP,native.notifications.DRIVER.split(native.BOOTSTRAP_MARKER)[0])
        self.assertIn('bootstrap_checker_sha256',Path(native.__file__).read_text())


if __name__=='__main__':unittest.main()
