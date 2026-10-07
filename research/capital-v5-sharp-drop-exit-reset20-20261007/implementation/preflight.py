from io_utils import *
from exit_adapter import route,compile_plan,numeric
from portfolio import day_replay
import sys,math,collections
sys.path.insert(0,str(NATIVE))
from allocation import allocation,band
from slot_policy import gate
from replay import day_replay as native_day

results=[]
def check(name,condition,details=None):
 results.append({'test':name,'status':'PASS' if condition else 'FAIL','details':details})
 if not condition:raise AssertionError(name)
def row(minute,price='1000',session='2025-07-15'):
 return {'session':session,'minute':minute,'O':price,'H':price,'L':price,'C':price,'Vo':'100','Va':'100000','lineage':{'fixture':'SYNTHETIC_BOUNDARY_ONLY'}}
def state(t,p='SHARP_DROP',usable=True,gap=False):return {'checkpoint_minute':t,'Primary':p,'usable':usable,'evidence_gap':gap}
def candidate(symbol='A',minute=600,score=2.0,day='2025-07-15'):
 return {'entry_id':day+'|'+symbol,'session':day,'symbol':symbol,'entry_minute':minute,'entry_timestamp':stamp(day,minute),'capital_score':score,'ML':score,'capacity_band':band(score),'rank':band(score),'admission':score>=1,'m2':.8,'m3':.6,'m5':.3,'raw_reference':'1000'}
def book(r,market=None,control=610,source=610):
 market=market or [row(t) for t in [599,600,601,602,610,611,620,920,930]]
 return {'entry_id':r['entry_id'],'session':r['session'],'symbol':r['symbol'],'capture_complete':True,'entry_actual_source':row(r['entry_minute']),'limit_up_authority':None,'market':market,'frozen_exit':{'exit_intent':{'minute':control},'sell_status':'FILLED','sell_source_assumed_available_at':stamp(r['session'],source+1),'sell_minute':source,'sell_source':'NEXT_ELIGIBLE_REGULAR_RAW_OPEN','sell_price_decimal':'999.5000'}}
