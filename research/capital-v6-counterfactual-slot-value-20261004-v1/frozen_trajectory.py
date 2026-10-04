"""One MAX3 counterfactual. Runtime allocation never receives outcome books."""
from collections import defaultdict,Counter
from decimal import Decimal
import json,math
from statistics import mean,median
from common import *

from execution import BUY,SELL,valid_market,frozen_execution,eod_intent,eod_source,limit_up_confirmed
from allocation import allocation,band

D=Decimal
from staircase import candidate_order
from frozen_v5_gate import gate


def day_replay(n,day,candidates,books,starting_cash,primary_chain=True,profile=PROFILE,tables=None,state_hook=None,trajectory_mode="v5"):
 assert n==3,'MAX3_ONLY_RESEARCH_POLICY'
 cash=D(str(starting_cash));positions={};fills=defaultdict(list);events=defaultdict(list)
 for r in candidates:events[r['entry_minute']].append(r)
 decisions=[];trades=[];frames=[];intents=[];blockers=[]
 original_pool=cash;recycled_pool=D(0);recycled_used=D(0);peak=0;cash_min=cash
 def equity():return cash+sum(p['quantity']*p['mark'] for p in positions.values())
 for t in range(540,932):
  for key,p in positions.items():
   assert books[key]['session']==day
   while p['mark_index']<len(p['mark_updates']) and p['mark_updates'][p['mark_index']][0]<=t:
    known,price=p['mark_updates'][p['mark_index']];p['mark']=price;p['mark_known_minute']=known;p['mark_index']+=1
  for key,source in sorted(fills.pop(t,[]),key=lambda x:x[0]):
   assert key in positions,'DUPLICATE_SELL_OR_RELEASE'
   if source.get('blocked'):blockers.append({'entry_id':key,'minute':t,'reason':source['blocked']});continue
   p=positions.pop(key);credit=D(source['price'])*p['quantity'];cash+=credit;recycled_pool+=credit
   debit=p['buy']*p['quantity']
   trades.append({'entry_id':key,'session':day,'quantity':p['quantity'],'entry_minute':p['entry_minute'],
    'release_minute':t,'source_minute':source['source_minute'],'exit_kind':source['kind'],
    'buy_effective':str(p['buy']),'sell_effective':source['price'],'debit':str(debit),'credit':str(credit),
    'pnl':str(credit-debit),'net_return':float(credit/debit-1),'lineage':source['lineage'],'commission':0})
  batch=sorted(events.get(t,[]),key=candidate_order)
  eligible=[]
  for r in batch:
   d={'entry_id':r['entry_id'],'session':day,'minute':t,'capital_score':r['capital_score'],
    'capacity_band':r['capacity_band'],'rank':r['rank'],'admission':r['admission'],'ML':r['ML'],'m2':r['m2'],'m3':r['m3'],'m5':r['m5'],'held_before_batch':sorted(positions),'profile':profile,'quantity':0,'reason':None,'primary_chain':primary_chain}
   decisions.append(d)
   if t>=920:d['reason']='CAPITAL_EOD_ENTRY_CUTOFF';continue
   if not r['admission']:d['reason']='UPWARD_BELOW_BASELINE';continue
   if band(r['capital_score']) is None:d['reason']='SCORE_INPUT_UNKNOWN';continue
   if any(p['symbol']==r['symbol'] for p in positions.values()):d['reason']='SYMBOL_ALREADY_OPEN';continue
   eligible.append((r,d))
  picked=[]
  for r,d in eligible:
   occupancy=len(positions)+len(picked)
   if state_hook is not None:
    prefix=[v for v in candidates if v['entry_minute']<t or v['entry_minute']==t and candidate_order(v)<candidate_order(r)]
    state_hook(r,positions,[z for z,dd in picked],cash,equity(),prefix,len(batch),batch.index(r),[dd['entry_id'] for dd in decisions if dd['reason']=='FUNDED'])
   if trajectory_mode=='v4':allowed,why,audit=occupancy<3,('V4_ADMISSION' if occupancy<3 else 'MAX_POSITION_CAP'),{}
   else:allowed,why,audit=gate(r,occupancy,t,tables[str(r['block'])])
   d.update(audit,slot_gate_reason=why,slot_gate_action='ADMIT' if allowed else 'REJECT')
   if not allowed:
    d['reason']='SLOT_RESERVE_REJECT' if why.startswith(('SLOT2_RESERVE','SLOT3_RESERVE')) else why
    continue
   d['slot_admission_index']=occupancy+1
   picked.append((r,d))
  if picked:
   eq=equity();exposure=eq-cash
   assigned=allocation([r for r,d in picked],eq,exposure,cash,[p['band'] for p in positions.values()])
   for (r,d),a in zip(picked,assigned):
    d.update({k:str(v) if isinstance(v,D) else v for k,v in a.items() if k!='entry_id'})
    q=a['quantity'];buy=D(r['raw_reference'])*BUY
    d['cash_before']=str(cash)
    if q<100:
     d['reason']='CASH_OR_LOT_CONSTRAINED'
     continue
    debit=q*buy;assert debit==a['debit'] and debit<=cash
    cash-=debit;cash_min=min(cash_min,cash)
    used=min(original_pool,debit);original_pool-=used;recycled=debit-used;recycled_pool-=recycled;recycled_used+=recycled
    assert recycled_pool>=0 and cash>=0
    d.update(quantity=q,reason='FUNDED',debit=str(debit),recycled_cash_used=str(recycled),funded_slot=len(positions)+1)
    key=r['entry_id'];raw=D(r['raw_reference'])
    positions[key]={'ML':r['ML'],'m5':r['m5'],'rank':r['rank'],'symbol':r['symbol'],'entry_minute':t,'raw_reference':str(raw),'buy':buy,
     'quantity':q,'mark':raw,'mark_known_minute':t,'band':r['capacity_band'],'side':'LONG','margin':False,'intent_issued':False}
    peak=max(peak,len(positions));assert len(positions)<=n and q%100==0
    # Execution/teacher suffix is consulted only after quantity/cash funding is fixed.
    book=books[key]
    positions[key]['mark_updates']=sorted([(row['minute']+1,D(row['C'])) for row in book['market']
     if row.get('session')==day and row['minute']>=t and valid_market(row)])
    positions[key]['mark_index']=0
    if not book['capture_complete'] or not book.get('entry_actual_source'):
     blockers.append({'entry_id':key,'minute':t,'reason':'MTM_SOURCE_LINEAGE_BLOCKED'})
    prior=frozen_execution(book)
    if prior:
     assert prior['release_minute']>t
     fills[prior['release_minute']].append((key,prior))
  if t==920:
   for key,p in sorted(positions.items()):
    it=eod_intent(p);assert it is not None;p['intent_issued']=True
    it.update(entry_id=key,session=day,limit_up_status='LIMIT_UP_CONFIRMED' if limit_up_confirmed(books[key]['limit_up_authority'],day,t) else 'LIMIT_UP_UNKNOWN')
    intents.append(it);source=eod_source(books[key]['market'],day)
    if source:fills[source['release_minute']].append((key,source))
    else:blockers.append({'entry_id':key,'minute':931,'reason':'LIMIT_UP_EOD_UNEXECUTED_FAIL_CLOSED' if it['limit_up_status']=='LIMIT_UP_CONFIRMED' else 'EOD_UNEXECUTED_FAIL_CLOSED'})
  eq=equity();assert cash>=0 and eq>0
  frames.append({'session':day,'minute':t,'equity':str(eq),'cash':str(cash),'exposure':str(eq-cash),
   'utilization':float((eq-cash)/eq),'concurrent':len(positions),'primary_chain':primary_chain,
   'known_marks':{k:p['mark_known_minute'] for k,p in positions.items()}})
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
  'cash_min':str(cash_min),'max_concurrent':peak,'recycled_cash_used':str(recycled_used)},decisions,trades,frames,intents

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

def run_profile(arm,n,stream,books,tables):
 assert n==3 and arm==PROFILE,'SINGLE_V4_PROFILE'
 days=sorted({r['session'] for r in stream});cash=D(1000000);chain=True
 daily=[];decisions=[];trades=[];curves=[];intents=[]
 for day in days:
  candidates=[r for r in stream if r['session']==day]
  d,ds,ts,cs,it=day_replay(n,day,candidates,books,cash if chain else D(1000000),chain,arm,tables=tables)
  daily.append(d);decisions+=ds;trades+=ts;curves+=cs;intents+=it
  if chain and d['status']=='COMPLETE':cash=D(d['ending_cash'])
  elif chain:chain=False
 result=summary(n,daily,decisions,trades,curves,intents)
 result.update(arm=arm,profile=arm,water_fill_lots_N=sum(d.get('water_fill_lots',0) for d in decisions),
  water_fill_funded_N=sum(d['reason']=='FUNDED' and d.get('water_fill_lots',0)>0 for d in decisions))
 return result,decisions,trades,curves,intents

if __name__=="__main__":raise SystemExit("TRAINING_ONLY_MODULE_NO_CONTROL_REPLAY")
