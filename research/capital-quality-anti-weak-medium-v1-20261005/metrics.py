"""Precommitted quality metrics; no fit, threshold, blend, allocator or replay."""
from collections import Counter
import math
import numpy as np
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score, average_precision_score

FRACTIONS=[.10,.20,.30,.40]
BUCKETS=['Q0_WEAK','Q1_LOW','Q2_MEDIUM','Q3_BIG','Q4_MEGA']

def order(data,score):
    if score=='legacy_ML':
        return sorted(range(len(data)),key=lambda i:(-data[i][score],-data[i]['legacy_m5'],-data[i]['legacy_m3'],-data[i]['legacy_m2'],data[i]['entry_timestamp'],data[i]['symbol'],data[i]['entry_id']))
    return sorted(range(len(data)),key=lambda i:(-data[i][score],data[i]['entry_timestamp'],data[i]['symbol'],data[i]['entry_id']))

def auc_pr(y,s,w=None):
    y=np.asarray(y);s=np.asarray(s)
    if w is not None:
        keep=np.asarray(w)>0;y=y[keep];s=s[keep];w=np.asarray(w)[keep]
    if len(np.unique(y))!=2:return {'AUC':None,'PR_AUC':None}
    return {'AUC':float(roc_auc_score(y,s,sample_weight=w)), 'PR_AUC':float(average_precision_score(y,s,sample_weight=w))}

def quality(data,score):
    ordered=order(data,score);n=len(data)
    positives={u:sum(r[f'U{u}'] for r in data) for u in [2,3,5,10]}
    top=[];bottom=[]
    for f in FRACTIONS:
        k=math.ceil(n*f);picked=[data[i] for i in ordered[:k]]
        uu={u:sum(r[f'U{u}'] for r in picked) for u in [2,3,5,10]}
        top.append({'fraction':f,'selected_N':k,'below2_N':k-uu[2],'below2_rate':(k-uu[2])/k,
            'below3_N':k-uu[3],'below3_rate':(k-uu[3])/k,'Medium_N':uu[3]-uu[5],
            **{f'U{u}_N':uu[u] for u in uu}, **{f'U{u}_density':uu[u]/k for u in uu},
            **{f'U{u}_capture':uu[u]/positives[u] for u in uu},
            'realized_PnL_diagnostic':{name:sum(r['realized_net_return_diagnostic_only'] is not None and condition(r['realized_net_return_diagnostic_only']) for r in picked)
                for name,condition in [('le0',lambda x:x<=0),('le_minus1',lambda x:x<=-.01),('le_minus3',lambda x:x<=-.03),('ge_plus1',lambda x:x>=.01)]}})
        if f<=.30:
            weak=sum(data[i]['WEAK2'] for i in ordered[-k:])
            bottom.append({'fraction':f,'selected_N':k,'Weak_N':weak,'Weak_density':weak/k,'Weak_capture':weak/(n-positives[2])})
    blocks={}
    for bl in range(1,9):
        rr=[r for r in data if r['block']==bl]
        blocks[str(bl)]={'N':len(rr), **{f'U{u}':auc_pr([r[f'U{u}'] for r in rr],[r[score] for r in rr]) for u in [2,3]}}
    return {'score':score,'N':n,**{f'U{u}':auc_pr([r[f'U{u}'] for r in data],[r[score] for r in data]) for u in [2,3,5,10]},
        'top':top,'bottom':bottom,'blocks':blocks}

