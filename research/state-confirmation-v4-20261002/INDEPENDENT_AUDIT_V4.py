"""Independent prefix, label, model and aggregation audit. No candidate imports.
Normal equations are checked without solving or refitting. Saved bootstrap only.
"""
from pathlib import Path
from collections import Counter,defaultdict
import json,csv,hashlib,math,statistics,importlib.util,sys
import numpy as np
R=Path(__file__).resolve().parent
CHECKS=Counter();ERRORS=[];MISMATCH=0
def check(ok,kind,detail=None):
    global MISMATCH
    CHECKS[kind]+=1
    if not ok:
        MISMATCH+=1
        if len(ERRORS)<200:ERRORS.append({'kind':kind,'detail':str(detail)})
def near(a,b):
    if a is None or b is None:return a is None and b is None
    return math.isclose(float(a),float(b),abs_tol=1e-8,rel_tol=1e-9)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def jread(n):return json.loads((R/n).read_text())
def cread(n):return list(csv.DictReader((R/n).open()))
def parse(v):return None if v in [None,'','None'] else float(v)
def admitted(r):
    a=r['audit_source']
    return a['observed'] and a['formal_primary'] is not None and a['raw_present'] and a['numeric_status']=='ACCEPTED' and a['auction']=='CONTINUOUS' and r['tradable_index'] is not None
UP={'RISE','SHARP_RISE','PULLBACK','RISE_STOP'};DOWN={'DROP','SHARP_DROP','REBOUND','DROP_STOP'}
UM={'RISE','SHARP_RISE','REBOUND'};DM={'DROP','SHARP_DROP','PULLBACK'};STOPS={'RISE_STOP','DROP_STOP'}
def label_oracle(stream,pos,task,index):
    anchor=stream[pos];a=anchor['audit_source']
    if not admitted(anchor):return False,None,None,'CURRENT_NOT_OBSERVED_CONTINUOUS'
    if task=='CONTEXT_REVERSAL' and a['formal_primary'] not in UP:return False,None,None,'ANCHOR_NOT_UP_CONTEXT'
    if task=='MOTION_REVERSAL' and a['formal_primary'] not in UM:return False,None,None,'ANCHOR_NOT_UP_MOVE'
    prev=pos;seen=False;horizon=1 if task=='NEXT_OBSERVED_PRIMARY' else 30
    for step in range(1,horizon+1):
        dest=index.get(anchor['tradable_index']+step)
        if dest is None:return False,None,None,'WINDOW_OUTSIDE_SESSION'
        b=stream[dest]
        if dest!=prev+1 or b['scheduled_t']!=stream[prev]['scheduled_t']+1:return False,None,None,'SCHEDULE_DISCONTINUITY'
        if b['causal_segment_id']!=anchor['causal_segment_id']:return False,None,None,'SEGMENT_BREAK'
        if not admitted(b):return False,None,None,'NULL_GAP_OR_AUCTION'
        state=b['audit_source']['formal_primary'];change=state!=stream[prev]['audit_source']['formal_primary']
        f=b['features'];label=None
        if task=='NEXT_OBSERVED_PRIMARY' or task=='NEXT_DISTINCT_PRIMARY' and change:label=state
        if task=='MOTION_REVERSAL' and change:label='UP_MOVE_CONTINUE' if state in UM else 'DOWN_MOVE_REVERSAL' if state in DM else 'NON_DIRECTIONAL'
        if task=='CONTEXT_REVERSAL':
            if change and state in DOWN and f['context_direction']==-1:label='DOWN_REVERSAL'
            if change and state in {'RISE','SHARP_RISE'} and f['context_direction']==1 and f['local_direction']==1:label='UP_CONTINUE'
            seen=seen or state=='RANGE' or state in STOPS
        if label is not None:return True,label,b['bar_end'],None
        prev=dest
    if task=='NEXT_DISTINCT_PRIMARY':return False,None,None,'NO_TRANSITION_WITHIN30'
    label=('RANGE_OR_STOP' if seen else 'NO_DECISION_WITHIN30') if task=='CONTEXT_REVERSAL' else 'NO_DECISION'
    return True,label,stream[prev]['bar_end'],None
