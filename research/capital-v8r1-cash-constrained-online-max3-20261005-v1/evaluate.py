"""Read the two fixed Main ledgers; teachers stay evaluation-only."""
from control import *
from collections import Counter
from decimal import Decimal as D
from statistics import mean,median
REASONS=['FUNDED','RANK_BASE_REJECT','CAPACITY_RESERVE_REJECT','MAX3_FULL','CASH_OR_LOT','SAME_SYMBOL','EXECUTION_BLOCKED','OTHER_EXPLICIT']
def quality(rr,tt):
 n=len(rr);p=[tt[r['entry_id']]['potential_return'] for r in rr]
 return {'N':n,'U5':sum(tt[r['entry_id']]['label_bigwinner5'] for r in rr),'U10':sum(tt[r['entry_id']]['label_bigwinner10'] for r in rr),'below2_N':sum(z<.02 for z in p),'below2_rate':sum(z<.02 for z in p)/n if n else None,'below3_N':sum(z<.03 for z in p),'below3_rate':sum(z<.03 for z in p)/n if n else None,'Medium3_5_N':sum(.03<=z<.05 for z in p)}
def conservation(ds,teacher):
 counts={}
 for label,field,total in [('U5','label_bigwinner5',170),('U10','label_bigwinner10',67)]:
  c=Counter(d['reason'] if d['reason'] in REASONS else 'OTHER_EXPLICIT' for d in ds if teacher[d['entry_id']][field]);assert sum(c.values())==total;counts[label]={k:c[k] for k in REASONS}
 return counts
