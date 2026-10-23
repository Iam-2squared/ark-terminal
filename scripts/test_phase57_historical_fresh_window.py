import copy
import unittest
from audit_phase57_historical_fresh_window import audit, upper_bound


class FreshWindowBoundTests(unittest.TestCase):
    def test_current_metadata_has_no_thirty_session_window(self):
        result=audit()
        self.assertEqual(result['primary']['longestUnblockedWeekdayRun'],4)
        self.assertEqual(result['primary']['unblockedWeekdayUpperBound'],27)
        self.assertEqual(result['widenedBoundarySensitivity']['longestUnblockedWeekdayRun'],6)
        self.assertFalse(result['global195ExactDatesRequired'])
        self.assertFalse(result['futureGDateUsedAsBlocker'])

    def test_weekend_does_not_split_trading_sequence(self):
        r=upper_bound([],'2026-09-04','2026-09-07',[])
        self.assertEqual(r['longestUnblockedWeekdayRun'],2)
        self.assertEqual(r['freshSessionsCertified'],0)

    def test_exposure_splits_sequence_even_without_reservation(self):
        r=upper_bound([{'sessionDate':'2026-09-07','primaryClassification':'EXPOSED'}],'2026-09-04','2026-09-08',[])
        self.assertEqual(r['longestUnblockedWeekdayRun'],1)

    def test_protected_envelope_blocks_unknown_dates_without_mapping(self):
        rows=[{'sessionDate':None,'primaryClassification':'UNKNOWN'}]
        before=copy.deepcopy(rows)
        r=upper_bound(rows,'2026-09-07','2026-09-09',[{'first':'2026-09-07','last':'2026-09-09'}])
        self.assertEqual(r['longestUnblockedWeekdayRun'],0)
        self.assertEqual(rows,before)

    def test_duplicate_identity_fails_closed(self):
        row={'sessionDate':'2026-09-07','primaryClassification':'SEALED'}
        with self.assertRaisesRegex(ValueError,'DUPLICATE_LEDGER_DATE'):
            upper_bound([row,row],'2026-09-07','2026-09-09',[])

    def test_outcome_siblings_never_used_or_rendered(self):
        class Poison:
            def __repr__(self):
                raise AssertionError('OUTCOME_RENDERED')
        base={'sessionDate':'2026-09-07','primaryClassification':'EXPOSED'}
        enriched=dict(base,classCounts=Poison(),candidateScore=Poison())
        self.assertEqual(upper_bound([base],'2026-09-07','2026-09-09',[]),
                         upper_bound([enriched],'2026-09-07','2026-09-09',[]))


if __name__=='__main__':
    unittest.main()
