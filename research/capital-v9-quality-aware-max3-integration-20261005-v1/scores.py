"""Frozen inference only. Pressure-table construction receives no teacher fields."""
from control import *
import numpy as np
def predict(rr,model):
    p=model['preprocessing'];nf=p['numeric_fields'];cf=p['categorical_fields']
    a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in nf] for r in rr],dtype=np.float64)
    assert not np.isinf(a).any()
    x=(np.column_stack([np.nan_to_num(a,nan=0),np.isnan(a).astype(float)])-np.array(p['numeric_mean'],dtype=np.float64))/np.array(p['numeric_scale'],dtype=np.float64)
    col=[]
    for k in cf:
        voc=p['categorical_train_vocab'][k];vv=[r['categorical'][k] if r['categorical'][k] in voc else '__UNKNOWN__' for r in rr]
        col.extend([[float(v==c) for v in vv] for c in voc])
    xx=np.column_stack([x,np.array(col).T]);logit=xx@np.array(model['coef'],dtype=np.float64)+model['intercept']
    return np.exp(-np.logaddexp(0,-logit)).tolist()
def raw():
    rr=rows(QUALITY/'inputs/RUNTIME_CAUSAL.jsonl.gz')
    # Scores use only the frozen feature dictionaries, never execution/teachers.
    return {r['entry_id']:{'numeric':r['numeric'],'categorical':r['categorical']} for r in rr},rr
def models(b):return [read(QUALITY/f'private/models/MOVE_U{h}_BLOCK_{b:02}.json') for h in (2,3)]
def current():
    assert read(OUT/'PRIVATE_PACK_CROSS_AUTHORITY_AUDIT.json')['mismatch_N']==0
    rm,rr=raw();split=read(SPLIT);saved={(r['head'],r['entry_id']):r for r in rows(QUALITY/'private/NEW_HEAD_OOF_PREDICTIONS.jsonl.gz')}
    runtime=rows(MAIN/'private/RANK_NATIVE_RUNTIME.jsonl.gz');mask={r['entry_id'] for r in rows(MAIN/'private/COMMON_EVAL_MASK.jsonl.gz') if r['included']}
    assert len(runtime)==1039 and len(mask)==1028 and len(saved)==2078
    values={};modelchecks=[];maxdelta=0.;common_delta=0.;ppdelta=0.
    for block in split['blocks']:
        b=block['block'];mm=models(b);pm=read(MAIN/f'inputs/movement/models/MOVE_P_BLOCK_{b:02}.json')
        test=[r for r in rr if r['session'] in block['test']];xs=[rm[r['entry_id']] for r in test]
        for h,m in zip((2,3),mm):
            name=f'MOVE_U{h}_BLOCK_{b:02}';state=np.load(QUALITY/f'private/models/{name}_FITTED_STATE.npz',allow_pickle=False);done=read(QUALITY/f'private/fit_claims/{name}_COMPLETE.json')
            assert np.array_equal(state['coef'][0],m['coef']) and state['intercept'][0]==m['intercept']
            assert json.loads(str(state['preprocessing_json']))==m['preprocessing']==pm['preprocessing']
            assert json.loads(str(state['parameters_json']))==m['parameters'] and np.array_equal(state['classes'],[0,1])
            assert done['artifact_sha256']==sha(QUALITY/f'private/models/{name}.json') and done['state_sha256']==sha(QUALITY/f'private/models/{name}_FITTED_STATE.npz')
            assert m['train_entry_ids']==pm['train_entry_ids'] and m['test_dates']==pm['test_dates']==block['test']
            assert m['fit_attempt']==done['attempts']==1 and m['ConvergenceWarning_N']==m['heldout_teacher_payload_reads']==0
            assert len(m['preprocessing']['numeric_fields'])==46 and len(m['preprocessing']['categorical_fields'])==7
            prob=predict(xs,m);delta=0.
            for r,q in zip(test,prob):
                eid=r['entry_id'];d=abs(q-saved[f'MOVE_U{h}',eid]['probability']);delta=max(delta,d);maxdelta=max(maxdelta,d)
                if eid in mask:common_delta=max(common_delta,d)
                values.setdefault(eid,{})[f'q{h}']=q
            assert delta<=1e-12
            modelchecks.append({'head':f'MOVE_U{h}','block':b,'model_sha256':sha(QUALITY/f'private/models/{name}.json'),'fitted_state_sha256':sha(QUALITY/f'private/models/{name}_FITTED_STATE.npz'),'preprocessing_identity':'EXACT','saved_prediction_max_abs_delta':delta,'OOF_N':len(test),'newFits':0})
        expected=[r for r in runtime if r['block']==b];pp=predict([rm[r['entry_id']] for r in expected],pm);ppdelta=max(ppdelta,max(abs(q-r['pP']) for q,r in zip(pp,expected)))
    assert ppdelta<=1e-12 and set(values)==set(r['entry_id'] for r in runtime)
    for r in runtime:r.update(values[r['entry_id']])
    gzsave(PRIVATE/'CURRENT_CAUSAL_QUALITY_RUNTIME.jsonl.gz',runtime)
    save(OUT/'QUALITY_SCORE_RUNTIME_RECONSTRUCTION.json',{'exact_jst':now(),'status':'PASS','current_OOF_N':1039,'common_N':1028,'head_model_N':16,'models':modelchecks,'max_saved_OOF_abs_delta':maxdelta,'common_max_saved_OOF_abs_delta':common_delta,'pP_reconstruction_max_abs_delta':ppdelta,'mismatch_N':0,'runtime_sha256':sha(PRIVATE/'CURRENT_CAUSAL_QUALITY_RUNTIME.jsonl.gz'),'current_score_input':'causal frozen 46 numeric +7 categorical; no saved prediction injection','saved_prediction_use':'audit only','probability_claim':False,'fits':0,'Safety':SAFETY})
    checkpoint('V3_QUALITY_SCORE_RUNTIME_RECONSTRUCTION',{'status':'PASS','models':16,'OOF_N':1039,'common_N':1028,'max_abs_delta':maxdelta,'mismatch_N':0},'Build training-only raw q2/q3 resubstitution table')
