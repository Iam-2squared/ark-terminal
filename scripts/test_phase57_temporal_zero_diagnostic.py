import unittest
import numpy as np
from scripts import phase57_temporal_zero_diagnostic as d
from scripts import phase57_sparse_handoff as s

class DiagnosticTests(unittest.TestCase):
    def test_exclusive_and_overlapping_reasons(self):
        r,ok=d.first_failure({'A':np.array([False,True,False,True]),'B':np.array([False,False,True,True])})
        self.assertEqual(r.tolist(),['A','B','A','ELIGIBLE']);self.assertEqual(ok.tolist(),[False,False,False,True])
    def test_candidate_symbols_deduplicate_but_cells_do_not(self):
        self.assertEqual(d.distribution(np.array([True,True,False]),['A','A','B']),{'symbols':1,'symbolTraits':2})
    def test_calendar_source_support_bound(self):
        p=s.admission.plan();allowed=set(p['dailyDevelopment'])|set(p['intradayDevelopment']);days=[x for x in s.calendar() if min(allowed)<=x<=max(allowed)];folds=s.folds(days,p)
        self.assertEqual([sum(days[i] in allowed for i in f['train']) for f in folds],[5,25,45])
        self.assertLess(5,20);self.assertLess(25/60,s.sample_policy()['MEDIUM']['coverageMin'])
    def test_inherited_target20_blocks_explicit8(self):
        rng=np.random.default_rng(71);data=rng.normal(size=(20,110));data[-1]=np.nan;cov=rng.normal(size=(20,110,4));el=np.ones((20,110),bool);el[-1]=False
        a=s.snapshot(data,cov,el,{'id':'synthetic','transform':'identity'},np.arange(20))
        self.assertTrue(np.all(a['n']>=8));self.assertEqual(a['mask'].sum(),0);self.assertIsNone(a['fit']);self.assertTrue(np.all(np.isnan(a['post'])))
    def test_peer100_is_separate_requirement(self):
        rng=np.random.default_rng(72);a=s.snapshot(rng.normal(size=(20,99)),rng.normal(size=(20,99,4)),np.ones((20,99),bool),{'id':'synthetic','transform':'identity'},np.arange(20))
        self.assertEqual(a['mask'].sum(),99);self.assertIsNone(a['fit'])
    def test_fixed_endpoint_does_not_read_future(self):
        rng=np.random.default_rng(73);data=rng.normal(size=(130,110));cv=rng.normal(size=(130,110,4));el=np.ones((130,110),bool);item={'id':'synthetic','transform':'identity'}
        args=(item,np.arange(60),np.arange(65,85),59)
        a=d.pair(data,cv,el,*args);data[85:]=1e30;cv[85:]=1e30;b=d.pair(data,cv,el,*args)
        np.testing.assert_equal(a[0]['post'],b[0]['post']);np.testing.assert_equal(a[-1],b[-1])
    def test_mapping_cannot_precede_completion(self):
        self.assertFalse(s.calibration_available('2025-05-29','2025-05-22'));self.assertTrue(s.calibration_available('2025-05-29','2025-06-19'))
    def test_missing_dates_not_fabricated(self):
        x=np.array([[np.nan,2],[1,np.nan],[np.nan,3.]])
        self.assertEqual(d.date_bounds(x,np.arange(3),['a','b','c']),[('b','b'),('a','c')])
    def test_unchanged_sources(self):d.verify_sources()
    def test_numeric_range_has_exact_min_max(self):
        self.assertEqual(d.stats([1,7,np.nan])['max'],7);self.assertEqual(d.stats([1,7,np.nan])['min'],1)
if __name__=='__main__':unittest.main()
