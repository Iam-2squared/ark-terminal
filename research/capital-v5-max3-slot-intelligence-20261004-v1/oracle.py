"""Evaluator-only lexicographic interval MILP; never imported by runtime policy.

The physical oracle has cash-only, >=100-share lots, MAX3 and fixed executions.
It does not inherit v4 utilization/capital caps, which are policy constraints.
A feasible one-lot witness matching the cash-relaxed lexicographic upper bound
certifies the physical maximum for any allowed lot sizing. Oracle PnL is not a
primary economic result and no oracle data is exported to the policy module.
"""
from common import *
from decimal import Decimal as D
from collections import Counter
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import csr_matrix, vstack

def optimize(candidates, cash_constraint, stages=True):
 n=len(candidates);times=sorted({(r['session'],r[k]) for r in candidates for k in ('entry_minute','release_minute')})
 occupancy=np.array([[int(r['session']==day and r['entry_minute']<=t<r['release_minute']) for r in candidates] for day,t in times],dtype=float)
 matrix=[csr_matrix(occupancy)];lower=[np.zeros(len(times))];upper=[np.full(len(times),3.)]
 # FIRST ENTRY creates at most one row per symbol/session. Assert rather than
 # silently ignore any simultaneous same-symbol contract constraint.
 assert len({(r['session'],r['symbol']) for r in candidates})==n
 if cash_constraint:
  cash=np.array([[float((r['credit'] if (r['session'],r['release_minute'])<=(day,t) else D(0))-(r['debit'] if (r['session'],r['entry_minute'])<=(day,t) else D(0))) for r in candidates] for day,t in times])
  matrix.append(csr_matrix(cash/1000000));lower.append(np.full(len(times),-1.));upper.append(np.full(len(times),np.inf))
 A=vstack(matrix,format='csr');lo=np.concatenate(lower);hi=np.concatenate(upper)
 vectors=[np.array([int(r['potential']>=k) for r in candidates],float) for k in (.05,.10)]
 vectors.append(np.array([int(.03<=r['potential']<.05) for r in candidates],float))
 vectors.append(np.array([float(r['debit']+r['credit']) for r in candidates],float)/1000000)
 names=('U5','U10_at_max_U5','Medium_at_max_U5_U10','turnover_jpy')
 log=[];selected=None
 for stage,(name,v) in enumerate(zip(names,vectors)):
  objective=v if stage==3 else -v
  result=milp(c=objective,integrality=np.ones(n),bounds=Bounds(np.zeros(n),np.ones(n)),constraints=LinearConstraint(A,lo,hi),options={'mip_rel_gap':0.,'time_limit':60.})
  assert result.status==0 and result.success and result.mip_gap==0.,(name,result.message)
  x=np.rint(result.x).astype(int);assert np.max(np.abs(x-result.x))<1e-6
  value=float(v@x)
  assert abs(float(objective@x)-result.mip_dual_bound)<1e-6
  log.append({'objective':name,'value':value*1000000 if stage==3 else int(round(value)),'solver_status':int(result.status),'mip_gap':float(result.mip_gap),'dual_bound':float(result.mip_dual_bound),'node_N':int(result.mip_node_count)})
  selected=[r for r,z in zip(candidates,x) if z]
  if stage<3:
   A=vstack([A,csr_matrix(v.reshape(1,-1))],format='csr');lo=np.append(lo,round(value));hi=np.append(hi,round(value))
 return selected,log

