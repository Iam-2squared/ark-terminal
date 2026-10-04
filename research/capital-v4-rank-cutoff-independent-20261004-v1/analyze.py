"""Post-replay outcome-only diagnostics. Not imported by decision engines."""
from common import *
from collections import Counter,defaultdict
from statistics import mean,median
from decimal import Decimal as D
import csv
BUCKETS=('<1','1-<2','2-<3','3-<4','4-<5','5-<10','>=10')
def bucket(v):
 for t,b in zip((.01,.02,.03,.04,.05,.10),BUCKETS):
  if v<t:return b
 return '>=10'
def quality(ids,tt,tm=None):
 ids=sorted(ids);n=len(ids);v=[tt[k]['potential_return'] for k in ids]
 realized=[(tm[k]['net_return'] if tm is not None else tt[k]['realized_net_return']) for k in ids if (k in tm if tm is not None else tt[k]['realized_net_return'] is not None)]
 q={'N':n,'realized_resolved_N':len(realized),'realized_unresolved_N':n-len(realized),'realized_mean':mean(realized) if realized else None,'realized_median':median(realized) if realized else None}
 predicates={'U2':lambda x:x>=.02,'U3':lambda x:x>=.03,'Medium':lambda x:.03<=x<.05,'U5':lambda x:x>=.05,'U10':lambda x:x>=.10,'below1':lambda x:x<.01,'below2':lambda x:x<.02,'below3':lambda x:x<.03}
 for k,f in predicates.items():q[k+'_N']=sum(f(x) for x in v);q[k+'_rate']=q[k+'_N']/n if n else None
 for k,f in {'PF1':lambda x:x>=.01,'positive':lambda x:x>0,'exact_zero':lambda x:x==0,'loss0':lambda x:x<=0,'tail1':lambda x:x<=-.01,'tail3':lambda x:x<=-.03}.items():q[k+'_N']=sum(f(x) for x in realized);q[k+'_rate']=q[k+'_N']/len(realized) if realized else None
 if tm is not None:q['actual_pnl_jpy']=float(sum((D(tm[k]['pnl']) for k in ids if k in tm),D(0)))
 return q
def monotonic(q):
 checks={k:all(q[a][k] is not None and q[b][k] is not None and (q[a][k]>q[b][k] if direction=='down' else q[a][k]<q[b][k]) for a,b in [('S','A'),('A','B')]) for k,direction in [('U5_rate','down'),('U10_rate','down'),('below2_rate','up'),('loss0_rate','up')]}
 return {'status':'RANK_QUALITY_MONOTONIC_STRONG' if all(checks.values()) else 'RANK_QUALITY_MONOTONIC_PARTIAL' if any(checks.values()) else 'RANK_QUALITY_NOT_MONOTONIC','strict_checks':checks}
