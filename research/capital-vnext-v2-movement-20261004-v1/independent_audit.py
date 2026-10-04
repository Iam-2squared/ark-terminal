"""Independent feature/teacher/scalar-model audit and exact Fraction9-run replay.

Imports no Primary model, ranking, movement or allocation implementation.
Provider aggregates, Frozen upstream and fixed fitted coefficients are shared I/O.
"""
from collections import Counter,defaultdict
from datetime import datetime
from fractions import Fraction as F
from pathlib import Path
from statistics import median
import gzip,hashlib,json,math
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
P=ROOT.parent/'capital_v2_private'
OUT=ROOT/'docs/evidence/capital-vnext-v2-movement-20261004-v1'
ARMS=('CORE_P5','MOVE_P5','MOVE_DUAL')
REGULAR=list(range(540,690))+list(range(750,925))

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
def sufficient(r):
 return bool(r and all(r.get(k,{}).get('date_scope_complete') and r.get(k,{}).get('terminal_pagination_proven') for k in ('daily_source','minute_source')))
def percentile(values,p):
 v=sorted(values)
 if not v:return None
 point=(len(v)-1)*p;lo=math.floor(point);hi=math.ceil(point)
 return v[lo]+(v[hi]-v[lo])*(point-lo)
def rp(raw):
 try:
  o,h,l=[F(str(raw[k])) for k in ('O','H','L')]
  return float(100*(h-l)/o) if min(o,h,l)>0 and h>=l else None
 except Exception:return None
def five_returns(bins,clock=9999):
 by={b[0]:b for b in bins if b[0]+5<=clock};out=[]
 for t in sorted(by):
  if t-5 in by and ((t<690)==(t-5<690)):
   out.append(float(F(str(by[t][4]))/F(str(by[t-5][4]))-1))
 return out
def volatility(rr):return 100*math.sqrt(math.fsum(math.log1p(x)**2 for x in rr)) if len(rr)>=2 else None
def thirty(bins):
 by={b[0]:b for b in bins};best=None
 for a,b in ((540,690),(750,925)):
  for start in range(a,b-29,5):
   bb=[by[t] for t in range(start,start+30,5) if t in by]
   if bb:
    x=float(100*(max(F(str(v[2])) for v in bb)-min(F(str(v[3])) for v in bb))/F(str(bb[0][1])))
    best=x if best is None else max(best,x)
 return best
