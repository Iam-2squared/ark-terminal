"""Post-replay evaluation-only joins. No runtime policy imports this module."""
from common import *
from decimal import Decimal as D
from statistics import mean,median
from collections import Counter,defaultdict
import csv
BUCKETS=('<1','1-<2','2-<3','3-<4','4-<5','5-<10','>=10')
def bucket(v):
 for t,b in zip((.01,.02,.03,.04,.05,.10),BUCKETS):
  if v<t:return b
 return '>=10'
def quality(ids,tt,sm,tm=None):
 ids=sorted(ids);n=len(ids);values=[tt[k]['potential_return'] for k in ids]
 realized=[float(D(tm[k]['credit'])/D(tm[k]['debit'])-1) if tm else tt[k]['realized_net_return'] for k in ids if (k in tm if tm else tt[k]['realized_net_return'] is not None)]
 q={'N':n,'rank_counts':dict(Counter(sm[k]['rank'] for k in ids)),'realized_resolved_N':len(realized),'realized_unresolved_N':n-len(realized),'realized_mean':mean(realized) if realized else None,'realized_median':median(realized) if realized else None}
 for name,predicate in [('U2',lambda x:x>=.02),('U3',lambda x:x>=.03),('Medium',lambda x:.03<=x<.05),('U5',lambda x:x>=.05),('U10',lambda x:x>=.10),('below2',lambda x:x<.02),('below3',lambda x:x<.03)]:
  q[name+'_N']=sum(predicate(x) for x in values);q[name+'_rate']=q[name+'_N']/n if n else None
 for name,predicate in [('PF1',lambda x:x>=.01),('positive',lambda x:x>0),('loser',lambda x:x<=0)]:
  q[name+'_N']=sum(predicate(x) for x in realized);q[name+'_rate']=q[name+'_N']/len(realized) if realized else None
 if tm is not None:q['actual_pnl_jpy']=float(sum((D(tm[k]['credit'])-D(tm[k]['debit']) for k in ids if k in tm),D(0)))
 return q
def actual_occupancy(decisions):
 result={};batch=None;earlier=[];rankpass_index=0
 for d in decisions:
  key=(d['session'],d['minute'])
  if key!=batch:batch=key;earlier=[];rankpass_index=0
  result[d['entry_id']]={'actual_predecision_open_IDs':d['held_before_batch']+earlier,'batch_rankpass_index':rankpass_index}
  if d['admission'] and d['minute']<920:rankpass_index+=1
  if d['reason']=='FUNDED':earlier.append(d['entry_id'])
 return result
def arm_analysis(ds,ts,tt,sm,control=False):
 tm={r['entry_id']:r for r in ts};funded=set(tm);occupancy=actual_occupancy(ds)
 slots=defaultdict(set)
 for d in ds:
  if d['reason']!='FUNDED':continue
  slot=len(occupancy[d['entry_id']]['actual_predecision_open_IDs'])+1
  assert 1<=slot<=3
  if not control:assert slot==d['funded_slot']
  slots[slot].add(d['entry_id'])
 metrics={}
 for k,denom in [(5,113),(10,47)]:
  cohort={i for i,r in sm.items() if r['admission'] and tt[i]['potential_return']>=k/100}
  assert len(cohort)==denom
  counts=dict(Counter(d['reason'] for d in ds if d['entry_id'] in cohort));F=counts.get('FUNDED',0);M=counts.get('MAX_POSITION_CAP',0);R=counts.get('SLOT_RESERVE_REJECT',0);C=counts.get('CASH_OR_LOT_CONSTRAINED',0)
  assert F+M+R+C==denom,counts
  metrics[f'U{k}']={'denominator':denom,'funded':F,'conversion':F/denom,'MAX3_miss':M,'reserve_rejected':R,'Net_Slot_Miss':M+R,'cash_lot_miss':C,'conservation':F+M+R+C}
 reservation=[]
 for d in ds:
  key=d['entry_id'];r=sm[key]
  if r['rank']!='B':continue
  reservation.append({'timestamp':r['entry_timestamp'],'entry_id':key,'ML':r['ML'],'rank':'B','pre_decision_occupancy':d.get('pre_decision_occupancy'),**occupancy[key],
   'training_B_median':d.get('training_B_median'),'training_B_p75':d.get('training_B_p75'),'remaining_Aplus_probability':d.get('remaining_Aplus_probability'),'expected_remaining_Aplus':d.get('expected_remaining_Aplus'),
   'decision':d['reason'],'reason':d.get('slot_gate_reason',d['reason']),'quantity':d['quantity'],'U3':tt[key]['potential_return']>=.03,'U5':tt[key]['potential_return']>=.05,'U10':tt[key]['potential_return']>=.10,'bucket':bucket(tt[key]['potential_return']),'potential_return':tt[key]['potential_return'],'realized_net_return_evaluation_only':tt[key]['realized_net_return']})
 B_funded={d['entry_id'] for d in ds if sm[d['entry_id']]['rank']=='B' and d['reason']=='FUNDED'};B_rejected={d['entry_id'] for d in ds if sm[d['entry_id']]['rank']=='B' and d['reason']=='SLOT_RESERVE_REJECT'}
 out={'quality':quality(funded,tt,sm,tm),'metrics':metrics,'slot_quality':{str(k):quality(slots[k],tt,sm,tm) for k in (1,2,3)},'B_funded':quality(B_funded,tt,sm,tm),'B_reserve_rejected':quality(B_rejected,tt,sm),'reservation_reason_counts':dict(Counter(d['reason'] for d in reservation if d['decision']=='SLOT_RESERVE_REJECT')),
 'entry_high_buckets':{b:{'candidate_N':sum(bucket(tt[k]['potential_return'])==b for k in sm),**quality({k for k in funded if bucket(tt[k]['potential_return'])==b},tt,sm,tm)} for b in BUCKETS}}
 return out,reservation,occupancy
