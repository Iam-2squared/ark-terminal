"""Frozen-score diagnostics. No fit, probability calibration, market replay or intents."""
import numpy as np
from scipy.stats import rankdata
SEED=570100520;B=1999
def ci(values,conditioning=None):
 a=np.asarray(values,dtype=float);a=a[np.isfinite(a)]
 return {'CI95':np.quantile(a,[.025,.975],method='linear').tolist() if len(a) else None,'valid_N':int(len(a)),'invalid_N':B-int(len(a)),'resamples':B,'seed':SEED,'bit_generator':'PCG64','unit':'session_cluster','quantile':'linear','conditioning':conditioning}
def weight_stream(sessions):
 rng=np.random.Generator(np.random.PCG64(SEED));n=len(sessions)
 draws=rng.integers(0,n,size=(B,n));out=np.zeros((B,n),dtype=np.int64)
 for i,d in enumerate(draws):out[i]=np.bincount(d,minlength=n)
 return out
def auc_ap(s,y,w=None):
 s=np.asarray(s,float);y=np.asarray(y,int);w=np.ones((1,len(s))) if w is None else np.asarray(w,float)
 order=np.argsort(s,kind='stable');sv=s[order];yv=y[order];ww=w[:,order]
 starts=np.r_[0,1+np.flatnonzero(sv[1:]!=sv[:-1])]
 pos=np.add.reduceat(ww*yv,starts,axis=1);neg=np.add.reduceat(ww*(1-yv),starts,axis=1)
 P=pos.sum(axis=1);N=neg.sum(axis=1)
 with np.errstate(divide='ignore',invalid='ignore'):
  auc=(pos*(np.cumsum(neg,axis=1)-.5*neg)).sum(axis=1)/(P*N)
  pd=pos[:,::-1];nd=neg[:,::-1];cp=np.cumsum(pd,axis=1);cn=np.cumsum(nd,axis=1)
  ap=(np.divide(cp,cp+cn,out=np.zeros_like(cp),where=cp+cn!=0)*pd).sum(axis=1)/P
 auc[(P==0)|(N==0)]=np.nan;ap[(P==0)|(N==0)]=np.nan
 return auc,ap
def weighted_spearman(s,y,w):
 s=np.asarray(s,float);y=np.asarray(y,float);w=np.asarray(w,float)
 def wrank(v):
  ix=np.argsort(v,kind='stable');sv=v[ix];starts=np.r_[0,1+np.flatnonzero(sv[1:]!=sv[:-1])]
  g=np.add.reduceat(w[:,ix],starts,axis=1);r=np.cumsum(g,axis=1)-.5*g
  spans=np.diff(np.r_[starts,len(v)]);res=np.empty_like(w);res[:,ix]=np.repeat(r,spans,axis=1);return res
 a=wrank(s);b=wrank(y);tot=w.sum(axis=1)
 with np.errstate(divide='ignore',invalid='ignore'):
  a=a-(w*a).sum(axis=1)[:,None]/tot[:,None];b=b-(w*b).sum(axis=1)[:,None]/tot[:,None]
  res=(w*a*b).sum(axis=1)/np.sqrt((w*a*a).sum(axis=1)*(w*b*b).sum(axis=1))
 return res
def cluster_auc(s,y,sidx,multiplicity):
 """Fixed contract: same-session pair m once, cross-session pair m_i*m_j.

 Start with row-weighted ROC numerator, remove only excess within-session replicas.
 Point ROC remains the native unweighted AUC. AP is a row functional, not pair count.
 """
 s=np.asarray(s,float);y=np.asarray(y,int);idx=np.asarray(sidx,int);M=np.asarray(multiplicity,float)
 w=M[:,idx];P=(w*y).sum(axis=1);N=(w*(1-y)).sum(axis=1);old,_=auc_ap(s,y,w);den=P*N;num=np.nan_to_num(old)*den
 for session in np.unique(idx):
  keep=idx==session;pp=y[keep].sum();nn=keep.sum()-pp
  if pp==0 or nn==0:continue
  a,_=auc_ap(s[keep],y[keep]);excess=M[:,session]*(M[:,session]-1);den-=excess*pp*nn;num-=excess*pp*nn*a[0]
 return np.divide(num,den,out=np.full(len(M),np.nan),where=den>0)
def concordance(s,y,groups,sidx,multiplicity):
 n=len(s);a,b=np.triu_indices(n,1);s=np.asarray(s);y=np.asarray(y);g=np.asarray(groups);idx=np.asarray(sidx)
 keep=(g[a]==g[b])&(y[a]!=y[b]);a=a[keep];b=b[keep]
 credit=(1+np.sign(s[a]-s[b])*np.sign(y[a]-y[b]))/2
 ns=multiplicity.shape[1];key=idx[a]*ns+idx[b]
 D=np.bincount(key,minlength=ns*ns).reshape(ns,ns).astype(float);C=np.bincount(key,weights=credit,minlength=ns*ns).reshape(ns,ns)
 diagD=np.diag(D).copy();diagC=np.diag(C).copy();np.fill_diagonal(D,0);np.fill_diagonal(C,0)
 den=np.einsum('bi,ij,bj->b',multiplicity,D,multiplicity)+multiplicity@diagD
 num=np.einsum('bi,ij,bj->b',multiplicity,C,multiplicity)+multiplicity@diagC
 value=np.divide(num,den,out=np.full(len(num),np.nan),where=den!=0)
 return {'concordance':float(credit.mean()) if len(a) else None,'valid_pairs':len(a),'credit':float(credit.sum()),'pairs_independent_samples':False,'null_reason':None if len(a) else 'NO_PAIR','bootstrap':ci(value),'same_session_weight':'multiplicity_once','different_session_weight':'endpoint_product'},value
