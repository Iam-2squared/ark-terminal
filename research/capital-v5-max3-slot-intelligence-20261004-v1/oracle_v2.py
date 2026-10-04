"""Complete physical oracle with integer lot sizing; evaluator-only.

V1 already certified maxU5=104 and conditional maxU10=47. Its one-lot
restriction lost two tertiary Medium entries, so this append-only extension
solves integer sizing for Medium and turnover without any policy retune.
"""
from common import *
from oracle import inputs,optimize
from decimal import Decimal as D,ROUND_FLOOR
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import csr_matrix,vstack,hstack

def full_sizing(a,u5,u10):
 n=len(a);times=sorted({(r['session'],r[k]) for r in a for k in ('entry_minute','release_minute')})
 occupancy=np.array([[r['session']==day and r['entry_minute']<=t<r['release_minute'] for r in a] for day,t in times],dtype=float)
 cash=np.array([[float((r['credit'] if (r['session'],r['release_minute'])<=(day,t) else D(0))-(r['debit'] if (r['session'],r['entry_minute'])<=(day,t) else D(0))) for r in a] for day,t in times])/1e6
 # Universally valid wealth upper bound: remove every losing trade and permit
 # full-wealth compounding once for every positive completed candidate. This
 # relaxation dominates all finite cash-only/MAX3 portfolios, at each entry.
 maxlots=[]
 for r in a:
  wealth=D(1000000)
  for z in a:
   if (z['session'],z['release_minute'])<=(r['session'],r['entry_minute']) and z['credit']>z['debit']:wealth*=z['credit']/z['debit']
  maxlots.append(int((wealth/r['debit']).to_integral_value(rounding=ROUND_FLOOR))+1)
 maxlots=np.array(maxlots,dtype=float)
 link=np.zeros((2*n,2*n))
 for i,m in enumerate(maxlots):
  link[2*i,i]=-1;link[2*i,n+i]=1
  link[2*i+1,i]=m;link[2*i+1,n+i]=-1
 A=vstack([hstack([csr_matrix(occupancy),csr_matrix((len(times),n))]),hstack([csr_matrix((len(times),n)),csr_matrix(cash)]),csr_matrix(link)],format='csr')
 lo=np.concatenate([np.zeros(len(times)),np.full(len(times),-1.),np.zeros(2*n)])
 hi=np.concatenate([np.full(len(times),3.),np.full(len(times),np.inf),np.full(2*n,np.inf)])
 for threshold,value in ((.05,u5),(.10,u10)):
  v=np.r_[[int(r['potential']>=threshold) for r in a],np.zeros(n)]
  A=vstack([A,csr_matrix(v.reshape(1,-1))],format='csr');lo=np.append(lo,value);hi=np.append(hi,value)
 log=[];solution=None
 for name in ('Medium','turnover'):
  v=np.r_[[int(.03<=r['potential']<.05) for r in a],np.zeros(n)] if name=='Medium' else np.r_[np.zeros(n),[float(r['debit']+r['credit'])/1e6 for r in a]]
  objective=-v if name=='Medium' else v
  result=milp(c=objective,integrality=np.ones(2*n),bounds=Bounds(np.zeros(2*n),np.r_[np.ones(n),maxlots]),constraints=LinearConstraint(A,lo,hi),options={'mip_rel_gap':0.,'time_limit':300.})
  assert result.status==0 and result.success and result.mip_gap==0.,(name,result.message,result.fun,getattr(result,'mip_gap',None))
  x=np.rint(result.x).astype(int);assert np.max(np.abs(x-result.x))<1e-5
  value=float(v@x);log.append({'objective':name,'value':int(round(value)) if name=='Medium' else value*1e6,'status':int(result.status),'mip_gap':float(result.mip_gap),'dual_bound':float(result.mip_dual_bound),'nodes':int(result.mip_node_count)})
  solution=x
  if name=='Medium':A=vstack([A,csr_matrix(v.reshape(1,-1))],format='csr');lo=np.append(lo,round(value));hi=np.append(hi,round(value))
 return solution,log,maxlots.tolist()

