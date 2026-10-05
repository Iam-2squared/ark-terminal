"""Independent Fraction portfolio reconstruction; no Primary imports."""
from independent_engine import *
from independent_policy import accept,predicted
def reconstruct_blocked(arm,stream,tables,audit):
 stream=[dict(r,cap_policy=arm) for r in stream]
 books={r['entry_id']:r for r in rows(I/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};primary_d={r['entry_id']:r for r in rows(P/f'{arm}_DECISIONS.jsonl.gz')};primary_t={r['entry_id']:r for r in rows(P/f'{arm}_TRADES.jsonl.gz')};primary_c={(r['session'],r['minute']):r for r in rows(P/f'{arm}_CURVE.jsonl.gz')};primary_result=read(O/f'{arm}_RESULT.json');days=read(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json')['OOF38']
 cash=F(1000000);daily=[];decisions=[];trades=[];frames=[];recycled_total=F(0);allcashmin=cash
 for day in days:
  starting=cash;hold={};pending=defaultdict(list);events=defaultdict(list);original=cash;recycled_pool=F(0);recycled_used=F(0);cashmin=cash;peak=0
  for r in stream:
   if r['session']==day:events[r['entry_minute']].append(r)
  for t in range(540,932):
   for p in hold.values():
    while p['cursor']<len(p['updates']) and p['updates'][p['cursor']][0]<=t:
     known,value=p['updates'][p['cursor']];p['mark']=value;p['known']=known;p['cursor']+=1
   for k,z in sorted(pending.pop(t,[])):
    p=hold.pop(k);credit=z['price']*p['quantity'];debit=p['buy']*p['quantity'];cash+=credit;recycled_pool+=credit
    tr={'entry_id':k,'session':day,'quantity':p['quantity'],'entry_minute':p['entry_minute'],'release_minute':t,'source_minute':z['source'],'exit_kind':z['kind'],'debit':debit,'credit':credit,'pnl':credit-debit};trades.append(tr);saved=primary_t[k]
    for f in ('quantity','entry_minute','release_minute','source_minute','exit_kind'):audit.check(k+'/trade/'+f,tr[f]==saved[f])
    for f in ('debit','credit','pnl'):audit.money(k+'/trade/'+f,tr[f],saved[f])
    audit.money(k+'/SELL',z['price'],saved['sell_effective']);audit.money(k+'/BUY',p['buy'],saved['buy_effective'])
   batch=sorted(events.get(t,[]),key=key);eligible=[];batch_hold=sorted(hold)
   for j,r in enumerate(batch):
    k=r['entry_id'];d={'entry_id':k,'session':day,'minute':t,'pP':r['pP'],'band':r['band'],'rank_units':r['rank_units'],'q2':r['q2'],'q3':r['q3'],'block':r['block'],'r':r['r'],'batch_index':j,'quantity':0,'reason':None};decisions.append(d)
    audit.check(k+'/held_before_batch',batch_hold==[z['entry_id'] for z in primary_d[k]['held_before_batch']]);audit.check(k+'/batchorder',j==primary_d[k]['batch_index'])
    expected=[{'entry_id':key,'symbol':p['symbol'],'pP':p['pP'],'entry_minute':p['entry_minute'],'quantity':p['quantity'],'band':p['band']} for key,p in sorted(hold.items())]
    audit.check(k+'/full_held_snapshot',expected==primary_d[k]['held_before_batch'])
    audit.check(k+'/pP_r_band',r['pP']==primary_d[k]['pP'] and r['rank_units']==primary_d[k]['rank_units'] and r['band']==primary_d[k]['band']);audit.num(k+'/r',r['r'],primary_d[k]['r'])
    for qfield in ('q2','q3'):audit.num(k+'/'+qfield,r[qfield],primary_d[k][qfield])
    if t>=920:d['reason']='CUTOFF'
    elif r['band']==BANDS[3]:d['reason']='RANK_BASE_REJECT'
    elif any(p['symbol']==r['symbol'] for p in hold.values()):d['reason']='SAME_SYMBOL'
    else:eligible.append((r,d))
   selected=[]
   for r,d in eligible:
    occ=len(hold)+len(selected);allowed,why,count,n=accept(arm,r,occ,t,tables[str(r['block'])]);saved=primary_d[r['entry_id']];d['slot_action']='ACCEPT' if allowed else 'REJECT';audit.check(r['entry_id']+'/gate',saved['occupancy']==occ and saved['slot_reason']==why and saved['slot_action']==('ACCEPT' if allowed else 'REJECT'));audit.check(r['entry_id']+'/future_count',saved['future_pressure_session_N']==count and saved['training_session_N']==n)
    audit.check(r['entry_id']+'/free_slots',saved['free_slots']==3-occ)
    if occ<3:
     horizon,duration=predicted(r,tables[str(r['block'])]);audit.check(r['entry_id']+'/predicted_release',saved['predicted_release_minute']==horizon and saved['predicted_active_duration']==duration)
    if count is not None:audit.num(r['entry_id']+'/P_future',count/n,saved['P_future_capacity_pressure'])
    if allowed:d['slot_admission_index']=occ+1;selected.append((r,d))
    else:d['reason']=why
   if selected:
    eq=cash+sum(p['quantity']*p['mark'] for p in hold.values());alloc=lot_allocate([r for r,d in selected],eq,cash,[p['band'] for p in hold.values()])
    for (r,d),z in zip(selected,alloc):
     k=r['entry_id'];saved=primary_d[k]
     for f in ('debit','lot_debit','equity_cap','effective_cap','frozen_equity_cap','batch_budget','batch_equity','target_utilization','budget_unspent'):audit.money(k+'/allocation/'+f,z[f],saved[f])
     for f in ('quantity','first_pass_quantity','water_fill_lots','water_fill_rounds'):audit.check(k+'/allocation/'+f,z[f]==saved[f])
     audit.num(k+'/desired',float(z['desired']),float(saved['desired']));audit.check(k+'/cap_policy',z['cap_policy']==saved['cap_policy']);audit.check(k+'/cap_hit',saved['cap_hit']==(z['debit']+z['lot_debit']>z['equity_cap']))
     for f in ('mP','rM'):audit.num(k+'/'+f,z[f],saved[f])
     audit.check(k+'/strict_percentile',z['rM']==saved['rM'])
     audit.money(k+'/cash_before',cash,saved['cash_before']);d['quantity']=z['quantity']
     if z['quantity']<100:d['reason']='CASH_OR_LOT';continue
     buy=F(r['raw_reference'])*F(10005,10000);debit=buy*z['quantity'];cash-=debit;cashmin=min(cashmin,cash);used=min(original,debit);original-=used;recycled=debit-used;recycled_pool-=recycled;recycled_used+=recycled
     audit.money(k+'/recycled',recycled,saved['recycled_cash_used']);audit.check(k+'/cash_nonnegative',cash>=0 and recycled_pool>=0)
     d.update(reason='FUNDED',funded_slot=len(hold)+1);audit.check(k+'/fundedslot',d['funded_slot']==saved['funded_slot']);b=books[k]
     updates=sorted((row['minute']+1,F(row['C'])) for row in b['market'] if row['session']==day and row['minute']>=t and actual(row));hold[k]={'symbol':r['symbol'],'entry_minute':t,'quantity':z['quantity'],'buy':buy,'mark':F(r['raw_reference']),'known':t,'band':r['band'],'pP':r['pP'],'updates':updates,'cursor':0}
     src=early(b)
     if src:pending[src['release']].append((k,src))
     peak=max(peak,len(hold));audit.check(k+'/MAX3lot',len(hold)<=3 and z['quantity']%100==0)
   for r in batch:
    k=r['entry_id'];d=next(z for z in reversed(decisions) if z['entry_id']==k);audit.check(k+'/decision',d['reason']==primary_d[k]['reason'] and d['quantity']==primary_d[k]['quantity'])
   if t==920:
    for k,p in hold.items():
     src=late(books[k]);audit.check(k+'/EODsource_or_explicit_blocker',src is not None or any(z['entry_id']==k and z['reason']=='EOD_EXECUTION_BLOCKED' for z in primary_result['daily_series'][-1]['blockers']))
     if src:pending[src['release']].append((k,src))
   eq=cash+sum(p['quantity']*p['mark'] for p in hold.values());saved=primary_c[day,t];frame={'session':day,'minute':t,'equity':eq,'cash':cash,'exposure':eq-cash,'utilization':float((eq-cash)/eq),'concurrent':len(hold)};frames.append(frame)
   for f in ('equity','cash','exposure'):audit.money(f'{day}/{t}/{f}',frame[f],saved[f])
   audit.num(f'{day}/{t}/util',frame['utilization'],saved['utilization']);audit.check(f'{day}/{t}/occupancy',len(hold)==saved['concurrent']);audit.check(f'{day}/{t}/marks',{k:p['known'] for k,p in hold.items()}==saved['known_marks'])
  if hold:
   failed=primary_result['daily_series'][-1];audit.check(day+'/expected_failed_day',day==failed['session'] and failed['status']=='EXECUTION_UNRESOLVED_FAIL_CLOSED');audit.check(day+'/unresolved_identity',sorted(hold)==failed['open_obligations']);audit.check(day+'/no_imputed_end',failed['ending_cash'] is None and failed['daily_return'] is None)
   audit.money(day+'/blocked_cash_min',cashmin,failed['cash_min']);audit.money(day+'/blocked_start',starting,failed['starting_cash']);audit.check(day+'/blocked_peak',peak==failed['max_concurrent'])
   evidence={'measurement_status':'CAPITAL_MEASUREMENT_BLOCKED_EXECUTION','valid_primary_day_N':len(daily),'blocked_execution_day_N':1,'open_obligations':sorted(hold),'unresolved_quantities':{k:z['quantity'] for k,z in hold.items()},'executed_candidate_N':len(decisions),'funded_N_observed_prefix':sum(d['reason']=='FUNDED' for d in decisions),'closed_trade_N':len(trades),'curve_frame_N':len(frames),'Final38':None,'rolling20':None,'gate_evaluable':False}
   audit.check(arm+'/blocked_model',primary_result['measurement_status']==evidence['measurement_status'] and primary_result['valid_primary_day_N']==len(daily) and primary_result['blocked_execution_day_N']==1 and primary_result['execution_source_unresolved_N']==len(hold))
   audit.check(arm+'/all_emitted_ledgers_checked',len(decisions)==len(primary_d) and len(trades)==len(primary_t) and len(frames)==len(primary_c))
   return decisions,evidence,trades,frames,daily
  recycled_total+=recycled_used;allcashmin=min(allcashmin,cashmin);d={'session':day,'starting_cash':starting,'ending_cash':cash,'daily_return':float(cash/starting-1),'cash_min':cashmin,'max_concurrent':peak,'recycled_cash_used':recycled_used};daily.append(d)
  z=next(z for z in primary_result['daily_series'] if z['session']==day)
  for f in ('starting_cash','ending_cash','cash_min','recycled_cash_used'):audit.money(day+'/daily/'+f,d[f],z[f])
  audit.num(day+'/return',d['daily_return'],z['daily_return'])
 raise RuntimeError('Expected raw unresolved execution was not reproduced')
