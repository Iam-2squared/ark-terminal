"""Meaningful artificial AD01 contracts only: no real source/results are opened."""
from io_utils import *
from admission_adapter import day_replay,admission_guard,_positive_price
from baseline_adapter import day_replay as baseline
from slot_policy import gate
from allocation import allocation,band,BUY,CAP
from staircase import band as rank_band,candidate_order
from pathlib import Path
import math,unittest,copy,types,ast

DAY='2099-01-05'
TABLE={'minute_counts':{str(t):[0,0,0] for t in range(540,932)},'training_session_N':20,'B_median':1.1,'B_p75':1.2,'minute_bucket':{str(t):'SYNTHETIC' for t in range(540,932)}}
TABLES={'1':TABLE}
def c(key,t=600,score=2.0,price='1000',day=DAY,symbol=None):
 return {'entry_id':key,'session':day,'symbol':symbol or key,'entry_minute':t,'entry_timestamp':stamp(day,t),'capital_score':score,'ML':score,'capacity_band':rank_band(score),'rank':rank_band(score),'admission':score>=1,'m2':.8,'m3':.6,'m5':.3,'raw_reference':price,'block':1}
def market(t,price='1000',day=DAY):
 return {'session':day,'minute':t,'O':price,'H':price,'L':price,'C':price,'Vo':'100','Va':'100000','lineage':{'fixture':'ARTIFICIAL_ONLY'}}
def b(row,price='1000'):
 return {'entry_id':row['entry_id'],'session':row['session'],'symbol':row['symbol'],'capture_complete':True,'entry_actual_source':market(row['entry_minute'],day=row['session']),'limit_up_authority':None,'market':[market(t,price,row['session']) for t in [row['entry_minute'],610,700,751,820,900,920,930]],'frozen_exit':{'exit_intent':{'minute':900},'sell_status':'FILLED','sell_source_assumed_available_at':stamp(row['session'],901),'sell_minute':900,'sell_source':'NEXT_ELIGIBLE_REGULAR_RAW_OPEN','sell_price_decimal':'999.5000'}}
def plan(row,sd=False,intent=610,release=612,price='999.5000',blocked=None):
 source={'kind':'SHARP_DROP_FIRST_OBSERVED_EXIT_V0' if sd else 'FROZEN_EXIT_V3','source_minute':release-1,'release_minute':release,'price':price,'lineage':{'fixture':'ARTIFICIAL_ONLY'}}
 if blocked:source['blocked']=blocked
 return {'action':'SD_FIRST' if sd else 'DELEGATE_CONTROL','intent_minute':intent,'source':source}
def run(rows,policy='H2',plans=None,books=None,day=DAY,cash='1000000',**kw):
 return day_replay(3,day,rows,books if books is not None else {r['entry_id']:b(r) for r in rows},D(cash),tables=TABLES,exit_plans=plans if plans is not None else {r['entry_id']:plan(r,intent=r['entry_minute']+10,release=r['entry_minute']+12) for r in rows},policy=policy,**kw)
def decisions(payload):return {r['entry_id']:r for r in payload[1]}
def serialized(payload):return json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)
# Isolate the unchanged, pure State-route function without loading real data.
_tree=ast.parse((ROOT.parent.parent/'evidence/previous_impl/exit_adapter.py').read_text())
_route=next(n for n in _tree.body if isinstance(n,ast.FunctionDef) and n.name=='route')
_module=ast.Module(body=[_route],type_ignores=[]);_ns={};exec(compile(_module,'immutable_pure_exit_route','exec'),_ns)
route=_ns['route']
def state(t,primary='SHARP_DROP',usable=True,gap=False):return {'checkpoint_minute':t,'Primary':primary,'usable':usable,'evidence_gap':gap}

