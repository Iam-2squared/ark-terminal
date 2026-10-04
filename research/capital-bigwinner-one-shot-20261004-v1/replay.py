"""Three fixed MAX profiles share one frozen causal score stream. No fit here."""
from collections import Counter,defaultdict
from datetime import datetime
from decimal import Decimal
import json
import math
from statistics import mean,median
from checkpoint import OUT,save,sha
from contracts import D,BUY,SELL,CAP,BASE,buy_quantity,last_actual_mark,eod_intent,eod_source,valid_market,limit_up_confirmed
from prepare import PRIVATE,rows,gzwrite

def clock(value):
    t=datetime.fromisoformat(value)
    return t.hour*60+t.minute

def frozen_execution(book):
    x=book['frozen_exit']
    if x['sell_status']!='FILLED':return None
    available=clock(x['sell_source_assumed_available_at'])
    # The confirmed fill event precedes15:20 overlay only if source already available.
    if available>920:return None
    source=next((r for r in book['market'] if r['minute']==x['sell_minute']),None)
    if source is None or not valid_market(source):return {'blocked':'FROZEN_EXIT_SOURCE_LINEAGE_BLOCKED','release_minute':available}
    reference=source['O'] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else source['C']
    price=D(str(reference))*SELL
    assert price==D(x['sell_price_decimal']),'FROZEN_EXIT_SOURCE_PRICE_MISMATCH'
    return {'kind':'FROZEN_EXIT_V3','source_minute':x['sell_minute'],'release_minute':available,
            'price':str(price),'lineage':source['lineage']}

