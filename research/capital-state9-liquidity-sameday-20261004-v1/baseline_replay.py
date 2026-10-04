"""Six precommitted research replays. Outcomes are revealed only after funding."""
from collections import Counter, defaultdict
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import gzip,json,math,sys
from pathlib import Path
import numpy as np
from capital_contract import candidate_runtime,quantity

def stamp(day,t):return day+'T%02d:%02d:00+09:00'%divmod(t,60)
def minute(t):return datetime.fromisoformat(t).hour*60+datetime.fromisoformat(t).minute
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def zipped(p,rows):p.write_bytes(gzip.compress(('\n'.join(json.dumps(r,sort_keys=True,allow_nan=False) for r in rows)+'\n').encode(),mtime=0))

def run(arm,n,entries,capacities,market,outcomes):
    # The scorer receives ONLY these projected runtime rows, never the outcome book.
    runtime=[candidate_runtime(e) for e in entries]
    events=defaultdict(list)
    for r in runtime:events[(r['session'],minute(r['entry_timestamp']))].append(r)
    days=sorted({r['session'] for r in runtime});decisions={r['entry_id']:{**r,'arm':arm,'max_positions':n,'quantity':None,'reason':'NOT_EVALUATED_AFTER_MEASUREMENT_BLOCKED'} for r in runtime}
    # The operational cutoff is defined for every identity, even beyond a blocked prefix.
    for r in runtime:
        if not r['eligible']:decisions[r['entry_id']].update(quantity=0,reason='CAPITAL_EOD_ENTRY_CUTOFF')
    cash=Decimal(1000000);positions={};exit_events=defaultdict(list);curves=[];trades=[];blocked=None;peakpos=0
    def equity():return cash+sum(v['quantity']*v['mark'] for v in positions.values())
    def frame(day,t):
        eq=equity();inv=eq-cash
        curves.append({'session':day,'timestamp':stamp(day,t),'equity':float(eq),'cash':float(cash),
                       'investment':float(inv),'utilization':float(inv/eq) if eq>0 else None,'positions':len(positions)})
    for day in days:
        if positions:raise RuntimeError('NO_SYNTHETIC_OVERNIGHT_VALUATION')
        grid=set(range(545,691,5))|set(range(755,926,5))
        timeline=sorted({540,931}|grid|{t for d,t in events if d==day}|set(range(540,932)))
        for t in timeline:
            # Source-completion cash release BEFORE same-time new Entries; never reference-backdated.
            for key in exit_events.pop((day,t),[]):
                v=positions.get(key)
                if not v:raise RuntimeError('DUPLICATE_CASH_RELEASE')
                o=outcomes[key]
                if not o.get('historical_cash_release_authorized'):
                    blocked={'session':day,'timestamp':stamp(day,t),'entry_id':key,'reason':'FUNDED_EXECUTION_UNKNOWN'};break
                sell=Decimal(str(o['integrated_exit_price']));credit=sell*v['quantity'];cash+=credit
                trades.append({'entry_id':key,'quantity':v['quantity'],'buy':str(v['buy']),'sell':str(sell),
                               'entry_debit':str(v['buy']*v['quantity']),'exit_credit':str(credit),'pnl':str((sell-v['buy'])*v['quantity']),
                               'cash_release_timestamp':o['cash_release_timestamp'],'commission':0})
                del positions[key]
            if blocked:break
            if t in grid:
                for key,v in positions.items():
                    bars=market[key]['today'];source=next((b for b in bars if int(b[0])==t-1),None)
                    if source is None or not math.isfinite(float(source[4])) or float(source[4])<=0:
                        blocked={'session':day,'timestamp':stamp(day,t),'entry_id':key,'reason':'MISSING_FUNDED_EXACT_5M_MARK'};break
                    v['mark']=Decimal(str(source[4]));v['mark_known_at']=stamp(day,t)
                if blocked:break
            candidates=sorted(events.get((day,t),[]),key=lambda r:(-(r['score'] if r['score'] is not None else -1),r['entry_id']))
            eligible=[]
            for r in candidates:
                d=decisions[r['entry_id']]
                if not r['eligible']:continue
                if r['score'] is None:d.update(quantity=0,reason='CAPITAL_SCORE_INPUT_UNKNOWN');continue
                liq=capacities[r['entry_id']]
                if liq is None:d.update(quantity=0,reason='CAPITAL_LIQUIDITY_INPUT_UNKNOWN');continue
                if any(v['symbol']==r['symbol'] for v in positions.values()):d.update(quantity=0,reason='SYMBOL_ALREADY_OPEN');continue
                eligible.append(r)
            before=equity();invested=before-cash
            target_util=min(.90,.60+.25*max((r['score'] for r in eligible),default=0)+.02*max(0,len(eligible)-1))
            deployment=max(Decimal(0),before*Decimal(str(target_util))-invested)
            remaining_weight=sum(.5+r['score'] for r in eligible)
            for r in eligible:
                d=decisions[r['entry_id']]
                if len(positions)>=n:d.update(quantity=0,reason='MAX_POSITION_CAP');remaining_weight-=.5+r['score'];continue
                eq=equity()
                if arm=='FIXED_SANITY':target=eq/Decimal(n);cap=target
                else:
                    target=deployment*Decimal(str((.5+r['score'])/remaining_weight)) if remaining_weight>0 else Decimal(0)
                    cap=eq*Decimal(str(.20+.20*r['score']))
                liq=Decimal(capacities[r['entry_id']]);q,reason=quantity(r,target,cash,cap,liq)
                remaining_weight-=.5+r['score']
                d.update(quantity=q,reason=reason or 'ACCEPTED',score=r['score'],rank='CONTINUOUS_ONLY',
                         target_notional=float(target),candidate_equity_cap=float(cap),liquidity_capacity=float(liq),cash_before=float(cash),equity_before=float(eq))
                if q:
                    price=Decimal(r['entry_effective_price']);debit=price*q;cash-=debit;deployment=max(Decimal(0),deployment-debit)
                    positions[r['entry_id']]={'symbol':r['symbol'],'quantity':q,'buy':price,'mark':price/Decimal('1.0005'),
                                              'mark_known_at':r['entry_timestamp']}
                    peakpos=max(peakpos,len(positions))
                    if cash<0 or q%100 or len(positions)>n:raise RuntimeError('ACCOUNTING_OR_CAP_BREACH')
                    # Only now consult future historical execution outcomes; never a BUY predicate.
                    o=outcomes[r['entry_id']]
                    release=minute(o['cash_release_timestamp']) if o.get('historical_cash_release_authorized') else 931
                    exit_events[(day,release)].append(r['entry_id'])
            if t in grid or candidates or t in [540,931]:frame(day,t)
        if blocked:break
        if positions:raise RuntimeError('UNRESOLVED_POSITION_CANNOT_BE_ZEROED')
    ds=list(decisions.values());accepted=[d for d in ds if d['reason']=='ACCEPTED'];rejected=[d for d in ds if d['quantity']==0]
    pending=[d for d in ds if d['quantity'] is None]
    # This evaluation-only access occurs after all causal funding decisions.
    future_unknown={k for k,o in outcomes.items() if o['reason']=='UNKNOWN_NO_ADMISSIBLE_SOURCE'}
    funded_unknown=[d['entry_id'] for d in accepted if d['entry_id'] in future_unknown]
    byid={e['watch_key']:e for e in entries}
    winner=lambda e:e['first_upside']['5']['minute'] is not None
    total_winners=sum(winner(e) for e in entries);funded_winners=sum(winner(byid[d['entry_id']]) for d in accepted)
    reasons=Counter(d['reason'] for d in rejected)
    result={'arm':arm,'max_positions':n,'candidate_N':1600,'status':'CAPITAL_MEASUREMENT_BLOCKED' if blocked else 'MEASURED_DEVELOPMENT_REFERENCE',
            'funding_trace_complete':not bool(blocked),'accepted_observed_N':len(accepted),'rejected_observed_N':len(rejected),
            'not_evaluated_after_block_N':len(pending),'rejection_reasons':dict(reasons),'max_concurrent_observed':peakpos,
            'funded_execution_unknown_observed_N':len(funded_unknown),'funded_unknown_full_trace_N':None if blocked else len(funded_unknown),
            'blocker':{k:v for k,v in blocked.items() if k!='entry_id'} if blocked else None,
            'closed_trades_observed_N':len(trades),'cash_recycling_observed_N':len(trades),'broker_commission_jpy':0,
            'confirmed_ge5_candidate_N':total_winners,'confirmed_ge5_funded_observed_N':funded_winners,
            'confirmed_ge5_liquidity_skip_observed_N':sum(winner(byid[d['entry_id']]) for d in rejected if d['reason']=='CAPITAL_SKIP_LIQUIDITY'),
            'confirmed_ge5_liquidity_input_unknown_observed_N':sum(winner(byid[d['entry_id']]) for d in rejected if d['reason']=='CAPITAL_LIQUIDITY_INPUT_UNKNOWN'),
            'initial_equity':1000000,'final_equity':None,'total_return':None,'geometric_mean_session':None,'max_drawdown':None,
            'mean_utilization':None,'median_utilization':None,'utilization_ge80_time':None,'utilization_ge90_time':None,
            'rolling20_max_multiple':None,'rolling22_max_multiple':None,'rolling24_max_multiple':None,'shortest_doubling_sessions':None,
            'result_based_retuning':False,'adaptive_sizing_replaced_by_1_over_N':False,'curve_role':'KNOWN_PREFIX_ONLY_NOT_FULL_PORTFOLIO' if blocked else 'FULL_MEASURED_REFERENCE'}
    if not blocked:
        end={}
        for f in curves:end[f['session']]=f['equity']
        vals=np.array([1000000]+[end[d] for d in days]);result['final_equity']=float(vals[-1]);result['total_return']=float(vals[-1]/1e6-1)
        result['geometric_mean_session']=float((vals[-1]/1e6)**(1/len(days))-1)
        eqs=np.array([f['equity'] for f in curves]);result['max_drawdown']=float(np.min(eqs/np.maximum.accumulate(eqs)-1))
        weights=[];utils=[]
        for a,b in zip(curves,curves[1:]):
            if a['session']==b['session']:
                dt=max(0,minute(b['timestamp'])-minute(a['timestamp']));dt=min(dt,5) if minute(a['timestamp'])<=690<minute(b['timestamp']) else dt
                weights.append(dt);utils.append(a['utilization'])
        result['mean_utilization']=float(np.average(utils,weights=weights));result['median_utilization']=float(np.median(utils))
        result['utilization_ge80_time']=float(np.average(np.array(utils)>=.8,weights=weights));result['utilization_ge90_time']=float(np.average(np.array(utils)>=.9,weights=weights))
        for w in [20,22,24]:result[f'rolling{w}_max_multiple']=float(np.max(vals[w:]/vals[:-w]))
        doubles=[j-i for i in range(len(vals)) for j in range(i+1,len(vals)) if vals[j]>=2*vals[i]]
        result['shortest_doubling_sessions']=min(doubles) if doubles else None
    return result,ds,curves,trades,{'blocker':blocked,'funded_unknown_ids':funded_unknown}

