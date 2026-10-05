"""Independent Fraction portfolio reconstruction; no Primary imports."""
from independent_engine import *
from independent_policy import accept,predicted
def reconstruct(arm,stream,tables,audit):
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
     for f in ('debit','lot_debit','equity_cap','batch_budget','batch_equity','target_utilization','budget_unspent'):audit.money(k+'/allocation/'+f,z[f],saved[f])
     for f in ('quantity','first_pass_quantity','water_fill_lots','water_fill_rounds'):audit.check(k+'/allocation/'+f,z[f]==saved[f])
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
     src=late(books[k]);audit.check(k+'/EODsource',src is not None)
     if src:pending[src['release']].append((k,src))
   eq=cash+sum(p['quantity']*p['mark'] for p in hold.values());saved=primary_c[day,t];frame={'session':day,'minute':t,'equity':eq,'cash':cash,'exposure':eq-cash,'utilization':float((eq-cash)/eq),'concurrent':len(hold)};frames.append(frame)
   for f in ('equity','cash','exposure'):audit.money(f'{day}/{t}/{f}',frame[f],saved[f])
   audit.num(f'{day}/{t}/util',frame['utilization'],saved['utilization']);audit.check(f'{day}/{t}/occupancy',len(hold)==saved['concurrent']);audit.check(f'{day}/{t}/marks',{k:p['known'] for k,p in hold.items()}==saved['known_marks'])
  audit.check(day+'/closed',not hold);recycled_total+=recycled_used;allcashmin=min(allcashmin,cashmin);d={'session':day,'starting_cash':starting,'ending_cash':cash,'daily_return':float(cash/starting-1),'cash_min':cashmin,'max_concurrent':peak,'recycled_cash_used':recycled_used};daily.append(d)
  s=next(s for s in primary_result['daily_series'] if s['session']==day)
  for f in ('starting_cash','ending_cash','cash_min','recycled_cash_used'):audit.money(day+'/daily/'+f,d[f],s[f])
  audit.num(day+'/return',d['daily_return'],s['daily_return'])
 returns=[d['daily_return'] for d in daily];rolling=[float(daily[i+19]['ending_cash']/daily[i]['starting_cash']) for i in range(19)];peak=F(1000000);dd=F(0)
 for c in frames:peak=max(peak,c['equity']);dd=max(dd,(peak-c['equity'])/peak)
 samples=[c for c in frames if 540<=c['minute']<690 or 750<=c['minute']<930];util=[c['utilization'] for c in samples]
 metrics={'rolling20_minimum':min(rolling),'rolling20_arithmetic_mean':mean(rolling),'rolling20_median':median(rolling),'rolling20_maximum':max(rolling),'north_star_hit_N':sum(x>=2 for x in rolling),'geometric_mean_daily_return':math.expm1(mean(math.log1p(x) for x in returns)),'arithmetic_mean_daily_return':mean(returns),'median_daily_return':median(returns),'final_equity':float(cash),'max_drawdown':float(dd),'utilization_mean':mean(util),'utilization_median':median(util),'idle_cash_mean_jpy':float(sum((c['cash'] for c in samples),F(0))/len(samples)),'mean_idle_cash_fraction':mean(1-z for z in util),'capital_recycling_used_jpy':float(recycled_total),'turnover_cash_jpy':float(sum((t['debit']+t['credit'] for t in trades),F(0))),'funded_N':sum(d['reason']=='FUNDED' for d in decisions),'LOWER_P_ACCEPT_AFTER_HIGHER_P_RESERVE_SAME_BATCH':sum(any(h['session']==d['session'] and h['minute']==d['minute'] and h['batch_index']<d['batch_index'] and h['pP']>d['pP'] and h['reason']=='CAPACITY_RESERVE_REJECT' for h in decisions) for d in decisions if d.get('slot_action')=='ACCEPT')}
 for f,v in metrics.items():
  if f in ('idle_cash_mean_jpy','capital_recycling_used_jpy','final_equity'):audit.money(arm+'/secondary/'+f,str(v),str(primary_result[f]))
  else:audit.num(arm+'/'+f,v,primary_result[f])
 for z,s in zip(rolling,primary_result['rolling20_windows']):audit.num(arm+'/rolling',z,s['growth_multiple'])
 return decisions,metrics,trades,frames,daily
