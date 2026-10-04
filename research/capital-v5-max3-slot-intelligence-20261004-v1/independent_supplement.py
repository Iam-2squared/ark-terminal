"""Read-only Control economics, buckets, reservation and opportunity audit."""
from independent_audit import read,F,quality,ROOT
from statistics import mean,median
from collections import Counter
from pathlib import Path
import json,math
W=ROOT.parent;S=W/'source_main';P=W/'capital_v5_slot_private';OUT=ROOT/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1';PROFILE='CAPITAL_MAX3_SLOT_RESERVE_V1'
def main():
 sm={r['entry_id']:r for r in read(S/'capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')};tt={r['entry_id']:r for r in read(S/'inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')};target=json.loads((OUT/'SLOT_QUALITY_AND_RESERVATION.json').read_text());op=json.loads((OUT/'OPPORTUNITY_AND_ORACLE_GAP.json').read_text());checks=Counter();mismatch=[];outputs={}
 def check(k,ok):
  checks[k]+=1
  if not ok:mismatch.append(k)
 def close(k,a,b,tol=1e-12):check(k,(a is None and b is None) or (a is not None and b is not None and abs(a-b)<=tol))
 def compare_quality(a,b):
  for k,v in a.items():
   if isinstance(v,dict):check('quality/'+k,v==b[k])
   else:close('quality/'+k,v,b[k],1e-8 if k=='actual_pnl_jpy' else 1e-12)
 def bucket(v):
  return next((label for bound,label in [(.01,'<1'),(.02,'1-<2'),(.03,'2-<3'),(.04,'3-<4'),(.05,'4-<5'),(.10,'5-<10')] if v<bound),'>=10')
 for arm,folder,base in [('Control',S/'capital_staircase_v4_private','UPWARD_STAIRCASE_V4_MAX3'),('v5',P,PROFILE)]:
  ds=read(folder/f'{base}_DECISIONS.jsonl.gz');ts=read(folder/f'{base}_TRADES.jsonl.gz');frames=read(folder/f'{base}_CURVE.jsonl.gz');economic=json.loads((folder/f'{base}_RESULT.json').read_text());tm={r['entry_id']:r for r in ts};funded=set(tm);dm={d['entry_id']:d for d in ds}
  for label in ('<1','1-<2','2-<3','3-<4','4-<5','5-<10','>=10'):
   ids={k for k in funded if bucket(tt[k]['potential_return'])==label};compare_quality(quality(ids,tt,sm,tm),target[arm]['entry_high_buckets'][label]);check('bucket/candidate_count',sum(bucket(tt[k]['potential_return'])==label for k in sm)==target[arm]['entry_high_buckets'][label]['candidate_N'])
  opp={}
  for winner,threshold,total in [('U5',.05,113),('U10',.10,47)]:
   cohort={k for k in sm if sm[k]['ML']>=1 and tt[k]['potential_return']>=threshold};batch=None;previous=[];index=0;records=[];first_funded={}
   for d in ds:
    if d['reason']=='FUNDED':first_funded.setdefault(d['session'],d['minute'])
   for d in ds:
    key=d['session'],d['minute']
    if key!=batch:batch=key;previous=[];index=0
    if d['entry_id'] in cohort:
     held=d['held_before_batch']+previous;records.append({'slot_free':len(held)<3,'held_block':d['reason']=='MAX_POSITION_CAP' and bool(d['held_before_batch']) and index<3,'reason':d['reason'],'later':d['minute']>first_funded.get(d['session'],9999)})
    if d['admission'] and d['minute']<920:index+=1
    if d['reason']=='FUNDED':previous.append(d['entry_id'])
   result={'all_rank_pass_arrivals_N':len(records),'arrived_slot_free_N':sum(x['slot_free'] for x in records),'arrived_slot_occupied_N':sum(not x['slot_free'] for x in records),'later_arrived_slot_free_N':sum(x['slot_free'] and x['later'] for x in records),'later_arrived_slot_occupied_N':sum(not x['slot_free'] and x['later'] for x in records),'HELD_SLOT_BLOCKED_N':sum(x['held_block'] for x in records),'RESERVE_REJECTED_N':sum(x['reason']=='SLOT_RESERVE_REJECT' for x in records),'cash_lot_missed_N':sum(x['reason']=='CASH_OR_LOT_CONSTRAINED' for x in records),'MAX3_missed_N':sum(x['reason']=='MAX_POSITION_CAP' for x in records)}
   check('opportunity/'+winner,result==op['opportunity'][arm][winner]);opp[winner]=result
  reservation=read(P/f'{arm}_RESERVATION_EVALUATION_JOIN.jsonl.gz');check('reservation/B_count',len(reservation)==sum(r['rank']=='B' for r in sm.values()))
  for r in reservation:
   d=dm[r['entry_id']];teacher=tt[r['entry_id']]
   check('reservation/decision',r['decision']==d['reason']);check('reservation/teacher',r['U5']==(teacher['potential_return']>=.05) and r['U10']==(teacher['potential_return']>=.10));check('reservation/bucket',r['bucket']==bucket(teacher['potential_return']))
  days=[]
  for day in sorted({r['session'] for r in frames}):
   ff=[r for r in frames if r['session']==day];check('daily/flat_EOD',ff[-1]['concurrent']==0)
   ending=F(ff[-1]['cash']);profit=sum((F(t['credit'])-F(t['debit']) for t in ts if t['session']==day),F(0));opening=ending-profit;days.append((day,opening,ending,float(ending/opening-1)))
  for a,b in zip(days,economic['daily_series']):
   check('saved_Control_or_v5/daily',a[0]==b['session'] and a[1]==F(b['starting_cash']) and a[2]==F(b['ending_cash']) and a[3]==b['daily_return'])
  returns=[d[3] for d in days];rolling=[float(days[i+19][2]/days[i][1]) for i in range(19)];peak=F(1000000);dd=F(0)
  for c in frames:peak=max(peak,F(c['equity']));dd=max(dd,(peak-F(c['equity']))/peak)
  sample=[c for c in frames if 540<=c['minute']<690 or 750<=c['minute']<930];u=[float(1-F(c['cash'])/F(c['equity'])) for c in sample]
  metrics={'geometric_mean_daily_return':math.expm1(mean(math.log1p(r) for r in returns)),'arithmetic_mean_daily_return':mean(returns),'median_daily_return':median(returns),'rolling20_minimum':min(rolling),'rolling20_median':median(rolling),'rolling20_arithmetic_mean':mean(rolling),'rolling20_maximum':max(rolling),'final_equity':float(days[-1][2]),'max_drawdown':float(dd),'utilization_mean':mean(u),'utilization_median':median(u),'time_utilization_ge80':mean(v>=.8 for v in u),'time_utilization_ge90':mean(v>=.9 for v in u),'turnover_cash_jpy':float(sum((F(t['credit'])+F(t['debit']) for t in ts),F(0))),'cash_minimum':float(min(F(f['cash']) for f in frames))}
  for k,v in metrics.items():close('economic/'+arm+'/'+k,v,economic[k],1e-8 if k in ('final_equity','cash_minimum') or k.endswith('_jpy') else 1e-12)
  outputs[arm]={'economic':metrics,'daily_returns':returns,'rolling20':rolling,'opportunity':opp}
 save={'mismatch_N':len(mismatch),'mismatch':mismatch,'check_N':sum(checks.values()),'checks':dict(checks),'Control_replay':0,'Primary_imports':0,'results':outputs}
 with (OUT/'INDEPENDENT_SUPPLEMENT.json').open('x') as f:json.dump(save,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps({'mismatch_N':len(mismatch),'checks':sum(checks.values())}));assert not mismatch
if __name__=='__main__':main()
