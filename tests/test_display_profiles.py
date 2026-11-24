"""Synthetic monitor transactions only: never contact a compositor or desktop."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import display_profile_model as m
import display_profiles as p


def monitor(name='DP-1',serial='fixture-1',x=0):
    return {'name':name,'make':'Synthetic','model':'Panel','serial':serial,'width':1920,'height':1080,
            'refreshRate':60.0,'scale':1,'x':x,'y':0,'transform':0,'disabled':False,'mirrorOf':-1,
            'availableModes':['1920x1080@60.00Hz','1280x720@60.00Hz']}


class Fake:
    def __init__(self,monitors=None):self.monitors=copy.deepcopy(monitors or [monitor()]);self.owner={'signature':'fixture','pid':123,'start':'456','inode':1};self.calls=[];self.fail_after=None
    def inventory(self):return copy.deepcopy(self.monitors)
    def apply(self,o):
        self.calls.append(copy.deepcopy(o))
        if self.fail_after is not None and len(self.calls)>self.fail_after:raise ValueError('injected failure')
        for current in self.monitors:
            if current['name']==o['identity']['connector']:
                current.update(width=o['width'],height=o['height'],refreshRate=o['refresh'],scale=o['scale'],x=o['x'],y=o['y'],transform=o['transform'],disabled=not o['enabled']);return
        raise ValueError('missing output')
    def settle(self,target):
        if not m.same(m.snapshot(self.monitors),target):raise ValueError('readback mismatch')
        return m.snapshot(self.monitors)


class DisplayProfileTests(unittest.TestCase):
    def setUp(self):
        base=ROOT/'work/tests';base.mkdir(parents=True,exist_ok=True);self.tmp=tempfile.TemporaryDirectory(dir=base);self.addCleanup(self.tmp.cleanup)
        self.native=Fake();self.now=10;self.guards=[]
        self.s=p.Profiles(Path(self.tmp.name)/'state',native=self.native,clock=lambda:self.now,guard=lambda token:self.guards.append(token))
    def profile(self,name='Desk'):
        return {'schema_version':1,'name':name,'outputs':m.snapshot(self.native.inventory()),'text_size':12}
    def save(self,profile=None):
        self.s.save(profile or self.profile(),m.digest(self.s.store()))
    def apply(self):
        review=self.s.review('Desk');return self.s.apply(review,m.digest(review))
    def altered(self):
        v=self.profile();v['outputs'][0]['scale']=1.5;v['text_size']=14;return v
    def test_status_and_capture_do_not_create_state_or_apply(self):
        self.s.overview();p.dispatch(self.s,{'op':'capture','name':'Desk'})
        self.assertFalse(self.s.directory.exists());self.assertFalse(self.native.calls)
    def test_closed_profile_and_wire_schemas(self):
        for value in ({'op':'reload'},{'op':'status','extra':True},[],{'op':'apply','review':{},'approval':'a'}):
            with self.assertRaises((ValueError,KeyError)):p.dispatch(self.s,value)
        v=self.profile();v['exec']='x'
        with self.assertRaises(ValueError):m.validate(v)
        p.put(self.s.pending_path,{})
        with self.assertRaises(ValueError):self.s.set_text(14)
        self.assertFalse(self.native.calls)
    def test_save_never_applies_and_keeps_a_private_backup(self):
        self.save();self.assertEqual(self.native.calls,[]);self.assertEqual(len(list((self.s.directory/'backups').glob('*.json'))),1)
        self.assertEqual(self.s.path.stat().st_mode&0o777,0o600)
        self.assertEqual(self.s.home.stat().st_mode&0o777,0o700)
    def test_profile_store_digest_prevents_lost_updates(self):
        self.save()
        with self.assertRaises(ValueError):self.s.save(self.profile('Other'),'stale')
        self.assertNotIn('Other',self.s.store()['profiles'])
    def test_review_is_read_only_and_stale_review_cannot_apply(self):
        self.save(self.altered());review=self.s.review('Desk');self.assertFalse(self.native.calls)
        self.native.monitors[0]['x']=1
        with self.assertRaises(ValueError):self.s.apply(review,m.digest(review))
        self.assertFalse(self.guards)
    def test_tampered_review_or_owner_cannot_apply(self):
        self.save();review=self.s.review('Desk')
        with self.assertRaises(ValueError):self.s.apply(review,'0'*64)
        self.native.owner={'signature':'other'}
        with self.assertRaises(ValueError):self.s.apply(review,m.digest(review))
    def test_apply_has_durable_intent_and_guard_before_native_write(self):
        self.save(self.altered())
        def guard(token):
            self.assertEqual(self.native.calls,[]);self.assertEqual(self.s.pending()['token'],token)
            self.assertEqual(p.read(self.s.receipt(token))['status'],'prepared')
        self.s.guard=guard;result=self.apply();self.assertEqual(result['status'],'awaiting-confirmation');self.assertEqual(self.s.text_size(),14)
        record=p.read(self.s.receipt(result['token']));self.assertGreater(len(record['allowed']),1)
    def test_guard_failure_issues_no_native_write(self):
        self.save();self.s.guard=mock.Mock(side_effect=ValueError('unavailable'))
        with self.assertRaises(ValueError):self.apply()
        self.assertFalse(self.native.calls);self.assertTrue(self.s.pending())
    def test_keep_marks_only_exact_profile_as_previously_accepted(self):
        self.save(self.altered());result=self.apply();self.s.keep(result['token'])
        self.assertIsNone(self.s.pending());self.assertEqual(self.s.store()['profiles']['Desk']['kept_digest'],m.digest(self.altered()))
        previous=self.s.overview()['previous'][0];self.assertEqual(previous['text_size'],12);self.assertEqual(previous['outputs'][0]['scale'],1)
        self.assertEqual(p.read(self.s.receipt(result['token']))['store_before_keep']['profiles']['Desk']['kept_digest'],None)
    def test_restore_restores_original_geometry_and_text_absence(self):
        self.save(self.altered());before=self.native.inventory();result=self.apply();self.s.restore(result['token'])
        self.assertTrue(m.same(m.snapshot(before),self.s.current()));self.assertFalse(self.s.text_path.exists());self.assertIsNone(self.s.pending())
    def test_restore_preserves_exact_existing_text_bytes_and_mode(self):
        p.atomic(self.s.text_path,b'11\n');self.s.text_path.chmod(0o640);self.save(self.altered());result=self.apply();self.s.restore(result['token'])
        self.assertEqual(self.s.text_path.read_bytes(),b'11\n');self.assertEqual(self.s.text_path.stat().st_mode&0o777,0o640)
    def test_keep_after_deadline_refuses_but_restore_is_available(self):
        self.save(self.altered());result=self.apply();self.now=99
        with self.assertRaises(ValueError):self.s.keep(result['token'])
        self.s.restore(result['token']);self.assertIsNone(self.s.pending())
    def test_external_geometry_text_and_owner_drift_are_not_overwritten(self):
        for kind in ('geometry','text','owner'):
            with self.subTest(kind=kind):
                self.setUp();self.save(self.altered());result=self.apply();calls=len(self.native.calls)
                if kind=='geometry':self.native.monitors[0]['x']=777
                elif kind=='text':p.atomic(self.s.text_path,b'20\n')
                else:self.native.owner={'signature':'new'}
                with self.assertRaises(ValueError):self.s.restore(result['token'])
                self.assertEqual(len(self.native.calls),calls);self.assertTrue(self.s.pending())
    def test_partial_failure_can_restore_an_intended_prefix(self):
        self.native.monitors.append(monitor('DP-2','fixture-2',1920));v=self.profile();v['outputs'][0]['scale']=1.5;v['outputs'][1]['x']=1280;self.save(v);self.native.fail_after=1
        with self.assertRaises(ValueError):self.apply()
        token=self.s.pending()['token'];self.native.fail_after=None;self.s.restore(token)
        self.assertTrue(m.same(self.s.current(),self.profile()['outputs']))
        self.assertEqual(self.native.monitors[1]['x'],1920)
    def test_disappeared_or_replaced_output_refuses_recovery(self):
        self.save(self.altered());result=self.apply();self.native.monitors[0]['serial']='replacement'
        with self.assertRaises(ValueError):self.s.restore(result['token'])
        self.native.monitors[0]['serial']='fixture-1';self.native.monitors[0]['availableModes']=['1280x720@60.00Hz'];calls=len(self.native.calls)
        with self.assertRaises(ValueError):self.s.restore(result['token'])
        self.assertEqual(len(self.native.calls),calls)
    def test_pending_blocks_other_writers_and_acknowledge_does_not_restore(self):
        self.save(self.altered());result=self.apply()
        with self.assertRaises(ValueError):self.s.set_text(16)
        with self.assertRaises(ValueError):self.s.acknowledge(result['token'])
        self.now=99;calls=len(self.native.calls);self.s.acknowledge(result['token']);self.assertEqual(len(self.native.calls),calls)
    def test_automation_requires_an_exact_previously_kept_profile(self):
        self.save(self.altered())
        with self.assertRaises(ValueError):self.s.automatic('Desk',True,m.digest(self.s.store()))
        result=self.apply();self.s.keep(result['token']);self.s.automatic('Desk',True,m.digest(self.s.store()))
        self.native.monitors[0]['scale']=1;last,result=self.s.auto_tick(None);self.assertEqual(result['status'],'kept')
        count=len(self.native.calls);self.native.monitors[0]['scale']=1
        last,result=self.s.auto_tick(last);self.assertEqual(result['status'],'unchanged-topology-no-write');self.assertEqual(len(self.native.calls),count)
    def test_automation_never_applies_a_partial_or_unknown_topology(self):
        self.save();result=self.apply();self.s.keep(result['token']);self.s.automatic('Desk',True,m.digest(self.s.store()));self.native.monitors.append(monitor('DP-2','fixture-2',1920))
        count=len(self.native.calls);_,result=self.s.auto_tick(None);self.assertEqual(result['status'],'no-unique-approved-profile');self.assertEqual(len(self.native.calls),count)
    def test_save_edit_revokes_previous_automation_acceptance(self):
        self.save();result=self.apply();self.s.keep(result['token']);self.s.automatic('Desk',True,m.digest(self.s.store()));self.save(self.altered())
        self.assertEqual(self.s.store()['automatic'],[]);self.assertIsNone(self.s.store()['profiles']['Desk']['kept_digest'])
    def test_text_size_is_shell_local_and_backed_up(self):
        self.s.set_text(16);self.assertEqual(self.s.text_size(),16);self.assertFalse(self.native.calls)
        for v in (True,13,999,'14'):
            with self.assertRaises(ValueError):self.s.set_text(v)
    def test_legacy_current_permissions_use_private_parent_without_chmod(self):
        self.s.home.mkdir(mode=0o700);current=self.s.home/'current';current.mkdir(mode=0o775);current.chmod(0o775)
        self.assertEqual(self.s.text_size(),12);self.s.set_text(14)
        self.assertEqual(self.s.text_size(),14);self.assertEqual(current.stat().st_mode&0o777,0o775)
        self.s.home.chmod(0o755)
        with self.assertRaises(ValueError):self.s.text_size()
        self.s.home.chmod(0o700)
    def test_no_symlink_state_or_text_overwrite(self):
        outside=Path(self.tmp.name)/'outside';outside.mkdir();self.s.home.mkdir();self.s.directory.symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):self.save()
    def test_geometry_rejects_disable_all_overlap_gaps_nonintegral_and_invalid_fields(self):
        invalid=[]
        v=self.profile();v['outputs'][0]['enabled']=False;invalid.append(v)
        v=self.profile();v['outputs'][0]['scale']=1.7;invalid.append(v)
        v=self.profile();v['outputs'][0]['scale']=float('nan');invalid.append(v)
        v=self.profile();v['outputs'][0]['transform']=True;invalid.append(v)
        self.native.monitors.append(monitor('DP-2','fixture-2',1920))
        v=self.profile();v['outputs'][1]['x']=100;invalid.append(v)
        v=self.profile();v['outputs'][1]['x']=3000;invalid.append(v)
        for v in invalid:
            with self.assertRaises(ValueError):m.validate(v)
    def test_rotation_negative_coordinates_and_supported_modes(self):
        v=self.profile();o=v['outputs'][0];o.update(transform=1,x=-1080,y=-1920)
        m.validate(v,self.native.inventory());program=m.program(o);self.assertIn('transform = 1',program);self.assertIn('position = "-1080x-1920"',program)
        o['refresh']=144
        with self.assertRaises(ValueError):m.validate(v,self.native.inventory())
    def test_unique_serial_can_rebind_connector_but_duplicate_serial_refuses(self):
        v=self.profile();self.native.monitors[0]['name']='DP-9';bound=m.bind(v['outputs'],self.native.inventory());self.assertEqual(bound[0]['identity']['connector'],'DP-9')
        self.native.monitors.append(monitor('DP-2'))
        with self.assertRaises(ValueError):m.snapshot(self.native.inventory())
    def test_advanced_monitor_features_refuse_before_any_action(self):
        for change in ({'vrr':True},{'colorManagementPreset':'hdr'},{'currentFormat':'XRGB2101010'},{'mirrorOf':'DP-2'},{'sdrBrightness':1.5}):
            value=monitor();value.update(change)
            with self.assertRaises(ValueError):m.snapshot([value])
        self.assertFalse(self.native.calls)
    def test_no_serial_is_connector_bound_and_lua_injection_refuses(self):
        self.native.monitors[0]['serial']='';v=self.profile();self.native.monitors[0]['name']='DP-9'
        with self.assertRaises(ValueError):m.bind(v['outputs'],self.native.inventory())
        v['outputs'][0]['identity']['connector']='DP-1"});evil()'
        with self.assertRaises(ValueError):m.validate(v)
    def test_all_outputs_enabled_before_disabling_and_last_output_guard(self):
        self.native.monitors.append(monitor('DP-2','fixture-2',1920));v=self.profile();v['outputs'][0]['enabled']=False;v['outputs'][1]['x']=0;self.save(v);result=self.apply()
        self.assertTrue(self.native.calls[0]['enabled']);self.assertFalse(self.native.calls[-1]['enabled']);self.s.restore(result['token']);self.assertTrue(all(o['enabled'] for o in self.s.current()))


if __name__=='__main__':unittest.main()
