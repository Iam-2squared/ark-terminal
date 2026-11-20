"""AD01: native V5 gate first, fixed rank guard second, unchanged funding/EXIT.

Book and compiled EXIT-plan access happens only after funding is fixed.
E0 dispatches the byte-identical repaired predecessor. Checkpoint state is an
execution-only carrier; it is never passed to admission_guard.
"""
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
SD_EXIT='SHARP_DROP_FIRST_OBSERVED_EXIT_V0'
POLICIES={'E0','H1','H2'}

def admission_guard(policy,rank,sd_full_release_seen_today):
 assert policy in POLICIES
 assert isinstance(sd_full_release_seen_today,bool)
 active=policy=='H1' or (policy=='H2' and sd_full_release_seen_today)
 return not active or rank in ('S','A')

def _jsonable(value):
 if isinstance(value,D):return str(value)
 if isinstance(value,dict):return {str(k):_jsonable(v) for k,v in value.items()}
 if isinstance(value,(list,tuple)):return [_jsonable(v) for v in value]
 return value

def _positive_price(value):
 try:
  import re
  if isinstance(value,bool) or not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?',str(value)):return False
  price=D(str(value))
  return price.is_finite() and price>0
 except Exception:return False


def _safe_valid_market(row):
 """Schema boundary around unchanged native validation, never an Admission input."""
 try:return valid_market(row)
 except (ArithmeticError,ValueError,TypeError,KeyError):return False


