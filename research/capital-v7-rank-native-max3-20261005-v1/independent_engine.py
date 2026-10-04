"""Standalone scalar inference / Fraction accounting auditor.

Never imports Primary mapping, runtime, execution, replay, oracle or evaluator.
Input market source independence is not claimed; implementation independence is.
"""
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal as D
from bisect import bisect_left
from collections import Counter,defaultdict
from statistics import mean,median
import gzip,json,hashlib,math
ROOT=Path(__file__).resolve().parents[2];W=ROOT.parent/'v7_work';P=W/'private';I=W/'inputs';O=ROOT/'docs/evidence/capital-v7-rank-native-max3-20261005-v1'
ARMS=['RANK_NATIVE_GREEDY_MAX3','RANK_NATIVE_LAST_SLOT_OPTION_MAX3'];BANDS=['P_HIGH','P_MID','P_BASE','P_BELOW'];CAP=[F(45,100),F(35,100),F(25,100)];BASE=[F(68,100),F(56,100),F(44,100)]
def read(p):return json.loads(Path(p).read_text())
def rows(p):
 with gzip.open(p,'rt') as f:return [json.loads(x) for x in f if x.strip()]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(r):return (-r['pP'],r['entry_timestamp'],r['symbol'])
class Audit:
 def __init__(self):self.checks=0;self.mismatches=[];self.max_float_delta=0
 def check(self,name,ok):
  self.checks+=1
  if not ok and len(self.mismatches)<200:self.mismatches.append(name)
 def money(self,name,a,b):self.check(name,F(a)==F(b))
 def num(self,name,a,b):
  delta=abs(a-b);self.max_float_delta=max(self.max_float_delta,delta);self.check(name,delta<=1e-12)
def logistic(row,model):
 p=model['preprocessing'];raw=[row['numeric'][k] for k in p['numeric_fields']]
 numeric=[0. if v is None else float(v) for v in raw]+[float(v is None) for v in raw]
 x=[(v-m)/s for v,m,s in zip(numeric,p['numeric_mean'],p['numeric_scale'])]
 for k in p['categorical_fields']:
  voc=p['categorical_train_vocab'][k];v=row['categorical'][k] if row['categorical'][k] in voc else '__UNKNOWN__';x += [float(v==z) for z in voc]
 z=math.fsum(v*c for v,c in zip(x,model['coef']))+model['intercept']
 return 1/(1+math.exp(-z)) if z>=0 else math.exp(z)/(1+math.exp(z))
def native(units,n,counts):
 index=0;total=0
 for s in 'SAB':
  total+=counts[s]
  if units>n-total:return BANDS[index]
  index+=1
 return BANDS[3]
