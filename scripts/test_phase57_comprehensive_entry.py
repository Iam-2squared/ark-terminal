import copy,tempfile,unittest
from pathlib import Path
import numpy as np
from scripts import phase57_comprehensive_entry as m
class Fake:
 def __init__(self,buy,wait):self.values=[buy,wait]
 def predict(self,fs):return np.array([self.values]*len(fs))
class EntryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p,cls.ops,cls.paths,cls.sel,cls.legacy=m.sources()
 def sample(self):
  x=next(x for x in self.ops if x['op']['referenceStatus']=='REFERENCE_OPEN' and x['op']['eventType']==m.q.INITIAL);p=copy.deepcopy(self.paths[x['op']['anchorId']]);return x,p,self.sel[x['op']['anchorId']]
 def test_source_identity(self):
  self.assertEqual(len(self.ops),3508);self.assertTrue(all(v is False for v in self.p['safety'].values()))
 def test_disjoint_split(self):
  s=self.p['split'];self.assertEqual([len(v) for v in s.values()], [19,38,19]) # canonical sorted keys
  self.assertEqual(len(set(sum(s.values(),[]))),76)
 def test_no_future_features(self):
  x,p,s=self.sample();t=m.c.minute(x['op']['opportunityTimestamp']);a=m.features(x,p,s,{},t)
  for b in p['future']:
   if not b['missing']:b.update(o=400,h=500,l=300,c=450)
  self.assertEqual(a,m.features(x,p,s,{},t))
 def test_only_completed_prefix(self):
  x,p,s=self.sample();t=m.c.minute(x['op']['opportunityTimestamp'])+5;a=m.features(x,p,s,{},t)
  for b in p['future'][1:]:
   if not b['missing']:b.update(o=400,h=500,l=300,c=450)
  self.assertEqual(a,m.features(x,p,s,{},t));self.assertIsNotNone(a['lastBody'])
 def test_missing_prefix_expires(self):
  x,p,s=self.sample();p['future'][0]['missing']=True;r=m.decide(x,p,s,{},Fake(-1,1));self.assertEqual(r['status'],'EXPIRE_MISSING_PREFIX')
 def test_reference_fail_closed(self):
  x,p,s=self.sample();x=copy.deepcopy(x);x['op']['referenceStatus']='UNKNOWN_REFERENCE_OPEN';self.assertEqual(m.decide(x,p,s,{},Fake(1,0))['status'],'EXPIRE_REFERENCE')
 def test_wait_cap(self):
  x,p,s=self.sample();r=m.decide(x,p,s,{},Fake(-1,1));self.assertNotEqual(r['status'],'COUNTERFACTUAL_ENTER');self.assertLessEqual(len(r['transitions']),7)
 def test_immediate_buy_unique(self):
  x,p,s=self.sample();r=m.decide(x,p,s,{},Fake(1,0));self.assertEqual(r['delay'],0);self.assertEqual(len(r['transitions']),1)
 def test_missing_open_no_substitution(self):
  x,p,s=self.sample();p['future'][0]['missing']=True;r=m.decide(x,p,s,{},Fake(1,0));self.assertEqual(r['status'],'EXPIRE_MISSING_OPEN')
 def test_future_decision_invariance(self):
  x,p,s=self.sample();a=m.decide(x,p,s,{},Fake(1,0))
  for b in p['future'][1:]:
   if not b['missing']:b.update(o=100,h=200,l=50,c=150)
  self.assertEqual(a,m.decide(x,p,s,{},Fake(1,0)))
 def test_no_symbol_or_label_feature(self):
  self.assertFalse(set(m.FEATURES)&{'symbol','session','futureMFE','futureMAE','referencePrice','terminalOutcome'})
 def test_deterministic_fit(self):
  f=[dict.fromkeys(m.FEATURES,float(i)) for i in range(220)];y=[[i/100,i/200] for i in range(220)]
  for kind in ('LINEAR','TREE'):
   a=m.Model(kind,m.FEATURES).fit(f,y,[1]*220);b=m.Model(kind,m.FEATURES).fit(f,y,[1]*220);self.assertEqual(a.dump(),b.dump())
 def test_candidate_a_later_bar(self):
  bars=[{'slot':1,'h':4,'c':0,'o':0},{'slot':2,'h':2,'c':0,'o':0},{'slot':3,'h':2,'c':0,'o':.5}];f={'exitBar':3,'grossPct':0,'netPct':-.05};r=m.ca.policy(bars,f);self.assertEqual(r['signalBar'],2);self.assertEqual(r['exitBar'],3)
 def test_output_immutable(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.json';m.write(p,{'x':1})
   with self.assertRaises(FileExistsError):m.write(p,{'x':2})
if __name__=='__main__':unittest.main()