def synthetic():
 for value in ['1000',D('1000'),1000,1000.0]:
  check('numeric_valid_'+type(value).__name__,numeric.raw_validation(row(601,value))[0])
 for name,value in [('null',None),('empty',''),('nan','NaN'),('infinity','Infinity'),('float_nan',float('nan')),('float_inf',float('inf')),('bool',True),('zero',0),('negative',-1),('junk','1_000')]:
  a=row(601);a['L']=value;a['O']=value;a['H']=value;a['C']=value
  check('numeric_reject_'+name,not numeric.raw_validation(a)[0])
 bad=row(601);bad['H']='999';check('OHLC_invalid',not numeric.raw_validation(bad)[0])
 for p in ['DROP','DROP_STOP','PULLBACK','RISE','SHARP_RISE','REBOUND','RANGE','RISE_STOP']:
  check('nonsharp_'+p,route(600,610,[state(601,p)])['action']=='DELEGATE_CONTROL')
 check('PRE_ACTIVE_no_extra_arm',route(600,610,[state(601)])['action']=='SD_FIRST')
 check('profit_condition_absent',route(600,610,[state(601)])['action']=='SD_FIRST')
 check('no_State_edge_required',route(600,610,[state(601),state(602)])['intent_minute']==601)
 check('buy_before_and_same_excluded',route(600,610,[state(599),state(600),state(601,'DROP')])['action']=='DELEGATE_CONTROL')
 check('Control_same_priority',route(600,610,[state(610)])['action']=='DELEGATE_CONTROL')
 check('Control_prior_priority',route(600,610,[state(611)])['action']=='DELEGATE_CONTROL')
 check('State_abstention',route(600,610,[state(601,None,False)])['action']=='DELEGATE_CONTROL')
 check('evidence_gap_not_abstention',route(600,610,[state(601,None,False,True)])['action']=='EVIDENCE_GAP')
 check('pending_recovery_cannot_cancel',route(600,610,[state(601),state(602,'REBOUND')])['intent_minute']==601)
 check('1520_Control_priority',route(600,920,[state(920)])['action']=='DELEGATE_CONTROL')
 s={'session':'2025-07-15','buy_fill_minute':600,'market':[row(t) for t in [599,600,601,750,751,920,924,930]]}
 for t,expected in [(600,601),(601,601),(690,751),(750,751),(919,920),(924,924),(925,930),(930,930)]:
  f=numeric.resolve_fill(s,t);check('fill_clock_'+str(t),f['source_minute']==expected and f['source_available_minute']==expected+1)
 check('1530_locked_terminal',numeric.resolve_fill(s,925)['closing_fallback_for_latched_intent'])
 unknown={'session':'2025-07-15','buy_fill_minute':600,'market':[row(599),row(600)]}
 check('no_future_fill_fabrication',numeric.resolve_fill(unknown,601)['status']!='FILLED')
 x=candidate();x['block']=1
 exact=allocation([x],D(1000000),D(0),D('100050'),[])[0]
 short=allocation([x],D(1000000),D(0),D('100049.99999'),[])[0]
 check('cash_equals_100share_lot',exact['quantity']==100)
 check('cash_below_100share_lot',short['quantity']==0)
 x2=candidate('B',score=1.5);x2['raw_reference']='100000'
 aa=allocation([x,x2],D(1000000),D(0),D(1000000),[])
 check('first_pass_zero_backfill_forbidden',aa[1]['first_pass_quantity']==aa[1]['quantity']==0)
 for v,expected in [(None,None),(float('nan'),None),(.999999,None),(1,'B'),(1.499999,'B'),(1.5,'A'),(1.99999,'A'),(2,'S')]:check('band_boundary_'+str(v),band(v)==expected)
 table={'minute_counts':{str(t):[0,0,0] for t in range(540,920)},'training_session_N':20,'B_median':1.2,'B_p75':1.4,'minute_bucket':{str(t):'10:00' for t in range(540,920)}}
 check('MAX3_exact_boundary',gate({**x,'rank':'S'},3,600,table)[0] is False)
 check('S_admit_occupancy_2',gate({**x,'rank':'S'},2,600,table)[0] is True)
 eps=F(1,10**30)
 label_sequence=['L5_PLUS','L4_5','L3_4','L2_3','L1_2','L0_1','P0_1','P1_2','P2_3','P3_4','P4_5','P5_PLUS']
 for k in range(-5,6):
  for delta,tag in [(-eps,'below'),(F(0),'equal'),(eps,'above')]:
   v=F(k)+delta
   if v<=-5:expect='L5_PLUS'
   elif v<=-4:expect='L4_5'
   elif v<=-3:expect='L3_4'
   elif v<=-2:expect='L2_3'
   elif v<=-1:expect='L1_2'
   elif v<0:expect='L0_1'
   elif v==0:expect='ZERO'
   elif v<1:expect='P0_1'
   elif v<2:expect='P1_2'
   elif v<3:expect='P2_3'
   elif v<4:expect='P3_4'
   elif v<5:expect='P4_5'
   else:expect='P5_PLUS'
   check('R_boundary_%d_%s'%(k,tag),bucket(v)==expect)
 check('UNKNOWN_separate_ZERO',bucket(None)=='R_UNKNOWN' and bucket(F(0))=='ZERO')
 r=candidate();r['block']=1;b=book(r)
 tables={'1':table};keys={r['entry_id']:b}
 check('overlay_OFF_byte_semantics',day_replay(3,r['session'],[r],keys,D(1000000),tables=tables)==native_day(3,r['session'],[r],keys,D(1000000),tables=tables))
 plan=compile_plan(b,600,[state(601),state(602,'REBOUND')])
 a,ds,ts,cs,it=day_replay(3,r['session'],[r],keys,D(1000000),tables=tables,exit_plans={r['entry_id']:plan})
 check('intent_fill_release_order',ts[0]['source_minute']==601 and ts[0]['release_minute']==602 and len([i for i in it if i.get('reason')=='SHARP_DROP_FIRST_OBSERVED'])==1)
 check('no_double_SELL',len(ts)==1 and len(it)==1)
 check('intent_does_not_release_cash',next(c for c in cs if c['minute']==601)['concurrent']==1 and next(c for c in cs if c['minute']==602)['concurrent']==0)
 check('fees_once',D(ts[0]['buy_effective'])==D('1000')*D('1.0005') and D(ts[0]['sell_effective'])==D('1000')*D('.9995'))
 r2=candidate('B',602);r2['block']=1;b2=book(r2,control=610)
 pp={r['entry_id']:plan,r2['entry_id']:compile_plan(b2,602,[state(603,'DROP')])}
 a2,dd,tt,cc,ii=day_replay(3,r['session'],[r,r2],{r['entry_id']:b,r2['entry_id']:b2},D(1000000),tables=tables,exit_plans=pp)
 d2=next(d for d in dd if d['entry_id']==r2['entry_id'])
 check('release_before_same_timestamp_next_BUY',d2['held_before_batch']==[] and d2['quantity']>0)
 ag,_,tg,_,ig=day_replay(3,r['session'],[r],keys,D(1000000),tables=tables,exit_plans={r['entry_id']:{'action':'EVIDENCE_GAP','block_minute':601,'reason':'EVIDENCE_GAP_BEFORE_CONTROL','source':None}})
 check('gap_funded_no_runtime_buy_filter',ag['status']!='COMPLETE' and len(ag['open_obligations'])==1 and not tg)
 check('window_portfolio_reset',day_replay(3,r['session'],[r],keys,D(1000000),tables=tables)==native_day(3,r['session'],[r],keys,D(1000000),tables=tables))
 check('market_State_history_separate_reset',plan['intent_minute']==compile_plan(b,600,[state(601)])['intent_minute'])

