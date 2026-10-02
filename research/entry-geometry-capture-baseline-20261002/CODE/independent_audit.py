#!/usr/bin/env python3
"""Independent saved-original audit: Decimal ratios, streaming extrema, interval clock,
manual sorted quantiles. Never imports the primary join or aggregate implementation.
"""
import collections,gzip,hashlib,json,math,zipfile
from decimal import Decimal,localcontext
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3];P=ROOT/'research/entry-geometry-capture-baseline-20261002'
WORKSPACE=ROOT.parent;FAIL=[];TESTS=collections.Counter();MAXERR=collections.defaultdict(float)
def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def write(n,o): (P/n).write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n')
def check(kind,got,want,at='',numeric=False):
 TESTS[kind]+=1
 if numeric and got is not None and want is not None:
  err=abs(got-want);MAXERR[kind]=max(MAXERR[kind],err);ok=math.isfinite(got) and err<=1e-8
 else:ok=(got==want)
 if not ok:FAIL.append(dict(test=kind,at=at,got=got,expected=want))
def percent(top,bottom):
 if top is None or bottom is None or bottom<=0:return None
 with localcontext() as c:
  c.prec=50
  return float(Decimal(100)*(Decimal(str(top))/Decimal(str(bottom))-1))
def ratio(x,y):
 if x is None or y is None or y<=0:return None
 with localcontext() as c:
  c.prec=50;return float(Decimal(100)*Decimal(str(x))/Decimal(str(y)))
def active(a,b):
 # Duration of intersection with actual trading intervals, independent of ordinal subtraction.
 return sum(max(0,min(b,stop)-max(a,start)) for start,stop in [(540,690),(750,930)])
