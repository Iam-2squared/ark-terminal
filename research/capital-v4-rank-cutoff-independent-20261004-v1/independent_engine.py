"""Independent exact Fraction MAX3 replay; imports no Primary implementation.

Shared fixed IO only. Independent scalar inference, four-partition isotonic projection, Fraction allocation and ledger; no Primary import.
Fixed source/score/model artifacts are shared IO; no fit or external-source validation.
"""
from collections import Counter,defaultdict
from datetime import datetime
from fractions import Fraction as F
from pathlib import Path
from statistics import mean,median
import gzip,hashlib,json,math
ROOT=Path(__file__).resolve().parents[2]
P=ROOT.parent/'capital_v4_rank_cutoff_private'
SRC=ROOT.parent/'inputs/v3'
V2=SRC/'capital_v2_private'
OUT=ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1'
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

def capacity_band(score):return 'S' if score>=2 else 'A' if score>=1.5 else 'B' if score>=1 else 'C'

def replay(n,stream,books,profile):
 assert n==3
 capital=F(1000000);chain=True;ds=[];ts=[];frames=[];days=[];intents=[]
 caps={'S':F(45,100),'A':F(35,100),'B':F(25,100)}
 deploy={'S':F(68,100),'A':F(56,100),'B':F(44,100)}
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
   ranked=sorted(events[t],key=lambda r:(-r['ML'],-r['m5'],-r['m3'],-r['m2'],r['entry_timestamp'],r['symbol']));choices=[]
   for r in ranked:
    d={'entry_id':r['entry_id'],'quantity':0,'reason':None};ds.append(d)
    if t>=920:d['reason']='CAPITAL_EOD_ENTRY_CUTOFF'
    elif r['ML']<1:d['reason']='UPWARD_BELOW_BASELINE'
    elif r['rank'] not in {'S_ONLY_MAX3':('S',),'A_PLUS_MAX3':('S','A'),'B_PLUS_MAX3':('S','A','B')}[profile]:d['reason']='RANK_CUTOFF_'+profile.removesuffix('_MAX3')
    elif not math.isfinite(r['capital_score']):d['reason']='SCORE_INPUT_UNKNOWN'
    elif any(p['symbol']==r['symbol'] for p in held.values()):d['reason']='SYMBOL_ALREADY_OPEN'
    else:choices.append((r,d))
   selected=choices[:max(0,n-len(held))]
   for r,d in choices[len(selected):]:d['reason']='MAX_POSITION_CAP'
   if selected:
    exposure=sum(p['q']*p['mark'] for p in held.values());equity=cash+exposure
    bb=[p['band'] for p in held.values()]+[capacity_band(r['capital_score']) for r,d in selected]
    best=min(bb,key=lambda x:('S','A','B').index(x));target=min(F(92,100),deploy[best]+F(55,1000)*(len(bb)-1))
    budget=min(cash,max(F(0),equity*target-exposure));unspent=budget;remaining=cash
    weights=sum(F(str(r['capital_score'])) for r,d in selected);sizes=[]
    for r,d in selected:
     b=capacity_band(r['capital_score']);lot=100*F(r['raw_reference'])*F(10005,10000)
     ceiling=equity*caps[b];desired=budget*F(str(r['capital_score']))/weights
     lots=int(min(desired,ceiling,remaining)/lot);debit=lots*lot;remaining-=debit;unspent-=debit
     sizes.append({'q':lots*100,'first':lots*100,'lot':lot,'debit':debit,'cap':ceiling,'extra':0,'band':b,'target':target,'equity':equity,'budget':budget,'desired':desired})
    while True:
     added=0
     for a in sizes:
      if a['first']>=100 and a['lot']<=remaining and a['lot']<=unspent and a['debit']+a['lot']<=a['cap']:
       a['q']+=100;a['debit']+=a['lot'];a['extra']+=1;remaining-=a['lot'];unspent-=a['lot'];added+=1
     if not added:break
    for (r,d),a in zip(selected,sizes):
     if a['q']<100:
      d['reason']='CASH_OR_LOT_CONSTRAINED';continue
     d.update(quantity=a['q'],first_pass_quantity=a['first'],water_fill_lots=a['extra'],reason='FUNDED',debit=str(a['debit']),equity_cap=str(a['cap']),target_utilization=str(a['target']),batch_equity=str(a['equity']),batch_budget=str(a['budget']),desired=str(a['desired']))
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