def fixtures():
 sources={r['entry_id']:r for r in json.loads((SHARP/'parent/private/ENTRY_CONTROL_SOURCE_ROWS.json').read_bytes())}
 cache={r['entry_id']:r for r in rows(PRI/'immutable/STATE_PREFIX_CACHE.jsonl.gz')}
 fixtures=rows(SHARP/'private/INTERVENTION_72_FILL_AND_RETURN_ROWS.jsonl.gz')
 comparisons=[]
 for f in fixtures:
  r=sources[f['entry_id']];choice=route(r['buy_fill_minute'],r['control_intent_minute'],cache[f['entry_id']]['frames'])
  fill=numeric.resolve_fill({'session':r['session'],'buy_fill_minute':r['buy_fill_minute'],'market':r['market']},choice['intent_minute'])
  same_intent=choice['action']=='SD_FIRST' and choice['intent_minute']==f['sealed_intent_minute']
  same_fill=fill==f['fill']
  credit=F(int(fill['effective_price_numerator']),int(fill['effective_price_denominator']))*100
  debit=F(r['buy_debit_100'])
  with localcontext() as c:c.prec=60;ret=str(D((credit-debit).numerator)/D((credit-debit).denominator)/ (D(debit.numerator)/D(debit.denominator)))
  same_R=F(ret)==F(f['R_E_native'])
  comparisons.append({'entry_id':f['entry_id'],'same_intent':same_intent,'same_fill':same_fill,'same_R':same_R})
 check('all_72_same_source_intent_fill_R',all(all(r[k] for k in ['same_intent','same_fill','same_R']) for r in comparisons),{'N':len(comparisons)})
 save(PRI/'FIXTURE72_COMPARISONS.json',comparisons)

def main():
 try:synthetic();fixtures()
 except Exception:
  import traceback
  save(PRI/'PREFLIGHT_FAILURE.json',{'traceback':traceback.format_exc(),'tests':results});save(PUB/'SYNTHETIC_TEST_RESULTS.json',{'status':'FAIL','tests':results});raise
 save(PUB/'SYNTHETIC_TEST_RESULTS.json',{'status':'PASS','PASS_N':len(results),'FAIL_N':0,'tests':results,'main_paths_started':0,'historical_fixture_72_recheck_only':True,'source_72_scope_different_from_Capital':True})
 print(json.dumps({'preflight':'PASS','test_N':len(results),'fixture72':'PASS','formal_replay_N':0}))
if __name__=='__main__':main()
