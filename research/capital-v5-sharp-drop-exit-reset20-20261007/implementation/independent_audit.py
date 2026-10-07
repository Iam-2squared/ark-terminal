"""Same-author independent scalar reconstruction. Imports stdlib only, no primary code."""
from pathlib import Path
from decimal import Decimal,ROUND_FLOOR,localcontext
from fractions import Fraction
import json,gzip,hashlib,zipfile,collections,re,math

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
  a=[D(str(r[k])) for k in ['minute','O','H','L','C','Vo','Va']]
  return all(math.isfinite(float(x)) for x in a) and a[3]>0 and a[3]<=min(a[1],a[4])<=max(a[1],a[4])<=a[2] and a[5]>=0 and a[6]>=0
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

checks=0;mismatches=[];seen_state_rows=0
def verify(name,a,b,money=False):
 global checks
 checks+=1
 try:ok=D(str(a))==D(str(b)) if money and a is not None and b is not None else a==b
 except Exception:ok=False
 if not ok and len(mismatches)<100:mismatches.append({'check':name,'independent':a,'primary':b})
 return ok
def compile_states(stream,books):
 global seen_state_rows
 prior={x['entry_id']:x for x in rows(R/'private/immutable/STATE_PREFIX_CACHE.jsonl.gz')}
 out={};st=('RISE_STOP','RISE','SHARP_RISE','PULLBACK','RANGE','REBOUND','SHARP_DROP','DROP','DROP_STOP')
 binding=read(R/'inputs/STATE9_TRACE_ARCHIVE_BINDING.json')
 with zipfile.ZipFile(R/'inputs/STATE9_V2_FROZEN_TRACE_ARCHIVE.zip') as z:
  for r in stream:
   key=r['entry_id'];b=books[key];x=b['frozen_exit']['exit_intent'];ctrl=min(x['minute'],920) if x else 920;buy=r['entry_minute'];member=binding['trace_members'][key];body=z.read(member);cp=binding['manifest']['components'][member]
   verify('raw_State_member_hash:'+key,hashlib.sha256(body).hexdigest(),cp['sha256']);cache={p['checkpoint_minute']:p for p in prior[key]['frames']};selected=None
   for line in gzip.decompress(body).splitlines(keepends=True):
    q=json.loads(line);t=q['bar_end_minute']
    if t>ctrl:break
    if t<=buy:continue
    seen_state_rows+=1;s=q['state'];p=q['path'];at=s['as_of'];i=q['input']
    timing=(q['watch_key']==s['case_id']==p['case_id']==key and at==t-540 and p['scheduled_t']==at and q['assumed_available_at']==stamp(r['session'],t) and p['bar_end']==q['assumed_available_at'] and (i is None or i['known_at']<=at and i['t']<=at))
    usable=bool(timing and s['current_semantics_observed'] is True and p['current_semantics_observed'] is True and s['observed_at']==s['as_of'] and p['quality']['numeric_status']=='ACCEPTED' and p['Primary_or_null'] in st and q['source_status']=='RAW_CLOSED_AT_ASSUMED_BAR_END' and s['activity']!='CARRIED_GAP' and s['basis']!='CARRIED_GAP')
    gap=not timing or p['Primary_or_null'] is not None and p['Primary_or_null'] not in st
    verify('State_usability:'+key+':'+str(t),usable,cache[t]['usable']);verify('State_Primary:'+key+':'+str(t),p['Primary_or_null'] if usable else None,cache[t]['Primary']);verify('State_line_bytes:'+key+':'+str(t),hashlib.sha256(line).hexdigest(),cache[t]['source_line_sha256'])
    if selected is None and t<ctrl:
     if gap:selected={'action':'EVIDENCE_GAP','block_minute':t,'reason':'EVIDENCE_GAP_BEFORE_CONTROL','source':None}
     elif usable and p['Primary_or_null']=='SHARP_DROP':selected={'action':'SD_FIRST','intent_minute':t}
   if selected is None:selected={'action':'DELEGATE_CONTROL','intent_minute':ctrl,'source':csource(b)}
   elif selected['action']=='SD_FIRST':
    ct=csource(b) or eod(b);terminal=ct.get('source_minute') if ct and ct.get('price') else 930
    mr=[q for q in b['market'] if q.get('session')==b['session'] and q['minute']<=terminal]
    mixed={540,750,min((q['minute'] for q in mr if q['minute']<690),default=None),min((q['minute'] for q in mr if 750<=q['minute']<925),default=None)}
    possible=[q for q in mr if rawvalid(q) and (540<=q['minute']<690 or 750<=q['minute']<925) and q['minute'] not in mixed and q['minute']>=selected['intent_minute'] and q['minute']>buy]
    close=[q for q in mr if q['minute']==930 and rawvalid(q)]
    sr=min(possible,key=lambda q:q['minute']) if possible else close[0] if len(close)==1 else None
    if sr and valid(sr,not possible):selected['source']={'kind':'SHARP_DROP_FIRST_OBSERVED_EXIT_V0','source_minute':sr['minute'],'release_minute':sr['minute']+1,'price':str(D(str(sr['O'] if possible else sr['C']))*D('.9995')),'lineage':sr['lineage']}
    else:selected['source']=None
   out[key]=selected
 return out

