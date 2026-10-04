"""Two capacity-aware one-shot causal capital chains. Runtime never receives teachers/Oracle."""
from control import *
from execution_bridge import FROZEN,BUY
from runtime import ARMS,order,gate,allocation
from decimal import Decimal as D
from collections import defaultdict,Counter
from statistics import mean,median
import math
def day_replay(day,candidates,books,starting_cash,arm,tables):
 cash=D(str(starting_cash));positions={};fills=defaultdict(list);events=defaultdict(list)
 for r in candidates:events[r['entry_minute']].append(r)
 decisions=[];trades=[];frames=[];intents=[];blockers=[];original_pool=cash;recycled_pool=D(0);recycled_used=D(0);peak=0;cash_min=cash
 def equity():return cash+sum(p['quantity']*p['mark'] for p in positions.values())
 def snapshot():return [{'entry_id':k,'symbol':p['symbol'],'pP':p['pP'],'entry_minute':p['entry_minute'],'quantity':p['quantity'],'band':p['band']} for k,p in sorted(positions.items())]
 for t in range(540,932):
  for key,p in positions.items():
   while p['mark_index']<len(p['mark_updates']) and p['mark_updates'][p['mark_index']][0]<=t:
    known,price=p['mark_updates'][p['mark_index']];p['mark']=price;p['mark_known_minute']=known;p['mark_index']+=1
  for key,source in sorted(fills.pop(t,[]),key=lambda x:x[0]):
   assert key in positions
   if source.get('blocked'):blockers.append({'entry_id':key,'minute':t,'reason':source['blocked']});continue
   p=positions.pop(key);credit=D(source['price'])*p['quantity'];cash+=credit;recycled_pool+=credit;debit=p['buy']*p['quantity']
   trades.append({'entry_id':key,'session':day,'symbol':p['symbol'],'quantity':p['quantity'],'entry_minute':p['entry_minute'],'release_minute':t,'source_minute':source['source_minute'],'exit_kind':source['kind'],'buy_effective':str(p['buy']),'sell_effective':source['price'],'debit':str(debit),'credit':str(credit),'pnl':str(credit-debit),'net_return':float(credit/debit-1),'commission':0})
  batch=sorted(events.get(t,[]),key=order);eligible=[];before=snapshot()
  for batch_index,r in enumerate(batch):
   d={'entry_id':r['entry_id'],'session':day,'symbol':r['symbol'],'minute':t,'pP':r['pP'],'rank_units':r['rank_units'],'train_N':r['train_N'],'r':r['r'],'band':r['band'],'block':r['block'],'held_before_batch':before,'batch_index':batch_index,'quantity':0,'reason':None,'profile':arm}
   decisions.append(d)
   if t>=920:d['reason']='CUTOFF';continue
   if r['band']=='P_BELOW':d['reason']='RANK_BASE_REJECT';continue
   assert math.isfinite(r['pP']) and 0<r['pP']<=1 and r['band'] in ('P_HIGH','P_MID','P_BASE')
   if any(p['symbol']==r['symbol'] for p in positions.values()):d['reason']='SAME_SYMBOL';continue
   eligible.append((r,d))
  picked=[]
  for r,d in eligible:
   occupancy=len(positions)+len(picked);allowed,why,audit=gate(arm,r,occupancy,t,tables[str(r['block'])]);d.update(audit,slot_action='ACCEPT' if allowed else 'REJECT',slot_reason=why)
   if not allowed:d['reason']=why;continue
   d['slot_admission_index']=occupancy+1;picked.append((r,d))
  if picked:
   eq=equity();exposure=eq-cash
   assigned=allocation([r for r,d in picked],eq,exposure,cash,[p['band'] for p in positions.values()])
   for (r,d),a in zip(picked,assigned):
    d.update({k:str(v) if isinstance(v,D) else v for k,v in a.items() if k!='entry_id'});q=a['quantity'];buy=D(r['raw_reference'])*BUY;d['cash_before']=str(cash)
    if q<100:d['reason']='CASH_OR_LOT';continue
    debit=q*buy;assert debit==a['debit'] and debit<=cash;cash-=debit;cash_min=min(cash_min,cash)
    used=min(original_pool,debit);original_pool-=used;recycled=debit-used;recycled_pool-=recycled;recycled_used+=recycled;assert recycled_pool>=0 and cash>=0
    d.update(quantity=q,reason='FUNDED',debit=str(debit),recycled_cash_used=str(recycled),funded_slot=len(positions)+1)
    key=r['entry_id'];raw=D(r['raw_reference']);book=books[key]
    positions[key]={'symbol':r['symbol'],'entry_minute':t,'raw_reference':str(raw),'buy':buy,'quantity':q,'mark':raw,'mark_known_minute':t,'band':r['band'],'pP':r['pP'],'side':'LONG','margin':False,'intent_issued':False}
    peak=max(peak,len(positions));assert len(positions)<=3 and q%100==0
    # Adapter source suffix does not reach gate/allocation; only confirmed-time
    # marks and releases change future portfolio state.
    positions[key]['mark_updates']=sorted([(row['minute']+1,D(row['C'])) for row in book['market'] if row.get('session')==day and row['minute']>=t and FROZEN.valid_market(row)])
    positions[key]['mark_index']=0
    if not book['capture_complete'] or not book.get('entry_actual_source'):blockers.append({'entry_id':key,'minute':t,'reason':'SOURCE_BLOCKED'})
    source=FROZEN.frozen_execution(book)
    if source:
     assert source['release_minute']>t;fills[source['release_minute']].append((key,source))
  if t==920:
   for key,p in sorted(positions.items()):
    it=FROZEN.eod_intent(p);assert it is not None;p['intent_issued']=True;it.update(entry_id=key,session=day);intents.append(it)
    source=FROZEN.eod_source(books[key]['market'],day)
    if source:fills[source['release_minute']].append((key,source))
    else:blockers.append({'entry_id':key,'minute':931,'reason':'EOD_EXECUTION_BLOCKED'})
  eq=equity();assert cash>=0 and eq>0
  frames.append({'session':day,'minute':t,'equity':str(eq),'cash':str(cash),'exposure':str(eq-cash),'utilization':float((eq-cash)/eq),'concurrent':len(positions),'known_marks':{k:p['mark_known_minute'] for k,p in positions.items()}})
 valid=not positions and not blockers
 return {'session':day,'status':'COMPLETE' if valid else 'EXECUTION_UNRESOLVED_FAIL_CLOSED','starting_cash':str(starting_cash),'ending_cash':str(cash) if valid else None,'daily_return':float(cash/D(str(starting_cash))-1) if valid else None,'cash_min':str(cash_min),'max_concurrent':peak,'recycled_cash_used':str(recycled_used),'blockers':blockers,'open_obligations':sorted(positions)},decisions,trades,frames,intents