def main():
    root=Path(sys.argv[1]);out=root/'svnext_private';entries=[e for e in map(json.loads,gzip.open(root/'eod_private/primary/entry.jsonl.gz','rt')) if e['entry_status']=='FIRST_ENTRY']
    cap=json.loads((out/'CAPACITIES_PRIVATE.json').read_text());market=json.loads(gzip.open(root/'eod_private/primary/raw_paths.json.gz','rt').read())
    outcomes={r['entry_id']:r for r in map(json.loads,gzip.open(root/'f1520_private/primary-v1/EOD1520_ADAPTER_ROWS.jsonl.gz','rt'))}
    allresults=[];decisions=[];curves=[];trades=[];private=[]
    for arm in ['FIXED_SANITY','CURRENT_CAUSAL_BASELINE']:
        for n in [3,4,5]:
            r,d,c,t,p=run(arm,n,entries,cap,market,outcomes)
            allresults.append(r);decisions.extend(d);curves.extend([{**f,'arm':arm,'max_positions':n} for f in c]);trades.extend([{**f,'arm':arm,'max_positions':n} for f in t]);private.append({**p,'arm':arm,'max_positions':n})
    result={'jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'status':'BASELINE_MEASUREMENT_BLOCKED' if any(r['blocker'] for r in allresults) else 'BASELINE_MEASURED',
            'research_replay_budget_consumed':6,'fit_budget_consumed':0,'provider_requests':0,'normal_limitup_flag_evidence':'UNKNOWN for all; precommitted normal EOD route, no fabricated confirmed limitup.',
            'arms':allresults}
    write(out/'BASELINE_RESULTS.json',result);write(out/'FUNDED_BLOCKERS_PRIVATE.json',private)
    zipped(out/'CAPITAL_DECISIONS.jsonl.gz',decisions);zipped(out/'PORTFOLIO_CURVES_KNOWN_PREFIX.jsonl.gz',curves);zipped(out/'TRADES_PRIVATE.jsonl.gz',trades)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
