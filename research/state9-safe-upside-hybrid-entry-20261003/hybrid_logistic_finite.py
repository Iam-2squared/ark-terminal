"""Precommitted fixed LR experiment. Maximum60 planned model fits, hard cap72.

Feature arrays and evaluator labels are separate. Thresholds use train-side
inner OOF first-cross decisions; outer test labels never select a family.
"""
import argparse
import collections
import concurrent.futures
import gzip
import hashlib
import json
from pathlib import Path
import threading
import warnings
import numpy as np
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning

HERE=Path(__file__).resolve().parent
FAMILIES=('H0','H1','H2')
KNOWN=('UP_FIRST','DOWN_FIRST','NEITHER')
CAP=72
LOCK=threading.Lock()
LEDGER=[]

def read(p):
    b=Path(p).read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):(HERE/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def gzip_write(path,records):
    with Path(path).open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as g:
        for x in records:g.write((json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())

class Preprocessor:
    def fit(self,num,cat):
        missing=~np.isfinite(num)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',RuntimeWarning);self.median=np.nanmedian(np.where(missing,np.nan,num),axis=0)
        self.all_missing=~np.isfinite(self.median);self.median[self.all_missing]=0.
        clean=np.where(missing,self.median,num)
        self.mean=clean.mean(axis=0);self.std=clean.std(axis=0);self.std[self.std==0]=1.
        assert np.isfinite(self.mean).all() and np.isfinite(self.std).all()
        self.categories=[sorted(set(cat[:,j])) for j in range(cat.shape[1])]
        self.maps=[{k:i for i,k in enumerate(c)} for c in self.categories]
        return self
    def transform(self,num,cat):
        missing=~np.isfinite(num);values=(np.where(missing,self.median,num)-self.mean)/self.std
        blocks=[sparse.csr_matrix(values),sparse.csr_matrix(missing.astype(np.float64))]
        offsets=np.cumsum([0]+[len(c) for c in self.categories]);rr=[];cc=[]
        for j,m in enumerate(self.maps):
            for i,v in enumerate(cat[:,j]):
                if v in m:rr.append(i);cc.append(offsets[j]+m[v])
        if len(self.categories):blocks.append(sparse.csr_matrix((np.ones(len(rr)),(rr,cc)),shape=(len(num),offsets[-1])))
        return sparse.hstack(blocks,format='csr')

def load_data(grid,h0_path):
    rows=read(grid);freeze=read(HERE/'FEATURE_FAMILY_FREEZE.json');index={r['id']:i for i,r in enumerate(rows)}
    h0=np.load(h0_path,mmap_mode='r',allow_pickle=False)
    assert h0.shape==(149900,480) and sha(h0_path)==read(HERE/'H0_SAVED_FEATURE_JOIN_RECEIPT.json')['matrix_sha256']
    numkeys=freeze['H1_numeric_added']+freeze['H2_numeric'];catkeys=freeze['H1_categorical_added']+freeze['H2_categorical']
    num=np.full((len(rows),len(numkeys)),np.nan);cat=np.empty((len(rows),len(catkeys)),dtype=object)
    state_n=0
    for line in gzip.open(HERE/'CAUSAL_STATE_CANDIDATE_ROWS.jsonl.gz','rt'):
        s=json.loads(line);i=index[s['row_id']];r=rows[i];state_n+=1
        assert s['intent_minute']==r['minute'] and (s['state_as_of_minute'] is None or s['state_as_of_minute']<=r['minute'])
        for j,k in enumerate(numkeys):
            v=s['H1'].get(k) if j<len(freeze['H1_numeric_added']) else s['H2'].get(k)
            if v is not None:num[i,j]=float(v)
        for j,k in enumerate(catkeys):
            v=s['H1'].get(k) if j<len(freeze['H1_categorical_added']) else s['H2'].get(k)
            cat[i,j]='__MISSING__' if v is None else str(v)
    assert state_n==149900
    labels=[None]*len(rows)
    for line in gzip.open(HERE/'FIRST_PASSAGE_LABELS.jsonl.gz','rt'):
        x=json.loads(line);i=index[x['row_id']]
        labels[i]=dict(status=x['primary_status'],fill_id=x['fill_id'],fill_minute=x['fill_minute'])
    assert all(x is not None for x in labels)
    return rows,h0,num,cat,labels,freeze

def receipt():
    write('MODEL_FIT_LEDGER.json',dict(planned_fits=60,hard_cap=CAP,
        started_fits=sum(x['status']!='PLANNED' for x in LEDGER),completed_fits=sum(x['status']=='COMPLETED' for x in LEDGER),
        hyperparameter_search=0,State_model_fits=0,exit_model_fits=0,fits=LEDGER))

def model_fit(fit_id,family,outer,role,inner,num,cat,rows,labels,tr,pr):
    known=np.array([labels[i]['status'] in KNOWN for i in tr]);train=tr[known]
    y=np.array([labels[i]['status']=='UP_FIRST' for i in train],dtype=int)
    assert len(np.unique(y))==2,'TRAINING_CLASS_SUPPORT_INCOMPLETE'
    counts=collections.Counter(rows[i]['opportunity'] for i in train)
    weights=np.array([1./counts[rows[i]['opportunity']] for i in train])
    assert abs(weights.sum()-len(counts))<1e-8
    train_sessions=sorted({rows[i]['session'] for i in train});score_sessions=sorted({rows[i]['session'] for i in pr})
    assert max(train_sessions)<min(score_sessions)
    assert not {rows[i]['opportunity'] for i in train}&{rows[i]['opportunity'] for i in pr}
    prep=Preprocessor().fit(num[train],cat[train]);matrix=prep.transform(num[train],cat[train])
    with LOCK:
        entry=next(x for x in LEDGER if x['fit_id']==fit_id)
        assert entry['status']=='PLANNED' and sum(x['status']!='PLANNED' for x in LEDGER)<CAP
        entry.update(status='STARTED',training_rows=len(train),excluded_unknown_training_rows=len(tr)-len(train),training_opportunities=len(counts),
            training_sessions=train_sessions,scoring_sessions=score_sessions,weight_sum=float(weights.sum()),min_weight=float(weights.min()),max_weight=float(weights.max()),
            positive_training_rows=int(y.sum()),expanded_feature_count=matrix.shape[1],all_missing_training_columns=int(prep.all_missing.sum()),
            preprocessing_fit_rows_sha256=hashlib.sha256('\n'.join(rows[i]['id'] for i in train).encode()).hexdigest())
        receipt()
    model=LogisticRegression(penalty='l2',C=1.,solver='liblinear',max_iter=1000,tol=1e-4,class_weight=None,random_state=0)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');model.fit(matrix,y,sample_weight=weights)
    scores=[]
    for lo in range(0,len(pr),10000):
        ix=pr[lo:lo+10000];scores.extend(model.decision_function(prep.transform(num[ix],cat[ix])).tolist())
    saved=HERE/'MODEL_ARITHMETIC'/f'{fit_id:02d}_{family}_outer{outer}_{role}{inner or 0}.npz';saved.parent.mkdir(exist_ok=True)
    np.savez_compressed(saved,median=prep.median,mean=prep.mean,std=prep.std,all_missing=prep.all_missing,
        coef=model.coef_[0],intercept=model.intercept_,categories_json=np.array(json.dumps(prep.categories)),classes=model.classes_)
    with LOCK:
        entry.update(status='COMPLETED',n_iter=int(model.n_iter_[0]),convergence_warnings=sum(isinstance(x.message,ConvergenceWarning) for x in caught),
            model_arithmetic_path=str(saved.relative_to(HERE)),model_arithmetic_sha256=sha(saved),score_rows=len(pr))
        receipt();print(json.dumps({'fit_completed':fit_id,'family':family,'outer':outer,'role':role,'inner':inner,'fits_completed_total':sum(x['status']=='COMPLETED' for x in LEDGER),'n_iter':entry['n_iter']}),flush=True)
    return np.array(scores),entry.copy()

def threshold_scan(indices,scores,rows,labels,outer,family):
    by=collections.defaultdict(list)
    for i,s in zip(indices,scores):by[rows[i]['opportunity']].append((rows[i]['minute'],float(s),int(i)))
    nodes={};events=collections.defaultdict(list)
    for oid,seq in by.items():
        records=[];high=-np.inf
        for _,s,i in sorted(seq):
            if s>high:records.append((s,i));high=s
        nodes[oid]=records
        for j,(s,i) in enumerate(records):events[s].append((oid,j))
    c=collections.Counter();ses=collections.Counter();selected=filled=0
    def update(i,delta):
        nonlocal selected,filled
        selected+=delta;x=labels[i]
        if x['fill_id'] is not None:filled+=delta
        c[x['status']]+=delta
        if x['status'] in KNOWN:ses[rows[i]['session']]+=delta
    for records in nodes.values():update(records[0][1],1)
    best={str(t):None for t in (.9,.85,.8)};curve=[];N=len(nodes)
    def inspect(threshold):
        known=sum(c[s] for s in KNOWN);precision=c['UP_FIRST']/known if known else None;down=c['DOWN_FIRST']/known if known else None
        sessions=sum(v>0 for v in ses.values());support=known>=100 and sessions>=10
        point=dict(outer_fold=outer,family=family,threshold=float(threshold),opportunities=N,selected_N=selected,filled_N=filled,
            evaluable_N=known,UP_FIRST=c['UP_FIRST'],DOWN_FIRST=c['DOWN_FIRST'],NEITHER=c['NEITHER'],ORDER_UNKNOWN=c['ORDER_UNKNOWN'],DATA_UNAVAILABLE=c['DATA_UNAVAILABLE'],
            represented_evaluable_sessions=sessions,precision=precision,DOWN_FIRST_rate=down,coverage=selected/N,no_entry_rate=1-selected/N,support_pass=support)
        curve.append(point)
        for target in (.9,.85,.8):
            if support and precision>=target and down<=.1:
                old=best[str(target)];key=(selected,-down,-point['no_entry_rate'],float(threshold))
                if old is None or key>(old['selected_N'],-old['DOWN_FIRST_rate'],-old['no_entry_rate'],old['threshold']):best[str(target)]=dict(point,precision_target=target,status='FEASIBLE')
    minimum=min(events);inspect(np.nextafter(minimum,-np.inf))
    for boundary,items in sorted(events.items()):
        for oid,j in items:
            records=nodes[oid];update(records[j][1],-1)
            if j+1<len(records):update(records[j+1][1],1)
        inspect(boundary)
    chosen=next((best[str(t)] for t in (.9,.85,.8) if best[str(t)] is not None),None)
    return dict(outer_fold=outer,family=family,inner_OOF_opportunities=N,inner_OOF_rows=len(indices),
        targets=best,selected_operating_point=chosen,status='FEASIBLE' if chosen else 'NO_CANDIDATE',
        threshold_boundaries_evaluated=len(curve),outer_labels_used=False),curve

def first_cross(rows,indices,scores,operating,family,outer):
    by=collections.defaultdict(list)
    for i,s in zip(indices,scores):by[rows[i]['opportunity']].append((int(i),float(s)))
    out=[]
    for oid,values in by.items():
        threshold=operating['threshold'] if operating else None
        found=next(((i,s) for i,s in sorted(values,key=lambda v:rows[v[0]]['minute']) if threshold is not None and s>threshold),None)
        r=rows[values[0][0]]
        out.append(dict(arm=family,outer_fold=outer,opportunity=oid,session=r['session'],
            status='BUY_INTENT' if found else 'NO_HIGH_CONFIDENCE_ENTRY',intent_row_id=rows[found[0]]['id'] if found else None,
            intent_minute=rows[found[0]]['minute'] if found else None,active_delay=rows[found[0]]['delay'] if found else None,
            raw_score=found[1] if found else None,threshold=threshold,precision_target=operating['precision_target'] if operating else None,
            forced_fallback=False,score_is_probability=False))
    return out

def family_job(family,outer,data):
    rows,h0,added,cat,labels,freeze=data;f=outer['id'];j=FAMILIES.index(family)
    if family=='H0':num=h0;cats=cat[:,:0]
    elif family=='H1':num=np.concatenate([h0,added[:,:33]],axis=1);cats=cat[:,:11]
    else:num=np.concatenate([h0,added],axis=1);cats=cat
    session=np.array([r['session'] for r in rows]);inner_indices=[];inner_scores=[];inner_records=[]
    for k,inn in enumerate(outer['inner']):
        tr=np.flatnonzero(np.isin(session,inn['train']));pr=np.flatnonzero(np.isin(session,inn['validation']))
        fit_id=(f-1)*12+j*4+k+1
        scores,model=model_fit(fit_id,family,f,'inner',inn['id'],num,cats,rows,labels,tr,pr)
        inner_indices.extend(pr);inner_scores.extend(scores)
        inner_records.extend(dict(row_id=rows[i]['id'],opportunity=rows[i]['opportunity'],session=rows[i]['session'],intent_minute=rows[i]['minute'],
            outer_fold=f,inner_fold=inn['id'],family=family,raw_score=float(s),model_fit_id=fit_id,max_training_session=max(model['training_sessions']),score_is_probability=False) for i,s in zip(pr,scores))
    selection,curve=threshold_scan(inner_indices,inner_scores,rows,labels,f,family)
    tr=np.flatnonzero(np.isin(session,outer['train']));pr=np.flatnonzero(np.isin(session,outer['test']));fit_id=(f-1)*12+j*4+4
    scores,model=model_fit(fit_id,family,f,'outer',None,num,cats,rows,labels,tr,pr)
    outer_records=[dict(row_id=rows[i]['id'],opportunity=rows[i]['opportunity'],session=rows[i]['session'],intent_minute=rows[i]['minute'],active_delay=rows[i]['delay'],
        outer_fold=f,family=family,raw_score=float(s),model_fit_id=fit_id,max_training_session=max(model['training_sessions']),score_is_probability=False) for i,s in zip(pr,scores)]
    entries=first_cross(rows,pr,scores,selection['selected_operating_point'],family,f)
    return dict(family=family,selection=selection,curve=curve,inner_records=inner_records,outer_records=outer_records,entries=entries,indices=pr,scores=scores)

def run(grid,h0_path,workers):
    assert read(HERE/'C4_GATE.json')['gate']=='PASS','C4_GATE_REQUIRED'
    assert not (HERE/'MODEL_FIT_LEDGER.json').exists(),'NO_REPEAT_EXPERIMENT'
    split=read(HERE/'SPLIT_PRECOMMIT.json');assert split['planned_fits']==60 and split['hard_cap']==CAP
    data=load_data(grid,h0_path)
    for outer in split['folds']:
        for j,family in enumerate(FAMILIES):
            for k in range(4):LEDGER.append(dict(fit_id=(outer['id']-1)*12+j*4+k+1,outer_fold=outer['id'],family=family,role='inner' if k<3 else 'outer',inner_fold=k+1 if k<3 else None,status='PLANNED'))
    receipt();oof={f:[] for f in FAMILIES};inner={f:[] for f in FAMILIES};curves=[];selections=[];entries=[];fold_choice=[]
    for outer in split['folds']:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:results=list(pool.map(lambda family:family_job(family,outer,data),FAMILIES))
        for x in results:
            family=x['family'];oof[family]+=x['outer_records'];inner[family]+=x['inner_records'];curves+=x['curve'];selections.append(x['selection']);entries+=x['entries']
        candidates=[]
        for target in (.9,.85,.8):
            candidates=[x for x in results if x['selection']['targets'][str(target)] is not None]
            if candidates:break
        choice=None
        if candidates:
            choice=min(candidates,key=lambda x:(-x['selection']['targets'][str(target)]['selected_N'],x['selection']['targets'][str(target)]['DOWN_FIRST_rate'],x['selection']['targets'][str(target)]['no_entry_rate'],FAMILIES.index(x['family'])))
            operating=choice['selection']['targets'][str(target)]
            chosen=first_cross(data[0],choice['indices'],choice['scores'],operating,'SELECTED_DEVELOPMENT',outer['id'])
            for x in chosen:x['selected_family']=choice['family']
        else:
            chosen=[dict(x,arm='SELECTED_DEVELOPMENT',selected_family=None) for x in results[0]['entries']]
        entries+=chosen
        fold_choice.append(dict(outer_fold=outer['id'],status='TRAIN_ONLY_SELECTION' if choice else 'NO_CANDIDATE',selected_family=choice['family'] if choice else None,
            selected_operating_point=choice['selection']['targets'][str(target)] if choice else None,outer_labels_used=False))
        print(json.dumps({'outer_fold_completed':outer['id'],'selected_family':fold_choice[-1]['selected_family'],'fits_completed':sum(x['status']=='COMPLETED' for x in LEDGER)}),flush=True)
    assert sum(x['status']=='COMPLETED' for x in LEDGER)==60
    for f in FAMILIES:
        assert len(oof[f])==65312 and len({x['row_id'] for x in oof[f]})==65312
        gzip_write(HERE/f'OOF_{f}.jsonl.gz',oof[f]);gzip_write(HERE/f'INNER_OOF_{f}.jsonl.gz',inner[f])
    gzip_write(HERE/'THRESHOLD_CURVES.jsonl.gz',curves);gzip_write(HERE/'ENTRY_CANDIDATE_RECORDS.jsonl.gz',entries)
    write('THRESHOLD_SELECTION_RECEIPT.json',dict(status='TRAIN_ONLY_THRESHOLD_SELECTION_COMPLETE',family_selections=selections,fold_selected_candidate=fold_choice,
        precision_targets=[.9,.85,.8],minimum_evaluable_opportunities=100,minimum_evaluable_sessions=10,DOWN_FIRST_rate_max=.1,
        threshold_selection_passes=15,precision_target_checks=45,threshold_boundaries_evaluated=len(curves),family_selection_passes=5,
        outer_labels_used=False,forced_fallback=False,new_model_fits=60,hard_cap=72,hyperparameter_search=0,bootstrap=0,provider_requests=0,
        code_sha256=sha(__file__),feature_contract_sha256=sha(HERE/'FEATURE_FAMILY_FREEZE.json'),split_contract_sha256=sha(HERE/'SPLIT_PRECOMMIT.json'),
        labels_sha256=sha(HERE/'FIRST_PASSAGE_LABELS.jsonl.gz'),score_handoff='raw logit; not absolute calibrated probability',productionReady=False))
    write('C5_COMPLETION.json',dict(status='C5_FINITE_EXPERIMENT_COMPLETE',model_fits=60,feature_families=3,model_families=1,outer_folds=5,inner_per_outer=3,
        policy_records=len(entries),opportunities_per_arm=2155,forced_fallbacks=0,provider_requests=0,protected_opens=0,new_label_creation_passes=0,
        calibration_certified=False,productionReady=False,FRESH_VALIDATION_REQUIRED=True))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--grid',required=True);ap.add_argument('--h0',required=True);ap.add_argument('--workers',type=int,default=3)
    a=ap.parse_args();run(a.grid,a.h0,a.workers)
