import ast
import unittest
from pathlib import Path
import numpy as np
from scripts.phase57_exit_failure_anatomy_r40 import (
    active_future_endpoint,bucket,canonical,decision_now,first_true,pattern_record,
    post_exit_path,prediction_diagnostics,signal_transitions,summary)


class FailureAnatomyTests(unittest.TestCase):
    def test_numpy_pattern_scalars_serialize_without_dropping(self):
        import json
        self.assertEqual(json.loads(canonical({'a':np.int64(7),'b':np.float32(1.5),'c':np.bool_(True)})),{'a':7,'b':1.5,'c':True})
    def test_unavailable_and_nonpositive_buckets_are_retained(self):
        for value in (None,'UNAVAILABLE','NON_POSITIVE_RANGE'):
            self.assertEqual(bucket({'metrics':{'bucket':value}}),'NOT_EVALUABLE')
        self.assertEqual(bucket({'metrics':{'bucket':'>=5%'}}),'>=5%')
    def test_lunch_uses_active_schedule(self):
        self.assertEqual(active_future_endpoint(688,5),753)
        self.assertEqual(active_future_endpoint(690,5),755)
        self.assertEqual(active_future_endpoint(750,5),755)
    def test_horizon_truncation_is_not_terminal_substitute(self):
        self.assertIsNone(active_future_endpoint(924,5))
        self.assertIsNone(active_future_endpoint(930,5))
    def test_decision_inverse_auction_and_lunch(self):
        self.assertEqual(decision_now({'exitKind':'MODEL_EXIT','exitMinute':750}),690)
        self.assertEqual(decision_now({'exitKind':'FORCED_TERMINAL','exitMinute':930}),925)
        self.assertIsNone(decision_now({'exitKind':None,'exitMinute':None}))
    def test_missing_fresh_close_never_counts_as_recovery_or_return(self):
        times=np.arange(601,611);closes=np.array([999]*5+[101]*5,dtype=float)
        fresh=np.array([False]*5+[True]*5)
        out=post_exit_path(times,closes,fresh,600,100,100,102)
        self.assertIsNone(out['returnsPctByActiveHorizon']['5']['returnFromExitPct'])
        self.assertEqual(out['recoveryAboveExit']['firstObservedEndpoint'],606)
        self.assertIsNone(out['recoveryAboveOwnedObservedPeak']['firstObservedEndpoint'])
    def test_close_recovery_is_strict(self):
        out=post_exit_path(np.array([601,602]),np.array([100,101]),np.ones(2,dtype=bool),600,100,100,100)
        self.assertEqual(out['recoveryAboveExit']['firstObservedEndpoint'],602)
    def test_unknown_is_not_signal_disappearance(self):
        out=signal_transitions(['TRUE','UNKNOWN','FALSE','TRUE','FALSE'])
        self.assertEqual(out,{'FALSE→TRUE':1,'TRUE→FALSE':1,'TRUE→UNKNOWN':1,'UNKNOWN→FALSE':1})
    def test_heads_negative_first_and_max_require_all(self):
        times=np.array([601,602,603,604]);pred=np.array([[-1,1,1],[-1,-1,1],[-1,-1,-1],[-1,-1,-1]],float)
        out=prediction_diagnostics(times,pred,np.array([True,True,False,True]),0,604)
        self.assertEqual(out['firstNegativeHeads'],['HOLD5'])
        self.assertEqual(out['firstNegativeByHead']['HOLD_TERMINAL'],604)
        self.assertEqual(out['firstAllHeadsExitSide'],604)
        self.assertEqual(out['disagreementCheckpoints'],2)
    def test_post_exit_predictions_do_not_change_pre_exit_diagnostics(self):
        t=np.array([601,602,603]);p=np.array([[1,1,1],[-1,-1,-1],[-9,-9,-9]],float)
        a=prediction_diagnostics(t,p,np.ones(3,dtype=bool),0,602)
        p[-1]=[999,999,999]
        self.assertEqual(a,prediction_diagnostics(t,p,np.ones(3,dtype=bool),0,602))
    def test_numpy_scalars_are_measured_not_silently_dropped(self):
        self.assertEqual(summary([np.float32(1),np.float32(3),None])['mean'],2)
    def test_pattern_availability_preserves_nulls(self):
        out=pattern_record({'MOM/A':1,'MOM/B':None,'VOL/A':2})
        self.assertEqual(out['families']['MOM']['knownFraction'],.5)
        self.assertIsNone(out['values']['MOM/B'])
    def test_module_has_no_fit_replay_or_order_call(self):
        import scripts.phase57_exit_failure_anatomy_r40 as m
        tree=ast.parse(Path(m.__file__).read_text())
        calls={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        self.assertFalse(calls&{'fit','fit_transform','fit_predict','replay_candidate','fit_predictions','replay_and_score','place_order'})


if __name__=='__main__':unittest.main()
