"""Worker accepts only a declared train or prediction view. No manager outcomes."""
import os, sys, pickle, pathlib, json, math
import numpy as np
import scipy, sklearn
from scipy.special import logsumexp, softmax
from scipy.optimize import minimize
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits
from common import PRICE, STATE, CAT, VOCAB, canonical, sha, rows, gzsave, save

def lock_data_view(view):
 # Linux mount namespaces are unavailable in this runtime. A separate OS user
 # plus a Python file-open audit guard enforces the declared data view instead.
 allowed=[view.resolve(),pathlib.Path(sys.prefix).resolve(),pathlib.Path(__file__).parent.resolve(),pathlib.Path('/usr/lib'),pathlib.Path('/lib'),pathlib.Path('/etc'),pathlib.Path('/proc'),pathlib.Path('/dev')]
 def audit(event,args):
  if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
   p=pathlib.Path(os.fsdecode(args[0])).resolve()
   if not any(p==a or a in p.parents for a in allowed):raise PermissionError('WORKER_VIEW_VIOLATION:'+str(p))
 sys.addaudithook(audit)
 isolation='DECLARED_INPUT_VIEW_WITH_OPEN_AUDIT'
 if os.getuid()==0:
  try:os.setgroups([]);os.setgid(65534);os.setuid(65534);isolation+=';UID65534'
  except PermissionError:isolation+=';UID_CHANGE_NOT_PERMITTED'
 # Probe access denial without reading any manager data or outcome content.
 forbidden=pathlib.Path(__file__).resolve().parents[1]/'private/EVALUATION_R_NEW_REUSED.jsonl.gz'
 try:
  with forbidden.open('rb'):pass
  raise AssertionError('WORKER_MANAGER_FILE_ACCESS_ALLOWED')
 except PermissionError:pass
 save(view/'WORKER_INPUT_ACCESS_AUDIT.json',{'isolation':isolation,'manager_outcome_open_denied':True,'physical_blindness':False})

def matrix(rr,fields):
 numeric=np.asarray([[np.nan if r['numeric'][k] is None else r['numeric'][k] for k in fields] for r in rr],dtype=np.float64)
 catcols=[k for k in CAT] if len(fields)>45 else []
 onehot=np.asarray([[float((r['categorical'].get(k) if r['categorical'].get(k) in VOCAB[k] else 'UNKNOWN')==v) for k in catcols for v in VOCAB[k]] for r in rr],dtype=np.float64)
 return numeric,onehot

def preprocess(rr,fields,linear,model=None):
 a,c=matrix(rr,fields);missing=np.isnan(a).astype(np.float64)
 if model is None:
  med=np.asarray([np.median(col[np.isfinite(col)]) if np.any(np.isfinite(col)) else 0. for col in a.T]);allmissing=np.all(np.isnan(a),axis=0)
 else:med=np.asarray(model['median']);allmissing=np.asarray(model['all_missing_train'])
 b=np.concatenate([np.where(np.isnan(a),med,a),missing,c],axis=1)
 if model is None:
  mean=b.mean(axis=0) if linear else np.zeros(b.shape[1]);scale=b.std(axis=0) if linear else np.ones(b.shape[1]);scale[scale==0]=1.
 else:mean=np.asarray(model['mean']);scale=np.asarray(model['scale'])
 pre={'median':med.tolist(),'all_missing_train':allmissing.tolist(),'mean':mean.tolist(),'scale':scale.tolist(),'numeric_fields':fields,'onehot_vocabulary':{k:VOCAB[k] for k in CAT} if len(fields)>45 else {},'final_dimension':b.shape[1],'standardized':linear}
 return (b-mean)/scale,pre

