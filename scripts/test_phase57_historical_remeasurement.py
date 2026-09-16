import unittest
from run_phase57_historical_remeasurement import causal_decisions, preservation

class CausalReplayTests(unittest.TestCase):
    def rows(self):
        return [dict(selectorEventId=str(i),symbolSessionId='s',decisionTimestamp=f'2024-12-02T10:{i*5:02d}:00+09:00',label={'labelable':i>0}) for i in range(3)]
    def test_unlabelable_first_entry_blocks_reentry(self):
        actual=causal_decisions(self.rows(),[2.1,2.3,2.4])
        self.assertEqual([r['state'] for r in actual],['ENTER','SKIP_THIS_DECISION','SKIP_THIS_DECISION'])
    def test_future_labels_do_not_gate_any_decision(self):
        rows=self.rows();before=causal_decisions(rows,[1.9,2,3]);rows[1]['label']={'labelable':False,'ordinalClass':4}
        self.assertEqual(before,causal_decisions(rows,[1.9,2,3]))
    def test_threshold_equality_and_independent_symbol(self):
        rows=self.rows();rows[1]['symbolSessionId']='t'
        self.assertEqual([r['state'] for r in causal_decisions(rows,[2,2,2])],['ENTER','ENTER','SKIP_THIS_DECISION'])
    def test_transfer_is_not_remaining_opportunity(self):
        first={'s':self.rows()[0]};entry={**self.rows()[1],'decisionTimestamp':'2024-12-02T11:00:00+09:00'}
        paths={'0':{'labelable':True,'highReturnPct':5},'1':{'labelable':True,'highReturnPct':0}}
        p=preservation(first,{'s':entry},paths,1)['1']
        self.assertEqual(p['preservationPct'],100);self.assertEqual(p['timelyPreservationPct'],0);self.assertEqual(p['winnerAndRemainingHit'],0)
    def test_score_count_identity(self):
        with self.assertRaises(ValueError):causal_decisions(self.rows(),[2])
if __name__=='__main__':unittest.main()
