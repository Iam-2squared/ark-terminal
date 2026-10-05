"""Precommitted evaluation only. Runtime and trainer never import this module."""
import numpy as np
from scipy.stats import spearmanr, rankdata
from sklearn.metrics import roc_auc_score, average_precision_score
SCORES=['pP','q2','q3','consensus']
def binary(y,s,w=None):
    y=np.asarray(y);s=np.asarray(s);w=np.ones(len(y)) if w is None else np.asarray(w)
    if sum(w[y==1])==0 or sum(w[y==0])==0:return {'AUC':None,'PR_AUC':None}
    return {'AUC':float(roc_auc_score(y,s,sample_weight=w)),'PR_AUC':float(average_precision_score(y,s,sample_weight=w))}
def concordance(rr,score,same_session=False):
    groups={}
    for i,r in enumerate(rr):groups.setdefault((r['session'] if same_session else r['block'],r['bucket']),[]).append(i)
    credit=0.;pairs=0;detail=[]
    for key,ii in sorted(groups.items()):
        a=np.array([rr[i]['realized'] for i in ii]);s=np.array([rr[i][score] for i in ii])
        i,j=np.triu_indices(len(ii),1);ok=a[i]!=a[j];i=i[ok];j=j[ok]
        high=np.where(a[i]>a[j],i,j);low=np.where(a[i]>a[j],j,i)
        c=float(np.sum((s[high]>s[low]).astype(float)+.5*(s[high]==s[low])));n=len(i)
        pairs+=n;credit+=c;detail.append({'group':list(key),'valid_pairs':n,'credit':c,'concordance':c/n if n else None})
    return {'concordance':credit/pairs if pairs else None,'valid_pairs':pairs,'credit':credit,'groups':detail,'pairs_independent_samples':False}
def summary(rr,score):
    y=[r['label'] for r in rr];s=[r[score] for r in rr];a=binary(y,s)
    order=sorted(rr,key=lambda r:(-r[score],r['entry_id']));base=sum(y)/len(y)
    top={}
    for pct in (.2,.3):
        n=int(np.ceil(len(rr)*pct));rate=sum(r['label'] for r in order[:n])/n
        top[str(int(pct*100))]={'N':n,'observed_rate':rate,'enrichment':rate/base if base else None}
    deciles=[]
    for d,ii in enumerate(np.array_split(np.arange(len(order)),10),1):
        q=[order[int(i)] for i in ii]
        deciles.append({'decile':d,'N':len(q),'score_mean':float(np.mean([r[score] for r in q])),'MRET_observed_rate':sum(r['label'] for r in q)/len(q)})
    realized=[r['realized'] for r in rr]
    out={'N':len(rr),'positive_N':sum(y),'MRET':a|{'Brier':float(np.mean((np.array(s)-np.array(y))**2))},'blocks':{str(b):binary([r['label'] for r in rr if r['block']==b],[r[score] for r in rr if r['block']==b]) for b in range(1,9)},'Top':top,'deciles':deciles,'conditional':concordance(rr,score),'same_session_conditional':concordance(rr,score,True)}
    out['realized']={k:binary([int(fn(r['realized'])) for r in rr],s)['AUC'] for k,fn in [('positive_AUC',lambda x:x>0),('ge1_AUC',lambda x:x>=.01),('loser_AUC',lambda x:x<=0)]}
    out['realized']['Spearman']=float(spearmanr(s,realized).statistic)
    return out
