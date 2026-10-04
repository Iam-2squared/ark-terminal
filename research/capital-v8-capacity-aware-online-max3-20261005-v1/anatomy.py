"""Saved v7 ledger diagnostic only, before any new policy outcome."""
from control import *
from collections import Counter
from statistics import mean,median
import csv,io
def dist(a):
 s=sorted(a);return {'N':len(s),'min':min(s),'median':median(s),'mean':mean(s),'max':max(s)} if s else {'N':0}
def main():
 runtime={r['entry_id']:r for r in rows(PIN/'RANK_NATIVE_RUNTIME.jsonl.gz')};teacher={r['entry_id']:r for r in rows(INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz')};regret=rows(PIN/'RANK_REGRET_LEDGER.jsonl.gz');records=[]
 for z in regret:
  if z['profile']!='RANK_NATIVE_GREEDY_MAX3' or not z['U5'] or z['miss_reason']!='MAX3_FULL' or not z['higher_than_min_held_pP']:continue
  r=runtime[z['entry_id']];positions=[];mt=teacher[r['entry_id']]
  for p in z['held_positions']:
   q=runtime[p['entry_id']];tt=teacher[q['entry_id']];potential=tt['potential_return'];release=tt['release_minute']
   positions.append(p|{'r':q['r'],'U5':tt['label_bigwinner5'],'U10':tt['label_bigwinner10'],'below2':potential<.02,'below3':potential<.03,'realized_net_return':tt['realized_net_return'],'release_minute':release,'age_wall_minutes':r['entry_minute']-q['entry_minute'],'held_remaining_wall_minutes':max(0,release-r['entry_minute']),'actual_interval_overlap_minutes':max(0,min(release,mt['release_minute'])-r['entry_minute'])})
  low=min(positions,key=lambda p:(p['pP'],p['entry_minute'],p['symbol'],p['entry_id']))
  records.append({'missed_entry_id':r['entry_id'],'missed_pP':r['pP'],'missed_r':r['r'],'U5':z['U5'],'U10':z['U10'],'arrival_minute':r['entry_minute'],'entry_hour':r['entry_minute']//60,'held_N':len(positions),'held_positions':positions,'minimum_held_entry_id':low['entry_id'],'minimum_held_pP':low['pP'],'minimum_held_r':low['r'],'pP_gap':r['pP']-low['pP'],'minimum_blocker':low,'evaluation_only':True})
 assert len(records)==51 and all(z['held_N']==3 for z in records)
 mins=[z['minimum_blocker'] for z in records];agg={'blocked_U5_events':51,'blocked_U10_events':sum(z['U10'] for z in records),'minimum_blocker_unique_N':len({p['entry_id'] for p in mins}),'minimum_blocker_below2_events':sum(p['below2'] for p in mins),'minimum_blocker_U5_events':sum(p['U5'] for p in mins),'minimum_blocker_U10_events':sum(p['U10'] for p in mins),'minimum_blocker_rank_decile':dict(Counter(min(10,max(1,int(p['r']*10)+1)) for p in mins)),'blocker_age_wall_minutes':dist([p['age_wall_minutes'] for p in mins]),'actual_overlap_wall_minutes':dist([p['actual_interval_overlap_minutes'] for p in mins]),'pP_gap':dist([z['pP_gap'] for z in records]),'arrival_hour':dict(Counter(z['entry_hour'] for z in records)),'occupancy_composition':dict(Counter(tuple(sorted(p['band'] for p in z['held_positions'])) for z in records))}
 agg['occupancy_composition']={','.join(k):v for k,v in agg['occupancy_composition'].items()}
 save(OUT/'BLOCKED_WINNER_ANATOMY.json',{'exact_jst':now(),'source_sha256':sha(PIN/'RANK_REGRET_LEDGER.jsonl.gz'),'aggregate':agg,'records':records,'minimum_blocker_is_diagnostic_not_unique_causal_responsibility':True,'policy_spec_changed_from_anatomy':False})
 buff=io.StringIO();columns=['missed_entry_id','missed_pP','missed_r','U5','U10','arrival_minute','entry_hour','held_N','minimum_held_entry_id','minimum_held_pP','minimum_held_r','pP_gap','held_positions'];writer=csv.DictWriter(buff,fieldnames=columns);writer.writeheader()
 for z in records:writer.writerow({k:json.dumps(z[k],ensure_ascii=False) if k=='held_positions' else z[k] for k in columns})
 with (OUT/'BLOCKED_WINNER_ANATOMY.csv').open('x') as f:f.write(buff.getvalue())
 checkpoint('D3_BLOCKED_WINNER_ANATOMY','SAVED_51_BLOCKED_WINNERS_ANALYZED',['saved A1 regret only','all held positions / minimum blocker'],agg,'No policy change; precommit one pP-only clairvoyant solve')
 print(json.dumps(agg,ensure_ascii=False))
if __name__=='__main__':main()