def day_replay(n,day,candidates,books,starting_cash,primary_chain=True):
    cash=D(str(starting_cash));positions={};fills=defaultdict(list)
    events=defaultdict(list)
    for r in candidates:events[r['entry_minute']].append(r)
    decisions=[];trades=[];snapshots=[];intents=[];blockers=[]
    original_pool=cash;recycled_pool=D(0);recycled_used=D(0)
    peak_concurrent=0;cash_min=cash
    def equity():return cash+sum(p['quantity']*p['mark'] for p in positions.values())
    for t in range(540,932):
        # 1. Closed/past actual marks only. No-trade retains same-session last trade.
        for key,p in positions.items():
            book=books[key]
            mark,known=last_actual_mark(book['market'],p['entry_minute'],t,p['raw_reference'])
            p['mark']=mark;p['mark_known_minute']=known
        # 2+3. Confirmed source fill -> one cash release, then new Entry decisions.
        for key,source in sorted(fills.pop(t,[]),key=lambda x:x[0]):
            assert key in positions,'DUPLICATE_SELL_OR_CASH_RELEASE'
            if source.get('blocked'):
                blockers.append({'entry_id':key,'minute':t,'reason':source['blocked']})
                continue
            p=positions.pop(key);credit=D(source['price'])*p['quantity'];cash+=credit;recycled_pool+=credit
            trades.append({'entry_id':key,'session':day,'quantity':p['quantity'],'entry_minute':p['entry_minute'],
                'release_minute':t,'source_minute':source['source_minute'],'exit_kind':source['kind'],
                'buy_effective':str(p['buy']),'sell_effective':source['price'],
                'debit':str(p['buy']*p['quantity']),'credit':str(credit),
                'pnl':str(credit-p['buy']*p['quantity']),'lineage':source['lineage'],'commission':0})
        batch=sorted(events.get(t,[]),key=lambda r:(-r['p_bigwinner5'],r['entry_timestamp'],r['symbol']))
        eligible=[]
        for r in batch:
            d={'entry_id':r['entry_id'],'session':day,'minute':t,'p_bigwinner5':r['p_bigwinner5'],
               'rank':r['rank'],'quantity':0,'reason':None,'primary_chain':primary_chain}
            decisions.append(d)
            if t>=920:d['reason']='CAPITAL_EOD_ENTRY_CUTOFF';continue
            if not r['liquidity']['eligible']:d['reason']=r['liquidity']['reason'];continue
            if r['rank']=='C':d['reason']='BELOW_BIGWINNER_BASE_RATE';continue
            if r['rank'] not in CAP:d['reason']='SCORE_INPUT_UNKNOWN';continue
            if any(p['symbol']==r['symbol'] for p in positions.values()):d['reason']='SYMBOL_ALREADY_OPEN';continue
            eligible.append((r,d))
        slots=max(0,n-len(positions));picked=eligible[:slots]
        for r,d in eligible[slots:]:d['reason']='MAX_POSITION_CAP'
        if picked:
            eq=equity();exposure=eq-cash
            all_ranks=[p['rank'] for p in positions.values()]+[r['rank'] for r,d in picked]
            best=min(all_ranks,key=lambda rk:('S','A','B').index(rk))
            target_util=min(D('.92'),BASE[best]+D('.055')*(len(all_ranks)-1))
            available=min(cash,max(D(0),eq*target_util-exposure))
            weights=sum(D(str(r['p_bigwinner5'])) for r,d in picked)
            for r,d in picked:
                target=available*D(str(r['p_bigwinner5']))/weights
                cap=eq*CAP[r['rank']];liq=D(r['liquidity']['capacity'])
                q=buy_quantity(r['raw_reference'],target,cap,liq,cash)
                d.update(target_notional=str(target),equity_cap=str(cap),liquidity_cap=str(liq),
                         target_utilization=str(target_util),cash_before=str(cash),equity_before=str(eq))
                if q<100:
                    d['reason']='CAPITAL_SKIP_LIQUIDITY_OR_LOT' if liq<D(r['raw_reference'])*BUY*100 else 'CASH_OR_LOT_CONSTRAINED'
                    continue
                raw=D(r['raw_reference']);buy=raw*BUY;debit=buy*q
                assert debit<=cash and debit<=cap and debit<=liq
                cash-=debit;cash_min=min(cash_min,cash)
                initial_used=min(original_pool,debit);original_pool-=initial_used
                from_recycled=debit-initial_used;recycled_pool-=from_recycled;recycled_used+=from_recycled
                assert recycled_pool>=0
                d.update(quantity=q,reason='FUNDED',debit=str(debit),recycled_cash_used=str(from_recycled))
                key=r['entry_id']
                positions[key]={'symbol':r['symbol'],'entry_minute':t,'raw_reference':str(raw),'buy':buy,
                                'quantity':q,'mark':raw,'mark_known_minute':t,'rank':r['rank'],
                                'side':'LONG','margin':False,'intent_issued':False}
                peak_concurrent=max(peak_concurrent,len(positions))
                assert len(positions)<=n and q%100==0 and cash>=0
                # Future source/outcome book is consulted ONLY after the BUY decision.
                book=books[key]
                if not book['capture_complete'] or not book.get('entry_actual_source'):
                    blockers.append({'entry_id':key,'minute':t,'reason':'MTM_SOURCE_LINEAGE_BLOCKED'})
                prior=frozen_execution(book)
                if prior:
                    assert prior['release_minute']>t,'EXIT_BEFORE_ENTRY'
                    fills[prior['release_minute']].append((key,prior))
        if t==920:
            for key,p in sorted(positions.items()):
                it=eod_intent(p)
                assert it is not None,'DUPLICATE_EOD_INTENT'
                p['intent_issued']=True
                # One full remaining symbolic intent; coalesces any pending Frozen
                # SELL into the same research lifecycle rather than double-selling.
                it.update(entry_id=key,session=day,limit_up_status='LIMIT_UP_CONFIRMED' if limit_up_confirmed(books[key]['limit_up_authority'],day,t) else 'LIMIT_UP_UNKNOWN')
                intents.append(it)
                source=eod_source(books[key]['market'])
                if source:fills[source['release_minute']].append((key,source))
                else:blockers.append({'entry_id':key,'minute':931,'reason':'LIMIT_UP_EOD_UNEXECUTED_FAIL_CLOSED' if it['limit_up_status']=='LIMIT_UP_CONFIRMED' else 'EOD_UNEXECUTED_FAIL_CLOSED'})
        eq=equity();exposure=eq-cash
        assert cash>=0 and eq>0
        snapshots.append({'session':day,'minute':t,'equity':str(eq),'cash':str(cash),
            'exposure':str(exposure),'utilization':float(exposure/eq),'concurrent':len(positions),
            'primary_chain':primary_chain,'known_marks':{key:p['mark_known_minute'] for key,p in positions.items()}})
    if positions:
        known={b['entry_id'] for b in blockers}
        for key in positions:
            if key not in known:blockers.append({'entry_id':key,'minute':931,'reason':'EOD_UNEXECUTED_FAIL_CLOSED'})
    valid=not blockers and not positions
    return {'session':day,'status':'COMPLETE' if valid else 'PORTFOLIO_MEASUREMENT_BLOCKED_EXECUTION',
        'starting_cash':str(starting_cash),'ending_cash':str(cash) if valid else None,
        'daily_return':float(cash/D(str(starting_cash))-1) if valid and primary_chain else None,
        'diagnostic_daily_return':float(cash/D(str(starting_cash))-1) if valid else None,
        'primary_chain':primary_chain,'blockers':blockers,'open_obligations':list(positions),
        'cash_min':str(cash_min),'max_concurrent':peak_concurrent,'recycled_cash_used':str(recycled_used)},decisions,trades,snapshots,intents

