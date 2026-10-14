"""Same admitted native path; never use real market originals or authority."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tools'))
from ark_selector_v2.authority import Authority,production_authority
from ark_selector_v2.native_fixture import fixture_authority,install_test_grant,request_for
from ark_selector_v2.native import NativeReader
from ark_selector_v2.orchestration import dispatch,Store
from ark_selector_v2.contracts import FLAGS,digest,feature_names,configuration_hash,registry
from ark_selector_v2.approval_package import propose_window,package_hash
from ark_selector_v2.exact_math import V2Error
from ark_selector_v2.selection import rank_candidates
import v2_cli


class NativeRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='ark-v2-native-route-')
        cls.authority,cls.manifest=fixture_authority(Path(cls.temp.name)/'isolated')
        a=cls.authority;m=cls.manifest
        cls.census=dispatch('census',request_for(a,m,'B'),authority=a)
        a.precommit['census_receipt_sha256']=digest(cls.census);install_test_grant(a,'C')
        from sklearn.ensemble import HistGradientBoostingClassifier
        original_fit=HistGradientBoostingClassifier.fit
        with patch.object(HistGradientBoostingClassifier,'fit',autospec=True,side_effect=original_fit) as calls:
            cls.train=dispatch('train',request_for(a,m,'C'),authority=a)
            cls.actual_fit_calls=calls.call_count
            cls.cal=dispatch('calibrate',request_for(a,m,'C'),authority=a)
            cls.calibration_extra_fit_calls=calls.call_count-cls.actual_fit_calls
        cls.pred=dispatch('predict',request_for(a,m,'C','VALIDATION'),authority=a)
        cls.evaluation=dispatch('evaluate',request_for(a,m,'C','VALIDATION'),authority=a)
        cls.restore=dispatch('restore-verify',request_for(a,m,'C','VALIDATION'),authority=a)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def fresh(self):
        a=copy.deepcopy(self.authority)
        a.output=Path(self.temp.name)/('fresh-'+self.id().rsplit('.',1)[-1]);a.artifact_pins={}
        install_test_grant(a,"B");install_test_grant(a,"C")
        return a,copy.deepcopy(self.manifest)

    def repin(self,a,m,mode='B'):
        a.manifest_pin=digest(m);a.precommit['manifest_sha256']=a.manifest_pin
        install_test_grant(a,mode)

    def blocked_before_native(self,a,m,stage='census',mode='B',role='FIT_CAL',reason=None):
        with patch.object(NativeReader,'read',side_effect=AssertionError('payload opened')) as read:
            with self.assertRaises(V2Error) as caught:dispatch(stage,request_for(a,m,mode,role),authority=a)
            read.assert_not_called()
        if reason:self.assertIn(reason,str(caught.exception))

    def test_n01_full_native_census_fit_cal_forecast_eval_restore(self):
        self.assertEqual(self.census['stats']['FIT']['known'],720)
        self.assertEqual(self.census['stats']['CAL']['known'],360)
        self.assertEqual(self.train['fits'],2);self.assertEqual(self.cal['calibrations'],2)
        self.assertEqual(self.restore['prediction_max_abs_difference'],0)
        self.assertTrue(self.census['test_only'])

    def test_n02_native_features_all95_not_arbitrary_matrix(self):
        f=Store(self.authority).get('forecast-VALIDATION.json')
        self.assertEqual(tuple(f['rows'][0]['values']),tuple(sorted(feature_names()))) # JSON sorted storage; matrix uses registered order
        self.assertEqual(len(f['rows'][0]['values']),95)
        for r in f['rows']:
            self.assertEqual(sum(v is None for k,v in r['values'].items() if k in feature_names()[51:]),44)
            self.assertTrue(r['provenance']['dependency_sets'])

    def test_n03_census_never_opens_validation_final_teachers(self):
        accesses=Store(self.authority).get('access-census-FIT_CAL.json')
        self.assertTrue(all(r['purpose'] not in {'VALIDATION_TEACHER','FINAL_TEACHER'} for r in accesses))
        self.assertEqual(self.census['market_fits'],0)

    def test_n04_prediction_never_mounts_current_session_teachers(self):
        accesses=Store(self.authority).get('access-predict-VALIDATION.json')
        self.assertTrue(all(not r['purpose'].endswith('TEACHER') for r in accesses))
        for e in accesses:
            if e['purpose']=='HISTORY':self.assertLess(e['session'],max(self.authority.precommit['split']['VALIDATION']))

    def test_n05_default_authority_all_six_stages_denied_before_any_open(self):
        self.assertIsNone(production_authority())
        with patch.object(Path,'read_text',side_effect=AssertionError('request opened')):
            for stage in ('census','train','calibrate','predict','evaluate','restore-verify'):
                self.assertEqual(v2_cli.main([stage,'--request','missing.json']),2)

    def test_n06_self_declared_approval_rejected(self):
        a,m=self.fresh();r=request_for(a,m,'B');r['approval']['owner_original_sha256']='a'*64
        with patch.object(NativeReader,'read') as read:
            with self.assertRaisesRegex(V2Error,'UNTRUSTED'):dispatch('census',r,authority=a)
            read.assert_not_called()

    def test_n07_owner_original_text_pin_independent(self):
        from dataclasses import replace
        a,m=self.fresh();a.grants['B']=replace(a.grants['B'],original_text='forged approval')
        self.blocked_before_native(a,m,reason='OWNER_ORIGINAL')

    def test_n08_code_hash_drift_blocks_without_refit(self):
        a,m=self.fresh();a.precommit['hashes']['code']='f'*64;install_test_grant(a,'B')
        self.blocked_before_native(a,m,reason='CODE_CONFIG_SCHEMA')

    def test_n09_schema_drift_blocks(self):
        a,m=self.fresh();a.precommit['hashes']['schema']='f'*64;install_test_grant(a,'B')
        self.blocked_before_native(a,m,reason='CODE_CONFIG_SCHEMA')

    def test_n10_manifest_drift_blocks(self):
        a,m=self.fresh();m['entries'][0]['bytes']+=1
        self.blocked_before_native(a,m,reason='MANIFEST_PIN')

    def test_n11_cal_protected_descriptor_fails_before_first_history_open(self):
        a,m=self.fresh();day=a.precommit['split']['CAL'][0]
        next(e for e in m['entries'] if e['dataset']=='DAILY' and e['session']==day)['protected']=True
        self.repin(a,m);self.blocked_before_native(a,m,reason='PROTECTED')

    def test_n12_purpose_outside_allowlist_before_open(self):
        a,m=self.fresh();a.precommit['allowlists']['CAL_TEACHER']=[];install_test_grant(a,'B')
        self.blocked_before_native(a,m,reason='PURPOSE_DATE')

    def test_n13_original_rights_and_dates_bound(self):
        a,m=self.fresh();e=next(e for e in m['entries'] if 'FIT_TEACHER' in e['purposes']);e['original']['allowed_purposes']=['HISTORY']
        self.repin(a,m);self.blocked_before_native(a,m,reason='ORIGINAL_MANIFEST')

    def test_n14_test_authority_cannot_accept_market_descriptor(self):
        a,m=self.fresh();m['entries'][0]['test_only']=False;self.repin(a,m)
        self.blocked_before_native(a,m,reason='TEST_NATIVE')

    def test_n15_generated_fixture_hashes_cannot_be_replaced(self):
        a,m=self.fresh();m['entries'][0]['sha256']='0'*64;self.repin(a,m)
        self.blocked_before_native(a,m,reason='REAL_ROWS_OR_CHANGED_BYTES')

    def test_n16_path_traversal_before_payload_open(self):
        a,m=self.fresh();m['entries'][0]['path']='../escape.json';self.repin(a,m)
        self.blocked_before_native(a,m,reason='PATH_TRAVERSAL')

    def test_n17_source_route_no_automatic_fallback(self):
        a,m=self.fresh();a.precommit['source_routes']['daily']='JQUANTS_MONTHLY_GZIP_UNIMPLEMENTED';install_test_grant(a,'B')
        self.blocked_before_native(a,m,reason='UNIMPLEMENTED_SOURCE_ROUTE')

    def test_n18_fit_role_leak_before_open(self):
        a=copy.deepcopy(self.authority)
        self.blocked_before_native(a,self.manifest,'train','C','VALIDATION',reason='LEARNER_DESCRIPTOR_ROLE_LEAK')

    def test_n19_mode_B_cannot_fit(self):
        a,m=self.fresh();a.grants.pop('C')
        # A B request cannot make the C stage authorized.
        with self.assertRaisesRegex(V2Error,'AWAITING_MARKET_APPROVAL:C'):dispatch('train',request_for(a,m,'B'),authority=a)

    def test_n20_mode_C_requires_parent_and_passed_census(self):
        a,m=self.fresh();a.grants.pop('B')
        self.blocked_before_native(a,m,'train','C',reason='MODE_C_REQUIRES')

    def test_n21_market_budget_changes_not_minor_adjustment(self):
        from dataclasses import replace
        a,m=self.fresh();g=a.grants['C'];approval=copy.deepcopy(g.approval);approval['budget']['fits']=3
        a.grants['C']=replace(g,approval=approval,approval_pin=digest(approval))
        self.blocked_before_native(a,m,'train','C',reason='BUDGET')

    def test_n22_native_two_fit_two_cal_budget_events_and_no_retry(self):
        pins=self.authority.artifact_pins
        self.assertEqual(sum('FIT_STARTED' in p for p in pins),2)
        self.assertEqual(sum('CAL_STARTED' in p for p in pins),2)
        with patch.object(NativeReader,'read') as read:
            with self.assertRaises(FileExistsError):dispatch('train',request_for(self.authority,self.manifest,'C'),authority=self.authority)
            read.assert_not_called()

    def test_n23_model_hash_is_not_independent_trust(self):
        a=copy.deepcopy(self.authority);a.artifact_pins.pop('fixed-model.joblib')
        with patch.object(Path,'read_bytes',side_effect=AssertionError('pickle opened')):
            with self.assertRaisesRegex(V2Error,'INDEPENDENT_ARTIFACT'):Store(a).get('fixed-model.joblib',model=True)

    def test_n24_all_watchlists_fixed_before_teacher_open(self):
        a=copy.deepcopy(self.authority);a.artifact_pins.pop('watchlists-VALIDATION.json')
        self.blocked_before_native(a,self.manifest,'evaluate','C','VALIDATION',reason='INDEPENDENT_ARTIFACT')

    def test_n25_all_safety_flags_false_header_and_item(self):
        sealed=Store(self.authority).get('watchlists-VALIDATION.json')
        for w in sealed['watchlists']:
            self.assertTrue(all(w[f] is False for f in FLAGS))
            for item in w['items']:self.assertTrue(all(item[f] is False for f in FLAGS))

    def test_n26_final_stays_sealed_after_actual_synthetic_failure(self):
        self.assertEqual(self.evaluation['status'],'FAIL')
        self.blocked_before_native(self.authority,self.manifest,'predict','C','FINAL',reason='FINAL_REMAINS_SEALED')
        self.assertFalse(any('LABEL_OPENED-FINAL' in p for p in self.authority.artifact_pins))

    def test_n27_feature_ranking_repeat_deterministic(self):
        f=Store(self.authority).get('forecast-VALIDATION.json')
        from ark_selector_v2.selection import joint
        import numpy as np
        q,p3,p5=joint(np.asarray(f['a']),np.asarray(f['b']))
        candidates=[{'canonical_symbol':r['canonical_symbol'],'g1':'PASS','g2':'PASS','q':q[i].tolist(),'p3':float(p3[i]),'p5':float(p5[i])} for i,r in enumerate(f['rows']) if r['session']==f['sessions'][0]]
        self.assertEqual(rank_candidates(candidates),rank_candidates(list(reversed(candidates))))

    def test_n28_teacher_maturity_before_next_partition(self):
        a,m=self.fresh();a.precommit['teacher_open_after']['CAL']=a.precommit['split']['VALIDATION'][0]+'T16:30:00+09:00';install_test_grant(a,'B')
        self.blocked_before_native(a,m,reason='MATURITY')

    def test_n29_window_does_not_skip_protected_latest_or_choose_older(self):
        days=self.authority.precommit['calendar_sessions']
        # Expand solely generated date metadata for a 350-session inventory.
        from datetime import date,timedelta
        days=[(date(2040,1,1)+timedelta(days=i)).isoformat() for i in range(360)]
        plan=propose_window(days,{'DAILY':days,'MASTER':days},protected={days[-1]},candidate_range=days)
        self.assertEqual(plan['status'],'BLOCKED_PROTECTED_LATEST_INVENTORY_WINDOW')
        self.assertEqual(plan['split']['FINAL'][-1],days[-1]);self.assertEqual(plan['authorized_teacher_days'],0)

    def test_n30_approval_package_precise_missing_calendar_and_no_false_permission(self):
        package=json.loads((ROOT/'MARKET_APPROVAL_PACKAGE_DRAFT.json').read_text())
        self.assertEqual(package_hash(package),package['package_sha256'])
        self.assertIsNone(package['exact_window']['fit_120'])
        self.assertEqual(package['exact_window']['teacher_dates_approved'],[])
        self.assertEqual(len(package['source_inventory_objects']),26)
        self.assertEqual(package['mode_B']['market_fits'],0)
        self.assertTrue(package['mode_C']['separate_owner_approval_after_mode_B_pass'])

    def test_n31_native_ram_preflight_before_raw_open(self):
        a,m=self.fresh();a.precommit['resource_limits']['ram_bytes']=1;install_test_grant(a,'B')
        self.blocked_before_native(a,m,reason='RAM_PREFLIGHT')

    def test_n32_future_teacher_poison_not_read_by_forecast(self):
        a,m=self.fresh();day=a.precommit['split']['FINAL'][-1]
        future=next(e for e in m['entries'] if e['dataset']=='DAILY' and e['session']==day)
        path=a.root/future['path'];original=path.read_bytes()
        try:
            path.write_bytes(b'{"future_label":true,"close":NaN}')
            with patch.object(NativeReader,'read',wraps=NativeReader(a,m,a.precommit).read) as read:
                rows=NativeReader(a,m,a.precommit).forecast('VALIDATION')
                self.assertTrue(all(call.args[0]['session']!=day for call in read.call_args_list))
                self.assertTrue(all(call.args[0]['authorized_purpose']!='FINAL_TEACHER' for call in read.call_args_list))
                expected=Store(self.authority).get('forecast-VALIDATION.json')['rows']
                self.assertEqual([r['feature_hash'] for r in rows.rows],[r['feature_hash'] for r in expected])
        finally:path.write_bytes(original)

    def test_n33_no_fit_on_failed_teacher_support(self):
        a,m=self.fresh();Store(a).put('census.json',self.census)
        with patch('ark_selector_v2.orchestration.teacher_support',side_effect=V2Error('BLOCKED_INSUFFICIENT_TEACHER_SUPPORT')):
            with patch('ark_selector_v2.orchestration.HistGradientBoostingClassifier') as estimator:
                with self.assertRaisesRegex(V2Error,'TEACHER_SUPPORT'):dispatch('train',request_for(a,m,'C'),authority=a)
                estimator.assert_not_called()
        self.assertFalse(any('FIT_STARTED' in k for k in a.artifact_pins))
        self.assertTrue((a.output/'failure-train-FIT_CAL.json').exists())

    def test_n34_actual_fit_spy_no_additional_calibration_fit(self):
        self.assertEqual(self.actual_fit_calls,2)
        self.assertEqual(self.calibration_extra_fit_calls,0)
        grant=self.authority.grants['B'].approval
        self.assertNotIn('VALIDATION_TEACHER',grant['allowlists'])
        self.assertNotIn('FINAL_TEACHER',grant['allowlists'])


if __name__=='__main__':unittest.main()