def timestamp(day,m):return None if m is None else day+'T'+str(int(m)//60).zfill(2)+':'+str(int(m)%60).zfill(2)+':00+09:00'
def classify(key,x):
 if x is None:return 'UNKNOWN'
 if key=='selector_to_high_pct':
  return '<1%' if x<1 else '1–3%' if x<3 else '3–5%' if x<5 else '5–10%' if x<10 else '>=10%'
 if key=='entry_to_later_high_pct':
  return '<=0%' if x<=0 else '0–1%' if x<1 else '1–2%' if x<2 else '2–3%' if x<3 else '3–5%' if x<5 else '>=5%'
 if key=='low_to_entry_pct':
  return '<=0%' if x<=0 else '0–0.5%' if x<.5 else '0.5–1%' if x<1 else '1–2%' if x<2 else '2–3%' if x<3 else '>=3%'
 if key=='selector_to_entry_active_minutes':
  return '0m' if x==0 else '1–5m' if x<=5 else '6–10m' if x<=10 else '11–20m' if x<=20 else '21–30m' if x<=30 else '>30m'
 return '<=5m' if x<=5 else '6–15m' if x<=15 else '16–30m' if x<=30 else '31–60m' if x<=60 else '>60m'
def timeband(m):
 if m is None:return 'UNKNOWN'
 if 540<=m<600:return '09:00–10:00'
 if 600<=m<660:return '10:00–11:00'
 if 660<=m<=690:return '11:00–11:30'
 if 750<=m<840:return '12:30–14:00'
 if 840<=m<900:return '14:00–15:00'
 if 900<=m<=930:return '15:00–15:30'
 return 'OUTSIDE_ACTIVE_SESSION'
def summary(values):
 v=sorted(x for x in values if x is not None);n=len(v)
 def q(p):
  if not n:return None
  pos=(n-1)*p;i=int(math.floor(pos));j=int(math.ceil(pos));return v[i]+(pos-i)*(v[j]-v[i])
 return dict(N=len(values),known_N=n,unknown_N=len(values)-n,mean=math.fsum(v)/n if n else None,
  median=q(.5),p5=q(.05),p25=q(.25),p75=q(.75),p90=q(.9),p95=q(.95),min=v[0] if n else None,max=v[-1] if n else None)
def compare_stats(kind,got,values,at):
 want=summary(values)
 for k in want:check(kind,got.get(k),want[k],at+'/'+k,numeric=k not in ('N','known_N','unknown_N'))

sources=read(P/'SOURCE_MANIFEST.json');contract=read(P/'METRIC_CONTRACT.json');freeze=read(P/'POPULATION_FREEZE.json')
for s in sources['sources']:
 f=Path(s['path']);f=f if f.is_absolute() else ROOT/f;b=f.read_bytes()
 check('source_sha256',hashlib.sha256(b).hexdigest(),s['sha256'],s['name'])
 check('source_git_object',hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest(),s['computed_git_object_sha1'],s['name'])
 if s['expected_sha256']:check('existing_manifest_hash',s['sha256'],s['expected_sha256'],s['name'])
for s in sources['artifacts']:check('artifact_sha256',hashlib.sha256(Path(s['path']).read_bytes()).hexdigest(),s['expected_sha256'],str(s['artifact_id']))
opp=read(ROOT/'docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz')
raw=read(ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz')
arms={'IMMEDIATE':read(ROOT/'docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/baseline-immediate-records.json.gz'),
      'R1':read(P/'FROZEN_ARTIFACT_MEMBERS/R1_ENTRY_RECORDS.original.json.gz')}
states=read(ROOT/'docs/evidence/phase57-state-v3-9pattern-entry-v1/measurement/state-checkpoints.json.gz');t0={x['opportunity']:x for x in states if x['delay']==0}
with gzip.open(P/'GEOMETRY_ROWS.jsonl.gz','rt') as f:joined=[json.loads(x) for x in f]
index={(r['arm'],r['opportunity']):r for r in joined}
check('row_count',len(joined),4310);check('unique_arm_identity',len(index),4310)
check('unique_opportunity',len({r['opportunity'] for r in joined}),2155)
check('sessions',len({o['session'] for o in opp}),58);check('symbols',len({o['symbol'] for o in opp}),950)
check('population_ids',sorted(o['opportunity'] for o in opp),sorted(freeze['opportunity_ids']))
check('gzip_alias',hashlib.sha256((P/'GEOMETRY_ROWS.jsonl.gz').read_bytes()).hexdigest(),hashlib.sha256((P/'JOINED_GEOMETRY_ROWS.jsonl.gz').read_bytes()).hexdigest())
derived={a:[] for a in arms};witness=collections.Counter();geometry_fields=list(contract['formulas'])
for a,records in arms.items():
 ids=[r['opportunity'] for r in records];check('saved_record_count',len(ids),2155,a);check('saved_duplicates',len(ids)-len(set(ids)),0,a)
 check('saved_population',sorted(ids),sorted(o['opportunity'] for o in opp),a);amap={r['opportunity']:r for r in records}
 for o in opp:
  oid=o['opportunity'];s=amap[oid];j=index[(a,oid)];at=a+'/'+oid;day=o['session'];start=o['selectorMinute'];em=s['entryMinute'];ep=s['price'];filled=s['entryId'] is not None
  check('raw_identity',raw[oid]['sourceHash'],o['sourceHash'],at)
  for key in ['session','symbol']:check('entry_selector_identity',s[key],o[key],at+'/'+key)
  check('selector_exact_price',s['quality']['selectorPrice'],o['selectorPrice'],at)
  for jk,sk in [('entry_id','entryId'),('entry_minute','entryMinute'),('entry_price','price'),('intent_minute','intentMinute'),('unfilled_reason','unfilledReason')]:check('saved_field_identity',j[jk],s.get(sk),at+'/'+jk)
  check('saved_labels_unchanged',j['saved_entry_labels'],s['labels'],at);check('legacy_quality_unchanged',j['legacy_entry_quality'],s['quality'],at)
  check('legacy_oracle_unchanged',j['legacy_ordered_oracle'],o['orderedOracle'],at)
  check('selector_exact_timestamp',j['selector_timestamp'],timestamp(day,start),at);check('entry_exact_timestamp',j['entry_timestamp'],timestamp(day,em),at)
  check('saved_entry_id',s['entryId'],oid+'|'+str(em) if filled else None,at)
  full=o['selectorOutcome']['fullStatus']=='AVAILABLE' and o['orderedOracle']['fullSessionEvaluable']
  check('canonical_evaluable',j['canonical_full_session_evaluable'],bool(full),at)
  # Stream saved bars in timestamp order: strict > for later high; ties retain first bar.
  bars=sorted(raw[oid]['today'],key=lambda b:b[0]);lo=hi=lh=None;entry_bars=[]
  close=900 if day<'2024-11-05' else 930
  for b in bars:
   if b[0]<start or (b[0]==start and start in [690,close]):continue
   if lo is None or b[3]<lo[3]:lo=b
   if hi is None or b[2]>hi[2]:hi=b
   if filled and b[0]>em and (lh is None or b[2]>lh[2]):lh=b
   if filled and b[0]>=em:entry_bars.append(b)
  if full and hi is not None:
   check('canonical_selector_MFE',o['selectorOutcome']['mfeEnd'],max(0,percent(hi[2],o['selectorPrice'])),at,numeric=True)
  if filled:
   entrybar=next((b for b in bars if b[0]==em),None)
   check('entry_open_bar_present',entrybar is not None,True,at)
   if entrybar:check('saved_fill_price_basis',ep,float(Decimal(str(entrybar[1]))*Decimal('1.0005')),at,numeric=True)
   check('delay_saved_parity',active(start,em),s['delay'],at)
  lp,lm=(lo[3],lo[0]) if full and lo is not None else (None,None)
  hp,hm=(hi[2],hi[0]) if full and hi is not None else (None,None)
  lhp,lhm=(lh[2],lh[0]) if full and lh is not None else (None,None)
  order='NO_ENTRY' if not filled else 'LOW_UNKNOWN' if lm is None else 'LOW_AFTER_ENTRY' if em<lm else 'LOW_AT_OR_BEFORE_ENTRY'
  up=percent(lhp,ep) if filled else None;su=o['selectorOutcome']['mfeEnd']
  d=dict(opportunity=oid,arm=a,session=day,symbol=o['symbol'],entry_id=s['entryId'],selector_minute=start,entry_minute=em,
   selector_to_high_pct=su,selector_to_observed_global_high_unclipped_pct=percent(hp,o['selectorPrice']),
   entry_to_later_high_pct=up,upside_retention_pct=ratio(up,su),ordering_status=order,
   low_to_entry_pct=percent(ep,lp) if order=='LOW_AT_OR_BEFORE_ENTRY' else None,
   entry_to_future_low_pct=percent(lp,ep) if order=='LOW_AFTER_ENTRY' else None,
   entry_mae_end_pct=s['labels'].get('maeEnd'),entry_mae_30_pct=(s['labels'].get('30') or {}).get('MAE'),entry_mae_60_pct=(s['labels'].get('60') or {}).get('MAE'),
   selector_to_entry_active_minutes=active(start,em) if filled else None,selector_to_entry_wall_minutes=em-start if filled else None,
   entry_to_high_active_minutes=active(em,lhm) if filled and lhm is not None else None,entry_to_high_wall_minutes=lhm-em if filled and lhm is not None else None,
   selector_time_band=timeband(start),entry_time_band=timeband(em),selector_global_high_minute=hm,saved_entry_mfe_end_pct=s['labels'].get('mfeEnd'))
  for key in geometry_fields:check('row_'+key,j[key],d[key],at,numeric=True)
  for prefix,price,minute in [('selector_global_low',lp,lm),('selector_global_high',hp,hm),('later_high',lhp,lhm)]:
   check('extrema_price',j[prefix+'_price'],price,at+'/'+prefix,numeric=True);check('extrema_minute',j[prefix+'_minute'],minute,at+'/'+prefix)
   check('extrema_timestamp',j[prefix+'_timestamp'],timestamp(day,minute),at+'/'+prefix)
  check('low_ordering',j['ordering_status'],order,at);check('same_bar_unknown',j['same_entry_bar_low_order_unknown'],bool(filled and lm is not None and lm==em),at)
  if order=='LOW_AFTER_ENTRY':check('future_low_not_low_distance',j['low_to_entry_pct'],None,at)
  if lhm is not None:check('strictly_post_entry_high',lhm>em,True,at)
  for flag,val in [('evaluator_only',True),('future_outcome_used',True),('future_decision_use',False)]:check('outcome_exposure_flag',j[flag],val,at+'/'+flag)
  check('RC2_not_substituted',j['state9_rc2'],None,at);check('legacy_state_exact',j['original_state_v3_t0'],t0.get(oid,{}).get('state'),at)
  for key in contract['buckets']:
   # Independently derived source ratios use the frozen IEEE-754 cutoff convention.
   # Decimal ratios independently verify arithmetic above; joined values never define the expected bucket.
   x=100*(lhp/ep-1) if key=='entry_to_later_high_pct' and lhp is not None else 100*(ep/lp-1) if key=='low_to_entry_pct' and order=='LOW_AT_OR_BEFORE_ENTRY' else d[key]
   bk=classify(key,x);d[key+'_bucket']=bk;check('bucket_exact',j[key+'_bucket'],bk,at+'/'+key)
  for key in ['selector_time_band','entry_time_band']:check('time_of_day_exact',j[key],d[key],at+'/'+key)
  for field,strict in [('canonical_capture',False),('strict_later_capture',True)]:
   d[field]={}
   for t in [1,2,3,5]:
    value=up if strict else s['labels'].get('mfeEnd')
    c='SELECTOR_UNKNOWN' if su is None else 'NOT_SELECTOR_WINNER' if su<t else 'NO_ENTRY' if not filled else 'OUTCOME_UNKNOWN' if value is None else 'CAPTURED' if value>=t else 'ENTERED_BUT_BELOW_THRESHOLD'
    d[field][str(t)]=c;check('winner_class_exact',j[field][str(t)],c,at+'/'+field+'/'+str(t))
  if full and filled and entry_bars:
   check('saved_entry_MFE_raw',s['labels'].get('mfeEnd'),max(0,percent(max(b[2] for b in entry_bars),ep)),at,numeric=True)
   check('saved_entry_MAE_raw',s['labels'].get('maeEnd'),min(0,percent(min(b[3] for b in entry_bars),ep)),at,numeric=True)
  if filled and start<=690 and em>=750:witness[a+'_selector_entry_lunch']+=1;check('lunch_delay_difference',j['selector_to_entry_wall_minutes']-j['selector_to_entry_active_minutes'],60,at)
  if lhm is not None and em<=690 and lhm>=750:witness[a+'_entry_high_lunch']+=1;check('lunch_high_difference',j['entry_to_high_wall_minutes']-j['entry_to_high_active_minutes'],60,at)
  if filled and hm is not None and hm<=em:witness[a+'_global_high_at_or_before_entry']+=1
  if d['upside_retention_pct'] is not None:
   if d['upside_retention_pct']>100:witness[a+'_retention_over100']+=1
   if d['upside_retention_pct']<0:witness[a+'_retention_negative']+=1
  if filled and s['labels'].get('mfeEnd') is not None and up is not None and abs(s['labels']['mfeEnd']-up)>1e-8:witness[a+'_entry_bar_MFE_vs_strict_high_differ']+=1
  derived[a].append(d)

g=read(P/'GEOMETRY_SUMMARY.json');miss=read(P/'MISS_WINNER_ANALYSIS.json');time=read(P/'TIME_GEOMETRY.json');conc=read(P/'CONCENTRATION.json');missing=read(P/'MISSINGNESS.json')
for a,ds in derived.items():
 t1=g['tables']['01_population'][a]
 for field,want in [('population_N',len(ds)),('fill_N',sum(d['entry_id'] is not None for d in ds)),('no_entry_N',sum(d['entry_id'] is None for d in ds)),('selector_outcome_known_N',sum(d['selector_to_high_pct'] is not None for d in ds)),('strict_later_high_known_N',sum(d['entry_to_later_high_pct'] is not None for d in ds)),('saved_entry_outcome_known_N',sum(d['saved_entry_mfe_end_pct'] is not None for d in ds))]:check('population_table',t1[field],want,a+'/'+field)
 for field,want in [('greater_than_100_N',sum(d['upside_retention_pct'] is not None and d['upside_retention_pct']>100 for d in ds)),('negative_N',sum(d['upside_retention_pct'] is not None and d['upside_retention_pct']<0 for d in ds))]:check('retention_unclipped_counts',g['tables']['04_upside_retention'][a][field],want,a+'/'+field)
 for key in geometry_fields:
  compare_stats('aggregate_continuous',g['continuous'][a][key],[d[key] for d in ds],a+'/'+key)
  compare_stats('fill_continuous',g['fill_conditioned_continuous'][a][key],[d[key] for d in ds if d['entry_id'] is not None],a+'/'+key)
  for k in ['known_N','unknown_N']:check('missingness_denominator',missing[a][key][k],summary([d[key] for d in ds])[k],a+'/'+key+'/'+k)
 for table,key in [('02_selector_to_high','selector_to_high_pct'),('03_entry_to_later_high','entry_to_later_high_pct'),('07_selector_to_entry_delay','selector_to_entry_active_minutes'),('08_entry_to_high_time','entry_to_high_active_minutes')]:
  c=collections.Counter(d[key+'_bucket'] for d in ds)
  for b,n in g['tables'][table][a]['bucket_counts'].items():check('aggregate_bucket_counts',n,c[b],a+'/'+key+'/'+b)
  check('bucket_denominator',sum(c.values()),2155,a+'/'+key)
 check('ordering_counts',g['tables']['05_low_to_entry'][a]['ordering_counts'],dict(collections.Counter(d['ordering_status'] for d in ds)),a)
 for key in ['session','symbol']:
  c=collections.Counter(d[key] for d in ds);check('concentration_unique',conc[key]['unique_N'],len(c),a+'/'+key)
  for group in conc[key]['groups']:
   rs=[d for d in ds if d[key]==group['value']]
   check('concentration_population',group['opportunity_N'],c[group['value']],a+'/'+key+'/'+group['value'])
   check('concentration_fills',group['arms'][a]['fill_N'],sum(d['entry_id'] is not None for d in rs),a+'/'+key+'/'+group['value'])
   st=summary([d['entry_to_later_high_pct'] for d in rs])
   for out,sk in [('remaining_known_N','known_N'),('remaining_mean','mean'),('remaining_median','median')]:check('concentration_metric',group['arms'][a][out],st[sk],a+'/'+key+'/'+group['value']+'/'+out,numeric=True)
 for store,groupkey in [(g['tables']['10_selector_upside_bucket'],'selector_to_high_pct_bucket'),(time['delay_buckets'],'selector_to_entry_active_minutes_bucket'),(time['selector_time_of_day'],'selector_time_band'),(time['entry_time_of_day'],'entry_time_band'),(g['low_distance_buckets'],'low_to_entry_pct_bucket')]:
  for b,data in store[a].items():
   rs=[d for d in ds if d[groupkey]==b];check('conditional_total_N',data['total_N'],len(rs),a+'/'+groupkey+'/'+b)
   for key,st in data['geometry'].items():compare_stats('conditional_geometry',st,[d[key] for d in rs],a+'/'+groupkey+'/'+b+'/'+key)
   for t,n in data['remaining_at_least_counts'].items():check('conditional_remaining_threshold_count',n,sum(d['entry_to_later_high_pct'] is not None and d['entry_to_later_high_pct']>=int(t) for d in rs),a+'/'+groupkey+'/'+b+'/'+t)
 for field,out in [('canonical_capture','canonical_capture'),('strict_later_capture','strict_later_sensitivity')]:
  for t,data in miss[out][a].items():
   c=collections.Counter(d[field][t] for d in ds);winners=sum(c[k] for k in ['CAPTURED','NO_ENTRY','ENTERED_BUT_BELOW_THRESHOLD','OUTCOME_UNKNOWN'])
   for cls,n in data['counts'].items():check('aggregate_winner_counts',n,c[cls],a+'/'+field+'/'+t+'/'+cls)
   check('winner_denominator',data['selector_winner_N'],winners,a+'/'+field+'/'+t)
   check('winner_unknown',data['selector_unknown_N'],c['SELECTOR_UNKNOWN'],a+'/'+field+'/'+t)
   check('winner_no_zero_imputation',data['known_missed_N'],c['NO_ENTRY']+c['ENTERED_BUT_BELOW_THRESHOLD'],a+'/'+field+'/'+t)
   check('capture_rate',data['capture_pct_of_all_winners'],100*c['CAPTURED']/winners,a+'/'+field+'/'+t,numeric=True)
 for t,data in miss['winner_geometry'][a].items():
  dswin=[d for d in ds if d['selector_to_high_pct'] is not None and d['selector_to_high_pct']>=int(t)]
  check('winner_geometry_total',data['total_N'],len(dswin),a+'/'+t)
  for key,st in data['geometry'].items():compare_stats('winner_geometry',st,[d[key] for d in dswin],a+'/'+t+'/'+key)
 for t,data in miss['entered_below_threshold_chronology'][a].items():
  below=[d for d in ds if d['canonical_capture'][t]=='ENTERED_BUT_BELOW_THRESHOLD']
  check('late_chronology_count',data['global_high_at_or_before_entry_N'],sum(d['selector_global_high_minute'] is not None and d['selector_global_high_minute']<=d['entry_minute'] for d in below),a+'/'+t)
for key,data in g['paired_common_known'].items():
 im={d['opportunity']:d for d in derived['IMMEDIATE']};rr={d['opportunity']:d for d in derived['R1']};common=[k for k in im if im[k][key] is not None and rr[k][key] is not None]
 check('paired_denominator',data['common_known_N'],len(common),key)
 compare_stats('paired_metric',data['IMMEDIATE'],[im[k][key] for k in common],key+'/IMMEDIATE');compare_stats('paired_metric',data['R1'],[rr[k][key] for k in common],key+'/R1')
 compare_stats('paired_difference',data['R1_minus_IMMEDIATE'],[rr[k][key]-im[k][key] for k in common],key)

# Historical scorecards are supplementary byte-pinned authorities, never the audit's calculation source.
scorepins=[]
for a,artifact_id,member,expected in [
 ('IMMEDIATE',10818327246,'immediate.json','4413da8aefe8e3a6f2efd07a787e64a544301fa39baaa3ff111bece59776e2a2'),
 ('R1',10851958443,'all-material-r1/ci-run-a/scorecard.json','8817f174e776ea2db321b3518aa4b9189ba81b98b0ed03f25d9e6d787078d037')]:
 artifact=next(x for x in sources['artifacts'] if x['artifact_id']==artifact_id)
 with zipfile.ZipFile(artifact['path']) as z:b=z.read(member)
 sha=hashlib.sha256(b).hexdigest();check('scorecard_member_sha256',sha,expected,a)
 dest=P/'FROZEN_ARTIFACT_MEMBERS'/(a+'_SCORECARD.original.json.gz');dest.write_bytes(gzip.compress(b,mtime=0))
 card=json.loads(b)
 for t in ['1','2','3','5']:
  old=card['overall']['capture'][t];new=miss['canonical_capture'][a][t]
  for oldkey,newkey in [('captured','CAPTURED'),('noEntry','NO_ENTRY'),('belowThreshold','ENTERED_BUT_BELOW_THRESHOLD'),('unknownEntered','OUTCOME_UNKNOWN')]:check('saved_scorecard_capture_parity',new['counts'][newkey],old[oldkey],a+'/'+t+'/'+oldkey)
  check('saved_scorecard_winner_denominator',new['selector_winner_N'],old['selectorWinnerDenominator'],a+'/'+t)
  check('saved_scorecard_legacy_missed',new['legacy_not_captured_including_unknown_N'],old['missed'],a+'/'+t)
 scorepins.append(dict(arm=a,artifact_id=artifact_id,member=member,original_sha256=sha,wrapped_path=str(dest.relative_to(ROOT)),wrapped_sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
check('lunch_boundary_check',active(690,751),1);check('lunch_boundary_wall',751-690,61)
check('threshold_5_distinct_from_3',miss['canonical_capture']['R1']['5']['selector_winner_N']!=miss['canonical_capture']['R1']['3']['selector_winner_N'],True)
check('State9_receipt',g['tables']['12_state9']['status'],'NOT_AVAILABLE_EXACT_SOURCE_JOIN_NOT_CERTIFIED')
audit=dict(status='ENTRY_GEOMETRY_BASELINE_AUDIT_PASS' if not FAIL else 'ENTRY_GEOMETRY_SEMANTIC_MISMATCH',
 independent_method='Original saved records + Decimal ratios + streaming extrema + active-interval intersections + manually interpolated sorted quantiles. No primary implementation imported; aggregates are comparison targets only.',
 opportunity_N=2155,arm_rows=4310,sessions=58,symbols=950,mismatch_count=len(FAIL),test_counts=dict(TESTS),total_checks=sum(TESTS.values()),
 max_absolute_errors=dict(MAXERR),tolerance_pct=1e-8,witness_counts=dict(witness),supplemental_scorecard_sources=scorepins,
 findings=FAIL,unknown_zero_imputation=False,future_decision_use=False,protected_opens=0,new_fits=0,new_policy_replays=0,provider_requests=0,bootstrap=0)
write('INDEPENDENT_AUDIT.json',audit)
print(json.dumps(audit,indent=2))
if FAIL:raise SystemExit(2)
