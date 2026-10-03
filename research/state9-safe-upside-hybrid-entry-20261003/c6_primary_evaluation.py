"""Descriptive outer-OOF evaluation. No fitting or operating-point tuning.

Old Entry geometry/capture numbers are copied from hash-verified scorecards.
The only new old-arm target is fill-anchored +2/-1 first passage. Shared
candidate labels are reused by exact fill identity and price where possible.
All generated row-level records are private, evaluator-only deliverables.
"""
import collections
import copy
import gzip
import hashlib
import itertools
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import expit
from sklearn.metrics import (average_precision_score, roc_auc_score,
    precision_recall_curve, auc)

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
GEOM=REPO/'research/entry-geometry-capture-baseline-20261002'
SUB=REPO/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate'
KNOWN=('UP_FIRST','DOWN_FIRST','NEITHER')
STATES=KNOWN+('ORDER_UNKNOWN','DATA_UNAVAILABLE')
FAMILIES=('H0','H1','H2')
NEW_ARMS=FAMILIES+('SELECTED_DEVELOPMENT',)
CANON=REPO/'docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz'
BASE_PATHS={
 'IMMEDIATE':REPO/'docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/baseline-immediate-records.json.gz',
 'R1':GEOM/'FROZEN_ARTIFACT_MEMBERS/R1_ENTRY_RECORDS.original.json.gz'}
BASE_SHA={'IMMEDIATE':'4522bea9ac94f597affc8518c4cb25354e27f9e64141152cde8b8a4b9e09df9c','R1':'15ddb5cfc5169024878ee72d9dbecc6e1d9dec24e78afa2dcdf8dea891117fa6'}
SCORE_SHA={'IMMEDIATE':'4413da8aefe8e3a6f2efd07a787e64a544301fa39baaa3ff111bece59776e2a2','R1':'8817f174e776ea2db321b3518aa4b9189ba81b98b0ed03f25d9e6d787078d037'}

