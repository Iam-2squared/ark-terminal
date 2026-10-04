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
P=ROOT.parent/'capital_quality_v3_private'
V2=ROOT.parent/'capital_v2_private'
OUT=ROOT/'docs/evidence/capital-max3-top3-quality-v3-20261004-v1'
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
 caps={'S':F(45,100),'A':F(35,100),'B':F(25,100),'C':F(15,100)}
 deploy={'S':F(68,100),'A':F(56,100),'B':F(44,100),'C':F(30,100)}
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
   ranked=sorted(events[t],key=lambda r:(-r['Q'],-r['L5'],-r['L3'],r['entry_timestamp'],r['symbol']));choices=[]
   for r in ranked:
    d={'entry_id':r['entry_id'],'quantity':0,'reason':None};ds.append(d)
    if t>=920:d['reason']='CAPITAL_EOD_ENTRY_CUTOFF'
    elif not r['quality_gate_pass']:d['reason']='QUALITY_GATE_REJECT'
    elif r['rank'] not in {'QUALITY_V3_MAX3':{'S','A','B','C'},'S_ONLY_MAX3':{'S'},'A_PLUS_MAX3':{'S','A'},'B_PLUS_MAX3':{'S','A','B'}}[profile]:d['reason']='RANK_CUTOFF_REJECT'
    elif not math.isfinite(r['capital_score']):d['reason']='SCORE_INPUT_UNKNOWN'
    elif any(p['symbol']==r['symbol'] for p in held.values()):d['reason']='SYMBOL_ALREADY_OPEN'
    else:choices.append((r,d))
   selected=choices[:max(0,n-len(held))]
   for r,d in choices[len(selected):]:d['reason']='MAX_POSITION_CAP'
   if selected:
    exposure=sum(p['q']*p['mark'] for p in held.values());equity=cash+exposure
    bb=[p['band'] for p in held.values()]+[capacity_band(r['capital_score']) for r,d in selected]
    best=min(bb,key=lambda x:('S','A','B','C').index(x));target=min(F(92,100),deploy[best]+F(55,1000)*(len(bb)-1))
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