def inputs():
 score=rows(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')
 teachers={r['entry_id']:r for r in rows(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')}
 # Local evaluator may read frozen execution helpers; the live slot decision
 # has no access to these future books or labels.
 from execution import frozen_execution,eod_source,BUY
 books={r['entry_id']:r for r in rows(SRC/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')}
 candidates=[];invalid=[]
 for r in score:
  if not r['admission'] or r['entry_minute']>=920:continue
  b=books[r['entry_id']];fill=frozen_execution(b) or eod_source(b['market'],r['session'])
  if not fill or fill.get('blocked') or not b['capture_complete'] or not b['entry_actual_source']:
   invalid.append(r['entry_id']);continue
  assert fill['release_minute']>r['entry_minute']
  candidates.append({k:r[k] for k in ('entry_id','session','symbol','entry_minute','rank')}|{'release_minute':fill['release_minute'],'potential':teachers[r['entry_id']]['potential_return'],'debit':100*D(r['raw_reference'])*BUY,'credit':100*D(fill['price']),'exit_kind':fill['kind']})
 return candidates,invalid

def main():
 save(PRIVATE/'ORACLE_STARTED.json',{'JST':now(),'evaluator_only':True})
 candidates,invalid=inputs()
 upper,ub=optimize(candidates,False)
 feasible,fb=optimize(candidates,True)
 # Matching all three integer upper bounds proves counts maximal even if an
 # alternative oracle uses more than one lot. Matching unconstrained minimum
 # turnover also proves the fourth tie-break without restricting lot sizing.
 assert [x['value'] for x in ub[:3]]==[x['value'] for x in fb[:3]],'ORACLE_NOT_CERTIFIED_FULL_PHYSICAL_MAXIMUM'
 assert abs(ub[3]['value']-fb[3]['value'])<1e-6,'TURNOVER_TIE_BREAK_NOT_CERTIFIED'
 times=sorted({(r['session'],r[k]) for r in candidates for k in ('entry_minute','release_minute')})
 cash_values=[D(1000000)+sum(((r['credit'] if (r['session'],r['release_minute'])<=(day,t) else D(0))-(r['debit'] if (r['session'],r['entry_minute'])<=(day,t) else D(0)) for r in feasible),D(0)) for day,t in times]
 assert min(cash_values)>=0 and all(sum(r['session']==day and r['entry_minute']<=t<r['release_minute'] for r in feasible)<=3 for day,t in times)
 O5=fb[0]['value'];O10=fb[1]['value'];M=fb[2]['value']
 witness=[dict(r,quantity=100,debit=str(r['debit']),credit=str(r['credit'])) for r in feasible]
 gzwrite(PRIVATE/'ORACLE_WITNESS.jsonl.gz',witness)
 selected={r['entry_id'] for r in feasible};blocked=[]
 for r in candidates:
  if r['potential']<.05 or r['entry_id'] in selected:continue
  overlaps=[z['entry_id'] for z in feasible if z['session']==r['session'] and z['entry_minute']<r['release_minute'] and r['entry_minute']<z['release_minute']]
  blocked.append({'entry_id':r['entry_id'],'overlapping_selected_IDs':overlaps,'interpretation':'Witness overlap only; no uniquely causal per-candidate attribution among alternative optima.'})
 gzwrite(PRIVATE/'ORACLE_MISSES.jsonl.gz',blocked)
 out={'JST':now(),'oracle':'ORACLE_U5_SLOT','evaluator_only':True,'candidate_N':len(candidates),'invalid_execution_IDs':invalid,'rank_pass_U5_denominator':113,'rank_pass_U10_denominator':47,'maximum_feasible_U5':O5,'maximum_U10_conditional_on_max_U5':O10,'maximum_Medium_conditional_on_max_U5_U10':M,'minimum_turnover_at_counts_jpy':fb[3]['value'],
 'slot_relaxed_cash_upper_bounds':ub,'cash_one_lot_feasible':fb,'full_physical_maximum_certified':True,'certificate':'Feasible 100-share cash witness attains all cash-relaxed integer count bounds and turnover lower bound; additional lot sizes cannot improve any lexicographic objective.',
 'unavoidable_U5_total_misses':113-O5,'unavoidable_overlap_only_U5_misses':113-ub[0]['value'],'additional_cash_loss_to_count_bound':ub[0]['value']-O5,'joint_lex_U10_misses':47-O10,'control_U5_gap':O5-42,'control_recovery':42/O5,'cash_minimum_witness':str(min(cash_values)),
 'scope':'Physical MAX3/cash/100-share/unchanged Entry-EXIT/cutoff/same-symbol bound. v4 rank fixed. Capital rank caps/utilization/allocation are deliberately relaxed in evaluator, so the ceiling need not be achievable by an exact v4 allocation policy.',
 'oracle_PnL_primary':False,'policy_threshold_selected_from_oracle':False,'Safety':SAFETY}
 save(OUT/'ORACLE_UPPER_BOUND.json',out)
 checkpoint('V2_ORACLE_UPPER_BOUND','CERTIFIED_EVALUATOR_ONLY',out)
 print(json.dumps({k:out[k] for k in ('maximum_feasible_U5','maximum_U10_conditional_on_max_U5','maximum_Medium_conditional_on_max_U5_U10','unavoidable_U5_total_misses','cash_minimum_witness')}))
if __name__=='__main__':main()
