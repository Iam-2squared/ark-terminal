import copy,unittest
from scripts import phase57_opportunity_quality as q

def bar(slot,h=1,l=-1,c=0,missing=False):
 return {'slot':slot,'minutes':slot*5,'missing':missing,'o':0,'h':h,'l':l,'c':c,'observedMinutes':5}
def row(w):return {'windows':{'30':w}}
class QualityTests(unittest.TestCase):
 def test_complete_horizon(self):
  w=q.window([bar(1),bar(2,c=2)],2);self.assertTrue(w['complete']);self.assertEqual(w['returnPct'],2)
 def test_missing_not_zero_or_negative_label(self):
  w=q.window([bar(1,missing=True)],1);self.assertIsNone(w['returnPct']);self.assertIsNone(w['reach']['3'])
 def test_observed_hit_survives_missing(self):
  w=q.window([bar(1,missing=True),bar(2,h=5)],2);self.assertTrue(w['reach']['5']);self.assertFalse(w['complete'])
 def test_first_hit_uncertain_after_missing(self):
  w=q.window([bar(1,missing=True),bar(2,h=5)],2);self.assertFalse(w['timeToHit']['5']['firstHitIdentified']);self.assertEqual(w['timeToHit']['5']['firstHitBounds'],[0,10])
 def test_interval_not_intrabar_order(self):
  w=q.window([bar(1,h=6,l=-8)],1);self.assertEqual(w['timeToHit']['5']['observedHitInterval'],[0,5]);self.assertEqual(w['mae'],-8)
 def test_boundary_not_complete(self):self.assertFalse(q.window([bar(1)],6,'SEGMENT_BOUNDARY')['complete'])
 def test_unknown_reference(self):self.assertEqual(q.window([],6,'UNKNOWN_REFERENCE_OPEN')['observedBars'],0)
 def test_denominators(self):
  x=q.aggregate([row(q.window([bar(1,h=4)],1)),row(q.window([],1,'MISSING'))],'30');self.assertEqual(x['completeN'],1);self.assertEqual(x['reach']['3']['allEmittedLowerBound']['rate'],.5);self.assertEqual(x['reach']['3']['allEmittedUpperBound']['rate'],1)
 def test_breadth_bounds(self):
  x=q.breadth({'t':[row(q.window([bar(1,h=4)],1)),row(q.window([],1,'MISSING'))]},'30')['3'];self.assertEqual(x['knownWinnerCount'],1);self.assertEqual(x['possibleWinnerCount'],2);self.assertEqual(x['outcomeIdentifiedTimestamps'],0)
 def test_negative_only_when_complete(self):self.assertIs(q.window([bar(1)],1)['reach']['5'],False)
 def test_inputs_not_mutated(self):
  bars=[bar(1)];before=copy.deepcopy(bars);q.window(bars,1);self.assertEqual(before,bars)
 def test_saved_population_and_pin_audit(self):
  rows,s=q.build();self.assertEqual(len(rows),3508);self.assertEqual(s['audit']['oldStrict30Parity'],1872);self.assertEqual(s['population']['timestamps'],1181);self.assertTrue(all(v is False for v in s['safety'].values()))
if __name__=='__main__':unittest.main()
