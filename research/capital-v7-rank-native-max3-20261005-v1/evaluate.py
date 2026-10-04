"""Read saved two-arm ledgers once; no runtime policy mutation or replay."""
from control import *
from collections import Counter,defaultdict
from decimal import Decimal as D
from statistics import mean
ARMS=['RANK_NATIVE_GREEDY_MAX3','RANK_NATIVE_LAST_SLOT_OPTION_MAX3']
REASONS=['FUNDED','RANK_BASE_REJECT','LAST_SLOT_RESERVE_REJECT','MAX3_FULL','CASH_OR_LOT','SAME_SYMBOL','EXECUTION_BLOCKED','OTHER_EXPLICIT']
def quality(rr,tt):
 n=len(rr);pot=[tt[r['entry_id']]['potential_return'] for r in rr]
 return {'N':n,'U5':sum(tt[r['entry_id']]['label_bigwinner5'] for r in rr),'U10':sum(tt[r['entry_id']]['label_bigwinner10'] for r in rr),'below2_N':sum(p<.02 for p in pot),'below2_rate':sum(p<.02 for p in pot)/n if n else None,'below3_N':sum(p<.03 for p in pot),'below3_rate':sum(p<.03 for p in pot)/n if n else None,'Medium3_5_N':sum(.03<=p<.05 for p in pot)}
