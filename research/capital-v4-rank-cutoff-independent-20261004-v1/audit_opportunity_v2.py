"""Supplementary independent opportunity/rank audit from Fraction ledgers.
No Primary replay, analysis, or summarizer imports; no additional replay.
"""
from pathlib import Path
from collections import Counter,defaultdict
import gzip,json
W=Path(__file__).resolve().parents[3];P=W/'capital_v4_rank_cutoff_private';OUT=W/'repo/docs/evidence/capital-v4-rank-cutoff-independent-20261004-v1'
def read(p):return [json.loads(s) for s in gzip.open(p,'rt')]
def main():
 sm={r['entry_id']:r for r in read(W/'capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')};tt={r['entry_id']:r for r in read(W/'inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')};a=json.loads((OUT/'DIAGNOSTIC_ANALYSIS.json').read_text());audit=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text());checks=[]
 for arm in ('S_ONLY_MAX3','A_PLUS_MAX3','B_PLUS_MAX3'):
  ledger=read(P/f'{arm}_INDEPENDENT_LEDGER.jsonl.gz');ds=[x for x in ledger if 'reason' in x];frames=[x for x in ledger if 'known_marks' in x];trades=[x for x in ledger if 'credit' in x];fm={(c['session'],c['minute']):c for c in frames};sold=defaultdict(set)
  for t in trades:sold[sm[t['entry_id']]['session'],t['release_minute']].add(t['entry_id'])
  samples=[c for c in frames if 540<=c['minute']<690 or 750<=c['minute']<930]
  held={};batch=defaultdict(list);dm={d['entry_id']:d for d in ds}
  for d in ds:
   r=sm[d['entry_id']];day,t=r['session'],r['entry_minute'];prev=fm.get((day,t-1),{'known_marks':{}});held[d['entry_id']]=set(prev['known_marks'])-sold[day,t];batch[day,t].append(d)
  blocked=set()
  for rows in batch.values():
   eligible=[d for d in rows if d['reason'] in ('FUNDED','CASH_OR_LOT_CONSTRAINED','MAX_POSITION_CAP')]
   blocked.update(d['entry_id'] for i,d in enumerate(eligible) if i<3 and d['reason']=='MAX_POSITION_CAP' and held[d['entry_id']])
  opp={'rank_cutoff_reject_N':sum(d['reason'].startswith('RANK_CUTOFF_') for d in ds),'sessions_with_unused_MAX3_slot':len({c['session'] for c in samples if c['concurrent']<3}),'minute_samples_positions':{str(i):sum(c['concurrent']==i for c in samples) for i in range(4)}}
  for name,threshold in [('U5',.05),('U10',.10)]:
   ids={k for k in sm if tt[k]['potential_return']>=threshold};arrivals={k for k in ids if sm[k]['entry_minute']<920};missed={k for k in ids if dm[k]['quantity']==0}
   opp[name]={'later_arrived_slot_free_N':sum(len(held[k])<3 for k in arrivals),'later_arrived_slot_occupied_N':sum(len(held[k])==3 for k in arrivals),'missed_cutoff_N':sum(dm[k]['reason'].startswith('RANK_CUTOFF_') for k in ids),'missed_MAX3_N':sum(dm[k]['reason']=='MAX_POSITION_CAP' for k in ids),'HELD_SLOT_BLOCKED_WINNER_N':len(ids&blocked),'missed_reasons':dict(Counter(dm[k]['reason'] for k in missed))}
  checks.append({'kind':arm+'/opportunity_all_fields','PASS':opp==a['profiles'][arm]['opportunity']})
 for label,q,target in [('candidate',a['rank']['candidate'],a['rank']['candidate_monotonic']),('main_funded',a['rank']['main_B_PLUS_funded'],a['rank']['main_funded_monotonic'])]:
  strict={k:(q['S'][k]>q['A'][k]>q['B'][k] if k.startswith('U') else q['S'][k]<q['A'][k]<q['B'][k]) for k in ('U5_rate','U10_rate','below2_rate','loss0_rate')}
  status='RANK_QUALITY_MONOTONIC_STRONG' if sum(strict.values())==4 else 'RANK_QUALITY_MONOTONIC_PARTIAL' if any(strict.values()) else 'RANK_QUALITY_NOT_MONOTONIC'
  checks.append({'kind':label+'/strict_monotonic','PASS':strict==target['strict_checks'] and status==target['status'],'inputs_independently_recalculated_in_core_audit':audit['mismatch_N']==0})
 result={'checks':checks,'mismatch_N':sum(not r['PASS'] for r in checks),'additional_replay_count':0,'primary_imports':0,'interpretation_changes':0}
 with (OUT/'INDEPENDENT_OPPORTUNITY_AUDIT.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
 assert result['mismatch_N']==0;print(json.dumps(result))
if __name__=='__main__':main()
