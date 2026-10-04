"""Independent exact Fraction MAX3 replay; imports no Primary implementation.

Adapted from prior audited independent v2 logic, removing only liquidity constraints.
Fixed source/score/model artifacts are shared IO; no fit or external-source validation.
"""
from collections import Counter,defaultdict
from datetime import datetime
from fractions import Fraction as F
from pathlib import Path
from statistics import mean,median
import gzip,hashlib,json,math
ROOT=Path(__file__).resolve().parents[2]
P=ROOT.parent/'capital_liquidity_off_private'
V2=ROOT.parent/'capital_v2_private'
OUT=ROOT/'docs/evidence/capital-max3-liquidity-off-20261004-v1'
def read(path):return [json.loads(x) for x in gzip.open(path,'rt')]
def output(path,value):
 with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def minute(value):
 t=datetime.fromisoformat(value);return t.hour*60+t.minute

def actual(row,auction=False):
 try:
  if not row.get('lineage'):return False
  o,h,l,c,v,a=[F(str(row[k])) for k in ('O','H','L','C','Vo','Va')]
  return min(o,h,l,c,v,a)>0 and l<=min(o,c) and max(o,c)<=h and (not auction or o==h==l==c)
 except Exception:return False

def scalar_probability(r,model):
 prep=model['preprocessing'];numeric=[r['numeric'][k] for k in prep['numeric_fields']]
 values=[float(x) if x is not None else 0 for x in numeric]+[float(x is None) for x in numeric]
 values=[(x-m)/s for x,m,s in zip(values,prep['numeric_mean'],prep['numeric_scale'])]
 for k in prep['categorical_fields']:
  vocab=prep['categorical_train_vocab'][k];v=r['categorical'][k]
  if v not in vocab:v='__UNKNOWN__'
  values.extend(float(v==c) for c in vocab)
 logit=math.fsum(x*w for x,w in zip(values,model['coef']))+model['intercept']
 return 1/(1+math.exp(-logit)) if logit>=0 else math.exp(logit)/(1+math.exp(logit))

def capacity_band(score):return 'HIGH' if score>=2 else 'MID' if score>=1.5 else 'BASE' if score>=1 else None