def preservation():
 mask={r['entry_id'] for r in rows(PRIVATE/'COMMON_EVAL_MASK.jsonl.gz') if r['included']};tt={r['entry_id']:r for r in rows(INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz')};runtime={r['entry_id']:r for r in rows(PRIVATE/'RANK_NATIVE_RUNTIME.jsonl.gz')};old={r['entry_id']:r for r in rows(INPUT/'v4/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')};oracles=read(OUT/'ORACLE_RESULT.json')['solves'];books={r['entry_id']:r for r in rows(INPUT/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
 assert len(mask)==1028;legacy={k for k in mask if old[k]['ML']>=1};assert sum(tt[k]['label_bigwinner5'] for k in legacy)==113 and sum(tt[k]['label_bigwinner10'] for k in legacy)==47
 ranked=sorted([runtime[k] for k in mask],key=lambda r:(-r['pP'],r['entry_timestamp'],r['symbol']));decile={r['entry_id']:i*10//len(ranked)+1 for i,r in enumerate(ranked)};profiles={};regrets=[]
 for arm in ARMS:
  result=read(OUT/f'{arm}_RESULT.json');assert result['valid_primary_day_N']==38 and result['blocked_execution_day_N']==0,'CAPITAL_CHAIN_BLOCKED_NO_RESULT_RESCUE'
  allrows=rows(PRIVATE/f'{arm}_DECISIONS.jsonl.gz');ds=[d for d in allrows if d['entry_id'] in mask];assert len(ds)==1028 and len({d['entry_id'] for d in ds})==1028;trades={r['entry_id']:r for r in rows(PRIVATE/f'{arm}_TRADES.jsonl.gz')}
  conservation={}
  for label,field,total in [('U5','label_bigwinner5',170),('U10','label_bigwinner10',67)]:
   c=Counter(d['reason'] if d['reason'] in REASONS else 'OTHER_EXPLICIT' for d in ds if tt[d['entry_id']][field]);assert sum(c.values())==total;conservation[label]={k:c[k] for k in REASONS}
  funded=[d for d in ds if d['reason']=='FUNDED'];q=quality(funded,tt);u5=q['U5'];u10=q['U10']
  gate={'P1_U5_gt50':u5>50,'P2_U10_ge26':u10>=26,'P3_below2_le38_666667pct':q['below2_rate']<=.38666667,'P4_integrity':result['execution_source_unresolved_N']==0 and D(result['cash_minimum'])>=0 and result['max_concurrent_actual']<=3 and read(OUT/'CAUSAL_CANARY_RESULTS.json')['all_PASS'],'P5_independent':'PENDING_D13'}
  pointpass=all(gate[k] for k in gate if k!='P5_independent')
  legacy_counts={}
  for label,field in [('U5','label_bigwinner5'),('U10','label_bigwinner10')]:
   c=Counter(d['reason'] for d in ds if d['entry_id'] in legacy and tt[d['entry_id']][field]);legacy_counts[label]={k:c[k] for k in REASONS}
  regret_u5=0;regret_u10=0
  for d in ds:
   k=d['entry_id'];target=tt[k];held=d['held_before_batch']
   if d['reason']=='FUNDED' or not target['label_bigwinner5']:continue
   r=runtime[k];higher=bool(held and r['pP']>min(h['pP'] for h in held));row={'profile':arm,'entry_id':k,'U5':target['label_bigwinner5'],'U10':target['label_bigwinner10'],'miss_reason':d['reason'],'arrival_minute':d['minute'],'held_N':len(held),'held_positions':held,'missed_pP':r['pP'],'higher_than_min_held_pP':higher,'overlap_duration_minutes':{h['entry_id']:max(0,min(trades[h['entry_id']]['release_minute'],920)-d['minute']) for h in held if h['entry_id'] in trades},'evaluation_only':True};regrets.append(row)
   if d['reason']=='MAX3_FULL' and higher:regret_u5+=1;regret_u10+=target['label_bigwinner10']
  profiles[arm]={'cohort_N':1028,'U5_denominator':170,'U10_denominator':67,'conservation':conservation,'funded_quality':q,'U5_funded':u5,'U10_funded':u10,'U5_capture':u5/170,'U10_capture':u10/67,'Oracle_ALL_U5_recovery':u5/oracles['ALL_U5']['maximum_U5'],'Oracle_ALL_U10_recovery':u10/oracles['ALL_U10']['maximum_U10'],'Oracle_ADMISSION_U5_recovery':u5/oracles['ADMISSION_U5']['maximum_U5'],'Oracle_ADMISSION_U10_recovery':u10/oracles['ADMISSION_U10']['maximum_U10'],'preservation_gate':gate,'point_gate_PASS':pointpass,'legacy_rank_pass_comparable':legacy_counts,'slot_quality':{str(slot):quality([d for d in funded if d['funded_slot']==slot],tt) for slot in (1,2,3)},'pP_deciles':{str(j):{'candidate_quality':quality([d for d in ds if decile[d['entry_id']]==j],tt),'funded_quality':quality([d for d in funded if decile[d['entry_id']]==j],tt)} for j in range(1,11)},'entry_hour_quality':{str(hour):{'candidate_quality':quality([d for d in ds if d['minute']//60==hour],tt),'funded_quality':quality([d for d in funded if d['minute']//60==hour],tt)} for hour in range(9,16)},'HIGHER_RANK_WINNER_BLOCKED_BY_LOWER_RANK_HOLDING_U5':regret_u5,'HIGHER_RANK_WINNER_BLOCKED_BY_LOWER_RANK_HOLDING_U10':regret_u10,'post_cutoff_identity_retained_N':sum(d['reason']=='CUTOFF' for d in allrows)}
 gzsave(PRIVATE/'RANK_REGRET_LEDGER.jsonl.gz',regrets)
 save(OUT/'PRESERVATION_RESULT.json',{'exact_jst':now(),'profiles':profiles,'mutually_exclusive_reason_totals_exact':True,'legacy_v5':{'U5':dict(zip(REASONS,[50,0,30,28,5,0,0,0])),'U10':dict(zip(REASONS,[26,0,10,9,2,0,0,0]))},'v5_primary_reconstructed_without_replay':{'U5':dict(zip(REASONS,[50,57,30,28,5,0,0,0])),'U10':dict(zip(REASONS,[26,20,10,9,2,0,0,0]))},'regret_ledger_sha256':sha(PRIVATE/'RANK_REGRET_LEDGER.jsonl.gz'),'P5_pending_independent':True,'Safety':SAFETY})
 checkpoint('D11_PRESERVATION_RESULT','PRESERVATION_CONSERVED_PENDING_AUDIT',['170 U5 conservation each arm','67 U10 conservation each arm','legacy113/47 subset','slots/deciles/time/regret'],{arm:{k:profiles[arm][k] for k in ('U5_funded','U10_funded','point_gate_PASS')} for arm in ARMS},'Report Capital from same saved ledgers; independent audit before final selection',{'oracle_solves':4,'primary_replays':2})
 print(json.dumps({a:{k:profiles[a][k] for k in ('U5_funded','U10_funded','funded_quality','conservation','point_gate_PASS')} for a in ARMS}),flush=True)
def capital():
 preserve=read(OUT/'PRESERVATION_RESULT.json')['profiles'];profiles={}
 for arm in ARMS:
  r=read(OUT/f'{arm}_RESULT.json');g={'median':r['rolling20_median']>1.199154192,'mean':r['rolling20_arithmetic_mean']>1.190646013,'daily_geometric':r['geometric_mean_daily_return']>.01032420041};pp=preserve[arm]['point_gate_PASS']
  status='NORTH_STAR_HIT' if pp and r['north_star_hit_N']>0 else 'CAPITAL_V7_IMPROVES' if pp and all(g.values()) else 'SLOT_IMPROVED_CAPITAL_MIXED' if pp else 'CAPITAL_ONLY_MIXED' if any(g.values()) else 'NO_GO'
  profiles[arm]={'economics':r,'Capital_gates':g,'provisional_status_before_P5':status,'same_ledger_no_additional_replay':True}
 save(OUT/'CAPITAL_ROLLING20_RESULT.json',{'exact_jst':now(),'profiles':profiles,'v5_saved_reference':read(ROOT/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/MAIN_REPLAY_RESULT.json'),'v5_control_replay':0,'38_sessions_not_one_month':True,'rolling19_windows_overlap_not_independent':True,'fresh_OOS_claim':False,'Safety':SAFETY})
 checkpoint('D12_CAPITAL_ROLLING20_RESULT','CAPITAL_FROM_SAME_LEDGER_PENDING_AUDIT',['rolling20 19 overlapping windows each arm','daily/Final38/MaxDD/utilization','saved v5 only'],{a:profiles[a]['provisional_status_before_P5'] for a in ARMS},'Independent scalar/Fraction reconstruction, separate Oracle upper bound; mismatch0 required',{'oracle_solves':4,'primary_replays':2})
if __name__=='__main__':
 import sys
 globals()[sys.argv[1]]()