def fit_linear(X,y):
 n,d=X.shape
 def objective(v):
  beta=v[:4*d].reshape(4,d);inter=v[4*d:];logits=np.c_[X@beta.T+inter,np.zeros(n)];lp=logits-logsumexp(logits,axis=1,keepdims=True);p=np.exp(lp)
  loss=-lp[np.arange(n),y].mean()+.005*np.sum(beta*beta);p[np.arange(n),y]-=1.;g=p[:,:4]/n
  grad=np.r_[(g.T@X+.01*beta).ravel(),g.sum(axis=0)]
  return float(loss),grad
 result=minimize(objective,np.zeros(4*d+4,dtype=np.float64),jac=True,method='L-BFGS-B',options={'maxiter':1000,'gtol':1e-7,'ftol':0.,'maxls':50})
 gradnorm=float(np.max(np.abs(result.jac)));converged=gradnorm<=1e-7 and result.success
 return {'beta':result.x[:4*d].reshape(4,d).tolist(),'intercept':result.x[4*d:].tolist(),'class_order':[0,1,2,3,4],'iterations':int(result.nit),'gradient_infinity_norm':gradnorm,'converged':bool(converged),'optimizer_message':str(result.message),'final_objective':float(result.fun)}

def probability(rr,model):
 X,_=preprocess(rr,model['numeric_fields'],model['method']=='D-LINEAR',model['preprocessing'])
 if model['method']=='D-LINEAR':
  z=model['learner'];p=softmax(np.c_[X@np.asarray(z['beta']).T+np.asarray(z['intercept']),np.zeros(len(X))],axis=1)
 else:p=model['learner'].predict_proba(X)
 assert p.shape==(len(rr),5) and np.all(p>=0) and np.all(p<=1)
 assert np.max(np.abs(p.sum(axis=1)-1))<=8*np.finfo(float).eps
 return p

def main(view,mode,method):
 view=pathlib.Path(view);lock_data_view(view)
 with threadpool_limits(limits=1):
  if mode=='fit':
   rr=rows(view/'train.jsonl.gz');y=np.asarray([r['target'] for r in rr],dtype=np.int64);assert set(y)==set(range(5))
   fields=PRICE if method=='D-PRICE' else PRICE+STATE;X,pre=preprocess(rr,fields,method=='D-LINEAR')
   if method=='D-LINEAR':learner=fit_linear(X,y);converged=learner['converged']
   else:
    learner=HistGradientBoostingClassifier(loss='log_loss',learning_rate=.05,max_iter=100,max_leaf_nodes=7,max_depth=3,min_samples_leaf=20,l2_regularization=1.,max_features=1.,max_bins=64,categorical_features=None,monotonic_cst=None,interaction_cst=None,warm_start=False,early_stopping=False,scoring='loss',validation_fraction=.1,n_iter_no_change=10,tol=1e-7,verbose=0,random_state=57,class_weight=None);learner.fit(X,y);converged=learner.n_iter_==100 and learner.n_trees_per_iteration_==5
   model={'method':method,'numeric_fields':fields,'preprocessing':pre,'learner':learner,'train_ID_hash':sha(canonical([r['entry_id'] for r in rr])),'train_N':len(rr),'converged':bool(converged),'dtype':'float64','threads':1}
   b=pickle.dumps(model,protocol=5);(view/'model.pkl').write_bytes(b)
   save(view/'fit_result.json',{'converged':bool(converged),'model_sha256':sha(b),'train_N':len(rr),'train_ID_hash':model['train_ID_hash'],'preprocessing_sha256':sha(canonical(pre)),'dimension':X.shape[1],'iterations':learner['iterations'] if method=='D-LINEAR' else learner.n_iter_,'gradient_infinity_norm':learner['gradient_infinity_norm'] if method=='D-LINEAR' else None,'tree_N':None if method=='D-LINEAR' else learner.n_iter_*learner.n_trees_per_iteration_,'optimizer_message':learner.get('optimizer_message') if method=='D-LINEAR' else None})
  else:
   model=pickle.loads((view/'model.pkl').read_bytes());rr=rows(view/'evaluate.jsonl.gz');p=probability(rr,model) if rr else np.empty((0,5));out=[]
   for r,a in zip(rr,p):
    q5=float(a[0]);q3=float(a[0]+a[1]);q2=float(a[0]+a[1]+a[2]);qneg=float(a[:4].sum());assert 0<=q5<=q3<=q2<=qneg<=1
    out.append({'entry_id':r['entry_id'],'p5':a.tolist(),'q5':q5,'q3':q3,'q2':q2,'qNEG':qneg,'feature_asof':r['feature_asof']})
   gzsave(view/'probabilities.jsonl.gz',out)
if __name__=='__main__':main(sys.argv[1],sys.argv[2],sys.argv[3])