def build_mapping(audit):
 move={r['entry_id']:r for r in rows(I/'movement/RUNTIME_CAUSAL.jsonl.gz')};core={r['entry_id']:r for r in rows(I/'core/CORE_RUNTIME_CAUSAL.jsonl.gz')};score=rows(I/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz');split=read(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json');saved_maps=read(O/'RANK_NATIVE_BAND_MAP.json')['blocks'];savedtrain={(r['block'],r['entry_id']):r for r in rows(P/'TRAIN_MAPPED_SCORES.jsonl.gz')};tables={};runtime=[];alltrain=[]
 for block in split['blocks']:
  b=block['block'];pm=read(I/f'movement/models/MOVE_P_BLOCK_{b:02}.json');heads=[read(I/f'current/models/H{h}_BLOCK_{b:02}.json') for h in (2,3,5)];ids=pm['train_entry_ids'];base=math.fsum(h['base_rate'] for h in heads)
  audit.check(f'{b}/ID_shared',all(ids==h['train_entry_ids'] for h in heads));audit.check(f'{b}/past',all(move[k]['session'] in block['train'] and move[k]['session']<min(block['test']) and move[k]['entry_minute']<920 for k in ids))
  train=[];counts=Counter()
  for k in ids:
   pp=logistic(move[k],pm);ml=math.fsum(logistic(core[k],h) for h in heads)/base;old='S' if ml>=2 else 'A' if ml>=1.5 else 'B' if ml>=1 else 'C';counts[old]+=1
   row={z:move[k][z] for z in ('entry_id','session','symbol','entry_minute','entry_timestamp')};row.update(pP=pp,old_ML=ml,old_band=old);train.append(row)
   audit.num(f'{b}/{k}/train_pP',pp,savedtrain[b,k]['pP']);audit.num(f'{b}/{k}/old_ML',ml,savedtrain[b,k]['old_ML'])
  train.sort(key=key);n=len(train);keys=[key(r) for r in train]
  counts={s:counts[s] for s in 'SABC'};audit.check(f'{b}/volume',counts==saved_maps[str(b)]['old_band_counts'])
  for j,r in enumerate(train):
   r.update(block=b,rank_units=n-j,train_N=n,r=(n-j)/n,band=native(n-j,n,counts));saved=savedtrain[b,r['entry_id']];audit.check(f'{b}/{r["entry_id"]}/rank_band',r['rank_units']==saved['rank_units'] and r['band']==saved['band'])
  for r in [r for r in score if r['block']==b]:
   audit.num(f'{b}/{r["entry_id"]}/saved_OOF_pP',logistic(r,pm),r['pP']);units=n-bisect_left(keys,key(r));rr={z:r[z] for z in ('entry_id','session','symbol','entry_minute','entry_timestamp','raw_reference','pP','block')};rr.update(rank_units=units,train_N=n,r=units/n,band=native(units,n,counts));runtime.append(rr)
  # Deliberately separate backward scan from Primary per-minute max generator.
  perday={};admitted=[r for r in train if r['band']!=BANDS[3]]
  for day in block['train']:
   minute_max={};maximum=None;byminute=defaultdict(list)
   for r in admitted:
    if r['session']==day:byminute[r['entry_minute']].append(r['rank_units'])
   for minute in range(919,539,-1):
    for u in byminute.get(minute+1,[]):maximum=u if maximum is None else max(maximum,u)
    minute_max[minute]=maximum
   perday[day]=minute_max
  tables[str(b)]={'train_N':n,'training_sessions':block['train'],'minutes':{str(t):[perday[d][t] for d in block['train']] for t in range(540,920)}};alltrain+=train
 runtime.sort(key=lambda r:(r['session'],r['entry_minute'],*key(r)))
 primary=rows(P/'RANK_NATIVE_RUNTIME.jsonl.gz');audit.check('runtime identity',len(runtime)==len(primary)==1039)
 for r,z in zip(runtime,primary):audit.check(r['entry_id']+'/runtime',all(r[k]==z[k] for k in ('entry_id','pP','rank_units','train_N','band','entry_timestamp','raw_reference')))
 audit.check('future table exact',tables==read(O/'FUTURE_MAX_RANK_TABLE.json'))
 return runtime,tables,alltrain
def actual(row,auction=False):
 try:
  vals=[F(row[k]) for k in ('O','H','L','C','Vo','Va')];o,h,l,c,vo,va=vals
  return bool(row.get('lineage')) and all(v>0 for v in vals) and l<=min(o,c)<=max(o,c)<=h and (not auction or o==h==l==c)
 except (KeyError,ValueError,ZeroDivisionError):return False
def clock(s):return int(s[11:13])*60+int(s[14:16])
def early(book):
 x=book['frozen_exit']
 if x['sell_status']!='FILLED' or clock(x['sell_source_assumed_available_at'])>920:return None
 r=next((r for r in book['market'] if r['minute']==x['sell_minute']),None)
 if r is None or not actual(r):return None
 price=F(r['O'] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else r['C'])*F(9995,10000)
 assert price==F(x['sell_price_decimal'])
 return {'release':clock(x['sell_source_assumed_available_at']),'source':r['minute'],'price':price,'kind':'FROZEN_EXIT_V3'}
def late(book):
 rr=[r for r in book['market'] if r['session']==book['session'] and 920<=r['minute']<925 and actual(r)];aa=[r for r in book['market'] if r['session']==book['session'] and r['minute']==930 and actual(r,True)]
 r=min(rr,key=lambda r:r['minute']) if rr else aa[0] if aa else None
 if r is None:return None
 return {'release':r['minute']+1,'source':r['minute'],'price':F(r['O'] if rr else r['C'])*F(9995,10000),'kind':'EOD_REGULAR' if rr else 'EOD_EXACT_1530_AUCTION'}
def accept(arm,r,occupancy,t,table):
 if occupancy==3:return False,'MAX3_FULL',None,None
 if arm==ARMS[0] or occupancy in (0,1):return True,'ACCEPT_NO_RESERVE',None,None
 count=sum(u is not None and u>r['rank_units'] for u in table['minutes'][str(t)]);n=len(table['training_sessions'])
 return count*2<n,'ACCEPT_LAST_SLOT' if count*2<n else 'LAST_SLOT_RESERVE_REJECT',count,n