def main():
 assert json.loads((OUT/'B_PLUS_IDENTITY.json').read_text())['mismatch']==[]
 sm={r['entry_id']:r for r in rows(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')};tt={r['entry_id']:r for r in rows(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')}
 sets={f'U{k}':{key for key in sm if tt[key]['potential_return']>=k/100} for k in (2,3,5,10)};sets['Medium']=sets['U3']-sets['U5']
 ranksets={r:{k for k in sm if sm[k]['rank']==r} for r in ('S','A','B','C')}
 candidate={r:quality(ids,tt) for r,ids in ranksets.items()};profiles={};oppledger=[];dailycsv=[];rollingcsv=[]
 for arm in PROFILES:
  ds=rows(PRIVATE/f'{arm}_DECISIONS.jsonl.gz');ts=rows(PRIVATE/f'{arm}_TRADES.jsonl.gz');cs=rows(PRIVATE/f'{arm}_CURVE.jsonl.gz');tm={t['entry_id']:t for t in ts};dm={d['entry_id']:d for d in ds};funded=set(tm)
  econ=json.loads((PRIVATE/f'{arm}_RESULT.json').read_text());q=quality(funded,tt,tm)
  cap={k:{'total_N':len(ids),'funded_N':len(funded&ids),'capture':len(funded&ids)/len(ids),'precision':len(funded&ids)/len(funded) if funded else None} for k,ids in sets.items()}
  br={b:{'total_candidate_N':sum(bucket(tt[k]['potential_return'])==b for k in sm),'composition':sum(bucket(tt[k]['potential_return'])==b for k in funded)/len(funded) if funded else None,**quality({k for k in funded if bucket(tt[k]['potential_return'])==b},tt,tm)} for b in BUCKETS}
  rq={r:quality(funded&ids,tt,tm) for r,ids in ranksets.items()}
  samples=[c for c in cs if 540<=c['minute']<690 or 750<=c['minute']<930]
  batches=defaultdict(list)
  for d in ds:batches[d['session'],d['minute']].append(d)
  heldblocked=set()
  for batch in batches.values():
   eligible=[d for d in batch if d['reason'] in ('FUNDED','CASH_OR_LOT_CONSTRAINED','MAX_POSITION_CAP')]
   for i,d in enumerate(eligible):
    if d['reason']=='MAX_POSITION_CAP' and d['held_before_batch'] and i<3:heldblocked.add(d['entry_id'])
  opp={'rank_cutoff_reject_N':sum(d['reason'].startswith('RANK_CUTOFF_') for d in ds),'sessions_with_unused_MAX3_slot':len({c['session'] for c in samples if c['concurrent']<3}),'minute_samples_positions':{str(i):sum(c['concurrent']==i for c in samples) for i in range(4)}}
  for name in ('U5','U10'):
   ids=sets[name];arrivals=[d for d in ds if d['entry_id'] in ids and d['minute']<920]
   opp[name]={'later_arrived_slot_free_N':sum(len(d['held_before_batch'])<3 for d in arrivals),'later_arrived_slot_occupied_N':sum(len(d['held_before_batch'])==3 for d in arrivals),'missed_cutoff_N':sum(dm[k]['reason'].startswith('RANK_CUTOFF_') for k in ids),'missed_MAX3_N':sum(dm[k]['reason']=='MAX_POSITION_CAP' for k in ids),'HELD_SLOT_BLOCKED_WINNER_N':len(ids&heldblocked),'missed_reasons':dict(Counter(dm[k]['reason'] for k in ids-funded))}
   oppledger += [{'profile':arm,'entry_id':d['entry_id'],'winner':name,'held_before_batch':d['held_before_batch'],'slot_free':len(d['held_before_batch'])<3,'reason':d['reason'],'HELD_SLOT_BLOCKED_WINNER':d['entry_id'] in heldblocked} for d in arrivals]
  liquidity={reason:quality({k for k in funded if sm[k]['liquidity']['reason']==reason},tt,tm) for reason in ('LIQUIDITY_ELIGIBLE','EXTREME_ILLIQUIDITY_REJECT','LIQUIDITY_UNKNOWN')}
  profiles[arm]={'economic':econ,'quality':q,'capture_precision':cap,'buckets':br,'funded_rank_quality':rq,'rank_monotonic':monotonic(rq),'opportunity':opp,'liquidity':liquidity,'liquidity_reject_N':sum('LIQUIDITY' in d['reason'] for d in ds)}
  dailycsv += [{'profile':arm,**{k:d[k] for k in ('session','starting_cash','ending_cash','daily_return','max_concurrent')}} for d in econ['daily_series']]
  rollingcsv += [{'profile':arm,**w} for w in econ['rolling20_windows']]
 rank={'candidate':candidate,'candidate_monotonic':monotonic(candidate),'main_B_PLUS_funded':profiles['B_PLUS_MAX3']['funded_rank_quality'],'main_funded_monotonic':profiles['B_PLUS_MAX3']['rank_monotonic'],'per_profile_funded':{p:profiles[p]['funded_rank_quality'] for p in PROFILES},'strict_definition':'All four criteria both adjacent pairs strict: U5/U10 S>A>B, below2/loser S<A<B; all=STRONG, some=PARTIAL, none=NOT_MONOTONIC. Empty rank prevents strict check.'}
 save(OUT/'RANK_QUALITY.json',rank);checkpoint('R6_RANK_QUALITY_MONOTONICITY','RANK_QUALITY_FIXED',{'candidate':rank['candidate_monotonic'],'main_funded':rank['main_funded_monotonic']})
 save(OUT/'DIAGNOSTIC_ANALYSIS.json',{'profiles':profiles,'rank':rank,'interpretation':'Diagnostic only; no winner selected or promoted.','Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','Safety':SAFETY})
 gzwrite(PRIVATE/'OPPORTUNITY_LEDGER.jsonl.gz',oppledger)
 for name,data in [('DAILY.csv',dailycsv),('ROLLING20.csv',rollingcsv)]:
  with (OUT/name).open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
 checkpoint('R7_CAPTURE_PRECISION_OPPORTUNITY_AUDIT','CAPTURE_PRECISION_OPPORTUNITY_FIXED',{p:{k:profiles[p][k] for k in ('quality','capture_precision','opportunity')} for p in PROFILES})
 print(json.dumps({p:{'funded':profiles[p]['quality']['N'],'capture_precision':profiles[p]['capture_precision'],'opportunity':profiles[p]['opportunity']} for p in PROFILES}))
if __name__=='__main__':main()