def main():
 import re
 profiles=('QUALITY_V3_MAX3','S_ONLY_MAX3','A_PLUS_MAX3','B_PLUS_MAX3')
 saved=read(P/'QUALITY_V3_SCORE_STREAM.jsonl.gz');runtime=read(P/'CORE_RUNTIME_CAUSAL.jsonl.gz');raw={r['entry_id']:r for r in runtime};days_all=sorted({r['session'] for r in runtime})
 h5={r['entry_id']:r for r in read(V2/'CORE_P5_SCORE_STREAM.jsonl.gz')}
 teachers={r['entry_id']:r for r in read(V2/'TEACHERS_EVALUATION.jsonl.gz')}
 books={r['entry_id']:r for r in read(ROOT.parent/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
 counters=Counter();mismatch=[]
 def check(k,ok,detail=None):
  counters[k]+=1
  if not ok:mismatch.append({'kind':k,'detail':detail})
 models={(p.stem.split('_BLOCK_')[0],int(p.stem.split('_BLOCK_')[1])):json.loads(p.read_text()) for p in (P/'models').glob('*.json')}
 h5models={int(p.stem.rsplit('_',1)[1]):json.loads(p.read_text()) for p in (V2/'models').glob('CORE_P_BLOCK_*.json')}
 manifest=json.loads((OUT/'CORE_FEATURE_MANIFEST.json').read_text())
 for (head,block),model in models.items():
  start=20+(block-1)*5;past=set(days_all[:start]);prefix=[r for r in runtime if r['session'] in past and r['entry_minute']<920]
  labels={}
  for r in prefix:
   t=teachers[r['entry_id']];ret=t['realized_net_return']
   label=t['label_bigwinner3'] if head=='H3' else None if ret is None else int(ret>=.01) if head=='HF1' else int(ret<=0)
   if label is not None:labels[r['entry_id']]=label
  train=[r for r in prefix if r['entry_id'] in labels];check('past_training_IDs',[r['entry_id'] for r in train]==model['train_entry_ids'],(head,block))
  base=sum(labels[r['entry_id']] for r in train)/len(train);check('training_only_base_rate',base==model['base_rate'],(head,block))
  check('training_before_test',all(r['session']<min(model['test_dates']) for r in train))
  prep=model['preprocessing'];check('CORE_manifest',prep['numeric_fields']==manifest['numeric'] and prep['categorical_fields']==manifest['categorical'])
  columns=[]
  for k in prep['numeric_fields']:columns.append([float(r['numeric'][k]) if r['numeric'][k] is not None else 0 for r in train])
  for k in prep['numeric_fields']:columns.append([int(r['numeric'][k] is None) for r in train])
  for i,vs in enumerate(columns):
   mu=math.fsum(vs)/len(vs);std=math.sqrt(math.fsum((x-mu)**2 for x in vs)/len(vs));std=std or 1
   check('training_only_mean',abs(mu-prep['numeric_mean'][i])<1e-10,(head,block,i))
   check('training_only_std',abs(std-prep['numeric_scale'][i])<1e-10,(head,block,i))
  for k in prep['categorical_fields']:
   check('training_only_vocabulary',sorted({r['categorical'][k] or '__UNKNOWN__' for r in train}|{'__UNKNOWN__'})==prep['categorical_train_vocab'][k])
 reconstructed=[];maxdiff=0
 for row in saved:
  key=row['entry_id'];r=raw[key];b=row['block'];probs={h:scalar_probability(r,models[h,b]) for h in ('H3','HF1','HL0')};pp=scalar_probability(r,h5models[b]);bases={h:models[h,b]['base_rate'] for h in probs}
  check('H5_fixed_identity',row['p5']==h5[key]['pP'] and row['base5']==h5[key]['baseP'])
  for h,col in [('H3','p3'),('HF1','p_floor1'),('HL0','p_loss0')]:
   diff=abs(probs[h]-row[col]);maxdiff=max(maxdiff,diff);check('head_probability_materialization',diff<1e-12,(key,h))
  check('H5_probability',abs(pp-row['p5'])<1e-12,key)
  lifts={'L5':pp/h5[key]['baseP'],'L3':probs['H3']/bases['H3'],'LF1':probs['HF1']/bases['HF1'],'LSAFE':(1-probs['HL0'])/(1-bases['HL0'])}
  q=(lifts['L5']*lifts['LF1']*lifts['LSAFE'])**(1/3);admit=all(lifts[k]>=1 for k in ('L3','LF1','LSAFE'));grade=capacity_band(q)
  for k,v in lifts.items():check('lift_'+k,abs(v-row[k])<1e-11,key)
  check('quality_arithmetic',abs(q-row['Q'])<1e-11,key);check('admission',admit==row['quality_gate_pass'],key);check('rank',grade==row['rank'],key)
  reconstructed.append({**r,**lifts,'block':b,'Q':q,'capital_score':q,'rank':grade,'capacity_band':grade,'quality_gate_pass':admit})
 endpoints={}
 for profile in profiles:
  ds,ts,frames,days,intents=replay(3,reconstructed,books,profile)
  pds=read(P/(profile+'_DECISIONS.jsonl.gz'));pts=read(P/(profile+'_TRADES.jsonl.gz'));pcs=read(P/(profile+'_CURVE.jsonl.gz'));pit=read(P/(profile+'_INTENTS.jsonl.gz'));pr=json.loads((P/(profile+'_RESULT.json')).read_text())
  for kind,a,b in (('decision_N',ds,pds),('trade_N',ts,pts),('curve_N',frames,pcs),('intent_N',intents,pit)):check(kind,len(a)==len(b),profile)
  for a,b in zip(ds,pds):
   for k in ('entry_id','reason','quantity'):check('decision_'+k,a[k]==b[k],(profile,a['entry_id']))
   if a['reason']=='FUNDED':
    for k in ('first_pass_quantity','water_fill_lots'):check(k,a[k]==b[k])
    for k in ('debit','equity_cap','target_utilization','batch_equity','batch_budget','recycled_cash_used'):check('allocation_'+k,F(a[k])==F(b[k]),(profile,a['entry_id']))
    check('proportional_budget',abs(float(F(a['desired'])-F(b['desired'])))<1e-8)
  for a,b in zip(ts,pts):
   for k in ('entry_id','quantity','release_minute','source_minute','exit_kind'):check('SELL_'+k,a[k]==b[k])
   for k in ('debit','credit'):check('exact_trade_'+k,F(a[k])==F(b[k]))
  for a,b in zip(frames,pcs):
   check('frame_order',(a['session'],a['minute'])==(b['session'],b['minute']))
   for k in ('cash','equity'):check('exact_'+k,F(a[k])==F(b[k]))
   check('concurrent',a['concurrent']==b['concurrent']);check('MTM_past_only',a['known_marks']==b['known_marks'] and all(v<=a['minute'] for v in a['known_marks'].values()))
  for a,b in zip(intents,pit):check('EOD_intent',all(a[k]==b[k] for k in a))
  returns=[]
  for a,b in zip(days,pr['daily_series']):
   check('day_order',a['session']==b['session']);check('day_complete',a['complete']==(b['status']=='COMPLETE'));check('primary_chain',a['primary_chain']==b['primary_chain'])
   for k in ('starting_cash','cash_min','recycled_cash_used'):check('day_'+k,F(a[k])==F(b[k]))
   check('day_end',a['ending_cash'] is None and b['ending_cash'] is None or a['ending_cash'] is not None and b['ending_cash'] is not None and F(a['ending_cash'])==F(b['ending_cash']))
   ret=float(F(a['ending_cash'])/F(a['starting_cash'])-1) if a['complete'] and a['primary_chain'] else None
   check('daily_return',ret==b['daily_return'])
   if ret is not None:returns.append(ret)
  rolling=[]
  for i in range(len(days)-19):
   win=days[i:i+20]
   if all(x['complete'] and x['primary_chain'] for x in win):rolling.append({'start_session':win[0]['session'],'end_session':win[-1]['session'],'growth_multiple':float(F(win[-1]['ending_cash'])/F(win[0]['starting_cash']))})
  check('rolling_N',len(rolling)==pr['valid_rolling20_window_N'])
  for a,b in zip(rolling,pr['rolling20_windows']):check('rolling20',all(a[k]==b[k] for k in a))
  vals=[r['growth_multiple'] for r in rolling]
  economic={'geometric_mean_daily_return':math.expm1(mean(math.log1p(v) for v in returns)) if returns else None,'arithmetic_mean_daily_return':mean(returns) if returns else None,'median_daily_return':median(returns) if returns else None,'rolling20_median':median(vals) if vals else None,'rolling20_maximum':max(vals) if vals else None}
  for k,v in economic.items():check('economic_'+k,v==pr[k])
  validdays={d['session'] for d in days if d['complete'] and d['primary_chain']};peak=F(1000000);dd=F(0);utils=[]
  for f in frames:
   if f['session'] not in validdays:continue
   eq=F(f['equity']);peak=max(peak,eq);dd=max(dd,(peak-eq)/peak)
   if 540<=f['minute']<690 or 750<=f['minute']<930:utils.append(float((eq-F(f['cash']))/eq))
  check('MaxDD',abs(float(dd)-pr['max_drawdown'])<1e-12 if validdays else pr['max_drawdown'] is None)
  check('utilization',abs(mean(utils)-pr['utilization_mean'])<1e-12 if utils else pr['utilization_mean'] is None)
  selected={d['entry_id'] for d in ds if d['reason']=='FUNDED'}
  ups={name:{r['entry_id'] for r in saved if teachers[r['entry_id']][lab]==1} for name,lab in [('U3','label_bigwinner3'),('U5','label_bigwinner5'),('U10','label_bigwinner10')]};ups['Medium']=ups['U3']-ups['U5']
  capture={k:{'total_N':len(ids),'funded_N':len(ids&selected),'capture_rate':len(ids&selected)/len(ids)} for k,ids in ups.items()}
  real=[float(F(t['credit'])/F(t['debit'])-1) for t in ts];quality={'funded_N':len(selected),'realized_resolved_N':len(real),'PF1_N':sum(v>=.01 for v in real),'loss0_N':sum(v<=0 for v in real),'tail1_N':sum(v<=-.01 for v in real),'tail3_N':sum(v<=-.03 for v in real)}
  expected=json.loads((OUT/'SELECTION_ANALYSIS.json').read_text())['profiles'][profile]
  for k,v in quality.items():check('realized_quality',expected['quality'][k]==v,(profile,k))
  for k,v in capture.items():check('winner_capture',expected['capture'][k]==v,(profile,k))
  endpoints[profile]={'economic':economic,'capture':capture,'quality':quality,'days':days,'rolling20':rolling}
 output(P/'INDEPENDENT_ENDPOINTS.json',endpoints)
 report={'status':'PASS' if not mismatch else 'FAIL','checks_N':sum(counters.values()),'checks':dict(counters),'mismatch_N':len(mismatch),'mismatch_categories':dict(Counter(m['kind'] for m in mismatch)),'max_scalar_probability_abs_difference':maxdiff,'independent_replays':4,'new_fits':0,'primary_imports':False,'arithmetic':'Fraction funding,cash,marks,BUY/SELL factors; separately implemented scalar probabilities and quality/portfolio summaries. Fixed saved model coefficients shared.','MAX4_MAX5_replays':0,'orders':0,'productionReady':False}
 if mismatch:output(P/'INDEPENDENT_MISMATCH_DETAIL.json',mismatch)
 output(OUT/'INDEPENDENT_AUDIT.json',report);print(json.dumps({k:v for k,v in report.items() if k!='checks'}),flush=True)
 assert not mismatch,'PRIMARY_INDEPENDENT_CONTRACT_FAIL'
if __name__=='__main__':main()
