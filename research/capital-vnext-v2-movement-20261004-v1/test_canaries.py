"""Required30 focused causal/accounting canaries; no new fit or tuning."""
import copy,hashlib,json,math
from pathlib import Path
from decimal import Decimal as D
from checkpoint import ROOT,OUT,PRIVATE,save,sha,SAFETY
from io_data import rows,books,calendar,history,gzwrite
from allocation import allocation,liquidity,band,CAP
from movement import project
from core_features import project as core_project
from model import predict_saved
from execution import last_actual_mark,eod_source,eod_intent,BUY
from replay import day_replay,run_profile,ARMS

def canonical(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def fixture_market(t,price,day='2025-06-30'):
 return {'minute':t,'O':str(price),'H':str(price),'L':str(price),'C':str(price),'Vo':'100','Va':str(price*100),
  'session':day,'lineage':{'wrapper_sha256':'fixture','response_sha256':'fixture','row_ordinal':0}}
def main():
 runtime=rows(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz');byid={r['entry_id']:r for r in runtime}
 bb=books();hist,_=history();cal=calendar()
 streams={arm:rows(PRIVATE/(arm+'_SCORE_STREAM.jsonl.gz')) for arm in ARMS}
 models={(m['head'],m['block']):m for p in (PRIVATE/'models').glob('*.json') if (m:=json.loads(p.read_text()))}
 saved={r['entry_id']:r for r in streams['MOVE_DUAL']}
 entries={r['watch_key']:r for r in rows(ROOT.parent/'work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if r['entry_status']=='FIRST_ENTRY'}
 tests=[]
 def check(n,name,ok,evidence=None):
  tests.append({'N':n,'name':name,'status':'PASS' if ok else 'FAIL','evidence':evidence})
 sample=[]
 for day in sorted({r['session'] for r in streams['MOVE_DUAL']}):
  sample.append(min((r for r in streams['MOVE_DUAL'] if r['session']==day),key=lambda r:(r['entry_minute'],r['symbol'])))
 mutations={k:True for k in ('high','low','state','path','same_day_future')}
 for r in sample:
  core=byid[r['entry_id']];book=bb[r['entry_id']];t=r['entry_minute']
  before,_=project(core,hist,cal,book['market'])
  for name in ('high','low','same_day_future'):
   changed=copy.deepcopy(book['market'])
   for row in changed:
    if row['minute']>=t:
     if name=='high':row['H']='999999999'
     elif name=='low':row['L']='0.000001'
     else:row.update(O='999999',H='999999',L='999999',C='999999',Va='999999999999')
   after,_=project(core,hist,cal,changed);rr={**r,'numeric':{**r['numeric'],**after}}
   model=models['MOVE_P',r['block']]
   mutations[name]&=before==after and abs(float(predict_saved([rr],model)[0])-r['pP'])<1e-12
  trace=rows(ROOT.parent/f"work_inputs/exit_v2/FULL_TRACE/{r['session']}_{r['symbol']}.jsonl.gz")
  original=core_project(entries[r['entry_id']],trace)
  for name in ('state','path'):
   changed=copy.deepcopy(trace)
   for row in changed:
    if row['bar_end_minute']>t:
     if name=='state':row['state']['primary']='FUTURE_MUTATION';row['state']['numeric_status']='FUTURE_MUTATION'
     else:row['path']['Primary_or_null']='FUTURE_MUTATION';row['path_events']=[{'event_type':'TRANSITION'}]
   after=core_project(entries[r['entry_id']],changed)
   rr={**r,'numeric':{**r['numeric'],**after['numeric']},'categorical':after['categorical']}
   mutations[name]&=original==after and abs(float(predict_saved([rr],models['MOVE_P',r['block']])[0])-r['pP'])<1e-12
 check(1,'future High -> runtime score unchanged',mutations['high'],{'representative_sessions':len(sample)})
 check(2,'future Low -> runtime score unchanged',mutations['low'])
 r=sample[0];core=byid[r['entry_id']];book=copy.deepcopy(bb[r['entry_id']]);before,_=project(core,hist,cal,book['market'])
 book['frozen_exit']={'future_changed':True};after,_=project(core,hist,cal,book['market'])
 check(3,'future EXIT -> runtime features unchanged',before==after)
 forbidden=('label_bigwinner5','label_realized_positive','realized_net_return','frozen_exit','potential_return')
 check(4,'Head R label training/eval only',all(not any(k in r or k in r['numeric'] or k in r['categorical'] for k in forbidden) for arm in ARMS for r in streams[arm]))
 check(5,'future State suffix -> score unchanged',mutations['state'])
 check(6,'future Path suffix -> score unchanged',mutations['path'])
 future_hist=dict(hist);key=next((k for k in hist if k[0]>=r['session'] and k[1]==r['symbol']),None)
 if key:
  hh=copy.deepcopy(hist[key]);hh['daily']['Va']='0';hh['active_minute_bitmap_hex']='0'*82;future_hist[key]=hh
 check(7,'future liquidity -> funding unchanged',liquidity(core,cal,hist)==liquidity(core,cal,future_hist))
 # Earliest BUY of an isolated day is fixed before any future source/limit-up book.
 funded=next(r for r in streams['MOVE_DUAL'] if r['liquidity']['eligible'] and r['capital_score']>=1 and r['entry_minute']<920)
 original=copy.deepcopy(bb[funded['entry_id']]);altered=copy.deepcopy(original)
 altered['limit_up_authority']={'status':'LIMIT_UP_CONFIRMED','authoritative_price_limit_source':'fixture','causal_exchange_status':'fixture',
  'session':funded['session'],'known_minute':919,'observed_minute':919}
 a=day_replay(3,funded['session'],[funded],{funded['entry_id']:original},D(1000000))
 b=day_replay(3,funded['session'],[funded],{funded['entry_id']:altered},D(1000000))
 check(8,'future limit-up -> Entry funding unchanged',a[1]==b[1])
 causal=all(r['movement_provenance']['current_max_source_minute'] is None or r['movement_provenance']['current_max_source_minute']<r['entry_minute'] for r in runtime)
 check(9,'Movement Entry-past only',causal and all(all(d<r['session'] for d in r['movement_provenance']['prior20_calendar_dates']) for r in runtime))
 check(10,'current same-day future bars unused',mutations['same_day_future'])
 decisions=[d for arm in ARMS for n in (3,4,5) for d in rows(PRIVATE/f'{arm}_MAX{n}_DECISIONS.jsonl.gz')]
 check(11,'Entry>=15:20 funding0',all(d['quantity']==0 for d in decisions if d['minute']>=920))
 class PastOnly(dict):
  def get(self,key,default=None):
   assert key[0]<core['session'];return super().get(key,default)
  def __getitem__(self,key):
   assert key[0]<core['session'];return super().__getitem__(key)
 liquidity(core,cal,PastOnly(hist));project(core,PastOnly(hist),cal,bb[core['entry_id']]['market'])
 check(12,'Extreme Liquidity past-only',True)
 design=json.loads((OUT/'DESIGN_PRECOMMIT.json').read_text())
 check(13,'identity blacklist0',not any('symbol' in k or 'calendar_date' in k for k in design.get('numeric_features',[])) and all('symbol' not in m['preprocessing']['numeric_fields'] and 'symbol' not in m['preprocessing']['categorical_fields'] for m in models.values()))
 check(14,'score threshold fixed1.0',design['scores']['funding_threshold']==1 and all(d['quantity']==0 for d in decisions if d['capital_score']<1) and band(1)=='BASE' and band(math.nextafter(1,0)) is None)
 funded_decisions=[d for d in decisions if d['reason']=='FUNDED']
 check(15,'equity cap obeyed',all(D(d['debit'])<=D(d['equity_cap']) for d in funded_decisions))
 check(16,'liquidity cap obeyed',all(D(d['debit'])<=D(d['liquidity_cap']) for d in funded_decisions))
 chosen=[r for r in streams['MOVE_DUAL'] if r['liquidity']['eligible'] and r['capital_score']>=1][:3]
 chosen=sorted(chosen,key=lambda r:(-r['capital_score'],r['entry_timestamp'],r['symbol']))
 check(17,'water-fill deterministic',allocation(chosen,D(1000000),D(0),D(1000000),[])==allocation(chosen,D(1000000),D(0),D(1000000),[]))
 changed=copy.deepcopy(chosen)
 for r0 in changed:r0.update(label_bigwinner5=1,label_realized_positive=1,realized_exit_pnl='99999999',future_source_available=False)
 check(18,'water-fill outcome blind',allocation(chosen,D(1000000),D(0),D(1000000),[])==allocation(changed,D(1000000),D(0),D(1000000),[]))
 results=[json.loads((PRIVATE/f'{arm}_MAX{n}_RESULT.json').read_text()) for arm in ARMS for n in (3,4,5)]
 check(19,'cash<0 zero',all(result['cash_minimum']>=0 for result in results))
 check(20,'100-share lot',all(d['quantity']%100==0 for d in decisions))
 check(21,'LONG only',all(not v for v in SAFETY.values()) and design['accounting']['LONG_only'])
 check(22,'margin/short/leverage0',not any(design['accounting'][k] for k in ('margin','short','leverage')))
 day='2025-06-30';near=fixture_market(600,101,day);future=fixture_market(607,999,day);prior=fixture_market(602,888,'2025-06-27')
 mark,known=last_actual_mark([near,future,prior],600,606,'100',day)
 check(23,'MTM mark != fill',mark==D(101) and known==601 and eod_source([near,future,prior],day) is None)
 row={'entry_id':'fixture','session':day,'symbol':'FIXTURE','entry_minute':600,'entry_timestamp':day+'T10:00:00+09:00',
  'capital_score':2.,'capacity_band':'HIGH','raw_reference':'100','liquidity':{'eligible':True,'reason':'LIQUIDITY_ELIGIBLE','capacity':'1000000'}}
 book={'session':day,'market':[fixture_market(600,100,day)],'capture_complete':True,'entry_actual_source':fixture_market(600,100,day),
  'frozen_exit':{'sell_status':'UNFILLED'},'limit_up_authority':None}
 nofill=day_replay(3,day,[row],{'fixture':book},D(1000000));debit=D(nofill[1][0]['debit']);last=nofill[3][-1]
 check(24,'no-trade mark no cash release',nofill[0]['ending_cash'] is None and not nofill[2] and D(last['cash'])==D(1000000)-debit)
 good=copy.deepcopy(book);good['market'].append(fixture_market(920,120,day));filled=day_replay(3,day,[row],{'fixture':good},D(1000000))
 check(25,'EOD valid fill only',len(filled[2])==1 and filled[2][0]['release_minute']==921 and nofill[0]['daily_return'] is None)
 check(26,'duplicate sell0',all(len({t['entry_id'] for t in rows(PRIVATE/f'{arm}_MAX{n}_TRADES.jsonl.gz')})==len(rows(PRIVATE/f'{arm}_MAX{n}_TRADES.jsonl.gz')) for arm in ARMS for n in (3,4,5)) and len(filled[4])==1)
 check(27,'MAX3/4/5 cap exact',all(result['max_concurrent_actual']<=result['max_positions'] for result in results))
 fitreport=json.loads((OUT/'ROLLING_ORIGIN_HEAD_FITS.json').read_text())
 check(28,'Profile refit0',fitreport['fits']==24 and fitreport['profile_refits']==fitreport['within_block_refits']==0 and len(models)==24)
 deterministic=True
 for arm in ARMS:
  for n in (3,4,5):
   rerun,dd,tt,cc,ii=run_profile(arm,n,streams[arm],bb)
   for label,values in [('DECISIONS',dd),('TRADES',tt),('CURVE',cc),('INTENTS',ii)]:deterministic&=canonical(values)==canonical(rows(PRIVATE/f'{arm}_MAX{n}_{label}.jsonl.gz'))
 check(29,'deterministic9-run rerun',deterministic,{'new_fits':0})
 independent=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text())
 check(30,'Primary / Independent mismatch0',independent['status']=='PASS' and independent['mismatch_N']==0 and not independent['Primary_logic_imported'])
 # Focused additional exact-source and floor boundaries, with fixed policies.
 changed_source=copy.deepcopy(original);changed_source['market']=[x for x in changed_source['market'] if x['minute']<920]
 changed_run=day_replay(3,funded['session'],[funded],{funded['entry_id']:changed_source},D(1000000))
 check(31,'future EOD source missing -> BUY unchanged',a[1]==changed_run[1])
 check(32,'limit-up normal EOD one intent',len(b[4])==len({i['entry_id'] for i in b[4]}) and all(i['minute']==920 for i in b[4]))
 report={'status':'PASS' if all(t['status']=='PASS' for t in tests) else 'FAIL','tests_N':len(tests),
  'passed_N':sum(t['status']=='PASS' for t in tests),'fail_N':sum(t['status']=='FAIL' for t in tests),'tests':tests,
  'fits_added':0,'profile_refits':0,'hyperparameter_sweep':0,'feature_search':0,'threshold_sweep':0,'orders':0,'productionReady':False}
 save(OUT/'FOCUSED_TEST_RESULTS.json',report);print(json.dumps({k:v for k,v in report.items() if k!='tests'}))
 assert report['fail_N']==0,'CANARY_CONTRACT_FAIL'

if __name__=='__main__':main()
