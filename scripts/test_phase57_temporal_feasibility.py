import unittest
import numpy as np
from scripts import phase57_temporal_feasibility as f
from scripts import phase57_sparse_handoff as s

class FeasibilityTests(unittest.TestCase):
 def setUp(self):
  p=s.admission.plan();self.allowed=set(p['dailyDevelopment'])|set(p['intradayDevelopment']);self.intra=p['intradayDevelopment'];self.days=[d for d in s.calendar() if min(self.allowed)<=d<=max(self.allowed)]
 def test_dates_fixed_by_calendar_only(self):
  r=f.calendar_schedule(self.days,self.allowed,self.intra);self.assertTrue(r['feasible'])
  self.assertEqual([(x['computedThrough'][:10],x['testStart'],x['testEnd']) for x in r['rows']],[('2024-11-12','2024-11-20','2025-05-01'),('2025-06-06','2025-06-16','2025-07-23'),('2025-07-15','2025-07-24','2025-08-21')])
 def test_future_mapping_never_used(self):
  rows=f.calendar_schedule(self.days,self.allowed,self.intra)['rows'];through=rows[0]['testEnd']
  for r in rows[1:]:self.assertLess(through,r['computedThrough'][:10])
 def test_independent_targets_and_causal_embargo(self):
  rows=f.calendar_schedule(self.days,self.allowed,self.intra)['rows']
  for r in rows:self.assertEqual(r['embargoExchangePositions'],5);self.assertEqual(r['targetPotentialEligible'],20);self.assertGreaterEqual(r['sourcePotentialEligible'],30)
  self.assertLess(rows[0]['testEnd'],rows[1]['testStart']);self.assertLess(rows[1]['testEnd'],rows[2]['testStart'])
 def test_truncated_input_reports_missing_support(self):
  days=[d for d in self.days if d<='2025-07-23'];r=f.calendar_schedule(days,self.allowed,self.intra);self.assertFalse(r['feasible'])
 def test_no_market_values_enter_scheduler(self):
  r=f.calendar_schedule(self.days,self.allowed,self.intra)
  self.assertEqual(r,f.calendar_schedule(list(self.days),set(self.allowed),list(self.intra)))
 def test_warmup_not_counted_as_valid_observation(self):
  rows=f.calendar_schedule(self.days,self.allowed,self.intra)['rows'];self.assertEqual(rows[0]['targetAllowedSessions'],26);self.assertEqual(rows[0]['targetPotentialEligible'],20)
 def test_past_source_invariant_to_all_future_observations(self):
  rng=np.random.default_rng(416);x=rng.normal(size=(100,110));cv=rng.normal(size=(100,110,4));el=np.ones((100,110),bool)
  args=({'id':'synthetic','transform':'identity'},np.arange(60),np.arange(65,85),59)
  first=f.d.pair(x,cv,el,*args)
  x[60:]=1e12;cv[60:]=1e12;el[60:]=False
  second=f.d.pair(x,cv,el,*args)
  for key in ['post','peer','sd','weight','coverage']:np.testing.assert_equal(first[0][key],second[0][key])
  self.assertEqual(first[2],second[2]);self.assertEqual(first[3],second[3])
 def test_exact_development_boundary(self):
  p=s.admission.plan();self.assertEqual(len(self.intra),144);self.assertEqual(len(p['commonHoldout']),244)
  self.assertFalse(set(self.intra)&set(p['commonHoldout']));self.assertFalse(self.allowed&set(p['excluded']))
if __name__=='__main__':unittest.main()
