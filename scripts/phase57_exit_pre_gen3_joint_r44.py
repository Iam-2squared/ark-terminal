"""Resolve handoff metric denominator: common full-window label-eligible rows."""
import argparse,json,gzip
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
from scripts import phase57_exit_finite_r36 as b

def run(core,gen2,out):
 labels=np.load(gen2/'data/training-labels.npz');pred=np.load(gen2/'oof-predictions.npz');meta=[]
 for session in b.r25.development_sessions():
  with gzip.open(core/'core-a/checkpoints'/f'{session}.jsonl.gz','rt')as f:rows=sorted((json.loads(l)for l in f),key=lambda r:(b.ARMS.index(r['identity'][0]),r['identity'][1],r['identity'][2]))
  meta.extend((b.ARMS.index(r['identity'][0]),r['fresh'])for r in rows)
 meta=np.asarray(meta);assert len(meta)==len(labels['targets'])==656247
 full=(labels['horizonBars']==[60,15]).all(axis=1);available=labels['available'].all(axis=1);scored=np.isfinite(pred[pred.files[0]]).all(axis=1)
 results=[]
 for ai,arm in enumerate(b.ARMS):
  ix=(meta[:,0]==ai)&meta[:,1].astype(bool)&full&available&scored;y=labels['targets'][ix]
  results.append({'arm':arm,'denominator':'fresh OOF, both C60/F15 full calendar windows and both labels available','n':int(ix.sum()),'labelPearsonPhi':float(np.corrcoef(y.T)[0,1]),'modelSpecs':{spec:{'Cauc':float(roc_auc_score(y[:,0],pred[spec][ix,0])),'Fauc':float(roc_auc_score(y[:,1],pred[spec][ix,1])),'scoreCorrelation':float(np.corrcoef(pred[spec][ix].T)[0,1])}for spec in pred.files}})
 b.write_json(out,{'results':results,'gen3Fits':0,'gen3Replays':0,'labelSourceSha256':b.sha(gen2/'data/training-labels.npz'),'predictionSha256':b.sha(gen2/'oof-predictions.npz'),'interpretation':'Availability-conditioned and unconditional fresh-OOF correlations are distinct; label overlap alone is not a causal explanation of score correlation.'});print(json.dumps(results,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--core',type=Path);p.add_argument('--gen2',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();run(a.core,a.gen2,a.out)
