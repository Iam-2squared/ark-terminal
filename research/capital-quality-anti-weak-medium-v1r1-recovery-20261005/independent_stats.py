"""Independent rank/tie/threshold/pairwise implementation. No primary imports."""
from collections import defaultdict
import hashlib
import json
import math
import numpy as np

FRACTIONS=[.1,.2,.3,.4]
BUCKETS=['Q0_WEAK','Q1_LOW','Q2_MEDIUM','Q3_BIG','Q4_MEGA']

def ordered(data,score):
    def tie(r):return (r['entry_timestamp'],r['symbol'],r['entry_id'])
    if score=='legacy_ML':return sorted(range(len(data)),key=lambda i:(-data[i][score],-data[i]['legacy_m5'],-data[i]['legacy_m3'],-data[i]['legacy_m2'],*tie(data[i])))
    return sorted(range(len(data)),key=lambda i:(-data[i][score],*tie(data[i])))

def auc_ap(y,s,weight=None):
    # Ascending weighted rank sum, averaging ties; AP at distinct-score thresholds.
    y=np.asarray(y,dtype=int);s=np.asarray(s,dtype=float)
    w=np.ones(len(y)) if weight is None else np.asarray(weight,dtype=float)
    active=w>0;y=y[active];s=s[active];w=w[active]
    p=float(w[y==1].sum());n=float(w[y==0].sum())
    if not p or not n:return {'AUC':None,'PR_AUC':None}
    ix=np.argsort(s,kind='stable');ss=s[ix];yy=y[ix];ww=w[ix]
    starts=np.r_[0,np.flatnonzero(ss[1:]!=ss[:-1])+1]
    pos=np.add.reduceat(ww*yy,starts);neg=np.add.reduceat(ww*(1-yy),starts)
    before=np.cumsum(neg)-neg
    auc=float(np.sum(pos*(before+.5*neg))/(p*n))
    pp=pos[::-1];tt=(pos+neg)[::-1];precision=np.cumsum(pp)/np.cumsum(tt)
    ap=float(np.sum(pp*precision)/p)
    return {'AUC':auc,'PR_AUC':ap}

def quality(data,score):
    ix=ordered(data,score);N=len(data);tot={u:sum(r[f'U{u}'] for r in data) for u in [2,3,5,10]}
    result={'score':score,'N':N}
    for u in [2,3,5,10]:result[f'U{u}']=auc_ap([r[f'U{u}'] for r in data],[r[score] for r in data])
    result['top']=[];result['bottom']=[];result['blocks']={}
    for f in FRACTIONS:
        k=int(math.ceil(f*N));selected=[data[i] for i in ix[:k]]
        counts={u:sum(r[f'U{u}'] for r in selected) for u in tot}
        diag={'le0':0,'le_minus1':0,'le_minus3':0,'ge_plus1':0}
        for r in selected:
            v=r['realized_net_return_diagnostic_only']
            if v is not None:
                diag['le0']+=int(v<=0);diag['le_minus1']+=int(v<=-.01)
                diag['le_minus3']+=int(v<=-.03);diag['ge_plus1']+=int(v>=.01)
        item={'fraction':f,'selected_N':k,'below2_N':k-counts[2],'below2_rate':(k-counts[2])/k,
            'below3_N':k-counts[3],'below3_rate':(k-counts[3])/k,'Medium_N':counts[3]-counts[5],'realized_PnL_diagnostic':diag}
        for u,c in counts.items():item.update({f'U{u}_N':c,f'U{u}_density':c/k,f'U{u}_capture':c/tot[u]})
        result['top'].append(item)
        if f<=.3:
            weak=sum(data[i]['WEAK2'] for i in ix[-k:])
            result['bottom'].append({'fraction':f,'selected_N':k,'Weak_N':weak,'Weak_density':weak/k,'Weak_capture':weak/(N-tot[2])})
    for b in range(1,9):
        rr=[r for r in data if r['block']==b]
        result['blocks'][str(b)]={'N':len(rr),**{f'U{u}':auc_ap([r[f'U{u}'] for r in rr],[r[score] for r in rr]) for u in [2,3]}}
    return result