def replay(n,stream,books):
 assert n==3
 capital=F(1000000);chain=True;ds=[];ts=[];frames=[];days=[];intents=[]
 caps={'HIGH':F(45,100),'MID':F(35,100),'BASE':F(25,100)}
 deploy={'HIGH':F(68,100),'MID':F(56,100),'BASE':F(44,100)}
 for day in sorted({r['session'] for r in stream}):
  opening=capital if chain else F(1000000);cash=opening;held={};scheduled=defaultdict(list);blocked=[];events=defaultdict(list)
  original_pool=opening;recycled_pool=F(0);recycled_used=F(0);cash_min=opening;peak=0
  for r in stream:
   if r['session']==day:events[r['entry_minute']].append(r)
  for t in range(540,932):
   for key,p in held.items():
    while p['cursor']<len(p['feed']) and p['feed'][p['cursor']][0]<=t:
     p['known'],p['mark']=p['feed'][p['cursor']];p['cursor']+=1
   for key,fill in sorted(scheduled.pop(t,[])):
    assert key in held
    if fill is None:blocked.append(key);continue
    p=held.pop(key);price,kind,source_minute=fill;debit=p['q']*p['buy'];credit=p['q']*price;cash+=credit;recycled_pool+=credit
    ts.append({'entry_id':key,'quantity':p['q'],'debit':str(debit),'credit':str(credit),'release_minute':t,'source_minute':source_minute,'exit_kind':kind})
   ranked=sorted(events[t],key=lambda r:(-r['capital_score'],r['entry_timestamp'],r['symbol']));choices=[]
   for r in ranked:
    d={'entry_id':r['entry_id'],'quantity':0,'reason':None};ds.append(d)
    if t>=920:d['reason']='CAPITAL_EOD_ENTRY_CUTOFF'
    elif r['capital_score']<1:d['reason']='BELOW_CAPITAL_BASELINE'
    elif not math.isfinite(r['capital_score']):d['reason']='SCORE_INPUT_UNKNOWN'
    elif any(p['symbol']==r['symbol'] for p in held.values()):d['reason']='SYMBOL_ALREADY_OPEN'
    else:choices.append((r,d))
   selected=choices[:max(0,n-len(held))]
   for r,d in choices[len(selected):]:d['reason']='MAX_POSITION_CAP'
   if selected:
    exposure=sum(p['q']*p['mark'] for p in held.values());equity=cash+exposure
    bb=[p['band'] for p in held.values()]+[capacity_band(r['capital_score']) for r,d in selected]
    best=min(bb,key=lambda x:('HIGH','MID','BASE').index(x));target=min(F(92,100),deploy[best]+F(55,1000)*(len(bb)-1))
    budget=min(cash,max(F(0),equity*target-exposure));unspent=budget;remaining=cash
    weights=sum(F(str(r['capital_score'])) for r,d in selected);sizes=[]
    for r,d in selected:
     b=capacity_band(r['capital_score']);lot=100*F(r['raw_reference'])*F(10005,10000)
     ceiling=equity*caps[b];desired=budget*F(str(r['capital_score']))/weights
     lots=int(min(desired,ceiling,remaining)/lot);debit=lots*lot;remaining-=debit;unspent-=debit
     sizes.append({'q':lots*100,'first':lots*100,'lot':lot,'debit':debit,'cap':ceiling,'extra':0,'band':b})
    while True:
     added=0
     for a in sizes:
      if a['first']>=100 and a['lot']<=remaining and a['lot']<=unspent and a['debit']+a['lot']<=a['cap']:
       a['q']+=100;a['debit']+=a['lot'];a['extra']+=1;remaining-=a['lot'];unspent-=a['lot'];added+=1
     if not added:break
    for (r,d),a in zip(selected,sizes):
     if a['q']<100:
      d['reason']='CASH_OR_LOT_CONSTRAINED';continue
     d.update(quantity=a['q'],first_pass_quantity=a['first'],water_fill_lots=a['extra'],reason='FUNDED',debit=str(a['debit']))
     cash-=a['debit'];cash_min=min(cash_min,cash)
     used=min(original_pool,a['debit']);original_pool-=used;recycled=a['debit']-used;recycled_pool-=recycled;recycled_used+=recycled
     assert recycled_pool>=0
     d['recycled_cash_used']=str(recycled)
     key=r['entry_id'];book=books[key]
     held[key]={'symbol':r['symbol'],'q':a['q'],'buy':F(r['raw_reference'])*F(10005,10000),'mark':F(r['raw_reference']),
      'known':t,'band':a['band'],'feed':sorted((row['minute']+1,F(row['C'])) for row in book['market'] if row.get('session')==day and row['minute']>=t and actual(row)),'cursor':0}
     peak=max(peak,len(held));assert cash>=0 and len(held)<=n
     if not book['capture_complete'] or not book.get('entry_actual_source'):blocked.append(key)
     x=book['frozen_exit']
     if x['sell_status']=='FILLED' and minute(x['sell_source_assumed_available_at'])<=920:
      rr=next((row for row in book['market'] if row['minute']==x['sell_minute']),None);release=minute(x['sell_source_assumed_available_at']);fill=None
      if rr and actual(rr):
       price=F(rr['O'] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else rr['C'])*F(9995,10000)
       assert price==F(x['sell_price_decimal']);fill=(price,'FROZEN_EXIT_V3',rr['minute'])
      scheduled[release].append((key,fill))
   if t==920:
    for key,p in sorted(held.items()):
     authority=books[key]['limit_up_authority'];confirmed=bool(authority and authority.get('status')=='LIMIT_UP_CONFIRMED' and authority.get('authoritative_price_limit_source') and authority.get('causal_exchange_status') and authority.get('session')==day and authority.get('known_minute',9999)<=t and authority.get('observed_minute',9999)<=t)
     intents.append({'entry_id':key,'quantity':p['q'],'minute':920,'limit_up_status':'LIMIT_UP_CONFIRMED' if confirmed else 'LIMIT_UP_UNKNOWN'})
     market=books[key]['market'];regular=[a for a in market if a.get('session')==day and 920<=a['minute']<925 and actual(a)]
     auction=[a for a in market if a.get('session')==day and a['minute']==930 and actual(a,True)]
     if regular:
      a=min(regular,key=lambda x:x['minute']);fill=(F(a['O'])*F(9995,10000),'EOD_REGULAR',a['minute'])
     elif auction:
      a=auction[0];fill=(F(a['C'])*F(9995,10000),'EOD_EXACT_1530_AUCTION',a['minute'])
     else:blocked.append(key);continue
     scheduled[a['minute']+1].append((key,fill))
   eq=cash+sum(p['q']*p['mark'] for p in held.values())
   frames.append({'session':day,'minute':t,'cash':str(cash),'equity':str(eq),'concurrent':len(held),'known_marks':{k:p['known'] for k,p in held.items()}})
  valid=not held and not blocked
  days.append({'session':day,'starting_cash':str(opening),'ending_cash':str(cash) if valid else None,'primary_chain':chain,'complete':valid,'cash_min':str(cash_min),'max_concurrent':peak,'recycled_cash_used':str(recycled_used)})
  if chain and valid:capital=cash
  elif chain:chain=False
 return ds,ts,frames,days,intents

