"""Training-only physical continuation; never imported by runtime slot policy."""
from decimal import Decimal as D, ROUND_FLOOR
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import csr_matrix,vstack
def solve(state,candidates,held_releases,labels,accept):
 n=len(candidates);current=state['entry_id'];t0=state['minute'];cash=D(state['cash']);held=state['held'];pending=set(state['pending_ids'])
 assert n and len(held)+len(pending) in (1,2)
 times=sorted({t0}|{z[k] for z in candidates for k in ('entry_minute','release_minute')}|{z['release_minute'] for z in held_releases})
 maxlots=[]
 for z in candidates:
  wealth=cash+sum((D(p['credit']) for p in held_releases),D(0))
  for p in candidates:
   if p['release_minute']<=z['entry_minute'] and D(p['credit'])>D(p['debit']):wealth*=D(p['credit'])/D(p['debit'])
  maxlots.append(int((wealth/D(z['debit'])).to_integral_value(rounding=ROUND_FLOOR))+1)
 matrix=[];lo=[];hi=[]
 for t in times:
  v=np.zeros(2*n)
  for i,z in enumerate(candidates):v[i]=int(z['entry_minute']<=t<z['release_minute'])
  matrix.append(v);lo.append(0);hi.append(3-sum(p['release_minute']>t for p in held_releases))
  v=np.zeros(2*n)
  for i,z in enumerate(candidates):v[n+i]=float((D(z['credit']) if z['release_minute']<=t else D(0))-(D(z['debit']) if z['entry_minute']<=t else D(0)))/1e6
  matrix.append(v);lo.append(-float(cash+sum((D(p['credit']) for p in held_releases if p['release_minute']<=t),D(0)))/1e6);hi.append(np.inf)
 for i,m in enumerate(maxlots):
  v=np.zeros(2*n);v[n+i]=1;v[i]=-1;matrix.append(v);lo.append(0);hi.append(np.inf)
  v=np.zeros(2*n);v[i]=m;v[n+i]=-1;matrix.append(v);lo.append(0);hi.append(np.inf)
 lb=np.zeros(2*n);ub=np.r_[np.ones(n),maxlots].astype(float)
 for i,z in enumerate(candidates):
  if z['entry_id'] in pending:lb[i]=ub[i]=1
  if z['entry_id']==current:lb[i]=ub[i]=int(accept)
 A=csr_matrix(np.array(matrix));lo=np.array(lo);hi=np.array(hi)
 countv=[np.r_[[int(z['potential']>=.05) for z in candidates],np.zeros(n)],np.r_[[int(z['potential']>=.10) for z in candidates],np.zeros(n)],np.r_[[int(.03<=z['potential']<.05) for z in candidates],np.zeros(n)]]
 w=n+1;objective=countv[0]*w*w+countv[1]*w+countv[2]
 result=milp(c=-objective,integrality=np.ones(2*n),bounds=Bounds(lb,ub),constraints=LinearConstraint(A,lo,hi),options={'mip_rel_gap':0.,'time_limit':120.})
 assert result.status==0 and result.success and result.mip_gap==0.,('COUNT_SOLVE_BLOCKED',state['state_key'],accept,result.message)
 x=np.rint(result.x).astype(int);counts=[int(round(v@x)) for v in countv]
 for v,value in zip(countv,counts):A=vstack([A,csr_matrix(v.reshape(1,-1))],format='csr');lo=np.append(lo,value);hi=np.append(hi,value)
 turnover=np.r_[np.zeros(n),[float(D(z['debit'])+D(z['credit']))/1e6 for z in candidates]]
 result=milp(c=turnover,integrality=np.ones(2*n),bounds=Bounds(lb,ub),constraints=LinearConstraint(A,lo,hi),options={'mip_rel_gap':0.,'time_limit':120.})
 assert result.status==0 and result.success and result.mip_gap==0.,('TURNOVER_SOLVE_BLOCKED',state['state_key'],accept,result.message)
 x=np.rint(result.x).astype(int);assert max(abs(result.x-x))<1e-5
 selected=[dict(z,quantity=int(x[n+i])*100) for i,z in enumerate(candidates) if x[i]]
 assert all(x[n+i]>=x[i] and x[n+i]<=maxlots[i]*x[i] for i in range(n))
 assert (current in {z['entry_id'] for z in selected})==accept
 exact_cash=[]
 for t in times:
  c=cash+sum((D(p['credit']) for p in held_releases if p['release_minute']<=t),D(0))+sum((((D(z['credit']) if z['release_minute']<=t else D(0))-(D(z['debit']) if z['entry_minute']<=t else D(0)))*(z['quantity']//100) for z in selected),D(0))
  assert c>=0,('EXACT_CASH_FAIL',state['state_key'],accept,str(c))
  assert sum(p['release_minute']>t for p in held_releases)+sum(z['entry_minute']<=t<z['release_minute'] for z in selected)<=3
  exact_cash.append(c)
 base=[sum(labels[k]['potential_return']>=threshold for k in state['funded_prefix_ids']) for threshold in (.05,.1)]+[sum(.03<=labels[k]['potential_return']<.05 for k in state['funded_prefix_ids'])]
 total=[a+b for a,b in zip(base,counts)];turn=sum(((D(z['debit'])+D(z['credit']))*(z['quantity']//100) for z in selected),D(0))
 return {'U5':total[0],'U10':total[1],'Medium':total[2],'continuation_turnover':str(turn),'counts_incremental':counts,'selected':selected,'cash_min':str(min(exact_cash)),'count_solver_gap':0.,'turnover_solver_gap':0.}
def action(current_U5,accept,reserve):
 a=(accept['U5'],accept['U10'],accept['Medium'],-D(accept['continuation_turnover']));r=(reserve['U5'],reserve['U10'],reserve['Medium'],-D(reserve['continuation_turnover']))
 if current_U5 and a[0]>=r[0]:return 'ACCEPT','CURRENT_U5_EQUAL_OR_HIGHER_TOTAL_U5_PRIORITY'
 return ('ACCEPT','LEX_OR_COMPLETE_TIE_ACCEPT') if a>=r else ('RESERVE','LEX_RESERVE')
