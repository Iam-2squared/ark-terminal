import copy, unittest
from scripts import phase57_entry_extended as e

def bar(t,o=100,h=106,l=99,c=101,day='2025-06-02'):
 return dict(Date=day,Time='%02d:%02d'%divmod(t,60),Code='12340',O=o,H=h,L=l,C=c,Vo=10,Va=1000)
def calculate(raw,start=570,h=30,price=100,day='2025-06-02'):
 lab=e.f.labels_for_raw(dict(sessionDate=day,decisionTimeJst='%02d:%02d'%divmod(start,60),decisionPrice=price),raw,None)
 return e.horizon(day,start,price,raw,h,lab)
class ExtendedTests(unittest.TestCase):
 def test_mfe_mae_arithmetic(self):
  x=calculate([bar(t) for t in range(570,600)]);self.assertAlmostEqual(x['MFE'],6);self.assertAlmostEqual(x['MAE'],-1);self.assertAlmostEqual(x['returnNet'],.9495)
 def test_entry_zero_floor_ceiling(self):
  x=calculate([bar(t,o=102,h=105,l=101,c=104) for t in range(570,600)]);self.assertEqual(x['MAE'],0)
  x=calculate([bar(t,o=98,h=99,l=97,c=98) for t in range(570,600)]);self.assertEqual(x['MFE'],0)
 def test_running_peak_not_entry_mae(self):
  confirmed,adverse=e.drawdown_bounds(100,[bar(570,100,106,100,106),bar(571,106,106,101,101)])
  self.assertAlmostEqual(confirmed,100*(101/106-1));self.assertAlmostEqual(adverse,100*(100/106-1))
 def test_intrabar_ambiguity_bounds(self):
  confirmed,adverse=e.drawdown_bounds(100,[bar(570,100,106,100,106)])
  self.assertEqual(confirmed,0);self.assertAlmostEqual(adverse,-100*6/106)
 def test_drawdown_monotone_flat(self):
  self.assertEqual(e.drawdown_bounds(100,[bar(570,100,100,100,100)]),(0,0))
 def test_hit_all_five_thresholds_inclusive(self):
  rows=[dict(observedMFE=x,MFE=x,status='COMPLETE') for x in range(1,6)];hit=e.hit_rates(rows)
  for t in range(1,6):self.assertEqual(hit[str(t)]['observedHits'],6-t);self.assertEqual(hit[str(t)]['buyDenominator'],5)
 def test_partial_observed_hit_and_unknown(self):
  rows=[dict(observedMFE=3,MFE=None,status='CENSORED'),dict(observedMFE=None,MFE=None,status='UNAVAILABLE'),dict(observedMFE=1,MFE=1,status='COMPLETE')];x=e.hit_rates(rows)
  self.assertEqual(x['2']['observedHits'],1);self.assertEqual(x['2']['unknown'],1);self.assertEqual(x['2']['confirmedMisses'],1);self.assertEqual(x['4']['unknown'],2)
 def test_capture_denominator_no_entry_and_unknown(self):
  opps=[{'id':str(i),'selectorOutcome':{'mfeEnd':5}} for i in range(3)];tr=[{'opportunity':'0','entryId':'a'},{'opportunity':'1','entryId':None},{'opportunity':'2','entryId':'b'}];labs={'a':{'labels':{'mfeEnd':4}},'b':{'labels':None}}
  c=e.capture(opps,tr,labs)
  for t in range(1,6):self.assertEqual(c[str(t)]['selectorWinnerDenominator'],3);self.assertEqual(c[str(t)]['captured'],int(t<=4))
  self.assertEqual(c['5']['missed'],3);self.assertEqual(c['4']['unknownEntered'],1)
 def test_censored_session_not_zero(self):
  x=calculate([bar(t) for t in range(900,925)]+[bar(930)],start=900,h=60)
  self.assertEqual(x['status'],'CENSORED');self.assertIsNone(x['MFE']);self.assertIsNotNone(x['observedMFE'])
 def test_lunch_censored_no_afternoon(self):
  raw=[bar(t) for t in range(680,690)]+[bar(690),bar(750,100,1000,1,100)];x=calculate(raw,start=680)
  self.assertEqual(x['status'],'CENSORED');self.assertEqual(x['observedThroughMinute'],690);self.assertAlmostEqual(x['observedMFE'],6)
 def test_exact_lunch_endpoint_complete(self):
  x=calculate([bar(t) for t in range(660,691)],start=660);self.assertEqual(x['status'],'COMPLETE')
 def test_missing_endpoint_unavailable(self):
  x=calculate([bar(t) for t in range(660,690)],start=660);self.assertEqual(x['status'],'UNAVAILABLE');self.assertIsNone(x['returnNet'])
 def test_missing_path(self):
  x=calculate([]);self.assertFalse(x['pathAvailable']);self.assertIsNone(x['MFE']);self.assertIsNone(x['observedMFE'])
 def test_missing_required_slot(self):
  x=calculate([bar(t) for t in range(570,600) if not 580<=t<585]);self.assertEqual(x['status'],'UNAVAILABLE')
 def test_no_minute_interpolation(self):
  x=calculate([bar(t) for t in range(570,600,5)]);self.assertEqual(x['status'],'COMPLETE');self.assertEqual(x['observedRows'],6)
 def test_exact_close_with_preclose_gap(self):
  x=calculate([bar(t) for t in range(900,925)]+[bar(930)],start=900,h=30);self.assertEqual(x['status'],'COMPLETE')
 def test_old_session_close(self):
  day='2024-10-02';x=calculate([bar(t,day=day) for t in range(870,901)],start=870,day=day);self.assertEqual(x['status'],'COMPLETE')
 def test_cross_session_reject(self):
  with self.assertRaises(AssertionError):calculate([bar(570,day='2025-06-03')])
 def test_no_future_beyond_horizon(self):
  raw=[bar(t) for t in range(570,600)];a=calculate(raw);b=calculate(raw+[bar(600,100,999,1,100),bar(630,100,9999,1,100)]);self.assertEqual(a,b)
 def test_no_mutation_to_decision_inputs(self):
  raw=[bar(t) for t in range(570,600)];saved=copy.deepcopy(raw);calculate(raw);self.assertEqual(raw,saved)
 def test_distribution_empty_and_quantiles(self):
  self.assertIsNone(e.distribution([])['median']);x=e.distribution([1,2,3,4,5]);self.assertEqual(x['count'],5);self.assertEqual(x['median'],3);self.assertEqual(x['p25'],2)
if __name__=='__main__':unittest.main()
