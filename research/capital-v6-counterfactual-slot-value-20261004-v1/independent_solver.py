"""Independent integer solver: explicit branch-and-bound + dual-simplex LP.

Imports no Primary teacher/policy/replay. Interleaved lot/select variables,
Fraction feasibility and rational box-adjusted dual bounds. The MIP search is
implemented here; scipy.milp/HiGHS MIP is never invoked by this implementation.
"""
from fractions import Fraction as F
from functools import reduce
import math
import numpy as np
from scipy.optimize import linprog
def ceiling(v):return -((-v.numerator)//v.denominator)
def problem(state,a,h,accept):
 n=len(a);rows=[];rhs=[];times=sorted({state['minute']}|{z[k] for z in a for k in ('entry_minute','release_minute')}|{z['release_minute'] for z in h});cash=F(state['cash']);L=[F(0)]*(2*n);U=[]
 for z in a:
  wealth=cash+sum((F(p['credit']) for p in h),F(0))
  for p in a:
   if p['release_minute']<=z['entry_minute'] and F(p['credit'])>F(p['debit']):wealth*=F(p['credit'])/F(p['debit'])
  U.extend([F(int(wealth/F(z['debit']))+1),F(1)])
 for t in times:
  v=[F(0)]*(2*n)
  for i,z in enumerate(a):v[2*i+1]=F(int(z['entry_minute']<=t<z['release_minute']))
  rows.append(v);rhs.append(F(3-sum(p['release_minute']>t for p in h)))
  v=[F(0)]*(2*n)
  for i,z in enumerate(a):v[2*i]=((F(z['debit']) if z['entry_minute']<=t else F(0))-(F(z['credit']) if z['release_minute']<=t else F(0)))/1000000
  rows.append(v);rhs.append((cash+sum((F(p['credit']) for p in h if p['release_minute']<=t),F(0)))/1000000)
 for i,z in enumerate(a):
  v=[F(0)]*(2*n);v[2*i]=1;v[2*i+1]=-U[2*i];rows.append(v);rhs.append(F(0))
  v=[F(0)]*(2*n);v[2*i+1]=1;v[2*i]=-1;rows.append(v);rhs.append(F(0))
  if z['entry_id'] in state['pending_ids']:L[2*i+1]=U[2*i+1]=F(1)
  if z['entry_id']==state['entry_id']:L[2*i+1]=U[2*i+1]=F(int(accept))
 counts=[]
 for kind in range(3):
  v=[F(0)]*(2*n)
  for i,z in enumerate(a):v[2*i+1]=F(int(z['potential']>=.05 if kind==0 else z['potential']>=.10 if kind==1 else .03<=z['potential']<.05))
  counts.append(v)
 return rows,rhs,L,U,counts
def feasible(x,A,b,E,e,L,U):
 return all(L[i]<=x[i]<=U[i] and x[i].denominator==1 for i in range(len(x))) and all(sum((v*z for v,z in zip(row,x)),F(0))<=bb for row,bb in zip(A,b)) and all(sum((v*z for v,z in zip(row,x)),F(0))==ee for row,ee in zip(E,e))
def integer_optimize(c,A,b,E,e,L,U,quantum,incumbent):
 assert feasible(incumbent,A,b,E,e,L,U),'INDEPENDENT_INCUMBENT_INFEASIBLE'
 best=sum((v*z for v,z in zip(c,incumbent)),F(0));winner=incumbent;nodes=0;leaves=0;stack=[(L,U)]
 Af=np.array(A,dtype=float);bf=np.array(b,dtype=float);Ef=np.array(E,dtype=float) if E else None;ef=np.array(e,dtype=float) if E else None;cf=np.array(c,dtype=float)
 while stack:
  lower,upper=stack.pop();nodes+=1
  r=linprog(cf,A_ub=Af,b_ub=bf,A_eq=Ef,b_eq=ef,bounds=list(zip(map(float,lower),map(float,upper))),method='highs-ds')
  if r.status==2:leaves+=1;continue
  assert r.status==0,('INDEPENDENT_LP_FAILED',r.message)
  y=[min(F(0),F(str(float(v)))) for v in r.ineqlin.marginals];z=[F(str(float(v))) for v in r.eqlin.marginals] if E else []
  dual=sum((v*bb for v,bb in zip(y,b)),F(0))+sum((v*ee for v,ee in zip(z,e)),F(0))
  for j,cj in enumerate(c):
   residual=cj-sum((v*row[j] for v,row in zip(y,A)),F(0))-sum((v*row[j] for v,row in zip(z,E)),F(0))
   dual+=min(residual*lower[j],residual*upper[j])
  if ceiling(dual/quantum)*quantum>=best:leaves+=1;continue
  rounded=[F(int(round(v))) for v in r.x]
  if feasible(rounded,A,b,E,e,lower,upper):
   val=sum((v*q for v,q in zip(c,rounded)),F(0))
   if val<best:best=val;winner=rounded
   if ceiling(dual/quantum)*quantum>=best:leaves+=1;continue
  fractional=[(min(v-math.floor(v),math.ceil(v)-v),j,v) for j,v in enumerate(r.x) if abs(v-round(v))>1e-7]
  assert fractional,('LP_INTEGER_ROUNDING_CERTIFICATE_FAILED',float(dual),float(best))
  _,j,v=max(fractional);floor=F(math.floor(v));ceil=F(math.ceil(v))
  if floor>=lower[j]:up=upper.copy();up[j]=min(up[j],floor);stack.append((lower.copy(),up))
  if ceil<=upper[j]:lo=lower.copy();lo[j]=max(lo[j],ceil);stack.append((lo,upper.copy()))
  assert nodes<200000,'INDEPENDENT_NODE_LIMIT'
 return winner,{'nodes':nodes,'terminal_certificates':leaves,'objective_exact':str(best),'algorithm':'Independent B&B with dual-simplex LP, exact Fraction box-adjusted dual/lattice pruning; numerical LP infeasibility leaves'}
def certify(state,a,h,accept,witness):
 A,b,L,U,counts=problem(state,a,h,accept);x=[]
 for i in range(len(a)):x.extend([F(int(witness[len(a)+i])),F(int(witness[i]))])
 w=len(a)+1;c=[-(counts[0][j]*w*w+counts[1][j]*w+counts[2][j]) for j in range(2*len(a))]
 optimum,search1=integer_optimize(c,A,b,[],[],L,U,F(1),x);target=[sum((v*q for v,q in zip(row,optimum)),F(0)) for row in counts]
 assert [sum((v*q for v,q in zip(row,x)),F(0)) for row in counts]==target,'INDEPENDENT_COUNT_MISMATCH'
 cost=[F(0)]*(2*len(a));amounts=[]
 for i,z in enumerate(a):cost[2*i]=(F(z['debit'])+F(z['credit']))/1000000;amounts.append(cost[2*i])
 den=math.lcm(*[q.denominator for q in amounts]);quantum=F(reduce(math.gcd,[q.numerator*(den//q.denominator) for q in amounts]),den)
 optimal,search2=integer_optimize(cost,A,b,counts,target,L,U,quantum,x)
 turn=sum((q*cc for q,cc in zip(optimal,cost)),F(0))*1000000;inputturn=sum((q*cc for q,cc in zip(x,cost)),F(0))*1000000;assert turn==inputturn,'INDEPENDENT_TURNOVER_MISMATCH'
 return {'incremental_counts':[int(v) for v in target],'turnover_exact':str(turn),'turnover_quantum_jpy':str(quantum*1000000),'count_search':search1,'turnover_search':search2,'constraints_exact_feasible':True,'Primary_imports':0,'scipy_milp_calls':0}
