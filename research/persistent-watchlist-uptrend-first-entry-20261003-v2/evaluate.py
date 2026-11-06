"""OOF FIRST ENTRY evaluation, frozen candidate selection; no model fits."""
import collections
from scipy.stats import spearmanr
from common import *
from teacher import future_metrics
METRICS={'entry_to_high_pct':'remaining_upside_pct','upside_retention_pct':'upside_retention_pct','pre_peak_mae_abs_pct':'pre_peak_mae_abs_pct','path_efficiency':'path_efficiency','total_variation_pct':'total_variation_pct','reversal_count':'reversal_count','time_to_peak_active_min':'time_to_peak_active_min','selector_to_entry_active_delay':'selector_to_entry_active_delay'}
def arm_summary(rs):
 entered=[r for r in rs if r['entry_status']=='FIRST_ENTRY'];out={'watch_N':len(rs),'FIRST_ENTRY_N':len(entered),'no_entry_N':len(rs)-len(entered),'entry_rate_pct':100*len(entered)/len(rs) if rs else None,'path_evaluable_N':sum(r.get('pre_peak_path_complete',False) for r in entered),'path_unknown_N':sum(not r.get('pre_peak_path_complete',False) for r in entered),'remaining_high_unknown_N':sum(r.get('remaining_upside_pct') is None for r in entered),'metrics':{k:summarize([r.get(v) for r in entered]) for k,v in METRICS.items()}}
 return out
def winners(rs,k):
 selected=[r for r in rs if r.get('selector_to_high_pct') is not None and r['selector_to_high_pct']>=k];entered=[r for r in selected if r['entry_status']=='FIRST_ENTRY'];hit=sum(r.get('first_upside',{}).get(str(k),{}).get('status')=='HIT_CONFIRMED' for r in entered);unknown=sum(r.get('first_upside',{}).get(str(k),{}).get('status','UNKNOWN')=='UNKNOWN' for r in entered)
 return {'threshold_pct':k,'selector_winner_denominator':len(selected),'FIRST_ENTRY_N':len(entered),'no_entry_N':len(selected)-len(entered),'entry_after_same_threshold_hit_N':hit,'unknown_N':unknown,'entry_confirmed_no_same_threshold_hit_N':len(entered)-hit-unknown,'capture_rate_pct':100*hit/len(selected) if selected else None,'entry_preservation_rate_pct':100*len(entered)/len(selected) if selected else None}
def baseline_records(raw,ws,geometry):
 out={};parity=[]
 for arm,file in [('IMMEDIATE',SCRATCH/'downloads/immediate.json.gz'),('R1',SCRATCH/'downloads/R1_ENTRY_RECORDS.json.gz')]:
  saved={r['opportunity']:r for r in read(file)};records=[]
  assert len(saved)==len(ws)==2155
  for w in ws:
   old=saved[w['watch_key']];g=geometry[(arm,w['watch_key'])];r={'watch_key':w['watch_key'],'session':w['session'],'symbol':w['symbol'],'first_selector_event':w['first_selector_event'],'selector_minute':w['selector_minute'],'selector_price':w['selector_price'],'family':arm,'policy':'SAVED_BASELINE','selector_to_high_pct':g['selector_to_high_pct'] if g['canonical_full_session_evaluable'] else None,'selector_bucket':bucket(g['selector_to_high_pct'] if g['canonical_full_session_evaluable'] else None),'record_lineage':'original frozen fill and canonical Geometry reused; only new Q/D/TV/reversal teacher metrics computed'}
   assert g['selector_minute']==w['selector_minute'] and g['selector_price']==w['selector_price']
   if old['entryMinute'] is None:r.update(entry_status='NO_ENTRY_SAVED_UNFILLED',fill_minute=None,fill_price=None)
   else:
    assert old['entryMinute']==g['entry_minute'] and old['price']==g['entry_price']
    m=future_metrics(w['session'],raw[w['watch_key']]['today'],old['entryMinute'],old['price']);r.update(m);calc=m['remaining_upside_pct'];existing=g['entry_to_later_high_pct'];delta=abs(calc-existing) if calc is not None and existing is not None else None
    parity.append({'arm':arm,'watch_key':w['watch_key'],'both_available':delta is not None,'mismatch':(delta>1e-8) if delta is not None else False,'availability_difference':(calc is None)!=(existing is None),'absolute_difference':delta})
    r.update(entry_status='FIRST_ENTRY',fill_minute=old['entryMinute'],fill_price=old['price'],remaining_upside_pct=existing,upside_retention_pct=g['upside_retention_pct'],selector_to_entry_active_delay=active_elapsed(w['session'],w['selector_minute'],old['entryMinute']),canonical_saved_selector_to_entry_active_minutes=g['selector_to_entry_active_minutes'],canonical_saved_entry_to_high_active_minutes=g['entry_to_high_active_minutes'])
   records.append(r)
  out[arm]=records;write_lines(HERE/f'BASELINE_{arm}_PAIRED_FIRST_WATCH.jsonl.gz',records)
 write(HERE/'BASELINE_GEOMETRY_REUSE_RECEIPT.json',{'saved_at_jst':now(),'canonical_event_reference_N':2155,'primary_watch_N':2155,'population_relationship':'canonical saved opportunities already use first-selector unique(session,symbol); panels kept separate despite coincident N','old_canonical_geometry_recalculated':False,'geometry_fields_reused':['Entry→High','upside retention','Selector MFE'], 'new_metrics_from_same_saved_fills':['clean Q','pre-peak D','TV','reversal count','RC2 active clock excluding closing auction pause; saved original clocks retained separately'],'geometry_parity_checks':sum(x['both_available'] for x in parity),'geometry_mismatch_N':sum(x['mismatch'] for x in parity),'geometry_availability_difference_N':sum(x['availability_difference'] for x in parity),'original_R1_records_sha256':sha(SCRATCH/'downloads/R1_ENTRY_RECORDS.json.gz'),'original_IMMEDIATE_records_sha256':sha(SCRATCH/'downloads/immediate.json.gz'),'original_geometry_sha256':sha(INPUT/'geometry_rows.jsonl.gz'),'private_parity_records':'BASELINE_GEOMETRY_PARITY.jsonl.gz'})
 write_lines(HERE/'BASELINE_GEOMETRY_PARITY.jsonl.gz',parity)
 return out
