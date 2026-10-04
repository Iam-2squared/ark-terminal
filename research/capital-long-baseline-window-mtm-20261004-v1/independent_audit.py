"""Independent source/accounting/diagnostic verification; no primary imports or fits.

Reconstructs the observed funded prefix, not an invented complete Portfolio.
All full-performance quantities remain null when a required mark is absent.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import copy, gzip, hashlib, json, math, pickle, sys, zipfile
from pathlib import Path
import numpy as np

def rows(p):
    with gzip.open(p,'rt') as f:return [json.loads(s) for s in f if s.strip()]
def tm(s):
    d=datetime.fromisoformat(s);return 60*d.hour+d.minute
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def serial(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def projection(e):
    d=datetime.fromisoformat(e['fill_timestamp']);s=e['first_intent'].get('score')
    return dict(entry_id=e['watch_key'],session=e['session'],symbol=e['symbol'],
        entry_timestamp=e['fill_timestamp'],entry_effective_price=str(e['fill_price']),
        score=s if isinstance(s,(int,float)) and math.isfinite(s) and 0<=s<=1 else None,
        eligible=(d.hour,d.minute,d.second)<(15,20,0),
        cutoff_reason=None if (d.hour,d.minute,d.second)<(15,20,0) else 'CAPITAL_EOD_ENTRY_CUTOFF')
def auc(y,p):
    positives=p[y==1];negatives=p[y==0]
    if not len(positives) or not len(negatives):return None
    return float(np.mean([(np.sum(a>negatives)+.5*np.sum(a==negatives))/len(negatives) for a in positives]))


def window_oracle(bars, grid):
    matches=[row for row in bars if grid-5<=int(row[0])<=grid-1
             and Decimal(str(row[4])).is_finite() and Decimal(str(row[4]))>0]
    if not matches:return None
    matches.sort(key=lambda row:int(row[0]))
    seen={}
    for row in matches:
        t=int(row[0])
        if t in seen and seen[t]!=row:raise ValueError('CONFLICTING_SAVED_WINDOW_SOURCE')
        seen[t]=row
    return matches[-1]

def metrics_oracle(frames,trades,days):
    import math,statistics
    closing={}
    for row in frames:closing[row['session']]=row['equity']
    assets=[1e6]+[closing[day] for day in days]
    changes=[assets[i+1]/assets[i]-1 for i in range(len(days))]
    session_rows=[dict(session=day,session_index=i+1,start_equity=assets[i],close_equity=assets[i+1],return_=changes[i]) for i,day in enumerate(days)]
    for r in session_rows:r['return']=r.pop('return_')
    high=1e6;drawdown=0.;peak_index=0;longest=0
    for i,row in enumerate(frames):
        if row['equity']>=high:high=row['equity'];peak_index=i
        else:drawdown=min(drawdown,row['equity']/high-1);longest=max(longest,i-peak_index)
    observations=[]
    for i in range(len(frames)-1):
        a,b=frames[i],frames[i+1]
        if a['session']!=b['session']:continue
        lo,hi=tm(a['timestamp']),tm(b['timestamp'])
        w=max(0,min(hi,690)-max(lo,540))+max(0,min(hi,931)-max(lo,750))
        if w:observations.append((w,a))
    clock=sum(w for w,a in observations)
    averaging=lambda key:sum(w*a[key] for w,a in observations)/clock
    ordered=sorted((a['utilization'],w) for w,a in observations)
    cumulative=0;medianutil=None
    for i,(u,w) in enumerate(ordered):
        cumulative+=w
        if cumulative>=clock/2:
            medianutil=(u+ordered[i+1][0])/2 if cumulative==clock/2 and i+1<len(ordered) else u
            break
    rolling={}
    for width in [20,22,24]:
        rs=[]
        for i in range(len(days)-width+1):
            multiple=assets[i+width]/assets[i]
            rs.append(dict(start_session=days[i],end_session=days[i+width-1],
                           start_session_index=i+1,end_session_index=i+width,multiple=multiple,equivalent_from_1m=multiple*1e6))
        values=[r['multiple'] for r in rs]
        rolling[str(width)]={'windows_N':len(values),'min_multiple':min(values) if values else None,
          'median_multiple':statistics.median(values) if values else None,'mean_multiple':statistics.mean(values) if values else None,
          'max_multiple':max(values) if values else None,'doubling_windows_N':sum(x>=2 for x in values),'rows':rs}
    pnls=[Decimal(t['pnl']) for t in trades]
    friction=sum(t['quantity']*(Decimal(t['buy'])/Decimal('1.0005')*Decimal('.0005')+
                 Decimal(t['sell'])/Decimal('.9995')*Decimal('.0005')) for t in trades)
    doubles=[j-i for i in range(len(assets)) for j in range(i+1,len(assets)) if assets[j]>=2*assets[i]]
    result=dict(initial_equity=1000000,final_equity=assets[-1],total_return=assets[-1]/1e6-1,
       geometric_mean_session=(assets[-1]/1e6)**(1/len(days))-1,
       arithmetic_mean_session=statistics.mean(changes),median_session_return=statistics.median(changes),
       session_return_volatility=statistics.pstdev(changes),winning_sessions_N=sum(r>0 for r in changes),
       losing_sessions_N=sum(r<0 for r in changes),flat_sessions_N=sum(r==0 for r in changes),worst_session_return=min(changes),
       max_drawdown=drawdown,drawdown_duration_observation_frames=longest,
       mean_utilization=averaging('utilization'),median_utilization=medianutil,
       utilization_ge80_time=sum(w for w,a in observations if a['utilization']>=.8)/clock,
       utilization_ge90_time=sum(w for w,a in observations if a['utilization']>=.9)/clock,
       peak_utilization=max(a['utilization'] for a in frames),
       average_concurrent_positions=averaging('positions'),average_idle_cash_jpy=averaging('cash'),
       zero_exposure_minutes=sum(w for w,a in observations if a['positions']==0),observed_active_minutes=clock,
       cash_recycling_count=len(trades),realized_pnl_jpy=float(sum(pnls)),commission_jpy=0,
       execution_friction_jpy=float(friction),gross_effective_turnover_jpy=float(sum(Decimal(t['entry_debit'])+Decimal(t['exit_credit']) for t in trades)),
       shortest_doubling_sessions=min(doubles) if doubles else None,rolling=rolling,session_rows=session_rows)
    for width in [20,22,24]:result[f'rolling{width}_max_multiple']=rolling[str(width)]['max_multiple']
    return result

def main():
    root=Path(sys.argv[1]);out=root/'long_mtm_private';here=Path(__file__).resolve().parents[1]/'capital-state9-liquidity-sameday-20261004-v1'
    counts=Counter();mismatches=[]
    def eq(a,b,label,tol=None):
        counts[label]+=1
        if tol is not None and a is not None and b is not None:
            good=abs(float(a)-float(b))<=tol
        else:good=a==b
        if not good:mismatches.append({'label':label,'expected':str(a),'actual':str(b)})
    entries=[e for e in rows(root/'eod_private/independent/entry.jsonl.gz') if e['entry_status']=='FIRST_ENTRY']
    exits={e['watch_key']:e for e in rows(root/'eod_private/independent/exit_v3.jsonl.gz')}
    market=json.loads(gzip.open(root/'eod_private/independent/raw_paths.json.gz','rt').read())
    outcome={e['entry_id']:e for e in rows(root/'f1520_private/independent/INDEPENDENT_ROWS.jsonl.gz')}
    with zipfile.ZipFile(root/'svnext_private/daily/private.zip') as z:
        daily=json.loads(gzip.decompress(z.read(next(n for n in z.namelist() if n.endswith('.gz')))))
    scope=json.loads((here/'DAILY_RECOVERY_SCOPE.json').read_text())
    safe=json.loads((here/'DAILY_RECOVERY_SCOPE_SAFE_V2.json').read_text())
    calendar=sorted(set(scope['required_prior_dates']+scope['entry_cohort_dates']))
    authorized=set(safe['source_dates_authorized'])
    protected=set(scope['required_prior_dates'])-authorized
    bysymbol=defaultdict(list)
    for r in daily:bysymbol[r['Code']].append(r)
    saved_cap=json.loads((root/'svnext_private/CAPACITIES_PRIVATE.json').read_text());caps={};reasons=Counter();capacity_lt_lot=[]
    for e in entries:
        prior=tuple(d for d in calendar if d<e['session'])[-20:]
        values=[];unavailable=False;missing=[]
        for day in prior:
            options=[]
            for r in bysymbol[e['symbol']]:
                if r['Date']==day and r.get('known_session',day)<e['session'] and r.get('Va') is not None:
                    v=Decimal(r['Va'])
                    if v.is_finite() and v>0:options.append(v)
            if not options or len(set(options))!=1:unavailable=True;missing.append(day)
            else:values.append(options[0])
        if len(prior)!=20:unavailable=True
        if unavailable:
            caps[e['watch_key']]=None
            reasons['REQUIRED_PROTECTED_DATE_UNOPENED' if any(d in protected for d in missing) else 'OTHER_EXACT_PRIOR_HISTORY_UNAVAILABLE']+=1
        else:
            values.sort();caps[e['watch_key']]=(values[9]+values[10])/Decimal(200);reasons['KNOWN']+=1
            if caps[e['watch_key']]<Decimal(str(e['fill_price']))*100:capacity_lt_lot.append(e)
        eq(caps[e['watch_key']],Decimal(saved_cap[e['watch_key']]) if saved_cap[e['watch_key']] is not None else None,'exact_prior20_capacity')
        r=projection(e);m=copy.deepcopy(e)
        m.update(execution_evidence_status='FORBIDDEN_MUTATION',profit=1e100,future_high=-1e50,next_day_open=0)
        eq(projection(m),r,'future_evidence_projection_canary')
    primary=rows(out/'CAPITAL_DECISIONS.jsonl.gz');curves=rows(out/'PORTFOLIO_CURVES.jsonl.gz')
    baseline=json.loads((out/'BASELINE_RESULTS.json').read_text());independent=[]
    byid={e['watch_key']:e for e in entries};events=defaultdict(list)
    for e in entries:events[(e['session'],tm(e['fill_timestamp']))].append(projection(e))
    daylist=sorted({e['session'] for e in entries});private_prefix=[]
    for result in baseline['arms']:
        arm,n=result['arm'],result['max_positions']
        observed={d['entry_id']:d for d in primary if d['arm']==arm and d['max_positions']==n}
        frames=[f for f in curves if f['arm']==arm and f['max_positions']==n]
        eq(set(observed),set(byid),'identity_set')
        expected={k:{'quantity':None,'reason':'NOT_EVALUATED_AFTER_MEASUREMENT_BLOCKED'} for k in byid}
        for e in entries:
            if not projection(e)['eligible']:expected[e['watch_key']]={'quantity':0,'reason':'CAPITAL_EOD_ENTRY_CUTOFF'}
        cash=Decimal(1000000);positions={};schedule=defaultdict(list);ownframes=[];block=None;maxpos=0;closeN=0;owntrades=[];markN=0
        for day in daylist:
            if positions:raise ValueError('NO_CROSS_SESSION_SYNTHETIC_MARK')
            grid=set(range(545,691,5))|set(range(755,926,5))
            for minute in range(540,932):
                due=schedule.pop((day,minute),[])
                for key in due:
                    o=outcome[key]
                    if not o['historical_cash_release_authorized']:
                        block=(day,minute,key,'FUNDED_EXECUTION_UNKNOWN');break
                    q,buy,mark=positions[key];sell=Decimal(o['integrated_exit_price'])
                    old=cash;cash+=q*sell;eq(cash-old-q*buy,q*(sell-buy),'cash_trade_pnl',1e-10)
                    owntrades.append({'entry_id':key,'quantity':q,'buy':str(buy),'sell':str(sell),'entry_debit':str(q*buy),'exit_credit':str(q*sell),'pnl':str(q*(sell-buy)),'cash_release_timestamp':o['cash_release_timestamp'],'commission':0})
                    del positions[key];closeN+=1
                if block:break
                if minute in grid:
                    for key,(q,buy,oldmark) in list(positions.items()):
                        selected=window_oracle(market[key]['today'],minute)
                        source=[] if selected is None else [selected]
                        if not source or not math.isfinite(float(source[0][4])) or source[0][4]<=0:
                            block=(day,minute,key,'MISSING_FUNDED_WINDOW_MTM_MARK');break
                        positions[key]=(q,buy,Decimal(str(source[0][4])));markN+=1
                    if block:break
                batch=sorted(events.get((day,minute),[]),key=lambda r:(-(r['score'] if r['score'] is not None else -1),r['entry_id']))
                good=[]
                for r in batch:
                    key=r['entry_id']
                    if not r['eligible']:continue
                    if r['score'] is None:expected[key]={'quantity':0,'reason':'CAPITAL_SCORE_INPUT_UNKNOWN'}
                    elif caps[key] is None:expected[key]={'quantity':0,'reason':'CAPITAL_LIQUIDITY_INPUT_UNKNOWN'}
                    elif any(byid[k]['symbol']==r['symbol'] for k in positions):expected[key]={'quantity':0,'reason':'SYMBOL_ALREADY_OPEN'}
                    else:good.append(r)
                equity=cash+sum(q*mark for q,buy,mark in positions.values());invested=equity-cash
                util=min(.90,.60+.25*max([r['score'] for r in good],default=0)+.02*max(0,len(good)-1))
                deployment=max(Decimal(0),equity*Decimal(str(util))-invested)
                weights={r['entry_id']:Decimal('.5')+Decimal(str(r['score'])) for r in good}
                total=sum(weights.values())
                for r in good:
                    k=r['entry_id'];equity=cash+sum(q*mark for q,buy,mark in positions.values())
                    if len(positions)>=n:expected[k]={'quantity':0,'reason':'MAX_POSITION_CAP'};total-=weights[k];continue
                    if arm=='FIXED_SANITY':target=equity/Decimal(n);cap=target
                    else:target=deployment*weights[k]/total;cap=equity*(Decimal('.20')+Decimal('.20')*Decimal(str(r['score'])))
                    total-=weights[k];price=Decimal(r['entry_effective_price']);limit=min(target,cap,cash,caps[k]);q=int(limit//(price*100))*100
                    reason='ACCEPTED' if q else 'CAPITAL_SKIP_LIQUIDITY' if caps[k]<price*100 else 'CAPITAL_LOT_OR_CASH_CONSTRAINED'
                    expected[k]={'quantity':q,'reason':reason}
                    d=observed[k]
                    for field,val in [('cash_before',cash),('equity_before',equity),('liquidity_capacity',caps[k]),('candidate_equity_cap',cap),('target_notional',target)]:eq(val,d[field],'allocation_'+field,1e-7)
                    if q:
                        cash-=q*price;positions[k]=(q,price,price/Decimal('1.0005'));deployment=max(Decimal(0),deployment-q*price)
                        eq(q%100,0,'100_share_lot');eq(cash>=0,True,'nonnegative_cash');eq(len(positions)<=n,True,'concurrent_cap')
                        maxpos=max(maxpos,len(positions));o=outcome[k]
                        schedule[(day,tm(o['cash_release_timestamp']) if o['historical_cash_release_authorized'] else 931)].append(k)
                if minute in grid or batch or due or minute in (540,931):
                    equity=cash+sum(q*mark for q,buy,mark in positions.values());investment=equity-cash
                    ownframes.append({'session':day,'timestamp':day+'T%02d:%02d:00+09:00'%divmod(minute,60),'cash':float(cash),'equity':float(equity),
                        'investment':float(investment),'utilization':float(investment/equity),'positions':len(positions)})
            if block:break
        for k,v in expected.items():
            eq(v['quantity'],observed[k]['quantity'],'decision_quantity');eq(v['reason'],observed[k]['reason'],'decision_reason')
            for field,v2 in projection(byid[k]).items():eq(v2,observed[k][field],'runtime_'+field)
        eq(len(frames),len(ownframes),'prefix_frame_N')
        for a,b in zip(ownframes,frames):
            for field in a:eq(a[field],b[field],'prefix_'+field,1e-8 if field in ('cash','equity','investment','utilization') else None)
        accepted=[k for k,v in expected.items() if v['reason']=='ACCEPTED'];unknown=[k for k in accepted if outcome[k]['reason']=='UNKNOWN_NO_ADMISSIBLE_SOURCE']
        eq(len(accepted),result['accepted_observed_N'],'accepted_N')
        eq(closeN,result['closed_trades_observed_N'],'closed_trade_N')
        eq(maxpos,result['max_concurrent_observed'],'max_positions_observed')
        eq(len(unknown),result['funded_execution_unknown_observed_N'],'funded_unknown_N')
        if block:
            eq(block[3],result['blocker']['reason'],'required_missing_mark_reason')
            eq(block[0],result['blocker']['session'],'block_session')
            eq(block[1],tm(result['blocker']['timestamp']),'block_time')
            eq(result['funded_unknown_full_trace_N'],None,'unknown_full_trace_not_fabricated')
            for field in ('final_equity','total_return','max_drawdown','mean_utilization','rolling'):
                eq(None,result[field],'full_metric_null')
            ownmetrics=None
        else:
            eq(result['blocker'],None,'no_block')
            eq(result['funded_unknown_full_trace_N'],len(unknown),'complete_unknown_N')
            eq(positions,{},'zero_overnight_positions')
            eq(cash-Decimal(1000000),sum(Decimal(t['pnl']) for t in owntrades),'cash_endpoint_equals_trade_pnl',1e-8)
            ownmetrics=metrics_oracle(ownframes,owntrades,daylist)
            for field,value in ownmetrics.items():
                if field not in ('rolling','session_rows'):
                    eq(value,result[field],'full_metric_'+field,1e-7 if 'jpy' in field or field=='final_equity' else 1e-11)
            for width,summary in ownmetrics['rolling'].items():
                expected_roll=result['rolling'][width]
                for field,value in summary.items():
                    if field=='rows':
                        eq(len(value),len(expected_roll['rows']),'rolling_row_N')
                        for aa,bb in zip(value,expected_roll['rows']):
                            for k in aa:eq(aa[k],bb[k],'rolling_'+k,1e-7 if k=='equivalent_from_1m' else 1e-11 if k=='multiple' else None)
                    else:eq(value,expected_roll[field],'rolling_summary_'+field,1e-11)
            for aa,bb in zip(ownmetrics['session_rows'],result['session_rows']):
                for k in aa:eq(aa[k],bb[k],'daily_'+k,1e-7 if 'equity' in k else 1e-11 if k=='return' else None)
        primary_trades=[t for t in rows(out/'TRADES_PRIVATE.jsonl.gz') if t['arm']==arm and t['max_positions']==n]
        eq(len(primary_trades),len(owntrades),'ledger_trade_N')
        for aa,bb in zip(owntrades,primary_trades):
            for k in aa:eq(aa[k],bb[k],'ledger_'+k,1e-8 if k in ('buy','sell','entry_debit','exit_credit','pnl') else None)
        independent.append({'arm':arm,'max_positions':n,'accepted_N':len(accepted),'closed_N':closeN,
                            'full_measurement':block is None,'mark_observations_N':markN,
                            'funded_unknown_N':len(unknown),'final_equity':ownmetrics['final_equity'] if ownmetrics else None})
        private_prefix.append({'arm':arm,'max_positions':n,'independent_block':block,'frames':ownframes})
    result={'jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),
            'status':'PASS' if not mismatches else 'FAIL','comparison_counts':dict(counts),
            'compared_values_N':sum(counts.values()),'mismatch_N':len(mismatches),'arms':independent,
            'primary_imported':False,'new_model_fits':0,'new_state9_evaluations':0,'provider_requests':0,
            'cash_only_LONG':True,'commission_jpy':0,'source_price_imputation_N':0}
    serial(out/'INDEPENDENT_AUDIT.json',result)
    serial(out/'INDEPENDENT_MISMATCHES_PRIVATE.json',mismatches)
    (out/'INDEPENDENT_FRAMES_PRIVATE.jsonl.gz').write_bytes(gzip.compress(('\n'.join(json.dumps(x) for x in private_prefix)+'\n').encode(),mtime=0))
    print(json.dumps(result,ensure_ascii=False))
    if mismatches:raise SystemExit(2)

if __name__=='__main__':main()
