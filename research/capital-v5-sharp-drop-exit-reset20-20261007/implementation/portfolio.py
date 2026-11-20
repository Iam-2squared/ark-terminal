"""Derived event-loop adapter; all funding functions imported unchanged from S2."""
from io_utils import *
import sys
sys.path.insert(0,str(NATIVE))
from collections import defaultdict
from execution import BUY,SELL,valid_market,eod_intent,eod_source,limit_up_confirmed
from allocation import allocation,band
from staircase import candidate_order
from slot_policy import gate
from replay import day_replay as native_day_replay
PROFILE='CAPITAL_MAX3_SLOT_RESERVE_V1'

def day_replay(n,day,candidates,books,starting_cash,primary_chain=True,profile=PROFILE,tables=None,exit_plans=None):
 if exit_plans is None:return native_day_replay(n,day,candidates,books,starting_cash,primary_chain,profile,tables)
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
  for key,p in sorted(positions.items()):
   plan=p['exit_plan']
   if plan['action']=='EVIDENCE_GAP' and t==plan['block_minute']:
    blockers.append({'entry_id':key,'minute':t,'reason':plan['reason']})
   if plan['action']=='SD_FIRST' and t==plan['intent_minute']:
    p['overlay_pending']=True;p['intent_issued']=True
    intents.append({'entry_id':key,'session':day,'minute':t,'side':'SELL','quantity':p['quantity'],'reason':'SHARP_DROP_FIRST_OBSERVED','transmitted':False,'latched':True})
  if any(b['reason']=='EVIDENCE_GAP_BEFORE_CONTROL' and b['minute']==t for b in blockers):break
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
   allowed,why,audit=gate(r,occupancy,t,tables[str(r['block'])])
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
    positions[key]={'symbol':r['symbol'],'entry_minute':t,'raw_reference':str(raw),'buy':buy,
     'quantity':q,'mark':raw,'mark_known_minute':t,'band':r['capacity_band'],'side':'LONG','margin':False,'intent_issued':False}
    peak=max(peak,len(positions));assert len(positions)<=n and q%100==0
    # Execution/teacher suffix is consulted only after quantity/cash funding is fixed.
    book=books[key]
    positions[key]['mark_updates']=sorted([(row['minute']+1,D(row['C'])) for row in book['market']
     if row.get('session')==day and row['minute']>=t and valid_market(row)])
    positions[key]['mark_index']=0
    if not book['capture_complete'] or not book.get('entry_actual_source'):
     blockers.append({'entry_id':key,'minute':t,'reason':'MTM_SOURCE_LINEAGE_BLOCKED'})
    plan=exit_plans[key]
    positions[key]['exit_plan']=plan
    positions[key]['overlay_pending']=False
    prior=plan.get('source')
    if prior:
     assert prior['release_minute']>t
     fills[prior['release_minute']].append((key,prior))
  if t==920:
   for key,p in sorted(positions.items()):
    if p.get('overlay_pending'):continue
    it=eod_intent(p);assert it is not None;p['intent_issued']=True
    it.update(entry_id=key,session=day,limit_up_status='LIMIT_UP_CONFIRMED' if limit_up_confirmed(books[key]['limit_up_authority'],day,t) else 'LIMIT_UP_UNKNOWN')
    intents.append(it);source=eod_source(books[key]['market'],day)
    if source:fills[source['release_minute']].append((key,source))
    else:blockers.append({'entry_id':key,'minute':931,'reason':'LIMIT_UP_EOD_UNEXECUTED_FAIL_CLOSED' if it['limit_up_status']=='LIMIT_UP_CONFIRMED' else 'EOD_UNEXECUTED_FAIL_CLOSED'})
  eq=equity();assert cash>=0 and eq>0
  if any(b['reason']=='MTM_SOURCE_LINEAGE_BLOCKED' for b in blockers):break
  frames.append({'session':day,'minute':t,'equity':str(eq),'cash':str(cash),'exposure':str(eq-cash),
   'utilization':float((eq-cash)/eq),'concurrent':len(positions),'primary_chain':primary_chain,
   'known_marks':{k:p['mark_known_minute'] for k,p in positions.items()}})
 if positions:
  known={b['entry_id'] for b in blockers}
  for key in positions:
   if key not in known:blockers.append({'entry_id':key,'minute':931,'reason':'EOD_UNEXECUTED_FAIL_CLOSED'})
 snapshot={'window_arm_event_cursor':{'session':day,'minute':t},'cash':str(cash),'holdings':{k:{f:str(v) if isinstance(v,D) else v for f,v in p.items() if f not in ('mark_updates','exit_plan')} for k,p in positions.items()},'pending_SELL':{k:p['exit_plan'] for k,p in positions.items()},'remaining_fill_schedule':{str(tm):ss for tm,ss in fills.items()}}
 valid=not blockers and not positions
 return {'session':day,'status':'COMPLETE' if valid else 'PORTFOLIO_MEASUREMENT_BLOCKED_EXECUTION',
  'starting_cash':str(starting_cash),'ending_cash':str(cash) if valid else None,
  'daily_return':float(cash/D(str(starting_cash))-1) if valid and primary_chain else None,
  'diagnostic_daily_return':float(cash/D(str(starting_cash))-1) if valid else None,
  'primary_chain':primary_chain,'blockers':blockers,'open_obligations':list(positions),'resume_snapshot':snapshot,
  'cash_min':str(cash_min),'max_concurrent':peak,'recycled_cash_used':str(recycled_used)},decisions,trades,frames,intents
