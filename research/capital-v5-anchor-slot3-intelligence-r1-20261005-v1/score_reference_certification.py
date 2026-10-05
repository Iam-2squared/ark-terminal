"""Causal frozen-model inference only; no trainer, replay, teacher or PnL imports."""
from pathlib import Path
import bisect, gzip, hashlib, json, math
import numpy as np

ROOT=Path('/workspace/scratch/f3d0aa747c89')
INPUT=ROOT/'r1_work/inputs'
HEADS=('pP','MOVE_U2','MOVE_U3','MRET')

def rows(p):
    with gzip.open(p,'rt') as f:return [json.loads(line) for line in f]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(data,f,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def gzsave(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(gzip.compress(('\n'.join(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False) for x in data)+'\n').encode(),mtime=0))

def infer(raw,model):
    """FIT_NUMERIC_OPERATOR_V1 with the frozen saved constants; no recomputation."""
    prep=model['preprocessing'];fields=prep['numeric_fields']
    a=np.asarray([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in fields] for r in raw],dtype=np.float64)
    assert not np.isinf(a).any(),'NONFINITE_CAUSAL_INPUT'
    a=np.column_stack([np.nan_to_num(a,nan=0.),np.isnan(a).astype(np.float64)])
    a=(a-np.asarray(prep['numeric_mean'],dtype=np.float64))/np.asarray(prep['numeric_scale'],dtype=np.float64)
    columns=[]
    for k in prep['categorical_fields']:
        vocab=prep['categorical_train_vocab'][k]
        values=[r['categorical'][k] if r['categorical'][k] in vocab else '__UNKNOWN__' for r in raw]
        columns.extend([[float(v==c) for v in values] for c in vocab])
    x=np.column_stack([a,np.asarray(columns,dtype=np.float64).T])
    logits=x@np.asarray(model['coef'],dtype=np.float64)+model['intercept']
    scores=np.exp(-np.logaddexp(0,-logits))
    assert np.isfinite(scores).all()
    return [float(v) for v in scores]

def scalar_infer(row,model):
    """Separate scalar construction for independent score tolerance checks."""
    p=model['preprocessing'];raw=[row['numeric'][k] for k in p['numeric_fields']]
    vector=[float(v) if v is not None else 0. for v in raw]+[float(v is None) for v in raw]
    vector=[(v-m)/s for v,m,s in zip(vector,p['numeric_mean'],p['numeric_scale'])]
    for k in p['categorical_fields']:
        vocab=p['categorical_train_vocab'][k];value=row['categorical'][k]
        if value not in vocab:value='__UNKNOWN__'
        vector.extend(float(value==c) for c in vocab)
    logit=math.fsum([model['intercept']]+[v*c for v,c in zip(vector,model['coef'])])
    return 1/(1+math.exp(-logit)) if logit>=0 else math.exp(logit)/(1+math.exp(logit))

def rank(score,reference):
    assert math.isfinite(score) and reference and all(math.isfinite(v) for v in reference)
    less=bisect.bisect_left(sorted(reference),score);numerator=1+less;denominator=len(reference)+1
    return {'score':score,'rank_numerator':numerator,'rank_denominator':denominator,'less_count':less,'reference_N':len(reference),'LOW':2*numerator<denominator,'HIGH':2*numerator>=denominator}

def model_paths(block):
    return {
      'pP':INPUT/'v8r1/inputs/movement/models'/f'MOVE_P_BLOCK_{block:02d}.json',
      'MOVE_U2':INPUT/'quality/private/models'/f'MOVE_U2_BLOCK_{block:02d}.json',
      'MOVE_U3':INPUT/'quality/private/models'/f'MOVE_U3_BLOCK_{block:02d}.json',
      'MRET':INPUT/'mret/private/models'/f'MRET_BLOCK_{block:02d}.json'}

