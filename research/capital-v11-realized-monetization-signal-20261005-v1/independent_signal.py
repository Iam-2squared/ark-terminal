"""Raw-only scalar model and independent rank/statistical audit. No trainer/evaluator import."""
from control import *
import math, statistics, bisect, numpy as np
CHECKS=0;MAX_DELTA=0.;FAILURES=[]
def check(name,ok):
    global CHECKS
    CHECKS+=1
    if not ok:FAILURES.append(name)
def equal(name,a,b):
    global MAX_DELTA
    if isinstance(a,dict) and isinstance(b,dict):
        check(name+'.keys',set(a)==set(b))
        for k in set(a)&set(b):equal(name+'.'+str(k),a[k],b[k])
    elif isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)):
        check(name+'.length',len(a)==len(b))
        for i,(x,y) in enumerate(zip(a,b)):equal(name+'.'+str(i),x,y)
    elif isinstance(a,(float,np.floating)) or isinstance(b,(float,np.floating)):
        if a is None or b is None:check(name,a is None and b is None);return
        d=abs(float(a)-float(b));MAX_DELTA=max(MAX_DELTA,d);check(name,d<=1e-12)
    else:check(name,a==b)
def feature_vector(r,p):
    n=[0. if r['numeric'][k] is None else float(r['numeric'][k]) for k in p['numeric_fields']]
    n += [float(r['numeric'][k] is None) for k in p['numeric_fields']]
    a=[(v-m)/s for v,m,s in zip(n,p['numeric_mean'],p['numeric_scale'])]
    for k in p['categorical_fields']:
        voc=p['categorical_train_vocab'][k];v=r['categorical'][k]
        if v not in voc:v='__UNKNOWN__'
        a.extend(float(v==c) for c in voc)
    return a
def infer(r,m):
    x=feature_vector(r,m['preprocessing']);z=math.fsum([m['intercept']]+[a*b for a,b in zip(x,m['coef'])])
    return 1/(1+math.exp(-z)) if z>=0 else math.exp(z)/(1+math.exp(z))
def weighted_metrics(y,s,w=None):
    y=np.asarray(y,dtype=float);s=np.asarray(s);w=np.ones(len(y)) if w is None else np.asarray(w)
    order=np.argsort(s,kind='stable');ss=s[order];yy=y[order];ww=w[order]
    starts=np.r_[0,np.where(ss[1:]!=ss[:-1])[0]+1];wp=np.add.reduceat(ww*yy,starts);wn=np.add.reduceat(ww*(1-yy),starts)
    pp=wp.sum();nn=wn.sum()
    if pp==0 or nn==0:return {'AUC':None,'PR_AUC':None}
    before=np.r_[0,np.cumsum(wn)[:-1]];auc=float(np.sum(wp*(before+.5*wn))/(pp*nn))
    p=wp[::-1];n=wn[::-1];tp=np.cumsum(p);alln=np.cumsum(p+n);precision=np.divide(tp,alln,out=np.zeros(len(p)),where=alln>0)
    ap=float(np.sum(p*precision)/pp)
    return {'AUC':auc,'PR_AUC':ap}
def rank_weighted(v,w):
    v=np.asarray(v);order=np.argsort(v,kind='stable');s=v[order];ww=w[order]
    starts=np.r_[0,np.where(s[1:]!=s[:-1])[0]+1];mass=np.add.reduceat(ww,starts);cum=np.cumsum(mass)
    values=cum-mass/2+.5;out=np.empty(len(v));out[order]=np.repeat(values,np.diff(np.r_[starts,len(v)]));return out
def correlation(s,y,w=None):
    w=np.ones(len(s)) if w is None else np.asarray(w)
    x=rank_weighted(s,w);z=rank_weighted(y,w);n=w.sum()
    xx=x-np.dot(w,x)/n;zz=z-np.dot(w,z)/n
    denom=math.sqrt(float(np.dot(w,xx*xx)*np.dot(w,zz*zz)))
    return float(np.dot(w,xx*zz)/denom) if denom else None
def conditional(rr,score,session=False):
    groups={}
    for r in rr:groups.setdefault((r['session'] if session else r['block'],r['bucket']),[]).append(r)
    details=[];total=0;points=0.
    for key,group in sorted(groups.items()):
        n=0;c=0.
        for i,a in enumerate(group):
            for b in group[i+1:]:
                if a['realized']==b['realized']:continue
                hi,lo=(a,b) if a['realized']>b['realized'] else (b,a)
                n+=1;c+=1. if hi[score]>lo[score] else (.5 if hi[score]==lo[score] else 0.)
        total+=n;points+=c;details.append({'group':list(key),'valid_pairs':n,'credit':c,'concordance':c/n if n else None})
    return {'concordance':points/total if total else None,'valid_pairs':total,'credit':points,'groups':details,'pairs_independent_samples':False}