def pair_kernel(rr,score,target,sessions):
    index={s:i for i,s in enumerate(sessions)};num=np.zeros((len(sessions),len(sessions)));den=np.zeros_like(num)
    sc=np.array([r[score] for r in rr]);ss=np.array([index[r['session']] for r in rr])
    if target=='conditional':
        yy=np.array([r['realized'] for r in rr]);i,j=np.triu_indices(len(rr),1)
        ok=(yy[i]!=yy[j])&np.array([rr[a]['block']==rr[b]['block'] and rr[a]['bucket']==rr[b]['bucket'] for a,b in zip(i,j)])
        i=i[ok];j=j[ok];hi=np.where(yy[i]>yy[j],i,j);lo=np.where(yy[i]>yy[j],j,i)
    else:
        yy=np.array([r['label'] if target=='MRET' else int(r['realized']>0) for r in rr])
        pp=np.where(yy==1)[0];nn=np.where(yy==0)[0];hi=np.repeat(pp,len(nn));lo=np.tile(nn,len(pp))
    c=(sc[hi]>sc[lo]).astype(float)+.5*(sc[hi]==sc[lo])
    np.add.at(num,(ss[hi],ss[lo]),c);np.add.at(den,(ss[hi],ss[lo]),1)
    return num,den
def weighted_spearman(s,y,w):
    s=np.asarray(s);y=np.asarray(y);w=np.asarray(w)
    def rank(v):
        order=np.argsort(v,kind='stable');out=np.zeros(len(v));before=0.;j=0
        while j<len(v):
            k=j+1
            while k<len(v) and v[order[k]]==v[order[j]]:k+=1
            idx=order[j:k];mass=float(w[idx].sum());out[idx]=before+(mass+1)/2;before+=mass;j=k
        return out
    x=rank(s);z=rank(y);n=w.sum();x=x-(x*w).sum()/n;z=z-(z*w).sum()/n
    div=np.sqrt((w*x*x).sum()*(w*z*z).sum())
    return float((w*x*z).sum()/div) if div else None
def bootstrap(rr,best,sessions):
    seed=5701105;draw=np.random.default_rng(seed).integers(0,len(sessions),size=(1999,len(sessions)))
    cc=np.array([np.bincount(x,minlength=len(sessions)) for x in draw]);pos={s:i for i,s in enumerate(sessions)}
    samples={k:[] for k in ['MRET_AUC_delta','MRET_PR_delta','conditional_delta','realized_positive_AUC_delta','Spearman_delta']}
    for target,key in [('MRET','MRET_AUC_delta'),('conditional','conditional_delta'),('positive','realized_positive_AUC_delta')]:
        vals=[]
        for score in ['mP',best]:
            n,d=pair_kernel(rr,score,target,sessions)
            numerator=np.einsum('bi,ij,bj->b',cc,n,cc);denominator=np.einsum('bi,ij,bj->b',cc,d,cc)
            vals.append(np.divide(numerator,denominator,out=np.full(1999,np.nan),where=denominator>0))
        samples[key]=(vals[0]-vals[1]).tolist()
    yy=np.array([r['label'] for r in rr]);real=np.array([r['realized'] for r in rr]);idx=np.array([pos[r['session']] for r in rr]);scores={s:np.array([r[s] for r in rr]) for s in ['mP',best]}
    for c in cc:
        w=c[idx];ap=[binary(yy,scores[s],w)['PR_AUC'] for s in ['mP',best]]
        sp=[weighted_spearman(scores[s],real,w) for s in ['mP',best]]
        samples['MRET_PR_delta'].append(ap[0]-ap[1] if None not in ap else None)
        samples['Spearman_delta'].append(sp[0]-sp[1] if None not in sp else None)
    results={}
    clean=[]
    for i in range(1999):clean.append({'resample':i+1,**{k:float(v[i]) if v[i] is not None and np.isfinite(v[i]) else None for k,v in samples.items()}})
    for k,v in samples.items():
        a=np.array([x for x in v if x is not None and np.isfinite(x)])
        results[k]={'valid_N':len(a),'mean':float(a.mean()),'CI95':np.quantile(a,[.025,.975],method='linear').tolist()}
    return {'seed':seed,'resamples':1999,'unit':'OOF38_SESSION_CLUSTER','independent_session_N':len(sessions),'best_control':best,'deltas':results},clean,cc
