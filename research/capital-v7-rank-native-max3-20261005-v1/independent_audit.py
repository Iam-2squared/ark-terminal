"""Separate scalar/Fraction trajectory and binary-MILP ceiling certification."""
from independent_engine import *
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
REASONS=['FUNDED','RANK_BASE_REJECT','LAST_SLOT_RESERVE_REJECT','MAX3_FULL','CASH_OR_LOT','SAME_SYMBOL','EXECUTION_BLOCKED','OTHER_EXPLICIT']
def oracle_audit(runtime,audit):
 books={r['entry_id']:r for r in rows(I/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};mask={r['entry_id'] for r in rows(P/'COMMON_EVAL_MASK.jsonl.gz') if r['included']};teacher={r['entry_id']:r for r in rows(I/'evaluation/TEACHERS_EVALUATION.jsonl.gz')};valid=[];unavailable=[];results={}
 for r in runtime:
  if r['entry_id'] not in mask:continue
  b=books[r['entry_id']];src=early(b) or late(b)
  if not b['capture_complete'] or not b.get('entry_actual_source') or src is None or src['release']<=r['entry_minute']:unavailable.append(r['entry_id']);continue
  valid.append(r|{'release_minute':src['release'],'buy_lot':F(r['raw_reference'])*F(10005,10000)*100,'sell_lot':src['price']*100,'U5':teacher[r['entry_id']]['label_bigwinner5'],'U10':teacher[r['entry_id']]['label_bigwinner10']})
 audit.check('Oracle executable identityN',len(valid)==1016 and len(unavailable)==12);audit.check('Oracle unavailable no winners',all(teacher[k]['label_bigwinner5']==teacher[k]['label_bigwinner10']==0 for k in unavailable))
 for scope,target in [('ALL','U5'),('ALL','U10'),('ADMISSION','U5'),('ADMISSION','U10')]:
  name=f'{scope}_{target}';pop=[r for r in valid if scope=='ALL' or r['band']!='P_BELOW'];clocks=sorted({(r['session'],r[z]) for r in pop for z in ('entry_minute','release_minute')});coor=[];cols=[]
  for j,r in enumerate(pop):
   for i,(day,t) in enumerate(clocks):
    if day==r['session'] and r['entry_minute']<=t<r['release_minute']:coor.append(i);cols.append(j)
  matrix=coo_matrix((np.ones(len(cols)),(coor,cols)),shape=(len(clocks),len(pop))).tocsr();u10bound=sum(r['U10'] for r in pop);reward=np.array([r['U5']*(u10bound+1)+r['U10'] if target=='U5' else r['U10'] for r in pop],dtype=float)
  res=milp(c=-reward,integrality=np.ones(len(pop)),bounds=Bounds(np.zeros(len(pop)),np.ones(len(pop))),constraints=LinearConstraint(matrix,np.zeros(len(clocks)),np.full(len(clocks),3.)),options={'mip_rel_gap':0.,'time_limit':60.})
  audit.check(name+'/MILP certificate',res.status==0 and res.success and res.mip_gap==0)
  assert res.status==0 and res.mip_gap==0,'INDEPENDENT_ORACLE_CERTIFICATE_UNRESOLVED'
  xx=np.rint(res.x).astype(int);u5=sum(r['U5']*x for r,x in zip(pop,xx));u10=sum(r['U10']*x for r,x in zip(pop,xx));primary=read(O/f'ORACLE_{name}.json');audit.check(name+'/upper_U10',u10==primary['maximum_U10'])
  if target=='U5':audit.check(name+'/upper_U5',u5==primary['maximum_U5'])
  witness=rows(P/f'{name}_WITNESS.jsonl.gz');lookup={r['entry_id']:r for r in pop};selected=[]
  for z in witness:
   r=lookup[z['entry_id']];q=z['quantity'];audit.check(z['entry_id']+'/Oracle_lot',q>=100 and q%100==0);audit.money(z['entry_id']+'/Oracle_buy',z['debit'],r['buy_lot']*(q//100));audit.money(z['entry_id']+'/Oracle_sell',z['credit'],r['sell_lot']*(q//100));audit.check(z['entry_id']+'/Oracle_timing',z['entry_minute']==r['entry_minute'] and z['release_minute']==r['release_minute']);selected.append((r,q//100))
  minimum=F(1000000);maxheld=0
  for day,t in clocks:
   balance=F(1000000);held=[]
   for r,lots in selected:
    if (r['session'],r['entry_minute'])<=(day,t):balance-=lots*r['buy_lot']
    if (r['session'],r['release_minute'])<=(day,t):balance+=lots*r['sell_lot']
    if day==r['session'] and r['entry_minute']<=t<r['release_minute']:held.append(r)
   audit.check(name+'/exactcash',balance>=0 and len(held)<=3 and len({r['symbol'] for r in held})==len(held));minimum=min(minimum,balance);maxheld=max(maxheld,len(held))
  audit.money(name+'/mincash',minimum,primary['minimum_lot_witness_cash_min']);counts={'U5':sum(r['U5'] for r,lots in selected),'U10':sum(r['U10'] for r,lots in selected)};audit.check(name+'/witnesscount',counts['U5']==primary['maximum_U5'] and counts['U10']==primary['maximum_U10']);audit.check(name+'/witnesshash',digest(P/f'{name}_WITNESS.jsonl.gz')==primary['witness_sha256'])
  results[name]={'upper_U5':int(u5) if target=='U5' else None,'upper_U10':int(u10),'cash_relaxed_MILP_gap':float(res.mip_gap),'exact_cash_witness_min':str(minimum),'max_held':maxheld,'global_count_ceiling_certified':True}
 return results
def summarize_decisions(ds,mask,teacher):
 cohort=[r for r in ds if r['entry_id'] in mask];funded=[r for r in cohort if r['reason']=='FUNDED'];n=len(funded)
 counts={label:{reason:sum(r['reason']==reason and teacher[r['entry_id']][field] for r in cohort) for reason in REASONS} for label,field in [('U5','label_bigwinner5'),('U10','label_bigwinner10')]}
 out={'conservation':counts,'U5_funded':counts['U5']['FUNDED'],'U10_funded':counts['U10']['FUNDED'],'below2_rate':sum(teacher[r['entry_id']]['potential_return']<.02 for r in funded)/n,'slot_quality':{str(s):{'N':sum(r['funded_slot']==s for r in funded),'U5':sum(r['funded_slot']==s and teacher[r['entry_id']]['label_bigwinner5'] for r in funded),'U10':sum(r['funded_slot']==s and teacher[r['entry_id']]['label_bigwinner10'] for r in funded),'below2_N':sum(r['funded_slot']==s and teacher[r['entry_id']]['potential_return']<.02 for r in funded)} for s in (1,2,3)}}
 return out
def winner(profiles):
 eligible=[a for a in ARMS if profiles[a]['preservation_PASS']]
 def sortkey(a):
  p=profiles[a];e=p['economics'];q=p['preservation'];return (-e['north_star_hit_N'],-e['rolling20_median'],-e['rolling20_arithmetic_mean'],-e['geometric_mean_daily_return'],-q['U5_funded'],-q['U10_funded'],q['below2_rate'],e['max_drawdown'],ARMS.index(a))
 chosen=min(eligible,key=sortkey) if eligible else None;diag=chosen or min(ARMS,key=sortkey);promoted=chosen if chosen and profiles[chosen]['status'] in ('CAPITAL_V7_IMPROVES','NORTH_STAR_HIT') else None
 c=profiles[diag]['preservation']['conservation']['U5'];gaps={'RANK_ADMISSION':c['RANK_BASE_REJECT'],'LAST_SLOT_RESERVE':c['LAST_SLOT_RESERVE_REJECT'],'MAX3_PHYSICAL_OCCUPANCY':c['MAX3_FULL'],'CASH_SIZING':c['CASH_OR_LOT']};maximum=max(gaps.values());names=[k for k,v in gaps.items() if v==maximum];bottleneck=names[0] if len(names)==1 and maximum>0 else 'NO_CLEAR_SINGLE_BOTTLENECK'
 return {'eligible_winner':chosen,'diagnostic_arm':diag,'selectedCapitalCandidate':promoted,'NEXT_BOTTLENECK':bottleneck,'reason_gaps':gaps}
def main():
 marker=P/'INDEPENDENT_FULL_AUDIT_STARTED.json';assert not marker.exists(),'INDEPENDENT_AUDIT_AMBIGUOUS_NO_RERUN'
 with marker.open('x') as f:json.dump({'exact_jst':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),'Primary_imports':0,'distinct_reconstruction':True},f)
 audit=Audit()
 for pin in read(O/'INPUT_BYTE_AND_SOURCE_FREEZE.json')['checks']:audit.check('hash/'+pin['path'],digest(W/pin['path'])==pin['sha256'])
 for a in ARMS:
  for name,h in read(O/f'{a}_RESULT.json')['ledger_sha256'].items():audit.check(a+'/'+name+'/hash',digest(P/f'{a}_{name}.jsonl.gz')==h)
 runtime,tables,train=build_mapping(audit);mask={r['entry_id'] for r in rows(P/'COMMON_EVAL_MASK.jsonl.gz') if r['included']};teacher={r['entry_id']:r for r in rows(I/'evaluation/TEACHERS_EVALUATION.jsonl.gz')};support={r['entry_id']:r for r in rows(P/'TEACHER_SUPPORT_LEDGER.jsonl.gz')};entries={r['watch_key']:r for r in rows(I/'entry/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if r['entry_status']=='FIRST_ENTRY'};book={r['entry_id']:r for r in rows(I/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
 for r in runtime:
  k=r['entry_id'];e=entries[k];audit.check(k+'/FrozenEntryidentity',r['session']==e['session'] and r['symbol']==e['symbol'] and r['entry_timestamp']==e['fill_timestamp'] and r['entry_minute']==e['fill_minute']);audit.money(k+'/raw_reference',r['raw_reference'],book[k]['entry_actual_source']['O'])
  if k in mask:
   audit.check(k+'/teacherknown',support[k]['status_U5'].startswith('KNOWN_') and support[k]['status_U10'].startswith('KNOWN_'));audit.check(k+'/teacherlabels',teacher[k]['label_bigwinner5']==support[k]['label_U5'] and teacher[k]['label_bigwinner10']==support[k]['label_U10'])
 oracle_results=oracle_audit(runtime,audit);profiles={};primary_pres=read(O/'PRESERVATION_RESULT.json')['profiles']
 for arm in ARMS:
  ds,economics=reconstruct(arm,runtime,tables,audit);q=summarize_decisions(ds,mask,teacher);saved=primary_pres[arm]
  audit.check(arm+'/conservation',q['conservation']==saved['conservation'] and sum(q['conservation']['U5'].values())==170 and sum(q['conservation']['U10'].values())==67);audit.check(arm+'/capture',q['U5_funded']==saved['U5_funded'] and q['U10_funded']==saved['U10_funded']);audit.num(arm+'/below2',q['below2_rate'],saved['funded_quality']['below2_rate'])
  for slot,v in q['slot_quality'].items():audit.check(arm+'/slot'+slot,all(v[k]==saved['slot_quality'][slot][k] for k in v))
  preservation_PASS=q['U5_funded']>50 and q['U10_funded']>=26 and q['below2_rate']<=.38666667
  capitals=[economics['rolling20_median']>1.199154192,economics['rolling20_arithmetic_mean']>1.190646013,economics['geometric_mean_daily_return']>.01032420041]
  status='NORTH_STAR_HIT' if preservation_PASS and economics['north_star_hit_N']>0 else 'CAPITAL_V7_IMPROVES' if preservation_PASS and all(capitals) else 'SLOT_IMPROVED_CAPITAL_MIXED' if preservation_PASS else 'CAPITAL_ONLY_MIXED' if any(capitals) else 'NO_GO'
  audit.check(arm+'/status',status==read(O/'CAPITAL_ROLLING20_RESULT.json')['profiles'][arm]['provisional_status_before_P5']);profiles[arm]={'economics':economics,'preservation':q,'preservation_PASS':preservation_PASS,'status':status}
 selection=winner(profiles);result={'exact_jst':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),'check_N':audit.checks,'mismatch_N':len(audit.mismatches),'mismatches':audit.mismatches,'max_float_delta':audit.max_float_delta,'float_tolerance':1e-12,'money_quantity_tolerance':0,'Primary_runtime_replay_evaluator_imports':0,'model_inference':'Scalar math.fsum independently rebuilt feature vector','accounting':'Exact Fraction independently replayed trajectory','Oracle':'Distinct binary occupancy MILP global upper bound + exact feasible cash witness, not Primary flow solver','Oracle_results':oracle_results,'profiles':profiles,'independent_selection':selection,'implementation_independent_market_source_not_independent':True,'independent_recalculations_not_primary_replays':2,'primary_replays_remain':2,'new_fits':0,'fresh_OOS_claim':False}
 with (O/'INDEPENDENT_AUDIT.json').open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps({'check_N':audit.checks,'mismatch_N':len(audit.mismatches),'mismatches':audit.mismatches[:20],'selection':selection,'max_float_delta':audit.max_float_delta}),flush=True)
 assert not audit.mismatches,'INDEPENDENT_MISMATCH_STOP_NO_REPLAY_OR_RETUNE'
if __name__=='__main__':main()
