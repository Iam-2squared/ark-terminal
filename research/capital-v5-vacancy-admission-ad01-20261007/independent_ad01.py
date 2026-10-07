"""AD01 same-author separate scalar implementation. Stdlib only; no primary allocator, Admission, replay or evaluator imports. Shared original saved State outputs; no third-party blind audit claim."""
from pathlib import Path
from decimal import Decimal,ROUND_FLOOR,localcontext
from fractions import Fraction
import json,gzip,hashlib,zipfile,collections,re,math,csv,argparse,sys
from statistics import median

R=Path(__file__).resolve().parent;D=Decimal;F=Fraction
def read(p):return json.loads(Path(p).read_bytes())
def rows(p):return [json.loads(x) for x in gzip.decompress(Path(p).read_bytes()).splitlines() if x]
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)+'\n');t.replace(p)
def gzsave(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress((''.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n' for r in x)).encode(),mtime=0))
def clock(s):return int(s[11:13])*60+int(s[14:16])
def stamp(day,t):return day+'T%02d:%02d:00+09:00'%divmod(t,60)
def valid(r,auction=False):
 try:
  if not r.get('lineage'):return False
  o,h,l,c,vo,va=[D(str(r[k])) for k in ['O','H','L','C','Vo','Va']]
  return all(x.is_finite() and x>0 for x in [o,h,l,c,vo,va]) and l<=min(o,c)<=max(o,c)<=h and (not auction or o==h==l==c)
 except Exception:return False
def rawvalid(r):
 try:
  token=re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z')
  if any(isinstance(r[k],bool) or not token.fullmatch(str(r[k])) for k in ['minute','O','H','L','C','Vo','Va']):return False
  a=[D(str(r[k])) for k in ['minute','O','H','L','C','Vo','Va']]
  return a[0]==a[0].to_integral_value() and all(math.isfinite(float(x)) for x in a) and a[3]>0 and a[3]<=min(a[1],a[4])<=max(a[1],a[4])<=a[2] and a[5]>=0 and a[6]>=0
 except Exception:return False
def csource(b):
 x=b['frozen_exit']
 if x['sell_status']=='FILLED' and clock(x['sell_source_assumed_available_at'])<=920:
  av=clock(x['sell_source_assumed_available_at']);r=next((r for r in b['market'] if r['minute']==x['sell_minute']),None)
  if r is None or not valid(r):return {'blocked':'FROZEN_EXIT_SOURCE_LINEAGE_BLOCKED','release_minute':av}
  px=D(str(r['O'] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else r['C']))*D('.9995')
  assert px==D(x['sell_price_decimal'])
  return {'kind':'FROZEN_EXIT_V3','source_minute':x['sell_minute'],'release_minute':av,'price':str(px),'lineage':r['lineage']}
 return None
def eod(b):
 rr=sorted([r for r in b['market'] if r.get('session')==b['session'] and 920<=r['minute']<925 and valid(r)],key=lambda r:r['minute']);au=[r for r in b['market'] if r.get('session')==b['session'] and r['minute']==930 and valid(r,True)]
 if not rr and not au:return None
 r=rr[0] if rr else au[0]
 return {'kind':'EOD_REGULAR' if rr else 'EOD_EXACT_1530_AUCTION','source_minute':r['minute'],'release_minute':r['minute']+1,'price':str(D(str(r['O'] if rr else r['C']))*D('.9995')),'lineage':r['lineage']}

def order(r):return (-r['ML'],-r['m5'],-r['m3'],-r['m2'],r['entry_timestamp'],r['symbol'])
def classify(score):
 if score is None or not math.isfinite(score) or score<1:return None
 return 'S' if score>=2 else 'A' if score>=1.5 else 'B'
def allot(selected,equity,exposure,cash,held):
 caps={'S':D('.45'),'A':D('.35'),'B':D('.25')};base={'S':D('.68'),'A':D('.56'),'B':D('.44')}
 bands=held+[classify(r['capital_score']) for r in selected];best=min(bands,key=lambda b:['S','A','B'].index(b));target=min(D('.92'),base[best]+D('.055')*(len(bands)-1));budget=min(cash,max(D(0),equity*target-exposure));weight=sum(D(str(r['capital_score'])) for r in selected);remaining=cash;unspent=budget;ans=[]
 for r in selected:
  ba=classify(r['capital_score']);lot=D(r['raw_reference'])*D('1.0005')*100;cap=equity*caps[ba];desired=budget*D(str(r['capital_score']))/weight;lots=max(0,int((min(desired,cap,remaining)/lot).to_integral_value(rounding=ROUND_FLOOR)));debit=lots*lot;remaining-=debit;unspent-=debit
  ans.append({'entry_id':r['entry_id'],'quantity':lots*100,'first_pass_quantity':lots*100,'water_fill_lots':0,'debit':debit,'lot_debit':lot,'equity_cap':cap,'liquidity_cap':None,'desired':desired,'band':ba,'target_utilization':target,'batch_equity':equity,'batch_budget':budget})
 rounds=0
 while True:
  any_change=False
  for a in ans:
   if a['first_pass_quantity'] and a['lot_debit']<=remaining and a['lot_debit']<=unspent and a['debit']+a['lot_debit']<=a['equity_cap']:
    a['quantity']+=100;a['water_fill_lots']+=1;a['debit']+=a['lot_debit'];remaining-=a['lot_debit'];unspent-=a['lot_debit'];any_change=True
  if not any_change:break
  rounds+=1
 for a in ans:a.update(water_fill_rounds=rounds,budget_unspent=unspent)
 return ans

def rb(pnl,debit):
 v=F(str(pnl))/F(str(debit))*100
 if v<=-5:return 'L5_PLUS'
 for k,b in [(-4,'L4_5'),(-3,'L3_4'),(-2,'L2_3'),(-1,'L1_2')]:
  if v<=k:return b
 if v<0:return 'L0_1'
 if v==0:return 'ZERO'
 if v<1:return 'P0_1'
 for k,b in [(2,'P1_2'),(3,'P2_3'),(4,'P3_4'),(5,'P4_5')]:
  if v<k:return b
 return 'P5_PLUS'
def retpct(pnl,debit):
 return F(str(pnl))/F(str(debit))*100
def fractionstr(v):
 with localcontext() as c:c.prec=80;return str(D(v.numerator)/D(v.denominator))
def maxdd(values):
 peak=F(1000000);answer=F(0)
 for value in values:
  v=F(str(value));peak=max(peak,v);answer=max(answer,(peak-v)/peak)
 return answer*100

checks=0
mismatch_N=0
mismatches=[]
seen_state_rows=0
MONEY_FIELDS={'equity','cash','exposure','buy_effective','sell_effective','debit','credit','pnl','cash_before','lot_debit','equity_cap','desired','target_utilization','batch_equity','batch_budget','budget_unspent','recycled_cash_used','starting_cash','ending_cash','cash_min','price'}

def verify(name,independent,primary,money=False):
 global checks,mismatch_N
 checks+=1
 try:
  equal=(D(str(independent))==D(str(primary))) if money and independent is not None and primary is not None else independent==primary
 except (ValueError,TypeError,ArithmeticError):equal=False
 if not equal:
  mismatch_N+=1
  if len(mismatches)<100:mismatches.append({'check':name,'independent':independent,'primary':primary})
 return equal

def native_gate(row,occupancy,minute,table):
 """Independent restatement of immutable V5 source, using only past inputs."""
 assert occupancy in (0,1,2,3) and row['ML']>=1
 counts=table['minute_counts'][str(minute)];n=table['training_session_N']
 probability=counts[0]/n;expected=counts[2]/n
 audit={'pre_decision_occupancy':occupancy,'training_B_median':table['B_median'],'training_B_p75':table['B_p75'],'remaining_Aplus_probability':probability,'remaining_Aplus_ge2_probability':counts[1]/n,'expected_remaining_Aplus':expected,'arrival_bucket':table['minute_bucket'][str(minute)],'training_block':row['block']}
 if occupancy==3:return False,'MAX_POSITION_CAP',audit
 if occupancy==0:return True,'SLOT1_NO_RESERVE',audit
 if row['rank'] in ('S','A'):return True,'SA_ALWAYS_ADMIT',audit
 assert row['rank']=='B'
 if occupancy==1:
  allowed=minute>=840 or row['ML']>=table['B_median'] and probability<.50
  reason='SLOT2_B_LATE_RELEASE' if minute>=840 else 'SLOT2_B_QUALITY_AND_ARRIVAL_PASS' if allowed else 'SLOT2_RESERVE_FOR_FUTURE_QUALITY'
 else:
  allowed=row['ML']>=table['B_p75'] and (minute>=870 or probability<.35 and expected<.75)
  reason='SLOT3_B_LATE_RELEASE' if allowed and minute>=870 else 'SLOT3_B_QUALITY_AND_ARRIVAL_PASS' if allowed else 'SLOT3_RESERVE_FOR_FUTURE_QUALITY'
 return allowed,reason,audit

def quality_guard(policy,rank,sd_release_seen):
 active=policy=='H1' or policy=='H2' and sd_release_seen
 return (not active or rank in ('S','A')),active

def positive_price(value):
 try:
  return not isinstance(value,bool) and re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?',str(value)) is not None and D(str(value)).is_finite() and D(str(value))>0
 except (ArithmeticError,ValueError,TypeError):return False

def compile_shared_states(stream,books,cache,root):
 """Read the original saved State trace again; never rerun its State kernel."""
 global seen_state_rows
 binding=read(root/'inputs/STATE9_TRACE_ARCHIVE_BINDING.json')
 archive=root/'inputs/sharp_archive/Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip'
 out={};states=('RISE_STOP','RISE','SHARP_RISE','PULLBACK','RANGE','REBOUND','SHARP_DROP','DROP','DROP_STOP')
 with zipfile.ZipFile(archive) as z:
  for r in stream:
   key=r['entry_id'];book=books[key];native=book['frozen_exit']['exit_intent'];control=min(native['minute'],920) if native else 920;buy=r['entry_minute'];member=binding['trace_members'][key];body=z.read(member);pin=binding['manifest']['components'][member]
   verify('State_member_bytes:'+key,len(body),pin['bytes'])
   verify('State_member_hash:'+key,hashlib.sha256(body).hexdigest(),pin['sha256'])
   saved={f['checkpoint_minute']:f for f in cache[key]['frames']};selected=None;last=None
   for line in gzip.decompress(body).splitlines(keepends=True):
    q=json.loads(line);t=q['bar_end_minute']
    if t>control:break
    if t<=buy:continue
    seen_state_rows+=1;s=q['state'];p=q['path'];at=s['as_of'];token=q['input']
    timing=(q['watch_key']==s['case_id']==p['case_id']==key and at==t-540 and p['scheduled_t']==at and q['assumed_available_at']==stamp(r['session'],t) and p['bar_end']==q['assumed_available_at'] and (token is None or token['known_at']<=at and token['t']<=at))
    usable=bool(timing and s['current_semantics_observed'] is True and p['current_semantics_observed'] is True and s['observed_at']==s['as_of'] and p['quality']['numeric_status']=='ACCEPTED' and p['Primary_or_null'] in states and q['source_status']=='RAW_CLOSED_AT_ASSUMED_BAR_END' and s['activity']!='CARRIED_GAP' and s['basis']!='CARRIED_GAP')
    gap=not timing or p['Primary_or_null'] is not None and p['Primary_or_null'] not in states or last is not None and t<=last
    last=t
    assert t in saved,('STATE_FRAME_MISSING',key,t)
    verify('State_usability:'+key+':'+str(t),usable,saved[t]['usable'])
    verify('State_Primary:'+key+':'+str(t),p['Primary_or_null'] if usable else None,saved[t]['Primary'])
    verify('State_gap:'+key+':'+str(t),gap,saved[t]['evidence_gap'])
    verify('State_line_hash:'+key+':'+str(t),hashlib.sha256(line).hexdigest(),saved[t]['source_line_sha256'])
    if selected is None and t<control:
     if gap:selected={'action':'EVIDENCE_GAP','block_minute':t,'reason':'EVIDENCE_GAP_BEFORE_CONTROL','source':None}
     elif usable and p['Primary_or_null']=='SHARP_DROP':selected={'action':'SD_FIRST','intent_minute':t}
   if selected is None:selected={'action':'DELEGATE_CONTROL','intent_minute':control,'source':csource(book)}
   elif selected['action']=='SD_FIRST':
    terminal_source=csource(book) or eod(book)
    terminal=terminal_source.get('source_minute') if terminal_source and terminal_source.get('price') else 930
    market=[q for q in book['market'] if q.get('session')==book['session'] and q['minute']<=terminal]
    mixed={540,750,min((q['minute'] for q in market if q['minute']<690),default=None),min((q['minute'] for q in market if 750<=q['minute']<925),default=None)}
    regular=[q for q in market if rawvalid(q) and (540<=q['minute']<690 or 750<=q['minute']<925) and q['minute'] not in mixed and q['minute']>=selected['intent_minute'] and q['minute']>buy]
    close=[q for q in market if q['minute']==930 and rawvalid(q)]
    source=min(regular,key=lambda q:q['minute']) if regular else close[0] if len(close)==1 else None
    if source and source['session']==book['session'] and valid(source,not regular):
     # Fraction price arithmetic reflects the frozen SD adapter's exact ingress.
     effective=F(str(source['O'] if regular else source['C']))*F('0.9995')
     with localcontext() as context:context.prec=60;price=str(D(effective.numerator)/D(effective.denominator))
     selected['source']={'kind':'SHARP_DROP_FIRST_OBSERVED_EXIT_V0','source_minute':source['minute'],'release_minute':source['minute']+1,'price':price,'lineage':source['lineage']}
    else:selected['source']=None
   out[key]=selected
 return out

def reconstruct(day,candidates,books,tables,starting_cash,policy,plans):
 """Own scalar event loop: confirmed cash release, intents, admission, sizing."""
 assert policy in ('E0','H1','H2')
 cash=D(str(starting_cash));held={};schedule=collections.defaultdict(list);events=collections.defaultdict(list)
 for row in candidates:events[row['entry_minute']].append(row)
 decisions=[];trades=[];curves=[];intents=[];blockers=[];peakN=0;cashmin=cash;origin=cash;recycled=D(0);reused=D(0)
 sd_seen=False;first_sd_release=None;sd_release_count=0;state_events=[]
 def equity():return cash+sum((position['quantity']*position['mark'] for position in held.values()),D(0))
 for minute in range(540,932):
  for position in held.values():
   while position['index']<len(position['updates']) and position['updates'][position['index']][0]<=minute:
    known,price=position['updates'][position['index']];position['mark']=price;position['known']=known;position['index']+=1
  for key,source in sorted(schedule.pop(minute,[]),key=lambda pair:pair[0]):
   assert key in held,('DUPLICATE_SELL_OR_RELEASE',key,minute)
   if source.get('blocked'):blockers.append({'entry_id':key,'minute':minute,'reason':source['blocked']});continue
   if policy!='E0' and not positive_price(source.get('price')):blockers.append({'entry_id':key,'minute':minute,'reason':'FILL_PRICE_INVALID_FAIL_CLOSED'});continue
   position=held.pop(key);credit=position['quantity']*D(source['price']);debit=position['quantity']*position['buy'];cash+=credit;recycled+=credit
   if source['kind']=='SHARP_DROP_FIRST_OBSERVED_EXIT_V0':
    assert position['plan']['action']=='SD_FIRST' and position['latched'],'SD_RELEASE_WITHOUT_OWN_LATCHED_INTENT'
    sd_seen=True;sd_release_count+=1
    if first_sd_release is None:first_sd_release=stamp(day,minute)
    state_events.append({'entry_id':key,'session':day,'minute':minute,'event':'SD_FULL_FILL_CASH_AND_SLOT_RELEASE_CONFIRMED','full_quantity':position['quantity'],'cash_credit':str(credit),'count_today':sd_release_count})
   trades.append({'entry_id':key,'session':day,'quantity':position['quantity'],'entry_minute':position['entry_minute'],'release_minute':minute,'source_minute':source['source_minute'],'exit_kind':source['kind'],'buy_effective':str(position['buy']),'sell_effective':source['price'],'debit':str(debit),'credit':str(credit),'pnl':str(credit-debit),'net_return':float(credit/debit-1),'lineage':source['lineage'],'commission':0})
  for key,position in sorted(held.items()):
   plan=position['plan']
   if plan['action']=='EVIDENCE_GAP' and minute==plan['block_minute']:blockers.append({'entry_id':key,'minute':minute,'reason':plan['reason']})
   if plan['action']=='SD_FIRST' and minute==plan['intent_minute']:
    position['latched']=True;intents.append({'entry_id':key,'session':day,'minute':minute,'side':'SELL','quantity':position['quantity'],'reason':'SHARP_DROP_FIRST_OBSERVED','transmitted':False,'latched':True})
  if any(item['reason']=='EVIDENCE_GAP_BEFORE_CONTROL' and item['minute']==minute for item in blockers):break
  eligible=[]
  for row in sorted(events.get(minute,[]),key=order):
   decision={name:row[name] for name in ['entry_id','session','capital_score','capacity_band','rank','admission','ML','m2','m3','m5']}
   decision.update(minute=minute,quantity=0,reason=None,held_before_batch=sorted(held),profile='CAPITAL_MAX3_SLOT_RESERVE_V1',primary_chain=True)
   decision.update(independent_policy=policy)
   if policy!='E0':decision.update(admission_policy=policy,native_eligibility=False,native_eligibility_reason=None,native_gate_action='NOT_EVALUATED',native_gate_reason=None,overlay_gate_action='NOT_EVALUATED',overlay_gate_reason=None,funding_action='NOT_EVALUATED',sd_full_release_seen_today=sd_seen,first_sd_release_known_at=first_sd_release,sd_full_release_count_today=sd_release_count)
   decisions.append(decision)
   if minute>=920:decision['reason']='CAPITAL_EOD_ENTRY_CUTOFF'
   elif not row['admission']:decision['reason']='UPWARD_BELOW_BASELINE'
   elif classify(row['capital_score']) is None:decision['reason']='SCORE_INPUT_UNKNOWN'
   elif any(position['symbol']==row['symbol'] for position in held.values()):decision['reason']='SYMBOL_ALREADY_OPEN'
   elif policy!='E0' and not positive_price(row.get('raw_reference')):decision['reason']='ENTRY_PRICE_INVALID_FAIL_CLOSED';blockers.append({'entry_id':row['entry_id'],'minute':minute,'reason':decision['reason']})
   else:eligible.append((row,decision))
   if policy!='E0':
    if decision['reason']:decision['native_eligibility_reason']=decision['reason']
    else:decision.update(native_eligibility=True,native_eligibility_reason='ELIGIBLE')
  picked=[]
  for row,decision in eligible:
   if policy!='E0' and any(other['symbol']==row['symbol'] for other,d in picked):decision.update(native_eligibility=False,native_eligibility_reason='SYMBOL_ALREADY_PENDING',reason='SYMBOL_ALREADY_PENDING');continue
   occupancy=len(held)+len(picked);native_ok,why,audit=native_gate(row,occupancy,minute,tables[str(row['block'])])
   decision.update(audit,slot_gate_reason=why,slot_gate_action='ADMIT' if native_ok else 'REJECT',independent_native_gate_pass=native_ok)
   if policy!='E0':decision.update(native_gate_action='ADMIT' if native_ok else 'REJECT',native_gate_reason=why)
   if not native_ok:
    decision['reason']='SLOT_RESERVE_REJECT' if why.startswith(('SLOT2_RESERVE','SLOT3_RESERVE')) else why
    continue
   allowed,guard=quality_guard(policy,row['rank'],sd_seen)
   decision.update(independent_overlay_guard_active=guard,independent_overlay_allowed=allowed)
   if policy!='E0':decision.update(overlay_gate_action='ADMIT' if allowed else 'REJECT',overlay_gate_reason='SA_QUALITY_FLOOR_PASS' if guard and allowed else 'ADMISSION_QUALITY_RESERVE' if not allowed else 'QUALITY_FLOOR_INACTIVE')
   if not allowed:
    decision['reason']='ADMISSION_QUALITY_RESERVE'
    continue
   decision['slot_admission_index']=occupancy+1;picked.append((row,decision))
  if picked:
   account_equity=equity();assigned=allot([row for row,decision in picked],account_equity,account_equity-cash,cash,[position['band'] for position in held.values()])
   for (row,decision),assignment in zip(picked,assigned):
    decision.update({key:str(value) if isinstance(value,D) else value for key,value in assignment.items() if key!='entry_id'});decision['cash_before']=str(cash);quantity=assignment['quantity']
    if quantity<100:
     decision['reason']='CASH_OR_LOT_CONSTRAINED'
     if policy!='E0':decision['funding_action']='REJECT_CASH_OR_LOT'
     continue
    buy=D(row['raw_reference'])*D('1.0005');debit=buy*quantity
    assert debit==assignment['debit'] and debit<=cash
    cash-=debit;cashmin=min(cashmin,cash);used=min(origin,debit);origin-=used;reuse=debit-used;recycled-=reuse;reused+=reuse
    assert recycled>=0 and cash>=0 and quantity%100==0
    decision.update(reason='FUNDED',debit=str(debit),recycled_cash_used=str(reuse),funded_slot=len(held)+1)
    if policy!='E0':decision['funding_action']='FUNDED'
    key=row['entry_id'];book=books[key]
    position={'quantity':quantity,'buy':buy,'mark':D(row['raw_reference']),'known':minute,'symbol':row['symbol'],'entry_minute':minute,'band':row['capacity_band'],'index':0,'updates':sorted([(source['minute']+1,D(source['C'])) for source in book['market'] if source.get('session')==day and source['minute']>=minute and valid(source)]),'latched':False,'plan':plans[key]}
    held[key]=position;peakN=max(peakN,len(held));assert len(held)<=3
    if not book['capture_complete'] or not book.get('entry_actual_source'):blockers.append({'entry_id':key,'minute':minute,'reason':'MTM_SOURCE_LINEAGE_BLOCKED'})
    source=plans[key].get('source')
    if source:
     assert source['release_minute']>minute
     schedule[source['release_minute']].append((key,source))
  if minute==920:
   for key,position in sorted(held.items()):
    if position['latched']:continue
    authority=books[key]['limit_up_authority'];limited=bool(authority and authority.get('status')=='LIMIT_UP_CONFIRMED' and authority.get('authoritative_price_limit_source') and authority.get('causal_exchange_status') and authority.get('session')==day and authority.get('known_minute',9999)<=minute and authority.get('observed_minute',9999)<=minute)
    intent={'minute':920,'side':'SELL','quantity':position['quantity'],'sor':True,'order_type':'MARKET','condition':'DAY','transmitted':False,'entry_id':key,'session':day,'limit_up_status':'LIMIT_UP_CONFIRMED' if limited else 'LIMIT_UP_UNKNOWN'};intents.append(intent);source=eod(books[key])
    if source:schedule[source['release_minute']].append((key,source))
    else:blockers.append({'entry_id':key,'minute':931,'reason':'LIMIT_UP_EOD_UNEXECUTED_FAIL_CLOSED' if limited else 'EOD_UNEXECUTED_FAIL_CLOSED'})
  if any(item['reason']=='MTM_SOURCE_LINEAGE_BLOCKED' for item in blockers):break
  eq=equity();assert cash>=0 and eq>0
  curves.append({'session':day,'minute':minute,'equity':str(eq),'cash':str(cash),'exposure':str(eq-cash),'concurrent':len(held),'known_marks':{key:position['known'] for key,position in held.items()},'utilization':float((eq-cash)/eq),'primary_chain':True})
 if held:
  prior={item['entry_id'] for item in blockers}
  for key in held:
   if key not in prior:blockers.append({'entry_id':key,'minute':931,'reason':'EOD_UNEXECUTED_FAIL_CLOSED'})
 complete=not held and not blockers
 daily={'session':day,'status':'COMPLETE' if complete else 'PORTFOLIO_MEASUREMENT_BLOCKED_EXECUTION','starting_cash':str(starting_cash),'ending_cash':str(cash) if complete else None,'daily_return':float(cash/D(str(starting_cash))-1) if complete else None,'diagnostic_daily_return':float(cash/D(str(starting_cash))-1) if complete else None,'primary_chain':True,'blockers':blockers,'open_obligations':list(held),'cash_min':str(cashmin),'max_concurrent':peakN,'recycled_cash_used':str(reused)}
 if policy!='E0':daily.update(admission_policy=policy,sd_full_release_seen_today=sd_seen,first_sd_release_known_at=first_sd_release,sd_full_release_count_today=sd_release_count,admission_state_events=state_events)
 if complete:
  snapshot={'window_arm_event_cursor':{'session':day,'minute':minute},'cash':str(cash),'holdings':{},'pending_SELL':{},'remaining_fill_schedule':{}}
  if policy!='E0':snapshot.update(admission_policy=policy,sd_full_release_seen_today=sd_seen,first_sd_release_known_at=first_sd_release,sd_full_release_count_today=sd_release_count)
  daily['resume_snapshot']=snapshot
 return daily,decisions,trades,curves,intents

def compare_records(tag,own,actual,fields=None):
 verify(tag+':length',len(own),len(actual))
 for index,(independent,primary) in enumerate(zip(own,actual)):
  keys=fields or list(independent)
  for key in keys:verify(tag+':'+str(index)+':'+key,independent.get(key),primary.get(key),key in MONEY_FIELDS)

def path_inputs(root):
 required=[root/'inputs'/name for name in ('candidate_stream','books','arrival','split')]+[root/'private/immutable/STATE_PREFIX_CACHE.jsonl.gz',root/'private/immutable/EXIT_PLANS.jsonl.gz',root/'inputs/STATE9_TRACE_ARCHIVE_BINDING.json',root/'inputs/sharp_archive/Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip']
 missing=[str(path) for path in required if not path.is_file()]
 windows=['W%02d'%n for n in range(13,22)]+['CHAIN38']
 for window in windows:
  for policy in ('E0','H1','H2'):
   source=root/'baseline/private/runs'/window/'E' if policy=='E0' else root/'private/runs'/window/policy
   for name in ('RESULT.json','DECISIONS.jsonl.gz','TRADES.jsonl.gz','CURVE.jsonl.gz','INTENTS.jsonl.gz'):
    if not (source/name).is_file():missing.append(str(source/name))
 if missing:return {'status':'BLOCKED_REQUIRED_SOURCE_OR_PRIMARY_PATHS_MISSING','missing_paths':missing,'path_N':0}
 extraction=read(root/'ORIGINAL_EXTRACTION_RECEIPT.json')
 for receipt in extraction['receipts']:
  if receipt['kind']=='archive_lineage':continue
  path=Path(receipt['local_path']);body=path.read_bytes()
  assert len(body)==receipt['bytes'] and hashlib.sha256(body).hexdigest()==receipt['sha256'],('ORIGINAL_INPUT_IDENTITY_CHANGED',str(path))
 for name,pin in [('STATE_PREFIX_CACHE.jsonl.gz',{'bytes':6083274,'sha256':'2fa33310f76cf5a9848af4dcbd9710751c4e408f8d283d04b9a620502fba474b'}),('STATE_PREFIX_LINEAGE.json',{'bytes':427432,'sha256':'c1cac43706ee1c03b4a0624c45933fb50cb3742144ac28b7669a10e14d49fc5c'})]:
  body=(root/'private/immutable'/name).read_bytes();assert len(body)==pin['bytes'] and hashlib.sha256(body).hexdigest()==pin['sha256'],('SAVED_CAUSAL_STATE_IDENTITY_CHANGED',name)
 stream=rows(root/'inputs/candidate_stream');bookrows=rows(root/'inputs/books');books={row['entry_id']:row for row in bookrows};cache={row['entry_id']:row for row in rows(root/'private/immutable/STATE_PREFIX_CACHE.jsonl.gz')};ids={row['entry_id'] for row in stream}
 assert len(stream)==len(ids)==1039 and ids<=books.keys() and ids<=cache.keys(), 'FAIL_CLOSED_SOURCE_POPULATION'
 return {'status':'READY','candidate_N':len(stream),'path_N':30}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=R);parser.add_argument('--run-campaign',action='store_true',help='Explicitly execute the single independent 30-path campaign after primary readiness');args=parser.parse_args();root=args.root.resolve();preflight=path_inputs(root)
 if not args.run_campaign:
  missing=preflight.pop('missing_paths',[])
  print(json.dumps({'mode':'PREFLIGHT_ONLY','campaign_executed':False,**preflight,'missing_path_N':len(missing),'first_missing_paths':missing[:3]},sort_keys=True));return
 assert preflight['status']=='READY',preflight
 destination=root/'private/independent';assert not (destination/'CAMPAIGN_STARTED.json').exists(),'ONE_INDEPENDENT_CAMPAIGN_ONLY_NO_SILENT_RERUN'
 save(destination/'CAMPAIGN_STARTED.json',{'status':'STARTED','maximum_reconstruction_paths':30,'same_author_separate_implementation':True,'third_party_blind_audit':False,'primary_imports':0,'independent_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'original_extraction_receipt_sha256':hashlib.sha256((root/'ORIGINAL_EXTRACTION_RECEIPT.json').read_bytes()).hexdigest()})
 stream=rows(root/'inputs/candidate_stream');books={row['entry_id']:row for row in rows(root/'inputs/books')};tables=read(root/'inputs/arrival');split=read(root/'inputs/split');cache={row['entry_id']:row for row in rows(root/'private/immutable/STATE_PREFIX_CACHE.jsonl.gz')};plans=compile_shared_states(stream,books,cache,root);primaryplans={row['entry_id']:row['plan'] for row in rows(root/'private/immutable/EXIT_PLANS.jsonl.gz')}
 for key,plan in plans.items():
  verify('EXIT_action:'+key,plan['action'],primaryplans[key]['action']);verify('EXIT_intent:'+key,plan.get('intent_minute'),primaryplans[key].get('intent_minute'))
  verify('EXIT_gap_block_minute:'+key,plan.get('block_minute'),primaryplans[key].get('block_minute'))
  if plan['action']=='EVIDENCE_GAP':verify('EXIT_gap_reason:'+key,plan.get('reason'),primaryplans[key].get('reason'))
  for field in ('source_minute','release_minute','kind','price','lineage','blocked'):verify('EXIT_source:'+key+':'+field,(plan.get('source') or {}).get(field),(primaryplans[key].get('source') or {}).get(field),field=='price')
 assert mismatch_N==0,('STATE_OR_EXIT_CONTRACT_MISMATCH',mismatches[:3])
 completed=[]
 for window in ['W%02d'%n for n in range(13,22)]+['CHAIN38']:
  sessions=read(root/'baseline/private/runs'/window/'E/RESULT.json')['planned_sessions'] if window!='CHAIN38' else split['OOF38']
  assert len(sessions)==(38 if window=='CHAIN38' else 20)
  for policy in ('E0','H1','H2'):
   primaryroot=root/'baseline/private/runs'/window/'E' if policy=='E0' else root/'private/runs'/window/policy
   dest=destination/window/policy;cash=D(1000000);daily=[];all_decisions=[];all_trades=[];all_curves=[];all_intents=[]
   for day in sessions:
    d,ds,ts,cs,it=reconstruct(day,[row for row in stream if row['session']==day],books,tables,cash,policy,plans);daily.append(d);all_decisions.extend(ds);all_trades.extend(ts);all_curves.extend(cs);all_intents.extend(it)
    if d['status']!='COMPLETE':break
    cash=D(d['ending_cash'])
   for label,ledger in [('DECISIONS',all_decisions),('TRADES',all_trades),('CURVE',all_curves),('INTENTS',all_intents)]:
    gzsave(dest/(label+'.jsonl.gz'),ledger);actual=rows(primaryroot/(label+'.jsonl.gz'))
    # Native economics/event fields are exhaustive. Independent metadata is not a primary field.
    fields=sorted({field for record in ledger for field in record if not field.startswith('independent_')})
    compare_records(window+':'+policy+':'+label,ledger,actual,fields)
   primary=read(primaryroot/'RESULT.json');compare_records(window+':'+policy+':DAILY',daily,primary['daily_series'])
   complete=len(daily)==len(sessions) and all(day['status']=='COMPLETE' for day in daily);final=str(cash) if complete else None
   verify(window+':'+policy+':FINAL',final,primary['final_equity'],True)
   funded=sum(row['reason']=='FUNDED' for row in all_decisions);verify(window+':'+policy+':FUNDED',funded,primary['funded_N']);verify(window+':'+policy+':CLOSED',len(all_trades),primary['closed_N'])
   metrics={'gross_loss_jpy':str(-sum((D(trade['pnl']) for trade in all_trades if D(trade['pnl'])<0),D(0))),'gross_positive_jpy':str(sum((D(trade['pnl']) for trade in all_trades if D(trade['pnl'])>0),D(0))),'minute_MTM_MaxDD_pct':fractionstr(maxdd([D(frame['equity']) for frame in all_curves])),'EOD_MaxDD_pct':fractionstr(maxdd([D(day['ending_cash']) for day in daily if day['status']=='COMPLETE'])),'negative_day_N':sum(D(day['ending_cash'])<D(day['starting_cash']) for day in daily if day['status']=='COMPLETE'),'R_bands':dict(collections.Counter(rb(trade['pnl'],trade['debit']) for trade in all_trades))}
   summary={'window_id':window,'arm':policy,'status':'COMPLETE' if complete else 'BLOCKED','final_equity':final,'funded_N':funded,'closed_N':len(all_trades),**metrics,'daily_series':daily};save(dest/'RESULT.json',summary);completed.append({key:value for key,value in summary.items() if key!='daily_series'})
   print(json.dumps({'independent_window':window,'arm':policy,'final':final,'mismatch_N':mismatch_N}),flush=True)
 out={'status':'PASS' if mismatch_N==0 and len(completed)==30 and all(path['status']=='COMPLETE' for path in completed) else 'FAIL','same_author_separate_implementation':True,'third_party_blind_audit':False,'primary_allocator_Admission_replay_evaluator_imports':0,'State_kernel':'SHARED_PREEXISTING_SAVED_KERNEL_OUTPUT; independent original trace prefix read and usability/trigger/fill reconstruction; no kernel certification','original_trace_rows_verified':seen_state_rows,'scalar_check_N':checks,'mismatch_N':mismatch_N,'mismatches_first100':mismatches,'path_N':len(completed),'paths':completed,'money_quantity_ID_time':'EXACT_NUMERIC_VALUES; lexical Decimal scale is not a numeric tolerance','new_fits':0,'new_inference':0,'new_rank':0,'State_kernel_run_N':0,'report_metrics_verification':'NOT_YET_RUN; independently computed but final report tables require separate comparison from saved independent ledgers'}
 save(root/'public/INDEPENDENT_AUDIT.json',out);save(destination/'INDEPENDENT_COMPLETE.json',out)
 if mismatch_N:raise AssertionError(('INDEPENDENT_MISMATCH',mismatches[:3]))

if __name__=='__main__':main()
