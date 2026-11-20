import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scripts import phase57_integrated_long_entry_v1 as z
from scripts.test_phase57_comprehensive_entry_v3 import fixture


class Scores:
    def __init__(self,values):self.values=values
    def predict(self,f):return self.values[f['elapsed']//5] if isinstance(self.values[0],list) else self.values


class IntegratedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p=z.protocol();cls.h=cls.p['decision']['thresholds']
    def sample(self,closes=None,start=540):
        x,p,s=fixture(start=start) if closes is None else fixture(closes,start)
        return x,p,s,z.states(x,p,s,{})
    def test_protocol_feature_identity(self):
        self.assertEqual(len(z.FEATURES),66);self.assertEqual(len(set(z.FEATURES)),66)
        self.assertEqual(z.FEATURES[:43],z.m.FEATURES);self.assertEqual(self.p['architecture']['fitBudget'],1)
    def test_split_and_upstream_identity(self):
        p,ops,paths,selectors,legacy=z.sources('TRAIN')
        self.assertEqual(len(ops),1760);self.assertEqual(len({x['id'] for x in ops}),1760)
        self.assertEqual([len(p['split'][k]) for k in ['TRAIN','VALIDATION','DEVELOPMENT_TEST']],[38,19,19])
        self.assertTrue(all(x['session'] in p['split']['TRAIN'] for x in ops))
    def test_dev_test_fresh_oos_rejected(self):
        for p in ['DEVELOPMENT_TEST','FRESH','OOS']:
            with self.assertRaisesRegex(RuntimeError,'SEALED'):z.sources(p)
    def test_no_evaluator_dependency(self):
        x,p,s=fixture()
        with patch.object(z.v2,'evaluate',side_effect=AssertionError),patch.object(z.m,'path_class',side_effect=AssertionError):
            ss=z.states(x,p,s,{});self.assertEqual(z.decide(x,p,ss,Scores([.4,.5,.2]),self.p)['delay'],0)
    def test_completed_bar_semantics(self):
        _,_,_,ss=self.sample()
        self.assertEqual([s['delay'] for s in ss],[0,5,10,15])
        self.assertTrue(all(s['newestCompletedEnd'] is None or s['newestCompletedEnd']<=s['timestamp'] for s in ss))
    def test_future_ohlc_mutation_invariance(self):
        x,p,s,ss=self.sample();changed=copy.deepcopy(p)
        for b in changed['future'][2:]:b.update(o=5,h=99,l=-50,c=6)
        self.assertEqual(ss[:3],z.states(x,changed,s,{})[:3])
    def test_future_outcome_metadata_ignored(self):
        x,p,s,ss=self.sample();p.update(futureMFE=999,pathClass='IMMEDIATE_WINNER',bestFutureEntry=1)
        self.assertEqual(ss,z.states(x,p,s,{}))
    def test_immediate_route(self):
        x,p,s,ss=self.sample();r=z.decide(x,p,ss,Scores([.25,.1,.1]),self.p)
        self.assertEqual((r['route'],r['delay']),('A',0))
    def test_pullback_context_required(self):
        _,_,_,ss=self.sample();state=copy.deepcopy(ss[2]);state['descriptors'].update(newLowStopped=True,closeDeteriorationStopped=True)
        self.assertEqual(z.route(state,[0,.3,.2],self.h),('B','BUY_NOW'))
        self.assertEqual(z.route(state,[0,.1,.2],self.h),('C','WAIT_ONE_STEP'))
    def test_pullback_alone_not_buy(self):
        _,_,_,ss=self.sample();s=copy.deepcopy(ss[1]);s['pullbackSeen']=True
        self.assertEqual(z.route(s,[0,.3,.2],self.h),('C','WAIT_ONE_STEP'))
    def test_delayed_urgent_route_c(self):
        _,_,_,ss=self.sample();self.assertEqual(z.route(ss[1],[.3,.3,.2],self.h),('C','BUY_NOW'))
    def test_failure_skip_priority(self):
        _,_,_,ss=self.sample();self.assertEqual(z.route(ss[0],[.9,.09,.75],self.h),('D','SKIP'))
    def test_wait_exactly_one_step_and_cap(self):
        x,p,s,ss=self.sample();r=z.decide(x,p,ss,Scores([0,.1,.4]),self.p)
        self.assertEqual([t['delay'] for t in r['transitions']],[0,5,10,15]);self.assertEqual(r['status'],'EXPIRE_WAIT_CAP')
    def test_cap_buy(self):
        _,_,_,ss=self.sample();s=copy.deepcopy(ss[-1]);s['pullbackSeen']=False
        self.assertEqual(z.route(s,[0,.2,.4],self.h),('C','BUY_NOW'))
    def test_missing_prefix_no_resurrection(self):
        x,p,s,_=self.sample();p['future'][0]['missing']=True;ss=z.states(x,p,s,{})
        self.assertTrue(all(r['status']=='EXPIRE_MISSING_PREFIX' for r in ss[1:]))
        r=z.decide(x,p,ss,Scores([0,.1,.4]),self.p);self.assertEqual(r['status'],'EXPIRE_MISSING_PREFIX')
    def test_gap_fail_closed(self):
        x,p,s,_=self.sample();del p['future'][0]
        self.assertEqual(z.states(x,p,s,{})[1]['status'],'EXPIRE_MISSING_PREFIX')
    def test_missing_reference(self):
        x,p,s,_=self.sample();x['op']['referencePrice']=None
        self.assertTrue(all(r['status']=='EXPIRE_REFERENCE' for r in z.states(x,p,s,{})))
    def test_execution_open_not_signal_low(self):
        x,p,s,ss=self.sample();model=Scores([[0,.1,.4],[.4,.4,.2],[.4,.4,.2],[.4,.4,.2]])
        r=z.decide(x,p,ss,model,self.p)
        self.assertEqual(r['delay'],5);self.assertEqual(r['executionPrice'],98.)
        p['future'][1].update(h=99,l=-99,c=20)
        self.assertEqual(r,z.decide(x,p,z.states(x,p,s,{}),model,self.p))
    def test_missing_execution_open_no_substitution(self):
        x,p,s,ss=self.sample();p['future'][0]['o']=None
        r=z.decide(x,p,z.states(x,p,s,{}),Scores([.4,.4,.2]),self.p)
        self.assertEqual(r['status'],'EXPIRE_MISSING_OPEN');self.assertIsNone(r['delay'])
    def test_session_boundary_no_cross(self):
        x,p,s,ss=self.sample(start=685);r=z.decide(x,p,ss,Scores([0,.1,.4]),self.p)
        self.assertEqual(len(r['transitions']),1);self.assertEqual(r['status'],'EXPIRE_BOUNDARY')
        self.assertTrue(all(s['status']=='EXPIRE_BOUNDARY' for s in ss[1:]))
    def test_intrabar_unknown(self):
        _,_,_,ss=self.sample();self.assertTrue(all(s['intrabarOrder']=='UNKNOWN_INTRABAR_ORDER' for s in ss))
    def test_initial_dip_identity(self):
        x,p,s,ss=self.sample();x['op']['eventType']=z.q.DIP
        dd=z.states(x,p,s,{});self.assertEqual(dd[0]['features']['isDip'],1)
        self.assertEqual(dd[0]['descriptors'],ss[0]['descriptors'])
    def test_no_duplicate_entry(self):
        x,p,s,ss=self.sample();r=z.decide(x,p,ss,Scores([.4,.5,.2]),self.p)
        self.assertEqual(sum(t['action']=='BUY_NOW' for t in r['transitions']),1);self.assertEqual(len(r['transitions']),1)
    def test_no_state_labels(self):
        _,_,_,ss=self.sample()
        for s in ss:self.assertEqual(set(s['features']),set(z.FEATURES))
        self.assertFalse(set(z.FEATURES)&{'pathClass','futureMFE','futureLOW','symbol','session'})
    def test_missingness_indicators_and_deterministic_inference(self):
        artifact={'medians':[1.]*66,'tree':{'children_left':[-1],'children_right':[-1],'feature':[-2],'threshold':[-2.],'value':[[[.2],[.3],[.4]]]}}
        model=z.Model(artifact);f=dict.fromkeys(z.FEATURES)
        self.assertTrue(np.array_equal(model.vector(f),np.ones(132,dtype=np.float32)))
        self.assertEqual(model.predict(f),model.predict(f))
    def test_fixed_near_miss_and_undefined(self):
        self.assertEqual(z.numeric_status(.87,.90,'fraction')['status'],'NEAR_MISS')
        self.assertEqual(z.numeric_status(.20,.90,'fraction')['status'],'HARD_FAIL')
        self.assertEqual(z.numeric_status(None,.90,'fraction')['status'],'HARD_FAIL')
    def test_safety_and_no_freeze(self):
        self.assertTrue(all(x is False for x in self.p['safety'].values()))
        self.assertFalse(self.p['runControl']['candidateFreeze'])
        self.assertTrue(all(x==0 for x in self.p['runControl']['postMeasurementChanges'].values()))
    def test_evidence_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileExistsError):z.train(td)
            with self.assertRaises(FileExistsError):z.validate(td,'missing')
    def test_state_and_route_repeat_deterministic(self):
        x,p,s,ss=self.sample();a=z.decide(x,p,ss,Scores([0,.1,.4]),self.p)
        self.assertEqual(ss,z.states(x,p,s,{}));self.assertEqual(a,z.decide(x,p,ss,Scores([0,.1,.4]),self.p))
    def test_invalid_model_score_fail_closed(self):
        _,_,_,ss=self.sample();self.assertEqual(z.route(ss[0],[float('nan'),.1,.2],self.h),('D','EXPIRE_INVALID_SCORE'))


if __name__=='__main__':unittest.main()
