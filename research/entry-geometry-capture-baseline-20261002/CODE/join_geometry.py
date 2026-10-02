#!/usr/bin/env python3
"""Deterministic saved-record join and evaluator arithmetic. No old Entry/State runner imported."""
import collections,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];P=ROOT/'research/entry-geometry-capture-baseline-20261002'
def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def write(n,o):
 b=(json.dumps(o,ensure_ascii=False,sort_keys=True,allow_nan=False,indent=2)+'\n').encode();(P/n).write_bytes(b)
def ordinal(m):
 if 540<=m<=690:return m-540
 if 750<=m<=930:return 150+m-750
 raise ValueError(('OUTSIDE_ACTIVE_SESSION',m))
def pct(a,b):return 100*(a/b-1) if a is not None and b is not None and b>0 else None
def stamp(day,m):return f'{day}T{m//60:02d}:{m%60:02d}:00+09:00' if m is not None else None
def band(m):
 if m is None:return 'UNKNOWN'
 for k,(lo,hi) in CONTRACT['time_of_day_bands'].items():
  if lo<=m<hi:return k
 return 'OUTSIDE_ACTIVE_SESSION'
def bucket(key,x):
 if x is None:return 'UNKNOWN'
 spec=CONTRACT['buckets'][key];e,l=spec['edges'],spec['labels']
 if key=='selector_to_high_pct':
  for j,v in enumerate(e):
   if x<v:return l[j]
  return l[-1]
 if key in ('entry_to_later_high_pct','low_to_entry_pct'):
  if x<=0:return l[0]
  for j,v in enumerate(e[1:],1):
   if x<v:return l[j]
  return l[-1]
 if key=='selector_to_entry_active_minutes':
  if x==0:return l[0]
  for j,v in enumerate(e[1:],1):
   if x<=v:return l[j]
  return l[-1]
 for j,v in enumerate(e):
  if x<=v:return l[j]
 return l[-1]
def capture(o,r,level,strict=False):
 if o['selectorOutcome']['mfeEnd'] is None:return 'SELECTOR_UNKNOWN'
 if o['selectorOutcome']['mfeEnd']<level:return 'NOT_SELECTOR_WINNER'
 if r['entry_id'] is None:return 'NO_ENTRY'
 value=r['entry_to_later_high_pct'] if strict else r['saved_entry_mfe_end_pct']
 if value is None:return 'OUTCOME_UNKNOWN'
 return 'CAPTURED' if value>=level else 'ENTERED_BUT_BELOW_THRESHOLD'

CONTRACT=read(P/'METRIC_CONTRACT.json');FREEZE=read(P/'POPULATION_FREEZE.json');SOURCES=read(P/'SOURCE_MANIFEST.json')
for src in SOURCES['sources']:
 f=Path(src['path']);f=f if f.is_absolute() else ROOT/f
 assert hashlib.sha256(f.read_bytes()).hexdigest()==src['sha256'],('SOURCE_CHANGED',src['name'])
