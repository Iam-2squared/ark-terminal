import copy
import tempfile
import unittest
from scripts import phase57_raw_selector_direct_entry_preflight as a


def row(time,symbol='A',score=1,rank=1):
    return {'selectorEventId':'2024-09-17|'+time+'|'+symbol,'sessionDate':'2024-09-17','symbol':symbol,
        'decisionTimestamp':'2024-09-17T'+time+':00+09:00','decisionTimeJst':time,'decisionPrice':100,
        'decisionPriceAvailableAtJst':'2024-09-17T'+time+':00+09:00','decisionPriceKind':'LATEST_ACCEPTED_MINUTE_CLOSE',
        'referenceAgeMin':0,'savedV1Score':score,'newEligibleRank':rank}


class PreflightTests(unittest.TestCase):
    def test_canonical_identity_and_actual_cadence(self):
        rows,ep,s=a.build();self.assertEqual(len(rows),3800);self.assertEqual(len(ep),2841)
        self.assertEqual(s['raw']['timestamps'],760);self.assertEqual(s['raw']['candidateCountDistribution'],{5:760})
        self.assertEqual(s['raw']['candidateCountMean'],5)
    def test_inventory_misidentification(self):
        old=a.read(a.ROOT/'docs/evidence/phase57-price75-entry-opportunity-timestamp-counts-v1/summary.json')
        p=old['panels']['FROZEN_SELECTOR_DECISION_TIMESTAMPS']
        self.assertEqual(p['opportunityEvents'],2841);self.assertAlmostEqual(p['candidateSymbols']['mean'],2841/760)
        self.assertEqual(old['scope'],'SAVED_OPPORTUNITY_TIMESTAMP_SYMBOL_COUNT_ONLY')
    def test_outcomes_removed(self):
        r=row('09:30');r.update(futureMFE=999,highOpportunity3=1,futureLOW=-5)
        self.assertEqual(a.project([r]),a.project([row('09:30')]))
    def test_unknown_five_minute_tick_no_forward_fill(self):
        s=a.known_state([row('09:30'),row('10:00')],'2024-09-17','A','2024-09-17T09:35:00+09:00')
        self.assertEqual(s['status'],'UNOBSERVED_NO_SELECTOR_DECISION');self.assertIsNone(s['currentScore'])
    def test_future_rank_and_selection_do_not_affect_past(self):
        rows=[row('09:30'),row('10:00',score=2,rank=3)];t='2024-09-17T09:30:00+09:00'
        base=a.known_state(rows,'2024-09-17','A',t);rows[1].update(symbol='B',savedV1Score=-999,newEligibleRank=5)
        self.assertEqual(base,a.known_state(rows,'2024-09-17','A',t))
    def test_actual_observed_drop_only(self):
        rows=[row('09:30'),row('10:00','B')]
        s=a.known_state(rows,'2024-09-17','A','2024-09-17T10:00:00+09:00')
        self.assertEqual(s['status'],'OBSERVED_DROPPED');self.assertIsNone(s['currentScore']);self.assertEqual(s['scoreHistory'],[1])
    def test_reselection_and_single_episode(self):
        rows=[row('09:30'),row('10:00','B'),row('10:30')]
        s=a.known_state(rows,'2024-09-17','A','2024-09-17T10:30:00+09:00')
        self.assertEqual(s['status'],'RESELECTED');self.assertEqual(s['selectionGapsKnown'],1)
        ep=[r for r in a.episodes(rows) if r['symbol']=='A'];self.assertEqual(len(ep),1);self.assertEqual(ep[0]['selectionCount'],2)
    def test_continuity_means_observed_slots(self):
        rows=[row('09:30'),row('10:00'),row('10:30')]
        self.assertEqual(a.episodes(rows)[0]['maxConsecutiveObservedSelections'],3)
    def test_lunch_break_explicit(self):
        ep=a.episodes([row('11:30'),row('13:00')])[0]
        self.assertEqual(ep['crossLunchSelectedPairs'],1);self.assertEqual(ep['maxConsecutiveObservedSelections'],2)
    def test_session_identity_prevents_cross_day_merging(self):
        r=row('09:30');s=copy.deepcopy(r);s.update(sessionDate='2024-09-18',decisionTimestamp='2024-09-18T09:30:00+09:00')
        self.assertEqual(len(a.episodes([r,s])),2)
    def test_deterministic_order(self):
        rs=[row('09:30'),row('10:00','B'),row('10:30')]
        self.assertEqual(a.project(rs),a.project(list(reversed(rs))))
        self.assertEqual(a.episodes(rs),a.episodes(list(reversed(rs))))
    def test_safety_and_no_overwrite(self):
        self.assertEqual(len(a.SAFETY),9);self.assertTrue(all(v is False for v in a.SAFETY.values()))
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):a.run(d)


if __name__=='__main__':unittest.main()