def summarize(rr,score):
    y=[r['label'] for r in rr];s=[r[score] for r in rr];z=weighted_metrics(y,s);order=sorted(rr,key=lambda r:(-r[score],r['entry_id']));base=sum(y)/len(y);top={}
    for pct in (.2,.3):
        n=math.ceil(len(rr)*pct);rate=sum(r['label'] for r in order[:n])/n;top[str(int(pct*100))]={'N':n,'observed_rate':rate,'enrichment':rate/base if base else None}
    dec=[];sizes=[len(rr)//10+int(d<len(rr)%10) for d in range(10)];at=0
    for d,n in enumerate(sizes,1):
        q=order[at:at+n];at+=n;dec.append({'decile':d,'N':n,'score_mean':math.fsum(r[score] for r in q)/n,'MRET_observed_rate':sum(r['label'] for r in q)/n})
    out={'N':len(rr),'positive_N':sum(y),'MRET':z|{'Brier':math.fsum((a-b)**2 for a,b in zip(s,y))/len(rr)},'blocks':{str(b):weighted_metrics([r['label'] for r in rr if r['block']==b],[r[score] for r in rr if r['block']==b]) for b in range(1,9)},'Top':top,'deciles':dec,'conditional':conditional(rr,score),'same_session_conditional':conditional(rr,score,True)}
    out['realized']={k:weighted_metrics([int(fn(r['realized'])) for r in rr],s)['AUC'] for k,fn in [('positive_AUC',lambda x:x>0),('ge1_AUC',lambda x:x>=.01),('loser_AUC',lambda x:x<=0)]}
    out['realized']['Spearman']=correlation(s,[r['realized'] for r in rr]);return out
def pair_cluster_table(rr,score,sessions):
    pos={s:i for i,s in enumerate(sessions)};num=np.zeros((38,38));den=np.zeros((38,38));gg={}
    for r in rr:gg.setdefault((r['block'],r['bucket']),[]).append(r)
    for group in gg.values():
        for i,a in enumerate(group):
            for b in group[i+1:]:
                if a['realized']==b['realized']:continue
                hi,lo=(a,b) if a['realized']>b['realized'] else (b,a);c=1. if hi[score]>lo[score] else (.5 if hi[score]==lo[score] else 0.)
                x,y=pos[hi['session']],pos[lo['session']];num[x,y]+=c;den[x,y]+=1
    return num,den
def independent_bootstrap(rr,best,sessions):
    rng=np.random.default_rng(5701105);draw=rng.integers(0,38,size=(1999,38));counts=np.zeros((1999,38),dtype=int)
    for i,d in enumerate(draw):
        for v in d:counts[i,int(v)]+=1
    savedcounts=rows(PRIVATE/'SESSION_BOOTSTRAP_COUNTS.jsonl.gz')
    equal('bootstrap_counts',counts.tolist(),[r['counts'] for r in savedcounts])
    pos={s:i for i,s in enumerate(sessions)};idx=np.array([pos[r['session']] for r in rr]);labels=np.array([r['label'] for r in rr]);real=np.array([r['realized'] for r in rr]);positive=(real>0).astype(int)
    scores={s:np.array([r[s] for r in rr]) for s in ['mP',best]};tables={s:pair_cluster_table(rr,s,sessions) for s in scores}
    output=[]
    for i,c in enumerate(counts):
        w=c[idx];metrics={s:weighted_metrics(labels,x,w) for s,x in scores.items()};realauc={s:weighted_metrics(positive,x,w)['AUC'] for s,x in scores.items()};sp={s:correlation(x,real,w) for s,x in scores.items()};cond={}
        for s,(n,d) in tables.items():
            denominator=float(c@d@c);cond[s]=float(c@n@c)/denominator if denominator else None
        diff=lambda x:None if x['mP'] is None or x[best] is None else x['mP']-x[best]
        output.append({'resample':i+1,'MRET_AUC_delta':diff({s:v['AUC'] for s,v in metrics.items()}),'MRET_PR_delta':diff({s:v['PR_AUC'] for s,v in metrics.items()}),'conditional_delta':diff(cond),'realized_positive_AUC_delta':diff(realauc),'Spearman_delta':diff(sp)})
        if (i+1)%500==0:print(json.dumps({'independent_bootstrap_complete':i+1}),flush=True)
    equal('bootstrap_resamples',output,rows(PRIVATE/'SESSION_BOOTSTRAP_DELTAS.jsonl.gz'))
    result={}
    for k in output[0]:
        if k=='resample':continue
        a=sorted(r[k] for r in output if r[k] is not None)
        def quantile(q):
            x=(len(a)-1)*q;i=int(x);j=min(i+1,len(a)-1);return a[i]+(a[j]-a[i])*(x-i)
        result[k]={'valid_N':len(a),'mean':math.fsum(a)/len(a),'CI95':[quantile(.025),quantile(.975)]}
    boot={'seed':5701105,'resamples':1999,'unit':'OOF38_SESSION_CLUSTER','independent_session_N':38,'best_control':best,'deltas':result}
    equal('bootstrap_result',boot,read(OUT/'SESSION_BOOTSTRAP_RESULT.json'));return boot
def main():
    assert (PRIVATE/'claims/R7_EVALUATION_COMPLETE.json').exists()
    save(PRIVATE/'claims/R8_INDEPENDENT_SIGNAL_STARTED.json',{'exact_jst':now(),'basis':read(WORK/'latest_basis.json'),'optimizer_refits':0,'trainer_evaluator_imports':0,'reexecution_allowed':False})
    raw=rows(MAIN/'inputs/movement/RUNTIME_CAUSAL.jsonl.gz');byid={r['entry_id']:r for r in raw};teachers={r['entry_id']:r for r in rows(MAIN/'inputs/evaluation/TEACHERS_EVALUATION.jsonl.gz')};split=read(SPLIT)
    mask={r['entry_id'] for r in rows(MAIN/'private/COMMON_EVAL_MASK.jsonl.gz') if r['included']};funded={r['entry_id'] for r in rows(V9/'private'/f'{I2}_TRADES.jsonl.gz')};native={r['entry_id']:r for r in rows(MAIN/'private/RANK_NATIVE_RUNTIME.jsonl.gz')}
    savedOOF={r['entry_id']:r for r in rows(PRIVATE/'MRET_OOF_SCORES.jsonl.gz')};savedtrain={(r['block'],r['entry_id']):r for r in rows(PRIVATE/'MRET_TRAIN_RESUBSTITUTION_SCORES.jsonl.gz')};parentcurrent={r['entry_id']:r for r in rows(V10/'private/CURRENT_SIZING_RUNTIME.jsonl.gz')};parenttrain={(r['block'],r['entry_id']):r for r in rows(V10/'private/SIZING_TRAIN_SCORE_TABLE.jsonl.gz')};table=read(OUT/'MRET_TEACHER_RESULT.json')['blocks'];spec=read(OUT/'MRET_TEACHER_FEATURE_MODEL_PRECOMMIT.json')
    valid=lambda t:t.get('capture_complete') is True and t.get('strictly_after_entry_before_1520') is True and all(t.get(k) is not None and math.isfinite(t[k]) for k in ['potential_return','realized_net_return'])
    bucket=lambda p:sum(p>=x for x in [.01,.02,.03,.04,.05,.10]);rr=[];current_rescore=[];train_rescore=[]
    for block in split['blocks']:
        b=block['block'];train=[r for r in raw if r['session'] in block['train'] and r['entry_minute']<920 and valid(teachers[r['entry_id']])];test=[r for r in raw if r['session'] in block['test']]
        distributions={k:[] for k in range(7)}
        for r in train:distributions[bucket(teachers[r['entry_id']]['potential_return'])].append(teachers[r['entry_id']]['realized_net_return'])
        medians={k:statistics.median(v) for k,v in distributions.items()};labels={r['entry_id']:int(teachers[r['entry_id']]['realized_net_return']>medians[bucket(teachers[r['entry_id']]['potential_return'])]) for r in train}
        equal('train_projection_'+str(b),labels,{r['entry_id']:r['label'] for r in rows(PRIVATE/f'train_labels/MRET_BLOCK_{b:02d}_PAST_ONLY.jsonl.gz')})
        for k,v in distributions.items():
            check('support',len(v)>=10);equal('teacher_bucket',{'support':len(v),'median_realized':medians[k],'exact_tie_N':sum(x==medians[k] for x in v),'positive_N':sum(x>medians[k] for x in v)},table[b-1]['buckets'][str(k)])
        m=read(PRIVATE/f'models/MRET_BLOCK_{b:02d}.json');prep=m['preprocessing'];equal('model_config',m['parameters'],spec['model']);equal('train_ids',m['train_entry_ids'],[r['entry_id'] for r in train]);check('temporal',max(r['session'] for r in train)<min(block['test']))
        equal('feature_names',prep['numeric_fields'],spec['features']['numeric_fields']);equal('categorical_names',prep['categorical_fields'],spec['features']['categorical_fields'])
        unscaled=[]
        for r in train:
            a=[0. if r['numeric'][k] is None else float(r['numeric'][k]) for k in prep['numeric_fields']]+[float(r['numeric'][k] is None) for k in prep['numeric_fields']];unscaled.append(a)
        mean=[math.fsum(col)/len(train) for col in zip(*unscaled)];scales=[math.sqrt(math.fsum((v-mu)**2 for v in col)/len(train)) or 1. for col,mu in zip(zip(*unscaled),mean)]
        equal('train_mean',mean,prep['numeric_mean']);equal('train_scale',scales,prep['numeric_scale'])
        for k in prep['categorical_fields']:equal('train_vocab',sorted({r['categorical'][k] or '__UNKNOWN__' for r in train}|{'__UNKNOWN__'}),prep['categorical_train_vocab'][k])
        with np.load(PRIVATE/f'fitted_state/MRET_BLOCK_{b:02d}.npz') as snap:
            equal('coef_snapshot',snap['coef'][0].tolist(),m['coef']);equal('intercept_snapshot',float(snap['intercept'][0]),m['intercept']);equal('classes_snapshot',snap['classes'].tolist(),m['classes']);equal('mean_snapshot',snap['numeric_mean'].tolist(),prep['numeric_mean']);equal('scale_snapshot',snap['numeric_scale'].tolist(),prep['numeric_scale'])
        done=read(PRIVATE/f'claims/MRET_BLOCK_{b:02d}_COMPLETE.json');check('one_optimizer_call',done['optimizer_calls']==1);check('no_convergence',done['ConvergenceWarning_N']==0);check('no_heldout_teacher',done['heldout_teacher_payload_reads']==0)
        for r in train:
            v=infer(r,m);equal('train_inference',v,savedtrain[b,r['entry_id']]['mP']);train_rescore.append({'entry_id':r['entry_id'],'session':r['session'],'block':b,'mP':v})
        parentmodels={'pP':read(MAIN/f'inputs/movement/models/MOVE_P_BLOCK_{b:02d}.json'),'q2':read(QUALITY/f'private/models/MOVE_U2_BLOCK_{b:02d}.json'),'q3':read(QUALITY/f'private/models/MOVE_U3_BLOCK_{b:02d}.json')}
        original_train=[r for r in raw if (b,r['entry_id']) in parenttrain];sorted_scores={s:[] for s in parentmodels}
        for r in original_train:
            for s,pm in parentmodels.items():
                v=infer(r,pm);equal('control_train_score',v,parenttrain[b,r['entry_id']][s]);sorted_scores[s].append(v)
        for v in sorted_scores.values():v.sort()
        for r in test:
            v=infer(r,m);equal('OOF_inference',v,savedOOF[r['entry_id']]['mP']);current_rescore.append({'entry_id':r['entry_id'],'session':r['session'],'block':b,'mP':v})
            frozen={s:infer(r,pm) for s,pm in parentmodels.items()}
            for s,z in frozen.items():equal('control_current_inference',z,parentcurrent[r['entry_id']][s])
            consensus=min((1+bisect.bisect_left(sorted_scores[s],frozen[s]))/(len(sorted_scores[s])+1) for s in sorted_scores);equal('consensus_percentile',consensus,parentcurrent[r['entry_id']]['consensus_weight'])
            t=teachers[r['entry_id']]
            if r['entry_id'] not in mask or not valid(t):continue
            k=bucket(t['potential_return']);rr.append({'entry_id':r['entry_id'],'session':r['session'],'block':b,'bucket':k,'potential':t['potential_return'],'realized':t['realized_net_return'],'median':medians[k],'label':int(t['realized_net_return']>medians[k]),'exact_tie':t['realized_net_return']==medians[k],'mP':v,**frozen,'consensus':consensus,'admitted':native[r['entry_id']]['band'] in ('P_HIGH','P_MID','P_BASE'),'I2_funded':r['entry_id'] in funded})
        print(json.dumps({'independent_raw_block':b,'OOF_scored':len(test)}),flush=True)
    equal('evaluation_join',rr,rows(PRIVATE/'MRET_POST_FIT_EVALUATION_ROWS.jsonl.gz'));check('OOF_unique',len(current_rescore)==1039 and len({r['entry_id'] for r in current_rescore})==1039)
    scores=['pP','q2','q3','consensus','mP'];results={s:summarize(rr,s) for s in scores};primary=read(OUT/'MRET_PRIMARY_RESULT.json');equal('all_primary_metrics',results,primary['scores'])
    best=max(scores[:4],key=lambda s:results[s]['MRET']['AUC']);equal('best_control',best,primary['best_existing_control'])
    subset={}
    for name,q in [('whole_common',rr),('I2_admission',[r for r in rr if r['admitted']]),('I2_funded',[r for r in rr if r['I2_funded']])]:
        subset[name]={'N':len(q),'scores':{s:{'positive_AUC':weighted_metrics([int(r['realized']>0) for r in q],[r[s] for r in q])['AUC'],'ge1_AUC':weighted_metrics([int(r['realized']>=.01) for r in q],[r[s] for r in q])['AUC'],'loser_AUC':weighted_metrics([int(r['realized']<=0) for r in q],[r[s] for r in q])['AUC'],'Spearman':correlation([r[s] for r in q],[r['realized'] for r in q])} for s in scores}}
    equal('realized_subsets',subset,read(OUT/'FROZEN_EXIT_REALIZED_DIAGNOSTICS.json'))
    boot=independent_bootstrap(rr,best,split['OOF38']);a=results['mP'];c=results[best]
    improved=sum(a['blocks'][str(b)]['AUC']>c['blocks'][str(b)]['AUC'] for b in range(1,9));bad=[b for b in range(1,9) if c['blocks'][str(b)]['AUC']>=.5 and a['blocks'][str(b)]['AUC']<.5 and a['blocks'][str(b)]['AUC']-c['blocks'][str(b)]['AUC']<=-.10]
    gate={'S1':a['MRET']['AUC']>c['MRET']['AUC'],'S2':a['MRET']['PR_AUC']>c['MRET']['PR_AUC'],'S3':a['conditional']['concordance']>c['conditional']['concordance'],'S4':a['conditional']['concordance']>.5,'S5':a['realized']['positive_AUC']>c['realized']['positive_AUC'],'S6':improved>=5,'S7':not bad,'S8':boot['deltas']['MRET_AUC_delta']['CI95'][0]>0}
    pending=read(OUT/'MRET_POINT_GATE_PENDING_INDEPENDENT_AUDIT.json');equal('point_gate',gate,pending['conditions_before_independent_audit']);equal('improved_blocks',improved,pending['block_improved_N']);equal('catastrophic_blocks',bad,pending['catastrophic_blocks'])
    gzsave(PRIVATE/'INDEPENDENT_MRET_OOF_SCORES.jsonl.gz',current_rescore);gzsave(PRIVATE/'INDEPENDENT_MRET_TRAIN_SCORES.jsonl.gz',train_rescore)
    audit={'status':'PASS' if not FAILURES else 'FAIL','checks':CHECKS,'mismatch_N':len(FAILURES),'failures':FAILURES[:100],'float_max_abs_difference':MAX_DELTA,'float_tolerance':1e-12,'trainer_evaluator_imports':0,'optimizer_refits':0,'raw_control_inference':True,'raw_teacher_feature_preprocessing_reconstruction':True,'bootstrap_seed_resamples_independently_reproduced':True,'fitted_state_snapshot_exact':True,'point_conditions':gate,'best_existing_control':best,'Safety':SAFETY}
    save(OUT/'INDEPENDENT_SIGNAL_AUDIT.json',audit);save(PRIVATE/'claims/R8_INDEPENDENT_SIGNAL_COMPLETE.json',{'exact_jst':now(),'audit_sha256':sha(OUT/'INDEPENDENT_SIGNAL_AUDIT.json'),'mismatch_N':len(FAILURES),'optimizer_refits':0})
    checkpoint('R8_MRET_INDEPENDENT_SIGNAL_AUDIT',audit,'R9 signal gate; STRONG alone permits Capital')
    print(json.dumps(audit));assert not FAILURES,'V11_CONTRACT_FAIL_INDEPENDENT_SIGNAL'
if __name__=='__main__':main()