def daily(rs,ws):
 rows=[]
 for d in sorted({w['session'] for w in ws}):
  ww=[w for w in ws if w['session']==d];rr=[r for r in rs if r['session']==d];ee=[r for r in rr if r['entry_status']=='FIRST_ENTRY'];timeline=[]
  for w in ww:timeline.append((w['selector_minute'],0,1))
  for r in ee:timeline.append((r['fill_minute'],1,-1))
  active=peak=0
  for t,order,delta in sorted(timeline):active+=delta;peak=max(peak,active)
  simultaneous=collections.Counter(r['fill_minute'] for r in ee);clock=collections.Counter('%02d:%02d'%divmod(r['fill_minute'],60) for r in ee);N=len(ee)
  rows.append({'session':d,'selector_event_N':sum(1+len(w['refresh_minutes']) for w in ww),'unique_active_watch_N':len(ww),'peak_active_watchlist_size':peak,'FIRST_ENTRY_N':N,'unique_entered_symbols_N':len({r['symbol'] for r in ee}),'no_entry_watch_N':len(ww)-N,'entry_rate_pct':100*N/len(ww),'entry_day_bucket':'0' if N==0 else '1–5' if N<=5 else '6–10' if N<=10 else '11–15' if N<=15 else '>15','entry_clock_distribution':dict(clock),'max_simultaneous_FIRST_ENTRY_demand':max(simultaneous.values(),default=0),'simultaneous_FIRST_ENTRY_demand':{str(t):n for t,n in sorted(simultaneous.items())}})
 return {'session_N':len(rows),'FIRST_ENTRY_per_session':summarize([x['FIRST_ENTRY_N'] for x in rows]),'day_buckets':dict(collections.Counter(x['entry_day_bucket'] for x in rows)),'zero_entry_days':sum(x['FIRST_ENTRY_N']==0 for x in rows),'daily':rows,'no_capital_capacity_assumed':True}
def paired(rs,baseline):
 by={r['watch_key']:r for r in baseline};out={}
 for name,field in METRICS.items():
  pairs=[(r.get(field),by[r['watch_key']].get(field)) for r in rs if r['entry_status']=='FIRST_ENTRY' and by[r['watch_key']]['entry_status']=='FIRST_ENTRY' and r.get(field) is not None and by[r['watch_key']].get(field) is not None]
  out[name]={'paired_N':len(pairs),'new':summarize([a for a,b in pairs]),'baseline':summarize([b for a,b in pairs]),'new_minus_baseline':summarize([a-b for a,b in pairs])}
 return out
