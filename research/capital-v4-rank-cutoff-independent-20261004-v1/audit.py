"""Independent audit: imports only its own Fraction engine, never Primary code."""
from independent_engine import replay,read,actual,F,ROOT
from pathlib import Path
from statistics import mean,median
from collections import Counter
import json,math,gzip,hashlib
W=ROOT.parent;P=W/'capital_v4_rank_cutoff_private';OUT=ROOT/'docs/evidence/capital-v4-rank-cutoff-independent-20261004-v1';FROZEN=W/'capital_staircase_v4_private'
PROFILES=('S_ONLY_MAX3','A_PLUS_MAX3','B_PLUS_MAX3')
def main():
 saved=read(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz');sm={r['entry_id']:r for r in saved};teachers={r['entry_id']:r for r in read(W/'inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')};books={r['entry_id']:r for r in read(W/'inputs/v3/bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
 analysis=json.loads((OUT/'DIAGNOSTIC_ANALYSIS.json').read_text());checks=Counter();mismatch=[]
 def check(k,ok,detail=None):
  checks[k]+=1
  if not ok:mismatch.append({'kind':k,'detail':detail})
 def close(k,a,b,tol=1e-12):check(k,(a is None and b is None) or (a is not None and b is not None and abs(a-b)<=tol))
 def qual(ids,trades=None):
  ids=sorted(ids);n=len(ids);v=[teachers[k]['potential_return'] for k in ids]
  r=[float(F(trades[k]['credit'])/F(trades[k]['debit'])-1) if trades is not None else teachers[k]['realized_net_return'] for k in ids if (k in trades if trades is not None else teachers[k]['realized_net_return'] is not None)]
  out={'N':n,'realized_resolved_N':len(r),'realized_unresolved_N':n-len(r),'realized_mean':mean(r) if r else None,'realized_median':median(r) if r else None}
  for k,a,b in [('U2',.02,None),('U3',.03,None),('Medium',.03,.05),('U5',.05,None),('U10',.10,None),('below1',None,.01),('below2',None,.02),('below3',None,.03)]:
   count=sum((a is None or x>=a) and (b is None or x<b) for x in v);out[k+'_N']=count;out[k+'_rate']=count/n if n else None
  for k,test in [('PF1',lambda x:x>=.01),('positive',lambda x:x>0),('exact_zero',lambda x:x==0),('loss0',lambda x:x<=0),('tail1',lambda x:x<=-.01),('tail3',lambda x:x<=-.03)]:out[k+'_N']=sum(test(x) for x in r);out[k+'_rate']=out[k+'_N']/len(r) if r else None
  if trades is not None:out['actual_pnl_jpy']=float(sum((F(trades[k]['credit'])-F(trades[k]['debit']) for k in ids if k in trades),F(0)))
  return out
 def compare_quality(a,b):
  check('quality_fields',a.keys()==b.keys())
  for k,v in a.items():close('quality/'+k,v,b[k],1e-8 if k=='actual_pnl_jpy' else 1e-12)
 for rank in ('S','A','B','C'):compare_quality(qual({k for k in sm if sm[k]['rank']==rank}),analysis['rank']['candidate'][rank])
 independently={}
 for arm in PROFILES:
  ds,ts,frames,days,intents=replay(3,saved,books,arm);pd=read(P/f'{arm}_DECISIONS.jsonl.gz');pt=read(P/f'{arm}_TRADES.jsonl.gz');pc=read(P/f'{arm}_CURVE.jsonl.gz');pi=read(P/f'{arm}_INTENTS.jsonl.gz');econ=json.loads((P/f'{arm}_RESULT.json').read_text())
  check('decision_count',len(ds)==len(pd));check('trade_count',len(ts)==len(pt));check('frame_count',len(frames)==len(pc));check('intent_count',len(intents)==len(pi))
  for a,b in zip(ds,pd):
   for k in ('entry_id','reason','quantity'):check('decision/'+k,a[k]==b[k],a['entry_id'])
   if a['reason']=='FUNDED':
    for k in ('first_pass_quantity','water_fill_lots'):check('allocation/'+k,a[k]==b[k],a['entry_id'])
    for k in ('debit','equity_cap','target_utilization','batch_equity','batch_budget','recycled_cash_used'):check('allocation/'+k,F(a[k])==F(b[k]),a['entry_id'])
    close('allocation/desired',float(F(a['desired'])),float(b['desired']),1e-8)
  for a,b in zip(ts,pt):
   for k in ('entry_id','quantity','release_minute','source_minute','exit_kind'):check('sell/'+k,a[k]==b[k],a['entry_id'])
   for k in ('debit','credit'):check('sell/'+k,F(a[k])==F(b[k]),a['entry_id'])
  for a,b in zip(frames,pc):
   for k in ('cash','equity'):check('MTM/'+k,F(a[k])==F(b[k]),(a['session'],a['minute']))
   check('MTM/concurrent',a['concurrent']==b['concurrent']);check('MTM/known_marks',a['known_marks']==b['known_marks'])
  for a,b in zip(intents,pi):
   for k in ('entry_id','quantity','minute','limit_up_status'):check('EOD_intent/'+k,a[k]==b[k])
  rr=[]
  for a,b in zip(days,econ['daily_series']):
   for k in ('session','primary_chain','max_concurrent'):check('day/'+k,a[k]==b[k])
   for k in ('starting_cash','ending_cash','cash_min','recycled_cash_used'):check('day/'+k,F(a[k])==F(b[k]))
   check('complete',a['complete']);ret=float(F(a['ending_cash'])/F(a['starting_cash'])-1);rr.append(ret);check('daily_exact',ret==b['daily_return'])
  rolls=[float(F(days[i+19]['ending_cash'])/F(days[i]['starting_cash'])) for i in range(len(days)-19)]
  check('rolling20_series',rolls==[r['growth_multiple'] for r in econ['rolling20_windows']])
  peak=F(1000000);dd=F(0)
  for c in frames:peak=max(peak,F(c['equity']));dd=max(dd,(peak-F(c['equity']))/peak)
  sample=[c for c in frames if 540<=c['minute']<690 or 750<=c['minute']<930];util=[float(1-F(c['cash'])/F(c['equity'])) for c in sample]
  em={'geometric_mean_daily_return':math.expm1(mean(math.log1p(x) for x in rr)),'arithmetic_mean_daily_return':mean(rr),'median_daily_return':median(rr),'rolling20_minimum':min(rolls),'rolling20_median':median(rolls),'rolling20_arithmetic_mean':mean(rolls),'rolling20_maximum':max(rolls),'final_equity':float(F(days[-1]['ending_cash'])),'total_return':float(F(days[-1]['ending_cash'])/1000000-1),'max_drawdown':float(dd),'utilization_mean':mean(util),'utilization_median':median(util),'time_utilization_ge80':mean(x>=.8 for x in util),'time_utilization_ge90':mean(x>=.9 for x in util),'cash_minimum':float(min(F(d['cash_min']) for d in days)),'turnover_cash_jpy':float(sum((F(t['credit'])+F(t['debit']) for t in ts),F(0))),'capital_recycling_used_jpy':float(sum((F(d['recycled_cash_used']) for d in days),F(0))),'funded_N':sum(d['quantity']>0 for d in ds),'avg_funded_per_session':len(ts)/38,'max_concurrent_actual':max(d['max_concurrent'] for d in days),'north_star_hit_N':sum(x>=2 for x in rolls),'north_star_hit_rate':sum(x>=2 for x in rolls)/len(rolls),'valid_rolling20_window_N':len(rolls)}
  for k,v in em.items():close('economic/'+k,v,econ[k],1e-8 if k.endswith('_jpy') or k in ('final_equity','cash_minimum') else 1e-12)
  check('reasons',dict(Counter(d['reason'] for d in ds))==econ['reasons']);check('day_sign_counts',{k:sum(test(x) for x in rr) for k,test in [('positive',lambda x:x>0),('negative',lambda x:x<0),('zero',lambda x:x==0)]}==econ['daily_sign_counts'])
  tm={t['entry_id']:t for t in ts};funded=set(tm);target=analysis['profiles'][arm];compare_quality(qual(funded,tm),target['quality'])
  for rank in ('S','A','B','C'):compare_quality(qual({k for k in funded if sm[k]['rank']==rank},tm),target['funded_rank_quality'][rank])
  for name,threshold,ceiling,total in [('U2',.02,None,432),('U3',.03,None,297),('Medium',.03,.05,127),('U5',.05,None,170),('U10',.10,None,67)]:
   cohort={k for k in sm if teachers[k]['potential_return']>=threshold and (ceiling is None or teachers[k]['potential_return']<ceiling)};count=len(cohort&funded)
   check('capture_total',len(cohort)==total);check('capture_count',target['capture_precision'][name]['funded_N']==count);close('capture',count/total,target['capture_precision'][name]['capture']);close('precision',count/len(funded) if funded else None,target['capture_precision'][name]['precision'])
  bounds=[(None,.01),(.01,.02),(.02,.03),(.03,.04),(.04,.05),(.05,.10),(.10,None)]
  for label,(a,b) in zip(('<1','1-<2','2-<3','3-<4','4-<5','5-<10','>=10'),bounds):
   ids={k for k in funded if (a is None or teachers[k]['potential_return']>=a) and (b is None or teachers[k]['potential_return']<b)};q=qual(ids,tm);compare_quality(q,{k:target['buckets'][label][k] for k in q});close('bucket_composition',len(ids)/len(funded) if funded else None,target['buckets'][label]['composition'])
  independently[arm]={'economic':em,'quality':qual(funded,tm),'independent_decisions':len(ds),'independent_frames':len(frames)}
  with (P/f'{arm}_INDEPENDENT_LEDGER.jsonl.gz').open('xb') as f:f.write(gzip.compress(('\n'.join(json.dumps(x,sort_keys=True) for x in ds+ts+frames+days+intents)+'\n').encode(),mtime=0))
  if arm=='B_PLUS_MAX3':
   main=read(FROZEN/'UPWARD_STAIRCASE_V4_MAX3_DECISIONS.jsonl.gz');check('B_PLUS_funded_ID_qty',[(d['entry_id'],d['quantity']) for d in ds if d['quantity']]>[] and [(d['entry_id'],d['quantity']) for d in ds if d['quantity']]==[(d['entry_id'],d['quantity']) for d in main if d['quantity']]);check('B_PLUS_final_exact',F(days[-1]['ending_cash'])==F('1433740.25'))
 result={'mismatch_N':len(mismatch),'mismatch':mismatch,'checks':dict(checks),'check_N':sum(checks.values()),'independent_replays':3,'new_fit':0,'no_primary_replay_or_summarizer_import':True,'tolerances':{'monetary_ledger':0,'quantity':0,'daily_series':0,'rolling20_series':0,'metric_float':1e-12,'allocation_desired_and_money_summaries':1e-8},'profiles':independently}
 with (OUT/'INDEPENDENT_AUDIT.json').open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps({'mismatch_N':len(mismatch),'check_N':sum(checks.values())}));assert not mismatch
if __name__=='__main__':main()
