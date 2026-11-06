"""New fixed representations from raw and frozen State prefix; no legacy bundle."""
import math
from decimal import Decimal, InvalidOperation
from common import *

def valid_raw(r):
 try:
  if not r.get('lineage'):return False
  if any(isinstance(r.get(k),bool) or r.get(k) is None for k in ['O','H','L','C','Vo','Va']):return False
  o,h,l,c,v,a=[Decimal(str(r[k])) for k in ['O','H','L','C','Vo','Va']]
  return all(x.is_finite() for x in [o,h,l,c,v,a]) and l>0 and l<=min(o,c)<=max(o,c)<=h and v>=0 and a>=0
 except (KeyError,TypeError,ValueError,InvalidOperation):return False

def state_valid(r):
 s,p=r['state'],r['path'];t=r['bar_end_minute']
 return bool(s['current_semantics_observed'] is True and p['current_semantics_observed'] is True and s['observed_at']==s['as_of']==t-540 and p['quality']['numeric_status']=='ACCEPTED' and p['Primary_or_null'] in STATES and r['source_status']=='RAW_CLOSED_AT_ASSUMED_BAR_END' and s.get('activity')!='CARRIED_GAP' and s.get('basis')!='CARRIED_GAP')

def trace_prefix(trace,key,day,t):
 out=[]
 for r in trace:
  m=r['bar_end_minute']
  if m>t:continue
  assert r['watch_key']==r['state']['case_id']==r['path']['case_id']==key
  assert r['assumed_available_at']==stamp(day,m)==r['path']['bar_end']
  assert r['state']['as_of']==r['path']['scheduled_t']==m-540
  a=r['input'];assert a is None or a['known_at']<=m-540 and a['t']<=m-540
  out.append(r)
 assert all(out[i]['bar_end_minute']<out[i+1]['bar_end_minute'] for i in range(len(out)-1))
 return out

def raw_series(market,prefix,day,t):
 sched=[m+1 for m in regular_starts() if m+1<=t];by={}
 for r in market:
  if r.get('session')!=day or r['minute']+1>t or r['minute'] not in regular_starts():continue
  if r['minute'] in by:raise AssertionError('DUPLICATE_RAW_MINUTE')
  by[r['minute']]=r
 trace={r['bar_end_minute']:r for r in prefix};items=[];seg=0;prev=None;breaks=[]
 for ctime in sched:
  r=by.get(ctime-1)
  if r is None or not valid_raw(r):prev=None;continue
  tr=trace.get(ctime);resets=(tr or {}).get('path',{}).get('quality',{}).get('reset_reasons',[])
  boundary=bool(items and (prev is None or ctime!=prev['close_time']+1 or resets))
  if boundary:seg+=1;breaks.append(ctime)
  v={k:float(Decimal(str(r[k]))) for k in ['O','H','L','C','Vo','Va']}
  item={'close_time':ctime,'segment':seg,**v,'lineage':r['lineage']};items.append(item);prev=item
 return sched,items,breaks

def quality_category(r,valid):
 if r is None:return 'UNKNOWN'
 s,p=r['state'],r['path'];q=p['quality'];reset=q.get('reset_reasons') or []
 if reset:return 'RESET:'+'|'.join(sorted(set(reset)))
 if r.get('source_unavailable_reason'):return 'SOURCE_UNAVAILABLE'
 if s.get('activity') in ['INITIALIZING','CARRIED_GAP']:return s['activity']
 if q.get('reason'):return q['reason']
 return 'OBSERVED_VALID' if valid else 'QUALITY_ABSTAIN'

