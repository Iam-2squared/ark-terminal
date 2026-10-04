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
P=ROOT.parent/'capital_staircase_v4_private'
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

def isotonic3(raw):
 # Independently enumerate all contiguous partitions, test decreasing feasibility,
 # then select least squared error. No Primary PAVA implementation is imported.
 possibilities=(((0,),(1,),(2,)),((0,1),(2,)),((0,),(1,2)),((0,1,2),))
 feasible=[]
 for groups in possibilities:
  values=[math.fsum(raw[i] for i in g)/len(g) for g in groups]
  if any(values[i]<values[i+1] for i in range(len(values)-1)):continue
  candidate=[0.]*3
  for g,value in zip(groups,values):
   for i in g:candidate[i]=value
  feasible.append((math.fsum((a-b)**2 for a,b in zip(raw,candidate)),candidate))
 return min(feasible,key=lambda x:x[0])[1]

def main():
 from zoneinfo import ZoneInfo
 profile='UPWARD_STAIRCASE_V4_MAX3'
 saved=read(P/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz');runtime=read(SRC/'capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz');raw={r['entry_id']:r for r in runtime};days_all=sorted({r['session'] for r in runtime})
 h3old={r['entry_id']:r for r in read(SRC/'capital_quality_v3_private/NEW_HEAD_OOF_PREDICTIONS.jsonl.gz')};h5old={r['entry_id']:r for r in read(V2/'CORE_P5_SCORE_STREAM.jsonl.gz')}
 teachers={r['entry_id']:r for r in read(V2/'TEACHERS_EVALUATION.jsonl.gz')};books={r['entry_id']:r for r in read(SRC/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
 counters=Counter();mismatch=[];maxdiff=0
 def check(k,ok,detail=None):
  counters[k]+=1
  if not ok:mismatch.append({'kind':k,'detail':detail})
 def near(k,a,b,tol=1e-12,detail=None):check(k,(a is None and b is None) or (a is not None and b is not None and abs(a-b)<=tol),detail)
 models={(h,i):json.loads((P/'models'/f'{h}_BLOCK_{i:02d}.json').read_text()) for h in ('H2','H3','H5') for i in range(1,9)}
 manifest=json.loads((OUT/'CORE_FEATURE_MANIFEST.json').read_text());hashes=json.loads((P/'MODEL_HASHES.json').read_text())
 for (head,block),model in models.items():
  file=P/'models'/f'{head}_BLOCK_{block:02d}.json';check('model_hash',hashlib.sha256(file.read_bytes()).hexdigest()==hashes[file.name])
  if head in ('H3','H5'):
   rel=f'capital_quality_v3_private/models/H3_BLOCK_{block:02d}.json' if head=='H3' else f'capital_v2_private/models/CORE_P_BLOCK_{block:02d}.json'
   check('reused_artifact_exact_bytes',file.read_bytes()==(SRC/rel).read_bytes(),(head,block))
  start=20+(block-1)*5;past=set(days_all[:start]);train=[r for r in runtime if r['session'] in past and r['entry_minute']<920]
  label_threshold=int(head[1:])/100;labels=[int(teachers[r['entry_id']]['potential_return']>=label_threshold) for r in train]
  check('past_training_IDs',[r['entry_id'] for r in train]==model['train_entry_ids'],(head,block))
  check('base_rate',sum(labels)/len(labels)==model['base_rate'],(head,block));check('both_train_classes',set(labels)=={0,1})
  check('training_before_test',all(r['session']<min(model['test_dates']) for r in train));check('test_block',model['test_dates']==days_all[start:start+5])
  prep=model['preprocessing'];check('CORE_manifest',prep['numeric_fields']==manifest['numeric'] and prep['categorical_fields']==manifest['categorical'])
  columns=[[float(r['numeric'][k]) if r['numeric'][k] is not None else 0 for r in train] for k in prep['numeric_fields']]+[[int(r['numeric'][k] is None) for r in train] for k in prep['numeric_fields']]
  for i,vs in enumerate(columns):
   mu=math.fsum(vs)/len(vs);std=math.sqrt(math.fsum((x-mu)**2 for x in vs)/len(vs)) or 1
   near('training_only_mean',mu,prep['numeric_mean'][i],1e-10,(head,block,i));near('training_only_std',std,prep['numeric_scale'][i],1e-10,(head,block,i))
  for k in prep['categorical_fields']:check('training_only_vocab',sorted({r['categorical'][k] or '__UNKNOWN__' for r in train}|{'__UNKNOWN__'})==prep['categorical_train_vocab'][k])
 reconstructed=[]
 for row in saved:
  key=row['entry_id'];r=raw[key];b=row['block'];prob=[scalar_probability(r,models[h,b]) for h in ('H2','H3','H5')];base=[models[h,b]['base_rate'] for h in ('H2','H3','H5')]
  for i,k in enumerate((2,3,5)):
   diff=abs(prob[i]-row[f'p{k}']);maxdiff=max(maxdiff,diff);near('probability_materialization',prob[i],row[f'p{k}'],detail=(key,k));check('base'+str(k),base[i]==row[f'base{k}'])
  check('H3_exact_reused_prediction',row['p3']==h3old[key]['H3']['p']);check('H5_exact_reused_prediction',row['p5']==h5old[key]['pP']);check('training_base_order',base[0]>=base[1]>=base[2])
  m=isotonic3(prob);M=sum(m);B=sum(base);ML=M/B
  for i,k in enumerate((2,3,5)):near('PAVA_m'+str(k),m[i],row[f'm{k}'],detail=key)
  for k,value in [('M',M),('B',B),('ML',ML)]:near(k,value,row[k],detail=key)
  check('admission',(ML>=1)==row['admission'],key);grade=capacity_band(ML);check('capacity_rank',grade==row['rank']==row['capacity_band'],key)
  reconstructed.append({**r,'m2':m[0],'m3':m[1],'m5':m[2],'ML':ML,'capital_score':ML,'rank':grade,'capacity_band':grade})
 ds,ts,frames,days,intents=replay(3,reconstructed,books,profile)
 pds=read(P/f'{profile}_DECISIONS.jsonl.gz');pts=read(P/f'{profile}_TRADES.jsonl.gz');pcs=read(P/f'{profile}_CURVE.jsonl.gz');pit=read(P/f'{profile}_INTENTS.jsonl.gz');pr=json.loads((P/f'{profile}_RESULT.json').read_text())
 for name,a,b in [('decision',ds,pds),('trade',ts,pts),('curve',frames,pcs),('intent',intents,pit)]:check(name+'_N',len(a)==len(b))
 for a,b in zip(ds,pds):
  for k in ('entry_id','reason','quantity'):check('decision_'+k,a[k]==b[k],a['entry_id'])
  if a['reason']=='FUNDED':
   for k in ('first_pass_quantity','water_fill_lots'):check('water_fill_'+k,a[k]==b[k])
   for k in ('debit','equity_cap','target_utilization','batch_equity','batch_budget','recycled_cash_used'):check('allocation_'+k,F(a[k])==F(b[k]),a['entry_id'])
   near('ML_proportional_desired',float(F(a['desired'])),float(F(b['desired'])),1e-8)
 for a,b in zip(ts,pts):
  for k in ('entry_id','quantity','release_minute','source_minute','exit_kind'):check('SELL_'+k,a[k]==b[k])
  for k in ('debit','credit'):check('BUY_SELL_exact_'+k,F(a[k])==F(b[k]))
 for a,b in zip(frames,pcs):
  check('frame_order',(a['session'],a['minute'])==(b['session'],b['minute']))
  for k in ('cash','equity'):check('ledger_exact_'+k,F(a[k])==F(b[k]))
  check('concurrent',a['concurrent']==b['concurrent']);check('MTM',a['known_marks']==b['known_marks'] and all(v<=a['minute'] for v in a['known_marks'].values()))
 for a,b in zip(intents,pit):check('EOD_intent',all(a[k]==b[k] for k in a))
 returns=[]
 for a,b in zip(days,pr['daily_series']):
  check('day_order',a['session']==b['session']);check('day_complete',a['complete']==(b['status']=='COMPLETE'));check('primary_chain',a['primary_chain']==b['primary_chain'])
  for k in ('starting_cash','cash_min','recycled_cash_used'):check('daily_'+k,F(a[k])==F(b[k]))
  check('day_end',a['ending_cash'] is None and b['ending_cash'] is None or a['ending_cash'] is not None and b['ending_cash'] is not None and F(a['ending_cash'])==F(b['ending_cash']))
  ret=float(F(a['ending_cash'])/F(a['starting_cash'])-1) if a['complete'] and a['primary_chain'] else None;near('daily_return',ret,b['daily_return'])
  if ret is not None:returns.append(ret)
 rolling=[]
 for i in range(len(days)-19):
  win=days[i:i+20]
  if all(x['complete'] and x['primary_chain'] for x in win):rolling.append({'start_session':win[0]['session'],'end_session':win[-1]['session'],'growth_multiple':float(F(win[-1]['ending_cash'])/F(win[0]['starting_cash']))})
 check('rolling20_N',len(rolling)==pr['valid_rolling20_window_N'])
 for a,b in zip(rolling,pr['rolling20_windows']):check('rolling20',all(a[k]==b[k] for k in a))
 vals=[r['growth_multiple'] for r in rolling];economic={'geometric_mean_daily_return':math.expm1(mean(math.log1p(v) for v in returns)),'arithmetic_mean_daily_return':mean(returns),'median_daily_return':median(returns),'rolling20_median':median(vals),'rolling20_maximum':max(vals),'rolling20_minimum':min(vals),'rolling20_arithmetic_mean':mean(vals),'final_equity':float(F(days[-1]['ending_cash'])),'total_return':float(F(days[-1]['ending_cash'])/1000000-1)}
 for k,v in economic.items():near('economic_'+k,v,pr[k])
 peak=F(1000000);dd=F(0);utils=[]
 for f in frames:
  eq=F(f['equity']);peak=max(peak,eq);dd=max(dd,(peak-eq)/peak)
  if 540<=f['minute']<690 or 750<=f['minute']<930:utils.append(float((eq-F(f['cash']))/eq))
 for k,v in [('max_drawdown',float(dd)),('utilization_mean',mean(utils)),('utilization_median',median(utils)),('time_utilization_ge80',mean(v>=.8 for v in utils)),('time_utilization_ge90',mean(v>=.9 for v in utils)),('cash_minimum',min(float(F(d['cash_min'])) for d in days)),('capital_recycling_used_jpy',sum(float(F(d['recycled_cash_used'])) for d in days)),('turnover_cash_jpy',float(sum((F(t['debit'])+F(t['credit']) for t in ts),F(0))))]:near('economic_'+k,v,pr[k],1e-7 if k in ('capital_recycling_used_jpy','turnover_cash_jpy') else 1e-12)
 selection=json.loads((OUT/'SELECTION_ANALYSIS.json').read_text());expected=selection['main'];funded={d['entry_id'] for d in ds if d['reason']=='FUNDED'}
 cohorts={f'U{k}':{r['entry_id'] for r in saved if teachers[r['entry_id']]['potential_return']>=k/100} for k in (2,3,5,10)};cohorts['Medium']=cohorts['U3']-cohorts['U5'];capture={k:{'total_N':len(ids),'funded_N':len(ids&funded),'capture_rate':len(ids&funded)/len(ids)} for k,ids in cohorts.items()}
 for k,v in capture.items():check('winner_capture',v==expected['capture'][k],k)
 def label_bucket(v):
  for threshold,name in [(.01,'<1'),(.02,'1-<2'),(.03,'2-<3'),(.04,'3-<4'),(.05,'4-<5'),(.10,'5-<10')]:
   if v<threshold:return name
  return '>=10'
 tm={t['entry_id']:t for t in ts};real=[float(F(t['credit'])/F(t['debit'])-1) for t in ts]
 def quality(vv):
  out={'realized_resolved_N':len(vv),'realized_mean':mean(vv) if vv else None,'realized_median':median(vv) if vv else None,'worst':min(vv) if vv else None}
  ordered=sorted(vv);at=(len(ordered)-1)*.05;low=math.floor(at);high=math.ceil(at);out['p05']=ordered[low]+(ordered[high]-ordered[low])*(at-low) if ordered else None
  for k,fn in [('PF1',lambda x:x>=.01),('positive',lambda x:x>0),('exact_zero',lambda x:x==0),('loss0',lambda x:x<=0),('tail1',lambda x:x<=-.01),('tail3',lambda x:x<=-.03)]:out[k+'_N']=sum(fn(x) for x in vv);out[k+'_rate']=out[k+'_N']/len(vv) if vv else None
  return out
 quality_main=quality(real)
 for k,v in quality_main.items():near('realized_quality_'+k,v,expected['quality'][k])
 for label,b in expected['buckets'].items():
  ids={r['entry_id'] for r in saved if label_bucket(teachers[r['entry_id']]['potential_return'])==label};selected=ids&funded;vv=[float(F(tm[k]['credit'])/F(tm[k]['debit'])-1) for k in selected if k in tm]
  check('bucket_candidate_N',len(ids)==b['total_candidate_N'],label);check('bucket_funded_N',len(selected)==b['funded_N'],label);near('bucket_capture',len(selected)/len(ids) if ids else None,b['capture_rate'])
  for k,v in quality(vv).items():near('bucket_quality_'+k,v,b[k])
  near('bucket_PnL',float(sum((F(tm[k]['credit'])-F(tm[k]['debit']) for k in selected if k in tm),F(0))),b['actual_pnl_jpy'],1e-8)
 for k,threshold in [('below1',.01),('below2',.02),('below3',.03)]:
  count=sum(teachers[key]['potential_return']<threshold for key in funded);check('contamination_'+k+'_N',count==expected['quality'][k+'_N']);near('contamination_'+k+'_rate',count/len(funded),expected['quality'][k+'_rate'])
 output(P/'INDEPENDENT_ENDPOINTS.json',{'economic':economic,'capture':capture,'quality':quality_main,'days':days,'rolling20':rolling})
 report={'JST':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),'status':'PASS' if not mismatch else 'FAIL','checks_N':sum(counters.values()),'checks':dict(counters),'mismatch_N':len(mismatch),'mismatch_categories':dict(Counter(x['kind'] for x in mismatch)),'max_scalar_probability_abs_difference':maxdiff,'independent_replays':1,'main_verification_reruns':0,'new_fits':0,'primary_imports':False,'independent_PAVA':'enumeration of four contiguous partitions, unweighted squared error','arithmetic':'exact Fraction funding/cash/marks/BUY/SELL; independent scalar inference and summaries','comparison_tolerances_precommitted':{'probability_score_and_return':1e-12,'training_mean_std':1e-10,'proportional_desired_JPY':1e-8,'cash_equity_BUY_SELL_quantity':0},'MAX4_MAX5_replays':0,'control_replays':0,'orders':0,'productionReady':False}
 if mismatch:output(P/'INDEPENDENT_MISMATCH_DETAIL.json',mismatch)
 output(OUT/'INDEPENDENT_AUDIT.json',report);print(json.dumps({k:v for k,v in report.items() if k!='checks'}),flush=True)
 assert not mismatch,'PRIMARY_INDEPENDENT_CONTRACT_FAIL'
if __name__=='__main__':main()