def summary(arm,daily,decisions,trades,curves,intents):
 assert len(daily)==38 and all(d['status']=='COMPLETE' for d in daily)
 returns=[d['daily_return'] for d in daily];rolling=[]
 for start in range(19):
  win=daily[start:start+20];multiple=float(D(win[-1]['ending_cash'])/D(win[0]['starting_cash']));rolling.append({'start_session':win[0]['session'],'end_session':win[-1]['session'],'growth_multiple':multiple,'amount_from_1m':1000000*multiple,'hit':multiple>=2})
 multiples=[w['growth_multiple'] for w in rolling];peak=D(1000000);maxdd=D(0)
 for c in curves:eq=D(c['equity']);peak=max(peak,eq);maxdd=max(maxdd,(peak-eq)/peak)
 samples=[c for c in curves if 540<=c['minute']<690 or 750<=c['minute']<930];util=[c['utilization'] for c in samples];funded=[d for d in decisions if d['reason']=='FUNDED']
 return {'profile':arm,'geometric_mean_daily_return':math.expm1(mean(math.log1p(r) for r in returns)),'arithmetic_mean_daily_return':mean(returns),'median_daily_return':median(returns),'valid_primary_day_N':38,'blocked_execution_day_N':0,'valid_rolling20_window_N':19,'rolling20_minimum':min(multiples),'rolling20_median':median(multiples),'rolling20_arithmetic_mean':mean(multiples),'rolling20_maximum':max(multiples),'north_star_hit_N':sum(w['hit'] for w in rolling),'north_star_hit_rate':sum(w['hit'] for w in rolling)/19,'final_equity':float(D(daily[-1]['ending_cash'])),'final_equity_exact':daily[-1]['ending_cash'],'total_return':float(D(daily[-1]['ending_cash'])/D(1000000)-1),'max_drawdown':float(maxdd),'utilization_mean':mean(util),'utilization_median':median(util),'idle_cash_mean_jpy':float(sum((D(c['cash']) for c in samples),D(0))/len(samples)),'mean_idle_cash_fraction':mean(1-v for v in util),'turnover_cash_jpy':float(sum((D(t['debit'])+D(t['credit']) for t in trades),D(0))),'capital_recycling_used_jpy':float(sum((D(d['recycled_cash_used']) for d in daily),D(0))),'funded_N':len(funded),'avg_funded_per_session':len(funded)/38,'cash_minimum':str(min(D(d['cash_min']) for d in daily)),'max_concurrent_actual':max(d['max_concurrent'] for d in daily),'execution_source_unresolved_N':0,'reasons':dict(Counter(d['reason'] for d in decisions)),'EOD_intent_N':len(intents),'Frozen_exit_N':sum(t['exit_kind']=='FROZEN_EXIT_V3' for t in trades),'EOD_regular_N':sum(t['exit_kind']=='EOD_REGULAR' for t in trades),'EOD_auction_N':sum(t['exit_kind']=='EOD_EXACT_1530_AUCTION' for t in trades),'rolling20_windows':rolling,'daily_series':daily,'productionReady':False}