def day_replay(n,day,candidates,books,starting_cash,primary_chain=True,profile=PROFILE,tables=None,exit_plans=None,policy='E0',stop_after_minute=None,resume_checkpoint=None,checkpoint_binding=None):
 assert policy in POLICIES,'UNKNOWN_AD01_POLICY'
 if policy=='E0':
  assert stop_after_minute is None and resume_checkpoint is None,'E0_CHECKPOINT_USES_PREDECESSOR_SESSION_BOUNDARY'
  from baseline_adapter import day_replay as baseline_day_replay
  return baseline_day_replay(n,day,candidates,books,starting_cash,primary_chain,profile,tables,exit_plans)
 assert exit_plans is not None,'AD01_REQUIRES_FROZEN_SHARP_DROP_EXIT_PLANS'

 assert n==3,'MAX3_ONLY_RESEARCH_POLICY'
 cash=D(str(starting_cash));positions={};fills=defaultdict(list);events=defaultdict(list)
 for r in candidates:events[r['entry_minute']].append(r)
 decisions=[];trades=[];frames=[];intents=[];blockers=[]
 original_pool=cash;recycled_pool=D(0);recycled_used=D(0);peak=0;cash_min=cash
 sd_full_release_seen_today=False;first_sd_release_known_at=None;sd_full_release_count_today=0
 state_events=[];start_minute=540
 binding=checkpoint_binding or {}
 if resume_checkpoint is not None:
  c=resume_checkpoint
  assert c['session']==day and c['policy']==policy and c['starting_cash']==str(starting_cash),'CHECKPOINT_SESSION_POLICY_CASH_MISMATCH'
  assert c['binding']==binding,'CHECKPOINT_BINDING_MISMATCH'
  assert c['next_minute'] in range(540,932),'CHECKPOINT_CURSOR_INVALID'
  cash=D(c['cash']);original_pool=D(c['original_pool']);recycled_pool=D(c['recycled_pool']);recycled_used=D(c['recycled_used']);cash_min=D(c['cash_min']);peak=c['peak']
  positions=c['positions']
  # Work on a fresh decoded copy, never mutate the user's saved carrier.
  positions=json.loads(json.dumps(positions))
  for p in positions.values():
   for f in ('buy','mark'):p[f]=D(p[f])
   p['mark_updates']=[(tm,D(price)) for tm,price in p['mark_updates']]
  fills=defaultdict(list,{int(tm):[(key,source) for key,source in rr] for tm,rr in c['fills'].items()})
  decisions=list(c['decisions']);trades=list(c['trades']);frames=list(c['frames']);intents=list(c['intents']);blockers=list(c['blockers'])
  sd_full_release_seen_today=c['sd_full_release_seen_today'];first_sd_release_known_at=c['first_sd_release_known_at'];sd_full_release_count_today=c['sd_full_release_count_today'];state_events=list(c['state_events']);start_minute=c['next_minute']
 def equity():return cash+sum(p['quantity']*p['mark'] for p in positions.values())
 def checkpoint(next_minute):
  return _jsonable({'session':day,'policy':policy,'starting_cash':str(starting_cash),'binding':binding,'next_minute':next_minute,
   'cash':cash,'original_pool':original_pool,'recycled_pool':recycled_pool,'recycled_used':recycled_used,'cash_min':cash_min,'peak':peak,
   'positions':positions,'fills':fills,'decisions':decisions,'trades':trades,'frames':frames,'intents':intents,'blockers':blockers,
   'sd_full_release_seen_today':sd_full_release_seen_today,'first_sd_release_known_at':first_sd_release_known_at,'sd_full_release_count_today':sd_full_release_count_today,'state_events':state_events})
 interrupted=False
 for t in range(start_minute,932):
  for key,p in positions.items():
   assert books[key]['session']==day
   while p['mark_index']<len(p['mark_updates']) and p['mark_updates'][p['mark_index']][0]<=t:
    known,price=p['mark_updates'][p['mark_index']];p['mark']=price;p['mark_known_minute']=known;p['mark_index']+=1
  for key,source in sorted(fills.pop(t,[]),key=lambda x:x[0]):
   assert key in positions,'DUPLICATE_SELL_OR_RELEASE'
   if source.get('blocked'):blockers.append({'entry_id':key,'minute':t,'reason':source['blocked']});continue
   if not _positive_price(source.get('price')):
    blockers.append({'entry_id':key,'minute':t,'reason':'FILL_PRICE_INVALID_FAIL_CLOSED'});continue
   p=positions.pop(key);credit=D(source['price'])*p['quantity'];cash+=credit;recycled_pool+=credit
   # The fact becomes known only after this own-arm full position pop and credit.
   if source['kind']==SD_EXIT:
    assert p['exit_plan']['action']=='SD_FIRST' and p['overlay_pending'] and p['intent_issued'],'SD_RELEASE_WITHOUT_OWN_LATCHED_INTENT'
    sd_full_release_seen_today=True;sd_full_release_count_today+=1
    if first_sd_release_known_at is None:first_sd_release_known_at=stamp(day,t)
    state_events.append({'entry_id':key,'session':day,'minute':t,'event':'SD_FULL_FILL_CASH_AND_SLOT_RELEASE_CONFIRMED','full_quantity':p['quantity'],'cash_credit':str(credit),'count_today':sd_full_release_count_today})
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
   d.update(admission_policy=policy,native_eligibility=False,native_eligibility_reason=None,native_gate_action='NOT_EVALUATED',native_gate_reason=None,
    overlay_gate_action='NOT_EVALUATED',overlay_gate_reason=None,funding_action='NOT_EVALUATED',sd_full_release_seen_today=sd_full_release_seen_today,
    first_sd_release_known_at=first_sd_release_known_at,sd_full_release_count_today=sd_full_release_count_today)
   decisions.append(d)
   if t>=920:d['reason']='CAPITAL_EOD_ENTRY_CUTOFF';d['native_eligibility_reason']=d['reason'];continue
   if not r['admission']:d['reason']='UPWARD_BELOW_BASELINE';d['native_eligibility_reason']=d['reason'];continue
   if band(r['capital_score']) is None:d['reason']='SCORE_INPUT_UNKNOWN';d['native_eligibility_reason']=d['reason'];continue
   if any(p['symbol']==r['symbol'] for p in positions.values()):d['reason']='SYMBOL_ALREADY_OPEN';d['native_eligibility_reason']=d['reason'];continue
   if not _positive_price(r.get('raw_reference')):d['reason']='ENTRY_PRICE_INVALID_FAIL_CLOSED';d['native_eligibility_reason']=d['reason'];blockers.append({'entry_id':r['entry_id'],'minute':t,'reason':d['reason']});continue
   d.update(native_eligibility=True,native_eligibility_reason='ELIGIBLE')
   eligible.append((r,d))
  picked=[]
  for r,d in eligible:
   occupancy=len(positions)+len(picked)
   if any(pr['symbol']==r['symbol'] for pr,pd in picked):
    d.update(native_eligibility=False,native_eligibility_reason='SYMBOL_ALREADY_PENDING',reason='SYMBOL_ALREADY_PENDING');continue
   allowed,why,audit=gate(r,occupancy,t,tables[str(r['block'])])
   d.update(audit,slot_gate_reason=why,slot_gate_action='ADMIT' if allowed else 'REJECT',native_gate_reason=why,native_gate_action='ADMIT' if allowed else 'REJECT')
   if not allowed:
    d['reason']='SLOT_RESERVE_REJECT' if why.startswith(('SLOT2_RESERVE','SLOT3_RESERVE')) else why
    continue
   quality_ok=admission_guard(policy,r['rank'],sd_full_release_seen_today)
   guard_active=policy=='H1' or (policy=='H2' and sd_full_release_seen_today)
   d.update(overlay_gate_action='ADMIT' if quality_ok else 'REJECT',overlay_gate_reason='SA_QUALITY_FLOOR_PASS' if guard_active and quality_ok else 'ADMISSION_QUALITY_RESERVE' if not quality_ok else 'QUALITY_FLOOR_INACTIVE')
   if not quality_ok:d['reason']='ADMISSION_QUALITY_RESERVE';continue
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
     d['reason']='CASH_OR_LOT_CONSTRAINED';d['funding_action']='REJECT_CASH_OR_LOT'
     continue
    debit=q*buy;assert debit==a['debit'] and debit<=cash
    cash-=debit;cash_min=min(cash_min,cash)
    used=min(original_pool,debit);original_pool-=used;recycled=debit-used;recycled_pool-=recycled;recycled_used+=recycled
    assert recycled_pool>=0 and cash>=0
    d.update(quantity=q,reason='FUNDED',funding_action='FUNDED',debit=str(debit),recycled_cash_used=str(recycled),funded_slot=len(positions)+1)
    key=r['entry_id'];raw=D(r['raw_reference'])
    positions[key]={'symbol':r['symbol'],'entry_minute':t,'raw_reference':str(raw),'buy':buy,
     'quantity':q,'mark':raw,'mark_known_minute':t,'band':r['capacity_band'],'side':'LONG','margin':False,'intent_issued':False}
    peak=max(peak,len(positions));assert len(positions)<=n and q%100==0
    # Execution/teacher suffix is consulted only after quantity/cash funding is fixed.
    book=books[key]
    positions[key]['mark_updates']=sorted([(row['minute']+1,D(row['C'])) for row in book['market']
     if row.get('session')==day and row['minute']>=t and _safe_valid_market(row)])
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
    intents.append(it);source=eod_source([row for row in books[key]['market'] if _safe_valid_market(row)],day)
    if source:fills[source['release_minute']].append((key,source))
    else:blockers.append({'entry_id':key,'minute':931,'reason':'LIMIT_UP_EOD_UNEXECUTED_FAIL_CLOSED' if it['limit_up_status']=='LIMIT_UP_CONFIRMED' else 'EOD_UNEXECUTED_FAIL_CLOSED'})
  eq=equity();assert cash>=0 and eq>0
  if any(b['reason']=='MTM_SOURCE_LINEAGE_BLOCKED' for b in blockers):break
  frames.append({'session':day,'minute':t,'equity':str(eq),'cash':str(cash),'exposure':str(eq-cash),
   'utilization':float((eq-cash)/eq),'concurrent':len(positions),'primary_chain':primary_chain,
   'known_marks':{k:p['mark_known_minute'] for k,p in positions.items()}})
  if stop_after_minute is not None and t==stop_after_minute and t<931:
   interrupted=True;break
 if positions and not interrupted:
  known={b['entry_id'] for b in blockers}
  for key in positions:
   if key not in known:blockers.append({'entry_id':key,'minute':931,'reason':'EOD_UNEXECUTED_FAIL_CLOSED'})
 snapshot={'window_arm_event_cursor':{'session':day,'minute':t},'cash':str(cash),'holdings':{k:{f:str(v) if isinstance(v,D) else v for f,v in p.items() if f not in ('mark_updates','exit_plan')} for k,p in positions.items()},'pending_SELL':{k:p['exit_plan'] for k,p in positions.items()},'remaining_fill_schedule':{str(tm):ss for tm,ss in fills.items()}}
 snapshot.update(admission_policy=policy,sd_full_release_seen_today=sd_full_release_seen_today,first_sd_release_known_at=first_sd_release_known_at,sd_full_release_count_today=sd_full_release_count_today)
 valid=not blockers and not positions and not interrupted
 result={'session':day,'status':'COMPLETE' if valid else 'INTERRUPTED' if interrupted else 'PORTFOLIO_MEASUREMENT_BLOCKED_EXECUTION','admission_policy':policy,
  'sd_full_release_seen_today':sd_full_release_seen_today,'first_sd_release_known_at':first_sd_release_known_at,'sd_full_release_count_today':sd_full_release_count_today,'admission_state_events':state_events,
  'starting_cash':str(starting_cash),'ending_cash':str(cash) if valid else None,
  'daily_return':float(cash/D(str(starting_cash))-1) if valid and primary_chain else None,
  'diagnostic_daily_return':float(cash/D(str(starting_cash))-1) if valid else None,
  'primary_chain':primary_chain,'blockers':blockers,'open_obligations':list(positions),'resume_snapshot':snapshot,
  'cash_min':str(cash_min),'max_concurrent':peak,'recycled_cash_used':str(recycled_used)}
 if interrupted:result['checkpoint']=checkpoint(t+1)
 return result,decisions,trades,frames,intents

