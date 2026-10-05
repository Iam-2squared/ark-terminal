"""Fixed Movement preprocessing and eight exclusive MRET optimizer calls."""
from control import *
import warnings, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
SPEC=read(OUT/'MRET_TEACHER_FEATURE_MODEL_PRECOMMIT.json')
NUMERIC=SPEC['features']['numeric_fields'];CATEGORICAL=SPEC['features']['categorical_fields'];UNKNOWN='__UNKNOWN__'
def transform(train,test):
    def numeric(rr):
        a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in NUMERIC] for r in rr]);assert not np.isinf(a).any()
        return np.column_stack([np.nan_to_num(a,nan=0),np.isnan(a).astype(float)])
    a=numeric(train);z=numeric(test);mu=a.mean(axis=0);scale=a.std(axis=0);scale[scale==0]=1
    vocab={k:sorted({r['categorical'][k] or UNKNOWN for r in train}|{UNKNOWN}) for k in CATEGORICAL}
    def cat(rr):
        col=[]
        for k in CATEGORICAL:
            vv=[r['categorical'][k] if r['categorical'][k] in vocab[k] else UNKNOWN for r in rr]
            col.extend([[float(v==c) for v in vv] for c in vocab[k]])
        return np.array(col).T
    return np.column_stack([(a-mu)/scale,cat(train)]),np.column_stack([(z-mu)/scale,cat(test)]),{'numeric_fields':NUMERIC,'categorical_fields':CATEGORICAL,'numeric_mean':mu.tolist(),'numeric_scale':scale.tolist(),'categorical_train_vocab':vocab,'constant_missing':0,'missing_indicators':True,'training_only':True}
def predict(rr,artifact):
    prep=artifact['preprocessing'];nn=prep['numeric_fields'];cc=prep['categorical_fields']
    a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in nn] for r in rr]);assert not np.isinf(a).any()
    a=np.column_stack([np.nan_to_num(a,nan=0),np.isnan(a).astype(float)]);a=(a-np.array(prep['numeric_mean']))/np.array(prep['numeric_scale']);col=[]
    for k in cc:
        voc=prep['categorical_train_vocab'][k];vv=[r['categorical'][k] if r['categorical'][k] in voc else UNKNOWN for r in rr]
        col.extend([[float(v==c) for v in vv] for c in voc])
    x=np.column_stack([a,np.array(col).T]);return np.exp(-np.logaddexp(0,-(x@np.array(artifact['coef'])+artifact['intercept'])))
def claim():
    assert (PRIVATE/'claims/R4_TEACHER_CONTROLS_COMPLETE.json').exists()
    files={str(p.relative_to(ROOT)):sha(p) for p in CODE.glob('*.py')}
    o={'exact_jst':now(),'basis':read(WORK/'latest_basis.json'),'new_fit_budget':8,'other_fits':0,'one_call_per_block':True,'reexecution_allowed':False,'code_sha256':files,'raw_features_sha256':sha(MAIN/'inputs/movement/RUNTIME_CAUSAL.jsonl.gz'),'label_projection_hashes':{p.name:sha(p) for p in (PRIVATE/'train_labels').glob('*')},'precommit_sha256':sha(OUT/'MRET_TEACHER_FEATURE_MODEL_PRECOMMIT.json'),'Safety':SAFETY}
    save(OUT/'MRET_FIT_CLAIM.json',o);checkpoint('R5_MRET_FIT_CLAIM','Exactly eight optimizer fits claimed; no heldout label payload in trainer','commit -> actual GET -> model.py fit')