def head_metrics():
 out={}
 for family in ('P0','P1'):
  out[family]={}
  for head in HEADS:
   rows=[r for r in lines(HERE/f'OOF_{family}_{head}.jsonl.gz') if r['actual_training_target'] is not None];p=np.asarray([r['prediction'] for r in rows]);y=np.asarray([r['actual_training_target'] for r in rows]);corr=spearmanr(p,y).statistic
   dec=[]
   for k in range(10):
    rr=[r for r in rows if min(9,int(r['percentile']*10))==k];dec.append({'training_percentile_decile':k+1,'N':len(rr),'prediction':summarize([r['prediction'] for r in rr]),'actual_target':summarize([r['actual_training_target'] for r in rr])})
   sessions=[]
   for d in sorted({r['session'] for r in rows}):
    rr=[r for r in rows if r['session']==d];pp=[r['prediction'] for r in rr];yy=[r['actual_training_target'] for r in rr];c=spearmanr(pp,yy).statistic
    sessions.append({'session':d,'N':len(rr),'MAE':float(np.mean(np.abs(np.asarray(pp)-yy))),'Spearman':float(c) if np.isfinite(c) else None})
   out[family][head]={'N':len(rows),'MAE':float(np.mean(abs(p-y))),'Spearman':float(corr) if np.isfinite(corr) else None,'prediction_decile_actual_target':dec,'session_stability':sessions}
 return out
def candidates(arms,kind):
 # Missing Q/D never gets artificially good rank. Fully specified rule ordering.
 def median(s,k,default):
  v=s['metrics'][k]['median'];return default if v is None else v
 summaries={k:arm_summary(v) for k,v in arms.items()};captures={k:{str(z):winners(v,z)['capture_rate_pct'] for z in (3,5)} for k,v in arms.items()}
 def rank(k):
  s=summaries[k];q=median(s,'path_efficiency',-float('inf'));d=median(s,'pre_peak_mae_abs_pct',float('inf'));u=median(s,'entry_to_high_pct',-float('inf'));c5=captures[k]['5'] or 0;c3=captures[k]['3'] or 0
  return (-q,d,-u,-c5,-s['entry_rate_pct'],k) if kind=='QUALITY' else (-q,d,-c3,-s['entry_rate_pct'],k)
 def choose(keys):
  eligible=list(keys)
  if kind=='BALANCED':
   mx=max(captures[k]['5'] or 0 for k in eligible);eligible=[k for k in eligible if (captures[k]['5'] or 0)>=mx-2]
  winner=sorted(eligible,key=rank)[0];return {'candidate':winner,'eligible_policy_N':len(eligible),'eligible_policies':eligible,'summary':summaries[winner],'captures':captures[winner]}
 return {'saved_at_jst':now(),'kind':kind,'global':choose(arms),'per_family':{f:choose([k for k in arms if k.startswith(f+'_')]) for f in ('P0','P1')},'all_fixed_policy_summaries':summaries,'all_fixed_policy_capture':captures,'development_candidate_only':True,'promotion':False,'selection_did_not_use_profit':True,'safety':SAFETY}
