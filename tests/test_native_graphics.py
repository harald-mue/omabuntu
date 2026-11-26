"""Device-free graphics harness guards and synthetic pixel controls; no native launch."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import check_native_graphics as graphics
import build_runtime as builder


class NativeGraphicsTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(dir=ROOT/'work');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name)

    def image(self,tinted=True):
        width,height=400,180;raw=bytearray(width*height*3)
        for x,y,color in ((50,50,(0,255,0) if tinted else (255,0,0)),
                          (150,50,(255,0,0)),(260,60,(0,0,255))):
            raw[(y*width+x)*3:(y*width+x)*3+3]=bytes(color)
        target=self.base/'fixture.ppm';target.write_bytes(b'P6\n400 180\n255\n'+raw)
        return target

    def lab(self):
        root=self.base/'root';root.mkdir()
        downloads=self.base/'downloads';downloads.mkdir()
        records={}
        for name,version in graphics.PACKAGES.items():
            deb=downloads/(name+'.deb');deb.write_bytes(('synthetic '+name).encode())
            notice=root/'usr/share/doc'/name/'copyright';notice.parent.mkdir(parents=True);notice.write_text('Synthetic notice')
            records[name]={'version':version,'sha256':builder.digest(deb),'copyright_sha256':builder.digest(notice)}
        (self.base/'packages.json').write_text(json.dumps(records))
        (self.base/'root-manifest.json').write_text(json.dumps(graphics.package_manifest(root)))
        return records

    def test_default_is_plan_only_and_never_runs(self):
        with patch.object(graphics,'run') as run,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(graphics.main([]),0)
            run.assert_not_called();self.assertIn('Plan only',out.getvalue())

    def test_positive_and_negative_pixel_controls_are_distinct(self):
        self.assertEqual(graphics.inspect_ppm(self.image(True),True)['samples']['shader'],(0,255,0))
        self.assertEqual(graphics.inspect_ppm(self.image(False),False)['samples']['shader'],(255,0,0))
        with self.assertRaisesRegex(ValueError,'shader pixel'):graphics.inspect_ppm(self.image(False),True)
        with self.assertRaisesRegex(ValueError,'shader pixel'):graphics.inspect_ppm(self.image(True),False)

    def test_missing_mask_or_raw_control_refuses(self):
        p=self.image(True);data=p.read_bytes();offset=data.index(b'255\n')+4
        for x,y in ((221,21),(150,50),(260,60)):
            modified=bytearray(data);index=offset+(y*400+x)*3;modified[index:index+3]=bytes((255,255,255));p.write_bytes(modified)
            with self.subTest(x=x,y=y),self.assertRaises(ValueError):graphics.inspect_ppm(p,True)

    def test_truncated_or_unexpected_screenshot_refuses(self):
        p=self.base/'bad.ppm'
        for data in (b'',b'P6\n400 180\n255\n',b'P6\n99999 99999\n255\n',b'P3 400 180 255'):
            p.write_bytes(data)
            with self.subTest(data=data),self.assertRaises(ValueError):graphics.inspect_ppm(p,True)

    def test_sandbox_has_no_host_bus_device_or_display_mount(self):
        with patch.object(Path,'is_file',return_value=True):
            args=graphics.sandbox(self.base/'runtime',self.base/'case',self.base/'lab',2)
        self.assertIn('--unshare-all',args);self.assertIn('--clearenv',args)
        self.assertNotIn('--dev-bind',args)
        mounts=[args[i+1:i+3] for i,value in enumerate(args) if value in ('--bind','--ro-bind')]
        self.assertFalse(any(str(item).startswith(('/run/user','/dev/dri','/dev/input','/tmp/')) for pair in mounts for item in pair))
        env={args[i+1]:args[i+2] for i,value in enumerate(args) if value=='--setenv'}
        self.assertEqual(env['QT_QPA_PLATFORM'],'wayland')
        self.assertEqual(env['QSG_RHI_BACKEND'],'opengl');self.assertNotIn('QT_QUICK_BACKEND',env)
        self.assertEqual(env['WLR_BACKENDS'],'headless');self.assertEqual(env['WLR_RENDERER'],'pixman')
        self.assertEqual(env['LABWC_UPDATE_ACTIVATION_ENV'],'0');self.assertEqual(env['WLR_HEADLESS_OUTPUTS'],'2')
        self.assertTrue(env['DBUS_SESSION_BUS_ADDRESS'].startswith('unix:path=/nonexistent/'))
        self.assertFalse(set(env)&{'HYPRLAND_INSTANCE_SIGNATURE','WAYLAND_DISPLAY','WAYLAND_SOCKET','DISPLAY'})
        for binary in ('Xwayland','systemctl','dbus-update-activation-environment'):
            self.assertIn([str(self.base/'case/probe/deny-exec'),'/usr/bin/'+binary],mounts)

    def test_fixture_never_uses_notifications_or_fake_native_surfaces(self):
        compile(graphics.DRIVER,'private-graphics-driver','exec')
        compile(graphics.GUARD,'private-exec-guard','exec')
        self.assertIn('PanelWindow {',graphics.QML)
        self.assertIn('Variants {',graphics.QML)
        self.assertIn('brightness:__TINT__;colorization:__TINT__',graphics.QML)
        self.assertNotIn('NotificationServer',graphics.QML)
        self.assertIn("'actual llvmpipe renderer evidence'",graphics.DRIVER)
        self.assertIn('Created shm allocator',graphics.DRIVER)
        self.assertIn('children_reaped',graphics.DRIVER)

    def test_exact_synthetic_lab_manifest_verifies_without_process_execution(self):
        self.lab()
        with patch.object(graphics.subprocess,'run',side_effect=AssertionError('No execution')):
            self.assertEqual(graphics.verify_lab(ROOT,self.base),self.base)

    def test_version_or_deb_tampering_refuses(self):
        records=self.lab();name='labwc'
        records[name]['version']='unknown';(self.base/'packages.json').write_text(json.dumps(records))
        with self.assertRaisesRegex(ValueError,'pin differs'):graphics.verify_lab(ROOT,self.base)
        records[name]['version']=graphics.PACKAGES[name];(self.base/'packages.json').write_text(json.dumps(records))
        (self.base/'downloads/labwc.deb').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'package changed'):graphics.verify_lab(ROOT,self.base)

    def test_extracted_tree_and_notice_tampering_refuse(self):
        self.lab();(self.base/'root/extra').write_bytes(b'unreviewed')
        with self.assertRaisesRegex(ValueError,'input changed'):graphics.verify_lab(ROOT,self.base)
        (self.base/'root/usr/share/doc/labwc/copyright').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'notice changed'):graphics.verify_lab(ROOT,self.base)

    def test_symlinked_seal_and_escaping_payload_refuse(self):
        self.lab();p=self.base/'packages.json';saved=self.base/'saved-seal';p.rename(saved);p.symlink_to(saved)
        with self.assertRaisesRegex(ValueError,'regular lab input'):graphics.verify_lab(ROOT,self.base)
        (self.base/'root/escape').symlink_to(self.base/'saved-seal')
        with self.assertRaisesRegex(ValueError,'Escaping lab'):graphics.package_manifest(self.base/'root')

    def test_candidate_must_remain_in_workspace_work(self):
        with self.assertRaisesRegex(ValueError,'under private work'):
            graphics.verify_lab(ROOT,ROOT/'work/../../not-a-lab')


if __name__=='__main__':unittest.main()
