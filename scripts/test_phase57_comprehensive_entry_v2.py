import copy,unittest
from unittest.mock import patch
import numpy as np
from scripts import phase57_comprehensive_entry_v2 as v
class Fake:
 def __init__(self,wait=-1,skip=-1,guard=None):self.values=(wait,skip,guard)
 def predict(self,f):return self.values
class V2Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p,cls.ops,cls.paths,cls.selectors,cls.legacy=v.sources()
 def sample(self):
  x=next(x for x in self.ops if x['op']['referenceStatus']=='REFERENCE_OPEN' and x['op']['eventType']==v.q.INITIAL);p=copy.deepcopy(self.paths[x['op']['anchorId']]);s=self.selectors[x['op']['anchorId']];return x,p,s
 def test_split_same(self):self.assertEqual(self.p['split'],v.m.read(v.m.BASE/'protocol.json')['split'])
 def test_source_safety(self):self.assertEqual(len(self.ops),3508);self.assertEqual(len(v.m.FEATURES),43);self.assertTrue(all(x is False for x in self.p['safety'].values()))
 def test_no_oracle_target(self):
  now={'price':100,'commonComplete':True,'common':{'return':1,'mae':-1,'mfe':5},'fastWinner':True};nxt={'price':101,'commonComplete':True,'common':{'return':0,'mae':-1,'mfe':2},'fastWinner':False};a=v.labels(now,nxt)
  self.assertAlmostEqual(a['waitAdvantage'],-7.05);self.assertAlmostEqual(a['lostThresholdPenalty'],5);self.assertEqual(a['fastChasePenalty'],1)
 def test_missing_label_not_zero(self):
  now={'price':100,'commonComplete':True,'common':{'return':0,'mae':0,'mfe':0},'fastWinner':False};self.assertIsNone(v.labels(now,None)['waitAdvantage'])
 def test_skip_penalizes_winners(self):
  now={'price':100,'commonComplete':True,'common':{'return':0,'mae':0,'mfe':5},'fastWinner':True};self.assertAlmostEqual(v.labels(now,None)['skipAdvantage'],-6.7)
 def test_buy_tie_priority(self):self.assertEqual(v.action(0,0,None,True),'BUY_NOW')
 def test_wait_one_step(self):
  class Step:
   def predict(self,f):return (1 if f['elapsed']==0 else -1,-1,None)
  x,p,s=self.sample();r=v.decide(x,p,s,{},Step());self.assertEqual(r['delay'],5);self.assertEqual([t['action'] for t in r['transitions']],['WAIT_ONE_STEP','BUY_NOW'])
 def test_cap_masks_wait(self):self.assertEqual(v.action(100,-1,None,False),'BUY_NOW')
 def test_skip_terminal(self):
  x,p,s=self.sample();r=v.decide(x,p,s,{},Fake(1,2));self.assertEqual(r['status'],'MODEL_SKIP');self.assertEqual(len(r['transitions']),1)
 def test_guard_is_predicted_probability(self):self.assertEqual(v.action(4,5,.5,True),'BUY_NOW');self.assertEqual(v.action(4,5,.49,True),'SKIP_OR_EXPIRE')
 def test_high_low_not_execution_input(self):
  x,p,s=self.sample();t=v.c.minute(x['op']['opportunityTimestamp']);a=v.open_reference(p,t);p['future'][0].update(h=None,l=None,c=None);self.assertEqual(a,v.open_reference(p,t));self.assertEqual(v.decide(x,p,s,{},Fake())['status'],'COUNTERFACTUAL_ENTER')
 def test_future_mutation_does_not_change_signal(self):
  x,p,s=self.sample();a=v.decide(x,p,s,{},Fake())
  for b in p['future']:
   if not b.get('missing'):b.update(h=999,l=-99,c=300)
  self.assertEqual(a,v.decide(x,p,s,{},Fake()))
 def test_prefix_gap_fail_closed(self):
  x,p,s=self.sample();t=v.c.minute(x['op']['opportunityTimestamp'])+10;p['future'].pop(0);self.assertIsNone(v.state(x,p,s,{},t))
 def test_missing_prefix_fail_closed(self):
  x,p,s=self.sample();p['future'][0]['missing']=True;r=v.decide(x,p,s,{},Fake(2,-1));self.assertEqual(r['status'],'EXPIRE_MISSING_PREFIX')
 def test_missing_open_fail_closed(self):
  x,p,s=self.sample();p['future'][0]['o']=None;self.assertEqual(v.decide(x,p,s,{},Fake())['status'],'EXPIRE_MISSING_OPEN')
 def test_no_reference_resurrection(self):
  x,p,s=self.sample();x=copy.deepcopy(x);x['op']['referenceStatus']='UNKNOWN_REFERENCE_OPEN';r=v.decide(x,p,s,{},Fake());self.assertEqual(r['status'],'EXPIRE_REFERENCE');self.assertEqual(r['transitions'],[])
 def test_boundary_masks_wait(self):
  x,p,s=self.sample();t=v.c.minute(x['op']['opportunityTimestamp']);p['sessionEndMinute']=t+5
  with patch.object(v.c,'segment_end',return_value=t+5):
   r=v.decide(x,p,s,{},Fake(2,-1));self.assertEqual(r['delay'],0);self.assertFalse(r['transitions'][0]['waitAllowed'])
 def test_no_exit_in_entry_evaluator(self):
  x,p,s=self.sample()
  with patch.object(v.m.ca,'policy',side_effect=AssertionError('EXIT_FORBIDDEN')):v.evaluate(x,p,0)
 def test_single_head_model_shapes_deterministic(self):
  f=[dict.fromkeys(v.m.FEATURES,float(i)) for i in range(220)];y=[[i/100] for i in range(220)]
  for kind in ('LINEAR','TREE'):
   h=v.m.Model(kind,v.m.FEATURES).fit(f,y,[1]*220);h2=v.m.Model(kind,v.m.FEATURES).fit(f,y,[1]*220);self.assertEqual(h.dump(),h2.dump());a=v.Sequential('x',h,h).predict(f[0]);self.assertEqual(len(a),3)
 def test_winner_missing_entry_fails_gate(self):
  x,p,s=self.sample();r=v.measure([x],{x['op']['anchorId']:p},{x['op']['anchorId']:s},{},Fake(1,2));z=v.summarize(r);self.assertFalse(all(v.entry_gates(z).values()))
if __name__=='__main__':unittest.main()
