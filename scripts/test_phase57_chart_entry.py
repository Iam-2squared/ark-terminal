import copy,tempfile,unittest
from pathlib import Path
import numpy as np
from scripts import phase57_chart_entry as e

def bar(t,price=100):return {'Date':'2025-06-02','Time':'%02d:%02d'%divmod(t,60),'Code':'12340','O':price,'H':price+1,'L':price-1,'C':price,'Vo':10,'Va':1000}
def row(day='2025-06-02',t=570,oid=None):
 oid=oid or day+'|12340'
 return {'id':oid+'|'+str(t),'opportunity':oid,'session':day,'symbol':'12340','minute':t,'decisionTime':e.stamp(day,t),'newEligibleTick':True,'quoteAvailable':True,'SELECTOR':{'timeFraction':.1,'elapsed':t-570},'WHO':[],'RECENT':{'features':{}},'NOW':{'features':{}},'SEQ':{'features':{}}}
def lab(ret=1):return {'return30':ret,'mae30':-1,'mfeEnd':3,'maeEnd':-2,'timeToRecovery':3,'timeToUpside1':5}
def opportunity(day='2025-06-02',start=570):return {'id':day+'|12340','session':day,'symbol':'12340','origin':{'decisionTimestamp':e.stamp(day,start),'decisionPrice':100},'grid':e.clock(day,start),'currentMinute':None,'selectorOutcome':{'mfeEnd':5,'maeEnd':-2,'order':'LOW_THEN_HIGH'}}
class ChartEntryTests(unittest.TestCase):
 def test_clock_lunch_and_deadline(self):
  self.assertEqual(e.clock('2025-06-02',680),[680,685]);self.assertEqual(e.clock('2025-06-02',750),[755,760,765,770,775,780]);self.assertEqual(e.clock('2024-10-02',900),[])
 def test_prefix_excludes_future_and_auction(self):
  raw=[bar(569),bar(570),bar(690),bar(750)];self.assertEqual([e.v.minute_time(x) for x in e.causal_prefix('2025-06-02',570,raw)],[569])
 def test_fixed_sequence_hole_is_null(self):
  raw=[bar(t) for t in range(540,570) if t!=563];s=e.sequence('2025-06-02',570,raw,[],100,{'minute':570,'price':100});self.assertIsNone(s['features']['lag01_C']);self.assertIsNone(s['features']['w15_return']);self.assertIsNotNone(s['features']['lag00_C'])
 def test_sequence_reject_future(self):
  with self.assertRaises(AssertionError):e.sequence('2025-06-02',570,[bar(570)],[],100,{'minute':570,'price':100})
 def test_no_fill_at_missing_open(self):
  x=e.outcome('2025-06-02',570,[bar(569),bar(571)],None,100);self.assertIsNone(x['price'])
 def test_fill_is_next_open_with_cost(self):
  raw=[bar(t) for t in range(570,601)];x=e.outcome('2025-06-02',570,raw,None,100);self.assertAlmostEqual(x['price'],100.05);self.assertLess(x['labels']['return30'],0)
 def test_unavailable_who_never_drops(self):
  o=opportunity();rows=[row(t=t) for t in o['grid']];labels={x['id']:{'price':100,'labels':lab()} for x in rows};scores={x['id']:-1 for x in rows};tr=e.policy([o],rows,labels,scores,'E4')[0];self.assertEqual(tr['delay'],30);self.assertEqual(tr['status'],'BUY')
 def test_buy_no_reentry(self):
  o=opportunity();rows=[row(t=t) for t in o['grid']];labels={x['id']:{'price':100,'labels':lab()} for x in rows};tr=e.policy([o],rows,labels,{},'E0')[0];self.assertEqual(len(tr['attempts']),1)
 def test_unfilled_buy_retries_only_later_causal_tick(self):
  o=opportunity();rows=[row(t=t) for t in o['grid']];labels={x['id']:{'price':100,'labels':lab()} for x in rows};labels[rows[0]['id']]['price']=None;tr=e.policy([o],rows,labels,{},'E0')[0];self.assertEqual(tr['delay'],5)
 def test_stale_reference_does_not_buy(self):
  o=opportunity();rows=[row(t=t) for t in o['grid']]
  for x in rows:x['quoteAvailable']=False
  labels={x['id']:{'price':100,'labels':lab()} for x in rows};self.assertIsNone(e.policy([o],rows,labels,{},'E0')[0]['entryId'])
 def test_target_excluded_from_vector(self):
  x=row();a=e.vector(x,[]);x['futureReturn']=100;x['labels']=lab(900);self.assertEqual(a,e.vector(x,[]))
 def test_advantage_label(self):
  a=row();b=row(t=575);ls={a['id']:{'labels':lab(1)},b['id']:{'labels':lab(2)}};y=e.target_rows([a,b],ls,[opportunity()]);self.assertAlmostEqual(y[a['id']],-.99)
 def test_fit_scaler_query_invariant(self):
  tr=[{'x':i,'m':None} for i in range(30)];_,a=e.fit_model(tr,[{'x':1}],np.arange(30),'RIDGE');_,b=e.fit_model(tr,[{'x':1e9}],np.arange(30),'RIDGE');self.assertEqual(a,b)
 def test_nonlinear_deterministic(self):
  tr=[{'x':i} for i in range(100)];a,m=e.fit_model(tr,[{'x':1}],np.arange(100),'TREE');b,n=e.fit_model(tr,[{'x':1}],np.arange(100),'TREE');self.assertEqual(m,n);np.testing.assert_array_equal(a,b)
 def test_analog_no_same_session_or_future(self):
  rows=[];opps=[];labels={}
  for day in ['2025-06-02','2025-06-03']:
   for i in range(6):
    oid=day+'|'+str(i);x=row(day,oid=oid);rows.append(x);o=opportunity(day);o['id']=oid;opps.append(o);labels[x['id']]={'labels':lab(i)}
  e.add_analog(rows,labels,opps);self.assertTrue(all(x['ANALOG']['count']==0 for x in rows[:6]));self.assertTrue(all(x['ANALOG']['count']==6 for x in rows[6:]));self.assertTrue(all('2025-06-02' in n for x in rows[6:] for n in x['ANALOG']['neighbors']))
 def test_analog_future_suffix_invariance(self):
  rows=[row('2025-06-02'),row('2025-06-03')];opps=[opportunity('2025-06-02'),opportunity('2025-06-03')];labels={x['id']:{'labels':lab()} for x in rows};a=copy.deepcopy(rows);e.add_analog(a,labels,opps);labels[rows[1]['id']]['labels']=lab(1000);e.add_analog(rows,labels,opps);self.assertEqual(a[0]['ANALOG'],rows[0]['ANALOG'])
 def test_missing_outcome_is_not_preserved_winner(self):
  o=opportunity();tr=[{'opportunity':o['id'],'session':o['session'],'symbol':'12340','entryId':o['id']+'|570','delay':0}];ls={tr[0]['entryId']:{'labels':None,'improvementPct':0}};m=e.metrics([o],tr,ls);self.assertEqual(m['capture']['5']['pct'],0);self.assertEqual(m['capture']['5']['unknownEntered'],1)
 def test_fixed_population_no_entry_penalty(self):
  o=opportunity();tr=[{'opportunity':o['id'],'session':o['session'],'symbol':'12340','entryId':None,'delay':None}];m=e.metrics([o],tr,{});self.assertEqual(m['noEntryPct'],100);self.assertEqual(m['populationObjective'],-1)
if __name__=='__main__':unittest.main()