def anatomy_oracle(stream):
    chain=[];last=None;out=[]
    for r in stream:
        observed=r['audit_source']['observed'];t=r['scheduled_t']
        if not(observed and last is not None and last['audit_source']['observed'] and last['causal_segment_id']==r['causal_segment_id'] and last['scheduled_t']+1==t):chain=[]
        if observed:chain.append(r)
        runs=[];events=[]
        for i,row in enumerate(chain):
            p=row['audit_source']['formal_primary'];changed=i>0 and p!=chain[i-1]['audit_source']['formal_primary']
            if i==0 or changed:runs.append({'primary':p,'entered':row['scheduled_t'],'dwell':1})
            else:runs[-1]['dwell']+=1
            events.append((int(changed),int(i>0 and not changed),int(i>0 and row['features']['context_direction']!=chain[i-1]['features']['context_direction'])))
        f={}
        for k in range(1,5):
            previous=runs[-1-k] if len(runs)>k else None
            f['anatomy_previous_primary_'+str(k)]=previous['primary'] if previous else 'NULL'
            f['anatomy_previous_dwell_'+str(k)]=previous['dwell'] if previous else None
        f['anatomy_current_dwell']=runs[-1]['dwell'] if runs else None
        f['anatomy_bars_since_transition']=t-runs[-1]['entered'] if len(runs)>1 else None
        for k,column in [('transition',0),('hold',1),('context_flips',2)]:f['anatomy_'+k+'_count_15' if k!='context_flips' else 'anatomy_context_flips_15']=sum(x[column] for x in events[-15:])
        for kind in ['range','stop','fast']:
            matches=[x['scheduled_t'] for x in chain if x['audit_source']['formal_primary']=='RANGE'] if kind=='range' else [x['scheduled_t'] for x in chain if x['audit_source']['formal_primary'] in STOPS] if kind=='stop' else [x['scheduled_t'] for x in chain if x['features']['fast']==1]
            f['anatomy_'+kind+'_recency']=t-max(matches) if matches else None
        f['anatomy_segment_age']=r['features']['segment_age'];out.append((f,runs[-5:]))
        last=r
    return out
def weights(rows):
    sessions=Counter((r['date'],r['security_id'],r['session_id']) for r in rows)
    dates=Counter(d for d,s,z in sessions)
    w=np.asarray([1/(len(dates)*dates[r['date']]*sessions[(r['date'],r['security_id'],r['session_id'])]) for r in rows]);return w/w.mean()
def transform(art,rows):
    enc=art['encoder'];columns=[np.ones(len(rows))]
    for name in enc['numeric']:
        values=np.asarray([np.nan if r['features'][name] is None else r['features'][name] for r in rows]);missing=~np.isfinite(values);mean,sd=enc['stats'][name]
        columns.extend([np.where(missing,0,(values-mean)/sd),missing.astype(float)])
    for name in enc['categorical']:
        for v in enc['vocab'][name]:columns.append(np.asarray([r['features'][name]==v for r in rows],float))
    return np.column_stack(columns)
def replay(art,train,test,Y,model,schema,detail):
    w=weights(train)
    if art['encoder'] is None:
        prior=np.sum(Y*w[:,None],axis=0)/w.sum();check(np.allclose(prior,art['prior'],atol=1e-9,rtol=1e-8),'independent_prior',detail)
        lookup={}
        if model=='R1':
            for p in sorted({r['features']['formal_primary'] for r in train}):
                ix=np.asarray([r['features']['formal_primary']==p for r in train]);v=(np.sum(Y[ix]*w[ix,None],axis=0)+10*prior)/(w[ix].sum()+10);lookup[p]=v
                check(p in art['lookup'] and np.allclose(v,art['lookup'][p],atol=1e-9,rtol=1e-8),'independent_shrunk_lookup',detail+':'+p)
        raw=np.asarray([lookup.get(r['features']['formal_primary'],prior) for r in test])
    else:
        suffix='path' if model=='R3' else 'anatomy' if model=='R4' else None
        num=schema['numeric_state']+(schema['numeric_'+suffix] if suffix else []);cat=schema['categorical_state']+(schema['categorical_'+suffix] if suffix else [])
        enc=art['encoder'];check(enc['numeric']==num and enc['categorical']==cat,'encoder_allowlist',detail)
        for name in num:
            ix=[i for i,r in enumerate(train) if r['features'][name] is not None];mass=math.fsum(float(w[i]) for i in ix)
            mean=math.fsum(float(w[i])*float(train[i]['features'][name]) for i in ix)/mass if mass else 0.
            var=math.fsum(float(w[i])*(float(train[i]['features'][name])-mean)**2 for i in ix)/mass if mass else 0.
            sd=math.sqrt(var) if var>0 else 1.
            check(near(mean,enc['stats'][name][0]) and near(sd,enc['stats'][name][1]),'train_only_weighted_numeric_stats',detail+':'+name)
        for name in cat:check(enc['vocab'][name]==sorted({r['features'][name] for r in train}),'train_only_vocab',detail+':'+name)
        z=transform(art,train);coef=np.asarray(art['coefficients']);A=(z.T*w)@z/w.sum()+np.diag([0.]+[art['alpha']]*(z.shape[1]-1));B=(z.T*w)@Y/w.sum()
        check(np.max(np.abs(A@coef-B))<=1e-8*max(1.,np.max(np.abs(B))),'normal_equation_NO_REFIT',detail)
        raw=transform(art,test)@coef
    p=np.maximum(raw,1e-12);p/=p.sum(1,keepdims=True);return p
