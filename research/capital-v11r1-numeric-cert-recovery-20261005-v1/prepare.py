"""Inference only. Saved predictions are references; current mP is causal inference."""
from control import *
from runtime import percentile
import numpy as np
def infer(rr,artifact):
    p=artifact['preprocessing'];a=np.asarray([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in p['numeric_fields']] for r in rr],dtype=np.float64)
    assert not np.isinf(a).any()
    a=np.column_stack([np.nan_to_num(a,nan=0.),np.isnan(a).astype(np.float64)])
    a=(a-np.asarray(p['numeric_mean']))/np.asarray(p['numeric_scale']);col=[]
    for k in p['categorical_fields']:
        vocab=p['categorical_train_vocab'][k];vv=[r['categorical'][k] if r['categorical'][k] in vocab else '__UNKNOWN__' for r in rr]
        col.extend([[float(v==c) for v in vv] for c in vocab])
    x=np.column_stack([a,np.asarray(col,dtype=np.float64).T])
    return np.exp(-np.logaddexp(0,-(x@np.asarray(artifact['coef'])+artifact['intercept'])))
def tables():
    train=rows(V9/'private/QUALITY_TRAIN_SCORE_TABLE.jsonl.gz');tenure=read(B2/'B2_TENURE_LOOKUP_TABLE.json');out={}
    for b in read(SPLIT)['blocks']:
        rr=[r for r in train if r['block']==b['block']]
        out[str(b['block'])]={'training_sessions':b['train'],'test_sessions':b['test'],'tenure':tenure[str(b['block'])],'sessions':{d:[r for r in rr if r['session']==d and r['band']!='P_BELOW'] for d in b['train']}}
    return out
def policy_freeze():
    cert=read(OUT/'S9R_CERTIFICATION_DECISION.json');assert cert['S9R']=='PASS'
    p=PARENT/'M1_M2_CAPITAL_POLICY_PRECOMMIT.json';o=read(p)
    assert sha(p)=='5db3336d0bdf9c9e09d0481f4fa09fbb1e94229979bbd8e1a97057380ee73d42'
    assert [o['policies'][k]['name'] for k in ('M1','M2')]==ARMS
    save(OUT/'M1_M2_POLICY_HASH_FREEZE.json',{'exact_jst':now(),'status':'PASS','authority_path':str(p.relative_to(ROOT)),'sha256':sha(p),'semantic_body':o,'policy_change':0,'old_performance_before_policy_precommit':False,'Safety':SAFETY})
    checkpoint('N8_M1_M2_POLICY_HASH_FREEZE','Original pre-performance M1/M2 JSON hash and semantics exact','N9 runtime inference and frozen resubstitution percentiles')
def build():
    assert read(OUT/'M1_M2_POLICY_HASH_FREEZE.json')['status']=='PASS'
    raw=rows(MAIN/'inputs/movement/RUNTIME_CAUSAL.jsonl.gz');saved={r['entry_id']:r for r in rows(V11/'private/MRET_OOF_SCORES.jsonl.gz')};training=rows(V11/'private/MRET_TRAIN_RESUBSTITUTION_SCORES.jsonl.gz')
    current=rows(V9/'private/CURRENT_CAUSAL_QUALITY_RUNTIME.jsonl.gz');cm={r['entry_id']:r for r in current};audit=[];maxdelta=0.
    for block in read(SPLIT)['blocks']:
        b=block['block'];path=V11/f'private/models/MRET_BLOCK_{b:02}.json';m=read(path);train=[r for r in training if r['block']==b];test=[r for r in raw if r['session'] in block['test']]
        assert [r['entry_id'] for r in train]==m['train_entry_ids'] and all(r['session'] in block['train'] and r['session']<min(block['test']) for r in train)
        dist=sorted(r['mP'] for r in train)
        for r,p in zip(test,infer(test,m)):
            k=r['entry_id'];delta=abs(float(p)-saved[k]['mP']);maxdelta=max(maxdelta,delta);assert delta<=1e-12
            cm[k].update(mP=float(p),rM=percentile(float(p),dist),MRET_train_N=len(dist))
        audit.append({'block':b,'model_sha256':sha(path),'train_score_N':len(dist),'train_entry_order_exact':True,'completed_past_only':True})
    assert len(current)==1039 and all(0<r['rM']<=1 for r in current)
    gzsave(PRIVATE/'CURRENT_MRET_CAP_RUNTIME.jsonl.gz',current)
    # Identity/score projection has no teacher or actual Potential/EXIT fields.
    gzsave(PRIVATE/'FROZEN_MRET_PERCENTILE_TRAIN_SCORES.jsonl.gz',training)
    save(PRIVATE/'PRIMARY_I2_PAST_TABLES.json',tables())
    save(OUT/'RUNTIME_MRET_PERCENTILE_FREEZE.json',{'exact_jst':now(),'status':'PASS','current_N':1039,'training_N':len(training),'current_causal_inference':True,'saved_current_score_decision_injection':False,'current_score_delta_vs_v11_max':maxdelta,'score_tolerance':1e-12,'training_scores':'frozen MRET resubstitution, no regeneration','training_authority_sha256':sha(V11/'private/MRET_TRAIN_RESUBSTITUTION_SCORES.jsonl.gz'),'runtime_sha256':sha(PRIVATE/'CURRENT_MRET_CAP_RUNTIME.jsonl.gz'),'percentile_training_sha256':sha(PRIVATE/'FROZEN_MRET_PERCENTILE_TRAIN_SCORES.jsonl.gz'),'I2_table_semantic_source_sha256':sha(V9/'private/QUALITY_TRAIN_SCORE_TABLE.jsonl.gz'),'tenure_authority_sha256':sha(B2/'B2_TENURE_LOOKUP_TABLE.json'),'label_fields':[],'test_cross_section':False,'probability_claim':False,'newFits':0,'blocks':audit,'Safety':SAFETY})
    checkpoint('N9_RUNTIME_MRET_PERCENTILE_FREEZE',{'current_N':1039,'training_N':len(training),'score_delta_max':maxdelta,'newFits':0},'70+ causal canaries and independent pre-main cap audit')
if __name__=='__main__':
    import sys
    {'policy':policy_freeze,'build':build}[sys.argv[1]]()
