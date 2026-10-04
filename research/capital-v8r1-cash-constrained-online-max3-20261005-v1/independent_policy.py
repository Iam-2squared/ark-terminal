"""Independent saved-score percentile, training table and policy reconstruction.
No Primary runtime, tables, replay or evaluator import.
"""
from independent_engine import ROOT,I,PIN,O,read,rows,early,late,Audit
from bisect import bisect_left
from collections import defaultdict,Counter
BUCKETS=[(540,570),(570,600),(600,630),(630,660),(660,690),(750,780),(780,810),(810,840),(840,870),(870,900),(900,920)]
ARMS=['CAPACITY_ORDERSTAT_MAX3_V1','TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1']
BANDS=['P_HIGH','P_MID','P_BASE','P_BELOW']
def lower_middle(x):return max(1,sorted(x)[(len(x)-1)//2])
def active(t):return t-540 if t<=690 else 150 if t<750 else t-600
def predicted(r,table):
 low,high=next((a,b) for a,b in BUCKETS if a<=r['entry_minute']<b);d=table['tenure']['cells'][r['band']][f'{low}-{high}']['median_active_duration'];clock=active(r['entry_minute'])+d
 return min(920,clock+540 if clock<=150 else clock+600),d
def accept(arm,r,occupancy,t,table):
 if occupancy==3:return False,'MAX3_FULL',None,None
 horizon=920 if arm==ARMS[0] else predicted(r,table)[0];threshold=3-occupancy;values=[]
 for day in table['training_sessions']:
  count=0
  for minute,units in table['sessions'][day]:
   if minute>t and minute<horizon and units>r['rank_units']:count+=1
  values.append(count>=threshold)
 hits=sum(values);n=len(values);ok=hits/n<.5
 return ok,'ACCEPT_CAPACITY' if ok else 'CAPACITY_RESERVE_REJECT',hits,n
def native(units,n,counts):
 running=0
 for j,band in enumerate('SAB'):
  running+=counts[band]
  if units>n-running:return BANDS[j]
 return BANDS[3]
def build(audit):
 scores=rows(I/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz');savedtrain=rows(PIN/'TRAIN_MAPPED_SCORES.jsonl.gz');savedruntime={r['entry_id']:r for r in rows(PIN/'RANK_NATIVE_RUNTIME.jsonl.gz')};split=read(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json');bandmaps=read(ROOT/'docs/evidence/capital-v7-rank-native-max3-20261005-v1/RANK_NATIVE_BAND_MAP.json')['blocks'];books={r['entry_id']:r for r in rows(I/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};release={r['entry_id']:{k:r.get(k) for k in ('execution_status','release_minute')} for r in rows(I/'evaluation/TEACHERS_EVALUATION.jsonl.gz')};tables={};runtime=[];alltrain=[]
 for block in split['blocks']:
  b=block['block'];rr=[dict(r) for r in savedtrain if r['block']==b];model=read(I/f'movement/models/MOVE_P_BLOCK_{b:02}.json');n=len(rr)
  audit.check(f'{b}/trainID',set(r['entry_id'] for r in rr)==set(model['train_entry_ids']) and len(rr)==len(model['train_entry_ids']))
  audit.check(f'{b}/past',all(r['session'] in block['train'] and r['session']<min(block['test']) and r['entry_minute']<920 for r in rr))
  rr.sort(key=lambda r:(-r['pP'],r['entry_timestamp'],r['symbol']));counts=Counter('S' if r['old_ML']>=2 else 'A' if r['old_ML']>=1.5 else 'B' if r['old_ML']>=1 else 'C' for r in rr);counts={k:counts[k] for k in 'SABC'};audit.check(f'{b}/volume',counts==bandmaps[str(b)]['old_band_counts']);keys=[(-r['pP'],r['entry_timestamp'],r['symbol']) for r in rr]
  for j,r in enumerate(rr):audit.check(f'{b}/{r["entry_id"]}/trainpercentile',r['rank_units']==n-j and r['train_N']==n and r['band']==native(n-j,n,counts));audit.num(f'{b}/{r["entry_id"]}/trainr',r['r'],(n-j)/n)
  for s in [z for z in scores if z['block']==b]:
   units=n-bisect_left(keys,(-s['pP'],s['entry_timestamp'],s['symbol']));r={k:s[k] for k in ('entry_id','session','symbol','entry_minute','entry_timestamp','raw_reference','pP','block')};r.update(rank_units=units,train_N=n,r=units/n,band=native(units,n,counts));z=savedruntime[r['entry_id']]
   audit.check(r['entry_id']+'/runtime_identity',all(r[k]==z[k] for k in r));runtime.append(r)
  sessions={day:sorted([[r['entry_minute'],r['rank_units']] for r in rr if r['session']==day and r['band']!='P_BELOW']) for day in block['train']};cells=defaultdict(list);band_values=defaultdict(list);global_values=[];ids=[]
  for r in rr:
   if r['band']=='P_BELOW':continue
   z=release[r['entry_id']]
   if z['execution_status']!='COMPLETE' or z['release_minute'] is None:continue
   book=books[r['entry_id']];source=early(book) or late(book);audit.check(r['entry_id']+'/training_confirmed_release',source is not None and source['release']==z['release_minute'])
   duration=max(1,sum(t<690 or t>=750 for t in range(r['entry_minute'],z['release_minute'])));lo,hi=next((lo,hi) for lo,hi in BUCKETS if lo<=r['entry_minute']<hi);key=f'{lo}-{hi}';cells[r['band'],key].append(duration);band_values[r['band']].append(duration);global_values.append(duration);ids.append(r['entry_id'])
  tenure={'cells':{},'training_support_N':len(global_values),'global_median_active_duration':lower_middle(global_values),'training_support_entry_ids':sorted(ids),'teacher_projection_fields':['entry_id','execution_status','release_minute']}
  for band in BANDS[:3]:
   tenure['cells'][band]={}
   for lo,hi in BUCKETS:
    key=f'{lo}-{hi}';xx=cells[band,key];fallback='CELL'
    if len(xx)<10:xx=band_values[band];fallback='BAND'
    if len(xx)<10:xx=global_values;fallback='GLOBAL'
    tenure['cells'][band][key]={'cell_support_N':len(cells[band,key]),'band_support_N':len(band_values[band]),'used_support_N':len(xx),'backoff':fallback,'median_active_duration':lower_middle(xx)}
  tables[str(b)]={'train_N':n,'training_sessions':block['train'],'sessions':sessions,'train_entry_ids':sorted(r['entry_id'] for r in rr),'test_sessions':block['test'],'tenure':tenure};alltrain+=rr
 primary=read(O/'B1_CAPACITY_PRESSURE_TABLE.json');primarytenure=read(O/'B2_TENURE_LOOKUP_TABLE.json')
 for b,t in tables.items():audit.check(b+'/pressure_table_exact',{k:v for k,v in t.items() if k!='tenure'}==primary[b]);audit.check(b+'/tenure_exact',t['tenure']==primarytenure[b])
 runtime.sort(key=lambda r:(r['session'],r['entry_minute'],-r['pP'],r['entry_timestamp'],r['symbol']));return runtime,tables,alltrain
