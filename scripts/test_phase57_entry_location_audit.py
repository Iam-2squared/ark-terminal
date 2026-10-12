"""Independent denominator semantics and attribution identities."""
import unittest
from scripts import audit_phase57_entry_location_study as a
from scripts import phase57_entry_location_study as s


class AuditSemanticsTests(unittest.TestCase):
    def test_missing_no_touch_is_unknown_but_observed_hit_known(self):
        w={'status':'UNKNOWN_INCOMPLETE','upside':None,'observedUpsideLowerBound':2.5}
        self.assertIsNone(a.outcome(w,3))
        self.assertIs(a.outcome(w,2),True)
        self.assertIs(a.outcome({'status':'COMPLETE','upside':2.5},3),False)

    def test_threshold_roundoff_is_not_a_missed_touch(self):
        self.assertTrue(a.touch(3-1e-14,3))
        self.assertFalse(a.touch(2.99999,3))
        self.assertFalse(a.touch(None,3))

    def test_capture_denominator_is_original_decision_not_reference_winners(self):
        rows=[{'eventId':str(i),'policies':{'WAIT5':{'status':'REFERENCE_OPEN','common60':{'status':'COMPLETE','upside':v}}}} for i,v in enumerate([2,4])]
        original={str(i):{'status':'COMPLETE','upside':v} for i,v in enumerate([4,2])}
        v=a.preservation(rows,original,'common60','WAIT5',3)
        self.assertEqual(v['originalKnownWinners'],1)
        self.assertEqual(v['knownLost'],1)
        self.assertEqual(v['preserved'],0)


class SavedAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit=s.read(s.BASE/'denominator-and-window-audit.json.gz')

    def test_full_original_census_winner_counts_and_conservation(self):
        for row in self.audit['originalOpportunityPreservation']:
            self.assertEqual(sum(row[k] for k in ['preserved','knownLost','unknown','boundaryNoReferenceEntry']),row['originalKnownWinners'])
            if row['panel']=='FULL_SAVED_SESSION_OBSERVED_DECISION_PRICE' and row['cohort']=='ALL':
                self.assertEqual(row['originalKnownWinners'],{1:2055,2:1619,3:1212,5:609}[row['levelPct']])

    def test_common60_original_counts_and_no_unknowns(self):
        for row in self.audit['originalOpportunityPreservation']:
            if row['panel']=='PRIMARY_COMMON60_DECISION_PRICE' and row['cohort']=='ALL':
                self.assertEqual(row['originalKnownWinners'],{1:633,2:440,3:296,5:141}[row['levelPct']])
                self.assertEqual(row['unknown']+row['boundaryNoReferenceEntry'],0)

    def test_window_and_buy_price_attribution_sum_exactly(self):
        count=0
        for rows in self.audit['windowAttributionLedger'].values():
            for r in rows:
                self.assertAlmostEqual(r['windowShiftImprovementPP']+r['buyPriceEffectImprovementPP'],r['totalD30ImprovementPP'],places=12)
                count+=1
        self.assertEqual(count,878*5)

    def test_exclusion_and_coverage_counts(self):
        counts=self.audit['primaryExclusionReasons']
        self.assertEqual(sum(counts.values()),2743)
        self.assertEqual(counts['PRIMARY_COMPLETE'],878)
        for field in ['firstClosedDip','timeOfDay','segment']:
            rows=[r for r in self.audit['coverageByGroup'] if r['field']==field]
            self.assertEqual(sum(r['full'] for r in rows),2743)
            self.assertEqual(sum(r['primary'] for r in rows),878)


if __name__=='__main__':unittest.main()
