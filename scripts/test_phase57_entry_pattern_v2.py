import copy,unittest
import numpy as np
from scripts import phase57_entry_pattern_v2 as e
from scripts import phase57_entry_pattern_learn as l
DAY='2025-06-02'
def bar(t,o=100,h=102,lo=99,c=101):return np.array([t,o,h,lo,c,10,1000],float)
def origin():return {'decisionPrice':100,'savedV1Score':.1,'newEligibleRank':1}
def row(t=570,quote=True):return {'id':'a|'+str(t),'opportunity':'a','minute':t,'delay':t-570,'eligible1':True,'eligible5':t%5==0,'quoteAvailable':quote,'session':DAY,'symbol':'12340'}
def opp():return {'id':'a','session':DAY,'symbol':'12340','v2grid':list(range(570,601)),'origin':{'decisionTimestamp':DAY+'T09:30:00+09:00'}}
def lab(price=100,ret=1):return {'price':price,'labels':{'30':{'returnNet':ret,'MFE':3,'MAE':-1,'MaxDD':-2,'status':'COMPLETE'}}}
class Tests(unittest.TestCase):
 def test_actual_protocol_inherits_exact_date_split(self):
  p=e.read(e.BASE/'protocol.json');prior=e.read(e.old.BASE/'protocol.json');e.validate_splits(p,prior)
 def test_selection_rule_cannot_replace_dates(self):
  p=e.read(e.BASE/'protocol.json');prior=copy.deepcopy(p);p['selection']='selection rule prose'
  with self.assertRaisesRegex(AssertionError,'SPLIT_DATE_LIST'):e.validate_splits(p,prior)
 def test_split_overlap_rejected(self):
  p=e.read(e.BASE/'protocol.json');prior=copy.deepcopy(p);p['selection'][0]=p['fit'][0]
  with self.assertRaisesRegex(AssertionError,'INHERITED_SPLIT_CHANGED'):e.validate_splits(p,prior)
 def test_lunch_carry_identity(self):
  self.assertEqual(e.clock(DAY,690),list(range(751,781)));self.assertEqual(e.clock(DAY,690,5),[755,760,765,770,775,780])
 def test_no_session_cross(self):self.assertEqual(e.clock(DAY,920),list(range(920,925)));self.assertEqual(e.clock('2024-10-02',900),[])
 def test_clock_active_budget(self):
  for start in [570,660,680,690,750,900]:
   for t in e.clock(DAY,start):self.assertLessEqual(e.elapsed(DAY,start,t),30);self.assertNotIn(t,[690,750,925])
 def test_prefix_excludes_future(self):
  a=np.array([bar(569),bar(570)]);self.assertEqual(e.closed(a,570).shape[0],1)
 def test_feature_future_reject(self):
  with self.assertRaises(AssertionError):e.features(DAY,570,570,origin(),np.array([bar(570)]),np.empty((0,7)),None,{})
 def test_future_suffix_invariance(self):
  a=np.array([bar(t) for t in range(540,600)]);b=a.copy();b[b[:,0]>=570,2]=999
  x=e.features(DAY,570,570,origin(),e.closed(a,570),np.empty((0,7)),None,{})
  y=e.features(DAY,570,570,origin(),e.closed(b,570),np.empty((0,7)),None,{})
  self.assertEqual(x,y)
 def test_partial_observed_aggregation_no_fill(self):
  b=e.five_observed(np.array([bar(540),bar(544)]),545);self.assertEqual(len(b),1);self.assertEqual(b[0,7],2);self.assertEqual(b[0,5],20)
 def test_no_empty_synthetic_bar(self):self.assertEqual(len(e.five_observed(np.empty((0,7)),570)),0)
 def test_no_previous_candidate_drop(self):
  z,q=e.features(DAY,570,570,origin(),np.array([bar(569)]),np.empty((0,7)),None,{})
  self.assertTrue(q);self.assertEqual(z['AVAIL/prevRows'],0);self.assertIsNone(z['SEQ_PREV/0'])
 def test_no_lunch_stale_forward_fill(self):
  _,q=e.features(DAY,751,690,origin(),np.array([bar(689)]),np.empty((0,7)),None,{})
  self.assertFalse(q)
 def test_missing_micro_is_null(self):
  z,_=e.features(DAY,570,570,origin(),np.array([bar(568)]),np.empty((0,7)),None,{})
  self.assertIsNone(z['SEQ_MICRO/0/C']);self.assertIsNotNone(z['SEQ_MICRO/1/C'])
 def test_label_active_lunch_horizon(self):
  a=np.array([bar(t) for t in list(range(680,690))+list(range(750,780))]);x=e.label(DAY,680,a,None,100)
  self.assertEqual(x['labels']['30']['status'],'COMPLETE');self.assertEqual(x['labels']['60']['status'],'UNAVAILABLE')
 def test_label_end_censored(self):
  x=e.label(DAY,910,np.array([bar(t) for t in range(910,925)]),None,100);self.assertEqual(x['labels']['30']['status'],'CENSORED');self.assertIsNone(x['labels']['mae30'])
 def test_no_price_no_fill(self):self.assertIsNone(e.label(DAY,570,np.array([bar(571)]),None,100)['price'])
 def test_wait_vs_fill_reason(self):
  rs=[row(570),row(571)];labs={rs[0]['id']:lab(None),rs[1]['id']:lab()};t=l.replay([opp()],rs,labs,None,'BASE')[0]
  self.assertEqual(t['entryId'],'a|571');self.assertEqual(t['attempts'][0]['state'],'BUY_ATTEMPT_UNFILLED')
 def test_negative_quality_expires(self):
  rs=[row(570)];labs={rs[0]['id']:lab()};p=np.array([[-1,0,-1,-1,0.]])
  t=l.replay([opp()],rs,labs,p,'STOP')[0];self.assertIsNone(t['entryId']);self.assertEqual(t['attempts'][0]['state'],'MODEL_WAIT');self.assertEqual(t['attempts'][-1]['state'],'EXPIRED')
 def test_continuation_prevents_buy(self):
  rs=[row(570),row(571)];labs={x['id']:lab() for x in rs};p=np.array([[1,0,0,0,2],[2,0,0,0,0.]])
  self.assertEqual(l.replay([opp()],rs,labs,p,'STOP')[0]['entryId'],'a|571')
 def test_no_reentry(self):
  rs=[row(570),row(571)];labs={x['id']:lab() for x in rs};t=l.replay([opp()],rs,labs,None,'BASE')[0];self.assertEqual(len(t['attempts']),1)
 def test_target_unknown_future_not_zero(self):
  rs=[row(570),row(571)];labs={rs[0]['id']:lab(),rs[1]['id']:lab()};labs[rs[1]['id']]['labels']['30']['returnNet']=None;labs[rs[1]['id']]['labels']['30']['status']='UNAVAILABLE'
  self.assertTrue(np.isnan(l.make_targets(rs,labs)[0,4]))
 def test_expire_terminal_value_zero(self):
  rs=[row(570)];self.assertEqual(l.make_targets(rs,{'a|570':lab()})[0,4],0)
 def test_fit_does_not_use_evaluation_targets(self):
  x=np.arange(360,dtype=float).reshape(120,3);y=np.ones((120,5));fit=np.arange(120)<110
  a,m=l.fit_predict(x,y,fit,[0,1,2],'RIDGE');y[110:]=999;b,n=l.fit_predict(x,y,fit,[0,1,2],'RIDGE');np.testing.assert_array_equal(a,b);self.assertEqual(m,n)
 def test_saved_model_roundtrip(self):
  x=np.arange(660,dtype=float).reshape(220,3);y=np.tile(np.sin(np.arange(220)/10)[:,None],(1,5));fit=np.ones(220,bool)
  for family in ['RIDGE','TREE']:
   pred,model=l.fit_predict(x,y,fit,[0,1,2],family);np.testing.assert_allclose(l.predict_saved(x[:12],model),pred[:12],rtol=1e-10,atol=1e-10)
 def test_efficiency_includes_first_open_close_leg(self):
  self.assertEqual(e.describe(np.array([bar(569)]),100,1)['trendEfficiency'],1)
  z=e.describe(np.array([bar(569),bar(570,c=100)]),100,2);self.assertEqual(z['trendEfficiency'],0)
 def test_raw_inputs_not_mutated(self):
  a=np.array([bar(569)]);cp=a.copy();e.features(DAY,570,570,origin(),a,np.empty((0,7)),None,{});np.testing.assert_array_equal(cp,a)
if __name__=='__main__':unittest.main()