def order(r):return (-r['ML'],-r['m5'],-r['m3'],-r['m2'],r['entry_timestamp'],r['symbol'])
def classify(score):
 if score is None or not math.isfinite(score) or score<1:return None
 return 'S' if score>=2 else 'A' if score>=1.5 else 'B'
def allot(selected,equity,exposure,cash,held):
 caps={'S':D('.45'),'A':D('.35'),'B':D('.25')};base={'S':D('.68'),'A':D('.56'),'B':D('.44')}
 bands=held+[classify(r['capital_score']) for r in selected];best=min(bands,key=lambda b:['S','A','B'].index(b));target=min(D('.92'),base[best]+D('.055')*(len(bands)-1));budget=min(cash,max(D(0),equity*target-exposure));weight=sum(D(str(r['capital_score'])) for r in selected);remaining=cash;unspent=budget;ans=[]
 for r in selected:
  ba=classify(r['capital_score']);lot=D(r['raw_reference'])*D('1.0005')*100;cap=equity*caps[ba];desired=budget*D(str(r['capital_score']))/weight;lots=max(0,int((min(desired,cap,remaining)/lot).to_integral_value(rounding=ROUND_FLOOR)));debit=lots*lot;remaining-=debit;unspent-=debit
  ans.append({'entry_id':r['entry_id'],'quantity':lots*100,'first_pass_quantity':lots*100,'water_fill_lots':0,'debit':debit,'lot_debit':lot,'equity_cap':cap,'desired':desired,'band':ba,'target_utilization':target,'batch_equity':equity,'batch_budget':budget})
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

