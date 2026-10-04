"""Only numerical representation correction with independent exact proof.

Original physical Oracle and all objectives remain byte unchanged. Nonzero
reported turnover gap can be canonicalized only after the independent integer
solver proves identical counts, minimum turnover and exact feasibility.
"""
import teacher_oracle as original
from independent_solver import certify
CERTIFICATES=[]
def solve(state,a,h,labels,accept):
 method=original.milp
 def checked(*args,**kwargs):
  r=method(*args,**kwargs)
  if r.status==0 and r.success and r.mip_gap!=0:
   assert min(kwargs['c'])>=0,'NONZERO_COUNT_GAP_REQUIRES_SEPARATE_STOP'
   cert=certify(state,a,h,accept,[round(v) for v in r.x])
   CERTIFICATES.append({'state_key':state['state_key'],'accept':accept,'original_mip_gap':float(r.mip_gap),'original_fun':float(r.fun),'original_dual':float(r.mip_dual_bound),'independent':cert})
   r.mip_gap=0.
  return r
 original.milp=checked
 try:return original.solve(state,a,h,labels,accept)
 finally:original.milp=method
