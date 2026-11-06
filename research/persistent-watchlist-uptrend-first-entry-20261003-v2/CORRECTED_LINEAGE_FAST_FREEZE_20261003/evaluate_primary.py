"""Minimum corrected FIRST ENTRY evidence. No selection or State-value study."""
from repair_utils import *
import numpy as np,collections
from common import bucket

METRICS={'entry_to_high_pct':'remaining_upside_pct','upside_retention_pct':'upside_retention_pct','pre_peak_mae_abs_pct':'pre_peak_mae_abs_pct','path_efficiency':'path_efficiency','selector_to_entry_active_delay':'selector_to_entry_active_delay'}
def median(values):
 x=[float(v) for v in values if v is not None and np.isfinite(v)]
 return {'N':len(x),'median':float(np.median(x)) if x else None}
def summary(rs):
 entered=[r for r in rs if r['entry_status']=='FIRST_ENTRY']
 return {'watch_N':len(rs),'FIRST_ENTRY_N':len(entered),'no_entry_N':len(rs)-len(entered),'entry_rate_pct':100*len(entered)/len(rs) if rs else None,'path_evaluable_N':sum(r.get('pre_peak_path_complete',False) for r in entered),'path_unknown_N':sum(not r.get('pre_peak_path_complete',False) for r in entered),'remaining_high_unknown_N':sum(r.get('remaining_upside_pct') is None for r in entered),'metrics':{k:median(r.get(v) for r in entered) for k,v in METRICS.items()}}
def winners(rs,k):
 ws=[r for r in rs if r.get('selector_to_high_pct') is not None and r['selector_to_high_pct']>=k];entered=[r for r in ws if r['entry_status']=='FIRST_ENTRY'];hits=sum(r.get('first_upside',{}).get(str(k),{}).get('status')=='HIT_CONFIRMED' for r in entered);unknown=sum(r.get('first_upside',{}).get(str(k),{}).get('status','UNKNOWN')=='UNKNOWN' for r in entered)
 return {'threshold_pct':k,'selector_winner_denominator':len(ws),'FIRST_ENTRY_N':len(entered),'no_entry_N':len(ws)-len(entered),'entry_after_same_threshold_hit_N':hits,'unknown_N':unknown,'entry_confirmed_no_same_threshold_hit_N':len(entered)-hits-unknown,'capture_rate_pct':100*hits/len(ws) if ws else None,'reference_only_not_freeze_optimization_gate':True}
def daily(rs,ws):
 out=[]
 for day in sorted({w['session'] for w in ws}):
  wday=[w for w in ws if w['session']==day];eday=[r for r in rs if r['session']==day and r['entry_status']=='FIRST_ENTRY'];n=len(eday);timeline=sorted([(w['selector_minute'],0,1) for w in wday]+[(r['fill_minute'],1,-1) for r in eday]);cur=peak=0
  for t,order,delta in timeline:cur+=delta;peak=max(cur,peak)
  counts=collections.Counter(r['fill_minute'] for r in eday)
  out.append({'session':day,'selector_event_N':sum(1+len(w['refresh_minutes']) for w in wday),'unique_active_watch_N':len(wday),'peak_active_watchlist_size':peak,'FIRST_ENTRY_N':n,'unique_entered_symbols_N':len({r['symbol'] for r in eday}),'no_entry_watch_N':len(wday)-n,'entry_rate_pct':100*n/len(wday),'entry_day_bucket':'0' if n==0 else '1–5' if n<=5 else '6–10' if n<=10 else '11–15' if n<=15 else '>15','max_simultaneous_FIRST_ENTRY_demand':max(counts.values(),default=0),'simultaneous_FIRST_ENTRY_demand':{str(t):n for t,n in sorted(counts.items())}})
 nums=[r['FIRST_ENTRY_N'] for r in out]
 return {'session_N':len(out),'FIRST_ENTRY_per_session':{'N':len(nums),'mean':float(np.mean(nums)),'median':float(np.median(nums))},'zero_entry_days':sum(n==0 for n in nums),'day_buckets':dict(collections.Counter(r['entry_day_bucket'] for r in out)),'maximum_simultaneous_FIRST_ENTRY':max(r['max_simultaneous_FIRST_ENTRY_demand'] for r in out),'daily':out,'capacity_gate_applied':False}

