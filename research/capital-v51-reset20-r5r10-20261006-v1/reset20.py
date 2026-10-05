"""Explicit-calendar account resets around the immutable V5 day engine."""
from decimal import Decimal as D
from collections import defaultdict
from statistics import median,mean
from pathlib import Path
import sys,types
from io_utils import *

NATIVE=REPO/'research/capital-v5-max3-slot-intelligence-20261004-v1'
sys.path.insert(0,str(NATIVE))
import replay as v5

def engine(allocator=None):
    if allocator is None:return v5.day_replay
    return types.FunctionType(v5.day_replay.__code__,dict(v5.day_replay.__globals__,allocation=allocator),argdefs=v5.day_replay.__defaults__)

def validate_sessions(sessions,calendar):
    if len(sessions)!=20 or len(set(sessions))!=20:return False
    try:i=calendar.index(sessions[0])
    except ValueError:return False
    return calendar[i:i+20]==sessions

def run_window(window,by_day,books,tables,day_engine=None,profile='V5_RESET20'):
    result={k:v for k,v in window.items()}
    result.update(profile=profile,initial_cash='1000000',initial_positions_N=0,execution_complete=None,final_cash_for_primary=None,attempted_day_N=0)
    if not window['coverage_complete']:
        result['status']='BLOCKED_COVERAGE';return result,[],[],[],[]
    cash=D('1000000');daily=[];decisions=[];trades=[];intents=[];frames=[]
    fn=day_engine or engine()
    peak=cash;maxdd=D(0);sumutil=0.;sumocc=0;frame_n=0
    for day in window['sessions']:
        d,ds,ts,cs,it=fn(3,day,by_day.get(day,[]),books,cash,True,profile,tables=tables)
        result['attempted_day_N']+=1;daily.append(d)
        decisions+=ds;trades+=ts;intents+=it;frames+=cs
        for c in cs:
            eq=D(c['equity']);peak=max(peak,eq);maxdd=max(maxdd,(peak-eq)/peak)
            if 540<=c['minute']<690 or 750<=c['minute']<930:
                sumutil+=c['utilization'];sumocc+=c['concurrent'];frame_n+=1
        if d['status']!='COMPLETE':
            result.update(status='BLOCKED_EXECUTION',execution_complete=False,failed_session=day,blockers=d['blockers'],open_obligations=d['open_obligations']);break
        cash=D(d['ending_cash'])
    else:
        result.update(status='COMPLETE',execution_complete=True,final_cash_for_primary=str(cash),two_x_hit=cash>=D('2000000'))
    result.update(daily_series=daily,max_drawdown=str(maxdd),utilization_mean=sumutil/frame_n if frame_n else None,occupancy_mean=sumocc/frame_n if frame_n else None,funded_N=sum(d['reason']=='FUNDED' for d in decisions),closed_N=len(trades))
    return result,decisions,trades,frames,intents

def summarize(windows):
    good=[w for w in windows if w['status']=='COMPLETE'];xs=[D(w['final_cash_for_primary']) for w in good]
    return {'planned_window_N':len(windows),'coverage_complete_N':sum(w['coverage_complete'] for w in windows),'complete_window_N':len(good),'blocked_coverage_N':sum(w['status']=='BLOCKED_COVERAGE' for w in windows),'blocked_execution_N':sum(w['status']=='BLOCKED_EXECUTION' for w in windows),'min_jpy':str(min(xs)) if xs else None,'mean_jpy':str(mean(xs)) if xs else None,'median_jpy':str(median(xs)) if xs else None,'max_jpy':str(max(xs)) if xs else None,'two_x_N':sum(x>=D('2000000') for x in xs),'two_x_rate':sum(x>=D('2000000') for x in xs)/len(xs) if xs else None,'median_gap_to_2m_jpy':str(D('2000000')-median(xs)) if xs else None,'measurement_status':'MEASUREMENT_COMPLETE' if len(good)==len(windows) else 'MEASUREMENT_INCOMPLETE','subset_status':'COMPLETE_PRIMARY_SET' if len(good)==len(windows) else 'PARTIAL_DIAGNOSTIC_ONLY','max_drawdown_worst':str(max((D(w['max_drawdown']) for w in good),default=D(0)))}

def run_batch(profile,manifest,stream,books,tables,allocator=None):
    root=PRIVATE/'runs'/profile;root.mkdir(parents=True,exist_ok=True)
    claim=root/'STARTED.json'
    if not claim.exists():save(claim,{'exact_jst':now(),'formal_batch':1,'profile':profile,'window_manifest_sha256':sha(OUT/'COVERAGE_AND_WINDOWS.json')})
    by_day=defaultdict(list)
    for r in stream:by_day[r['session']].append(r)
    windows=[];day_n=0;reused=0
    for w in manifest['windows']:
        dest=root/w['window_id'];done=dest/'COMPLETE.json'
        if done.exists():
            res=read(done);reused+=1
        else:
            res,ds,ts,cs,it=run_window(w,by_day,books,tables,engine(allocator),profile)
            for name,data in [('DECISIONS',ds),('TRADES',ts),('CURVE',cs),('INTENTS',it)]:
                for row in data:row['window_id']=w['window_id']
                write_rows(dest/(name+'.jsonl.gz'),data)
            save(done,res);print(profile,w['window_id'],res['status'],res['attempted_day_N'],flush=True)
        windows.append(res);day_n+=res['attempted_day_N']
    result={'schema':'ARK_RESET20_RESULT_V1','exact_jst':now(),'profile':profile,'mode':'RESET20_CASH1M','formal_batches':1,'window_attempt_N':len(windows),'day_attempt_N':day_n,'window_reused_N':reused,'summary':summarize(windows),'windows':windows,'source_exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','productionReady':False}
    save(OUT/(profile+'_RESULT.json'),result);return result
