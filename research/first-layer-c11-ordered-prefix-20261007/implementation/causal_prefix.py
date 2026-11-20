"""Pure C10 pre-buy representation: no files, labels, outcomes or daily futures."""
import datetime as dt
import math

def regular(m):return 540<=m<690 or 750<=m<925
def active(a,b):return max(0,min(b,690)-max(a,540))+max(0,min(b,925)-max(a,750))
def adjacent(a,b):return b-a==1 and ((a<690 and b<690) or (a>=750 and b>=750))
def mean(v):return sum(v)/len(v) if v else None
def ratio(a,b):return a/b if a is not None and b is not None and b!=0 else None
def lg(a,b):return math.log(a/b) if a is not None and b is not None and a>0 and b>0 else None
def bar_check(b):
 if len(b)!=7 or not all(math.isfinite(float(v)) for v in b) or not isinstance(b[0],int) or min(b[1:5])<=0 or min(b[5:])<0 or b[2]<b[3]:raise ValueError('INVALID_BAR')

def identity_check(i):
 if set(i)!={'entry_id','session','symbol','decision_time','cutoff_minute'}:raise ValueError('UNAUTHORIZED_IDENTITY_CAPABILITY')
 if i['entry_id']!=i['session']+'|'+i['symbol']:raise ValueError('SECURITY_DATE_JOIN')
 t=dt.datetime.fromisoformat(i['decision_time'])
 if t.date().isoformat()!=i['session'] or t.hour*60+t.minute!=i['cutoff_minute']:raise ValueError('CUTOFF_IDENTITY')
 if not 540<=i['cutoff_minute']<=925:raise ValueError('OUTSIDE_ENTRY_SESSION')

def prefix_view(identity,raw_bars):
 """Inspect only timestamps until eligibility is known; future payload unreadable."""
 identity_check(identity);cut=identity['cutoff_minute'];out=[]
 for b in raw_bars:
  m=b[0]
  if m+1<=cut:
   row=[m]+[b[j] for j in range(1,7)];bar_check(row);out.append(row)
 out.sort(key=lambda b:b[0])
 if len({b[0] for b in out})!=len(out):raise ValueError('DUPLICATE_BAR_ORDERING')
 return out

def _rv(bars):
 ds=[math.log(y[4]/x[4]) for x,y in zip(bars,bars[1:]) if adjacent(x[0],y[0])]
 return math.sqrt(sum(v*v for v in ds)) if ds else None

def _range(bars):return lg(max(b[2] for b in bars),min(b[3] for b in bars)) if bars else None

def _slope(bars):
 if len(bars)<2:return None
 x=[active(540,b[0]+1) for b in bars];y=[math.log(b[4]) for b in bars];xm=mean(x);ym=mean(y)
 den=sum((v-xm)**2 for v in x)
 return sum((a-xm)*(b-ym) for a,b in zip(x,y))/den if den>0 else None

