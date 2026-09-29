"""Fixed session-cluster descriptive bootstrap of saved outcomes only."""
from __future__ import annotations
import gzip,json,platform
from pathlib import Path
import numpy as np
import scipy
from scipy.stats import rankdata
from scripts.phase57_post_prr_a_plus import OUT,D,S,sha,write

def rows():
 with gzip.open(OUT/'INTENT_UNIVERSE_ROWS.jsonl.gz','rt') as f:return [json.loads(x) for x in f]
def quant(v,p):
 v=np.sort(v);h=(len(v)-1)*p;k=int(h);return float(v[k]*(1-(h-k))+v[min(k+1,len(v)-1)]*(h-k))
def ci(v):
 a=np.asarray(v,dtype=float);v=a[np.isfinite(a)]
 return {'validB':len(v),'invalidB':len(a)-len(v),'low':quant(v,.025) if len(v) else None,'high':quant(v,.975) if len(v) else None}
def corr(x,y):
 if len(x)<2 or np.all(x==x[0]) or np.all(y==y[0]):return np.nan
 a=rankdata(x,method='average');b=rankdata(y,method='average');a-=a.mean();b-=b.mean()
 den=np.sqrt((a*a).sum()*(b*b).sum())
 return float((a*b).sum()/den) if den else np.nan
def main():
 spec=json.loads((OUT/'ANALYSIS_SPEC.json').read_text())['bootstrap']
 assert spec['seed']==20260929 and spec['B']==10000 and spec['generator']=='numpy.PCG64'
 a=rows()
 sessions=sorted({r['session'] for r in a});assert len(sessions)==24
 rng=np.random.Generator(np.random.PCG64(20260929));ids=rng.integers(0,24,size=(10000,24),dtype=np.int16)
 draws=np.zeros((10000,24),dtype=np.int16)
 for j in range(24):draws[:,j]=(ids==j).sum(axis=1)
 np.savez_compressed(OUT/'SESSION_DRAWS.npz',session_counts=draws,session_ids=np.asarray(sessions))
 bspec={'schema':'phase57-a-plus-bootstrap-v1','seed':20260929,'generator':'numpy.PCG64','numpy':np.__version__,'scipy':scipy.__version__,'python':platform.python_version(),'B':10000,'sessionIds':sessions,'sampleSizeClusters':24,'drawSha256':sha(OUT/'SESSION_DRAWS.npz'),'quantile':'linear h=(Bvalid−1)*p; invalid draws retained as null, never redrawn','sharedDraws':True,'source':'repeatedly exposed Development; conditional descriptive uncertainty only'}
 write('BOOTSTRAP_SPEC.json',bspec)
 out={};arrays={}
 for arm in ('IM','R1'):
  for world in ('ALL_100','PRIMARY_100','PRIMARY_FUNDED','PRIMARY_OUTSIDE_100'):
   for typ in ('ALL','I','E'):
    for comp,field,netfield in (('component','deltaPnlJpy','deltaNetPp'),('frozenRoute','routeDeltaPnlJpy','routeDeltaNetPp')):
     z=[r for r in a if r['arm']==arm and (r['world']=='PRIMARY_FUNDED' if world=='PRIMARY_FUNDED' else r['world']=='ALL_100' and (world=='ALL_100' or (r['primary'] if world=='PRIMARY_100' else not r['primary']))) and (typ=='ALL' or typ=='I' and r['firstIntentKnown'] or typ=='E' and r['provisionalEligibility']) and r['labelKnown'] and r[field] is not None]
     s=np.array([sessions.index(r['session']) for r in z]);v=np.array([float(D(r[field])) for r in z]);n=np.array([float(D(r[netfield])) for r in z])
     sv=np.bincount(s,weights=v,minlength=24);sn=np.bincount(s,weights=n,minlength=24);sc=np.bincount(s,minlength=24)
     total=draws@sv;den=draws@sc;net=(draws@sn)/np.where(den==0,1,den);net[den==0]=np.nan
     key='|'.join([arm,world,typ,comp]);arrays[key]=(total,net)
     out[key]={'N_known':len(z),'sessionN':len(set(s)),'mask':'paired outcome known K','sumDeltaJpy':{'point':float(v.sum()),**ci(total)},'meanDeltaNetPp':{'point':float(n.mean()) if len(n) else None,**ci(net)}}
 for arm in ('IM','R1'):
  for typ in ('ALL','I','E'):
   for head in ('5','10'):
    z=[r for r in a if r['arm']==arm and r['world']=='ALL_100' and r['labelKnown'] and (typ=='ALL' or typ=='I' and r['firstIntentKnown'] or typ=='E' and r['provisionalEligibility'])]
    s=np.array([sessions.index(r['session']) for r in z]);x=np.array([r['score'+head] for r in z]);y=np.array([float(D(r['deltaNetPp'])) for r in z]);reps=np.empty(10000)
    for i,draw in enumerate(draws):
     idx=np.repeat(np.arange(len(z)),draw[s]);reps[i]=corr(x[idx],y[idx])
    out['|'.join([arm,typ,'head'+head])]={'N_known':len(z),'sessionN':len(set(s)),'scoreDeltaNetPpSpearman':{'point':corr(x,y),**ci(reps)}}
 contrasts={}
 for arm in ('IM','R1'):
  for typ in ('ALL','I','E'):
   for world in ('ALL_100','PRIMARY_100','PRIMARY_FUNDED','PRIMARY_OUTSIDE_100'):
    c=arrays['|'.join([arm,world,typ,'component'])];r=arrays['|'.join([arm,world,typ,'frozenRoute'])]
    contrasts[arm+'|'+world+'|'+typ+'|component_minus_route']={'sumDeltaJpy':ci(c[0]-r[0]),'meanDeltaNetPp':ci(c[1]-r[1])}
 # Same session-draw contrast between alternative Entry worlds, not independent samples.
 for typ in ('ALL','I','E'):
  c=arrays['IM|ALL_100|'+typ+'|component'];r=arrays['R1|ALL_100|'+typ+'|component']
  contrasts[typ+'|IM_minus_R1']={'sumDeltaJpy':ci(c[0]-r[0]),'meanDeltaNetPp':ci(c[1]-r[1])}
 for arm in ('IM','R1'):
  for typ in ('ALL','I','E'):
   f=arrays[arm+'|PRIMARY_FUNDED|'+typ+'|component'];p=arrays[arm+'|PRIMARY_100|'+typ+'|component']
   contrasts[arm+'|'+typ+'|funded_minus_primary100']={'sumDeltaJpy':ci(f[0]-p[0]),'meanDeltaNetPp':ci(f[1]-p[1])}
 write('CLUSTER_CI_RESULTS.json',{'schema':'phase57-a-plus-ci-v1','bootstrapSpecSha256':sha(OUT/'BOOTSTRAP_SPEC.json'),'estimates':out,'directContrasts':contrasts,'noIndependenceClaim':True,'notMissingnessCorrected':True})
 print('BOOTSTRAP',sha(OUT/'CLUSTER_CI_RESULTS.json'))
if __name__=='__main__':main()