def calibrated(p,T):
    z=np.log(p)/T;z-=z.max(1,keepdims=True);z=np.exp(z);return z/z.sum(1,keepdims=True)
def weighted_ll(p,y,rows):return float(np.average(-np.log(np.maximum(p[np.arange(len(y)),y],1e-300)),weights=weights(rows)))
def metric_ref(rows,classes):
    idx={c:i for i,c in enumerate(classes)};m=np.zeros((len(classes),len(classes)),int)
    for r in rows:m[idx[r['actual']],idx[r['predicted']]]+=1
    pc=[]
    for i,c in enumerate(classes):
        actual=int(sum(m[i]));pred=int(sum(m[:,i]));correct=int(m[i,i]);p=correct/pred if pred else None;rec=correct/actual if actual else None
        f=None if p is None or rec is None else 2*p*rec/(p+rec) if p+rec else 0.
        pc.append({'Predicted_N':pred,'Correct_N':correct,'Precision':p,'Actual_N':actual,'Recalled_N':correct,'Recall':rec,'F1':f})
    days=defaultdict(list)
    for r in rows:days[r['date']].append(r)
    def loss(rr):
        return statistics.fmean(-math.log(max(r['probabilities'][idx[r['actual']]],1e-300)) for r in rr),statistics.fmean(math.fsum((v-int(j==idx[r['actual']]))**2 for j,v in enumerate(r['probabilities'])) for r in rr)
    ll,br=loss(rows) if rows else (None,None);dl=[loss(v) for v in days.values()]
    recs=[p['Recall'] for p in pc if p['Recall'] is not None];ece=0.
    for b in range(10):
        rr=[r for r in rows if min(int(max(r['probabilities'])*10),9)==b]
        if rr:ece+=len(rr)/len(rows)*abs(statistics.fmean(max(r['probabilities']) for r in rr)-statistics.fmean(r['actual']==r['predicted'] for r in rr))
    return {'row_N':len(rows),'date_N':len(days),'security_N':len({r['security_id'] for r in rows}),'security_session_N':len({(r['security_id'],r['session_id']) for r in rows}),
        'fold_N':len({r['fold'] for r in rows}),'accuracy':int(np.trace(m))/len(rows) if rows else None,'balanced_accuracy':statistics.fmean(recs) if recs else None,
        'macro_precision':sum(p['Precision'] or 0 for p in pc)/len(classes),'macro_recall':sum(p['Recall'] or 0 for p in pc)/len(classes),'macro_F1':sum(p['F1'] or 0 for p in pc)/len(classes),
        'Brier':br,'log_loss':ll,'date_equal_Brier':statistics.fmean(x[1] for x in dl) if dl else None,'date_equal_log_loss':statistics.fmean(x[0] for x in dl) if dl else None,'top_label_ECE':ece if rows else None},m,pc
