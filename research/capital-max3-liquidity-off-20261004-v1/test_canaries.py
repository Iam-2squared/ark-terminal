"""Focused counterfactual canaries and one deterministic verification; no fits."""
import copy,json,hashlib,ast
from decimal import Decimal as D
from checkpoint import ROOT,OUT,PRIVATE,V2,SAFETY,save,sha
from io_data import rows,stream,books
from allocation import allocation,band
from execution import BUY,last_actual_mark,eod_source
from replay import day_replay,run_profile

def canonical(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def market(t,price,day):
 return {'minute':t,'session':day,'O':str(price),'H':str(price),'L':str(price),'C':str(price),
  'Vo':'100','Va':str(price*100),'lineage':{'fixture':'synthetic canary only; not historical fill'}}

def main():
 tests=[]
 def check(n,name,ok,evidence=None):tests.append({'N':n,'name':name,'status':'PASS' if ok else 'FAIL','evidence':evidence})
 score=stream();bookmap=books();day='2025-06-30'
 r={'entry_id':'fixture','session':day,'symbol':'FIXTURE','entry_minute':600,
  'entry_timestamp':day+'T10:00:00+09:00','capital_score':2.,'capacity_band':'HIGH',
  'raw_reference':'100','liquidity':{'eligible':False,'reason':'LIQUIDITY_UNKNOWN','capacity':None}}
 b={'session':day,'market':[market(600,100,day),market(920,120,day)],'capture_complete':True,
  'entry_actual_source':market(600,100,day),'frozen_exit':{'sell_status':'UNFILLED'},'limit_up_authority':None}
 variants=[]
 for status,eligible,capacity in [('LIQUIDITY_ELIGIBLE',True,'999999999'),('EXTREME_ILLIQUIDITY_REJECT',False,'0'),('LIQUIDITY_UNKNOWN',False,None)]:
  v=copy.deepcopy(r);v['liquidity'].update(eligible=eligible,reason=status,capacity=capacity);variants.append(v)
 runs=[day_replay(3,day,[v],{'fixture':b},D(1000000)) for v in variants]
 check(1,'Liquidity status change -> score unchanged',all(v['capital_score']==r['capital_score'] for v in variants))
 check(2,'Liquidity status change -> candidate eligibility unchanged',all(x[1]==runs[0][1] for x in runs) and all(x[1][0]['reason']=='FUNDED' for x in runs))
 sizes=[allocation([v],D(1000000),D(0),D(1000000),[]) for v in variants]
 check(3,'Liquidity capacity change -> position size unchanged',all(a==sizes[0] for a in sizes))
 future=copy.deepcopy(r);future.update(future_liquidity={'coverage':0,'volume':0,'status':'FUTURE_REJECT'})
 altered=day_replay(3,day,[future],{'fixture':b},D(1000000))
 check(4,'Future liquidity change -> BUY unchanged',runs[0][1]==altered[1])
 future_book=copy.deepcopy(b)
 for row in future_book['market']:
  if row['minute']>r['entry_minute']:row.update(H='999999999',L='0.0000001')
 altered=day_replay(3,day,[r],{'fixture':future_book},D(1000000))
 check(5,'Future High/Low change -> score and first BUY unchanged',r['capital_score']==altered[1][0]['capital_score'] and runs[0][1]==altered[1])
 future_book=copy.deepcopy(b);future_book['frozen_exit']={'sell_status':'UNFILLED','future_net_result':999999,'future_state':'FUTURE'}
 altered=day_replay(3,day,[r],{'fixture':future_book},D(1000000))
 check(6,'Future EXIT change -> score unchanged',runs[0][1][0]['capital_score']==altered[1][0]['capital_score'])
 ds=rows(PRIVATE/'LIQUIDITY_OFF_MAX3_DECISIONS.jsonl.gz');ts=rows(PRIVATE/'LIQUIDITY_OFF_MAX3_TRADES.jsonl.gz')
 frames=rows(PRIVATE/'LIQUIDITY_OFF_MAX3_CURVE.jsonl.gz');intents=rows(PRIVATE/'LIQUIDITY_OFF_MAX3_INTENTS.jsonl.gz')
 result=json.loads((PRIVATE/'LIQUIDITY_OFF_MAX3_RESULT.json').read_text());design=json.loads((OUT/'DESIGN_PRECOMMIT.json').read_text())
 check(7,'MAX concurrent <=3',all(c['concurrent']<=3 for c in frames) and result['max_positions']==3)
 check(8,'100-share lot',all(d['quantity']>=0 and d['quantity']%100==0 for d in ds))
 check(9,'cash<0 absent',all(D(c['cash'])>=0 for c in frames))
 check(10,'LONG only',design['accounting']['LONG_only'] and all(d['quantity']>=0 for d in ds))
 check(11,'short/margin/leverage zero',not any(design['accounting'][k] for k in ('short','margin','leverage')))
 boundary=True
 for t in (920,921,925):
  v={**r,'entry_minute':t,'entry_timestamp':day+f'T{t//60:02}:{t%60:02}:00+09:00'}
  z=day_replay(3,day,[v],{},D(1000000));boundary&=z[1][0]['quantity']==0 and z[1][0]['reason']=='CAPITAL_EOD_ENTRY_CUTOFF'
 check(12,'Entry>=15:20 funding0',boundary and all(d['quantity']==0 for d in ds if d['minute']>=920))
 mark,known=last_actual_mark([market(600,101,day),market(607,999,day),market(602,888,'2025-06-27')],600,606,'100',day)
 check(13,'MTM mark != fill',mark==D(101) and known==601 and eod_source([market(600,101,day)],day) is None)
 sparse=copy.deepcopy(b);sparse['market']=[market(600,100,day)]
 nofill=day_replay(3,day,[r],{'fixture':sparse},D(1000000));debit=D(nofill[1][0]['debit'])
 check(14,'no-trade mark -> cash release0',nofill[0]['ending_cash'] is None and not nofill[2] and D(nofill[3][-1]['cash'])==D(1000000)-debit)
 check(15,'Valid EXIT/EOD fill only -> cash release',len(runs[0][2])==1 and runs[0][2][0]['release_minute']==921 and not nofill[2] and nofill[0]['daily_return'] is None)
 earlier=copy.deepcopy(b);earlier['market'].append(market(601,110,day));earlier['frozen_exit']={
  'sell_status':'FILLED','sell_source_assumed_available_at':day+'T10:02:00+09:00','sell_minute':601,
  'sell_source':'NEXT_ELIGIBLE_REGULAR_RAW_OPEN','sell_price_decimal':str(D(110)*D('.9995'))}
 prior=day_replay(3,day,[r],{'fixture':earlier},D(1000000))
 check(16,'Duplicate sell0',len(prior[2])==1 and not prior[4] and len(ts)==len({t['entry_id'] for t in ts}) and len(intents)==len({i['entry_id'] for i in intents}))
 pins=json.loads((PRIVATE/'REFERENCE_READ_ONLY_HASHES.json').read_text())
 manifest=json.loads((PRIVATE/'SOURCE_MANIFEST.json').read_text())
 check(17,'Frozen Entry/EXIT and old Evidence changes0',all(sha(ROOT/p)==h for p,h in pins.items()) and all(sha(ROOT.parent/manifest[k]['path'])==manifest[k]['sha256'] for k in ('frozen_entry','frozen_exit_rows')))
 rerun,dd,tt,cc,ii=run_profile('LIQUIDITY_OFF',3,score,bookmap)
 check(18,'Deterministic single-profile rerun',all(canonical(a)==canonical(b) for a,b in ((dd,ds),(tt,ts),(cc,frames),(ii,intents))),{'verification_replays':1,'new_fits':0})
 expected='a34f2c4a090a589d4e80858b65f01f3dc95a7849a57aece7e815213d20429731'
 check(19,'Control score stream identity',sha(V2/'CORE_P5_SCORE_STREAM.jsonl.gz')==expected==result['score_stream_sha256'] and len(score)==1039)
 independent=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text())
 check(20,'Primary/Independent mismatch0',independent['mismatch_N']==0 and independent['status']=='PASS' and not independent['primary_imports'])
 class NoLiquidityRead(dict):
  def __getitem__(self,key):
   assert key!='liquidity','LIQUIDITY_RUNTIME_ACCESS';return super().__getitem__(key)
 poison=NoLiquidityRead(r);poisoned=day_replay(3,day,[poison],{'fixture':b},D(1000000))
 check(21,'Runtime liquidity access0',poisoned[1]==runs[0][1])
 check(22,'Candidate equity caps and fixed score1 obeyed',all(D(d['debit'])<=D(d['equity_cap']) for d in ds if d['reason']=='FUNDED') and all(d['quantity']==0 for d in ds if d['capital_score']<1) and band(1)=='BASE')
 check(23,'Execution contract byte identity',sha(ROOT/'research/capital-max3-liquidity-off-20261004-v1/execution.py')==sha(ROOT/'research/capital-vnext-v2-movement-20261004-v1/execution.py'))
 check(24,'Safety allfalse and fits/MAX4/MAX5 zero',not any(SAFETY.values()) and design['new_fits']==design['MAX4_MAX5_replays']==design['new_provider_requests']==0)
 report={'status':'PASS' if all(x['status']=='PASS' for x in tests) else 'FAIL','tests_N':len(tests),
  'passed_N':sum(x['status']=='PASS' for x in tests),'fail_N':sum(x['status']=='FAIL' for x in tests),'tests':tests,
  'new_fits':0,'deterministic_verification_replays':1,'MAX4_MAX5_replays':0,'orders':0,'productionReady':False}
 save(OUT/'FOCUSED_TEST_RESULTS.json',report)
 print(json.dumps({k:v for k,v in report.items() if k!='tests'}),flush=True)
 assert report['fail_N']==0,'CANARY_CONTRACT_FAIL'

if __name__=='__main__':main()