def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,x):(HERE/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def lines(p):
 for s in gzip.open(p,'rt'):yield json.loads(s)
def gzwrite(n,rows):
 with (HERE/n).open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as g:
  for x in rows:g.write((json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())
def ratio(a,b):return a/b if b else None
def stats(v,N):
 a=np.array([x for x in v if x is not None and np.isfinite(x)],dtype=float)
 z=dict(N=N,known_N=len(a),unknown_N=N-len(a))
 if len(a):
  z.update(mean=float(a.mean()),median=float(np.median(a)),min=float(a.min()),max=float(a.max()))
  z.update({f'p{q}':float(np.percentile(a,q)) for q in (5,25,75,90,95)})
 else:z.update({k:None for k in ('mean','median','min','max','p5','p25','p75','p90','p95')})
 return z
def metric_quality(x):
 return dict(entry_to_strictly_later_high_pct=x.get('strictly_later_high_pct'),session_end_MFE_pct=x.get('saved_session_end_MFE'),
  session_end_MAE_pct=x.get('saved_session_end_MAE'),MAE30_pct=(x.get('saved_30') or {}).get('MAE'),
  MFE30_pct=(x.get('saved_30') or {}).get('MFE'),MAE60_pct=(x.get('saved_60') or {}).get('MAE'),
  MFE60_pct=(x.get('saved_60') or {}).get('MFE'),remaining_active_minutes=x.get('remaining_active_minutes'))

def primary_original(day,minute,p0,path,full_status):
 """Only +2/-1 for a saved baseline fill outside the reused candidate labels."""
 last=900 if day<'2024-11-05' else 925; terminal=900 if day<'2024-11-05' else 930
 schedule=[t for t in list(range(540,690))+[690]+list(range(750,last))+[terminal] if t>=minute]
 by={int(b[0]):b for b in path['today'] if b[0]>=minute};up=p0*1.02;down=p0*.99
 for t in schedule:
  b=by.get(t)
  if b is None:return dict(status='DATA_UNAVAILABLE',first_touch_bar_start=None,time_to_up_active=None,time_to_down_active=None,censor_reason='UNCLASSIFIED_MISSING_SOURCE_BEFORE_FIRST_TOUCH')
  o,h,l,c=map(float,b[1:5])
  assert min(o,h,l,c)>0 and l<=min(o,c)<=max(o,c)<=h
  status='UP_FIRST' if o>=up else 'DOWN_FIRST' if o<=down else 'ORDER_UNKNOWN' if h>=up and l<=down else 'UP_FIRST' if h>=up else 'DOWN_FIRST' if l<=down else None
  if status:
   elapsed=sum(max(0,min(t,hi)-max(minute,lo)) for lo,hi in ((540,690),(750,last)))
   return dict(status=status,first_touch_bar_start=t,time_to_up_active=elapsed if status=='UP_FIRST' else None,
    time_to_down_active=elapsed if status=='DOWN_FIRST' else None,censor_reason='BOTH_BARRIERS_SAME_BAR_OPEN_INSIDE' if status=='ORDER_UNKNOWN' else None)
 return dict(status='NEITHER' if full_status=='AVAILABLE' else 'DATA_UNAVAILABLE',first_touch_bar_start=None,time_to_up_active=None,time_to_down_active=None,
  censor_reason=None if full_status=='AVAILABLE' else 'CANONICAL_SESSION_END_NOT_EVALUABLE')

def safe_summary(records):
 filled=[r for r in records if r['filled']];c=collections.Counter(r['primary_status'] for r in filled)
 known=sum(c[k] for k in KNOWN);selected=sum(r['selected'] for r in records)
 return dict(population_N=len(records),selected_N=selected,filled_N=len(filled),evaluable_N=known,
  **{k+'_N':c[k] for k in STATES},UP_FIRST_rate=ratio(c['UP_FIRST'],known),DOWN_FIRST_rate=ratio(c['DOWN_FIRST'],known),NEITHER_rate=ratio(c['NEITHER'],known),
  conservative_success=ratio(c['UP_FIRST'],len(filled)),evaluable_precision=ratio(c['UP_FIRST'],known),
  fill_rate_all_opportunities=ratio(len(filled),len(records)),fill_rate_selected=ratio(len(filled),selected),
  no_entry_N=len(records)-len(filled),no_entry_rate=ratio(len(records)-len(filled),len(records)),
  no_high_confidence_intent_N=sum(r.get('policy_status')=='NO_HIGH_CONFIDENCE_ENTRY' for r in records),
  unfilled_intent_N=sum(r['selected'] and not r['filled'] for r in records),unknown_filled_N=c['ORDER_UNKNOWN']+c['DATA_UNAVAILABLE'],
  empty_denominator_is_UNKNOWN=True)

def row_metrics(records,labels):
 known=[r for r in records if labels[r['row_id']]['primary_status'] in KNOWN]
 c=collections.Counter(r['opportunity'] for r in known)
 y=np.array([labels[r['row_id']]['primary_status']=='UP_FIRST' for r in known],dtype=int)
 s=np.array([r['raw_score'] for r in known]);w=np.array([1/c[r['opportunity']] for r in known])
 z=dict(total_rows=len(records),evaluable_rows=len(known),unknown_rows=len(records)-len(known),evaluable_opportunities=len(c),
  weight_sum=float(w.sum()),row_weight='one total evaluable OOF weight per Opportunity',calibration_certified=False)
 if not len(y) or len(np.unique(y))<2:
  return dict(z,PR_AUC_AP=None,PR_AUC_trapezoid=None,ROC_AUC=None,Brier=None,LogLoss=None)
 p=expit(s);precision,recall,_=precision_recall_curve(y,s,sample_weight=w)
 z.update(PR_AUC_AP=float(average_precision_score(y,s,sample_weight=w)),PR_AUC_trapezoid=float(auc(recall,precision)),
  ROC_AUC=float(roc_auc_score(y,s,sample_weight=w)),Brier=float(np.average((p-y)**2,weights=w)),
  LogLoss=float(np.average(np.logaddexp(0,s)-y*s,weights=w)),weighted_prevalence=float(np.average(y,weights=w)))
 return z

def capture_row(canon,record,t):
 sm=(canon.get('selectorOutcome') or {}).get('mfeEnd')
 if sm is None:return 'SELECTOR_OUTCOME_UNKNOWN'
 if sm<t:return 'NOT_SELECTOR_WINNER'
 if not record['filled']:return 'NO_ENTRY'
 mfe=record['quality'].get('session_end_MFE_pct')
 return 'OUTCOME_UNKNOWN' if mfe is None else 'CAPTURED' if mfe>=t else 'ENTERED_BUT_BELOW_THRESHOLD'

def plot_results(evaluation,incremental,support,curves):
 figdir=HERE/'FIGURES';figdir.mkdir(exist_ok=True)
 fig,ax=plt.subplots(figsize=(9,4.5));xx=np.arange(3);ap=[incremental['pooled'][f]['PR_AUC_AP'] for f in FAMILIES];roc=[incremental['pooled'][f]['ROC_AUC'] for f in FAMILIES]
 ax.bar(xx-.17,ap,.34,label='PR-AUC (AP)');ax.bar(xx+.17,roc,.34,label='ROC-AUC');ax.set_xticks(xx,FAMILIES);ax.set_ylim(0,1);ax.set_ylabel('AUC (unitless)');ax.legend();ax.set_title('Same model / folds / +2% before -1% target')
 fig.text(.02,.01,'Each arm N=65,312 rows, known N=23,457; Opportunity-weighted; evaluator-only / future-outcome-used',fontsize=8);fig.tight_layout(rect=(0,.05,1,1));fig.savefig(figdir/'C6_OOF_DISCRIMINATION.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,4.5))
 for f in FAMILIES:
  values=[p for p in curves if p['family']==f and p['evaluable_N']>=100 and p['represented_evaluable_sessions']>=10 and p['precision'] is not None]
  if values:ax.scatter([p['coverage']*100 for p in values],[p['precision']*100 for p in values],s=3,alpha=.35,label=f)
 for t in (80,85,90):ax.axhline(t,color='grey',linestyle='--',linewidth=.7)
 ax.set(xlabel='Selected Opportunity coverage (%)',ylabel='Train-side OOF evaluable precision (%)',ylim=(0,100),title='All precommitted threshold points meeting N/session support')
 ax.legend();fig.text(.02,.01,'Five train-inner-OOF pools per arm; known selected N>=100, evaluable sessions>=10; not outer-test tuning; evaluator-only',fontsize=8);fig.tight_layout(rect=(0,.05,1,1));fig.savefig(figdir/'C6_PRECISION_COVERAGE.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,4.5));arms=list(evaluation['arms']);bottom=np.zeros(len(arms))
 for status in STATES:
  vals=[evaluation['arms'][a]['safe_up'][status+'_N'] for a in arms];ax.bar(arms,vals,bottom=bottom,label=status);bottom+=vals
 ax.set_ylabel('Filled Opportunities (N)');ax.set_title('Fill-anchored +2% / -1% outcomes; empty arms are NO_ENTRY');ax.legend(fontsize=7,ncol=3)
 fig.text(.02,.01,'Each arm total N=2,155; baseline fills reused, only new first-passage target computed; evaluator-only / future-outcome-used',fontsize=8);fig.tight_layout(rect=(0,.06,1,1));fig.savefig(figdir/'C6_SAFE_UP_ENTRY_COUNTS.png',dpi=180);plt.close(fig)

def run():
 assert read(HERE/'C5_COMPLETION.json')['model_fits']==60
 canonical=read(CANON);assert sha(CANON)=='4b9afd72ccfff0b557fb4a5e067ac122ace90ae501d15a79627a89af9554a01e'
 canon={r['opportunity']:r for r in canonical};assert len(canon)==2155
 labels={};fill_labels={}
 keep=('row_id','opportunity','session','intent_minute','active_delay','fill_id','fill_minute','fill_price','primary_status','strictly_later_high_pct','saved_session_end_MFE','saved_session_end_MAE','saved_30','saved_60','remaining_active_minutes','source_coverage')
 for full in lines(HERE/'FIRST_PASSAGE_LABELS.jsonl.gz'):
  if full['opportunity'] in canon:
   x={k:full.get(k) for k in keep};x['primary']=full['grid']['+2/-1'];labels[x['row_id']]=x
   if x['fill_id'] is not None:fill_labels[x['fill_id']]=x
 assert len(labels)==65312
 raw=read(SUB/'raw-paths-evaluator-only.json.gz');geometry={ (x['arm'],x['opportunity']):x for x in lines(GEOM/'GEOMETRY_ROWS.jsonl.gz')}
 arms={};basereceipt={};scorecards={};base_new_anchor=0;base_reused=0;price_mismatches=[]
 for arm,p in BASE_PATHS.items():
  assert sha(p)==BASE_SHA[arm];saved=read(p);assert {x['opportunity'] for x in saved}==set(canon)
  sp=GEOM/f'FROZEN_ARTIFACT_MEMBERS/{arm}_SCORECARD.original.json.gz';assert sha(sp)==SCORE_SHA[arm];scorecards[arm]=read(sp)
  records=[]
  for x in saved:
   oid=x['opportunity'];g=geometry[(arm,oid)];fill=x['entryId'] is not None and x['price'] is not None
   record=dict(arm=arm,opportunity=oid,session=x['session'],symbol=x['symbol'],selected=x.get('intentMinute') is not None,filled=fill,
    fill_id=x['entryId'],fill_minute=x['entryMinute'],fill_price=x['price'],intent_minute=x.get('intentMinute'),outer_fold=None,
    policy_status='SAVED_BASELINE_INTENT',primary_status='NO_ENTRY',primary=None,evaluator_only=True,future_decision_use=False,
    quality=dict(entry_to_strictly_later_high_pct=g.get('entry_to_later_high_pct'),session_end_MFE_pct=g.get('saved_entry_mfe_end_pct'),
     session_end_MAE_pct=g.get('entry_mae_end_pct'),MAE30_pct=g.get('entry_mae_30_pct'),MAE60_pct=g.get('entry_mae_60_pct'),
     MFE30_pct=(x['labels'].get('30') or {}).get('MFE'),MFE60_pct=(x['labels'].get('60') or {}).get('MFE'),
     selector_to_entry_active_minutes=g.get('selector_to_entry_active_minutes'),remaining_active_minutes=None),old_quality_values_reused=True)
   if fill:
    a=fill_labels.get(x['entryId'])
    if a is not None and abs(a['fill_price']-x['price'])<=max(1e-10,abs(x['price'])*1e-12):
     record['primary']=a['primary'];record['primary_label_source']='EXACT_SAVED_CANDIDATE_FILL_LABEL';base_reused+=1
    else:
     if a is not None:price_mismatches.append(dict(arm=arm,entry_id=x['entryId']))
     path=raw[oid];bar=next((b for b in path['today'] if int(b[0])==x['entryMinute']),None)
     assert bar is not None and abs(bar[1]*1.0005-x['price'])<=max(1e-10,abs(x['price'])*1e-12),'BASELINE_CANONICAL_FILL_BASIS_MISMATCH'
     record['primary']=primary_original(x['session'],x['entryMinute'],x['price'],path,x['labels'].get('status'))
     record['primary_label_source']='NEW_PRIMARY_ONLY_FOR_SAVED_BASELINE_FILL';base_new_anchor+=1
    record['primary_status']=record['primary']['status']
   record['quality']['time_to_up_active_minutes']=(record['primary'] or {}).get('time_to_up_active') if record['primary_status']=='UP_FIRST' else None
   records.append(record)
  arms[arm]=records;basereceipt[arm]=dict(original_records_sha256=sha(p),old_scorecard_sha256=sha(sp),old_entry_decisions_regenerated=0,old_geometry_recomputed=0,old_capture_aggregate_recomputed=0)
 assert not price_mismatches,'BASELINE_LABEL_FILL_PRICE_MISMATCH'
 for arm in NEW_ARMS:arms[arm]=[]
 for x in lines(HERE/'ENTRY_CANDIDATE_RECORDS.jsonl.gz'):
  lab=labels[x['intent_row_id']] if x['intent_row_id'] is not None else None;filled=lab is not None and lab['fill_id'] is not None;c=canon[x['opportunity']]
  q=metric_quality(lab) if lab else {k:None for k in ('entry_to_strictly_later_high_pct','session_end_MFE_pct','session_end_MAE_pct','MAE30_pct','MFE30_pct','MAE60_pct','MFE60_pct','remaining_active_minutes')}
  q['selector_to_entry_active_minutes']=None
  if filled:
   m=lab['fill_minute'];sel=c['selectorMinute'];last=900 if x['session']<'2024-11-05' else 925
   q['selector_to_entry_active_minutes']=sum(max(0,min(m,hi)-max(sel,lo)) for lo,hi in ((540,690),(750,last)))
  q['time_to_up_active_minutes']=lab['primary'].get('time_to_up_active') if filled and lab['primary_status']=='UP_FIRST' else None
  arms[x['arm']].append(dict(arm=x['arm'],opportunity=x['opportunity'],session=x['session'],symbol=c['symbol'],selected=x['intent_row_id'] is not None,filled=filled,
   fill_id=lab['fill_id'] if filled else None,fill_minute=lab['fill_minute'] if filled else None,fill_price=lab['fill_price'] if filled else None,
   intent_minute=x['intent_minute'],intent_row_id=x['intent_row_id'],outer_fold=x['outer_fold'],policy_status=x['status'],selected_family=x.get('selected_family'),
   primary_status=lab['primary_status'] if filled else 'NO_ENTRY',primary=lab['primary'] if filled else None,quality=q,evaluator_only=True,future_decision_use=False))
 for arm,rs in arms.items():assert len(rs)==2155 and {x['opportunity'] for x in rs}==set(canon)
 summary=read(GEOM/'GEOMETRY_SUMMARY.json');evaluation=dict(status='C6_OUTER_OOF_DESCRIPTIVE_EVALUATION_COMPLETE',population_N=2155,sessions=58,symbols=950,
  primary='SAFE_UP_2_BEFORE_DOWN_1',arms={},baseline_reuse=basereceipt,new_model_fits=0,new_threshold_tuning=0,bootstrap=0,productionReady=False,
  comparison_scope='Alternative Entry worlds on the same Opportunity population; do not sum arms as independent trades.',
  old_delay_clock='Baseline Geometry retained original PM endpoint930; new R1 candidate contract endpoint925; no relabeling of old geometry.',
  unknown_policy='Unknown outcomes are retained and never zero-filled; no-entry quality and zero-denominator precision are null.')
 for arm,rs in arms.items():
  safe=safe_summary(rs)
  if arm in BASE_PATHS:
   quality=dict(existing_geometry=copy.deepcopy(summary['continuous'][arm]),existing_scorecard_horizons=copy.deepcopy(scorecards[arm]['overall']['horizons']),recomputed=False)
   capture=copy.deepcopy(scorecards[arm]['overall']['capture'])
  else:
   quality={k:stats([r['quality'].get(k) for r in rs],len(rs)) for k in rs[0]['quality']};capture={}
   for t in range(1,6):
    cc=collections.Counter(capture_row(canon[r['opportunity']],r,t) for r in rs);den=cc['CAPTURED']+cc['NO_ENTRY']+cc['ENTERED_BUT_BELOW_THRESHOLD']+cc['OUTCOME_UNKNOWN']
    assert den==scorecards['IMMEDIATE']['overall']['capture'][str(t)]['selectorWinnerDenominator']
    capture[str(t)]=dict(selectorWinnerDenominator=den,captured=cc['CAPTURED'],noEntry=cc['NO_ENTRY'],belowThreshold=cc['ENTERED_BUT_BELOW_THRESHOLD'],unknownEntered=cc['OUTCOME_UNKNOWN'],
     missed=cc['NO_ENTRY']+cc['ENTERED_BUT_BELOW_THRESHOLD'],ratePct=100*cc['CAPTURED']/den,selectorOutcomeUnknown=cc['SELECTOR_OUTCOME_UNKNOWN'])
  evaluation['arms'][arm]=dict(safe_up=safe,quality=quality,capture=capture,quality_source='HASH_VERIFIED_EXISTING_AGGREGATES' if arm in BASE_PATHS else 'NEW_CANDIDATE_SAVED_FILL_LABELS')
 oof={f:list(lines(HERE/f'OOF_{f}.jsonl.gz')) for f in FAMILIES}
 incremental=dict(status='SAME_MODEL_SPLIT_TARGET_COMPARISON',pooled={},by_outer_fold={},by_session={},differences={},
  Brier_LogLoss_scope='Uncalibrated sigmoid(raw logit), diagnostic evaluator only; never absolute Entry probability.',calibration_certified=False,productionReady=False)
 for f,rs in oof.items():
  incremental['pooled'][f]=row_metrics(rs,labels);incremental['by_outer_fold'][f]={str(k):row_metrics([r for r in rs if r['outer_fold']==k],labels) for k in range(1,6)}
  by=collections.defaultdict(list)
  for r in rs:by[r['session']].append(r)
  incremental['by_session'][f]={s:row_metrics(rr,labels) for s,rr in sorted(by.items())}
 for a,b in (('H1','H0'),('H2','H0'),('H2','H1')):
  incremental['differences'][a+'-'+b]={k:incremental['pooled'][a][k]-incremental['pooled'][b][k] for k in ('PR_AUC_AP','PR_AUC_trapezoid','ROC_AUC','Brier','LogLoss')}
 selection=read(HERE/'THRESHOLD_SELECTION_RECEIPT.json');curves=list(lines(HERE/'THRESHOLD_CURVES.jsonl.gz'));support=[]
 for x in selection['family_selections']:
  ps=[p for p in curves if p['family']==x['family'] and p['outer_fold']==x['outer_fold'] and p['evaluable_N']>=100 and p['represented_evaluable_sessions']>=10]
  safe_ps=[p for p in ps if p['DOWN_FIRST_rate']<=.1]
  support.append(dict(family=x['family'],outer_fold=x['outer_fold'],inner_OOF_opportunities=x['inner_OOF_opportunities'],threshold_points=x['threshold_boundaries_evaluated'],
   support_eligible_points=len(ps),support_and_down_gate_points=len(safe_ps),maximum_precision_with_N_and_session_support=max((p['precision'] for p in ps),default=None),
   maximum_precision_with_support_and_down_gate=max((p['precision'] for p in safe_ps),default=None),
   target90_feasible=x['targets']['0.9'] is not None,target85_feasible=x['targets']['0.85'] is not None,target80_feasible=x['targets']['0.8'] is not None,
   selected_operating_point=x['selected_operating_point'],descriptive_only_not_new_threshold_selection=True))
 incremental['operating_point_support']=support
 paired={};byarm={a:{r['opportunity']:r for r in rs} for a,rs in arms.items()}
 for a,b in itertools.combinations(arms,2):
  contingency=collections.Counter();common=[]
  for oid in canon:
   ra,rb=byarm[a][oid],byarm[b][oid];contingency[ra['primary_status']+'|'+rb['primary_status']]+=1
   if ra['filled'] and rb['filled']:common.append((ra,rb))
  deltas={k:stats([rb['quality'].get(k)-ra['quality'].get(k) for ra,rb in common if ra['quality'].get(k) is not None and rb['quality'].get(k) is not None],len(common)) for k in ('entry_to_strictly_later_high_pct','session_end_MAE_pct','selector_to_entry_active_minutes')}
  capture_pair={str(t):dict(collections.Counter(capture_row(canon[oid],byarm[a][oid],t)+'|'+capture_row(canon[oid],byarm[b][oid],t) for oid in canon if (canon[oid].get('selectorOutcome') or {}).get('mfeEnd') is not None and canon[oid]['selectorOutcome']['mfeEnd']>=t)) for t in range(1,6)}
  paired[a+'__'+b]=dict(population_N=2155,common_filled_N=len(common),common_evaluable_N=sum(ra['primary_status'] in KNOWN and rb['primary_status'] in KNOWN for ra,rb in common),
   primary_contingency=dict(contingency),quality_delta_b_minus_a=deltas,capture_contingency=capture_pair,independent_trades=False)
 concentration={}
 for a,rs in arms.items():
  chosen=[r for r in rs if r['filled']];c={}
  for key in ('session','symbol'):
   counts=collections.Counter(r[key] for r in chosen);N=len(chosen)
   c[key]=dict(filled_N=N,unique_N=len(counts),top20=[dict(value=k,N=v,share=ratio(v,N)) for k,v in counts.most_common(20)],max_share=max(counts.values())/N if N else None)
  c['session_safe_up']={s:safe_summary([r for r in rs if r['session']==s]) for s in sorted({r['session'] for r in rs})}
  concentration[a]=c
 all_no_candidate=all(x['selected_operating_point'] is None for x in selection['family_selections'])
 evaluation['research_status']='SAFE_UPSIDE_ENTRY_NO_HIGH_PRECISION_CANDIDATE' if all_no_candidate else 'DEVELOPMENT_OPERATING_POINT_EXISTS_REQUIRES_AUDIT'
 evaluation['fresh_validation_direction']='Do not open Fresh Validation without a supported development operating point.' if all_no_candidate else 'FRESH_VALIDATION_REQUIRED; no automatic promotion.'
 evaluation['baseline_primary_label_reuse']=dict(reused_saved_fill_labels=base_reused,new_primary_only_baseline_fill_evaluations=base_new_anchor,old_geometry_or_capture_regenerated=0,old_entry_decisions_regenerated=0,fill_price_mismatches=price_mismatches)
 incremental['State_incremental_deployment_claim']='NOT_ESTABLISHED_NO_FEASIBLE_OPERATING_POINT' if all_no_candidate else 'REQUIRES_C7_AND_FRESH_VALIDATION'
 write('ENTRY_EVALUATION.json',evaluation);write('STATE_INCREMENTAL_VALUE.json',incremental);write('MATCHED_COMPARISON.json',paired);write('SESSION_SYMBOL_CONCENTRATION.json',concentration)
 write('OPERATING_POINT_SUPPORT.json',dict(status='DESCRIPTIVE_FIXED_GRID_SUPPORT',rows=support,secondary_target_search=0,outer_label_selection=0))
 write('BASELINE_PRIMARY_LABEL_RECEIPT.json',dict(status='NEW_TARGET_ONLY_OLD_ARMS',**evaluation['baseline_primary_label_reuse'],source_raw_sha256=sha(SUB/'raw-paths-evaluator-only.json.gz'),baseline_record_hashes=BASE_SHA,scorecard_hashes=SCORE_SHA,new_candidate_label_creation_passes=0,new_old_policy_replays=0,provider_requests=0,new_fits=0))
 gzwrite('C6_EVALUATED_ENTRY_RECORDS.jsonl.gz',itertools.chain.from_iterable(arms.values()))
 write('C6_EVALUATION_RECEIPT.json',dict(status=evaluation['research_status'],model_fits_total=60,model_fits_this_checkpoint=0,threshold_selections_this_checkpoint=0,old_geometry_recalculation=0,old_capture_aggregate_recalculation=0,
  arms=6,population_per_arm=2155,new_baseline_primary_only_anchors=base_new_anchor,matched_common_opportunity=True,bootstrap=0,provider_requests=0,orders=0,productionReady=False))
 plot_results(evaluation,incremental,support,curves)
 print(json.dumps(dict(status=evaluation['research_status'],pooled_metrics=incremental['pooled'],support=support,baseline_primary_reuse=evaluation['baseline_primary_label_reuse']),allow_nan=False),flush=True)

if __name__=='__main__':run()
