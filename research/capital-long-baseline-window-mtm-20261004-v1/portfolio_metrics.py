"""Portfolio evaluation only. Never called to score or fund candidates."""
from datetime import datetime
from decimal import Decimal
from statistics import mean, median, pstdev
import math

def minute(value):
    stamp = datetime.fromisoformat(value)
    return stamp.hour*60 + stamp.minute + stamp.second/60

def duration(start, stop):
    # Include committed auction/preclose time and source-completion cash receipt.
    # Lunch is never counted. These are valuation/capital-lock observation times.
    return sum(max(0, min(stop, b)-max(start, a))
               for a, b in [(540, 690), (750, 931)])

def weighted_median(values, weights):
    pairs = sorted(zip(values, weights))
    half = sum(weights)/2
    total = 0
    for index, (value, weight) in enumerate(pairs):
        total += weight
        if total > half:
            return value
        if total == half:
            return (value+pairs[index+1][0])/2 if index+1 < len(pairs) else value
    return None

def summarize(curves, trades, days, decisions):
    endpoints = {}
    for frame in curves:
        endpoints[frame['session']] = frame['equity']
    if set(endpoints) != set(days):
        raise ValueError('INCOMPLETE_SESSION_ENDPOINTS')
    assets = [1_000_000.] + [endpoints[day] for day in days]
    returns = [end/start-1 for start,end in zip(assets,assets[1:])]
    sessions = [{'session':day, 'session_index':i+1,
                 'start_equity':assets[i], 'close_equity':assets[i+1],
                 'return':returns[i]} for i,day in enumerate(days)]
    peak, maxdd = 1_000_000., 0.
    last_peak = 0
    maxdd_duration = 0
    for i, frame in enumerate(curves):
        value = frame['equity']
        if value >= peak:
            peak, last_peak = value, i
        else:
            maxdd = min(maxdd, value/peak-1)
            maxdd_duration = max(maxdd_duration, i-last_peak)
    intervals = []
    for a,b in zip(curves,curves[1:]):
        if a['session'] != b['session']:
            continue
        length = duration(minute(a['timestamp']), minute(b['timestamp']))
        if length:
            intervals.append((a['utilization'],length,a['positions'],a['cash']))
    clock = sum(length for _,length,_,_ in intervals)
    if not clock:
        raise ValueError('EMPTY_VALUATION_CLOCK')
    util = [x[0] for x in intervals]
    weights = [x[1] for x in intervals]
    weighted = lambda values:sum(v*w for v,w in zip(values,weights))/clock
    rolling = {}
    for window in [20,22,24]:
        rows=[]
        for start in range(len(days)-window+1):
            multiple=assets[start+window]/assets[start]
            rows.append({'start_session':days[start], 'end_session':days[start+window-1],
                         'start_session_index':start+1, 'end_session_index':start+window,
                         'multiple':multiple,'equivalent_from_1m':multiple*1_000_000})
        values=[r['multiple'] for r in rows]
        rolling[str(window)]={'windows_N':len(rows), 'min_multiple':min(values) if values else None,
             'median_multiple':median(values) if values else None,
             'mean_multiple':mean(values) if values else None,
             'max_multiple':max(values) if values else None,
             'doubling_windows_N':sum(v>=2 for v in values), 'rows':rows}
    pnls=[Decimal(t['pnl']) for t in trades]
    turnover=sum(Decimal(t['entry_debit'])+Decimal(t['exit_credit']) for t in trades)
    friction=sum((Decimal(t['buy'])/Decimal('1.0005')*Decimal('.0005')+
                  Decimal(t['sell'])/Decimal('.9995')*Decimal('.0005'))*t['quantity'] for t in trades)
    doubles=[j-i for i in range(len(assets)) for j in range(i+1,len(assets)) if assets[j]>=2*assets[i]]
    result={'initial_equity':1_000_000, 'final_equity':assets[-1],
            'total_return':assets[-1]/assets[0]-1,
            'geometric_mean_session':math.expm1(sum(math.log1p(r) for r in returns)/len(days)),
            'arithmetic_mean_session':mean(returns), 'median_session_return':median(returns),
            'session_return_volatility':pstdev(returns),
            'winning_sessions_N':sum(r>0 for r in returns), 'losing_sessions_N':sum(r<0 for r in returns),
            'flat_sessions_N':sum(r==0 for r in returns), 'worst_session_return':min(returns),
            'max_drawdown':maxdd, 'drawdown_duration_observation_frames':maxdd_duration,
            'mean_utilization':weighted(util), 'median_utilization':weighted_median(util,weights),
            'utilization_ge80_time':weighted([u>=.8 for u in util]),
            'utilization_ge90_time':weighted([u>=.9 for u in util]),
            'peak_utilization':max(f['utilization'] for f in curves),
            'average_concurrent_positions':weighted([x[2] for x in intervals]),
            'average_idle_cash_jpy':weighted([x[3] for x in intervals]),
            'zero_exposure_minutes':sum(x[1] for x in intervals if x[2]==0),
            'observed_active_minutes':clock, 'cash_recycling_count':len(trades),
            'realized_pnl_jpy':float(sum(pnls)), 'commission_jpy':0,
            'execution_friction_jpy':float(friction), 'gross_effective_turnover_jpy':float(turnover),
            'shortest_doubling_sessions':min(doubles) if doubles else None,
            'rolling':rolling, 'session_rows':sessions,
            'weighted_utilization_clock':'09:00–11:30 and12:30–15:31; lunch excluded; preclose/auction/receipt capital-lock retained',
            'curve_role':'FULL_OBSERVED_WINDOW_MTM_REFERENCE_NOT_LIVE_CERTIFIED'}
    for window in [20,22,24]:
        result[f'rolling{window}_max_multiple']=rolling[str(window)]['max_multiple']
    return result
