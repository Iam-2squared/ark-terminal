import copy
import tempfile
import unittest
from pathlib import Path
from scripts import phase57_strict30_mae_attribution as m


def b(i,o=0,h=1,l=-1,c=0):
    return {'slot':i,'minutes':i*5,'start':f'2024-09-17T09:{(i-1)*5:02}:00+09:00',
            'end':f'2024-09-17T09:{i*5:02}:00+09:00','o':o,'h':h,'l':l,'c':c,'missing':False,'observedMinutes':5}


class AttributionTests(unittest.TestCase):
    def test_bucket_boundaries_are_disjoint(self):
        self.assertEqual([m.bucket(x) for x in [0,-1,-2,-3,-5,-10]],list(m.BUCKETS))
        self.assertEqual(m.bucket(-35),m.BUCKETS[-1])

    def test_same_bar_high_low_is_not_recovery(self):
        bs=[b(1,h=5,l=-5,c=-4),b(2,o=-4,h=-2,l=-6,c=-5)]
        self.assertEqual(m.classify(bs,0,5),'INCONCLUSIVE')
        self.assertFalse(m.after_anchor(bs,0)['recovery']['5']['observed'])

    def test_high_before_low_is_not_recovery(self):
        bs=[b(1,h=5,c=4),b(2,o=4,h=4,l=-5,c=-5),b(3,o=-5,h=-3,l=-7,c=-6)]
        # Trigger itself contains a high, so order remains unknown, not winner.
        self.assertEqual(m.classify(bs,1,5),'INCONCLUSIVE')
        self.assertEqual(m.path_metrics(bs,100)['ordering'],'MFE_BEFORE_MAE')

    def test_true_recovery_then_giveback_keeps_opportunity_label(self):
        bs=[b(1,h=1,l=-5,c=-4),b(2,o=-4,h=5,l=-4,c=-3),b(3,o=-3,h=-2,l=-8,c=-7)]
        self.assertEqual(m.classify(bs,0,5),'RECOVERY_WINNER')
        self.assertEqual(m.after_anchor(bs,0)['terminalPct'],-7)

    def test_reclaim_without_major_win(self):
        bs=[b(1,h=0,l=-5,c=-4),b(2,o=-4,h=2,l=-4,c=0)]
        self.assertEqual(m.classify(bs,0,5),'RECOVERY_BUT_NO_MAJOR_WIN')

    def test_trigger_close_reclaim_is_known_after_low(self):
        bs=[b(1,h=2,l=-5,c=1),b(2,o=1,h=2,l=-1,c=-1)]
        self.assertEqual(m.classify(bs,0,5),'RECOVERY_BUT_NO_MAJOR_WIN')
        self.assertTrue(m.after_anchor(bs,0)['triggerBarCloseReclaimKnown'])

    def test_continued_failure_and_small_loss_not_same(self):
        bs=[b(1,h=0,l=-5,c=-4),b(2,o=-4,h=-3,l=-7,c=-6)]
        self.assertEqual(m.classify(bs,0,5),'CONTINUED_FAILURE')
        bs[-1]['c']=-2
        self.assertEqual(m.classify(bs,0,5),'INCONCLUSIVE')

    def test_missing_session_cannot_prove_failure(self):
        bs=[b(1,l=-5,c=-4),b(2,o=-4,h=-3,l=-7,c=-6)]
        self.assertEqual(m.classify(bs,0,5,False),'INCONCLUSIVE')
        self.assertIsNone(m.after_anchor(bs,0,False)['laterCloseReclaim'])

    def test_last_bar_breach_no_followup_is_unknown(self):
        bs=[b(1,h=0,l=-5,c=-5)]
        self.assertEqual(m.classify(bs,0,5),'INCONCLUSIVE')
        self.assertIsNone(m.after_anchor(bs,0)['additionalDrop2'])

    def test_additional_drop_uses_breach_close_price(self):
        bs=[b(1,h=0,l=-6,c=-5),b(2,o=-5,h=-5,l=-7,c=-7)]
        self.assertAlmostEqual(m.after_anchor(bs,0)['additionalDropPctFromBreachClose'],100*(93/95-1))

    def test_open_exit_before_low_is_post_exit(self):
        bs=[b(1),b(2,o=1,h=2,l=-10,c=-9)]
        self.assertEqual(m.exit_vs_breach({'exitBar':2,'status':'PROTECT_EXIT','grossPct':1},bs,5),'BREACH_AFTER_EXIT_OPEN')
        self.assertEqual(m.exit_vs_breach({'exitBar':2,'status':'PROTECT_EXIT','grossPct':-6},bs,5),'BREACH_AT_OR_BEFORE_EXIT_OPEN')

    def test_close_exit_after_bar_low(self):
        self.assertEqual(m.exit_vs_breach({'exitBar':1,'status':'FIXED12_FALLBACK','grossPct':0},[b(1,l=-5)],5),'BREACH_BEFORE_OR_AT_CLOSE_EXIT')

    def test_strict30_prefix_invariance(self):
        bs=[b(i) for i in range(1,8)];x=m.strict30(bs)
        bs[6].update(missing=True,l=-99,h=999)
        self.assertEqual(x,m.strict30(bs))

    def test_sparse_minutes_disclosed_not_rejected(self):
        bs=[b(i) for i in range(1,7)];bs[2]['observedMinutes']=1
        self.assertEqual(m.strict30(bs)['status'],'COMPLETE')
        self.assertFalse(m.path_metrics(bs,100)['fullUnderlyingMinutes'])

    def test_lunch_gap_and_missing_are_not_imputed(self):
        bs=[b(i) for i in range(1,7)];bs[5]['minutes']=90
        self.assertEqual(m.strict30(bs)['status'],'LUNCH_OR_SESSION_BOUNDARY')
        bs[5]['minutes']=30;bs[1]['missing']=True
        self.assertEqual(m.strict30(bs)['status'],'MISSING_BAR')

    def test_zero_mae_uses_entry_reference(self):
        x=m.path_metrics([b(1,o=1,h=5,l=1,c=3),b(2,o=3,h=6,l=2,c=5)],100)
        self.assertEqual(x['maeLocation']['price'],100)
        self.assertTrue(x['afterGlobalMae']['recovery']['5']['observed'])

    def test_verdict_precommitted_rules(self):
        self.assertEqual(m.verdict({'CONTINUED_FAILURE':80,'RECOVERY_WINNER':10,'INCONCLUSIVE':10},100),'DEEP_MAE_PRIMARILY_ENTRY_FAILURE')
        self.assertEqual(m.verdict({'CONTINUED_FAILURE':45,'RECOVERY_WINNER':35,'INCONCLUSIVE':20},100),'DEEP_MAE_MIXED_RECOVERY_AND_FAILURE')
        self.assertEqual(m.verdict({'CONTINUED_FAILURE':10},10),'INCONCLUSIVE')

    def test_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):m.run(Path(d))


if __name__=='__main__':unittest.main()