def run():
 ws=[w for w in rows(BASE/'WATCH_RECORDS.jsonl.gz') if w['canonical']];bywatch={w['watch_key']:w for w in ws};geometry={(r['arm'],r['opportunity']):r for r in rows(SCRATCH/'persistent_sources/geometry_rows.jsonl.gz')};arms={}
 for p in POLICIES:
  records=list(rows(HERE/f'FIRST_ENTRY_{p}.jsonl.gz'))
  for r in records:
   g=geometry[('IMMEDIATE',r['watch_key'])];assert r['first_selector_event']==bywatch[r['watch_key']]['first_selector_event'] and g['selector_minute']==r['selector_minute'] and g['selector_price']==r['selector_price']
   r['selector_to_high_pct']=g['selector_to_high_pct'] if g['canonical_full_session_evaluable'] else None;r['selector_bucket']=bucket(r['selector_to_high_pct']);r['upside_retention_pct']=100*r['remaining_upside_pct']/r['selector_to_high_pct'] if r.get('remaining_upside_pct') is not None and r['selector_to_high_pct'] is not None and r['selector_to_high_pct']>0 else None
  write_rows(HERE/f'FIRST_ENTRY_{p}.jsonl.gz',records)
  for f in ['P0','P1']:
   arms[f+'_'+p]=[r for r in records if r['family']==f];assert len(arms[f+'_'+p])==len(ws)==2155
 summaries={k:summary(v) for k,v in arms.items()};buckets={k:{b:summary([r for r in v if r['selector_bucket']==b]) for b in ['<1%','1–<2%','2–<3%','3–<4%','4–<5%','>=5%','missing']} for k,v in arms.items()};capture={k:{str(i):winners(v,i) for i in range(1,6)} for k,v in arms.items()};activity={k:daily(v,ws) for k,v in arms.items()}
 shared={'document_id':DOCUMENT_ID,'saved_at_jst':now(),'Primary_Freeze_Target':'P1_Q70','candidate_reselection':0,'State_incremental_study_reopened':False,'safety':SAFETY}
 write(HERE/'SELECTOR_WATCH_BUCKET_EVALUATION.json',{**shared,'policies':buckets,'unit':'watch first-selector anchor','selector_bucket_future_evaluator_only':True})
 write(HERE/'WINNER_PRESERVATION.json',{**shared,'panels':capture,'capture_is_reference_only':True})
 write(HERE/'DAILY_FIRST_ENTRY_ACTIVITY.json',{**shared,'panels':activity})
 key='P1_Q70';s=summaries[key];a=activity[key];p=arms[key]
 write_rows(HERE/'P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz',p)
 primary={**shared,'unit':'unique session|symbol, first-selector anchor','population':'existing chronological outer OOF development sessions only','session_N':a['session_N'],'Activity':{'watch_N':s['watch_N'],'FIRST_ENTRY_N':s['FIRST_ENTRY_N'],'no_entry_N':s['no_entry_N'],'mean_Entry_per_session':a['FIRST_ENTRY_per_session']['mean'],'median_Entry_per_session':a['FIRST_ENTRY_per_session']['median'],'Entry_rate_pct':s['entry_rate_pct'],'zero_Entry_session_N':a['zero_entry_days'],'Selector_to_Entry_delay_active_min_median':s['metrics']['selector_to_entry_active_delay']['median']},'Upside':{'Entry_to_strictly_later_High':s['metrics']['entry_to_high_pct'],'Upside_Retention_pct':s['metrics']['upside_retention_pct']},'Pre_peak_MAE_abs_pct':s['metrics']['pre_peak_mae_abs_pct'],'Path_Efficiency':s['metrics']['path_efficiency'],'path_evaluable_N':s['path_evaluable_N'],'path_unknown_N':s['path_unknown_N'],'remaining_high_unknown_N':s['remaining_high_unknown_N'],'Capture_reference':capture[key],'metrics_not_used_to_change_precommitted_target':True,'EXIT_calls':0,'Reentry_calls':0,'Capital_replays':0}
 write(HERE/'P1_Q70_ENTRY_EVALUATION.json',primary)
 write(HERE/'P1_Q70_SELECTOR_BUCKET_ENTRY_HIGH.json',{**shared,'selector_bucket_future_evaluator_only':True,'buckets':{b:{'watch_N':z['watch_N'],'Entry_N':z['FIRST_ENTRY_N'],'Entry_to_High_pct':z['metrics']['entry_to_high_pct']} for b,z in buckets[key].items()}})
 write(HERE/'P1_Q70_PRE_PEAK_MAE_EVIDENCE.json',{**shared,'median_only':True,'tail_or_hard_stop_simulation':0,'metric':'abs(min(0,100*(pre_peak_min_Low/fill_price-1))); includes peak bar Low conservatively','complete_pre_peak_paths_only':True,**s['metrics']['pre_peak_mae_abs_pct'],'unknown_N':s['path_unknown_N']})
 write(HERE/'P1_Q70_PATH_QUALITY_EVIDENCE.json',{**shared,'median_only':True,'standalone_Freeze_performance_gate':False,'complete_pre_peak_paths_only':True,'metric':'max(net close progress,0) / total variation; zero variation =>0',**s['metrics']['path_efficiency'],'unknown_N':s['path_unknown_N']})
 write(HERE/'CORRECTED_REFERENCE_PANEL_P0_Q70_Q95.json',{**shared,'reference_only':True,'P0_role':'State9-free control; never elevated to Primary','Q80_Q90_Q95_role':'existing fixed selectivity/capacity references; no reselection','summaries':summaries,'capture_reference':capture,'daily_activity':activity,'selector_buckets':buckets})
 print(json.dumps({'Primary_Freeze_Target':key,'Activity':primary['Activity'],'Upside':primary['Upside'],'MAE':primary['Pre_peak_MAE_abs_pct'],'Q':primary['Path_Efficiency'],'additional_fit':0,'candidate_reselection':0},ensure_ascii=False))

if __name__=='__main__':run()