def build_direct(case):
 if set(case)!={'identity','prefix','authorized_past_sessions','past'}:raise ValueError('UNAUTHORIZED_CHART_CAPABILITY')
 ident=case['identity'];identity_check(ident);cut=ident['cutoff_minute'];bars=case['prefix']
 # Whole-prefix values retain all authoritative already completed observations.
 # Scheduled rolling slots remain regular-only; native 11:30 bars are not erased.
 for b in bars:
  if b[0]+1>cut:raise ValueError('POST_BUY_INTENT_CAPABILITY')
  bar_check(b)
 if any(a[0]>=b[0] for a,b in zip(bars,bars[1:])):raise ValueError('UNORDERED_OR_DUPLICATE_PREFIX')
 dates=case['authorized_past_sessions'];past=case['past']
 if len(dates)>5 or len(set(dates))!=len(dates) or dates!=sorted(dates) or any(d>=ident['session'] for d in dates):raise ValueError('PAST_DATE_CAPABILITY')
 if set(past)!={d+'|'+ident['symbol'] for d in dates}:raise ValueError('PAST_SECURITY_JOIN')
 for d in dates:
  row=past[d+'|'+ident['symbol']]
  if set(row)!={'key','session','bars'} or row['key']!=d+'|'+ident['symbol'] or row['session']!=d:raise ValueError('PAST_SECURITY_DATE_JOIN')
  for b in row['bars']:bar_check(b)
  if any(a[0]>=b[0] for a,b in zip(row['bars'],row['bars'][1:])):raise ValueError('PAST_ORDERING')
 half=750 if cut>=750 else 540;elapsed=active(half,cut);out={};put=lambda n,v:out.__setitem__('C10.'+n,v)
 put('elapsed_active_minutes',float(active(540,cut)));put('active_minutes_in_half',float(elapsed))
 windows={h:[b for b in bars if regular(b[0]) and b[0]>=max(half,cut-h)] for h in [1,3,5,10,20,30,60]}
 latest=bars[-1][4] if bars else None;first=bars[0] if bars else None
 for h,w in windows.items():
  den=min(h,elapsed);put(f'window{h}.support_fraction',len(w)/den if den else None);put(f'window{h}.short_history',float(elapsed<h))
  endpoint=next((b[4] for b in bars if b[0]+1==cut),None)
  anchor=next((b[4] for b in bars if b[0]+1==cut-h and b[0]>=half),None)
  if half==540 and cut-h==540:anchor=next((b[1] for b in bars if b[0]==540),None)
  put(f'return{h}',lg(endpoint,anchor) if elapsed>=h else None)
 for h in [5,10,20,30]:put(f'slope{h}',_slope(windows[h]));put(f'rv{h}',_rv(windows[h]))
 for a,b in [(5,20),(10,30)]:
  x=out['C10.slope'+str(a)];y=out['C10.slope'+str(b)];put(f'acceleration{a}_{b}',x-y if x is not None and y is not None else None);put(f'range_ratio{a}_{b}',ratio(_range(windows[a]),_range(windows[b])))
 hi=max(b[2] for b in bars) if bars else None;lo=min(b[3] for b in bars) if bars else None
 gross=abs(math.log(first[4]/first[1]))+sum(abs(math.log(y[4]/x[4])) for x,y in zip(bars,bars[1:])) if first else None
 net=lg(latest,first[1]) if first else None;vol=sum(b[5] for b in bars);val=sum(b[6] for b in bars)
 vwok=all(b[5]==0 and b[6]==0 or b[5]>0 and b[3]-max(1e-8,1e-6*b[3])<=b[6]/b[5]<=b[2]+max(1e-8,1e-6*b[2]) for b in bars)
 vw=val/vol if vwok and vol>0 and val>0 else None
 for n,v in {'prefix.observed_count':float(len(bars)) if bars else None,'prefix.support_fraction':sum(regular(b[0]) for b in bars)/active(540,cut) if bars and active(540,cut)>0 else None,'prefix.range_position':ratio(latest-lo,hi-lo) if bars else None,'prefix.distance_high':lg(latest,hi),'prefix.distance_low':lg(latest,lo),'prefix.net_movement':net,'prefix.observed_range':lg(hi,lo),'prefix.price_vwap_distance':lg(latest,vw),'prefix.mean_volume':mean([b[5] for b in bars]),'prefix.mean_value':mean([b[6] for b in bars]),'prefix.running_high':hi,'prefix.running_low':lo,'prefix.gross_observed_movement':gross,'prefix.observed_path_efficiency':ratio(net,gross),'prefix.observed_vwap':vw}.items():put(n,v)
 for h in [5,10,20]:
  w=windows[h];early=[b for b in bars if b[0]<max(half,cut-h)]
  for a,j in [('volume',5),('value',6)]:
   recent=mean([b[j] for b in w]);r=ratio(recent,mean([b[j] for b in early]));put(f'window{h}.mean_{a}',recent);put(f'{a}_ratio{h}',r)
   if h in [5,20]:
    ret=out[f'C10.return{h}'];put(f'direction_activity_{a}{h}',(1 if ret>0 else -1 if ret<0 else 0)*math.log(r) if ret is not None and r is not None and r>0 else None)
 prev=past[dates[-1]+'|'+ident['symbol']]['bars'] if dates else [];pc=prev[-1][4] if prev else None
 ph=max(b[2] for b in prev) if prev else None;pl=min(b[3] for b in prev) if prev else None
 op=next((b[1] for b in bars if b[0]==540),None)
 put('past.previous_close',pc);put('past.opening_gap',lg(op,pc));put('past.previous_range_position',ratio(latest-pl,ph-pl) if latest is not None and prev else None)
 for side,v in [('high',ph),('low',pl),('close',pc)]:put('past.distance_previous_'+side,lg(latest,v))
 for k in [1,2,3,5]:
  bb=past[dates[-k]+'|'+ident['symbol']]['bars'] if len(dates)>=k else [];put(f'past.return{k}',lg(latest,bb[-1][4]) if bb else None)
 for k in [1,3,5]:
  groups=[past[d+'|'+ident['symbol']]['bars'] for d in dates[-k:]];ok=len(groups)==k and all(groups);combined=[b for group in groups for b in group] if ok else []
  put(f'past.complete_sessions{k}',float(ok));put(f'past.range{k}',_range(combined) if ok else None)
  rvs=[_rv(g) for g in groups] if ok else [];put(f'past.rv{k}',math.sqrt(sum(v*v for v in rvs)) if ok and all(v is not None for v in rvs) else None)
  for a,j in [('volume',5),('value',6)]:put(f'past.mean_daily_{a}{k}',mean([sum(b[j] for b in g) for g in groups]) if ok else None)
  if k==5:
   hh=max(b[2] for b in combined) if combined else None;ll=min(b[3] for b in combined) if combined else None;put('past.position5',ratio(latest-ll,hh-ll) if combined and latest is not None else None)
 put('past.observed_sessions',float(sum(bool(past[d+'|'+ident['symbol']]['bars']) for d in dates)))
 put('past.previous_late_close_observed',float(bool(prev) and prev[-1][0]>=924))
 datesall=dates+[ident['session']];ages=[(dt.date.fromisoformat(b)-dt.date.fromisoformat(a)).days for a,b in zip(datesall,datesall[1:])]
 put('past.previous_calendar_age_days',float(ages[-1]) if ages else None);put('past.maximum_calendar_gap_days',float(max(ages)) if ages else None);put('past.unadjusted_basis_unknown',1.)
 if not all(v is None or math.isfinite(v) for v in out.values()):raise ValueError('NONFINITE_OUTPUT')
 return out