def opportunity(ds,tt,sm,occ):
 ledger=[];out={}
 first_funded={day:min(d['minute'] for d in ds if d['session']==day and d['reason']=='FUNDED') for day in {d['session'] for d in ds} if any(d['session']==day and d['reason']=='FUNDED' for d in ds)}
 for k in (5,10):
  records=[]
  for d in ds:
   i=d['entry_id']
   if not sm[i]['admission'] or tt[i]['potential_return']<k/100:continue
   x={'entry_id':i,'session':d['session'],'minute':d['minute'],'winner':f'U{k}','reason':d['reason'],'slot_free_before_candidate':len(occ[i]['actual_predecision_open_IDs'])<3,'actual_predecision_open_IDs':occ[i]['actual_predecision_open_IDs'],'held_from_earlier_batch_IDs':d['held_before_batch'],
    'HELD_SLOT_BLOCKED':d['reason']=='MAX_POSITION_CAP' and bool(d['held_before_batch']) and occ[i]['batch_rankpass_index']<3,'later_than_first_funded_entry':d['minute']>first_funded.get(d['session'],9999)}
   records.append(x);ledger.append(x)
  later=[z for z in records if z['later_than_first_funded_entry']]
  out[f'U{k}']={'all_rank_pass_arrivals_N':len(records),'arrived_slot_free_N':sum(z['slot_free_before_candidate'] for z in records),'arrived_slot_occupied_N':sum(not z['slot_free_before_candidate'] for z in records),'later_arrived_slot_free_N':sum(z['slot_free_before_candidate'] for z in later),'later_arrived_slot_occupied_N':sum(not z['slot_free_before_candidate'] for z in later),'HELD_SLOT_BLOCKED_N':sum(z['HELD_SLOT_BLOCKED'] for z in records),'RESERVE_REJECTED_N':sum(z['reason']=='SLOT_RESERVE_REJECT' for z in records),'cash_lot_missed_N':sum(z['reason']=='CASH_OR_LOT_CONSTRAINED' for z in records),'MAX3_missed_N':sum(z['reason']=='MAX_POSITION_CAP' for z in records)}
 return out,ledger
