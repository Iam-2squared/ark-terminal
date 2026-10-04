"""Independent identity, policy, Fraction accounting and selection audit.
Primary runtime/replay/evaluator imports = 0. Old Oracle solves = 0.
"""
from independent_engine import *
from independent_policy import build
from independent_replay import reconstruct
from datetime import datetime
from zoneinfo import ZoneInfo
REASONS=['FUNDED','RANK_BASE_REJECT','CAPACITY_RESERVE_REJECT','MAX3_FULL','CASH_OR_LOT','SAME_SYMBOL','EXECUTION_BLOCKED','OTHER_EXPLICIT']
def now():return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='microseconds')
def quality(rr,teacher):
 pots=[teacher[r['entry_id']]['potential_return'] for r in rr];n=len(rr)
 return {'N':n,'U5':sum(teacher[r['entry_id']]['label_bigwinner5'] for r in rr),'U10':sum(teacher[r['entry_id']]['label_bigwinner10'] for r in rr),'below2_N':sum(v<.02 for v in pots),'below2_rate':sum(v<.02 for v in pots)/n if n else None,'below3_N':sum(v<.03 for v in pots),'below3_rate':sum(v<.03 for v in pots)/n if n else None,'Medium3_5_N':sum(.03<=v<.05 for v in pots)}