def main():
 save(PRIVATE/'ORACLE_V2_STARTED.json',{'JST':now(),'evaluator_only':True,'reason':'Complete tertiary objective with unrestricted integer lots; primary count ceiling already certified byV1.'})
 a,invalid=inputs();v1=json.loads((OUT/'ORACLE_V1_CERTIFICATION_FAILURE.json').read_text());ub=v1['slot_only_upper'];fb=v1['one_lot_feasible']
 assert [z['value'] for z in ub[:2]]==[z['value'] for z in fb[:2]]
 O5,O10=ub[0]['value'],ub[1]['value'];x,logs,bounds=full_sizing(a,O5,O10);n=len(a)
 selected=[dict(r,quantity=int(x[n+i])*100,debit=str(r['debit']*int(x[n+i])),credit=str(r['credit']*int(x[n+i]))) for i,r in enumerate(a) if x[i]]
 assert all(x[n+i]>=x[i] and x[n+i]<=bounds[i]*x[i] for i in range(n))
 times=sorted({(r['session'],r[k]) for r in a for k in ('entry_minute','release_minute')})
 cv=[D(1000000)+sum(((D(r['credit']) if (r['session'],r['release_minute'])<=(day,t) else D(0))-(D(r['debit']) if (r['session'],r['entry_minute'])<=(day,t) else D(0)) for r in selected),D(0)) for day,t in times]
 assert min(cv)>=0
 assert all(sum(r['session']==day and r['entry_minute']<=t<r['release_minute'] for r in selected)<=3 for day,t in times)
 gzwrite(PRIVATE/'ORACLE_WITNESS.jsonl.gz',selected)
 out={'JST':now(),'oracle':'ORACLE_U5_SLOT','evaluator_only':True,'candidate_N':len(a),'invalid_execution_IDs':invalid,'rank_pass_U5_denominator':113,'rank_pass_U10_denominator':47,'maximum_feasible_U5':O5,'maximum_U10_conditional_on_max_U5':O10,'maximum_Medium_conditional_on_max_U5_U10':logs[0]['value'],'minimum_turnover_at_counts_jpy':logs[1]['value'],'full_physical_maximum_certified':True,'count_upper_certificate':ub,'integer_sizing_solver':logs,'sizing_upper_bounds_hash':hashlib.sha256(json.dumps(bounds).encode()).hexdigest(),'cash_minimum_witness':str(min(cv)),
 'unavoidable_U5_total_misses':113-O5,'unavoidable_overlap_only_U5_misses':113-O5,'additional_cash_loss_to_U5_count_bound':0,'joint_lex_U10_misses':47-O10,'control_U5_gap':O5-42,'control_recovery':42/O5,'scope':'Physical MAX3/cash/100-share/same-symbol/fixed Entry-EXIT/15:20 cutoff. v4 allocation caps and utilization are policy constraints deliberately relaxed by physical evaluator ceiling. Oracle sizing is not a live allocation recommendation.',
 'certificate':'Binary selection with integer lot sizes, exact source prices/cash validation. U5/U10 match interval-only upper bounds; Medium and turnover solve remaining lexicographic MILPs with zero gap.','oracle_PnL_primary':False,'policy_threshold_selected_from_oracle':False,'historical_v1_certification_failure_preserved':True,'Safety':SAFETY}
 save(OUT/'ORACLE_UPPER_BOUND.json',out);checkpoint('V2_ORACLE_UPPER_BOUND','CERTIFIED_EVALUATOR_ONLY',out)
 print(json.dumps({k:out[k] for k in ('maximum_feasible_U5','maximum_U10_conditional_on_max_U5','maximum_Medium_conditional_on_max_U5_U10','minimum_turnover_at_counts_jpy','cash_minimum_witness')}),flush=True)
if __name__=='__main__':main()