def main():
 sm={r['entry_id']:r for r in rows(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')};tt={r['entry_id']:r for r in rows(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')}
 control_ds=rows(FROZEN/'UPWARD_STAIRCASE_V4_MAX3_DECISIONS.jsonl.gz');control_ts=rows(FROZEN/'UPWARD_STAIRCASE_V4_MAX3_TRADES.jsonl.gz')
 v5_ds=rows(PRIVATE/f'{PROFILE}_DECISIONS.jsonl.gz');v5_ts=rows(PRIVATE/f'{PROFILE}_TRADES.jsonl.gz')
 controls={};reservations={};occupancies={}
 for arm,ds,ts,iscontrol in [('Control',control_ds,control_ts,True),('v5',v5_ds,v5_ts,False)]:
  controls[arm],reservations[arm],occupancies[arm]=arm_analysis(ds,ts,tt,sm,iscontrol)
  gzwrite(PRIVATE/f'{arm}_RESERVATION_EVALUATION_JOIN.jsonl.gz',reservations[arm])
 save(OUT/'SLOT_QUALITY_AND_RESERVATION.json',controls)
 checkpoint('V6_SLOT_QUALITY_AND_RESERVATION_AUDIT','QUALITY_JOIN_COMPLETE',{'Control':controls['Control']['metrics'],'v5':controls['v5']['metrics'],'v5_quality':controls['v5']['quality']})
 oracle=json.loads((OUT/'ORACLE_UPPER_BOUND.json').read_text());O5=oracle['maximum_feasible_U5'];opp={}
 for arm,ds in [('Control',control_ds),('v5',v5_ds)]:
  opp[arm],ledger=opportunity(ds,tt,sm,occupancies[arm]);gzwrite(PRIVATE/f'{arm}_OPPORTUNITY_LEDGER.jsonl.gz',ledger)
 gap={'Oracle_max_feasible_rank_pass_U5':O5,'Control_recovery':42/O5,'v5_recovery':controls['v5']['metrics']['U5']['funded']/O5,'remaining_oracle_gap':O5-controls['v5']['metrics']['U5']['funded'],'opportunity':opp,'HELD_SLOT_BLOCKED_definition':'MAX3 rejection, prior-batch holding exists, candidate among first3 rank-pass entries of this batch; diagnostic overlap classification, not unique counterfactual blame.'}
 save(OUT/'OPPORTUNITY_AND_ORACLE_GAP.json',gap)
 checkpoint('V7_ORACLE_GAP_AND_OPPORTUNITY_COST','GAP_AND_NET_MISS_FIXED',gap)
 control=json.loads((FROZEN/'UPWARD_STAIRCASE_V4_MAX3_RESULT.json').read_text());v5=json.loads((PRIVATE/f'{PROFILE}_RESULT.json').read_text())
 a=controls['Control']['metrics'];b=controls['v5']['metrics'];quality0=controls['Control']['quality'];quality5=controls['v5']['quality']
 P={'P1_U5_conversion':b['U5']['conversion']>a['U5']['conversion'],'P2_U5_MAX3_miss':b['U5']['MAX3_miss']<66,'P3_U5_Net_Slot_Miss':b['U5']['Net_Slot_Miss']<66,'P4_U10_funded':b['U10']['funded']>23,'P5_U10_MAX3_miss':b['U10']['MAX3_miss']<21,'P6_U10_Net_Slot_Miss':b['U10']['Net_Slot_Miss']<21,'P7_below2_contamination':quality5['below2_rate']<=quality0['below2_rate']}
 E={'E1_daily_geom':v5['geometric_mean_daily_return']>control['geometric_mean_daily_return'],'E2_rolling20_median':v5['rolling20_median']>control['rolling20_median'],'E3_final_equity':v5['final_equity']>control['final_equity']}
 success={'P':P,'E':E,'SLOT_INTELLIGENCE':'SLOT_INTELLIGENCE_IMPROVED' if all(P[k] for k in list(P)[:3]) else 'MIXED' if any(P.values()) else 'WORSE','CAPITAL_V5':'CAPITAL_V5_IMPROVES' if all(E.values()) else 'MIXED' if any(E.values()) else 'WORSE','North_Star':{'Control':control['north_star_hit_N'],'v5':v5['north_star_hit_N'],'target':2,'status':'NOT_REACHED' if not v5['north_star_hit_N'] else 'REACHED_IN_DEVELOPMENT'},'control_replays':0,'Primary_replays':1,'policy_count':1,'retune':0,'Safety':SAFETY}
 save(OUT/'SUCCESS_CRITERIA.json',success)
 paired=[]
 for c,v in zip(control['daily_series'],v5['daily_series']):
  assert c['session']==v['session'];paired.append({'session':c['session'],'control_return':c['daily_return'],'v5_return':v['daily_return'],'paired_daily_delta':v['daily_return']-c['daily_return'],'control_starting_cash':c['starting_cash'],'control_ending_cash':c['ending_cash'],'v5_starting_cash':v['starting_cash'],'v5_ending_cash':v['ending_cash']})
 rolls=[{'start_session':c['start_session'],'end_session':c['end_session'],'control_multiple':c['growth_multiple'],'v5_multiple':v['growth_multiple'],'paired_delta':v['growth_multiple']-c['growth_multiple'],'control_amount_from_1m':c['amount_from_1m'],'v5_amount_from_1m':v['amount_from_1m']} for c,v in zip(control['rolling20_windows'],v5['rolling20_windows'])]
 for name,data in [('PAIRED_DAILY.csv',paired),('PAIRED_ROLLING20.csv',rolls)]:
  with (OUT/name).open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
 save(OUT/'PAIRED_DAILY_DELTA_SUMMARY.json',{'N':len(paired),'mean_delta':mean(x['paired_daily_delta'] for x in paired),'median_delta':median(x['paired_daily_delta'] for x in paired),'positive_delta_days':sum(x['paired_daily_delta']>0 for x in paired),'negative_delta_days':sum(x['paired_daily_delta']<0 for x in paired),'equal_delta_days':sum(x['paired_daily_delta']==0 for x in paired),'Control_positive_days':sum(x['control_return']>0 for x in paired),'v5_positive_days':sum(x['v5_return']>0 for x in paired)})
 print(json.dumps({'Control':a,'v5':b,'v5_quality':quality5,'criteria':success,'oracle_gap':gap},ensure_ascii=False))
if __name__=='__main__':main()