def summarize(ds,runtime,teacher,mask,primary_rows):
 runtime={r['entry_id']:r for r in runtime};cohort=[d for d in ds if d['entry_id'] in mask];fund=[d for d in cohort if d['reason']=='FUNDED'];ordered=sorted((runtime[k] for k in mask),key=lambda r:(-r['pP'],r['entry_timestamp'],r['symbol']));deciles={r['entry_id']:i*10//1028+1 for i,r in enumerate(ordered)}
 counts={label:{reason:sum(d['reason']==reason and teacher[d['entry_id']][field] for d in cohort) for reason in REASONS} for label,field in [('U5','label_bigwinner5'),('U10','label_bigwinner10')]};admission={label:{reason:sum(d['band']!='P_BELOW' and d['reason']==reason and teacher[d['entry_id']][field] for d in cohort) for reason in REASONS} for label,field in [('U5','label_bigwinner5'),('U10','label_bigwinner10')]}
 rank5=rank10=bad5=bad10=0
 # Primary snapshots were already reconstructed and compared exact in replay;
 # use the independently validated field to derive separate diagnostic counts.
 for d in cohort:
  k=d['entry_id'];target=teacher[k]
  if d['reason']!='MAX3_FULL' or not target['label_bigwinner5']:continue
  held=primary_rows[k]['held_before_batch'];lower=[h for h in held if h['pP']<runtime[k]['pP']];bad=[h for h in lower if teacher[h['entry_id']]['potential_return']<.02];rank5+=bool(lower);rank10+=bool(lower)*target['label_bigwinner10'];bad5+=bool(bad);bad10+=bool(bad)*target['label_bigwinner10']
 fr=[runtime[d['entry_id']]['r'] for d in fund];mr=[runtime[d['entry_id']]['r'] for d in cohort if d['reason']!='FUNDED' and teacher[d['entry_id']]['label_bigwinner5']]
 return {'conservation':counts,'admission_conservation':admission,'funded_quality':quality(fund,teacher),'U5_funded':counts['U5']['FUNDED'],'U10_funded':counts['U10']['FUNDED'],'slot_quality':{str(s):quality([d for d in fund if d['funded_slot']==s],teacher) for s in (1,2,3)},'pP_deciles':{str(i):{'candidate':quality([d for d in cohort if deciles[d['entry_id']]==i],teacher),'funded':quality([d for d in fund if deciles[d['entry_id']]==i],teacher)} for i in range(1,11)},'Entry_hours':{str(h):{'candidate':quality([d for d in cohort if d['minute']//60==h],teacher),'funded':quality([d for d in fund if d['minute']//60==h],teacher)} for h in range(9,16)},'FALSE_RESERVE_U5':counts['U5']['CAPACITY_RESERVE_REJECT'],'FALSE_RESERVE_U10':counts['U10']['CAPACITY_RESERVE_REJECT'],'BAD_FILL_BLOCKED_U5_unique_missed':bad5,'BAD_FILL_BLOCKED_U10_unique_missed':bad10,'HIGHER_P5_BLOCKED_BY_LOWER_HELD_U5':rank5,'HIGHER_P5_BLOCKED_BY_LOWER_HELD_U10':rank10,'mean_funded_r':mean(fr),'median_funded_r':median(fr),'mean_missed_U5_r':mean(mr),'median_missed_U5_r':median(mr),'sum_r':math.fsum(fr)}
def selection(profiles):
 eligible=[a for a in ARMS if profiles[a]['Preservation_PASS'] and profiles[a]['Capital_PASS']]
 def winnerkey(a):
  p=profiles[a];q=p['preservation'];e=p['economics'];return (-e['north_star_hit_N'],-e['rolling20_median'],-e['rolling20_arithmetic_mean'],-e['geometric_mean_daily_return'],-q['U5_funded'],-q['U10_funded'],q['funded_quality']['below2_rate'],e['max_drawdown'],ARMS.index(a))
 winner=min(eligible,key=winnerkey) if eligible else None
 def diagnostic(a):
  p=profiles[a];q=p['preservation'];return (-q['U5_funded'],-q['U10_funded'],q['funded_quality']['below2_rate'],-p['economics']['rolling20_median'],ARMS.index(a))
 diag=winner or min(ARMS,key=diagnostic);c=profiles[diag]['preservation']['conservation']['U5'];gaps={'RANK_ADMISSION':c['RANK_BASE_REJECT'],'CAPACITY_RESERVE':c['CAPACITY_RESERVE_REJECT'],'MAX3_ONLINE_OCCUPANCY':c['MAX3_FULL'],'CASH_SIZING':c['CASH_OR_LOT']};priority=['RANK_ADMISSION','MAX3_ONLINE_OCCUPANCY','CAPACITY_RESERVE','CASH_SIZING'];bottleneck=min(gaps,key=lambda k:(-gaps[k],priority.index(k)))
 status='V8R1_NORTH_STAR_HIT' if winner and profiles[winner]['economics']['north_star_hit_N']>0 else 'V8R1_CAPITAL_IMPROVED' if winner else 'V8R1_PRESERVATION_ONLY' if any(p['Preservation_PASS'] for p in profiles.values()) else 'V8R1_NO_GO'
 return {'status':status,'selectedCapitalCandidate':winner,'diagnosticArm':diag,'NEXT_BOTTLENECK':bottleneck,'observed_U5_exclusive_gaps':gaps,'physical_unavoidable':21,'admission_ceiling_loss':33,'Admission_Oracle_to_runtime_gap':116-profiles[diag]['preservation']['U5_funded']}
def main():
 P.mkdir(parents=True,exist_ok=True)
 with (P/'INDEPENDENT_FULL_AUDIT_STARTED.json').open('x') as f:json.dump({'exact_jst':now(),'single_execution_audit':True,'Primary_imports':0},f)
 audit=Audit()
 for z in read(O/'INPUT_BYTE_FREEZE.json')['files']:audit.check('sourcehash/'+z['path'],digest(ROOT.parent/'v7_work'/z['path'])==z['sha256'])
 for name,hash in read(O/'AUTHORITY_FREEZE.json')['sha256'].items():audit.check('authority/'+name,digest(ROOT/name)==hash)
 for arm in ARMS:
  for name,h in read(O/f'{arm}_RESULT.json')['ledger_sha256'].items():audit.check(arm+'/'+name+'/SHA',digest(P/f'{arm}_{name}.jsonl.gz')==h)
 runtime,tables,train=build(audit);mask={r['entry_id'] for r in rows(PIN/'COMMON_EVAL_MASK.jsonl.gz') if r['included']};teacher={r['entry_id']:r for r in rows(I/'evaluation/TEACHERS_EVALUATION.jsonl.gz')};support={r['entry_id']:r for r in rows(PIN/'TEACHER_SUPPORT_LEDGER.jsonl.gz')};entry={r['watch_key']:r for r in rows(I/'entry/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if r['entry_status']=='FIRST_ENTRY'};book={r['entry_id']:r for r in rows(I/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
 for r in runtime:
  k=r['entry_id'];e=entry[k];audit.check(k+'/Frozen_identity',r['session']==e['session'] and r['symbol']==e['symbol'] and r['entry_timestamp']==e['fill_timestamp'] and r['entry_minute']==e['fill_minute']);audit.money(k+'/raw_reference',r['raw_reference'],book[k]['entry_actual_source']['O'])
  if k in mask:audit.check(k+'/teacher_known',support[k]['status_U5'].startswith('KNOWN_') and support[k]['status_U10'].startswith('KNOWN_'));audit.check(k+'/teacher_label',teacher[k]['label_bigwinner5']==support[k]['label_U5'] and teacher[k]['label_bigwinner10']==support[k]['label_U10'])
 old=read(ROOT/'docs/evidence/capital-v7-rank-native-max3-20261005-v1/ORACLE_RESULT.json');audit.check('saved_Oracle_counts',old['solves']['ALL_U5']['maximum_U5']==149 and old['solves']['ADMISSION_U5']['maximum_U5']==116 and old['solves']['ALL_U10']['maximum_U10']==67 and old['solves']['ADMISSION_U10']['maximum_U10']==55)
 profiles={};primary=read(O/'PRESERVATION_RESULT.json')['profiles'];capital=read(O/'CAPITAL_ROLLING20_RESULT.json')['profiles']
 for arm in ARMS:
  ds,economic=reconstruct(arm,runtime,tables,audit);lookup={r['entry_id']:r for r in rows(P/f'{arm}_DECISIONS.jsonl.gz')};q=summarize(ds,runtime,teacher,mask,lookup);saved=primary[arm]
  for field,v in q.items():
   if field.startswith('mean_') or field.startswith('median_') or field=='sum_r':audit.num(arm+'/'+field,v,saved[field])
   else:audit.check(arm+'/'+field,v==saved[field])
  audit.check(arm+'/conservation170_67',sum(q['conservation']['U5'].values())==170 and sum(q['conservation']['U10'].values())==67);audit.check(arm+'/admission124_55',sum(q['admission_conservation']['U5'].values())==124 and sum(q['admission_conservation']['U10'].values())==55)
  for field,expected in [('Physical_U5_recovery',q['U5_funded']/149),('Physical_U10_recovery',q['U10_funded']/67),('Admission_U5_recovery',q['U5_funded']/116),('Admission_U10_recovery',q['U10_funded']/55)]:audit.num(arm+'/'+field,expected,saved[field])
  p=q['U5_funded']>50 and q['U10_funded']>=26 and q['funded_quality']['below2_rate']<=.38666667 and q['U5_funded']/116>50/116
  gates={'rolling20_median':economic['rolling20_median']>1.1991541915,'rolling20_mean':economic['rolling20_arithmetic_mean']>1.1906460126,'daily_geometric':economic['geometric_mean_daily_return']>.01032420041};audit.check(arm+'/capital_gate_points',gates==capital[arm]['economic_point_gates']);audit.check(arm+'/preservation_gate_point',p==saved['point_gates_PASS']);profiles[arm]={'preservation':q,'economics':economic,'Preservation_PASS':p,'Capital_PASS':p and all(gates.values())}
 result={'exact_jst':now(),'status':'PASS' if not audit.mismatches else 'FAIL','check_N':audit.checks,'mismatch_N':len(audit.mismatches),'mismatches':audit.mismatches,'max_float_delta':audit.max_float_delta,'float_tolerance':1e-12,'money_quantity_tolerance':0,'Primary_runtime_replay_evaluator_imports':0,'input_source_independence_claim':False,'implementation_independent_same_market_source':True,'old_Oracle_solves':0,'independent_full_recalculations':2,'primary_replays_remain':2,'profiles':profiles,'independent_selection':selection(profiles),'fresh_OOS_claim':False}
 with (O/'INDEPENDENT_AUDIT.json').open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps({'checks':audit.checks,'mismatch':len(audit.mismatches),'mismatches':audit.mismatches[:20],'max_float_delta':audit.max_float_delta,'selection':result['independent_selection']}),flush=True)
 assert not audit.mismatches,'INDEPENDENT_MISMATCH_NO_REPLAY_OR_RETUNE'
if __name__=='__main__':main()