def current_raw(market,t):
 pp=sorted((r for r in market if r['minute'] in REGULAR and r['minute']+1<=t and actual(r)),key=lambda r:r['minute'])
 prefix={'clock':t,'O':pp[0]['O'] if pp else None,'H':str(max(F(r['H']) for r in pp)) if pp else None,
  'L':str(min(F(r['L']) for r in pp)) if pp else None,'Va':str(sum((F(r['Va']) for r in pp),F(0))),
  'max_source_minute':pp[-1]['minute'] if pp else None}
 by=defaultdict(list)
 for r in pp:by[r['minute']//5*5].append(r)
 bins=[[tm,rs[0]['O'],str(max(F(r['H']) for r in rs)),str(min(F(r['L']) for r in rs)),rs[-1]['C'],None,len(rs)] for tm,rs in sorted(by.items())]
 return prefix,bins
def value_pace(prefix):
 elapsed=sum(t+1<=prefix['clock'] for t in REGULAR)
 return float(F(prefix['Va'])/elapsed) if elapsed else None

def movement_features(r,cal,hist,market):
 dates=sorted(d for d in cal if d<r['session'])[-20:];five=dates[-5:]
 hh=[hist[d,r['symbol']] for d in dates if sufficient(hist.get((d,r['symbol'])))]
 values={f'movement/M{i}':None for i in range(1,17)};values.update({f'movement/I{i}':None for i in range(1,4)})
 ranges20=[v for h in hh if (v:=rp(h.get('daily') or {})) is not None]
 ranges5=[v for h in hh if h['session'] in five and (v:=rp(h.get('daily') or {})) is not None]
 if len(ranges5)>=3:values['movement/M1']=median(ranges5)
 if len(ranges20)>=10:
  values['movement/M2']=median(ranges20);values['movement/M3']=percentile(ranges20,.75);values['movement/M4']=max(ranges20)
  for number,threshold in ((5,3),(6,5),(7,10)):values[f'movement/M{number}']=sum(x>=threshold for x in ranges20)/len(ranges20)
 a5=[];a20=[];pooled=[];vol=[];r30=[];same_range=[];same_pace=[]
 for h in hh:
  ret=five_returns(h['bins']);absret=[100*abs(x) for x in ret]
  if absret:
   a20.append(median(absret));pooled+=absret
   if h['session'] in five:a5.append(median(absret))
  v=volatility(ret);rng=thirty(h['bins'])
  if v is not None:vol.append(v)
  if rng is not None:r30.append(rng)
  pref=h['prefixes'].get(str(r['entry_minute']))
  if pref is None and int(h['active_minute_bitmap_hex'],16)==0:
   pref={'clock':r['entry_minute'],'O':None,'H':None,'L':None,'Va':'0','max_source_minute':None}
  if pref is not None:
   assert pref['max_source_minute'] is None or pref['max_source_minute']<r['entry_minute']
   vr=rp(pref);vp=value_pace(pref)
   if vr is not None:same_range.append(vr)
   if vp is not None:same_pace.append(vp)
 if len(a5)>=3:values['movement/M8']=median(a5)
 if len(a20)>=10:values['movement/M9']=median(a20);values['movement/M10']=percentile(pooled,.9)
 if len(vol)>=10:values['movement/M11']=median(vol)
 if len(r30)>=10:values['movement/M12']=median(r30)
 prefix,bins=current_raw(market,r['entry_minute']);values['movement/M13']=rp(prefix)
 values['movement/M14']=volatility(five_returns(bins,r['entry_minute']))
 if len(same_range)>=10 and median(same_range)>0 and values['movement/M13'] is not None:
  values['movement/M15']=values['movement/M13']/median(same_range)
 if len(same_pace)>=10 and median(same_pace)>0 and value_pace(prefix) is not None:
  values['movement/M16']=value_pace(prefix)/median(same_pace)
 p1=r['numeric']['entry/p1_score'];threshold=r['numeric']['entry/p1_threshold']
 normal=float(p1)/float(threshold) if p1 is not None and threshold is not None and threshold>0 else None
 if normal is not None:
  if values['movement/M2'] is not None:values['movement/I1']=normal*values['movement/M2']
  if values['movement/M15'] is not None:values['movement/I2']=normal*values['movement/M15']
 d=r['numeric']['state/context_direction']
 if d in (-1,0,1) and values['movement/M2'] is not None:values['movement/I3']=d*values['movement/M2']
 return values

def extreme_gate(r,cal,hist):
 dates=sorted(d for d in cal if d<r['session'])[-20:];vv=[];cc=[]
 for day in dates:
  h=hist.get((day,r['symbol']))
  if not sufficient(h) or not h.get('daily'):continue
  try:va=F(str(h['daily']['Va']))
  except Exception:continue
  if va<0:continue
  bits=int(h['active_minute_bitmap_hex'],16);assert bits.bit_length()<=325
  active=sum(bool(bits&(31<<i)) for i in range(0,325,5))
  vv.append(va);cc.append(F(active,65))
 if len(vv)<10:return False,'LIQUIDITY_UNKNOWN',None,len(vv)
 capacity=median(vv)/20;ok=100*F(r['raw_reference'])<=capacity and median(cc)>=F(1,5)
 return ok,'LIQUIDITY_ELIGIBLE' if ok else 'EXTREME_ILLIQUIDITY_REJECT',capacity,len(vv)

def final_execution(r,book):
 if r['entry_minute']>=920:return None,'ENTRY_AFTER_CAPITAL_CUTOFF'
 if not book['capture_complete'] or not book.get('entry_actual_source'):return None,'SOURCE_LINEAGE_BLOCKED'
 x=book['frozen_exit']
 if x['sell_status']=='FILLED' and minute(x['sell_source_assumed_available_at'])<=920:
  row=next((a for a in book['market'] if a['minute']==x['sell_minute']),None)
  if row is None or not actual(row):return None,'FROZEN_EXIT_SOURCE_LINEAGE_BLOCKED'
  price=F(row['O'] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else row['C'])*F(9995,10000)
  assert price==F(x['sell_price_decimal'])
  return (price,'FROZEN_EXIT_V3',minute(x['sell_source_assumed_available_at']),row['minute']),'COMPLETE'
 regular=[a for a in book['market'] if a.get('session')==r['session'] and 920<=a['minute']<925 and actual(a)]
 if regular:
  row=min(regular,key=lambda a:a['minute']);return (F(row['O'])*F(9995,10000),'EOD_REGULAR',row['minute']+1,row['minute']),'COMPLETE'
 auction=[a for a in book['market'] if a.get('session')==r['session'] and a['minute']==930 and actual(a,True)]
 if auction:
  row=auction[0];return (F(row['C'])*F(9995,10000),'EOD_EXACT_1530_AUCTION',931,930),'COMPLETE'
 return None,'EOD_UNEXECUTED_FAIL_CLOSED'

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
 capital=F(1000000);chain=True;ds=[];ts=[];frames=[];days=[];intents=[]
 caps={'HIGH':F(45,100),'MID':F(35,100),'BASE':F(25,100)}
 deploy={'HIGH':F(68,100),'MID':F(56,100),'BASE':F(44,100)}
 for day in sorted({r['session'] for r in stream}):
  opening=capital if chain else F(1000000);cash=opening;held={};scheduled=defaultdict(list);blocked=[];events=defaultdict(list)
  for r in stream:
   if r['session']==day:events[r['entry_minute']].append(r)
  for t in range(540,932):
   for key,p in held.items():
    while p['cursor']<len(p['feed']) and p['feed'][p['cursor']][0]<=t:
     p['known'],p['mark']=p['feed'][p['cursor']];p['cursor']+=1
   for key,fill in sorted(scheduled.pop(t,[])):
    assert key in held
    if fill is None:blocked.append(key);continue
    p=held.pop(key);price,kind,source_minute=fill;debit=p['q']*p['buy'];credit=p['q']*price;cash+=credit
    ts.append({'entry_id':key,'quantity':p['q'],'debit':str(debit),'credit':str(credit),'release_minute':t,'source_minute':source_minute,'exit_kind':kind})
   ranked=sorted(events[t],key=lambda r:(-r['capital_score'],r['entry_timestamp'],r['symbol']));choices=[]
   for r in ranked:
    d={'entry_id':r['entry_id'],'quantity':0,'reason':None};ds.append(d)
    if t>=920:d['reason']='CAPITAL_EOD_ENTRY_CUTOFF'
    elif not r['liquidity']['eligible']:d['reason']=r['liquidity']['reason']
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
     ceiling=equity*caps[b];liquid=F(r['liquidity']['capacity']);desired=budget*F(str(r['capital_score']))/weights
     lots=int(min(desired,ceiling,liquid,remaining)/lot);debit=lots*lot;remaining-=debit;unspent-=debit
     sizes.append({'q':lots*100,'first':lots*100,'lot':lot,'debit':debit,'cap':ceiling,'liquid':liquid,'extra':0,'band':b})
    while True:
     added=0
     for a in sizes:
      if a['first']>=100 and a['lot']<=remaining and a['lot']<=unspent and a['debit']+a['lot']<=min(a['cap'],a['liquid']):
       a['q']+=100;a['debit']+=a['lot'];a['extra']+=1;remaining-=a['lot'];unspent-=a['lot'];added+=1
     if not added:break
    for (r,d),a in zip(selected,sizes):
     if a['q']<100:
      d['reason']='LIQUIDITY_LOT_CAP_REJECT' if a['liquid']<a['lot'] else 'CASH_OR_LOT_CONSTRAINED';continue
     d.update(quantity=a['q'],first_pass_quantity=a['first'],water_fill_lots=a['extra'],reason='FUNDED',debit=str(a['debit']))
     cash-=a['debit'];key=r['entry_id'];book=books[key]
     held[key]={'symbol':r['symbol'],'q':a['q'],'buy':F(r['raw_reference'])*F(10005,10000),'mark':F(r['raw_reference']),
      'known':t,'band':a['band'],'feed':sorted((row['minute']+1,F(row['C'])) for row in book['market'] if row.get('session')==day and row['minute']>=t and actual(row)),'cursor':0}
     assert cash>=0 and len(held)<=n
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
  days.append({'session':day,'starting_cash':str(opening),'ending_cash':str(cash) if valid else None,'primary_chain':chain,'complete':valid})
  if chain and valid:capital=cash
  elif chain:chain=False
 return ds,ts,frames,days,intents

def independent_features(e,trace):
    t=e['fill_minute']
    past=[]
    for row in trace:
        if row['bar_end_minute']<=t:past.append(row)
    def observed(row):
        return (row['state']['current_semantics_observed'] and row['state']['observed_at']==row['state']['as_of']
                and row['state']['numeric_status']=='ACCEPTED' and row['path']['Primary_or_null'] is not None)
    latest=past[-1] if past else None
    known=bool(latest and observed(latest));s=latest['state'] if latest else {};p=latest['path'] if latest else {}
    intent=e['first_intent'];unknown='__UNKNOWN__'
    numeric={
        'entry/p1_score':intent.get('score'),'entry/p1_threshold':intent.get('threshold'),
        'entry/intent_clock':intent.get('intent_minute'),'entry/fill_clock':t,
        'entry/intent_to_fill_active_delay':e.get('intent_to_fill_active_delay'),
        'selector/first_clock':e.get('selector_minute'),'selector/to_intent_active_delay':e.get('selector_to_intent_active_delay'),
        'selector/to_entry_active_delay':e.get('selector_to_entry_active_delay'),
        'selector/raw_entry_vs_first_price_pct':float((F(str(e['fill_price']))/F('1.0005')/F(str(e['selector_price']))-1)*100),
        'state/observed':int(known),'state/context_direction':p.get('context_direction') if known else None,
        'state/local_direction':p.get('local_direction') if known else None,
        'state/fast_applicable':int(p.get('fast_applicable_to_primary',False)) if known else None,
        'state/stop_count':(s.get('stop') or {}).get('count') if known else None,
        'path/dwell_observed_bars':p.get('dwell_observed_bars') if known else None,
        'path/dwell_scheduled_bars':p.get('dwell_scheduled_bars') if known else None,
    }
    changes=[];breaks=losses=0
    for row in past:
        for event in row.get('path_events',[]):
            if event['event_type']=='TRANSITION':changes.append(row['bar_end_minute'])
            elif event['event_type']=='SEGMENT_BREAK':breaks+=1
            elif event['event_type']=='OBSERVATION_LOST':losses+=1
    numeric.update({'path/transitions_total':len(changes),'path/segment_breaks_total':breaks,
        'path/observation_losses_total':losses,'path/observed_prefix_rows':sum(observed(row) for row in past),
        'path/last_transition_age_minutes':t-changes[-1] if changes else None})
    for width in (15,30,60):
        numeric[f'path/transitions_{width}m']=sum(t-width<m<=t for m in changes)
        numeric[f'path/observed_rows_{width}m']=sum(t-width<row['bar_end_minute']<=t and observed(row) for row in past)
    start=len(past)
    if known:
        start=len(past)-1
        while start>0:
            a,b=past[start-1],past[start]
            if not observed(a) or a['path']['causal_segment_id']!=b['path']['causal_segment_id'] or a['path']['scheduled_t']+1!=b['path']['scheduled_t']:break
            start-=1
    seq=[]
    for row in past[start:]:
        if not seq or row['path']['Primary_or_null']!=seq[-1]:seq.append(row['path']['Primary_or_null'])
    categories={'state/current_primary':p.get('Primary_or_null') if known else unknown,
        'state/activity':s.get('activity',unknown),'state/basis':s.get('basis',unknown),
        'state/direction_basis':s.get('direction_basis',unknown) if known else unknown,
        'state/fast':str(p.get('fast')) if known and p.get('fast') is not None else unknown,
        'state/numeric_status':s.get('numeric_status',unknown),
        'path/last3_connected_primary':'>'.join(seq[-3:]) if seq else unknown}
    return numeric,categories

def main():
 runtime=read(P/'RUNTIME_CAUSAL.jsonl.gz');teacher={r['entry_id']:r for r in read(P/'TEACHERS_EVALUATION.jsonl.gz')}
 books={r['entry_id']:r for r in read(ROOT.parent/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
 scope=json.loads((ROOT/'research/capital-bigwinner-one-shot-20261004-v1/SOURCE_RECOVERY_SCOPE.json').read_text());cal=set(scope['required_prior_dates']+scope['entry_cohort_dates'])
 source_dir=ROOT.parent/'work_inputs/movement_v2_source';receipt=json.loads((source_dir/'MOVEMENT_SOURCE_RECEIPT.json').read_text());hist={}
 for p in receipt['shards']:
  raw=(source_dir/p['filename']).read_bytes();assert hashlib.sha256(raw).hexdigest()==p['sha256']
  for r in json.loads(gzip.decompress(raw)):hist[r['session'],r['symbol']]=r
 entries={r['watch_key']:r for r in read(ROOT.parent/'work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if r['entry_status']=='FIRST_ENTRY'}
 counts=Counter();mismatches=[]
 def check(kind,ok,detail=None):
  counts[kind]+=1
  if not ok:mismatches.append({'kind':kind,'detail':detail})
 for r in runtime:
  trace=read(ROOT.parent/f"work_inputs/exit_v2/FULL_TRACE/{r['session']}_{r['symbol']}.jsonl.gz")
  core,cat=independent_features(entries[r['entry_id']],trace)
  for k,v in core.items():
   z=r['numeric'][k];check('core_numeric',v==z if v is None or z is None else abs(float(v)-float(z))<1e-12,r['entry_id']+':'+k)
  check('core_categories',cat==r['categorical'])
  mm=movement_features(r,cal,hist,books[r['entry_id']]['market'])
  for k,v in mm.items():
   z=r['numeric'][k];check('movement_numeric',v==z if v is None or z is None else abs(v-z)<=1e-11*max(1,abs(v),abs(z)),r['entry_id']+':'+k)
  eligible,reason,cap,support=extreme_gate(r,cal,hist)
  check('extreme_veto',eligible==r['liquidity']['eligible'] and reason==r['liquidity']['reason'] and support==r['liquidity']['support'],r['entry_id'])
  check('liquidity_cap',cap is None and r['liquidity']['capacity'] is None or cap is not None and cap==F(r['liquidity']['capacity']))
  future=[x for x in books[r['entry_id']]['market'] if r['entry_minute']<x['minute']<920 and actual(x)]
  best=max((F(x['H']) for x in future),default=F(r['raw_reference']));p=int(best/F(r['raw_reference'])-1>=F(5,100)) if future else 0 if books[r['entry_id']]['capture_complete'] else None
  check('potential_teacher',p==teacher[r['entry_id']]['label_bigwinner5'])
  fill,status=final_execution(r,books[r['entry_id']]);net=fill[0]/(F(r['raw_reference'])*F(10005,10000))-1 if fill else None
  check('realized_teacher',(int(net>0) if net is not None else None)==teacher[r['entry_id']]['label_realized_positive'])
  check('realized_source',status==teacher[r['entry_id']]['execution_status'])
  if net is not None:check('realized_net',abs(float(net)-teacher[r['entry_id']]['realized_net_return'])<1e-12)
 models={}
 for path in sorted((P/'models').glob('*.json')):
  m=json.loads(path.read_text());models[m['head'],m['block']]=m
  label='label_realized_positive' if m['head']=='MOVE_R' else 'label_bigwinner5'
  train=[r for r in runtime if r['session']<=m['train_through'] and r['entry_minute']<920 and teacher[r['entry_id']][label] is not None]
  check('fit_prefix',[r['entry_id'] for r in train]==m['train_entry_ids'])
  check('temporal_boundary',max(r['session'] for r in train)<min(m['test_dates']))
  check('training_baseline',sum(teacher[r['entry_id']][label] for r in train)/len(train)==m['base_rate'])
  prep=m['preprocessing'];a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in prep['numeric_fields']] for r in train])
  a=np.column_stack([np.nan_to_num(a,nan=0),np.isnan(a).astype(float)]);sc=a.std(axis=0);sc[sc==0]=1
  check('train_only_mean',np.max(np.abs(a.mean(axis=0)-prep['numeric_mean']))<1e-12)
  check('train_only_scale',np.max(np.abs(sc-prep['numeric_scale']))<1e-12)
  for k in prep['categorical_fields']:check('train_only_vocabulary',sorted({r['categorical'][k] or '__UNKNOWN__' for r in train}|{'__UNKNOWN__'})==prep['categorical_train_vocab'][k])
 check('fixed_fit_count',len(models)==24)
 max_diff=0
 for arm in ARMS:
  stream=read(P/(arm+'_SCORE_STREAM.jsonl.gz'))
  for r in stream:
   pm=models['CORE_P' if arm=='CORE_P5' else 'MOVE_P',r['block']];pp=scalar_probability(r,pm);max_diff=max(max_diff,abs(pp-r['pP']))
   check('scalar_P',abs(pp-r['pP'])<1e-12)
   sc=pp/pm['base_rate']
   if arm=='MOVE_DUAL':
    rm=models['MOVE_R',r['block']];pr=scalar_probability(r,rm);max_diff=max(max_diff,abs(pr-r['pR']))
    check('scalar_R',abs(pr-r['pR'])<1e-12);sc=math.sqrt(sc*pr/rm['base_rate'])
   check('continuous_score',abs(sc-r['capital_score'])<1e-11)
   check('capacity_band',capacity_band(sc)==r['capacity_band'])
  for n in (3,4,5):
   label=f'{arm}_MAX{n}';ds,ts,cs,days,intents=replay(n,stream,books)
   pd=read(P/(label+'_DECISIONS.jsonl.gz'));pt=read(P/(label+'_TRADES.jsonl.gz'));pc=read(P/(label+'_CURVE.jsonl.gz'));pi=read(P/(label+'_INTENTS.jsonl.gz'))
   check('decision_count',len(ds)==len(pd))
   for a,b in zip(ds,pd):
    check('funding',all(a[k]==b[k] for k in ('entry_id','quantity','reason')),label+':'+a['entry_id'])
    if a['quantity']:
     check('water_fill',a['first_pass_quantity']==b['first_pass_quantity'] and a['water_fill_lots']==b['water_fill_lots'])
     check('BUY_debit',F(a['debit'])==F(b['debit']))
   check('trade_count',len(ts)==len(pt))
   for a,b in zip(ts,pt):
    check('SELL',all(a[k]==b[k] for k in ('entry_id','quantity','release_minute','source_minute','exit_kind')))
    check('trade_cash',F(a['debit'])==F(b['debit']) and F(a['credit'])==F(b['credit']))
   check('curve_count',len(cs)==len(pc))
   for a,b in zip(cs,pc):
    check('exact_cash_equity',F(a['cash'])==F(b['cash']) and F(a['equity'])==F(b['equity']) and a['concurrent']==b['concurrent'],label+':'+a['session']+':'+str(a['minute']))
    check('causal_marks',a['known_marks']==b['known_marks'])
   primary=json.loads((P/(label+'_RESULT.json')).read_text())['daily_series']
   for a,b in zip(days,primary):check('daily_endpoint',a['primary_chain']==b['primary_chain'] and a['complete']==(b['status']=='COMPLETE') and (a['ending_cash']==b['ending_cash'] if a['ending_cash'] is None or b['ending_cash'] is None else F(a['ending_cash'])==F(b['ending_cash'])))
   check('EOD_intent_count',len(intents)==len(pi))
   for a,b in zip(intents,pi):check('EOD_intent',all(a[k]==b[k] for k in ('entry_id','quantity','minute','limit_up_status')))
   output(P/(label+'_INDEPENDENT_ENDPOINTS.json'),days)
 report={'status':'PASS' if not mismatches else 'FAIL','mismatch_N':len(mismatches),
  'mismatch_categories':dict(Counter(m['kind'] for m in mismatches)),'checks_N':sum(counts.values()),'checks':dict(counts),
  'independent_profiles':9,'independent_fit_count':0,'Primary_logic_imported':False,
  'max_scalar_probability_abs_difference':max_diff,'cash_arithmetic':'Exact Fraction compared to Primary Decimal as rational equality',
  'shared_IO_limit':'Saved provider5m/prefix aggregates,Frozen Entry/State/Path/EXIT and24 fixed fitted artifacts shared. No independent external market source or production certification.',
  'future_suffix_runtime_inputs':False,'productionReady':False}
 output(OUT/'INDEPENDENT_AUDIT.json',report)
 if mismatches:output(P/'INDEPENDENT_MISMATCH_DETAILS.json',mismatches)
 print(json.dumps(report));assert not mismatches,'PRIMARY_INDEPENDENT_MISMATCH'

if __name__=='__main__':main()