class AdmissionContracts(unittest.TestCase):
 def test_01_gate_guard_occupancy_rank_cross_product(self):
  for occ in (0,1,2,3):
   for rank,score in [('S',2),('A',1.5),('B',1.4),('C',.99)]:
    row=c(rank,score=score)
    # C fails inherited eligibility and never reaches native gate's ML>=1 contract.
    native=score>=1 and gate(row,occ,600,TABLE)[0]
    self.assertEqual(native,rank!='C' and occ<3)
    for policy in ('E0','H1','H2'):
     for seen in (False,True):
      final=native and admission_guard(policy,rank,seen)
      self.assertEqual(final,native and (rank in ('S','A') or policy=='E0' or policy=='H2' and not seen))
 def test_02_exact_rank_boundaries(self):
  for v in (1,1.5,2):
   for value in (math.nextafter(v,-math.inf),v,math.nextafter(v,math.inf)):
    expect='S' if value>=2 else 'A' if value>=1.5 else 'B' if value>=1 else 'C'
    self.assertEqual(rank_band(value),expect)
    rr=c(str(value),score=value);p=run([rr],policy='H1');d=p[1][0]
    self.assertEqual(d['rank'],expect)
    self.assertEqual(d['reason']=='FUNDED',expect in ('S','A'))
 def test_03_native_sort_stable_ties(self):
  rr=[c('id2',symbol='SAME'),c('id1',symbol='SAME'),c('id3',symbol='ZZZ')]
  self.assertEqual([r['entry_id'] for r in sorted(rr,key=candidate_order)],['id2','id1','id3'])
  rr=[c('c',score=1.5),c('b',score=2),c('a',score=2)];p=run(rr,policy='H1')
  self.assertEqual([d['entry_id'] for d in p[1]],['a','b','c'])
 def test_04_h1_all_vacancy_events(self):
  rr=[c('B_INITIAL',score=1.4),c('A_NORMAL',t=602,score=1.8),c('B_AFTER_NORMAL',t=614,score=1.4),c('S_SD',t=620),c('B_AFTER_SD',t=632,score=1.4)]
  pp={r['entry_id']:plan(r,sd=r['entry_id']=='S_SD',intent=r['entry_minute']+10,release=r['entry_minute']+12) for r in rr};p=run(rr,policy='H1',plans=pp)
  self.assertTrue(all(d['reason']=='ADMISSION_QUALITY_RESERVE' and d['held_before_batch']==[] for d in p[1] if d['rank']=='B'))
 def test_05_h1_no_late_relaxation(self):
  for t in (839,840,841,869,870,871,919):
   p=run([c('B',t=t,score=1.4)],policy='H1');self.assertEqual(p[1][0]['reason'],'ADMISSION_QUALITY_RESERVE')
 def test_06_intent_no_full_release_no_guard(self):
  rr=[c('S'),c('B',t=611,score=1.4)];pp={'S':plan(rr[0],sd=True,intent=610,release=620),'B':plan(rr[1],intent=630,release=632)};p=run(rr,plans=pp)
  self.assertEqual(decisions(p)['B']['reason'],'FUNDED');self.assertFalse(decisions(p)['B']['sd_full_release_seen_today'])
  self.assertEqual(next(f for f in p[3] if f['minute']==610)['concurrent'],1)
 def test_07_h2_release_same_timestamp_lunch_multiple_sd_reset(self):
  rr=[c('S1'),c('S2',t=601),c('B_SAME',t=612,score=1.4),c('B_LUNCH',t=720,score=1.4),c('A_NORMAL',t=750,score=1.5),c('B_AFTER_NORMAL',t=780,score=1.4)]
  pp={r['entry_id']:plan(r,sd=r['entry_id'] in ('S1','S2'),intent=610 if r['entry_id'].startswith('S') else 760,release=612 if r['entry_id'].startswith('S') else 762) for r in rr};p=run(rr,plans=pp)
  self.assertEqual(p[0]['sd_full_release_count_today'],2);self.assertEqual(p[0]['first_sd_release_known_at'],stamp(DAY,612))
  for d in p[1]:
   if d['rank']=='B':self.assertEqual(d['reason'],'ADMISSION_QUALITY_RESERVE');self.assertTrue(d['sd_full_release_seen_today'])
  self.assertEqual(decisions(p)['A_NORMAL']['reason'],'FUNDED')
  nextday='2099-01-06';p2=run([c('B_NEXT',day=nextday,score=1.4)],day=nextday,cash=p[0]['ending_cash'])
  self.assertEqual(p2[1][0]['reason'],'FUNDED');self.assertFalse(p2[1][0]['sd_full_release_seen_today'])
 def test_08_foreign_unfunded_future_plans_ignored(self):
  rr=[c('B',score=1.4)];pp={'B':plan(rr[0]),'FOREIGN_ARM_SD':{'action':'SD_FIRST','intent_minute':590,'source':{'kind':'SHARP_DROP_FIRST_OBSERVED_EXIT_V0','release_minute':591}}};p=run(rr,plans=pp)
  self.assertEqual(p[1][0]['reason'],'FUNDED');self.assertFalse(p[0]['sd_full_release_seen_today'])
  pp['B']=plan(rr[0],sd=True,intent=850,release=852);q=run(rr,plans=pp)
  self.assertEqual(p[1][0],q[1][0])
 def test_09_h2_native_b_gate_before_release(self):
  rr=[c('S1'),c('S2',t=601),c('B',t=602,score=1.1)];pp={r['entry_id']:plan(r,intent=700,release=702) for r in rr};p=run(rr,plans=pp)
  d=decisions(p)['B'];self.assertEqual(d['native_gate_action'],'REJECT');self.assertEqual(d['reason'],'SLOT_RESERVE_REJECT');self.assertEqual(d['overlay_gate_action'],'NOT_EVALUATED')
  q=run([c('B',score=1.1)]);self.assertEqual(q[1][0]['reason'],'FUNDED')
 def test_10_rejected_b_no_pending_slot_and_no_cash_backfill(self):
  p=run([c('B'+str(i),score=1.4) for i in range(5)],policy='H1');self.assertTrue(all(d['pre_decision_occupancy']==0 for d in p[1]))
  rr=[c('S'+str(i),price='100000') for i in range(4)];q=run(rr,policy='H1',books={},plans={})
  self.assertEqual([d['reason'] for d in q[1]],['CASH_OR_LOT_CONSTRAINED']*3+['MAX_POSITION_CAP'])
 def test_11_empty_rejected_empty_jsonl(self):
  for rr in ([],[c('B',score=1.4)]):
   p=run(rr,policy='H1',books={},plans={});self.assertEqual(p[0]['ending_cash'],'1000000');self.assertEqual(p[2],[]);self.assertEqual(p[4],[]);self.assertEqual(len(p[3]),392)
  target=ROOT/'synthetic'/'EMPTY.jsonl.gz';gzsave(target,[]);self.assertEqual(rows(target),[])
 def test_12_lot_cap_cash_max3_same_symbol(self):
  rr=[c('s',score=2),c('a',score=1.5),c('b',score=1.4),c('s_duplicate',t=601,symbol='s')];pp={r['entry_id']:plan(r,intent=700,release=702) for r in rr};p=run(rr,plans=pp)
  for d in p[1]:
   if d['reason']=='FUNDED':self.assertEqual(d['quantity']%100,0);self.assertLessEqual(D(d['debit']),D(d['equity_cap']))
  self.assertTrue(all(D(f['cash'])>=0 and f['concurrent']<=3 for f in p[3]));self.assertEqual(decisions(p)['s_duplicate']['reason'],'SYMBOL_ALREADY_OPEN')
  q=run([c('same1',symbol='same'),c('same2',symbol='same')],policy='H1');self.assertEqual(q[1][1]['reason'],'SYMBOL_ALREADY_PENDING')
 def test_13_e0_exact_on_off_predecessor_and_exit_semantics(self):
  rr=[c('S')];bb={'S':b(rr[0])};pp={'S':plan(rr[0],sd=True)}
  self.assertEqual(run(rr,policy='E0',books=bb,plans=pp),baseline(3,DAY,rr,bb,D(1000000),tables=TABLES,exit_plans=pp))
  self.assertEqual(day_replay(3,DAY,rr,bb,D(1000000),tables=TABLES,policy='E0'),baseline(3,DAY,rr,bb,D(1000000),tables=TABLES))
  self.assertEqual(route(600,610,[state(610)])['action'],'DELEGATE_CONTROL')
  for primary in ('DROP','DROP_STOP','PULLBACK','REBOUND','RANGE'):
   self.assertEqual(route(600,610,[state(601,primary)])['action'],'DELEGATE_CONTROL')
  self.assertEqual(route(600,610,[state(601),state(602,'REBOUND')])['intent_minute'],601)
 def test_14_common_entry_exit_r_costs_equal(self):
  rr=[c('S'),c('B',t=602,score=1.4)];pp={'S':plan(rr[0],sd=True,intent=610,release=612),'B':plan(rr[1],intent=630,release=632)};p=[run(rr,policy=a,plans=pp) for a in ('E0','H1','H2')]
  tt=[next(t for t in a[2] if t['entry_id']=='S') for a in p]
  for field in ('entry_minute','release_minute','source_minute','exit_kind','buy_effective','sell_effective','net_return','lineage','commission'):
   self.assertEqual(tt[0][field],tt[1][field]);self.assertEqual(tt[0][field],tt[2][field])
  self.assertEqual(D(tt[0]['buy_effective']),D('1000')*BUY);self.assertEqual(D(tt[0]['sell_effective']),D('1000')*D('.9995'))
 def test_15_state_abstention_vs_true_gap(self):
  self.assertEqual(route(600,610,[state(601,None,False)])['action'],'DELEGATE_CONTROL')
  self.assertEqual(route(600,610,[state(601,None,False,True)])['action'],'EVIDENCE_GAP')
  rr=[c('S')];p=run(rr,plans={'S':{'action':'EVIDENCE_GAP','block_minute':601,'reason':'EVIDENCE_GAP_BEFORE_CONTROL','source':None}})
  self.assertNotEqual(p[0]['status'],'COMPLETE');self.assertEqual(p[0]['open_obligations'],['S']);self.assertEqual(p[2],[])
 def test_16_unfilled_invalid_prices_no_fake_cash(self):
  self.assertTrue(all(_positive_price(v) for v in ('1000',D(1000),1000,1000.0)))
  for v in (None,'NaN','Infinity',float('nan'),float('inf'),True,0,-1,'junk','1_000'):
   self.assertFalse(_positive_price(v));rr=[c('S')];p=run(rr,plans={'S':plan(rr[0],sd=True,price=v)})
   self.assertNotEqual(p[0]['status'],'COMPLETE');self.assertEqual(p[2],[]);self.assertFalse(p[0]['sd_full_release_seen_today'])
  for invalid in (None,'NaN','Infinity',float('nan'),float('inf'),True,0,-1,'junk'):
   rr=[c('S')];book=b(rr[0]);book['market']=[market(920,invalid)]
   p=run(rr,books={'S':book},plans={'S':{'action':'DELEGATE_CONTROL','intent_minute':920,'source':None}})
   self.assertNotEqual(p[0]['status'],'COMPLETE');self.assertEqual(p[2],[]);self.assertFalse(p[0]['sd_full_release_seen_today'])
  rr=[c('S')];p=run(rr,plans={'S':plan(rr[0],sd=True,blocked='UNFILLED_EXECUTION_SOURCE')})
  self.assertFalse(p[0]['sd_full_release_seen_today']);self.assertEqual(p[2],[])
 def test_17_future_books_plans_do_not_change_prior_funding(self):
  rr=[c('S'),c('B',t=605,score=1.4)];pp={'S':plan(rr[0],sd=True,intent=800,release=802),'B':plan(rr[1],intent=700,release=702)}
  p=run(rr,plans=pp);bb={r['entry_id']:b(r) for r in rr}
  for book in bb.values():
   for row in book['market']:
    if row['minute']>=606:
     for field in ('O','H','L','C'):row[field]='2000'
  pp2=copy.deepcopy(pp);pp2['S']['source']['price']='500';q=run(rr,plans=pp2,books=bb)
  self.assertEqual(p[1],q[1])
  class NoLookup(dict):
   def __getitem__(self,key):raise AssertionError('REJECTED_ENTRY_EXECUTION_LOOKUP')
  r=run([c('B',score=1.4)],policy='H1',plans=NoLookup(),books=NoLookup());self.assertEqual(r[0]['status'],'COMPLETE')
 def test_18_window_id_label_invariance(self):
  rr=[c('S')];p=run([{**r,'window_id':'W_SYNTHETIC_A'} for r in rr]);q=run([{**r,'window_id':'renamed_display'} for r in rr]);self.assertEqual(p,q)
 def test_19_all_r_boundaries_unknown_zero(self):
  eps=F(1,10**30)
  def expected(v):
   if v is None:return 'R_UNKNOWN'
   for k,label in [(-5,'L5_PLUS'),(-4,'L4_5'),(-3,'L3_4'),(-2,'L2_3'),(-1,'L1_2')]:
    if v<=k:return label
   if v<0:return 'L0_1'
   if v==0:return 'ZERO'
   for k,label in [(1,'P0_1'),(2,'P1_2'),(3,'P2_3'),(4,'P3_4'),(5,'P4_5')]:
    if v<k:return label
   return 'P5_PLUS'
  for k in range(-5,6):
   for delta in (-eps,F(0),eps):self.assertEqual(bucket(F(k)+delta),expected(F(k)+delta))
  self.assertEqual(bucket(None),'R_UNKNOWN');self.assertEqual(bucket(F(0)),'ZERO');self.assertNotEqual(bucket(None),bucket(0))
  cohort=[None,F(0),F(-1),F(1)];self.assertEqual(sum(r is not None for r in cohort),3);self.assertEqual(sum(r is not None and r<0 for r in cohort),1)
 def test_20_midday_checkpoint_exact_no_duplicate_cash_trade(self):
  rr=[c('S'),c('B_PRE',t=609,score=1.4),c('B_AFTER',t=612,score=1.4),c('A',t=750,score=1.5)];pp={'S':plan(rr[0],sd=True,intent=610,release=612),'B_PRE':plan(rr[1],intent=620,release=622),'B_AFTER':plan(rr[2],intent=630,release=632),'A':plan(rr[3],sd=True,intent=760,release=762)}
  for policy in ('H1','H2'):
   binding={'window':'SYNTHETIC','input':'ARTIFICIAL_HASH','spec':'FIXED'};full=run(rr,policy=policy,plans=pp,checkpoint_binding=binding)
   for stop in (600,610,612,750,761,762):
    partial=run(rr,policy=policy,plans=pp,stop_after_minute=stop,checkpoint_binding=binding);carrier=json.loads(serialized(partial[0]['checkpoint']))
    restored=run(rr,policy=policy,plans=pp,resume_checkpoint=carrier,checkpoint_binding=binding)
    self.assertEqual(serialized(full),serialized(restored));self.assertEqual(len(restored[2]),len({t['entry_id'] for t in restored[2]}))
   with self.assertRaisesRegex(AssertionError,'CHECKPOINT_BINDING_MISMATCH'):run(rr,policy=policy,plans=pp,resume_checkpoint=carrier,checkpoint_binding={'input':'WRONG'})

class ReceiptResult(unittest.TextTestResult):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.records=[]
 def addSuccess(self,test):super().addSuccess(test);self.records.append({'test':test.id(),'status':'PASS'})
 def addFailure(self,test,err):super().addFailure(test,err);self.records.append({'test':test.id(),'status':'FAIL','reason':self._exc_info_to_string(err,test)})
 def addError(self,test,err):super().addError(test,err);self.records.append({'test':test.id(),'status':'ERROR','reason':self._exc_info_to_string(err,test)})
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(AdmissionContracts);result=unittest.TextTestRunner(verbosity=2,resultclass=ReceiptResult).run(suite)
 save(ROOT/'public'/'SYNTHETIC_TEST_RESULTS.json',{'scope':'ARTIFICIAL_FIXTURES_ONLY','real_replay_runs':0,'real_result_inspections':0,'test_N':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.records,'code_hashes':{n:pin(Path(__file__).parent/n) for n in ('admission_adapter.py','baseline_adapter.py','io_utils.py','synthetic_tests.py')},'checkpoint_restore_scope':'H1/H2 complete within-session execution state, intent/release/flat boundaries; E0 uses original flat-session carrier'})
 raise SystemExit(0 if result.wasSuccessful() else 1)
