"""Frozen existing causal primitives. A caller supplies closed prefixes only."""
import numpy as np
from common import OLD,REPO,sha,active_elapsed
from price_primitives import window,describe,activity,observed_vwap,pct,phase_start
WINDOWS=(5,10,20)
DESCRIBE=('count','coverage','return','high','low','range','volatility','body','upper','lower','volume','value','vwapDistance','closeLocation','timeHigh','timeLow','trendEfficiency')
ACTIVITY=tuple(activity(np.empty((0,7)),np.empty((0,7)),600))
CONTEXT=('return1','return3','return5','return10','return20','vwapDistancePct','vwapSlope3Pct','vwapObservedCoverage','pullback5Pct','pullback10Pct','pullback20Pct','activeMinutesSinceSelector','priceVsFirstSelectorPct','knownRefreshCount','activeMinutesSinceLatestSelector','clockMinute','isPM')
P0_NAMES=[f'w{n}/{k}' for n in WINDOWS for k in DESCRIBE]+['activity/'+k for k in ACTIVITY]+list(CONTEXT)
P1_NUM=['state/'+k for k in ('observed','observed_age','local_direction','context_direction','fast','fast_applicable','close_u','stop_direction','stop_width','stop_center_distance','stop_age','stop_recognized_age','stop_count','stop_progress_age','range_width','range_established_age','range_exit_low_distance','range_exit_high_distance','range_analysis_net','range_analysis_tv','range_analysis_span','range_analysis_width','range_analysis_eta','range_analysis_turns','range_analysis_guard','range_A','range_B','range_C','range_D','fast_analysis_net','fast_analysis_tv','fast_analysis_eta','fast_analysis_directional_net')]+['history/'+k for k in ('current_state_active_dwell','active_time_since_last_primary_change','transition_count_last5active','transition_count_last10active','transition_count_last20active')]
P1_CAT=['state/'+k for k in ('formal_primary','display_primary','activity','basis','direction_basis','numeric_status','rejection_reason','auction','source','source_events','range_reason')]+['history/'+k for k in ('previous_distinct_formal_primary','previous_to_current_pair','last3_distinct_primary_sequence')]+['source_status']
def compute(w,a,previous,t):
 assert len(a) and np.max(a[:,0])+1<=t,'UNCLOSED_PRICE_PREFIX'
 out={};c=a[-1,4]
 for n in WINDOWS:
  x=window(a,t,n);lo=max(phase_start(t),t-n);actual=int(np.sum((a[:,0]>=lo)&(a[:,0]<t)))
  d=describe(x if x is not None else np.empty((0,7)),c,n)
  d['count']=actual;d['coverage']=actual/n
  for k in DESCRIBE:out[f'w{n}/{k}']=d[k]
 for k,v in activity(a,previous,t).items():out['activity/'+k]=v
 for n in (1,3,5,10,20):
  x=window(a,t,n+1);out['return'+str(n)]=pct(c,x[0,4]) if x is not None else None
 vw,cov=observed_vwap(w['session'],a,t);vw3,_=observed_vwap(w['session'],a,t-3)
 out.update(vwapDistancePct=pct(c,vw),vwapSlope3Pct=pct(vw,vw3) if vw is not None else None,vwapObservedCoverage=cov)
 for n in WINDOWS:
  x=window(a,t,n);out['pullback'+str(n)+'Pct']=pct(c,max(x[:,2])) if x is not None else None
 known=[m for m in w['refresh_minutes'] if m<=t]
 out.update(activeMinutesSinceSelector=active_elapsed(w['session'],w['selector_minute'],t),priceVsFirstSelectorPct=pct(c,w['selector_price']),knownRefreshCount=len(known),activeMinutesSinceLatestSelector=active_elapsed(w['session'],known[-1] if known else w['selector_minute'],t),clockMinute=t,isPM=int(t>=750))
 assert set(out)==set(P0_NAMES)
 return [np.nan if out[k] is None else float(out[k]) for k in P0_NAMES]
def provenance():
 return {'price_primitives.py':sha(__import__('pathlib').Path(__file__).parent/'price_primitives.py'),'describe':'exact AST body phase57_entry_pattern_v2.py:describe','strict_window_activity_vwap':'exact AST bodies phase57_entry_timing_signals.py','parameterization':'fixed close-lag windows 1/3/5/10/20; fixed describe/pullback windows5/10/20','new_watch_context':'causal clock, elapsed minutes, first anchor price, refresh known by t','source_hashes':{p:sha(REPO/'scripts'/p) for p in ('phase57_entry_pattern_v2.py','phase57_entry_timing_signals.py')},'no_estimated_absent_features':True}
