"""Fixed movement definitions. Raw actual bars only; no synthetic or carried OHLC."""
from collections import defaultdict
from decimal import Decimal
import math
from statistics import median

MOVEMENT=[f'M{i}' for i in range(1,17)]
INTERACTIONS=['I1','I2','I3']
MOVEMENT_KEYS=['movement/'+k for k in MOVEMENT+INTERACTIONS]
REGULAR=list(range(540,690))+list(range(750,925))

def quantile(values,p):
 v=sorted(values)
 if not v:return None
 x=(len(v)-1)*p;i=int(x);f=x-i
 return v[i] if i==len(v)-1 else v[i]*(1-f)+v[i+1]*f

def valid(r):
 try:
  a={k:Decimal(str(r[k])) for k in ('O','H','L','C','Vo','Va')}
  return bool(r.get('lineage')) and all(x.is_finite() and x>0 for x in a.values()) and a['L']<=min(a['O'],a['C'])<=max(a['O'],a['C'])<=a['H']
 except (KeyError,ValueError,TypeError,ArithmeticError):return False

def raw_bins(market):
 grouped=defaultdict(list)
 for r in market:
  if r['minute'] in REGULAR and valid(r):grouped[(r['minute']//5)*5].append(r)
 result=[]
 for t,rows in sorted(grouped.items()):
  rows=sorted(rows,key=lambda r:r['minute'])
  result.append([t,rows[0]['O'],str(max(Decimal(r['H']) for r in rows)),
   str(min(Decimal(r['L']) for r in rows)),rows[-1]['C'],
   str(sum((Decimal(r['Va']) for r in rows),Decimal(0))),len(rows)])
 return result

def raw_prefix(market,t):
 # Bar_end = minute+1; only completed bars known at Entry are retained.
 rr=sorted([r for r in market if r['minute'] in REGULAR and r['minute']+1<=t and valid(r)],key=lambda r:r['minute'])
 if not rr:return {'clock':t,'O':None,'H':None,'L':None,'Va':'0','trade_minutes':0,'max_source_minute':None}
 return {'clock':t,'O':rr[0]['O'],'H':str(max(Decimal(r['H']) for r in rr)),
  'L':str(min(Decimal(r['L']) for r in rr)), 'Va':str(sum((Decimal(r['Va']) for r in rr),Decimal(0))),
  'trade_minutes':len(rr),'max_source_minute':rr[-1]['minute']}

def bitmap(market):
 actual={r['minute'] for r in market if r['minute'] in REGULAR and valid(r)}
 bits=sum(1<<i for i,t in enumerate(REGULAR) if t in actual)
 return format(bits,'082x')

def activity(bits_hex):
 bits=int(bits_hex,16);active=[bool(bits&(1<<i)) for i in range(325)]
 longest=0
 for a,b in ((0,150),(150,325)):
  run=0
  for flag in active[a:b]:
   run=0 if flag else run+1;longest=max(longest,run)
 return {'active_5m_N':sum(any(active[i:i+5]) for i in range(0,325,5)),
  'actual_trade_minute_N':sum(active),'max_consecutive_no_trade_minutes':longest}

def returns5(bins,clock=None):
 bb=[b for b in bins if clock is None or b[0]+5<=clock]
 ret=[]
 for a,b in zip(bb,bb[1:]):
  if b[0]-a[0]!=5 or (a[0]<690)!=(b[0]<690):continue
  ret.append(float(Decimal(b[4])/Decimal(a[4])-1))
 return ret

def rv(ret):return 100*math.sqrt(sum(math.log1p(r)**2 for r in ret)) if len(ret)>=2 else None

def range_pct(r):
 try:
  o,h,l=[Decimal(str(r[k])) for k in ('O','H','L')]
  if not all(x.is_finite() and x>0 for x in (o,h,l)) or h<l:return None
  return float(100*(h-l)/o)
 except (KeyError,ValueError,TypeError,ArithmeticError):return None

def pace(prefix):
 t=prefix['clock'];elapsed=sum(m+1<=t for m in REGULAR)
 if elapsed<=0:return None
 try:return float(Decimal(prefix['Va'])/elapsed)
 except (KeyError,ValueError,TypeError,ArithmeticError):return None

def max30(bins):
 by={b[0]:b for b in bins};values=[]
 for start,end in ((540,690),(750,925)):
  for t in range(start,end-29,5):
   bb=[by[m] for m in range(t,t+30,5) if m in by]
   if not bb:continue
   o=Decimal(bb[0][1]);hi=max(Decimal(b[2]) for b in bb);lo=min(Decimal(b[3]) for b in bb)
   values.append(float(100*(hi-lo)/o))
 return max(values) if values else None

def complete(record):
 return bool(record and all(record.get(k,{}).get('date_scope_complete') and record.get(k,{}).get('terminal_pagination_proven') for k in ('daily_source','minute_source')))

def project(core,history,calendar,current_market):
 day=core['session'];code=core['symbol'];t=core['entry_minute']
 prior20=[d for d in calendar if d<day][-20:];prior5=prior20[-5:]
 hist=[history[(d,code)] for d in prior20 if complete(history.get((d,code)))]
 assert all(r['session']<day for r in hist)
 d20=[v for r in hist if (v:=range_pct(r.get('daily') or {})) is not None]
 d5=[v for r in hist if r['session'] in prior5 and (v:=range_pct(r.get('daily') or {})) is not None]
 out={k:None for k in MOVEMENT_KEYS}
 if len(d5)>=3:out['movement/M1']=median(d5)
 if len(d20)>=10:
  out.update({'movement/M2':median(d20),'movement/M3':quantile(d20,.75),'movement/M4':max(d20),
   **{f'movement/M{i}':sum(v>=threshold for v in d20)/len(d20) for i,threshold in ((5,3),(6,5),(7,10))}})
 abs5=[];abs20=[];pooled=[];vol=[];ranges30=[]
 for r in hist:
  ret=returns5(r['bins']);a=[abs(x)*100 for x in ret]
  if a:
   abs20.append(median(a));pooled+=a
   if r['session'] in prior5:abs5.append(median(a))
  v=rv(ret);r30=max30(r['bins'])
  if v is not None:vol.append(v)
  if r30 is not None:ranges30.append(r30)
 if len(abs5)>=3:out['movement/M8']=median(abs5)
 if len(abs20)>=10:out['movement/M9']=median(abs20);out['movement/M10']=quantile(pooled,.9)
 if len(vol)>=10:out['movement/M11']=median(vol)
 if len(ranges30)>=10:out['movement/M12']=median(ranges30)
 # Slice raw bars BEFORE reading any future OHLC or Va value.
 past=[r for r in current_market if r['minute']+1<=t]
 prefix=raw_prefix(past,t);current_bins=raw_bins(past)
 out['movement/M13']=range_pct(prefix)
 out['movement/M14']=rv(returns5(current_bins,t))
 ranges=[];paces=[]
 for r in hist:
  pref=r['prefixes'].get(str(t))
  if pref is None:continue
  assert pref['max_source_minute'] is None or pref['max_source_minute']+1<=t
  ra=range_pct(pref);pa=pace(pref)
  if ra is not None:ranges.append(ra)
  if pa is not None:paces.append(pa)
 if len(ranges)>=10 and median(ranges)>0 and out['movement/M13'] is not None:
  out['movement/M15']=out['movement/M13']/median(ranges)
 if len(paces)>=10 and median(paces)>0 and pace(prefix) is not None:
  out['movement/M16']=pace(prefix)/median(paces)
 p1=core['numeric']['entry/p1_score'];th=core['numeric']['entry/p1_threshold']
 normalized=float(p1)/float(th) if p1 is not None and th is not None and float(th)>0 else None
 if normalized is not None:
  if out['movement/M2'] is not None:out['movement/I1']=normalized*out['movement/M2']
  if out['movement/M15'] is not None:out['movement/I2']=normalized*out['movement/M15']
 direction=core['numeric']['state/context_direction']
 if direction in (-1,0,1) and out['movement/M2'] is not None:
  out['movement/I3']=direction*out['movement/M2']
 return out,{'prior20_calendar_dates':prior20,'prior5_calendar_dates':prior5,'valid_daily20':len(d20),
  'valid_daily5':len(d5),'valid_intraday20':len(abs20),'valid_sameclock_range':len(ranges),
  'valid_sameclock_pace':len(paces),'current_max_source_minute':prefix['max_source_minute'],
  'current_closed_5m_bin_N':sum(b[0]+5<=t for b in current_bins),'normalization_P1':'score / Frozen positive threshold; not probability',
  'normalization_direction':'Authoritative Path context_direction -1/0/+1 retained without state mapping'}