def main():
    pre=jread('PREDICTIVENESS_V4_PRECOMMIT.json');schema=jread('FEATURE_SCHEMA_V4.json');classes=jread('REVERSAL_TARGET_SCHEMA.json')['classes'];manifest=jread('DATASET_MANIFEST_V4.json');split=jread('SPLIT_REALIZED_V4.json');foldmap={d:f['fold'] for f in split['folds'] for d in f['test_dates']}
    for n,h in pre['hashes'].items():check(sha(R/n)==h,'precommit_exact',n)
    for x in jread('FROZEN_IDENTITY_RECEIPT.json')['checks']:check(sha(R/x['member'])==x['expected_SHA256'],'frozen_exact',x['kind'])
    receipt=jread('C3_DATASET_FIXATION_RECEIPT.json');check(sha(R/'DATASET_MANIFEST_V4.json')==receipt['dataset_SHA256'],'C3_dataset_exact');check(sha(R/'SPLIT_REALIZED_V4.json')==receipt['split_SHA256'],'C3_split_exact')
    check([f['test_dates'] for f in split['folds']]==jread('SPLIT_PLAN_V4.json')['fixed_three_blocks'],'fixed_chronological_blocks')
    for x in jread('C4_LABEL_FIXATION_RECEIPT.json')['files']:check(sha(R/x['path'])==x['SHA256'],'fixed_label_hash',x['path'])
    features={};labels={};anatomies={}
    for pair in manifest['pairs']:
        f=Path(pair['feature_path']);check(sha(f)==pair['feature_SHA256'],'feature_file_hash',pair['pair_id']);original=Path(pair['original_feature_path']);check(sha(original)==pair['original_feature_SHA256'],'original_feature_hash',pair['pair_id']);trace=Path(pair['trace_path']);check(sha(trace)==pair['state_trace_SHA256'],'trace_hash',pair['pair_id'])
        stream=list(map(json.loads,f.read_text().splitlines()));old=list(map(json.loads,original.read_text().splitlines()));traces=list(map(json.loads,trace.read_text().splitlines()))
        import AUDIT_TRACE_PREFIX_V4
        AUDIT_TRACE_PREFIX_V4.run(sys.modules[__name__],stream,traces)
        lab=list(map(json.loads,(R/'LABELS'/f"{pair['pair_id']}.jsonl").read_text().splitlines()));check(len(stream)==len(lab)==len(old)==len(traces),'pair_length',pair['pair_id'])
        index={r['tradable_index']:i for i,r in enumerate(stream) if r['tradable_index'] is not None};an=anatomy_oracle(stream)
        for i,(r,prior,l) in enumerate(zip(stream,old,lab)):
            check(r['row_key'] not in features,'row_key_unique',r['row_key']);features[r['row_key']]=r;labels[r['row_key']]=l;anatomies[r['row_key']]=an[i][1]
            check(r['audit_source']==prior['audit_source'] and all(r['features'][k]==v for k,v in prior['features'].items()),'original_saved_features_unchanged',r['row_key'])
            check(r['feature_max_timestamp']<=r['bar_end'] and r['anatomy_source_max_timestamp']<=r['bar_end'],'prefix_timestamp',r['row_key'])
            check(not r['audit_source']['observed'] or r['audit_source']['raw_present'],'observed_requires_raw',r['row_key'])
            for k,v in an[i][0].items():check(r['features'][k]==v if isinstance(v,str) else near(r['features'][k],v),'anatomy_prefix_value',r['row_key']+':'+k)
            check([(x['primary'],x['entered'],x['dwell']) for x in r['anatomy_history']]==[(x['primary'],x['entered'],x['dwell']) for x in an[i][1]],'prefix_history_not_future_final_dwell',r['row_key'])
            si=index.get(r['tradable_index']+60) if r['tradable_index'] is not None else None
            bridge=False
            if si is not None:
                rr=stream[i:si+1];bridge=all(admitted(x) and x['causal_segment_id']==r['causal_segment_id'] for x in rr) and all(b['tradable_index']==a['tradable_index']+1 and b['scheduled_t']==a['scheduled_t']+1 for a,b in zip(rr,rr[1:]))
            for task in classes:
                av,y,end,reason=label_oracle(stream,i,task,index);s=l['REAL'][task]
                check((s['available'],s['target'],s['label_end'],s['reason'])==(av,y,end,reason),'ordered_label_oracle',r['row_key']+':'+task)
                av,y,end,reason=label_oracle(stream,si,task,index) if bridge else (False,None,None,'SHIFT_ANCHOR_OR_BRIDGE_UNAVAILABLE');s=l['SHIFT60'][task]
                check((s['available'],s['target'],s['label_end'],s['reason'])==(av,y,end,reason),'shift_bridge_label_oracle',r['row_key']+':'+task)
    donors={};permutation=cread('PERMUTATION_MAPPING_V4.csv');pergroups=defaultdict(list)
    for p in permutation:
        donors[(p['task'],p['feature_key'])]=p['donor_key'];a=features[p['feature_key']];b=features[p['donor_key']]
        check((a['date'],a['security_id'],a['session_id'])==(b['date'],b['security_id'],b['session_id']),'null_same_date_security_session',p['feature_key']);pergroups[(p['task'],a['date'],a['security_id'],a['session_id'])].append(p)
    for group,rr in pergroups.items():
        rr.sort(key=lambda r:r['feature_key']);seed=int(hashlib.sha256(('2026100402|'+group[0]+'|'+'|'.join(group[1:])).encode()).hexdigest()[:16],16);perm=np.random.default_rng(seed).permutation(len(rr));check([r['donor_key'] for r in rr]==[rr[int(i)]['feature_key'] for i in perm],'deterministic_null_permutation_identity',group)
    def target(key,task,control):return labels[donors.get((task,key),key) if control=='TRUE_NULL' else key]['REAL' if control=='TRUE_NULL' else control][task]
    oof=list(map(json.loads,(R/'OOF_ALL.jsonl').open()));byfit=defaultdict(list);grouped=defaultdict(list);foldgroups=defaultdict(list)
    for r in oof:
        byfit[r['fit_path']].append(r);key=(r['task'],r['control'],r['model'],r['calibrated']);grouped[key].append(r);foldgroups[key+(r['fold'],)].append(r)
        check(foldmap.get(r['date'])==r['fold'] and r['exposure']=='V4_NEW_DEV_EVAL','OOF_fixed_new_date_fold',r['row_key'])
    check(sum(len(v) for v in grouped.values())==len(oof),'OOF_all_records_grouped')
    receipt=jread('C5_OOF_FIXATION_RECEIPT.json');check(sha(R/'OOF_ALL.jsonl')==receipt['OOF_SHA256'] and len(oof)==receipt['classification_records'],'C5_exact_OOF_identity')
    ledger=list(map(json.loads,(R/'MODEL_EXECUTION_LEDGER.jsonl').read_text().splitlines()));check([x['fit_N'] for x in ledger]==list(range(1,len(ledger)+1)) and all(x['charged_before_fit'] for x in ledger),'append_before_fit_contiguous_ledger');ordinals=[]
    for item in jread('FIT_INDEX_V4.json')['items']:
        if item['status']!='FITTED':continue
        fp=item['path'];check(sha(R/fp)==item['SHA256'],'fixed_fitted_hash',fp);art=jread(fp);task=art['task'];control=art['control'];model=art['model'];cl=classes[task];fold=split['folds'][art['fold']-1]
        usable=[r for k,r in sorted(features.items()) if target(k,task,control)['available']]
        expected_train=[r['row_key'] for r in usable if r['date'] in fold['train_dates']];expected_test=[r['row_key'] for r in usable if r['date'] in fold['test_dates']]
        check(art['train_keys']==expected_train and art['test_keys']==expected_test,'exact_train_test_membership',fp)
        train=[features[k] for k in art['train_keys']];test=[features[k] for k in art['test_keys']]
        check(all(r['date']<fold['test_dates'][0] and target(r['row_key'],task,control)['label_end']<fold['test_start'] for r in train),'train_donor_end_purged',fp)
        Y=np.asarray([[int(target(r['row_key'],task,control)['target']==c) for c in cl] for r in train],float)
        check(hashlib.sha256(Y.astype('<f8').tobytes()).hexdigest()==art['train_target_hash'],'train_target_matrix_exact',fp)
        check(hashlib.sha256(json.dumps([[r['row_key'],r['features']] for r in train],sort_keys=True,separators=(',',':')).encode()).hexdigest()==art['train_feature_hash'],'train_feature_matrix_exact',fp)
        p=replay(art,train,test,Y,model,schema,fp);ordinals.append(art['charged_fit_ordinal']);inner_probs=[];inner_losses=[]
        last_train_date=max(x['date'] for x in train)
        expected_inner_train=[r['row_key'] for r in train if r['date']<last_train_date]
        expected_inner_validation=[r['row_key'] for r in train if r['date']==last_train_date]
        for k,inner in enumerate(art['inner_artifacts']):
            tr=[features[x] for x in inner['train_keys']];val=[features[x] for x in inner['validation_keys']];YY=np.asarray([[int(target(r['row_key'],task,control)['target']==c) for c in cl] for r in tr],float);yv=np.asarray([cl.index(target(r['row_key'],task,control)['target']) for r in val])
            check(inner['train_keys']==expected_inner_train and inner['validation_keys']==expected_inner_validation,'inner_training_only_keys',fp)
            pp=replay(inner,tr,val,YY,model,schema,fp+':inner'+str(k));check(np.allclose(pp,inner['validation_probabilities'],atol=1e-8,rtol=1e-8) and yv.tolist()==inner['validation_actual'],'inner_probabilities_and_truth_NO_REFIT',fp)
            ll=weighted_ll(pp,yv,val);inner_losses.append(ll);inner_probs.append((pp,yv,val));check(near(ll,art['validation_grid'][k]['validation_loss']),'independent_alpha_grid_loss',fp);ordinals.append(inner['charged_fit_ordinal'])
        if inner_probs:
            pick=min(range(len(inner_losses)),key=lambda k:(inner_losses[k],-(art['validation_grid'][k]['alpha'] or 0)));check(art['alpha']==art['validation_grid'][pick]['alpha'],'train_only_alpha_selection',fp)
            pp,yv,val=inner_probs[pick];grid=[]
            for T in [.5,.75,1.,1.25,1.5,2.]:grid.append((weighted_ll(calibrated(pp,T),yv,val),abs(T-1),-T,T))
            for k,v in enumerate(grid):check(near(v[0],art['temperature_grid'][k]['validation_loss']) and v[3]==art['temperature_grid'][k]['temperature'],'temperature_grid_replay',fp)
            check(art['temperature']==min(grid)[3],'train_only_temperature_selection',fp)
        else:check(art['temperature']==1 and art['inner_unavailable'],'unavailable_inner_fixed_fallback',fp)
        q=calibrated(p,art['temperature']);saved={(r['row_key'],r['calibrated']):r for r in byfit[fp]};check(len(saved)==2*len(test)==len(byfit[fp]),'OOF_completeness_no_duplicates',fp)
        for i,r in enumerate(test):
            t=target(r['row_key'],task,control)
            for cal,prob in [(False,p[i]),(True,q[i])]:
                row=saved.get((r['row_key'],cal));check(row is not None,'OOF_key_exists',fp)
                if row is None:continue
                check(row['actual']==t['target'] and row['label_end']==t['label_end'] and row['label_start']==t.get('label_start'),'OOF_truth_and_exact_label_end',r['row_key'])
                check(row['predicted']==cl[int(prob.argmax())] and np.allclose(row['probabilities'],prob,atol=1e-8,rtol=1e-8),'OOF_score_argmax_replay_NO_REFIT',r['row_key'])
    check(sorted(ordinals)==list(range(1,len(ledger)+1)) and len(ledger)==jread('FIT_INDEX_V4.json')['fit_operations'],'every_fit_ordinal_has_saved_artifact')
    boot=jread('BOOTSTRAP_GLOBAL_DATE_DRAWS.json');dates=boot['dates'];di={d:i for i,d in enumerate(dates)}
    check(len(boot['draws'])==1000 and boot['generated_vector_N']==1000 and boot['generation_invocation_N']==1,'saved_global1000_once')
    check(len({tuple(v) for v in boot['draws']})==boot['distinct_value_N'] and all(len(v)==len(dates) and all(0<=i<len(dates) for i in v) for v in boot['draws']),'saved_bootstrap_indices')
    check(sha(R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json')==jread('BOOTSTRAP_GLOBAL_1000_RECEIPT.json')['SHA256'],'bootstrap_exact_hash_NO_NEW_DRAWS')
    counts=np.asarray([np.bincount(v,minlength=len(dates)) for v in boot['draws']],float)
    def ratio(rr,numerator,denominator):
        a=np.zeros(len(dates));b=a.copy()
        for row in rr:a[di[row['date']]]+=bool(numerator(row));b[di[row['date']]]+=bool(denominator(row))
        aa=counts@a;bb=counts@b;return np.divide(aa,bb,out=np.full(1000,np.nan),where=bb>0)
    def ci(v,tail=.025):
        v=sorted(float(x) for x in v if np.isfinite(x))
        def quantile(q):
            h=(len(v)-1)*q;i=int(math.floor(h));return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(h-i)
        return (quantile(tail),quantile(1-tail),len(v)) if v else (None,None,0)
    for name,grouper,withfold in [('REVERSAL_METRICS_AGGREGATE_V4.csv',grouped,False),('REVERSAL_METRICS_BY_FOLD_V4.csv',foldgroups,True)]:
        for row in cread(name):
            key=(row['task'],row['control'],row['model'],row['calibrated']=='True')+((int(row['fold']),) if withfold else ());m=metric_ref(grouper.get(key,[]),classes[row['task']])[0]
            for k,v in m.items():check(near(parse(row[k]),v),'direct_metric_'+k,str(key))
    for row in cread('REVERSAL_CONFUSION_MATRIX_V4.csv'):
        key=(row['task'],row['control'],row['model'],row['calibrated']=='True');rr=grouped.get(key,[])
        check(int(row['N'])==sum(r['actual']==row['actual_class'] and r['predicted']==row['predicted_class'] for r in rr),'direct_confusion_cell',str(key))
    for row in cread('REVERSAL_PER_CLASS_METRICS_V4.csv'):
        key=(row['task'],row['control'],row['model'],row['calibrated']=='True');rr=grouped.get(key,[]);cl=classes[row['task']];pc=metric_ref(rr,cl)[2][cl.index(row['class'])]
        for k,v in pc.items():check(near(parse(row[k]),v),'direct_per_class_'+k,str(key)+':'+row['class'])
        c=row['class'];pl,ph,pv=ci(ratio(rr,lambda r:r['actual']==c and r['predicted']==c,lambda r:r['predicted']==c));rl,rh,rv=ci(ratio(rr,lambda r:r['actual']==c and r['predicted']==c,lambda r:r['actual']==c))
        check(near(pl,parse(row['precision_CI95_low'])) and near(ph,parse(row['precision_CI95_high'])) and pv==int(row['precision_valid_global_draws']) and near(rl,parse(row['recall_CI95_low'])) and near(rh,parse(row['recall_CI95_high'])),'direct_per_class_saved_vector_CI',str(key))
    def seq(key,length):
        hist=[r['primary'] for r in anatomies[key]][-length:];return '>'.join(['<MISSING>']*(length-len(hist))+hist)
    for name,pred,actual in [('UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V4.csv','UP_CONTINUE','DOWN_REVERSAL'),('DOWN_TO_UP_FALSE_NEGATIVE_V4.csv','DOWN_REVERSAL','UP_CONTINUE')]:
        for row in cread(name):
            rr=grouped.get(('CONTEXT_REVERSAL','REAL',row['model'],True),[]);kind=row['group_kind'];v=row['group']
            if kind=='FOLD':rr=[r for r in rr if str(r['fold'])==v]
            if kind=='DATE':rr=[r for r in rr if r['date']==v]
            if kind=='SECURITY':rr=[r for r in rr if r['security_id']==v]
            if kind=='CURRENT_PRIMARY':rr=[r for r in rr if r['current_primary']==v]
            if kind.startswith('SEQUENCE_LENGTH'):rr=[r for r in rr if seq(r['row_key'],int(kind[-1]))==v]
            pn=sum(r['predicted']==pred for r in rr);dn=sum(r['predicted']==pred and r['actual']==actual for r in rr);lo,hi,valid=ci(ratio(rr,lambda r:r['predicted']==pred and r['actual']==actual,lambda r:r['predicted']==pred))
            check(int(row['predicted_N'])==pn and int(row['opposite_actual_N'])==dn and near(parse(row['rate']),dn/pn if pn else None),'direct_dangerous_error_counts',name+':'+row['model']+':'+kind+':'+v)
            check(near(lo,parse(row['CI95_low'])) and near(hi,parse(row['CI95_high'])) and valid==int(row['valid_global_draws']),'direct_risk_saved_vector_CI',name+':'+v)
    primary=grouped.get(('CONTEXT_REVERSAL','REAL','R0',True),[])
    for length in range(1,5):
        for row in cread(f'PATH_ANATOMY_LENGTH{length}_V4.csv'):
            rr=[r for r in primary if seq(r['row_key'],length)==row['sequence']];check(len(rr)==int(row['N']) and len({r['date'] for r in rr})==int(row['date_N']) and len({r['security_id'] for r in rr})==int(row['security_N']),'direct_anatomy_support',row['sequence'])
            for c in classes['CONTEXT_REVERSAL']:
                n=sum(r['actual']==c for r in rr);lo,hi,valid=ci(ratio(rr,lambda r:r['actual']==c,lambda r:True))
                check(n==int(row[c+'_N']) and near(n/len(rr) if rr else None,parse(row[c+'_rate'])) and near(lo,parse(row[c+'_CI95_low'])) and near(hi,parse(row[c+'_CI95_high'])),'direct_anatomy_class_rate_CI',row['sequence']+':'+c)
    for row in cread('NEGATIVE_CONTROL_V4.csv'):
        key=(row['task'],'REAL',row['model'],row['calibrated']=='True');a={r['row_key']:r for r in grouped.get(key,[])};b={r['row_key']:r for r in grouped.get((row['task'],row['control'],row['model'],row['calibrated']=='True'),[])};keys=sorted(a.keys()&b.keys());ar=[a[k] for k in keys];br=[b[k] for k in keys]
        am=metric_ref(ar,classes[row['task']])[0];bm=metric_ref(br,classes[row['task']])[0]
        check(len(keys)==int(row['matched_row_N']) and row['matched_keys_PASS']=='True','matched_control_exact_keys',str(key))
        for prefix,m in [('REAL',am),('control',bm)]:
            for k in ['accuracy','log_loss','date_equal_log_loss']:check(near(parse(row[prefix+'_'+k]),m[k]),'direct_matched_control_metric',str(key))
        warning=row['model'] in ['R2','R3','R4'] and (bm['date_equal_log_loss'] is not None and am['date_equal_log_loss'] is not None and bm['date_equal_log_loss']<=am['date_equal_log_loss']+1e-12 or parse(row['REAL_gain_vs_R1']) is not None and float(row['REAL_gain_vs_R1'])>0 and float(row['control_gain_vs_R1'])>=.9*float(row['REAL_gain_vs_R1']))
        check((row['warning']=='True')==warning,'fixed_control_warning',str(key))
    import AUDIT_SUPPLEMENT_V4
    expected=AUDIT_SUPPLEMENT_V4.run(sys.modules[__name__],grouped,features,ratio,ci)
    caps=jread('BUDGET_START_V4.json')['finite_caps'];runner=jread('NEW_DEVELOPMENT/RUNNER_FINAL_RECEIPT.json')
    check(len(ledger)<=caps['fit_operations'] and jread('RUNNER_ACCOUNTING_V4.json')['actual_provider_HTTP_requests']<=caps['provider_HTTP_requests'] and runner['new_steps']<=caps['new_frozen_steps'] and len(manifest['pairs'])<=caps['completed_pairs'] and len(boot['draws'])<=caps['bootstrap_generated_vectors'],'finite_compute_budget')
    metric=metric_ref(primary,classes['CONTEXT_REVERSAL'])[0]
    result={'status':'PASS' if MISMATCH==0 else 'FAIL','assertion_N':sum(CHECKS.values()),'mismatch_N':MISMATCH,'counts':dict(CHECKS),'errors':ERRORS,
        'candidate_helper_imports':0,'independent_model_refits':0,'new_bootstrap_draws':0,'new_kernel_steps':0,'provider_requests':0,
        'core_rows':metric['row_N'],'core_dates':metric['date_N'],'core_folds':metric['fold_N'],
        'independent_source_SHA256':sha(Path(__file__)),'independence_scope':'Separate code, same assistant; no external human reviewer. Frozen State9/Path full semantic kernel re-audit deliberately not rerun; source/trace identity and prefix anatomy audited.',
        'raw_scope':'Exact derived values and saved source hashes checked; purged full provider responses not re-downloaded.'}
    (R/'INDEPENDENT_AUDIT_V4.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['counts','errors']}));print(json.dumps(ERRORS[:10]))
    if MISMATCH:raise SystemExit(1)
if __name__=='__main__':
    try:main()
    except Exception as exc:
        (R/'INDEPENDENT_AUDIT_RUNTIME_FAILURE_V4.json').write_text(json.dumps({'status':'RUNTIME_FAILURE','exception':type(exc).__name__,'message':str(exc),'assertion_N':sum(CHECKS.values()),'mismatch_N':MISMATCH,'counts':dict(CHECKS),'errors':ERRORS,'new_fits':0,'new_draws':0},sort_keys=True,indent=2)+'\n')
        raise