def summary(n,daily,decisions,trades,curves,intents):
    valid=[d for d in daily if d['daily_return'] is not None]
    returns=[d['daily_return'] for d in valid]
    rolling=[]
    for start in range(len(daily)-19):
        win=daily[start:start+20]
        if not all(d['daily_return'] is not None for d in win):continue
        multiple=float(D(win[-1]['ending_cash'])/D(win[0]['starting_cash']))
        rolling.append({'start_session':win[0]['session'],'end_session':win[-1]['session'],
                        'growth_multiple':multiple,'amount_from_1m':1000000*multiple,'hit':multiple>=2})
    multiples=[w['growth_multiple'] for w in rolling];hits=[w for w in rolling if w['hit']]
    primary_curves=[c for c in curves if c['primary_chain'] and c['session'] in {d['session'] for d in valid}]
    peak=D(1000000);maxdd=D(0)
    for c in primary_curves:
        eq=D(c['equity']);peak=max(peak,eq);maxdd=max(maxdd,(peak-eq)/peak)
    samples=[c for c in primary_curves if 540<=c['minute']<690 or 750<=c['minute']<930]
    util=[c['utilization'] for c in samples]
    funded=[d for d in decisions if d['reason']=='FUNDED']
    return {'profile':f'CAPITAL_VNEXT_MAX{n}','max_positions':n,
        'geometric_mean_daily_return':math.expm1(mean(math.log1p(r) for r in returns)) if returns else None,
        'arithmetic_mean_daily_return':mean(returns) if returns else None,
        'median_daily_return':median(returns) if returns else None,'valid_primary_day_N':len(valid),
        'blocked_execution_day_N':sum(d['status']!='COMPLETE' for d in daily),
        'primary_origin_unknown_day_N':sum(not d['primary_chain'] for d in daily),
        'valid_rolling20_window_N':len(rolling),'rolling20_minimum':min(multiples) if multiples else None,
        'rolling20_median':median(multiples) if multiples else None,'rolling20_arithmetic_mean':mean(multiples) if multiples else None,
        'rolling20_maximum':max(multiples) if multiples else None,'north_star_hit_any':bool(hits) if rolling else None,
        'north_star_hit_N':len(hits),'north_star_hit_rate':len(hits)/len(rolling) if rolling else None,
        'earliest_2x_hit':hits[0] if hits else None,
        'maximum_20_session_amount':max(w['amount_from_1m'] for w in rolling) if rolling else None,
        'final_equity':float(D(daily[-1]['ending_cash'])) if daily[-1]['daily_return'] is not None else None,
        'total_return':float(D(daily[-1]['ending_cash'])/D(1000000)-1) if daily[-1]['daily_return'] is not None else None,
        'max_drawdown':float(maxdd) if valid else None,
        'utilization_mean':mean(util) if util else None,'utilization_median':median(util) if util else None,
        'time_utilization_ge80':mean(v>=.8 for v in util) if util else None,
        'time_utilization_ge90':mean(v>=.9 for v in util) if util else None,
        'mean_idle_cash_fraction':mean(1-v for v in util) if util else None,
        'turnover_cash_jpy':float(sum((D(t['debit'])+D(t['credit']) for t in trades),D(0))),
        'capital_recycling_closed_N':len(trades),'capital_recycling_used_jpy':float(sum((D(d['recycled_cash_used']) for d in daily),D(0))),
        'funded_N':len(funded),'rejected_N':len(decisions)-len(funded),'cash_minimum':float(min(D(d['cash_min']) for d in daily)),
        'max_concurrent_actual':max(d['max_concurrent'] for d in daily),
        'execution_source_unresolved_N':sum(len(d['open_obligations']) for d in daily),
        'reasons':dict(Counter(d['reason'] for d in decisions)),
        'EOD_intent_N':len(intents),'Frozen_exit_N':sum(t['exit_kind']=='FROZEN_EXIT_V3' for t in trades),
        'EOD_regular_N':sum(t['exit_kind']=='EOD_REGULAR' for t in trades),
        'EOD_auction_N':sum(t['exit_kind']=='EOD_EXACT_1530_AUCTION' for t in trades),
        'rolling20_windows':rolling,'daily_series':daily,'productionReady':False}

def run_profile(n,stream,books):
    days=sorted({r['session'] for r in stream})
    cash=D(1000000);chain=True
    daily=[];decisions=[];trades=[];curves=[];intents=[]
    for day in days:
        candidates=[r for r in stream if r['session']==day]
        d,ds,ts,cs,its=day_replay(n,day,candidates,books,cash if chain else D(1000000),chain)
        daily.append(d);decisions+=ds;trades+=ts;curves+=cs;intents+=its
        if chain and d['status']=='COMPLETE':cash=D(d['ending_cash'])
        elif chain:chain=False
    return summary(n,daily,decisions,trades,curves,intents),decisions,trades,curves,intents

def main():
    stream=rows(PRIVATE/'ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz')
    books={r['entry_id']:r for r in rows(PRIVATE/'MARKET_EXECUTION_BOOK.jsonl.gz')}
    results=[]
    for n in (3,4,5):
        result,ds,ts,cs,it=run_profile(n,stream,books)
        result['score_stream_sha256']=sha(PRIVATE/'ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz')
        for label,data in [('DECISIONS',ds),('TRADES',ts),('CURVE',cs),('INTENTS',it)]:
            gzwrite(PRIVATE/f'MAX{n}_{label}.jsonl.gz',data)
        save(PRIVATE/f'MAX{n}_RESULT.json',result)
        results.append(result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('rolling20_windows','daily_series')}))
    save(OUT/'MAX3_4_5_REPLAY.json',{'profiles':results,'fits_in_replay':0,'profiles_compared':3,
        'score_stream_sha256':sha(PRIVATE/'ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz'),'result_based_retuning':False,
        'private_rows_public':0,'research_only':True})

if __name__=='__main__':main()
