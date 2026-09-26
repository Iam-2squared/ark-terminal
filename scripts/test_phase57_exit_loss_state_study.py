"""Causal and measurement semantics, not strategy profitability assertions."""
import copy
import tempfile
import unittest
from pathlib import Path

from scripts import phase57_exit_loss_state_study as s


def bar(slot, o, h, l, c):
    return {'slot':slot,'minutes':slot*5,'start':f'2024-09-17T09:{(slot-1)*5:02d}:00+09:00',
            'end':f'2024-09-17T09:{slot*5:02d}:00+09:00','o':o,'h':h,'l':l,'c':c,'missing':False}


class LossStateTests(unittest.TestCase):
    def test_completed_prefix_invariant_to_future_and_labels(self):
        bars=[bar(1,0,1,-1,-.5),bar(2,-.5,1,-2,-1),bar(3,-1,1,-3,-2)]
        observed=s.observation(bars,5)
        changed=copy.deepcopy(bars);changed[1].update(o=999.,h=999.,c=999.,missing=True)
        self.assertEqual(observed,s.observation(changed,5))
        self.assertEqual(observed,s.observation(bars[:1],5))

    def test_missing_prefix_not_imputed(self):
        bars=[bar(1,0,1,-1,-.5)];bars[0]['missing']=True
        self.assertEqual(s.observation(bars,5)['status'],'UNKNOWN_MISSING')

    def test_lunch_clock_boundary_rejected(self):
        bars=[bar(1,0,1,-1,-.5),bar(2,-.5,1,-2,-1)]
        bars[1]['minutes']=70
        self.assertEqual(s.observation(bars,10)['status'],'SESSION_BOUNDARY')

    def test_zero_range_is_unknown_for_normalized_state(self):
        bars=[bar(1,0,0,0,0),bar(2,0,0,0,0),bar(3,0,0,0,0)]
        self.assertIsNone(s.features(bars)['normalizedDisplacement'])
        self.assertIsNone(s.states(bars)['NORMALIZED_ACCELERATION'])

    def test_reclaim_rejection_requires_real_reclaim(self):
        bars=[bar(1,0,.3,-1,-.5),bar(2,-.5,.8,-.6,.2),bar(3,.2,.3,-1,-.8)]
        self.assertTrue(s.states(bars)['RECLAIM_REJECTION'])
        bars[1]['c']=-.1
        self.assertFalse(s.states(bars)['RECLAIM_REJECTION'])

    def test_failed_bounce_requires_intermediate_improvement(self):
        bars=[bar(1,0,.1,-1,-.8),bar(2,-.8,.5,-.9,-.2),bar(3,-.2,.1,-1.3,-1.2)]
        self.assertTrue(s.states(bars)['FAILED_BOUNCE'])
        bars[1]['c']=-.9
        self.assertFalse(s.states(bars)['FAILED_BOUNCE'])

    def test_normalized_acceleration_needs_wick_decay(self):
        bars=[bar(1,0,.2,-1,-.5),bar(2,-.5,0,-1.3,-.8),bar(3,-.8,0,-2.5,-2.4)]
        self.assertTrue(s.states(bars)['NORMALIZED_ACCELERATION'])
        bars[2].update(l=-5.,c=-2.4)
        self.assertFalse(s.states(bars)['NORMALIZED_ACCELERATION'])

    def test_same_bar_open_does_not_preserve_later_high(self):
        bars=[bar(1,0,2,-1,1),bar(2,1,6,0,5)]
        result={'exitBar':2,'status':'PROTECT_EXIT','grossPct':1.}
        self.assertFalse(s.preserved(result,bars,5))
        result['grossPct']=5.
        self.assertTrue(s.preserved(result,bars,5))

    def test_fixed_close_preserves_its_bar_high(self):
        self.assertTrue(s.preserved({'exitBar':1,'status':'FIXED12_FALLBACK','grossPct':-1.},[bar(1,0,6,-2,-1)],5))

    def test_unknown_milestone_is_not_failure(self):
        self.assertIsNone(s.preserved({'exitBar':1,'status':'FIXED12_FALLBACK','grossPct':0},[bar(1,0,1,-1,0)],5))

    def test_auc_ties_and_fixed_direction(self):
        self.assertEqual(s.auc([1,2],[1,2])['aucHigherDeep'],.5)
        self.assertEqual(s.auc([0],[2])['aucHigherDeep'],0)
        self.assertIsNone(s.auc([None],[2])['aucHigherDeep'])

    def test_output_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'evidence';p.mkdir();(p/'saved.txt').write_text('keep')
            with self.assertRaises(FileExistsError):s.run(p)
            self.assertEqual((p/'saved.txt').read_text(),'keep')

    def test_label_does_not_count_past_milestone_as_future_recovery(self):
        bars=[bar(1,0,4,-1,-.5),bar(2,-.5,5,-3,1)]
        labels=s.label_snapshot(bars,5,{'netPct':-6})
        self.assertFalse(labels['recovery3'])
        self.assertTrue(labels['recovery5'])
        self.assertTrue(labels['deepFailure'])


if __name__=='__main__':unittest.main()