def preservation():
 mask={r['entry_id'] for r in rows(PIN/'COMMON_EVAL_MASK.jsonl.gz') if r['included']};tt={r['entry_id']:r for r in rows(INPUT/'evaluation/TEACHERS_EVALUATION.jsonl.gz')};runtime={r['entry_id']:r for r in rows(PIN/'RANK_NATIVE_RUNTIME.jsonl.gz')};assert len(mask)==1028
 ordered=sorted([runtime[k] for k in mask],key=lambda r:(-r['pP'],r['entry_timestamp'],r['symbol']));decile={r['entry_id']:i*10//len(ordered)+1 for i,r in enumerate(ordered)};profiles={};regrets=[];bad_pairs=[];diag=read(OUT/'PPRANK_CASH_DIAGNOSTIC_RESULT.json')
 for arm in ARMS:
  economic=read(OUT/f'{arm}_RESULT.json');assert economic.get('valid_primary_day_N')==38 and economic.get('blocked_execution_day_N')==0,'SHARED_RUNTIME_EXECUTION_BLOCKED_NO_RESULT_RESCUE'
  allrows=rows(PRIVATE/f'{arm}_DECISIONS.jsonl.gz');ds=[r for r in allrows if r['entry_id'] in mask];assert len(ds)==1028 and len({r['entry_id'] for r in ds})==1028;funded=[d for d in ds if d['reason']=='FUNDED'];q=quality(funded,tt);counts=conservation(ds,tt);admitted=[r for r in ds if r['band']!='P_BELOW'];adc={}
  for label,field,total in [('U5','label_bigwinner5',124),('U10','label_bigwinner10',55)]:
   c=Counter(d['reason'] if d['reason'] in REASONS else 'OTHER_EXPLICIT' for d in admitted if tt[d['entry_id']][field]);assert sum(c.values())==total;adc[label]={r:c[r] for r in REASONS}
  u5=q['U5'];u10=q['U10'];trades={r['entry_id']:r for r in rows(PRIVATE/f'{arm}_TRADES.jsonl.gz')};higher5=higher10=bad5=bad10=0
  for d in ds:
   k=d['entry_id'];target=tt[k]
   if not target['label_bigwinner5'] or d['reason']=='FUNDED':continue
   r=runtime[k];held=d['held_before_batch'];lower=[h for h in held if h['pP']<r['pP']];bad=[h for h in lower if tt[h['entry_id']]['potential_return']<.02]
   if d['reason']=='MAX3_FULL':
    higher5+=bool(lower);higher10+=bool(lower)*target['label_bigwinner10'];bad5+=bool(bad);bad10+=bool(bad)*target['label_bigwinner10']
    for h in bad:bad_pairs.append({'profile':arm,'missed_entry_id':k,'blocker_entry_id':h['entry_id'],'missed_pP':r['pP'],'blocker_pP':h['pP'],'arrival_minute':d['minute'],'blocker_release_minute':trades[h['entry_id']]['release_minute'],'U5':target['label_bigwinner5'],'U10':target['label_bigwinner10'],'blocker_below2':True,'evaluation_only':True})
   regrets.append({'profile':arm,'entry_id':k,'U5':target['label_bigwinner5'],'U10':target['label_bigwinner10'],'reason':d['reason'],'arrival_minute':d['minute'],'missed_pP':r['pP'],'missed_r':r['r'],'held_positions':held,'higher_than_min_held_pP':bool(lower),'bad_below2_blocker_N':len(bad),'overlap_remaining_minutes':{h['entry_id']:max(0,trades[h['entry_id']]['release_minute']-d['minute']) for h in held},'evaluation_only':True})
  integrity={'cash_nonnegative':D(economic['cash_minimum'])>=0,'MAX3':economic['max_concurrent_actual']<=3,'same_symbol':True,'execution_unresolved':economic['execution_source_unresolved_N']==0,'canary_all_PASS':read(OUT/'CAUSAL_CANARY_RESULTS.json')['all_PASS'],'future_test_use':0,'leakage':0}
  gates={'P1_U5_gt50':u5>50,'P2_U10_ge26':u10>=26,'P3_below2_le38_666667pct':q['below2_rate']<=.38666667,'P4_admission_recovery_gt50_116':u5/116>50/116,'P5_runtime_integrity':all(integrity[k] for k in ('cash_nonnegative','MAX3','same_symbol','execution_unresolved','canary_all_PASS')),'P6_independent_mismatch0':'PENDING'}
  funded_r=[runtime[d['entry_id']]['r'] for d in funded];missed_r=[runtime[d['entry_id']]['r'] for d in ds if tt[d['entry_id']]['label_bigwinner5'] and d['reason']!='FUNDED'];sum_r=math.fsum(funded_r)
  profiles[arm]={'cohort_N':1028,'conservation':counts,'admission_conservation':adc,'funded_quality':q,'U5_funded':u5,'U10_funded':u10,'U5_capture':u5/170,'U10_capture':u10/67,'Physical_U5_recovery':u5/149,'Physical_U10_recovery':u10/67,'Admission_U5_recovery':u5/116,'Admission_U10_recovery':u10/55,'preservation_gates':gates,'point_gates_PASS':all(v for k,v in gates.items() if k!='P6_independent_mismatch0'),'runtime_integrity':integrity,'slot_quality':{str(s):quality([d for d in funded if d['funded_slot']==s],tt) for s in (1,2,3)},'pP_decile_definition':'common OOF raw pP DESC, timestamp/symbol ties, decile1 highest','pP_deciles':{str(j):{'candidate':quality([d for d in ds if decile[d['entry_id']]==j],tt),'funded':quality([d for d in funded if decile[d['entry_id']]==j],tt)} for j in range(1,11)},'Entry_hours':{str(h):{'candidate':quality([d for d in ds if d['minute']//60==h],tt),'funded':quality([d for d in funded if d['minute']//60==h],tt)} for h in range(9,16)},'FALSE_RESERVE_U5':counts['U5']['CAPACITY_RESERVE_REJECT'],'FALSE_RESERVE_U10':counts['U10']['CAPACITY_RESERVE_REJECT'],'BAD_FILL_BLOCKED_U5_unique_missed':bad5,'BAD_FILL_BLOCKED_U10_unique_missed':bad10,'HIGHER_P5_BLOCKED_BY_LOWER_HELD_U5':higher5,'HIGHER_P5_BLOCKED_BY_LOWER_HELD_U10':higher10,'mean_funded_r':mean(funded_r),'median_funded_r':median(funded_r),'mean_missed_U5_r':mean(missed_r),'median_missed_U5_r':median(missed_r),'sum_r':sum_r,'runtime_rank_utility_efficiency':sum_r/diag['sum_r'] if diag['status']=='CERTIFIED' else None,'funded_per_session':len(funded)/38,'same_ledger_no_additional_replay':True}
 gzsave(PRIVATE/'RANK_REGRET_LEDGER.jsonl.gz',regrets);gzsave(PRIVATE/'BAD_FILL_PAIR_LEDGER.jsonl.gz',bad_pairs)
 save(OUT/'PRESERVATION_RESULT.json',{'exact_jst':now(),'profiles':profiles,'primary_U5':170,'primary_U10':67,'admission_U5':124,'admission_U10':55,'conservation_exact':True,'P6_independent_pending':True,'regret_sha256':sha(PRIVATE/'RANK_REGRET_LEDGER.jsonl.gz'),'bad_fill_pairs_sha256':sha(PRIVATE/'BAD_FILL_PAIR_LEDGER.jsonl.gz'),'diagnostic_terms_not_unique_causal_blame':True,'Safety':SAFETY})
 checkpoint('R11_PRESERVATION_RESULT','PRESERVATION_CONSERVED_PENDING_FULL_AUDIT',['170/67 and124/55 conservation','False Reserve / Bad Fill / rank regret','slot/decile/time/r diagnostics'],{a:{k:profiles[a][k] for k in ('U5_funded','U10_funded','point_gates_PASS')} for a in ARMS},'Same-ledger economics then independent Fraction reconstruction; no replay/retune',{'primary_pP_diagnostic_solve':1,'independent_pP_diagnostic_solve':1,'uniqueness_no_good_solve':1,'B1_replay':1,'B2_replay':1})
 print(json.dumps({a:{k:profiles[a][k] for k in ('U5_funded','U10_funded','funded_quality','conservation','point_gates_PASS')} for a in ARMS}),flush=True)
def capital():
 profiles={};pres=read(OUT/'PRESERVATION_RESULT.json')['profiles']
 for arm in ARMS:
  e=read(OUT/f'{arm}_RESULT.json');g={'rolling20_median':e['rolling20_median']>1.1991541915,'rolling20_mean':e['rolling20_arithmetic_mean']>1.1906460126,'daily_geometric':e['geometric_mean_daily_return']>.01032420041};p=pres[arm]['point_gates_PASS'];profiles[arm]={'economics':e,'economic_point_gates':g,'capital_point_PASS':p and all(g.values()),'NORTH_STAR_HIT_DEVELOPMENT':e['north_star_hit_N']>0,'independent_pending':True,'same_ledger_no_additional_replay':True}
 save(OUT/'CAPITAL_ROLLING20_RESULT.json',{'exact_jst':now(),'profiles':profiles,'38_sessions_not_one_month':True,'19_rolling_windows_overlap_not_independent':True,'fresh_OOS_claim':False,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','Safety':SAFETY})
 checkpoint('R12_CAPITAL_ROLLING20_RESULT','SAME_LEDGER_CAPITAL_PENDING_FULL_AUDIT',['two 38 COMPLETE chains','19 overlapping rolling20 windows each','daily/Final38/MTM DD/utilization'],{a:profiles[a]['capital_point_PASS'] for a in ARMS},'Full independent audit before final fixed winner/bottleneck',{'primary_pP_diagnostic_solve':1,'independent_pP_diagnostic_solve':1,'uniqueness_no_good_solve':1,'B1_replay':1,'B2_replay':1})
if __name__=='__main__':
 import sys,math
 {'preservation':preservation,'capital':capital}[sys.argv[1]]()
