"""Scalar inference + Fraction portfolio audit; imports no Primary policy/replay."""
from independent_engine import replay,read,actual,F,ROOT,scalar_probability
from pathlib import Path
from statistics import mean,median
from collections import Counter
import json,math,gzip,hashlib
W=ROOT.parent;P=W/'capital_v5_slot_private';S=W/'source_main';OUT=ROOT/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1';FROZEN=S/'capital_staircase_v4_private';SRC=S/'inputs/v3';PROFILE='CAPITAL_MAX3_SLOT_RESERVE_V1'
def save(p,x):
 with Path(p).open('x') as f:json.dump(x,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
def gzsave(p,x):
 with Path(p).open('xb') as f:f.write(gzip.compress(('\n'.join(json.dumps(r,sort_keys=True) for r in x)+'\n').encode(),mtime=0))
def isotonic(v):
 candidates=[v,[sum(v[:2])/2]*2+[v[2]],[v[0]]+[sum(v[1:])/2]*2,[sum(v)/3]*3]
 valid=[x for x in candidates if x[0]>=x[1]>=x[2]]
 return min(valid,key=lambda x:sum((a-b)**2 for a,b in zip(x,v)))
def quantile(v,p):
 v=sorted(v);h=(len(v)-1)*p;a=int(math.floor(h));b=int(math.ceil(h));return v[a]+(v[b]-v[a])*(h-a)
def training_tables(runtime,split,models):
 tables={};predictions=[]
 for block in split['blocks']:
  b=block['block'];training=[r for r in runtime if r['session'] in block['train'] and r['entry_minute']<920]
  artifacts=[models[f'H{k}_BLOCK_{b:02d}.json'] for k in (2,3,5)];base=sum(h['base_rate'] for h in artifacts);scored=[]
  for r in training:
   raw=[scalar_probability(r,h) for h in artifacts];m=isotonic(raw);ml=sum(m)/base;rank='S' if ml>=2 else 'A' if ml>=1.5 else 'B' if ml>=1 else 'C'
   z={'block':b,'entry_id':r['entry_id'],'session':r['session'],'entry_minute':r['entry_minute'],'ML':ml,'rank':rank,'admission':ml>=1,**{f'p{k}':raw[i] for i,k in enumerate((2,3,5))},**{f'm{k}':m[i] for i,k in enumerate((2,3,5))}}
   scored.append(z);predictions.append(z)
  Bs=[r['ML'] for r in scored if r['rank']=='B'];n=len(block['train']);table={'training_sessions':block['train'],'training_session_N':n,'training_candidate_N':len(training),'training_B_N':len(Bs),'B_median':quantile(Bs,.5),'B_p75':quantile(Bs,.75),'minute_counts':{},'buckets':[]}
  for lower,upper in [(540,570),(570,600),(600,630),(630,660),(660,690),(750,780),(780,810),(810,840),(840,870),(870,900),(900,920)]:
   for minute in range(lower,upper):
    byday=[]
    for day in block['train']:
     remaining=[r for r in scored if r['session']==day and minute<=r['entry_minute']<920]
     byday.append((sum(r['ML']>=1 for r in remaining),sum(r['ML']>=1.5 for r in remaining)))
    admission=[z[0] for z in byday];a=[z[1] for z in byday]
    table['minute_counts'][str(minute)]=[sum(z>=1 for z in a),sum(z>=2 for z in a),sum(a),sum(admission)]
    if minute==lower:table['buckets'].append({'remaining_Admission_pass_distribution':{str(k):v for k,v in Counter(admission).items()},'remaining_A_or_better_distribution':{str(k):v for k,v in Counter(a).items()},'P_remaining_Aplus_ge1':sum(z>=1 for z in a)/n,'P_remaining_Aplus_ge2':sum(z>=2 for z in a)/n,'expected_remaining_Aplus':sum(a)/n,'per_training_session_counts':[list(z) for z in byday]})
  tables[str(b)]=table
 return tables,predictions
def quality(ids,tt,sm,tm=None):
 ids=sorted(ids);n=len(ids);v=[tt[k]['potential_return'] for k in ids]
 rv=[float(F(tm[k]['credit'])/F(tm[k]['debit'])-1) if tm else tt[k]['realized_net_return'] for k in ids if (k in tm if tm else tt[k]['realized_net_return'] is not None)]
 result={'N':n,'rank_counts':dict(Counter(sm[k]['rank'] for k in ids)),'realized_resolved_N':len(rv),'realized_unresolved_N':n-len(rv),'realized_mean':mean(rv) if rv else None,'realized_median':median(rv) if rv else None}
 for name,low,high in [('U2',.02,None),('U3',.03,None),('Medium',.03,.05),('U5',.05,None),('U10',.10,None),('below2',None,.02),('below3',None,.03)]:
  count=sum((low is None or z>=low) and (high is None or z<high) for z in v);result[name+'_N']=count;result[name+'_rate']=count/n if n else None
 for name,fn in [('PF1',lambda z:z>=.01),('positive',lambda z:z>0),('loser',lambda z:z<=0)]:
  count=sum(fn(z) for z in rv);result[name+'_N']=count;result[name+'_rate']=count/len(rv) if rv else None
 if tm is not None:result['actual_pnl_jpy']=float(sum((F(tm[k]['credit'])-F(tm[k]['debit']) for k in ids if k in tm),F(0)))
 return result
def main():
 checks=Counter();mismatches=[]
 def check(name,ok,detail=None):
  checks[name]+=1
  if not ok:mismatches.append({'kind':name,'detail':detail})
 def close(name,a,b,tol=1e-12):check(name,(a is None and b is None) or (a is not None and b is not None and abs(a-b)<=tol))
 def compare_quality(a,b):
  check('quality/fields',a.keys()==b.keys())
  for k,v in a.items():
   if isinstance(v,dict):check('quality/'+k,v==b[k])
   else:close('quality/'+k,v,b[k],1e-8 if k=='actual_pnl_jpy' else 1e-12)
 saved=read(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz');sm={r['entry_id']:r for r in saved};tt={r['entry_id']:r for r in read(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')};books={r['entry_id']:r for r in read(SRC/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
 split=json.loads((S/'repo/docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json').read_text());models={p.name:json.loads(p.read_text()) for p in (FROZEN/'models').glob('*.json')}
 tables,trainpred=training_tables(read(SRC/'capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz'),split,models);primary_tables=json.loads((OUT/'ARRIVAL_TABLE.json').read_text());saved_train={(r['block'],r['entry_id']):r for r in read(P/'TRAINING_ONLY_SCORED_ARRIVALS.jsonl.gz')}
 for r in trainpred:
  z=saved_train[(r['block'],r['entry_id'])]
  for k in ('ML','p2','p3','p5','m2','m3','m5'):close('training_inference/'+k,r[k],z[k])
  check('training_inference/rank',r['rank']==z['rank']);check('training_inference/admission',r['admission']==z['admission'])
 for b,table in tables.items():
  primary=primary_tables[b]
  for k in ('training_sessions','training_session_N','training_candidate_N','training_B_N','minute_counts'):check('arrival/'+k,table[k]==primary[k])
  for k in ('B_median','B_p75'):close('arrival/'+k,table[k],primary[k])
  for a,z in zip(table['buckets'],primary['buckets']):
   for k,v in a.items():
    if isinstance(v,(dict,list)):check('bucket/'+k,v==z[k])
    else:close('bucket/'+k,v,z[k])
 for r in saved:
  heads=[models[f'H{k}_BLOCK_{r["block"]:02d}.json'] for k in (2,3,5)];raw=[scalar_probability(r,h) for h in heads];m=isotonic(raw);ml=sum(m)/sum(h['base_rate'] for h in heads)
  for k,a,z in zip(('p2','p3','p5'),raw,[r['p2'],r['p3'],r['p5']]):close('OOF/'+k,a,z)
  close('OOF/ML',ml,r['ML']);check('OOF/rank',('S' if ml>=2 else 'A' if ml>=1.5 else 'B' if ml>=1 else 'C')==r['rank'])
 ds,ts,frames,days,intents=replay(3,saved,books,PROFILE,tables)
 pd=read(P/f'{PROFILE}_DECISIONS.jsonl.gz');pt=read(P/f'{PROFILE}_TRADES.jsonl.gz');pc=read(P/f'{PROFILE}_CURVE.jsonl.gz');pi=read(P/f'{PROFILE}_INTENTS.jsonl.gz');econ=json.loads((P/f'{PROFILE}_RESULT.json').read_text());analysis=json.loads((OUT/'SLOT_QUALITY_AND_RESERVATION.json').read_text())
 for name,a,z in [('decisions',ds,pd),('trades',ts,pt),('frames',frames,pc),('intents',intents,pi)]:check(name+'/count',len(a)==len(z))
 for a,z in zip(ds,pd):
  for k in ('entry_id','reason','quantity'):check('decision/'+k,a[k]==z[k],a['entry_id'])
  if 'pre_decision_occupancy' in a:
   for k in ('pre_decision_occupancy','slot_gate_reason'):check('slot_gate/'+k,a[k]==z[k],a['entry_id'])
   for k in ('remaining_Aplus_probability','expected_remaining_Aplus','training_B_median','training_B_p75'):close('slot_gate/'+k,a[k],z[k])
  if a['quantity']:
   for k in ('first_pass_quantity','water_fill_lots','funded_slot','slot_admission_index'):check('allocation/'+k,a[k]==z[k],a['entry_id'])
   for k in ('debit','equity_cap','target_utilization','batch_equity','batch_budget','recycled_cash_used'):check('allocation/'+k,F(a[k])==F(z[k]),a['entry_id'])
   close('allocation/desired',float(F(a['desired'])),float(z['desired']),1e-8)
 for a,z in zip(ts,pt):
  for k in ('entry_id','quantity','release_minute','source_minute','exit_kind'):check('SELL/'+k,a[k]==z[k],a['entry_id'])
  for k in ('debit','credit'):check('SELL/'+k,F(a[k])==F(z[k]),a['entry_id'])
 for a,z in zip(frames,pc):
  for k in ('cash','equity'):check('MTM/'+k,F(a[k])==F(z[k]),(a['session'],a['minute']))
  for k in ('concurrent','known_marks'):check('MTM/'+k,a[k]==z[k])
 for a,z in zip(intents,pi):
  for k in ('entry_id','quantity','minute','limit_up_status'):check('EOD/'+k,a[k]==z[k])
 returns=[]
 for a,z in zip(days,econ['daily_series']):
  check('daily/complete',a['complete'])
  for k in ('session','primary_chain','max_concurrent'):check('daily/'+k,a[k]==z[k])
  for k in ('starting_cash','ending_cash','cash_min','recycled_cash_used'):check('daily/'+k,F(a[k])==F(z[k]))
  r=float(F(a['ending_cash'])/F(a['starting_cash'])-1);returns.append(r);check('daily/return_exact',r==z['daily_return'])
 rolling=[float(F(days[i+19]['ending_cash'])/F(days[i]['starting_cash'])) for i in range(19)];check('rolling20/exact_series',rolling==[z['growth_multiple'] for z in econ['rolling20_windows']])
 peak=F(1000000);dd=F(0)
 for c in frames:peak=max(peak,F(c['equity']));dd=max(dd,(peak-F(c['equity']))/peak)
 sample=[c for c in frames if 540<=c['minute']<690 or 750<=c['minute']<930];util=[float(1-F(c['cash'])/F(c['equity'])) for c in sample]
 economic={'geometric_mean_daily_return':math.expm1(mean(math.log1p(x) for x in returns)),'arithmetic_mean_daily_return':mean(returns),'median_daily_return':median(returns),'rolling20_minimum':min(rolling),'rolling20_median':median(rolling),'rolling20_arithmetic_mean':mean(rolling),'rolling20_maximum':max(rolling),'final_equity':float(F(days[-1]['ending_cash'])),'total_return':float(F(days[-1]['ending_cash'])/1000000-1),'max_drawdown':float(dd),'utilization_mean':mean(util),'utilization_median':median(util),'time_utilization_ge80':mean(x>=.8 for x in util),'time_utilization_ge90':mean(x>=.9 for x in util),'cash_minimum':float(min(F(d['cash_min']) for d in days)),'turnover_cash_jpy':float(sum((F(t['credit'])+F(t['debit']) for t in ts),F(0))),'capital_recycling_used_jpy':float(sum((F(d['recycled_cash_used']) for d in days),F(0))),'funded_N':sum(d['quantity']>0 for d in ds),'avg_funded_per_session':len(ts)/38,'max_concurrent_actual':max(d['max_concurrent'] for d in days),'north_star_hit_N':sum(x>=2 for x in rolling),'valid_rolling20_window_N':len(rolling)}
 for k,v in economic.items():close('economic/'+k,v,econ[k],1e-8 if k in ('final_equity','cash_minimum') or k.endswith('_jpy') else 1e-12)
 check('economic/reasons',dict(Counter(d['reason'] for d in ds))==econ['reasons'])
 recomputed={}
 # Control is read-only ledger analysis, never replayed by any engine here.
 for arm,ad,at in [('Control',read(FROZEN/'UPWARD_STAIRCASE_V4_MAX3_DECISIONS.jsonl.gz'),read(FROZEN/'UPWARD_STAIRCASE_V4_MAX3_TRADES.jsonl.gz')),('v5',ds,ts)]:
  tm={t['entry_id']:t for t in at};compare_quality(quality(set(tm),tt,sm,tm),analysis[arm]['quality']);dm={d['entry_id']:d for d in ad};metrics={}
  for k,total in [(5,113),(10,47)]:
   cohort={i for i in sm if sm[i]['ML']>=1 and tt[i]['potential_return']>=k/100};cc=Counter(dm[i]['reason'] for i in cohort)
   met={'denominator':len(cohort),'funded':cc['FUNDED'],'conversion':cc['FUNDED']/len(cohort),'MAX3_miss':cc['MAX_POSITION_CAP'],'reserve_rejected':cc['SLOT_RESERVE_REJECT'],'Net_Slot_Miss':cc['MAX_POSITION_CAP']+cc['SLOT_RESERVE_REJECT'],'cash_lot_miss':cc['CASH_OR_LOT_CONSTRAINED'],'conservation':sum(cc.values())};metrics[f'U{k}']=met;check('conversion/denominator',len(cohort)==total);check('conversion/metrics',met==analysis[arm]['metrics'][f'U{k}'])
  if arm=='v5':slotmap={k:{d['entry_id'] for d in ad if d.get('funded_slot')==k} for k in (1,2,3)}
  else:
   slotmap={k:set() for k in (1,2,3)};batch=None;prior=0
   for d in ad:
    key=d['session'],d['minute']
    if batch!=key:batch=key;prior=0
    if d['reason']=='FUNDED':slotmap[len(d['held_before_batch'])+prior+1].add(d['entry_id']);prior+=1
  for k in (1,2,3):compare_quality(quality(slotmap[k],tt,sm,tm),analysis[arm]['slot_quality'][str(k)])
  for target,reason in [('B_funded','FUNDED'),('B_reserve_rejected','SLOT_RESERVE_REJECT')]:
   ids={d['entry_id'] for d in ad if sm[d['entry_id']]['rank']=='B' and d['reason']==reason};compare_quality(quality(ids,tt,sm,tm if reason=='FUNDED' else None),analysis[arm][target])
  recomputed[arm]=metrics
 gzsave(P/'INDEPENDENT_TRAINING_PREDICTIONS.jsonl.gz',trainpred);gzsave(P/'INDEPENDENT_V5_LEDGER.jsonl.gz',ds+ts+frames+days+intents)
 result={'mismatch_N':len(mismatches),'mismatch':mismatches,'check_N':sum(checks.values()),'checks':dict(checks),'independent_v5_replay_N':1,'Control_replay_N':0,'new_fit':0,'Primary_policy_replay_imports':0,'independent_training_inference_rows':len(trainpred),'monetary_ledger_tolerance':0,'quantities_and_decisions_tolerance':0,'floating_summary_tolerance':1e-12,'allocation_desired_and_money_summary_tolerance':1e-8,'economic':economic,'rank_pass_metrics':recomputed}
 save(OUT/'INDEPENDENT_AUDIT.json',result);print(json.dumps({'mismatch_N':len(mismatches),'check_N':sum(checks.values()),'first_mismatches':mismatches[:5]}),flush=True);assert not mismatches
if __name__=='__main__':main()