def compute(key,day,t,market,trace,evidence_present=True):
 prefix=trace_prefix(trace,key,day,t) if evidence_present else []
 sched,raw,rb=raw_series(market,prefix,day,t)
 x={k:None for k in PRICE+STATE};cats={k:'UNKNOWN' for k in CAT};av=[];reasons={}
 for w in [5,20,60]:
  times=sched[-w:];a=[r for r in raw if r['close_time'] in times];n=len(a);pre=f'PRICE/w{w}/';x[pre+'coverage']=n/len(times) if times else 0.
  pairs=[(a[i-1],a[i]) for i in range(1,n) if a[i]['segment']==a[i-1]['segment'] and a[i]['close_time']==a[i-1]['close_time']+1]
  rets=[math.log(b['C']/aa['C']) for aa,b in pairs]
  if n:
   c=a[-1]['C'];hi=max(r['H'] for r in a);lo=min(r['L'] for r in a)
   for name,val in [('net_log',math.log(c/a[0]['O'])),('range_log',math.log(hi/lo)),('from_high_log',math.log(c/hi)),('from_low_log',math.log(c/lo)),('mean_volume_log1p',math.log1p(sum(r['Vo'] for r in a)/n)),('mean_value_log1p',math.log1p(sum(r['Va'] for r in a)/n))]:x[pre+name]=val
   av.extend(r['close_time'] for r in a)
  if pairs:
   ab=sum(abs(r) for r in rets);x[pre+'signed_efficiency']=sum(rets)/ab if ab else 0.
   x[pre+'return_rms']=math.sqrt(sum(r*r for r in rets)/len(rets));x[pre+'down_pair_rate']=sum(r<0 for r in rets)/len(rets)
   vv=sum(b['Vo'] for aa,b in pairs);x[pre+'down_volume_share']=sum(b['Vo'] for (aa,b),rt in zip(pairs,rets) if rt<0)/vv if vv>0 else None
   segments={}
   for r in a:segments.setdefault(r['segment'],[]).append(r['C'])
   dd=[]
   for vals in segments.values():
    if len(vals)<2:continue
    high=vals[0]
    for c in vals:high=max(high,c);dd.append(math.log(c/high))
   x[pre+'close_drawdown']=min(dd) if dd else None
  if not pairs:
   for name in ['signed_efficiency','return_rms','close_drawdown','down_pair_rate','down_volume_share']:reasons[pre+name]='NO_VALID_ADJACENT_PAIR'
 if raw:
  last=raw[-1];den=last['H']-last['L'];x['PRICE/flat']=int(den==0)
  for name,val in [('body',last['C']-last['O']),('upper_wick',last['H']-max(last['O'],last['C'])),('lower_wick',min(last['O'],last['C'])-last['L'])]:x['PRICE/'+name]=val/den if den else 0.
  x['PRICE/raw_age']=active(t)-active(last['close_time'])
 for typ,col in [('volume','Vo'),('value','Va')]:
  aa=[r for r in raw if r['close_time'] in sched[-5:]];bb=[r for r in raw if r['close_time'] in sched[-20:]]
  v=sum(r[col] for r in aa)/len(aa) if aa else None;z=sum(r[col] for r in bb)/len(bb) if bb else None
  x[f'PRICE/{typ}5_20_log']=math.log(v/z) if v is not None and z is not None and v>0 and z>0 else None
 x['PRICE/active_minutes']=active(t);x['PRICE/raw_breaks60']=sum(tm in sched[-60:] for tm in rb)
 # Saved checkpoint schedule includes terminal/lunch-boundary slots; regular
 # representation uses only the pinned regular-minute close set.
 regular=[r for r in prefix if r['bar_end_minute'] in sched];tb={r['bar_end_minute']:r for r in regular}
 expected_gap=[tm for tm in sched if tm not in tb] if evidence_present else sched
 state_evidence_ok=bool(evidence_present and not expected_gap)
 connected=[];last_valid=None
 for tm in sched:
  r=tb.get(tm)
  if r and state_valid(r):
   if connected and (tm!=connected[-1]['bar_end_minute']+1 or r['path']['causal_segment_id']!=connected[-1]['path']['causal_segment_id']):connected=[]
   connected.append(r);last_valid=r
  else:connected=[]
 for w in [20,60]:
  times=sched[-w:];a=[tb[tm] for tm in times if tm in tb and state_valid(tb[tm])];n=len(a);pre=f'STATE/w{w}/'
  for name in STATES:x[pre+name]=sum(r['path']['Primary_or_null']==name for r in a)/n if n else None
  x[pre+'coverage']=n/len(times) if times else 0.
  changes=0;previous=None
  for tm in times:
   r=tb.get(tm)
   if not r or not state_valid(r):previous=None;continue
   if previous and tm==previous['bar_end_minute']+1 and r['path']['causal_segment_id']==previous['path']['causal_segment_id'] and r['path']['Primary_or_null']!=previous['path']['Primary_or_null']:changes+=1
   previous=r
  x[pre+'transitions']=changes
 current=prefix[-1] if prefix else None;observed=bool(current and current['bar_end_minute'] in sched and state_valid(current));qc=quality_category(current,observed)
 cats[CAT[3]]=qc if qc in VOCAB[CAT[3]] else 'UNKNOWN'
 if observed:
  cats[CAT[0]]=current['path']['Primary_or_null'];runs=[]
  for r in connected:
   state=r['path']['Primary_or_null']
   if not runs or runs[-1][0]!=state:runs.append((state,r['bar_end_minute']))
  cats[CAT[1]]=runs[-2][0] if len(runs)>1 else 'START';cats[CAT[2]]=runs[-3][0] if len(runs)>2 else 'START'
  x['STATE/run_duration']=active(t)-active(runs[-1][1])
 else:
  a=(current or {}).get('state',{}).get('activity')
  cats[CAT[0]]=a if a in ['INITIALIZING','CARRIED_GAP'] else 'SOURCE_UNAVAILABLE' if current and current.get('source_unavailable_reason') else 'QUALITY_ABSTAIN' if current else 'START'
 if last_valid:x['STATE/last_valid_age']=active(t)-active(last_valid['bar_end_minute'])
 x['STATE/breaks60']=sum(ev['event_type']=='SEGMENT_BREAK' for r in regular if r['bar_end_minute'] in sched[-60:] for ev in r.get('path_events',[]))
 assert list(x)==PRICE+STATE and len(PRICE)==45 and len(STATE)==25
 for k,v in x.items():
  assert v is None or math.isfinite(v),'NONFINITE_FEATURE:'+k
  if v is None:reasons.setdefault(k,'NO_VALID_OBSERVATIONS_OR_UNDEFINED_RATIO')
 state_max=max((r['bar_end_minute'] for r in prefix),default=None)
 return {'entry_id':key,'session':day,'intent_minute':t,'feature_asof':stamp(day,t),'numeric':x,'categorical':cats,'price_available':bool(raw),'state_evidence_ok':state_evidence_ok,'state_evidence_gaps':expected_gap,'quality_raw_category_unmapped':qc if qc not in VOCAB[CAT[3]] else None,'max_raw_available_at':stamp(day,max(av)) if av else None,'max_state_available_at':stamp(day,state_max) if state_max else None,'last_raw_reference_close':str(raw[-1]['C']) if raw else None,'missing_reason':reasons,'availability_assumption':'HISTORICAL_BAR_END_AND_FROZEN_STAGE_ORDER; ACTUAL_ARRIVAL_UNKNOWN'}
