import copy,inspect,unittest
import numpy as np
from scripts import phase57_research_dictionary_v0 as v
from scripts import phase57_expansion_assess as a
from scripts import phase57_chart_reader_research as c
class ResearchTests(unittest.TestCase):
 def data(self):
  day='2024-10-01';rows=[]
  for t in range(540,610):
   price=100+(t-540)*.02;rows.append({'Date':day,'Time':f'{t//60:02}:{t%60:02}','Code':'12340','O':price,'H':price+.1,'L':price-.1,'C':price+.01,'Vo':10,'Va':(price+.01)*10})
  previous={'Date':'2024-09-30','O':100,'H':101,'L':99,'C':100,'Vo':100,'Va':10000}
  history=[{'session':f'2024-09-{d:02}','tr':.02,'barValues':{str(t):5000 for t in range(545,615,5)}} for d in range(20,30)]
  return day,rows,previous,history
 def test_exact_assessor_except_split_indices(self):
  old=inspect.getsource(v.assess).splitlines();new=inspect.getsource(a.assess).splitlines();self.assertEqual(old[:1]+old[2:],new[:1]+new[2:])
 def test_drift_minimum_and_reproducibility(self):
  from scripts.phase57_expansion_measure import drift_summary
  z=np.arange(80,dtype=float)[:,None]
  x=v.clean(drift_summary(z,20));self.assertEqual(x,v.clean(drift_summary(z,20)));self.assertTrue(x['driftFlag'][0])
  z[:65]=np.nan;self.assertIsNone(v.clean(drift_summary(z,20))['driftFlag'][0])
 def test_future_poison(self):
  day,rows,prev,hist=self.data();expected=c.context(day,580,rows,prev,hist);poison=copy.deepcopy(rows)
  for r in poison:
   if v.minute_time(r)>=580:r.update(O=-1e99,H=1e100,L=-1e100,C=None,Va=None)
  self.assertEqual(expected,c.context(day,580,poison,prev,hist))
 def test_truncation(self):
  day,rows,prev,hist=self.data()
  for t in [560,570,590,610]:self.assertEqual(c.context(day,t,rows,prev,hist),c.context(day,t,[r for r in rows if v.minute_time(r)<t],prev,hist))
 def test_future_dictionary_rejected(self):
  day,rows,prev,hist=self.data()
  with self.assertRaisesRegex(ValueError,'FUTURE_DICTIONARY'):c.context(day,580,rows,prev,hist,{'computed_through':day})
 def test_future_history_rejected(self):
  day,rows,prev,hist=self.data();hist.append({'session':day,'tr':1})
  with self.assertRaises(ValueError):c.context(day,580,rows,prev,hist)
 def test_or_unavailable_before_0930(self):
  day,rows,prev,hist=self.data();self.assertNotIn('distance_ORH_s',c.context(day,565,rows,prev,hist)['features']);self.assertIn('distance_ORH_s',c.context(day,570,rows,prev,hist)['features'])
 def test_missing_minute_not_filled(self):
  day,rows,prev,hist=self.data();rows=[r for r in rows if v.minute_time(r)!=579];result=c.context(day,580,rows,prev,hist)
  self.assertEqual(result['lastCompletedBar'],575);self.assertEqual(result['missingReason'],'UNKNOWN')
 def test_no_identity_feature_or_production(self):
  day,rows,prev,hist=self.data();r=c.context(day,580,rows,prev,hist)
  self.assertFalse({'Code','symbol','securityId','price','entryPnl','winner'}&set(r['features']));self.assertFalse(r['productionAllowed'])
  with self.assertRaises(ValueError):v.production_load(r)
 def test_scale_price_invariance(self):
  day,rows,prev,hist=self.data();r=c.context(day,580,rows,prev,hist)
  for b in rows+[prev]:
   for k in ['O','H','L','C','Va']:b[k]*=10
  x=c.context(day,580,rows,prev,hist)
  for k in r['features']:
   if r['features'][k] is not None and k!='rvol_value':self.assertAlmostEqual(r['features'][k],x['features'][k],places=9)
if __name__=='__main__':unittest.main()