def run():
 ws=[w for w in lines(HERE/'WATCH_RECORDS.jsonl.gz') if w['canonical']];raw=read(INPUT/'raw_paths_selected.json.gz');geometry={(r['arm'],r['opportunity']):r for r in lines(INPUT/'geometry_rows.jsonl.gz')};assert len(geometry)==4310
 arms={}
 for p in POLICIES:
  for f in ('P0','P1'):
   rs=[r for r in lines(HERE/f'FIRST_ENTRY_{p}.jsonl.gz') if r['family']==f];assert len(rs)==len(ws)==2155
   for r in rs:
    g=geometry[('IMMEDIATE',r['watch_key'])];assert r['first_selector_event']==next(w['first_selector_event'] for w in ws if w['watch_key']==r['watch_key'])
    r['selector_to_high_pct']=g['selector_to_high_pct'] if g['canonical_full_session_evaluable'] else None;r['selector_bucket']=bucket(r['selector_to_high_pct']);r['upside_retention_pct']=100*r['remaining_upside_pct']/r['selector_to_high_pct'] if r.get('remaining_upside_pct') is not None and r['selector_to_high_pct'] is not None and r['selector_to_high_pct']>0 else None
    for k in ('selector_global_high_minute','selector_global_high_price','selector_global_low_minute','selector_global_low_price'):r[k]=g[k]
    low=g['selector_global_low_price'];high=g['selector_global_high_price'];lm=g['selector_global_low_minute'];hm=g['selector_global_high_minute']
    r['selector_to_global_low_pct']=100*(low/r['selector_price']-1) if low is not None else None;r['global_low_to_global_high_pct']=100*(high/low-1) if low is not None and high is not None and lm<hm else None;r['global_low_high_order']='LOW_BEFORE_HIGH' if lm is not None and hm is not None and lm<hm else 'NOT_STRICTLY_ORDERED_OR_UNKNOWN'
   arms[f+'_'+p]=rs
 # Persist evaluator enrichment while sealed threshold/intent lineage remains intact.
 for p in POLICIES:write_lines(HERE/f'FIRST_ENTRY_{p}.jsonl.gz',arms['P0_'+p]+arms['P1_'+p])
 baselines=baseline_records(raw,ws,geometry);allarms={**arms,**baselines};summaries={k:arm_summary(rs) for k,rs in allarms.items()}
 buckets={}
 for name,rs in arms.items():buckets[name]={b:arm_summary([r for r in rs if r['selector_bucket']==b]) for b in ('<1%','1–<2%','2–<3%','3–<4%','4–<5%','>=5%','missing')}
 write(HERE/'SELECTOR_WATCH_BUCKET_EVALUATION.json',{'saved_at_jst':now(),'unit':'unique session|symbol; first-selector anchor','selector_MFE_lineage':'saved canonical full-session evaluator reused, never a feature','population_N':2155,'source_partiality_separate_from_canonical_MFE':True,'policies':buckets,'safety':SAFETY})
 winner_panels={name:{str(k):winners(rs,k) for k in range(1,6)} for name,rs in allarms.items()};write(HERE/'WINNER_PRESERVATION.json',{'saved_at_jst':now(),'denominator':'all canonical first-selector winners, including no-entry; unknown not silently dropped','thresholds':[1,2,3,4,5],'panels':winner_panels,'safety':SAFETY})
 comparisons={name:{b:paired(rs,bs) for b,bs in baselines.items()} for name,rs in arms.items()}
 write(HERE/'ENTRY_HIGH_EVALUATION.json',{'saved_at_jst':now(),'primary_watch_summaries':summaries,'paired_comparisons':comparisons,'canonical_2155_event_reference':{b:{'watch_N':2155,'FIRST_ENTRY_N':arm_summary(baselines[b])['FIRST_ENTRY_N'],'entry_to_high_pct':summarize([g['entry_to_later_high_pct'] for (arm,key),g in geometry.items() if arm==b]),'upside_retention_pct':summarize([g['upside_retention_pct'] for (arm,key),g in geometry.items() if arm==b]),'selector_to_entry_active_minutes':summarize([g['selector_to_entry_active_minutes'] for (arm,key),g in geometry.items() if arm==b]),'entry_to_high_active_minutes':summarize([g['entry_to_high_active_minutes'] for (arm,key),g in geometry.items() if arm==b]),'saved_geometry_only':True} for b in baselines},'reference_population_relation':'same N because canonical first-selection opportunities already unique watch anchors; displayed separately, never added','retention_definition_all_arms':'100*Entry strictly-later observed High pct / saved selector MFE pct; positive denominator only; exact old Geometry formula reused','primary_clock':'dated RC2 regular activity, excludes lunch and closing auction pause; canonical reference preserves original clock','safety':SAFETY})
 write(HERE/'PATH_QUALITY_EVALUATION.json',{'saved_at_jst':now(),'complete_pre_peak_path_only':True,'summaries':{k:{z:v for z,v in s.items() if z in ('watch_N','FIRST_ENTRY_N','path_evaluable_N','path_unknown_N','metrics')} for k,s in summaries.items()},'paired_comparisons':{k:{b:{m:v for m,v in values.items() if m in ('path_efficiency','pre_peak_mae_abs_pct','total_variation_pct','reversal_count')} for b,values in ps.items()} for k,ps in comparisons.items()},'missing_path_never_interpolated':True,'safety':SAFETY})
 write(HERE/'MAE_EVALUATION.json',{'saved_at_jst':now(),'summaries':{k:s['metrics']['pre_peak_mae_abs_pct'] for k,s in summaries.items()},'paired':{k:{b:ps[b]['pre_peak_mae_abs_pct'] for b in ps} for k,ps in comparisons.items()},'safety':SAFETY})
 repeat=read(HERE/'SELECTOR_REPEAT_AUDIT.json');daily_panels={k:daily(rs,ws) for k,rs in allarms.items()};write(HERE/'DAILY_FIRST_ENTRY_ACTIVITY.json',{'saved_at_jst':now(),'selector_events_per_session':summarize([r['selector_events'] for r in repeat['daily_primary']]),'unique_watches_per_session':summarize([r['unique_watch'] for r in repeat['daily_primary']]),'panels':daily_panels,'entry_count_is_outcome_not_gate':True,'safety':SAFETY})
 q=candidates(arms,'QUALITY');bal=candidates(arms,'BALANCED');write(HERE/'QUALITY_CANDIDATE.json',q);write(HERE/'BALANCED_CANDIDATE.json',bal)
 heads=head_metrics();delta={}
 for p in POLICIES:
  aa=summaries['P0_'+p];bb=summaries['P1_'+p];d={}
  for m in METRICS:
   a=aa['metrics'][m]['median'];b=bb['metrics'][m]['median'];d[m+'_median_P1_minus_P0']=b-a if a is not None and b is not None else None
  for k in (3,5):d[f'capture_ge{k}_pp_P1_minus_P0']=winner_panels['P1_'+p][str(k)]['capture_rate_pct']-winner_panels['P0_'+p][str(k)]['capture_rate_pct']
  d['entry_rate_pp_P1_minus_P0']=bb['entry_rate_pct']-aa['entry_rate_pct'];d['entries_per_session_P1_minus_P0']=daily_panels['P1_'+p]['FIRST_ENTRY_per_session']['mean']-daily_panels['P0_'+p]['FIRST_ENTRY_per_session']['mean'];delta[p]=d
 q0=q['per_family']['P0'];q1=q['per_family']['P1'];b0=bal['per_family']['P0'];b1=bal['per_family']['P1']
 # Descriptive evidence, never another operating-point or promotion search.
 p1_better_all_fixed=all(d['path_efficiency_median_P1_minus_P0'] is not None and d['path_efficiency_median_P1_minus_P0']>=0 and d['pre_peak_mae_abs_pct_median_P1_minus_P0']<=0 and d['capture_ge5_pp_P1_minus_P0']>=0 for d in delta.values())
 status='STATE9_INCREMENTAL_UPTREND_ENTRY_VALUE_OBSERVED_ON_DEVELOPMENT' if p1_better_all_fixed else 'STATE9_NO_INCREMENTAL_UPTREND_ENTRY_VALUE_ON_DEVELOPMENT'
 write(HERE/'STATE_INCREMENTAL_VALUE.json',{'saved_at_jst':now(),'status':status,'adopted_State9':False,'head_metrics':heads,'fixed_quantile_entry_deltas':delta,'per_family_quality_candidates':{'P0':q0['candidate'],'P1':q1['candidate']},'per_family_balanced_candidates':{'P0':b0['candidate'],'P1':b1['candidate']},'interpretation_rule':'clear non-worsening across all four fixed quantiles in median Q, median D and >=5 capture; otherwise no established incremental value; descriptive only','mixed_tradeoffs_kept_visible':True,'development_only':True,'safety':SAFETY})
 write(HERE/'EVALUATION_RECEIPT.json',{'saved_at_jst':now(),'primary_watches':2155,'policies':8,'baseline_arms':2,'QUALITY_candidate':q['global']['candidate'],'BALANCED_candidate':bal['global']['candidate'],'same_candidate':q['global']['candidate']==bal['global']['candidate'],'State_status':status,'profit_based_selection':False,'EXIT_calls':0,'reentry_calls':0,'safety':SAFETY})
 if (HERE/'CALENDAR_INTEGRITY_DIAGNOSIS.json').exists():
  for name in ['SELECTOR_WATCH_BUCKET_EVALUATION.json','WINNER_PRESERVATION.json','ENTRY_HIGH_EVALUATION.json','PATH_QUALITY_EVALUATION.json','MAE_EVALUATION.json','DAILY_FIRST_ENTRY_ACTIVITY.json','QUALITY_CANDIDATE.json','BALANCED_CANDIDATE.json','STATE_INCREMENTAL_VALUE.json','EVALUATION_RECEIPT.json']:
   artifact=read(HERE/name);artifact.update({'model_teacher_lineage_valid':False,'diagnostic_only':True,'blocking_status':'BLOCKED_SPLIT_OR_LINEAGE_MISMATCH','freeze_or_promotion_allowed':False})
   if name=='STATE_INCREMENTAL_VALUE.json':artifact.update({'formal_incremental_conclusion_available':False,'head_metrics_scope':'original masked target population, not corrected teacher OOF design'})
   write(HERE/name,artifact)
 print(json.dumps(read(HERE/'EVALUATION_RECEIPT.json'),ensure_ascii=False))
if __name__=='__main__':run()