def deciles(data):
    out={}
    for b in range(1,9):
        rr=sorted((r for r in data if r['block']==b),key=lambda r:(-r['pP'],r['entry_timestamp'],r['symbol'],r['entry_id']))
        for j,r in enumerate(rr):out[r['entry_id']]=min(9,(10*j)//len(rr))
    return out

def grouping(data,dec):
    return {'pP_conditional':[(r['block'],dec[r['entry_id']]) for r in data],
        'same_session':[r['session'] for r in data],
        'same_session_pP_conditional':[(r['session'],r['block'],dec[r['entry_id']]) for r in data]}

def pairwise(data,score,target,groups):
    by=defaultdict(list)
    for i,g in enumerate(groups):by[g].append(i)
    total=0;credit=0.;details=[]
    for g in sorted(by,key=str):
        pos=[data[i] for i in by[g] if data[i][target]==1];neg=[data[i] for i in by[g] if data[i][target]==0]
        count=len(pos)*len(neg)
        if not count:continue
        win=sum(float(a[score]>b[score])+.5*float(a[score]==b[score]) for a in pos for b in neg)
        total+=count;credit+=win
        details.append({'group':str(g),'positive_N':len(pos),'negative_N':len(neg),'valid_pairs':count,'credit':win,'discrimination':win/count})
    return {'discrimination':credit/total if total else None,'valid_pairs':total,'credit':credit,'groups':details}

def conditional(data,score,target,dec):
    return {'score':score,'target':target,**{name:pairwise(data,score,target,g) for name,g in grouping(data,dec).items()}}

def matrices(data,score,target,groups,sessions):
    size=len(sessions);ids={s:i for i,s in enumerate(sessions)}
    n=np.zeros((size,size));d=np.zeros_like(n);by=defaultdict(list)
    for i,g in enumerate(groups):by[g].append(i)
    for ix in by.values():
        a=np.array([i for i in ix if data[i][target]],dtype=int)
        b=np.array([i for i in ix if not data[i][target]],dtype=int)
        if not len(a) or not len(b):continue
        sca=np.array([data[i][score] for i in a]);scb=np.array([data[i][score] for i in b])
        si=np.repeat([ids[data[i]['session']] for i in a],len(b));sj=np.tile([ids[data[i]['session']] for i in b],len(a))
        wins=((sca[:,None]>scb)+.5*(sca[:,None]==scb)).ravel()
        np.add.at(n,(si,sj),wins);np.add.at(d,(si,sj),1.)
    return n,d

def draw_hash(draws):
    body=b''.join((json.dumps(x.tolist(),separators=(',',':'))+'\n').encode() for x in draws)
    return hashlib.sha256(body).hexdigest()

def bootstrap(data,head,control,target,dec):
    sessions=sorted({r['session'] for r in data});S=len(sessions);lookup={s:i for i,s in enumerate(sessions)}
    row_ids=np.array([lookup[r['session']] for r in data]);groups=grouping(data,dec)
    mat={name:(matrices(data,head,target,g,sessions),matrices(data,control,target,g,sessions)) for name,g in groups.items()}
    ys=[r[target] for r in data];ss=[r[head] for r in data];cs=[r[control] for r in data]
    samples={k:[] for k in ['AUC_delta','PR_AUC_delta',*groups]}
    rng=np.random.default_rng(5701005);draws=[]
    for b in range(1999):
        draw=rng.integers(0,S,S);draws.append(draw)
        mult=np.zeros(S)
        for v in draw:mult[v]+=1
        w=mult[row_ids];a=auc_ap(ys,ss,w);c=auc_ap(ys,cs,w)
        if a['AUC'] is not None:
            samples['AUC_delta'].append(a['AUC']-c['AUC']);samples['PR_AUC_delta'].append(a['PR_AUC']-c['PR_AUC'])
        for name,((an,ad),(cn,cd)) in mat.items():
            da=float(np.sum(ad*mult[:,None]*mult[None,:]));dc=float(np.sum(cd*mult[:,None]*mult[None,:]))
            if da and dc:samples[name].append(float(np.sum(an*mult[:,None]*mult[None,:]))/da-float(np.sum(cn*mult[:,None]*mult[None,:]))/dc)
    out={'unit':'paired session cluster','sessions':S,'resamples':1999,'seed':5701005,
        'fixed_outcome_free_deciles':True,'pairs_are_not_independent_samples':True}
    for k,v in samples.items():
        out[k]={'lower':float(np.quantile(v,.025,method='linear')),'upper':float(np.quantile(v,.975,method='linear')),
            'valid_resamples':len(v),'discarded_single_class_resamples':1999-len(v)}
    return out,draw_hash(draws),samples

def ordinal(data,score):
    # Independently average integer ranks within exact-score ties.
    ix=sorted(range(len(data)),key=lambda i:data[i][score]);percentile=np.zeros(len(data));start=0
    while start<len(ix):
        end=start+1
        while end<len(ix) and data[ix[end]][score]==data[ix[start]][score]:end+=1
        percentile[ix[start:end]]=((start+1+end)/2-1)/(len(data)-1);start=end
    rank=ordered(data,score);bucket=[]
    for b in BUCKETS:
        vv=np.array([percentile[i] for i,r in enumerate(data) if r['bucket']==b]);top=[]
        for f in [.2,.3]:
            k=math.ceil(len(data)*f);n=sum(data[i]['bucket']==b for i in rank[:k]);top.append({'fraction':f,'N':n,'density':n/k})
        bucket.append({'bucket':b,'N':len(vv),'mean_percentile':float(vv.mean()),'median_percentile':float(np.median(vv)),'top':top})
    gains={b:g for b,g in zip(BUCKETS,[0,1,3,7,15])};allg=[gains[r['bucket']] for r in data];ideal=sorted(allg,reverse=True);ndcg=[]
    for f in FRACTIONS:
        k=math.ceil(f*len(data));dcg=sum(allg[i]/math.log2(j+2) for j,i in enumerate(rank[:k]))
        idcg=sum(g/math.log2(j+2) for j,g in enumerate(ideal[:k]));ndcg.append({'fraction':f,'K':k,'NDCG':dcg/idcg})
    return {'score':score,'buckets':bucket,'ideal_mean_order':all(a['mean_percentile']<b['mean_percentile'] for a,b in zip(bucket,bucket[1:])),
        'ideal_median_order':all(a['median_percentile']<b['median_percentile'] for a,b in zip(bucket,bucket[1:])),
        'NDCG':ndcg,'gain':[0,1,3,7,15]}

def gates(mm,cc,bb,head,control,target,prefix):
    cand,base=mm[head],mm[control];improved=[];bad=[];undefined=[]
    for bl in range(1,9):
        a=cand['blocks'][str(bl)][target]['AUC'];b=base['blocks'][str(bl)][target]['AUC']
        if a is None or b is None:undefined.append(bl);continue
        if a>b:improved.append(bl)
        if b>=.5 and a<.5 and a-b<=-.1:bad.append(bl)
    three=cand['top'][1]['below2_rate']<base['top'][1]['below2_rate'] if target=='U2' else cand['top'][1]['U3_density']>base['top'][1]['U3_density']
    four=cand['top'][2]['below2_rate']<base['top'][2]['below2_rate'] if target=='U2' else cand['top'][2]['U3_capture']>base['top'][2]['U3_capture']
    gs={prefix+'1':cand[target]['AUC']>base[target]['AUC'],prefix+'2':cand[target]['PR_AUC']>base[target]['PR_AUC'],
        prefix+'3':three,prefix+'4':four,prefix+'5':len(improved)>=5,prefix+'6':not bad and not undefined,
        prefix+'7':cc[head]['pP_conditional']['discrimination']>cc[control]['pP_conditional']['discrimination'],prefix+'8':True}
    passed=all(gs.values());ci=bb['AUC_delta'];state='NO_GO'
    if passed:state='STRONG' if ci['lower']>0 else 'PROMISING'
    return {'head':head,'control':control,'target':target,'AUC_delta':cand[target]['AUC']-base[target]['AUC'],
        'PR_AUC_delta':cand[target]['PR_AUC']-base[target]['PR_AUC'],'AUC_delta_CI':ci,
        'conditional_delta':cc[head]['pP_conditional']['discrimination']-cc[control]['pP_conditional']['discrimination'],
        'gates':gs,'block_improved':improved,'catastrophic_blocks':bad,'undefined_blocks':undefined,
        'point_gate_PASS':passed,'status_pending_integrity_audit':state}

def decision(a,b):
    heads=[h for h,g in [('MOVE_U2',a),('MOVE_U3',b)] if g['point_gate_PASS']]
    status='QUALITY_NO_GO'
    if len(heads)==2:status='ANTI_WEAK_MEDIUM_STRONG' if a['status_pending_integrity_audit']==b['status_pending_integrity_audit']=='STRONG' else 'ANTI_WEAK_MEDIUM_PROMISING'
    elif heads==['MOVE_U2']:status='ANTI_WEAK_ONLY'
    elif heads==['MOVE_U3']:status='MEDIUM_PLUS_ONLY'
    return {'qualityStatus':status,'selectedAuxiliaryHeads':heads}