def training():
    rm,rawrows=raw();rawmeta={r['entry_id']:r for r in rawrows};mapped=rows(MAIN/'private/TRAIN_MAPPED_SCORES.jsonl.gz');split=read(SPLIT);table=[];summary=[]
    fields=['entry_id','session','entry_minute','r','q2','q3','band','block']
    for block in split['blocks']:
        b=block['block'];mm=models(b);byid={r['entry_id']:r for r in mapped if r['block']==b};ids=mm[0]['train_entry_ids']
        assert mm[1]['train_entry_ids']==ids and set(byid)==set(ids)
        rr=[byid[e] for e in ids];assert all(r['session'] in block['train'] and r['session']<min(block['test']) for r in rr)
        q2,q3=[predict([rm[e] for e in ids],m) for m in mm]
        for r,a,z in zip(rr,q2,q3):
            assert rawmeta[r['entry_id']]['entry_minute']==r['entry_minute'] and r['r']==r['rank_units']/r['train_N']
            table.append({k:v for k,v in (r|{'q2':a,'q3':z}).items() if k in fields})
        summary.append({'block':b,'N':len(rr),'admitted_N':sum(r['band']!='P_BELOW' for r in rr),'training_session_N':len(block['train']),'completed_through':max(block['train']),'test_from':min(block['test'])})
    table.sort(key=lambda r:(r['block'],r['session'],r['entry_minute'],r['entry_id']))
    assert all(set(r)==set(fields) for r in table)
    gzsave(PRIVATE/'QUALITY_TRAIN_SCORE_TABLE.jsonl.gz',table)
    save(OUT/'TRAIN_QUALITY_SCORE_TABLE_FREEZE.json',{'exact_jst':now(),'status':'PASS','fields':fields,'N':len(table),'blocks':summary,'table_sha256':sha(PRIVATE/'QUALITY_TRAIN_SCORE_TABLE.jsonl.gz'),'score_semantics':'raw frozen block-model resubstitution, not OOF or calibrated probability','teacher_input_fields':[],'teacher_payload_files_opened':0,'fit_N':0,'r_exact':'same frozen rank_units/train_N; no rounding or remapping','Safety':SAFETY})
    checkpoint('V4_TRAIN_QUALITY_SCORE_TABLE_FREEZE',{'N':len(table),'teacher_input_fields':0,'newFits':0},'Freeze both dominance pressure tables and local monotonicity')
if __name__=='__main__':
    import sys
    {'current':current,'training':training}[sys.argv[1]]()
