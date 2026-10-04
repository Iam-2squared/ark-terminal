"""Independent saved-state audit and masked OOF join. No optimizer/trainer imports."""
import ast
import numpy as np
from independent_io import *

def valid(z):
    if not z.get('lineage'):return False
    try:
        v=[Decimal(str(z[k])) for k in ['O','H','L','C','Vo','Va']]
        return all(x.is_finite() and x>0 for x in v) and v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1]
    except (KeyError,TypeError,ValueError):return False

def prep_from_training(rr,fields,cats):
    a=np.asarray([[np.nan if r['numeric'][k] is None else float(r['numeric'][k]) for k in fields] for r in rr])
    a=np.column_stack([np.where(np.isnan(a),0,a),np.isnan(a).astype(float)])
    scale=a.std(axis=0);scale[scale==0]=1
    return {'numeric_fields':fields,'categorical_fields':cats,'numeric_mean':a.mean(axis=0).tolist(),
        'numeric_scale':scale.tolist(),'categorical_train_vocab':{k:sorted({r['categorical'][k] or '__UNKNOWN__' for r in rr}|{'__UNKNOWN__'}) for k in cats},
        'constant_missing':0,'missing_indicators':True,'training_only':True}

def transform(rr,p):
    a=np.asarray([[np.nan if r['numeric'][k] is None else float(r['numeric'][k]) for k in p['numeric_fields']] for r in rr])
    assert not np.isinf(a).any()
    x=np.column_stack([np.where(np.isnan(a),0,a),np.isnan(a).astype(float)])
    x=(x-np.asarray(p['numeric_mean']))/np.asarray(p['numeric_scale'])
    columns=[]
    for k in p['categorical_fields']:
        voc=p['categorical_train_vocab'][k]
        for v in voc:columns.append([float((r['categorical'][k] if r['categorical'][k] in voc else '__UNKNOWN__')==v) for r in rr])
    return np.column_stack([x,np.asarray(columns).T])

