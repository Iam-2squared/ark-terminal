"""V5 saved rows/draws only, implementation sanity without fit/new label/draw."""
from pathlib import Path
from collections import Counter
import json,math,hashlib
import numpy as np
import METRICS_V6 as m
import AUDIT_METRICS_V6 as a
R=Path(__file__).resolve().parent;V=R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1'
def main():
 oo=list(map(json.loads,(V/'R1_R2_FRESH_OOF_V5.jsonl').open()));vec=json.loads((V/'BOOTSTRAP_GLOBAL_DATE_DRAWS_V5.json').read_text());ds=vec['dates'];w=np.array([np.bincount(v,minlength=len(ds)) for v in vec['draws']]);checks=0
 for control in ['REAL','TRUE_NULL']:
  for model in ['R1','R2']:
   for cal in [False,True]:
    rr=[r for r in oo if r['control']==control and r['model']==model and r['calibrated']==cal];point,rep,cm=m.point_and_reps(rr,ds,w);expected=a.measure(rr);replay=a.cluster_replicates(rr,ds,vec['draws'])
    for k,v in expected.items():assert a.near(point[k],v),'POINT_SANITY:'+k;checks+=1
    for k in m.CI_KEYS:assert np.allclose(rep[k],replay[k],equal_nan=True,atol=1e-10),'REPLICATE_SANITY:'+k;checks+=1
   r1=[r for r in oo if r['control']=='REAL' and r['model']=='R1' and not r['calibrated']];r2=[r for r in oo if r['control']=='REAL' and r['model']=='R2' and not r['calibrated']];p1,b1,_=m.point_and_reps(r1,ds,w);p2,b2,_=m.point_and_reps(r2,ds,w);lo,hi,n=m.interval(100*(b1['dangerous_rate']-b2['dangerous_rate']),True);assert abs(lo-1.0824449690224203)<1e-8 and abs(hi-6.758631829640437)<1e-8,'V5_STORED_CI_SANITY';checks+=1
 receipt={'status':'PASS','checks':checks,'source':'immutable V5 saved OOF/global1000 vectors only','V5_OOF_SHA256':hashlib.sha256((V/'R1_R2_FRESH_OOF_V5.jsonl').read_bytes()).hexdigest(),'V6_new_labels':0,'new_fits':0,'new_bootstrap_draws':0,'V5_result_changes':0,'method_changes':0};p=R/'EXPOSED_IMPLEMENTATION_SANITY_V6.json';assert not p.exists();p.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