def certify():
    out=ROOT/'r1_work/score_certification'
    claim=out/'INFERENCE_CLAIM.json'
    assert not claim.exists(),'CLAIM_EXISTS_NO_REINFERENCE'
    manifest=read(INPUT/'INPUT_TRANSPORT_MANIFEST.json')
    save(claim,{'R2_actual_GET_HEAD':'6aaa325aa339f8f75083af47d0d0566621cd3118','code_sha256':sha(__file__),'input_transport_sha256':sha(INPUT/'INPUT_TRANSPORT_MANIFEST.json'),'four_head_reference_certification_invocation':1,'new_fit':0,'market_replays':0,'score_pnl_joins':0,'reexecution_permitted':False})
    raw=rows(INPUT/'v8r1/inputs/movement/RUNTIME_CAUSAL.jsonl.gz')
    lookup={r['entry_id']:r for r in raw};assert len(lookup)==len(raw)
    native=rows(INPUT/'v5_source/capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')
    native_map={r['entry_id']:r for r in native};assert len(native_map)==len(native)==1039
    split=read(INPUT/'v5_source/repo/docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json')
    ptrain=rows(INPUT/'v8r1/private/TRAIN_MAPPED_SCORES.jsonl.gz')
    qtrain=rows(INPUT/'v9/private/QUALITY_TRAIN_SCORE_TABLE.jsonl.gz')
    mtrain=rows(INPUT/'mret/private/MRET_TRAIN_RESUBSTITUTION_SCORES.jsonl.gz')
    saved_current=rows(INPUT/'v9/private/CURRENT_CAUSAL_QUALITY_RUNTIME.jsonl.gz')
    saved_mcurrent=rows(INPUT/'mret/private/MRET_OOF_SCORES.jsonl.gz')
    current_map={r['entry_id']:r for r in saved_current}
    mcurrent_map={r['entry_id']:r for r in saved_mcurrent}
    assert set(native_map)==set(current_map)==set(mcurrent_map)
    sources={'pP':(ptrain,'pP'),'MOVE_U2':(qtrain,'q2'),'MOVE_U3':(qtrain,'q3'),'MRET':(mtrain,'mP')}
    current_keys={'pP':'pP','MOVE_U2':'q2','MOVE_U3':'q3','MRET':'mP'}
    for row in raw:
        known=row['provenance']['max_known_minute']
        assert known is None or known<=row['entry_minute']
        known=row['movement_provenance']['current_max_source_minute']
        assert known is None or known<row['entry_minute']
        for name in ('prior20_calendar_dates','prior5_calendar_dates'):
            assert all(day<row['session'] for day in row['movement_provenance'][name])
    current_result={k:{'entry_id':k,'block':n['block'],'session':n['session'],'entry_minute':n['entry_minute']} for k,n in native_map.items()}
    references=[];certs=[];native_delta=0.;scalar_delta=0.;score_delta=0.
    for block in split['blocks']:
        b=block['block'];test=[r for r in raw if r['session'] in block['test']]
        assert {r['entry_id'] for r in test}=={k for k,n in native_map.items() if n['block']==b}
        assert max(block['train'])<min(block['test']) and not set(block['train'])&set(block['test'])
        for head,path in model_paths(b).items():
            model=read(path);ids=model['train_entry_ids']
            assert len(ids)==len(set(ids))==model['train_N'] and ids
            training=[lookup[k] for k in ids]
            assert all(r['session'] in block['train'] and r['session']<min(block['test']) for r in training)
            assert model['test_dates']==block['test'] and model['train_through']==max(block['train'])
            srckeys,scorekey=sources[head]
            saved=[r for r in srckeys if r['block']==b];saved_lookup={r['entry_id']:r for r in saved}
            assert len(saved_lookup)==len(saved)==len(ids) and set(saved_lookup)==set(ids),'REFERENCE_DENOMINATOR_CHANGED'
            reference=[saved_lookup[k][scorekey] for k in ids]
            assert all(math.isfinite(x) for x in reference)
            tp=infer(training,model);cp=infer(test,model)
            td=max(abs(x-y) for x,y in zip(tp,reference));assert td<=1e-12,(head,b,'TRAIN_DELTA',td)
            cd=0.;sd=0.;rank_mismatch=0
            for row,value in zip(test,cp):
                key=row['entry_id'];savedrow=mcurrent_map[key] if head=='MRET' else current_map[key]
                delta=abs(value-savedrow[current_keys[head]]);cd=max(cd,delta)
                scalar=scalar_infer(row,model);sd=max(sd,abs(value-scalar))
                assert delta<=1e-12 and abs(value-scalar)<=1e-12
                state=rank(value,reference)
                other=rank(scalar,reference)
                if state['rank_numerator']!=other['rank_numerator']:rank_mismatch+=1
                current_result[key][head]=state|{'model_sha256':sha(path),'reference_sha256':hashlib.sha256(json.dumps(reference,separators=(',',':')).encode()).hexdigest()}
            assert rank_mismatch==0,(head,b,'SCALAR_RANK_MISMATCH',rank_mismatch)
            refrows=[{'entry_id':r['entry_id'],'session':r['session'],'score':s} for r,s in zip(training,reference)]
            references.append({'head':head,'block':b,'model_sha256':sha(path),'train_identity_order':ids,'train_identity_sha256':hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest(),'ordered_reference':refrows,'reference_N':len(refrows),'scores':reference})
            certs.append({'head':head,'block':b,'model_sha256':sha(path),'reference_N':len(ids),'training_ordered_unique':True,'completed_past_only':True,'test_current_identity_N':0,'finite_only':True,'saved_reference_reinference_max_delta':td,'saved_current_reinference_max_delta':cd,'canonical_vs_scalar_max_delta':sd,'rank_mismatch_N':rank_mismatch,'denominator_changes':0})
            scalar_delta=max(scalar_delta,sd);score_delta=max(score_delta,td,cd)
        # Frozen native prediction is checked separately; auxiliary heads never replace ML.
        for h in (2,3,5):
            path=INPUT/'v5_source/capital_staircase_v4_private/models'/f'H{h}_BLOCK_{b:02d}.json';model=read(path)
            for row,value in zip(test,infer(test,model)):
                n=native_map[row['entry_id']]
                assert {k:row['numeric'][k] for k in model['preprocessing']['numeric_fields']}==n['numeric']
                assert row['categorical']==n['categorical']
                for key in ('entry_minute','entry_timestamp','raw_reference','session','symbol'):assert row[key]==n[key]
                delta=abs(value-n[f'p{h}']);native_delta=max(native_delta,delta);assert delta<=1e-12
    result_rows=[current_result[k] for k in native_map]
    assert all(all(h in row for h in HEADS) for row in result_rows)
    gzsave(out/'CURRENT_FOUR_HEAD_INTELLIGENCE.jsonl.gz',result_rows)
    save(out/'TRAINING_REFERENCE_POPULATIONS.json',references)
    save(out/'SCORE_REFERENCE_CERTIFICATION.json',{'status':'PASS','current_native_N':1039,'current_four_head_available_N':1039,'head_block_N':32,'heads':list(HEADS),'saved_score_causal_reinference_max_delta':score_delta,'canonical_scalar_max_delta':scalar_delta,'native_H2_H3_H5_causal_reinference_max_delta':native_delta,'score_tolerance':1e-12,'current_missing_N':0,'current_nonfinite_N':0,'duplicate_ID_N':0,'train_denominator_changes':0,'past_source_boundary_pass':True,'new_fit':0,'score_pnl_joins':0,'replays':0,'model_inference_certification_invocations':1,'blocks':certs,'current_intelligence_sha256':sha(out/'CURRENT_FOUR_HEAD_INTELLIGENCE.jsonl.gz'),'training_reference_sha256':sha(out/'TRAINING_REFERENCE_POPULATIONS.json')})
    print(json.dumps({'status':'PASS','current_native_N':1039,'head_block_N':32,'max_delta':score_delta,'native_delta':native_delta,'scalar_delta':scalar_delta}))

if __name__=='__main__':certify()