def main():
    claimed('MODEL_ARTIFACT_AUDIT_EXECUTION_CLAIM',[OUT/'MODEL_ARTIFACT_AUDIT.json',PRIVATE/'QUALITY_COMMON_EVAL_ROWS_V1R1.jsonl.gz'])
    cert=load(OUT/'BASELINE_INDEPENDENT_CERTIFICATION.json');assert cert['status']=='PASS' and cert['public_compact_mismatch_N']==0
    assert any(str((OUT/'R4_BASELINE_INDEPENDENT_CERTIFICATION.json').relative_to(ROOT)) in p['paths'] for p in load(WORK/'publications.json'))
    auth=load(OUT/'PRIVATE_PACK_AUTHENTICATION.json');assert auth['mismatch_N']==0
    for x in auth['transport_members']:assert sha(OLD_WORK/x['path'])==x['sha256']
    pre=load(OLD/'FEATURE_MODEL_SPLIT_PRECOMMIT.json');claim=load(OLD/'FIT_CLAIM.json');fit=load(OLD/'FITS_COMPLETE.json')
    split=pre['split'];inp=OLD_WORK/'inputs';pri=OLD_WORK/'private'
    runtime=rows(inp/'RUNTIME_CAUSAL.jsonl.gz');rm={r['entry_id']:r for r in runtime}
    book={r['entry_id']:r for r in rows(inp/'MARKET_TEACHER_BOOK.jsonl.gz')}
    frozen={r['watch_key']:r for r in rows(inp/'FROZEN_ENTRY.jsonl.gz') if r['entry_status']=='FIRST_ENTRY'}
    teachers={r['entry_id']:r for r in rows(pri/'QUALITY_TEACHERS_EVAL.jsonl.gz')}
    original_teacher={r['entry_id']:r for r in rows(inp/'TEACHERS_EVALUATION.jsonl.gz')}
    support={r['entry_id']:r for r in rows(inp/'TEACHER_SUPPORT_LEDGER.jsonl.gz')}
    assert len(rm)==1600 and set(rm)==set(book)==set(frozen)==set(teachers)==set(original_teacher)==set(support)
    labels={};maxdiff=0.
    for eid,r in rm.items():
        t=teachers[eid];b=book[eid];f=frozen[eid];s=b.get('source') or {}
        assert (r['session'],r['symbol'],r['entry_timestamp'],r['entry_minute'])==(f['session'],f['symbol'],f['fill_timestamp'],f['fill_minute'])
        assert b['entry_actual_source']['O']==r['raw_reference']
        assert abs(Decimal(r['raw_reference'])*Decimal('1.0005')-Decimal(str(f['fill_price'])))<=Decimal('1e-8')
        complete=bool(b['capture_complete'] and s.get('date_scope_complete') and s.get('terminal_pagination_proven'))
        future=[z for z in b['market'] if valid(z) and r['entry_minute']<z['minute']<920]
        p=max(Decimal(z['H']) for z in future)/Decimal(r['raw_reference'])-1 if future else Decimal(0) if complete else None
        accepted=complete and r['entry_minute']<920
        labels[eid]={f'U{u}':int(p>=Decimal(u)/100) if accepted else None for u in [2,3,5,10]}
        assert all(t[k]==v for k,v in labels[eid].items()) and t['WEAK2']==(1-t['U2'] if accepted else None)
        bucket='Q4_MEGA' if t['U10'] else 'Q3_BIG' if t['U5'] else 'Q2_MEDIUM' if t['U3'] else 'Q1_LOW' if t['U2'] else 'Q0_WEAK' if accepted else None
        assert t['bucket']==bucket
        if p is not None:
            maxdiff=max(maxdiff,abs(float(p)-t['potential_return']),abs(float(p)-original_teacher[eid]['potential_return']))
        assert maxdiff<=1e-12 and t['capture_complete']==complete
        assert labels[eid]['U5']==support[eid]['label_U5'] and labels[eid]['U10']==support[eid]['label_U10']
        assert set(r['numeric'])==set(pre['feature_numeric_order']) and len(r['numeric'])==46
        assert set(r['categorical'])==set(pre['feature_categorical_order']) and len(r['categorical'])==7
        for name in list(r['numeric'])+list(r['categorical']):
            assert not any(x in name.lower() for x in ['future','high','pnl','realized','release','exit','session','symbol','date'])
            assert name!='pP'
        cp=r['provenance'];mp=r['movement_provenance']
        assert cp['max_known_minute'] is None or cp['max_known_minute']<=r['entry_minute']
        assert mp['current_max_source_minute'] is None or mp['current_max_source_minute']<r['entry_minute']
        assert all(d<r['session'] for d in mp['prior20_calendar_dates']+mp['prior5_calendar_dates'])
    days=sorted({r['session'] for r in runtime})
    assert split==load(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json')
    assert split['all58']==days and split['warmup20']==days[:20] and split['OOF38']==days[20:] and len(split['blocks'])==8
    predictions=rows(pri/'NEW_HEAD_OOF_PREDICTIONS.jsonl.gz')
    pm={(r['head'],r['entry_id']):r for r in predictions}
    assert len(pm)==len(predictions)==2078
    for p in predictions:assert math.isfinite(p['probability']) and 0<=p['probability']<=1
    assert Counter(p['head'] for p in predictions)=={'MOVE_U2':1039,'MOVE_U3':1039}
    checks=[]
    for c in claim['claims']:
        h,bl=c['head'],c['block'];name=f'{h}_BLOCK_{bl:02d}'
        artifact=load(pri/'models'/(name+'.json'));state=np.load(pri/'models'/(name+'_FITTED_STATE.npz'),allow_pickle=False)
        done=load(pri/'fit_claims'/(name+'_COMPLETE.json'));start=load(pri/'fit_claims'/(name+'_STARTED.json'))
        assert done==next(x for x in fit['fit_ledger'] if x['head']==h and x['block']==bl)
        assert start['attempt']==done['attempts']==artifact['fit_attempt']==1
        assert done['artifact_sha256']==sha(pri/'models'/(name+'.json')) and done['state_sha256']==sha(pri/'models'/(name+'_FITTED_STATE.npz'))
        assert done['prediction_sha256']==sha(pri/'predictions'/(name+'.jsonl.gz'))
        assert done['ConvergenceWarning_N']==artifact['ConvergenceWarning_N']==artifact['heldout_teacher_payload_reads']==0
        train=[rm[eid] for eid in artifact['train_entry_ids']];test=[r for r in runtime if r['session'] in split['blocks'][bl-1]['test']]
        assert len(train)==artifact['train_N']==done['train_N'] and len(test)==done['test_N']
        assert max(r['session'] for r in train)<min(r['session'] for r in test)
        original=load(inp/'models'/f'MOVE_P_BLOCK_{bl:02d}.json')
        assert artifact['train_entry_ids']==original['train_entry_ids'] and artifact['test_dates']==original['test_dates']==split['blocks'][bl-1]['test']
        training=rows(pri/'training'/f'BLOCK_{bl:02d}_PAST_ONLY.jsonl.gz')
        assert sha(pri/'training'/f'BLOCK_{bl:02d}_PAST_ONLY.jsonl.gz')==c['training_payload_sha256']==start['training_sha256']
        assert [r['entry_id'] for r in training]==artifact['train_entry_ids']
        assert all(set(r)=={'entry_id','session','U2','U3'} and r['session'] in split['blocks'][bl-1]['train'] for r in training)
        assert all(r['U2']==labels[r['entry_id']]['U2'] and r['U3']==labels[r['entry_id']]['U3'] for r in training)
        prep=prep_from_training(train,pre['feature_numeric_order'],pre['feature_categorical_order'])
        for other in [artifact['preprocessing'],original['preprocessing'],json.loads(str(state['preprocessing_json']))]:
            err,d=difference(prep,other);assert not err;maxdiff=max(maxdiff,d)
        assert json.loads(str(state['parameters_json']))==artifact['parameters']==pre['parameters']
        assert np.array_equal(state['classes'],[0,1]) and int(state['iterations'][0])==artifact['iterations']==done['iterations']
        for a,b in [(artifact['coef'],state['coef'][0].tolist()),(artifact['intercept'],float(state['intercept'][0]))]:
            err,d=difference(a,b);assert not err;maxdiff=max(maxdiff,d)
        x=transform(test,prep);prob=np.exp(-np.logaddexp(0,-(x@state['coef'][0]+state['intercept'][0])))
        shard=rows(pri/'predictions'/(name+'.jsonl.gz'));assert len(shard)==len(test)
        for r in shard:assert r==pm[(h,r['entry_id'])] and r['head']==h and r['block']==bl
        delta=max(abs(float(p)-pm[(h,r['entry_id'])]['probability']) for r,p in zip(test,prob));assert delta<=1e-12
        maxdiff=max(maxdiff,delta)
        assert artifact['train_positive_N']==done['train_positive_N']==sum(labels[r['entry_id']][c['target']] for r in train)
        checks.append({'head':h,'block':bl,'train_N':len(train),'test_N':len(test),'iterations':done['iterations'],
            'preprocessing_mismatch_N':0,'coef_intercept_state_mismatch_N':0,'prediction_shard_mismatch_N':0,
            'OOF_max_abs_difference':delta,'audit_refits':0,'optimizer_execution':0})
    data,dec=source_rows();common_ids={r['entry_id'] for r in data};mask=rows(inp/'COMMON_EVAL_MASK.jsonl.gz')
    join={}
    for h in ['MOVE_U2','MOVE_U3']:
        all_ids={p['entry_id'] for p in predictions if p['head']==h}
        assert common_ids<=all_ids and len(all_ids-common_ids)==11
        assert all_ids-common_ids=={r['entry_id'] for r in mask if not r['included']}
        join[h]={'OOF_N':1039,'common_present':1028,'extra':11,'missing':0,'original_artifact_rewritten':False}
    up={r['entry_id']:r for r in rows(inp/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')}
    mov={r['entry_id']:r for r in rows(inp/'MOVE_P5_SCORE_STREAM.jsonl.gz')}
    intended=[r['entry_id'] for r in up.values() if r['entry_minute']<920 and labels[r['entry_id']]['U5'] is not None and labels[r['entry_id']]['U10'] is not None]
    assert set(intended)==common_ids and len(intended)==1028
    assert hashlib.sha256(('\n'.join(intended)+'\n').encode()).hexdigest()==load(OLD/'TEACHER_MASK_FREEZE.json')['ordered_identity_sha256']
    for r in data:
        u=up[r['entry_id']];m=mov[r['entry_id']]
        assert r['CORE_H2']==u['p2'] and r['CORE_H3']==u['p3'] and r['pP']==m['pP']
        assert r['legacy_ML']==u['ML'] and all(r[f'legacy_m{v}']==u[f'm{v}'] for v in [2,3,5])
        for h in ['MOVE_U2','MOVE_U3']:
            p=pm[(h,r['entry_id'])];assert p['session']==r['session'] and p['block']==r['block'];r[h]=p['probability']
    assert len(checks)==16 and fit['ConvergenceWarning_N']==0
    compressed=compress(PRIVATE/'QUALITY_COMMON_EVAL_ROWS_V1R1.jsonl.gz',data,True)
    imports=[]
    for n in ast.walk(ast.parse(Path(__file__).read_text())):
        if isinstance(n,ast.Import):imports += [a.name for a in n.names]
        if isinstance(n,ast.ImportFrom):imports.append(n.module)
    assert not any(x in ['metrics','evaluate','train_heads','movement_preprocessing','control','sklearn'] for x in imports)
    report={'exact_jst':now(),'status':'PASS','N':1028,'newFits':0,'refits':0,'auditRefits':0,'optimizer_execution':0,
        'trainer_evaluator_imports':0,'model_checks':checks,'join':join,'label_mask_split_model_OOF_mismatch_N':0,
        'max_abs_float_difference':maxdiff,'float_tolerance':1e-12,'ConvergenceWarning_N':0,
        'joined_artifact':{'path':'private/QUALITY_COMMON_EVAL_ROWS_V1R1.jsonl.gz',**compressed},
        'new_head_performance_evaluations':0,'source_arrival_limitation':'Inherited bar-end assumption; actual arrival unknown'}
    save(OUT/'MODEL_ARTIFACT_AUDIT.json',report)
    save(OUT/'NEW_HEAD_JOIN_AUDIT.json',{'exact_jst':now(),'status':'PASS','heads':join,'N':1028,
        'mask_sha256':sha(inp/'COMMON_EVAL_MASK.jsonl.gz'),'joined_artifact':report['joined_artifact'],'extra_mask_only':True})
    checkpoint('R5_NEW_HEAD_JOIN_AND_MODEL_ARTIFACT_AUDIT',report,'R6 fixed performance package precommit/claims; then one primary evaluation without fitting')
    print(json.dumps({'status':'PASS','structural_mismatch_N':0,'max_float':maxdiff,'joins':join,'newFits':0}))

if __name__=='__main__':main()