def decile_rows(data):
    result={}
    for bl in range(1,9):
        indices=[i for i,r in enumerate(data) if r['block']==bl]
        indices.sort(key=lambda i:(-data[i]['pP'],data[i]['entry_timestamp'],data[i]['symbol'],data[i]['entry_id']))
        for j,i in enumerate(indices):result[data[i]['entry_id']]=min(9,10*j//len(indices))
    return result

def pairs(data,score,target,groups,weights=None):
    y=np.array([r[target] for r in data]);s=np.array([r[score] for r in data])
    w=np.ones(len(data)) if weights is None else np.array(weights,dtype=float)
    total=credit=0.;details=[]
    for g in sorted(set(groups),key=str):
        ix=np.array([i for i,x in enumerate(groups) if x==g])
        p=ix[y[ix]==1];q=ix[y[ix]==0]
        count=float(w[p].sum()*w[q].sum())
        if count:
            diff=s[p,None]-s[q][None,:]
            win=float(np.sum(((diff>0)+.5*(diff==0))*w[p,None]*w[q][None,:]))
            credit+=win;total+=count
            details.append({'group':str(g),'positive_N':len(p),'negative_N':len(q),'valid_pairs':int(count),'credit':win,'discrimination':win/count})
    return {'discrimination':credit/total if total else None,'valid_pairs':int(total),'credit':credit,'groups':details}

def concordance_matrix(data,score,target,groups,sessions):
    """Session-pair concordance permits paired cluster resampling without treating pairs as samples."""
    ds={d:i for i,d in enumerate(sessions)};size=len(sessions)
    numerator=np.zeros((size,size));denominator=np.zeros((size,size))
    for g in set(groups):
        p=[r for r,x in zip(data,groups) if x==g and r[target]==1]
        q=[r for r,x in zip(data,groups) if x==g and r[target]==0]
        for a in p:
            for b in q:
                i,j=ds[a['session']],ds[b['session']]
                denominator[i,j]+=1
                numerator[i,j]+=(a[score]>b[score])+.5*(a[score]==b[score])
    return numerator,denominator

def interval(values):
    values=np.array(values,dtype=float)
    return {'lower':float(np.quantile(values,.025,method='linear')),'upper':float(np.quantile(values,.975,method='linear')),
        'valid_resamples':len(values),'discarded_single_class_resamples':1999-len(values)}

def bootstrap(data,score,control,target,deciles):
    sessions=sorted({r['session'] for r in data});sid={d:i for i,d in enumerate(sessions)}
    row_sid=np.array([sid[r['session']] for r in data]);y=np.array([r[target] for r in data])
    ss=np.array([r[score] for r in data]);cs=np.array([r[control] for r in data])
    groupdefs={
        'pP_conditional':[(r['block'],deciles[r['entry_id']]) for r in data],
        'same_session':[r['session'] for r in data],
        'same_session_pP_conditional':[(r['session'],r['block'],deciles[r['entry_id']]) for r in data]}
    matrices={name:(concordance_matrix(data,score,target,g,sessions),concordance_matrix(data,control,target,g,sessions)) for name,g in groupdefs.items()}
    rng=np.random.default_rng(5701005);values={k:[] for k in ['AUC_delta','PR_AUC_delta',*groupdefs]}
    for _ in range(1999):
        multiplicity=np.bincount(rng.integers(0,len(sessions),len(sessions)),minlength=len(sessions)).astype(float)
        weight=multiplicity[row_sid]
        a=auc_pr(y,ss,weight);b=auc_pr(y,cs,weight)
        if a['AUC'] is not None:
            values['AUC_delta'].append(a['AUC']-b['AUC']);values['PR_AUC_delta'].append(a['PR_AUC']-b['PR_AUC'])
        for name,((num,den),(cn,cd)) in matrices.items():
            d=float(multiplicity@den@multiplicity);dc=float(multiplicity@cd@multiplicity)
            if d and dc:values[name].append(float(multiplicity@num@multiplicity)/d-float(multiplicity@cn@multiplicity)/dc)
    return {'unit':'paired session cluster','sessions':len(sessions),'resamples':1999,'seed':5701005,
        'fixed_outcome_free_deciles':True,'pairs_are_not_independent_samples':True,
        **{name:interval(v) for name,v in values.items()}}

def conditional(data,score,target,deciles):
    return {'score':score,'target':target,
        'pP_conditional':pairs(data,score,target,[(r['block'],deciles[r['entry_id']]) for r in data]),
        'same_session':pairs(data,score,target,[r['session'] for r in data]),
        'same_session_pP_conditional':pairs(data,score,target,[(r['session'],r['block'],deciles[r['entry_id']]) for r in data])}

def ordinal(data,score):
    s=np.array([r[score] for r in data]);percentile=(rankdata(s,method='average')-1)/(len(s)-1)
    ordered=order(data,score);gains=np.array([dict(zip(BUCKETS,[0,1,3,7,15]))[r['bucket']] for r in data])
    bucket=[]
    for b in BUCKETS:
        ix=np.array([i for i,r in enumerate(data) if r['bucket']==b]);top=[]
        for f in [.20,.30]:
            k=math.ceil(f*len(data));v=sum(data[i]['bucket']==b for i in ordered[:k]);top.append({'fraction':f,'N':v,'density':v/k})
        bucket.append({'bucket':b,'N':len(ix),'mean_percentile':float(np.mean(percentile[ix])),'median_percentile':float(np.median(percentile[ix])),'top':top})
    ndcg=[]
    for f in FRACTIONS:
        k=math.ceil(f*len(data));discount=np.log2(np.arange(k)+2)
        ndcg.append({'fraction':f,'K':k,'NDCG':float(np.sum(gains[ordered[:k]]/discount)/np.sum(np.sort(gains)[::-1][:k]/discount))})
    return {'score':score,'buckets':bucket,'ideal_mean_order':all(a['mean_percentile']<b['mean_percentile'] for a,b in zip(bucket,bucket[1:])),
        'ideal_median_order':all(a['median_percentile']<b['median_percentile'] for a,b in zip(bucket,bucket[1:])),'NDCG':ndcg,'gain':[0,1,3,7,15]}

def primary_gates(metrics,cond,boot,head,control,target,prefix):
    a=metrics[head];b=metrics[control];delta=a[target]['AUC']-b[target]['AUC']
    improved=[];catastrophic=[];undefined=[]
    for bl in range(1,9):
        ca=a['blocks'][str(bl)][target]['AUC'];co=b['blocks'][str(bl)][target]['AUC']
        if ca is None or co is None:undefined.append(bl);continue
        if ca>co:improved.append(bl)
        if co>=.5 and ca<.5 and ca-co<=-.10:catastrophic.append(bl)
    if target=='U2':
        third=a['top'][1]['below2_rate']<b['top'][1]['below2_rate']
        fourth=a['top'][2]['below2_rate']<b['top'][2]['below2_rate']
    else:
        third=a['top'][1]['U3_density']>b['top'][1]['U3_density']
        fourth=a['top'][2]['U3_capture']>b['top'][2]['U3_capture']
    gates={prefix+'1':a[target]['AUC']>b[target]['AUC'],prefix+'2':a[target]['PR_AUC']>b[target]['PR_AUC'],
        prefix+'3':third,prefix+'4':fourth,prefix+'5':len(improved)>=5,prefix+'6':not catastrophic and not undefined,
        prefix+'7':cond[head]['pP_conditional']['discrimination']>cond[control]['pP_conditional']['discrimination'],
        prefix+'8':True}
    passed=all(gates.values());ci=boot['AUC_delta']
    status='STRONG' if passed and ci['lower']>0 else 'PROMISING' if passed else 'NO_GO'
    return {'head':head,'control':control,'target':target,'AUC_delta':delta,
        'PR_AUC_delta':a[target]['PR_AUC']-b[target]['PR_AUC'],'AUC_delta_CI':ci,
        'conditional_delta':cond[head]['pP_conditional']['discrimination']-cond[control]['pP_conditional']['discrimination'],
        'gates':gates,'block_improved':improved,'catastrophic_blocks':catastrophic,'undefined_blocks':undefined,
        'point_gate_PASS':passed,'status_pending_integrity_audit':status}

def decision(u2,u3,integrity=True):
    ok2=u2['point_gate_PASS'];ok3=u3['point_gate_PASS']
    if not integrity:return {'qualityStatus':'QUALITY_CONTRACT_FAIL','selectedAuxiliaryHeads':[]}
    if ok2 and ok3:status='ANTI_WEAK_MEDIUM_STRONG' if u2['status_pending_integrity_audit']==u3['status_pending_integrity_audit']=='STRONG' else 'ANTI_WEAK_MEDIUM_PROMISING'
    elif ok2:status='ANTI_WEAK_ONLY'
    elif ok3:status='MEDIUM_PLUS_ONLY'
    else:status='QUALITY_NO_GO'
    return {'qualityStatus':status,'selectedAuxiliaryHeads':(['MOVE_U2'] if ok2 else [])+(['MOVE_U3'] if ok3 else [])}
