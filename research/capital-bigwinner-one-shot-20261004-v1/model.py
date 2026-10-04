"""Exactly one deterministic L2 logistic classifier; one expanding temporal stream."""
import gzip
import json
import math
from pathlib import Path
import warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from checkpoint import ROOT,OUT,save,sha
from features import NUMERIC,CATEGORICAL,UNKNOWN
from contracts import rank
from prepare import rows,gzwrite,PRIVATE

def fit_transform(train,test):
    def numeric(rr):
        a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in NUMERIC] for r in rr])
        assert not np.isinf(a).any()
        missing=np.isnan(a).astype(float)
        return np.column_stack([np.nan_to_num(a,nan=0.0),missing])
    a=numeric(train);z=numeric(test)
    means=a.mean(axis=0);scale=a.std(axis=0);scale[scale==0]=1
    a=(a-means)/scale;z=(z-means)/scale
    vocab={k:sorted({r['categorical'][k] or UNKNOWN for r in train}|{UNKNOWN}) for k in CATEGORICAL}
    def categories(rr):
        columns=[]
        for k in CATEGORICAL:
            values=[r['categorical'][k] if r['categorical'][k] in vocab[k] else UNKNOWN for r in rr]
            columns.extend([[float(v==c) for v in values] for c in vocab[k]])
        return np.asarray(columns).T
    return np.column_stack([a,categories(train)]),np.column_stack([z,categories(test)]),{
        'numeric_mean':means.tolist(),'numeric_scale':scale.tolist(),'categorical_train_vocab':vocab,
        'missing_strategy':'constant0 with one explicit indicator per numeric field; all fitted scales training-only',
        'feature_columns':len(means)+sum(len(v) for v in vocab.values())}

def predict_saved(rr,artifact):
    a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in NUMERIC] for r in rr])
    a=np.column_stack([np.nan_to_num(a,nan=0),np.isnan(a).astype(float)])
    prep=artifact['preprocessing']
    a=(a-np.array(prep['numeric_mean']))/np.array(prep['numeric_scale'])
    cat=[]
    for k in CATEGORICAL:
        voc=prep['categorical_train_vocab'][k]
        vals=[r['categorical'][k] if r['categorical'][k] in voc else UNKNOWN for r in rr]
        cat.extend([[float(v==c) for v in vals] for c in voc])
    x=np.column_stack([a,np.array(cat).T])
    logits=x@np.array(artifact['coef'])+artifact['intercept']
    return np.exp(-np.logaddexp(0,-logits))

def main():
    assert (OUT/'MODEL_PRECOMMIT.json').exists()
    runtime=rows(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz')
    teachers={r['entry_id']:r for r in rows(PRIVATE/'TEACHERS_EVALUATION.jsonl.gz')}
    days=sorted({r['session'] for r in runtime})
    assert len(days)==58
    scored=[];fit_ledger=[];models=[];hashes={}
    for start in range(20,58,5):
        past=set(days[:start]);future=set(days[start:start+5])
        train=[r for r in runtime if r['session'] in past and r['entry_minute']<920 and teachers[r['entry_id']]['label_bigwinner5'] is not None]
        test=[r for r in runtime if r['session'] in future]
        assert max(r['session'] for r in train)<min(future)
        y=np.array([teachers[r['entry_id']]['label_bigwinner5'] for r in train],dtype=int)
        assert set(y)=={0,1},'MODEL_SUPPORT_BLOCKED_SINGLE_CLASS'
        a,z,prep=fit_transform(train,test)
        classifier=LogisticRegression(penalty='l2',C=1.0,solver='lbfgs',max_iter=2000,class_weight=None,random_state=57)
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter('always')
            classifier.fit(a,y)
        assert not any(issubclass(w.category,ConvergenceWarning) for w in ws),'FIXED_MODEL_DID_NOT_CONVERGE'
        prob=classifier.predict_proba(z)[:,1]
        base=float(y.mean())
        artifact={'block':len(models)+1,'train_session_N':start,'train_through':days[start-1],
            'test_dates':days[start:start+5],'train_N':len(y),'train_positive_N':int(y.sum()),'base_rate':base,
            'preprocessing':prep,'coef':classifier.coef_[0].tolist(),'intercept':float(classifier.intercept_[0]),
            'iterations':int(classifier.n_iter_[0]),'random_seed':57,'class_weight':None}
        assert np.max(np.abs(predict_saved(test,artifact)-prob))<1e-12
        model_name=f'BLOCK_{len(models)+1:02d}.json'
        save(PRIVATE/'models'/model_name,artifact)
        hashes[model_name]=sha(PRIVATE/'models'/model_name)
        for r,p in zip(test,prob):
            rk,lift=rank(float(p),base)
            scored.append({**r,'p_bigwinner5':float(p),'base_rate':base,'winner_lift':lift,'rank':rk,
                'block':len(models)+1,'model_sha256':hashes[model_name]})
        models.append(artifact)
        fit_ledger.append({k:artifact[k] for k in ('block','train_session_N','train_through','test_dates','train_N','train_positive_N','base_rate','iterations')})
    assert len(fit_ledger)==8
    assert len(scored)==sum(r['session'] in days[20:] for r in runtime)
    gzwrite(PRIVATE/'ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz',scored)
    save(PRIVATE/'MODEL_HASHES.json',hashes)
    save(OUT/'ROLLING_ORIGIN_SCORE_RESULT.json',{'status':'SCORE_STREAM_COMPLETE','fits':8,'evaluation_sessions':38,
        'OOF_candidate_N':len(scored),'fit_ledger':fit_ledger,'model_hashes':hashes,
        'score_stream_sha256':sha(PRIVATE/'ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz'),
        'rank_distribution':{k:sum(r['rank']==k for r in scored) for k in ('S','A','B','C')},
        'test_outcomes_used_in_fit':False,'within_block_refits':0,'profile_refits':0,
        'hyperparameter_sweeps':0,'feature_sweeps':0,'threshold_sweeps':0,'productionReady':False})
    print(json.dumps({'fits':8,'evaluation_sessions':38,'OOF_candidates':len(scored),'stream_hash':sha(PRIVATE/'ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz')}))

if __name__=='__main__':main()