OPP=read(ROOT/'docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz')
RAW=read(ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz')
ARM={'IMMEDIATE':read(ROOT/'docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/baseline-immediate-records.json.gz'),
     'R1':read(P/'FROZEN_ARTIFACT_MEMBERS/R1_ENTRY_RECORDS.original.json.gz')}
STATES=read(ROOT/'docs/evidence/phase57-state-v3-9pattern-entry-v1/measurement/state-checkpoints.json.gz')
T0={r['opportunity']:r for r in STATES if r['delay']==0}
audit={'status':'C3_JOIN_PASS','primary_opportunities':len(OPP),'arms':list(ARM),'row_unit':'one opportunity per arm, no independent sample duplication',
 'duplicates':{},'missing':{},'extra':{},'identity_mismatches':[],'clock_mismatches':[],'raw_source_hash_mismatches':[],
 'source_checks':'exact session/security/Selector price/Entry ID/timestamp/price and canonical raw sourceHash',
 'new_policy_replays':0,'entry_decisions_created':0,'state_generations':0}
idset=set(FREEZE['opportunity_ids']);maps={}
for arm,rs in ARM.items():
 c=collections.Counter(r['opportunity'] for r in rs)
 audit['duplicates'][arm]=[k for k,n in c.items() if n>1]
 audit['missing'][arm]=sorted(idset-set(c));audit['extra'][arm]=sorted(set(c)-idset)
 maps[arm]={r['opportunity']:r for r in rs}
rows=[]
for o in OPP:
 oid=o['opportunity'];day=o['session'];start=o['selectorMinute'];selector=o['selectorPrice'];path=RAW.get(oid)
 if path is None or path['sourceHash']!=o['sourceHash']:audit['raw_source_hash_mismatches'].append(oid)
 close=900 if day<'2024-11-05' else 930
 future=[bar for bar in (path or {}).get('today',[]) if bar[0]>=start and not (bar[0]==start and start in (690,close))]
 full=bool(o['orderedOracle'].get('fullSessionEvaluable') and o['selectorOutcome'].get('fullStatus')=='AVAILABLE')
 low=min(future,key=lambda b:(b[3],b[0])) if future else None
 high=max(future,key=lambda b:(b[2],-b[0])) if future else None
 for arm in ARM:
  s=maps[arm].get(oid);issues=[]
  if s is None:issues=['MISSING_SAVED_ENTRY_RECORD'];s={'entryId':None,'entryMinute':None,'price':None,'labels':{},'quality':{},'unfilledReason':'JOIN_MISSING'}
  else:
   for k in ('session','symbol'):
    if s[k]!=o[k]:issues.append(k)
   if s['quality'].get('selectorPrice')!=selector:issues.append('selectorPrice')
   if s['entryId'] and s['entryId']!=oid+'|'+str(s['entryMinute']):issues.append('entryId')
   if s['entryId'] and (s['price'] is None or s['price']<=0 or s['entryMinute']<start):issues.append('entry_clock_price')
  em,ep=s.get('entryMinute'),s.get('price');filled=bool(s.get('entryId'))
  later=[b for b in future if filled and b[0]>em]
  lh=max(later,key=lambda b:(b[2],-b[0])) if later else None
  ok=full and not issues
  lprice=float(low[3]) if low and ok else None;lminute=int(low[0]) if low and ok else None
  hprice=float(high[2]) if high and ok else None;hminute=int(high[0]) if high and ok else None
  lhprice=float(lh[2]) if lh and ok else None;lhminute=int(lh[0]) if lh and ok else None
  order='NO_ENTRY' if not filled else 'LOW_UNKNOWN' if lminute is None else 'LOW_AT_OR_BEFORE_ENTRY' if lminute<=em else 'LOW_AFTER_ENTRY'
  up=pct(lhprice,ep) if filled else None
  selector_up=o['selectorOutcome']['mfeEnd']
  retention=100*up/selector_up if up is not None and selector_up is not None and selector_up>0 else None
  delay=ordinal(em)-ordinal(start) if filled and not issues else None
  if delay is not None and delay!=s.get('delay'):audit['clock_mismatches'].append({'opportunity':oid,'arm':arm,'saved':s.get('delay'),'calculated':delay})
  why='JOIN_MISMATCH' if issues else 'NO_ENTRY' if not filled else 'FULL_SESSION_NOT_EVALUABLE' if not full else 'NO_STRICTLY_LATER_HIGH' if lh is None else None
  labs=s.get('labels',{});legacy=s.get('quality',{});state=T0.get(oid)
  row=dict(opportunity=oid,arm=arm,session=day,symbol=o['symbol'],join_status='JOIN_MISMATCH' if issues else 'MATCHED',
   selector_minute=start,selector_timestamp=stamp(day,start),selector_price=selector,
   entry_id=s.get('entryId'),entry_minute=em,entry_timestamp=stamp(day,em),entry_price=ep,
   intent_minute=s.get('intentMinute'),intent_reason=s.get('intentReason'),unfilled_reason=s.get('unfilledReason'),
   saved_source_hash=o['sourceHash'],canonical_full_session_evaluable=full,
   selector_to_high_pct=selector_up,selector_to_observed_global_high_unclipped_pct=pct(hprice,selector),
   selector_global_low_price=lprice,selector_global_low_minute=lminute,selector_global_low_timestamp=stamp(day,lminute),
   selector_global_high_price=hprice,selector_global_high_minute=hminute,selector_global_high_timestamp=stamp(day,hminute),
   later_high_price=lhprice,later_high_minute=lhminute,later_high_timestamp=stamp(day,lhminute),
   entry_to_later_high_pct=up,upside_retention_pct=retention,ordering_status=order,
   low_to_entry_pct=pct(ep,lprice) if order=='LOW_AT_OR_BEFORE_ENTRY' else None,
   entry_to_future_low_pct=pct(lprice,ep) if order=='LOW_AFTER_ENTRY' else None,
   same_entry_bar_low_order_unknown=bool(filled and lminute is not None and lminute==em),
   saved_entry_mfe_end_pct=labs.get('mfeEnd'),entry_mae_end_pct=labs.get('maeEnd'),
   entry_mae_30_pct=(labs.get('30') or {}).get('MAE'),entry_mae_60_pct=(labs.get('60') or {}).get('MAE'),
   selector_to_entry_active_minutes=delay,selector_to_entry_wall_minutes=em-start if filled else None,
   entry_to_high_active_minutes=ordinal(lhminute)-ordinal(em) if filled and lhminute is not None else None,
   entry_to_high_wall_minutes=lhminute-em if filled and lhminute is not None else None,
   selector_time_band=band(start),entry_time_band=band(em),
   legacy_ordered_oracle=o['orderedOracle'],legacy_entry_quality=legacy,saved_entry_labels=labs,
   original_state_v3_t0=(state or {}).get('state'),original_state_v3_revision=(state or {}).get('contractVersion'),
   saved_r1_initial_state=s.get('initialState'),state9_rc2=None,state9_status='NOT_AVAILABLE_EXACT_SOURCE_JOIN_NOT_CERTIFIED',
   remaining_upside_unknown_reason=why,retention_unknown_reason=why or ('NONPOSITIVE_SELECTOR_UPSIDE' if selector_up is None or selector_up<=0 else None),
   evaluator_only=True,future_outcome_used=True,future_decision_use=False)
  for key in CONTRACT['buckets']:row[key+'_bucket']=bucket(key,row[key])
  row['canonical_capture']={str(k):capture(o,row,k) for k in [1,2,3,5]}
  row['strict_later_capture']={str(k):capture(o,row,k,True) for k in [1,2,3,5]}
  rows.append(row)
  if issues:audit['identity_mismatches'].append({'opportunity':oid,'arm':arm,'fields':issues})
audit.update(joined_rows=len(rows),unique_opportunities=len({r['opportunity'] for r in rows}),sessions=len({r['session'] for r in rows}),symbols=len({r['symbol'] for r in rows}))
bad=bool(audit['identity_mismatches'] or audit['clock_mismatches'] or audit['raw_source_hash_mismatches'] or any(audit['duplicates'].values()) or any(audit['missing'].values()) or any(audit['extra'].values()))
if bad:audit['status']='ENTRY_GEOMETRY_SOURCE_MISMATCH'
b=('\n'.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False) for r in rows)+'\n').encode()
(P/'GEOMETRY_ROWS.jsonl.gz').write_bytes(gzip.compress(b,mtime=0))
(P/'JOINED_GEOMETRY_ROWS.jsonl.gz').write_bytes((P/'GEOMETRY_ROWS.jsonl.gz').read_bytes())
write('JOIN_AUDIT.json',audit)
missing={arm:{key:{'total_N':2155,'known_N':sum(r[key] is not None for r in rows if r['arm']==arm),'unknown_N':sum(r[key] is None for r in rows if r['arm']==arm)} for key in CONTRACT['formulas']} for arm in ARM}
write('MISSINGNESS.json',missing)
write('STATE9_GEOMETRY_NOT_AVAILABLE.json',dict(status='NOT_AVAILABLE_EXACT_SOURCE_JOIN_NOT_CERTIFIED',population_N=2155,
 reason='Saved Entry nine-pattern sources use an earlier State-v3 contract, not frozen RC2. Saved V3/V6 RC2 trace manifests use different source identities and security/session units; equivalence against these exact Entry raw paths has not been certified. No nearest-time mapping, source substitution or State regeneration performed.',
 frozen_rc2_contract_SHA256='45859122a62ccdc946b31bb5709f3fc080ea4a4f935958afd8f1ca895f75b6ff',
 legacy_source='docs/evidence/phase57-state-v3-9pattern-entry-v1/measurement/state-checkpoints.json.gz',new_state_runs=0))
write('C3_RECEIPT.json',dict(status=audit['status'],geometry_rows_sha256=hashlib.sha256((P/'GEOMETRY_ROWS.jsonl.gz').read_bytes()).hexdigest(),
 joined_rows=len(rows),opportunities=2155,policy_replays=0,entry_decisions_created=0,
 mechanical_raw_path_calculation='Global extrema chronology and strict later-bar maximum only; canonical labels retained byte-for-field',future_used_for_decisions=0))
print(json.dumps({k:v for k,v in audit.items() if k in ('status','joined_rows','unique_opportunities','sessions','symbols','identity_mismatches','clock_mismatches')}))
if bad:raise SystemExit(2)