def reconstruct(day,candidates,books,tables,cash,arm,plans):
 held={};schedule=collections.defaultdict(list);events=collections.defaultdict(list)
 for r in candidates:events[r['entry_minute']].append(r)
 decisions=[];trades=[];curves=[];intents=[];blockers=[];peakN=0;cashmin=cash;origin=cash;recycled=D(0);reused=D(0);initial=cash
 def equity():return cash+sum(p['quantity']*p['mark'] for p in held.values())
 for minute in range(540,932):
  for key,p in held.items():
   while p['index']<len(p['updates']) and p['updates'][p['index']][0]<=minute:
    kt,px=p['updates'][p['index']];p['mark']=px;p['known']=kt;p['index']+=1
  for key,s in sorted(schedule.pop(minute,[]),key=lambda pair:pair[0]):
   if s.get('blocked'):blockers.append({'entry_id':key,'minute':minute,'reason':s['blocked']});continue
   p=held.pop(key);credit=p['quantity']*D(s['price']);debit=p['quantity']*p['buy'];cash+=credit;recycled+=credit
   trades.append({'entry_id':key,'session':day,'quantity':p['quantity'],'entry_minute':p['entry_minute'],'release_minute':minute,'source_minute':s['source_minute'],'exit_kind':s['kind'],'buy_effective':str(p['buy']),'sell_effective':s['price'],'debit':str(debit),'credit':str(credit),'pnl':str(credit-debit),'net_return':float(credit/debit-1),'lineage':s['lineage'],'commission':0})
  if arm=='E':
   for key,p in sorted(held.items()):
    plan=p['plan']
    if plan['action']=='EVIDENCE_GAP' and minute==plan['block_minute']:blockers.append({'entry_id':key,'minute':minute,'reason':plan['reason']})
    if plan['action']=='SD_FIRST' and minute==plan['intent_minute']:
     p['latched']=True;intents.append({'entry_id':key,'session':day,'minute':minute,'side':'SELL','quantity':p['quantity'],'reason':'SHARP_DROP_FIRST_OBSERVED','transmitted':False,'latched':True})
   if any(b['reason']=='EVIDENCE_GAP_BEFORE_CONTROL' and b['minute']==minute for b in blockers):break
  batch=sorted(events.get(minute,[]),key=order);eligible=[]
  for r in batch:
   d={k:r[k] for k in ['entry_id','session','capital_score','rank','ML','m2','m3','m5']};d.update(minute=minute,quantity=0,reason=None,held_before_batch=sorted(held));decisions.append(d)
   if minute>=920:d['reason']='CAPITAL_EOD_ENTRY_CUTOFF'
   elif not r['admission']:d['reason']='UPWARD_BELOW_BASELINE'
   elif classify(r['capital_score']) is None:d['reason']='SCORE_INPUT_UNKNOWN'
   elif any(p['symbol']==r['symbol'] for p in held.values()):d['reason']='SYMBOL_ALREADY_OPEN'
   else:eligible.append((r,d))
  picked=[]
  for r,d in eligible:
   occ=len(held)+len(picked);table=tables[str(r['block'])];cnt=table['minute_counts'][str(minute)];prob=cnt[0]/table['training_session_N'];ex=cnt[2]/table['training_session_N'];rank=r['rank']
   if occ==3:allow=False;why='MAX_POSITION_CAP'
   elif occ==0:allow=True;why='SLOT1_NO_RESERVE'
   elif rank in ['S','A']:allow=True;why='SA_ALWAYS_ADMIT'
   elif occ==1:
    allow=minute>=840 or r['ML']>=table['B_median'] and prob<.50;why='SLOT2_B_LATE_RELEASE' if minute>=840 else 'SLOT2_B_QUALITY_AND_ARRIVAL_PASS' if allow else 'SLOT2_RESERVE_FOR_FUTURE_QUALITY'
   else:
    allow=r['ML']>=table['B_p75'] and (minute>=870 or prob<.35 and ex<.75);why='SLOT3_B_LATE_RELEASE' if allow and minute>=870 else 'SLOT3_B_QUALITY_AND_ARRIVAL_PASS' if allow else 'SLOT3_RESERVE_FOR_FUTURE_QUALITY'
   d.update(pre_decision_occupancy=occ,slot_gate_reason=why,remaining_Aplus_probability=prob,expected_remaining_Aplus=ex)
   if allow:d['slot_admission_index']=occ+1;picked.append((r,d))
   else:d['reason']='SLOT_RESERVE_REJECT' if why.startswith(('SLOT2_RESERVE','SLOT3_RESERVE')) else why
  if picked:
   eq=equity();assigned=allot([r for r,d in picked],eq,eq-cash,cash,[p['band'] for p in held.values()])
   for (r,d),a in zip(picked,assigned):
    d.update({k:str(v) if isinstance(v,D) else v for k,v in a.items() if k!='entry_id'});d['cash_before']=str(cash);q=a['quantity']
    if q==0:d['reason']='CASH_OR_LOT_CONSTRAINED';continue
    buy=D(r['raw_reference'])*D('1.0005');debit=buy*q;cash-=debit;cashmin=min(cashmin,cash);used=min(origin,debit);origin-=used;rc=debit-used;recycled-=rc;reused+=rc;d.update(reason='FUNDED',debit=str(debit),recycled_cash_used=str(rc),funded_slot=len(held)+1)
    key=r['entry_id'];b=books[key];p={'quantity':q,'buy':buy,'mark':D(r['raw_reference']),'known':minute,'symbol':r['symbol'],'entry_minute':minute,'band':r['capacity_band'],'index':0,'updates':sorted([(s['minute']+1,D(s['C'])) for s in b['market'] if s.get('session')==day and s['minute']>=minute and valid(s)]),'latched':False,'plan':plans[key]};held[key]=p;peakN=max(peakN,len(held))
    if not b['capture_complete'] or not b.get('entry_actual_source'):blockers.append({'entry_id':key,'minute':minute,'reason':'MTM_SOURCE_LINEAGE_BLOCKED'})
    src=plans[key].get('source') if arm=='E' else csource(b)
    if src:schedule[src['release_minute']].append((key,src))
  if minute==920:
   for key,p in sorted(held.items()):
    if arm=='E' and p['latched']:continue
    auth=books[key]['limit_up_authority'];limit=bool(auth and auth.get('status')=='LIMIT_UP_CONFIRMED' and auth.get('authoritative_price_limit_source') and auth.get('causal_exchange_status') and auth.get('session')==day and auth.get('known_minute',9999)<=minute and auth.get('observed_minute',9999)<=minute)
    it={'minute':920,'side':'SELL','quantity':p['quantity'],'sor':True,'order_type':'MARKET','condition':'DAY','transmitted':False,'entry_id':key,'session':day,'limit_up_status':'LIMIT_UP_CONFIRMED' if limit else 'LIMIT_UP_UNKNOWN'};intents.append(it);s=eod(books[key])
    if s:schedule[s['release_minute']].append((key,s))
    else:blockers.append({'entry_id':key,'minute':931,'reason':'LIMIT_UP_EOD_UNEXECUTED_FAIL_CLOSED' if limit else 'EOD_UNEXECUTED_FAIL_CLOSED'})
  if arm=='E' and any(b['reason']=='MTM_SOURCE_LINEAGE_BLOCKED' for b in blockers):break
  eq=equity();curves.append({'session':day,'minute':minute,'equity':str(eq),'cash':str(cash),'exposure':str(eq-cash),'concurrent':len(held),'known_marks':{k:p['known'] for k,p in held.items()},'utilization':float((eq-cash)/eq),'primary_chain':True})
 if held:
  prior={b['entry_id'] for b in blockers}
  for key in held:
   if key not in prior:blockers.append({'entry_id':key,'minute':931,'reason':'EOD_UNEXECUTED_FAIL_CLOSED'})
 complete=not held and not blockers
 daily={'session':day,'status':'COMPLETE' if complete else 'PORTFOLIO_MEASUREMENT_BLOCKED_EXECUTION','starting_cash':str(initial),'ending_cash':str(cash) if complete else None,'daily_return':float(cash/initial-1) if complete else None,'diagnostic_daily_return':float(cash/initial-1) if complete else None,'primary_chain':True,'blockers':blockers,'open_obligations':list(held),'cash_min':str(cashmin),'max_concurrent':peakN,'recycled_cash_used':str(reused)}
 return daily,decisions,trades,curves,intents

