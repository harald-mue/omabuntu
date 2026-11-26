"""Synthetic-only native notification harness regressions; never starts a compositor/bus."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import check_native_notifications as native
import notification_state as state


class NativeNotificationTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(dir=ROOT/'work');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);(self.base/'home').mkdir(mode=0o700)

    def frames(self,output='HEADLESS-1',active=True,square=False,tinted=True,raw=True,outside=False):
        width,height=800,400;empty=bytes(width*height*3)
        for name in ('empty','photo','grouped','symbolic','raw-icon'):
            data=bytearray(empty)
            if active and name!='empty':
                color=(255,0,255) if name in ('photo','grouped') else ((0,220,0) if name=='symbolic' and tinted else (255,0,0))
                if name=='raw-icon' and not raw:color=(0,220,0)
                for y in range(60,100):
                    for x in range(600,640):
                        if name=='photo' and not square and (x,y) in ((600,60),(639,60),(600,99),(639,99)):continue
                        data[(y*width+x)*3:(y*width+x)*3+3]=bytes(color)
                if outside:data[(10*width+10)*3:(10*width+10)*3+3]=b'\xff\xff\xff'
            (self.base/'home'/(name+'-'+output+'.ppm')).write_bytes(b'P6\n800 400\n255\n'+data)

    def private_state(self):
        home=self.base/'home/.local/state/omabuntu';directory=state.prepare(home)
        rows=[]
        for i in range(4):
            row={k:'' for k in (*state.STRING_FIELDS,'closed_reason')}
            row.update({k:0 for k in (*state.NUMBER_FIELDS,'closed_ts')})
            row.update(key='fixture'+str(i),app='Fixture',closed_reason=('silenced' if i==0 else 'expired'))
            rows.append(row)
        (directory/'history.json').write_text(json.dumps(rows))
        return directory

    def test_default_is_plan_only(self):
        with patch.object(native,'run') as run,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(native.main([]),0);run.assert_not_called()
            self.assertIn('Plan only',out.getvalue())

    def test_explicit_run_requires_both_private_inputs(self):
        with patch.object(native,'run') as run,contextlib.redirect_stderr(io.StringIO()):
            for args in (['--run'],['--run','--lab-dir','work/fixture']):
                with self.assertRaises(SystemExit):native.main(args)
            run.assert_not_called()

    def test_driver_retains_real_service_bus_and_input_boundaries(self):
        compile(native.DRIVER,'private-native-notifications','exec')
        self.assertIn('Notifications.Service {',native.QML)
        for text in ('PanelWindow {','NotificationServer {','keyboardPressed(','onNotification('):
            self.assertNotIn(text,native.QML)
        for text in ('org.freedesktop.Notifications.Notify',"LAB+'wtype','-s','500','-k','Escape'",
                     "LAB+'wtype','-s','500','-k','Return'",'GetConnectionUnixProcessID','ActionInvoked','children_reaped'):
            self.assertIn(text,native.DRIVER)
        self.assertNotIn('servicedir',native.BUS);self.assertNotIn('standard_session_servicedirs',native.BUS)
        self.assertIn('PRIVATE_NATIVE_NOTIFICATIONS_WATCHDOG',native.QML)

    def test_staged_closure_is_the_verified_actual_service_not_surface_stripped(self):
        files,_=native.preview.verified_sources(ROOT)
        for name,data in native.notification_frontend.sources(ROOT).items():self.assertEqual(files[name],data,name)
        service=files['Notifications/Service.qml'].decode()
        for text in ('PanelWindow {','Variants {','Quickshell.Hyprland','Quickshell.Services.Notifications'):
            self.assertIn(text,service)

    def test_fixed_photo_is_an_authored_png(self):
        self.assertTrue(native.fixture_photo().startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertEqual(native.fixture_photo(),native.fixture_photo())

    def test_bad_ppm_extent_or_truncation_refuses(self):
        p=self.base/'bad.ppm'
        for data in (b'',b'P3\n800 400\n255\n',b'P6\n800 400\n255\n',b'P6\n99999 99999\n255\n',b'P6\n1 1\n255\n\0\0\0'):
            p.write_bytes(data)
            with self.subTest(data=data),self.assertRaises(ValueError):native.ppm(p)

    def test_actual_pixel_controls_distinguish_mask_tint_and_raw(self):
        self.frames();result=native.images(self.base,['HEADLESS-1'],'#00ff00')
        effects=result['photo-HEADLESS-1.ppm']['original_effects']
        self.assertEqual(effects['symbolic_green_pixels'],1600)
        self.assertEqual(effects['raw_center'],(255,0,0))
        self.assertNotEqual(effects['rounded_photo_corners'][0],(255,0,255))

    def test_exactly_one_of_two_outputs_must_paint(self):
        self.frames();self.frames('HEADLESS-2',active=False)
        native.images(self.base,['HEADLESS-1','HEADLESS-2'],'#00ff00')
        self.frames('HEADLESS-2',active=True)
        with self.assertRaisesRegex(ValueError,'exactly one'):native.images(self.base,['HEADLESS-1','HEADLESS-2'],'#00ff00')

    def test_no_card_or_uncontrolled_palette_refuses(self):
        self.frames(active=False)
        with self.assertRaisesRegex(ValueError,'exactly one'):native.images(self.base,['HEADLESS-1'],'#00ff00')
        with self.assertRaisesRegex(ValueError,'control palette'):native.images(self.base,['HEADLESS-1'],'#cacccc')

    def test_painting_outside_deck_refuses(self):
        self.frames(outside=True)
        with self.assertRaisesRegex(ValueError,'outside original'):native.images(self.base,['HEADLESS-1'],'#00ff00')

    def test_missing_original_mask_refuses(self):
        self.frames(square=True)
        with self.assertRaisesRegex(ValueError,'not rounded'):native.images(self.base,['HEADLESS-1'],'#00ff00')

    def test_missing_original_tint_or_raw_control_refuses(self):
        for tinted,raw in ((False,True),(True,False)):
            self.frames(tinted=tinted,raw=raw)
            with self.subTest(tinted=tinted,raw=raw),self.assertRaisesRegex(ValueError,'tint/raw'):native.images(self.base,['HEADLESS-1'],'#00ff00')

    def test_final_private_state_is_read_only(self):
        directory=self.private_state();before={p.name:p.read_bytes() for p in directory.iterdir()}
        self.assertEqual(native.validate_private_state(self.base),{'history_rows':4,'live_empty':True,'quiet_off':True})
        self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})

    def test_missing_state_is_not_prepared_or_reset(self):
        with self.assertRaises(OSError):native.validate_private_state(self.base)
        self.assertFalse((self.base/'home/.local').exists())
        directory=self.private_state();(directory/'live.json').unlink()
        with self.assertRaises(OSError):native.validate_private_state(self.base)
        self.assertFalse((directory/'live.json').exists())

    def test_bad_quiet_state_is_not_fixed(self):
        directory=self.private_state();path=directory/'quiet.json';path.write_text('{"dnd":true}')
        with self.assertRaisesRegex(ValueError,'quiet/live'):native.validate_private_state(self.base)
        self.assertEqual(path.read_text(),'{"dnd":true}')

    def test_final_history_requires_original_expiry_and_dnd_records(self):
        directory=self.private_state();path=directory/'history.json';rows=json.loads(path.read_text())
        for row in rows:row['closed_reason']='dismissed'
        path.write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError,'history/persistence'):native.validate_private_state(self.base)

    def test_final_state_refuses_public_or_hardlinked_files(self):
        directory=self.private_state();path=directory/'quiet.json';path.chmod(0o644)
        with self.assertRaises(ValueError):native.validate_private_state(self.base)
        path.chmod(0o600);(directory/'quiet-copy').hardlink_to(path)
        with self.assertRaises(ValueError):native.validate_private_state(self.base)


if __name__=='__main__':unittest.main()