def main():
 stream=read(V2/'CORE_P5_SCORE_STREAM.jsonl.gz')
 books={r['entry_id']:r for r in read(ROOT.parent/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
 teacher={r['entry_id']:r for r in read(V2/'TEACHERS_EVALUATION.jsonl.gz')}
 counts=Counter();mismatches=[]
 def check(kind,ok,detail=None):
  counts[kind]+=1
  if not ok:mismatches.append({'kind':kind,'detail':detail})
 models={int(p.stem.rsplit('_',1)[1]):json.loads(p.read_text()) for p in (V2/'models').glob('CORE_P_BLOCK_*.json')}
 maximum_scalar_difference=0
 for r in stream:
  p=scalar_probability(r,models[r['block']]);difference=abs(p-r['pP']);maximum_scalar_difference=max(maximum_scalar_difference,difference)
  check('scalar_probability',difference<1e-12,r['entry_id'])
  check('score_identity',abs(p/r['baseP']-r['capital_score'])<1e-11,r['entry_id'])
 ds,ts,frames,days,intents=replay(3,stream,books)
 primary_ds=read(P/'LIQUIDITY_OFF_MAX3_DECISIONS.jsonl.gz')
 primary_ts=read(P/'LIQUIDITY_OFF_MAX3_TRADES.jsonl.gz')
 primary_frames=read(P/'LIQUIDITY_OFF_MAX3_CURVE.jsonl.gz')
 primary_intents=read(P/'LIQUIDITY_OFF_MAX3_INTENTS.jsonl.gz')
 primary=json.loads((P/'LIQUIDITY_OFF_MAX3_RESULT.json').read_text())
 for category,left,right in (('decision_N',ds,primary_ds),('trade_N',ts,primary_ts),('frame_N',frames,primary_frames),('intent_N',intents,primary_intents)):
  check(category,len(left)==len(right))
 for a,b in zip(ds,primary_ds):
  check('entry_order',a['entry_id']==b['entry_id'],a['entry_id'])
  check('candidate_eligibility',a['reason']==b['reason'],a['entry_id'])
  check('quantity',a['quantity']==b['quantity'],a['entry_id'])
  if a['reason']=='FUNDED':
   for key in ('first_pass_quantity','water_fill_lots'):check(key,a[key]==b[key],a['entry_id'])
   check('BUY_debit',F(a['debit'])==F(b['debit']),a['entry_id'])
   check('cash_recycling',F(a['recycled_cash_used'])==F(b['recycled_cash_used']),a['entry_id'])
 for a,b in zip(ts,primary_ts):
  check('SELL_order',a['entry_id']==b['entry_id'])
  for key in ('quantity','release_minute','source_minute','exit_kind'):check('SELL_'+key,a[key]==b[key],a['entry_id'])
  for key in ('debit','credit'):check('trade_'+key,F(a[key])==F(b[key]),a['entry_id'])
 for a,b in zip(frames,primary_frames):
  check('frame_order',(a['session'],a['minute'])==(b['session'],b['minute']))
  for key in ('cash','equity'):check('exact_'+key,F(a[key])==F(b[key]),(a['session'],a['minute']))
  check('concurrent',a['concurrent']==b['concurrent'])
  check('causal_marks',a['known_marks']==b['known_marks'])
 for a,b in zip(intents,primary_intents):
  check('EOD_intent',all(a[k]==b[k] for k in a),a['entry_id'])
 independent_daily=[]
 for a,b in zip(days,primary['daily_series']):
  check('day_order',a['session']==b['session'])
  check('day_complete',a['complete']==(b['status']=='COMPLETE'))
  check('day_primary_chain',a['primary_chain']==b['primary_chain'])
  check('day_start_cash',F(a['starting_cash'])==F(b['starting_cash']))
  check('day_end_cash',a['ending_cash'] is None and b['ending_cash'] is None or a['ending_cash'] is not None and b['ending_cash'] is not None and F(a['ending_cash'])==F(b['ending_cash']))
  check('day_cash_min',F(a['cash_min'])==F(b['cash_min']))
  check('day_recycling',F(a['recycled_cash_used'])==F(b['recycled_cash_used']))
  check('day_max_concurrent',a['max_concurrent']==b['max_concurrent'])
  daily_return=float(F(a['ending_cash'])/F(a['starting_cash'])-1) if a['complete'] and a['primary_chain'] else None
  check('daily_return',daily_return==b['daily_return'])
  independent_daily.append({**a,'daily_return':daily_return})
 rolling=[]
 for i in range(len(days)-19):
  window=days[i:i+20]
  if not all(d['complete'] and d['primary_chain'] for d in window):continue
  multiple=float(F(window[-1]['ending_cash'])/F(window[0]['starting_cash']))
  rolling.append({'start_session':window[0]['session'],'end_session':window[-1]['session'],'growth_multiple':multiple,'hit':multiple>=2})
 check('rolling_N',len(rolling)==primary['valid_rolling20_window_N'])
 for a,b in zip(rolling,primary['rolling20_windows']):
  check('rolling20',all(a[k]==b[k] for k in a))
 funded={d['entry_id'] for d in ds if d['reason']=='FUNDED'}
 winner_ids={r['entry_id'] for r in stream if teacher[r['entry_id']]['label_bigwinner5']==1}
 winner10_ids={r['entry_id'] for r in stream if teacher[r['entry_id']]['label_bigwinner10']==1}
 check('BigWinner5_total',len(winner_ids)==170)
 capture={'BigWinner5_total_N':len(winner_ids),'BigWinner5_funded_N':len(funded&winner_ids),
  'BigWinner5_capture_rate':len(funded&winner_ids)/len(winner_ids),'BigWinner10_funded_N':len(funded&winner10_ids)}
 if (OUT/'BIGWINNER_PRESERVATION.json').exists():
  expected=json.loads((OUT/'BIGWINNER_PRESERVATION.json').read_text())
  for key,value in capture.items():check('BigWinner_capture',expected[key]==value)
 for key in ('geometric_mean_daily_return','arithmetic_mean_daily_return','median_daily_return'):
  returns=[d['daily_return'] for d in independent_daily if d['daily_return'] is not None]
  value=(math.expm1(mean(math.log1p(x) for x in returns)) if key.startswith('geometric') else mean(returns) if key.startswith('arithmetic') else median(returns)) if returns else None
  check('return_summary',value==primary[key])
 valid_days={d['session'] for d in days if d['complete'] and d['primary_chain']};peak=F(1000000);maxdd=F(0)
 for frame in frames:
  if frame['session'] not in valid_days:continue
  equity=F(frame['equity']);peak=max(peak,equity);maxdd=max(maxdd,(peak-equity)/peak)
 check('MaxDD',abs(float(maxdd)-primary['max_drawdown'])<1e-12 if valid_days else primary['max_drawdown'] is None)
 output(P/'INDEPENDENT_ENDPOINTS.json',{'days':independent_daily,'rolling20':rolling,'capture':capture})
 report={'status':'PASS' if not mismatches else 'FAIL','checks_N':sum(counts.values()),'checks':dict(counts),
  'mismatch_N':len(mismatches),'mismatch_categories':dict(Counter(m['kind'] for m in mismatches)),
  'primary_imports':False,'independent_replays':1,'new_fits':0,'MAX4_MAX5_replays':0,
  'max_scalar_probability_abs_difference':maximum_scalar_difference,'capture':capture,
  'independence_limit':'Shared fixed stream/model coefficients, Frozen upstream and saved source IO; separately implemented Fraction funding/cash/marks/metrics.',
  'orders':0,'productionReady':False}
 output(OUT/'INDEPENDENT_AUDIT.json',report)
 print(json.dumps({k:v for k,v in report.items() if k!='checks'}),flush=True)
 assert not mismatches,'PRIMARY_INDEPENDENT_CONTRACT_FAIL'

if __name__=='__main__':main()