def rb(pnl,debit):
 with localcontext() as c:c.prec=60;ret=D(pnl)/D(debit)
 v=F(str(ret))*100
 if v<=-5:return 'L5_PLUS'
 for k,b in [(-4,'L4_5'),(-3,'L3_4'),(-2,'L2_3'),(-1,'L1_2')]:
  if v<=k:return b
 if v<0:return 'L0_1'
 if v==0:return 'ZERO'
 if v<1:return 'P0_1'
 for k,b in [(2,'P1_2'),(3,'P2_3'),(4,'P3_4'),(5,'P4_5')]:
  if v<k:return b
 return 'P5_PLUS'
def compare_records(tag,own,actual,fields=None):
 verify(tag+':length',len(own),len(actual))
 for index,(a,b) in enumerate(zip(own,actual)):
  for k in fields or a:
   verify(tag+':'+str(index)+':'+k,a.get(k),b.get(k),k in ['equity','cash','exposure','buy_effective','sell_effective','debit','credit','pnl','cash_before','lot_debit','equity_cap','desired','target_utilization','batch_equity','batch_budget','budget_unspent','recycled_cash_used','starting_cash','ending_cash','cash_min'])

def main():
 assert not (R/'private/independent/INDEPENDENT_COMPLETE.json').exists(),'one independent campaign only'
 stream=rows(R/'inputs/v5/candidate_stream');books={r['entry_id']:r for r in rows(R/'inputs/v5/books')};table=read(R/'inputs/v5/arrival');split=read(R/'inputs/v5/split');plans=compile_states(stream,books);primaryplans={r['entry_id']:r['plan'] for r in rows(R/'private/immutable/EXIT_PLANS.jsonl.gz')}
 for key,plan in plans.items():
  x=primaryplans[key];verify('EXIT_trigger:'+key,plan['action'],x['action']);verify('EXIT_first_intent:'+key,plan.get('intent_minute'),x.get('intent_minute'))
  for k in ['source_minute','release_minute','kind','price']:verify('EXIT_fill:'+key+':'+k,(plan.get('source') or {}).get(k),(x.get('source') or {}).get(k),k=='price')
 completed=[]
 windows={r['window_id']:r['sessions'] for r in read(R/'inputs/S6_COVERAGE_AND_WINDOWS.json')['windows'] if r['coverage_complete']};windows['CHAIN38']=split['OOF38']
 for w,sessions in windows.items():
  for arm in ['C','E']:
   original=R/'private/runs'/w/arm
   if not (original/'RESULT.json').exists():continue
   dest=R/'private/independent'/w/arm;save(dest/'STARTED.json',{'stage':'INDEPENDENT_RECONSTRUCTION','input_source':'ORIGINAL_SCORE_BOOK_STATE_ARCHIVE_TABLES','primary_imports':0,'window_id':w,'arm':arm})
   cash=D(1000000);daily=[];all_d=[];all_t=[];all_c=[];all_i=[]
   for day in sessions:
    d,ds,ts,cs,it=reconstruct(day,[r for r in stream if r['session']==day],books,table,cash,arm,plans);daily.append(d);all_d+=ds;all_t+=ts;all_c+=cs;all_i+=it
    if d['status']!='COMPLETE':break
    cash=D(d['ending_cash'])
   for label,rr in [('DECISIONS',all_d),('TRADES',all_t),('CURVE',all_c),('INTENTS',all_i)]:
    gzsave(dest/(label+'.jsonl.gz'),rr);compare_records(w+':'+arm+':'+label,rr,rows(original/(label+'.jsonl.gz')))
   primary=read(original/'RESULT.json');compare_records(w+':'+arm+':DAILY',daily,primary['daily_series'])
   complete=len(daily)==len(sessions) and all(d['status']=='COMPLETE' for d in daily);final=str(cash) if complete else None
   verify(w+':'+arm+':FINAL',final,primary['final_equity'],True)
   ownbands=dict(collections.Counter(rb(t['pnl'],t['debit']) for t in all_t));savedbands=dict(collections.Counter(rb(t['pnl'],t['debit']) for t in rows(original/'TRADES.jsonl.gz')));verify(w+':'+arm+':R_BANDS',ownbands,savedbands)
   peak=D(1000000);maxdd=D(0)
   for c in all_c:
    eq=D(c['equity']);peak=max(peak,eq);maxdd=max(maxdd,(peak-eq)/peak)
   sm={'window_id':w,'arm':arm,'status':'COMPLETE' if complete else 'BLOCKED','final_equity':final,'funded_N':sum(d['reason']=='FUNDED' for d in all_d),'closed_N':len(all_t),'gross_loss_jpy':str(-sum((D(t['pnl']) for t in all_t if D(t['pnl'])<0),D(0))),'gross_positive_jpy':str(sum((D(t['pnl']) for t in all_t if D(t['pnl'])>0),D(0))),'MaxDD_pct':str(maxdd*100),'R_bands':ownbands,'daily_series':daily};save(dest/'RESULT.json',sm);completed.append({k:v for k,v in sm.items() if k!='daily_series'})
   print(json.dumps({'independent_window':w,'arm':arm,'final':final,'mismatch_N':len(mismatches)}),flush=True)
 out={'status':'PASS' if not mismatches else 'FAIL','same_author_separate_implementation':True,'third_party_blind_audit':False,'primary_allocator_overlay_evaluator_imports':0,'State_kernel':'SHARED_PREEXISTING_SAVED_KERNEL_OUTPUT; independently re-read original raw saved trace prefixes; no kernel certification','original_trace_rows_verified':seen_state_rows,'scalar_check_N':checks,'mismatch_N':len(mismatches),'mismatches':mismatches,'path_N':len(completed),'paths':completed,'money_quantity_ID_time':'EXACT_NUMERIC_VALUES; decimal lexical scale not a tolerance','new_fits':0,'provider_requests':0,'protected_opens':0}
 save(R/'public/INDEPENDENT_AUDIT.json',out);save(R/'private/independent/INDEPENDENT_COMPLETE.json',out)
 if mismatches:raise AssertionError(('INDEPENDENT_MISMATCH',mismatches[:3]))
if __name__=='__main__':main()