def fit():
    assert (WORK/'publication_receipts/R5_MRET_FIT_CLAIM_BEFORE_8_FITS_ACTUAL_GET.json').exists()
    c=read(OUT/'MRET_FIT_CLAIM.json')
    for p,h in c['code_sha256'].items():assert sha(ROOT/p)==h,'CLAIMED_CODE_CHANGED'
    raw=rows(MAIN/'inputs/movement/RUNTIME_CAUSAL.jsonl.gz')
    # Only allowlisted raw causal columns enter X. Identity/session select blocks only.
    causal=[{'entry_id':r['entry_id'],'session':r['session'],'numeric':{k:r['numeric'][k] for k in NUMERIC},'categorical':{k:r['categorical'][k] for k in CATEGORICAL}} for r in raw]
    current=[];training=[];ledger=[];reconstruction=0.
    for block in read(SPLIT)['blocks']:
        b=block['block'];started=PRIVATE/f'claims/MRET_BLOCK_{b:02d}_STARTED.json';complete=PRIVATE/f'claims/MRET_BLOCK_{b:02d}_COMPLETE.json'
        assert not started.exists() and not complete.exists(),'AMBIGUOUS_OR_COMPLETED_FIT_NO_REEXECUTION'
        path=PRIVATE/f'train_labels/MRET_BLOCK_{b:02d}_PAST_ONLY.jsonl.gz';assert sha(path)==c['label_projection_hashes'][path.name]
        yy={r['entry_id']:r for r in rows(path)};train=[r for r in causal if r['entry_id'] in yy];test=[r for r in causal if r['session'] in block['test']]
        assert len(train)==len(yy) and all(r['session'] in block['train'] for r in train)
        assert max(r['session'] for r in train)<min(block['test'])
        y=np.array([yy[r['entry_id']]['label'] for r in train],dtype=int);assert set(y)=={0,1}
        a,z,prep=transform(train,test)
        save(started,{'exact_jst':now(),'block':b,'claim_basis':read(WORK/'latest_basis.json'),'train_label_file':path.name,'train_labels_sha256':sha(path),'train_N':len(train),'test_N':len(test),'heldout_teacher_payload_reads':0,'optimizer_calls_requested':1,'Safety':SAFETY})
        clf=LogisticRegression(**SPEC['model'])
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter('always');clf.fit(a,y)
        convergence=[str(w.message) for w in ws if issubclass(w.category,ConvergenceWarning)]
        if convergence:
            save(PRIVATE/f'claims/MRET_BLOCK_{b:02d}_CONTRACT_FAIL.json',{'exact_jst':now(),'ConvergenceWarning':convergence,'optimizer_calls':1,'retry_allowed':False});raise RuntimeError('V11_CONTRACT_FAIL_CONVERGENCE')
        prob=clf.predict_proba(z)[:,1];tp=clf.predict_proba(a)[:,1]
        artifact={'head':'MRET','block':b,'parameters':SPEC['model'],'preprocessing':prep,'coef':clf.coef_[0].tolist(),'intercept':float(clf.intercept_[0]),'classes':clf.classes_.tolist(),'iterations':int(clf.n_iter_[0]),'train_entry_ids':[r['entry_id'] for r in train],'train_N':len(train),'train_positive_N':int(y.sum()),'train_session_N':len(block['train']),'train_through':max(block['train']),'test_dates':block['test'],'base_rate':float(y.mean()),'heldout_teacher_payload_reads':0,'optimizer_calls':1,'claim_sha256':sha(OUT/'MRET_FIT_CLAIM.json')}
        delta=float(np.max(np.abs(predict(test,artifact)-prob)));assert delta<=1e-12;reconstruction=max(reconstruction,delta)
        p=PRIVATE/f'models/MRET_BLOCK_{b:02d}.json';save(p,artifact)
        snap=PRIVATE/f'fitted_state/MRET_BLOCK_{b:02d}.npz';snap.parent.mkdir(exist_ok=True)
        with snap.open('xb') as f:np.savez(f,coef=clf.coef_,intercept=clf.intercept_,classes=clf.classes_,iterations=clf.n_iter_,numeric_mean=np.array(prep['numeric_mean']),numeric_scale=np.array(prep['numeric_scale']))
        current.extend({'entry_id':r['entry_id'],'session':r['session'],'block':b,'mP':float(v)} for r,v in zip(test,prob))
        training.extend({'entry_id':r['entry_id'],'session':r['session'],'block':b,'mP':float(v)} for r,v in zip(train,tp))
        done={'exact_jst':now(),'block':b,'train_N':len(train),'test_N':len(test),'train_positive_N':int(y.sum()),'iterations':int(clf.n_iter_[0]),'model_sha256':sha(p),'snapshot_sha256':sha(snap),'warnings':[{'category':w.category.__name__,'message':str(w.message)} for w in ws],'ConvergenceWarning_N':0,'heldout_teacher_payload_reads':0,'optimizer_calls':1,'reconstruction_max_delta':delta}
        save(complete,done);ledger.append(done);print(json.dumps({'block':b,'fit':'COMPLETE','iterations':done['iterations']}),flush=True)
    assert len(current)==1039 and len({r['entry_id'] for r in current})==1039
    gzsave(PRIVATE/'MRET_OOF_SCORES.jsonl.gz',current);gzsave(PRIVATE/'MRET_TRAIN_RESUBSTITUTION_SCORES.jsonl.gz',training)
    save(OUT/'MRET_8_FITS_RESULT.json',{'status':'COMPLETE','fits':8,'fit_ledger':ledger,'OOF_N':len(current),'train_score_N':len(training),'train_score_kind':'RESUBSTITUTION','OOF_causal_reconstruction_max_delta':reconstruction,'ConvergenceWarning_N':0,'heldout_teacher_payload_reads_before_fit':0,'within_block_refits':0,'other_fits':0,'Safety':SAFETY})
    checkpoint('R6_MRET_8_FITS_COMPLETE','Eight one-shot fits complete; causal OOF score reconstructed; test teacher join0 in trainer','R7 single evaluation')
if __name__=='__main__':
    import sys
    if sys.argv[1]=='claim':claim()
    elif sys.argv[1]=='fit':fit()
    else:raise RuntimeError('invalid action')