def lot_allocate(picked,equity,cash,held_bands):
 ids=[BANDS.index(b) for b in held_bands]+[BANDS.index(r['band']) for r in picked];target=min(F(92,100),BASE[min(ids)]+F(55,1000)*(len(ids)-1));budget=min(cash,max(F(0),equity*target-(equity-cash)));ws=[F(str(r['pP'])) for r in picked];remaining=cash;unspent=budget;alloc=[]
 for r,w in zip(picked,ws):
  lot=F(r['raw_reference'])*F(10005,10000)*100;cap=equity*CAP[BANDS.index(r['band'])];desired=budget*w/sum(ws);lots=max(0,int(min(desired,cap,remaining)//lot));debit=lots*lot;remaining-=debit;unspent-=debit
  alloc.append({'quantity':lots*100,'first_pass_quantity':lots*100,'debit':debit,'lot_debit':lot,'equity_cap':cap,'batch_budget':budget,'batch_equity':equity,'target_utilization':target,'water_fill_lots':0})
 rounds=0
 while True:
  changes=0
  for z in alloc:
   if z['first_pass_quantity'] and z['lot_debit']<=min(remaining,unspent,z['equity_cap']-z['debit']):
    z['quantity']+=100;z['debit']+=z['lot_debit'];z['water_fill_lots']+=1;remaining-=z['lot_debit'];unspent-=z['lot_debit'];changes+=1
  if not changes:break
  rounds+=1
 for z in alloc:z.update(water_fill_rounds=rounds,budget_unspent=unspent)
 return alloc
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
    k=r['entry_id'];d={'entry_id':k,'session':day,'minute':t,'pP':r['pP'],'band':r['band'],'rank_units':r['rank_units'],'quantity':0,'reason':None};decisions.append(d)
    audit.check(k+'/held_before_batch',batch_hold==[z['entry_id'] for z in primary_d[k]['held_before_batch']]);audit.check(k+'/batchorder',j==primary_d[k]['batch_index'])
    if t>=920:d['reason']='CUTOFF'
    elif r['band']==BANDS[3]:d['reason']='RANK_BASE_REJECT'
    elif any(p['symbol']==r['symbol'] for p in hold.values()):d['reason']='SAME_SYMBOL'
    else:eligible.append((r,d))
   selected=[]
   for r,d in eligible:
    occ=len(hold)+len(selected);allowed,why,count,n=accept(arm,r,occ,t,tables[str(r['block'])]);saved=primary_d[r['entry_id']];audit.check(r['entry_id']+'/gate',saved['occupancy']==occ and saved['slot_reason']==why and saved['slot_action']==('ACCEPT' if allowed else 'REJECT'));audit.check(r['entry_id']+'/future_count',saved['future_better_N']==count and saved['training_session_N']==n)
    if count is not None:audit.num(r['entry_id']+'/P_future',count/n,saved['P_future_better'])
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
 metrics={'rolling20_minimum':min(rolling),'rolling20_arithmetic_mean':mean(rolling),'rolling20_median':median(rolling),'rolling20_maximum':max(rolling),'north_star_hit_N':sum(x>=2 for x in rolling),'geometric_mean_daily_return':math.expm1(mean(math.log1p(x) for x in returns)),'arithmetic_mean_daily_return':mean(returns),'median_daily_return':median(returns),'final_equity':float(cash),'max_drawdown':float(dd),'utilization_mean':mean(util),'utilization_median':median(util),'idle_cash_mean_jpy':float(sum((c['cash'] for c in samples),F(0))/len(samples)),'mean_idle_cash_fraction':mean(1-z for z in util),'capital_recycling_used_jpy':float(recycled_total),'funded_N':sum(d['reason']=='FUNDED' for d in decisions)}
 for f,v in metrics.items():
  if f in ('idle_cash_mean_jpy','capital_recycling_used_jpy','final_equity'):audit.money(arm+'/secondary/'+f,str(v),str(primary_result[f]))
  else:audit.num(arm+'/'+f,v,primary_result[f])
 for z,s in zip(rolling,primary_result['rolling20_windows']):audit.num(arm+'/rolling',z,s['growth_multiple'])
 return decisions,metrics