def run(arm,stream,books,tables):
 days=read(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json')['OOF38'];cash=D(1000000);daily=[];decisions=[];trades=[];curves=[];intents=[]
 for day in days:
  d,ds,ts,cs,it=day_replay(day,[r for r in stream if r['session']==day],books,cash,arm,tables);daily.append(d);decisions+=ds;trades+=ts;curves+=cs;intents+=it
  if d['status']!='COMPLETE':
   return {'profile':arm,'measurement_status':'CAPITAL_MEASUREMENT_BLOCKED_EXECUTION','valid_primary_day_N':sum(x['status']=='COMPLETE' for x in daily),'blocked_execution_day_N':1,'daily_series':daily,'reasons':dict(Counter(x['reason'] for x in decisions)),'execution_source_unresolved_N':len(d['open_obligations']),'productionReady':False},decisions,trades,curves,intents
  cash=D(d['ending_cash'])
 return summary(arm,daily,decisions,trades,curves,intents),decisions,trades,curves,intents
def main():
 claim=read(OUT/'MAIN_REPLAY_CLAIM.json');assert claim['B1_replay']==1 and claim['B2_replay']==1
 assert read(OUT/'CAUSAL_CANARY_RESULTS.json')['all_PASS']
 assert read(OUT/'PRE_MAIN_INDEPENDENT_POLICY_AUDIT.json')['mismatch_N']==0
 assert (OUT/'receipts/R9_MAIN_REPLAY_CLAIM_ACTUAL_GET.json').exists(),'ACTUAL_GET_CLAIM_REQUIRED'
 for name,value in claim['code_sha256'].items():assert sha(CODE/name)==value
 stream=rows(PIN/'RANK_NATIVE_RUNTIME.jsonl.gz');books={r['entry_id']:r for r in rows(INPUT/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};tables=read(OUT/'B1_CAPACITY_PRESSURE_TABLE.json');tenures=read(OUT/'B2_TENURE_LOOKUP_TABLE.json');results={}
 for b in tables:tables[b]['tenure']=tenures[b]
 for arm in ARMS:
  save(PRIVATE/f'{arm}_STARTED.json',{'exact_jst':now(),'claim_sha256':sha(OUT/'MAIN_REPLAY_CLAIM.json'),'single_execution':True,'rerun_allowed':False})
  result,ds,ts,cs,it=run(arm,stream,books,tables)
  for name,data in [('DECISIONS',ds),('TRADES',ts),('CURVE',cs),('INTENTS',it)]:gzsave(PRIVATE/f'{arm}_{name}.jsonl.gz',data)
  result['ledger_sha256']={name:sha(PRIVATE/f'{arm}_{name}.jsonl.gz') for name in ('DECISIONS','TRADES','CURVE','INTENTS')};save(OUT/f'{arm}_RESULT.json',result);results[arm]=result
  print(json.dumps({k:result.get(k) for k in ('profile','measurement_status','rolling20_minimum','rolling20_arithmetic_mean','rolling20_median','rolling20_maximum','north_star_hit_N','geometric_mean_daily_return','final_equity','max_drawdown','funded_N')}),flush=True)
 save(OUT/'MAIN_REPLAY_RESULT.json',{'exact_jst':now(),'arms':results,'B1_replay':1,'B2_replay':1,'primary_replays':2,'saved_reference_replays':0,'new_fits':0,'teacher_regeneration':0,'single_execution_claim_sha256':sha(OUT/'MAIN_REPLAY_CLAIM.json'),'Safety':SAFETY})
 checkpoint('R10_B1_B2_REPLAY_COMPLETE','TWO_FIXED_SINGLE_EXECUTION_LEDGERS_SAVED',['B1 primary once','B2 primary once','economic/preservation ledgers same invocation'],{'primary_replays':2,'day_status':{a:r.get('measurement_status','COMPLETE') for a,r in results.items()}},'Compute preservation and rolling20 from these exact ledgers; do not rerun',{'primary_pP_diagnostic_solve':1,'B1_replay':1,'B2_replay':1})
if __name__=='__main__':main()
