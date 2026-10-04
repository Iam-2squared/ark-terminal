"""Cash LONG research contracts. Pure funding inputs contain no outcome fields."""
from decimal import Decimal, ROUND_FLOOR
from statistics import median
import math

D=Decimal
BUY=D('1.0005')
SELL=D('0.9995')
CAP={'S':D('.45'),'A':D('.35'),'B':D('.25')}
BASE={'S':D('.68'),'A':D('.56'),'B':D('.44')}

def valid_market(r,auction=False):
    try:
        v={k:D(str(r[k])) for k in ('O','H','L','C','Vo','Va')}
        if not all(x.is_finite() and x>0 for x in v.values()):return False
        if not v['L']<=min(v['O'],v['C'])<=max(v['O'],v['C'])<=v['H']:return False
        return not auction or v['O']==v['H']==v['L']==v['C']
    except (KeyError,ValueError,TypeError):return False

def liquidity(day,symbol,raw_reference,calendar,source):
    dates=[d for d in calendar if d<day][-20:]
    history=[]
    for prior in dates:
        r=source.get((prior,symbol))
        if not r or not r.get('daily') or not r.get('minute_source') or not r.get('daily_source'):continue
        if not r['minute_source'].get('date_scope_complete') or not r['minute_source'].get('terminal_pagination_proven'):continue
        if not r['daily_source'].get('date_scope_complete'):continue
        # prior completed sessions only. Current/future records are never read.
        assert r['session']<day
        try:va=D(str(r['daily']['Va']))
        except Exception:continue
        if not va.is_finite() or va<0:continue
        history.append((prior,va,D(len(r['active_windows']))/D(65)))
    result={'support':len(history),'lookback_dates':dates,'support_dates':[h[0] for h in history],
            'median_value':None,'median_coverage':None,'capacity':None,'eligible':False,
            'reason':'LIQUIDITY_UNKNOWN','minimum_lot_notional':str(D(100)*D(str(raw_reference)))}
    if len(history)<10:return result
    va=median([h[1] for h in history]);coverage=median([h[2] for h in history])
    result.update(median_value=str(va),median_coverage=str(coverage),capacity=str(va*D('.01')))
    value_ok=D(result['minimum_lot_notional'])<=va*D('.005')
    coverage_ok=coverage>=D('.60')
    result.update(eligible=value_ok and coverage_ok,
                  reason='LIQUIDITY_ELIGIBLE' if value_ok and coverage_ok else 'LIQUIDITY_HARD_GATE_REJECT',
                  lot_gate_pass=value_ok,coverage_gate_pass=coverage_ok)
    return result

def rank(prob,base_rate):
    if prob is None or base_rate is None or not math.isfinite(prob) or not 0<=prob<=1 or not 0<base_rate<1:
        return 'UNKNOWN',None
    lift=prob/base_rate
    return ('S' if lift>=2 else 'A' if lift>=1.5 else 'B' if lift>=1 else 'C'),lift

def buy_quantity(raw_price,target,rank_cap,liquidity_cap,cash):
    # All caps apply to actual cash debit, conservatively including the5bps once.
    limit=min(D(str(target)),D(str(rank_cap)),D(str(liquidity_cap)),D(str(cash)))
    per_share=D(str(raw_price))*BUY
    q=int((limit/(per_share*100)).to_integral_value(rounding=ROUND_FLOOR))*100
    return max(0,q)

def last_actual_mark(rows,entry_minute,t,anchor):
    candidates=[r for r in rows if entry_minute<=r['minute'] and r['minute']+1<=t and valid_market(r)]
    if candidates:
        row=max(candidates,key=lambda r:r['minute'])
        return D(str(row['C'])),row['minute']+1
    return D(str(anchor)),entry_minute

def limit_up_confirmed(record,day,t):
    return bool(record and record.get('status')=='LIMIT_UP_CONFIRMED'
                and record.get('authoritative_price_limit_source') and record.get('causal_exchange_status')
                and record.get('session')==day and record.get('known_minute',9999)<=t
                and record.get('observed_minute',9999)<=t)

def eod_intent(position,t=920):
    if t!=920 or position.get('closed') or position['quantity']<=0 or position.get('intent_issued'):return None
    assert position.get('side','LONG')=='LONG' and not position.get('margin',False)
    return {'minute':920,'side':'SELL','quantity':position['quantity'],'sor':True,
            'order_type':'MARKET','condition':'DAY','transmitted':False}

def eod_source(rows):
    regular=sorted([r for r in rows if 920<=r['minute']<925 and valid_market(r)],key=lambda r:r['minute'])
    auction=[r for r in rows if r['minute']==930 and valid_market(r,True)]
    selected=regular[0] if regular else auction[0] if auction else None
    if selected is None:return None
    kind='EOD_REGULAR' if regular else 'EOD_EXACT_1530_AUCTION'
    p=D(str(selected['O'] if regular else selected['C']))*SELL
    return {'kind':kind,'source_minute':selected['minute'],'release_minute':selected['minute']+1,
            'price':str(p),'lineage':selected['lineage']}
