"""Standalone structural audit after a baseline integrity stop.

No trainer/evaluator/metric imports, optimizer calls or outcome performance
calculations. Independently reconstructs source labels, mask, matrices,
coefficient snapshots and OOF probabilities. Baseline failure remains a failure.
"""
import ast
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT.parent/'quality_work'
INPUTS=WORK/'inputs'
PRIVATE=WORK/'private'
OUT=ROOT/'docs/evidence/capital-quality-anti-weak-medium-v1-20261005'

def load(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt')]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')

def valid(z):
    if not z.get('lineage'):return False
    try:
        v=[Decimal(str(z[k])) for k in ['O','H','L','C','Vo','Va']]
        return all(x.is_finite() and x>0 for x in v) and v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1]
    except (KeyError,TypeError,ValueError):return False

def matrix(rr,prep):
    f=prep['numeric_fields'];c=prep['categorical_fields']
    raw=np.asarray([[np.nan if r['numeric'][k] is None else float(r['numeric'][k]) for k in f] for r in rr])
    assert not np.isinf(raw).any()
    x=np.concatenate([np.where(np.isnan(raw),0,raw),np.isnan(raw).astype(float)],axis=1)
    x=(x-np.asarray(prep['numeric_mean']))/np.asarray(prep['numeric_scale'])
    cols=[]
    for k in c:
        voc=prep['categorical_train_vocab'][k]
        for value in voc:
            cols.append([float((r['categorical'][k] if r['categorical'][k] in voc else '__UNKNOWN__')==value) for r in rr])
    return np.column_stack([x,np.asarray(cols).T])

def independently_derived_prep(rr,fields,cats):
    a=np.asarray([[np.nan if r['numeric'][k] is None else float(r['numeric'][k]) for k in fields] for r in rr])
    a=np.column_stack([np.where(np.isnan(a),0,a),np.isnan(a).astype(float)])
    scale=a.std(axis=0);scale[scale==0]=1
    return {'numeric_fields':fields,'categorical_fields':cats,'numeric_mean':a.mean(axis=0).tolist(),
        'numeric_scale':scale.tolist(),'categorical_train_vocab':{k:sorted({r['categorical'][k] or '__UNKNOWN__' for r in rr}|{'__UNKNOWN__'}) for k in cats},
        'constant_missing':0,'missing_indicators':True,'training_only':True}

def same_float(a,b):
    if isinstance(a,dict):
        assert set(a)==set(b)
        return max([same_float(a[k],b[k]) for k in a] or [0.])
    if isinstance(a,list):
        assert len(a)==len(b)
        return max([same_float(x,y) for x,y in zip(a,b)] or [0.])
    if isinstance(a,(int,float)) and not isinstance(a,bool):
        diff=abs(float(a)-float(b));assert diff<=1e-12,(a,b,diff);return diff
    assert a==b,(a,b);return 0.

def main():
    pre=load(OUT/'FEATURE_MODEL_SPLIT_PRECOMMIT.json');claim=load(OUT/'FIT_CLAIM.json')
    rec=load(OUT/'INPUT_BYTE_RECOVERY.json');fit=load(OUT/'FITS_COMPLETE.json')
    for source in rec['checks']:assert sha(INPUTS/source['input_relative'])==source['sha256']
    assert all(sha(Path(__file__).parent/n)==h for n,h in claim['code_sha256'].items())
    assert sha(OUT/'FEATURE_MODEL_SPLIT_PRECOMMIT.json')==claim['design_sha256']
    runtime=rows(INPUTS/'RUNTIME_CAUSAL.jsonl.gz');rm={r['entry_id']:r for r in runtime}
    book={r['entry_id']:r for r in rows(INPUTS/'MARKET_TEACHER_BOOK.jsonl.gz')}
    original_teacher={r['entry_id']:r for r in rows(INPUTS/'TEACHERS_EVALUATION.jsonl.gz')}
    frozen={r['watch_key']:r for r in rows(INPUTS/'FROZEN_ENTRY.jsonl.gz') if r['entry_status']=='FIRST_ENTRY'}
    teachers={r['entry_id']:r for r in rows(PRIVATE/'QUALITY_TEACHERS_EVAL.jsonl.gz')}
    support={r['entry_id']:r for r in rows(INPUTS/'TEACHER_SUPPORT_LEDGER.jsonl.gz')}
    assert len(rm)==1600 and set(rm)==set(book)==set(original_teacher)==set(frozen)==set(teachers)==set(support)
    labels={};max_float=0.
    for k,r in rm.items():
        f=frozen[k];t=teachers[k];b=book[k];s=b.get('source') or {}
        assert (r['session'],r['symbol'],r['entry_timestamp'],r['entry_minute'])==(f['session'],f['symbol'],f['fill_timestamp'],f['fill_minute'])
        assert b['entry_actual_source']['O']==r['raw_reference']
        assert abs(Decimal(r['raw_reference'])*Decimal('1.0005')-Decimal(str(f['fill_price'])))<=Decimal('1e-8')
        complete=bool(b['capture_complete'] and s.get('date_scope_complete') and s.get('terminal_pagination_proven'))
        future=[z for z in b['market'] if valid(z) and r['entry_minute']<z['minute']<920]
        p=max(Decimal(z['H']) for z in future)/Decimal(r['raw_reference'])-1 if future else Decimal(0) if complete else None
        accepted=complete and r['entry_minute']<920
        labels[k]={f'U{u}':int(p>=Decimal(u)/100) if accepted else None for u in [2,3,5,10]}
        for name,y in labels[k].items():assert t[name]==y
        assert t['WEAK2']==1-t['U2'] if accepted else t['WEAK2'] is None
        if p is not None:
            max_float=max(max_float,abs(float(p)-t['potential_return']),abs(float(p)-original_teacher[k]['potential_return']))
            assert max_float<=1e-12
        assert labels[k]['U5']==support[k]['label_U5'] and labels[k]['U10']==support[k]['label_U10']
        assert t['capture_complete']==complete
        assert set(r['numeric'])==set(pre['feature_numeric_order']) and set(r['categorical'])==set(pre['feature_categorical_order'])
        assert not any(x.lower() in name.lower() for name in list(r['numeric'])+list(r['categorical']) for x in ['future','high','pnl','realized','release','exit','session','symbol','date','pP'])
        cp=r['provenance'];mp=r['movement_provenance']
        assert cp['max_known_minute'] is None or cp['max_known_minute']<=r['entry_minute']
        assert mp['current_max_source_minute'] is None or mp['current_max_source_minute']<r['entry_minute']
        assert all(d<r['session'] for d in mp['prior20_calendar_dates']+mp['prior5_calendar_dates'])
    split=pre['split'];days=sorted({r['session'] for r in runtime})
    assert split==load(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json')
    assert split['all58']==days and split['warmup20']==days[:20] and split['OOF38']==days[20:] and len(split['blocks'])==8
    current=rows(INPUTS/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz');move={r['entry_id']:r for r in rows(INPUTS/'MOVE_P5_SCORE_STREAM.jsonl.gz')}
    common=rows(PRIVATE/'COMMON_SAVED_SCORES.jsonl.gz');mask=rows(INPUTS/'COMMON_EVAL_MASK.jsonl.gz')
    intended=[r['entry_id'] for r in current if r['entry_minute']<920 and labels[r['entry_id']]['U5'] is not None and labels[r['entry_id']]['U10'] is not None]
    assert intended==[r['entry_id'] for r in common] and set(intended)=={r['entry_id'] for r in mask if r['included']} and len(intended)==1028
    assert hashlib.sha256(('\n'.join(intended)+'\n').encode()).hexdigest()==load(OUT/'TEACHER_MASK_FREEZE.json')['ordered_identity_sha256']
    buckets=Counter(teachers[k]['bucket'] for k in intended)
    assert buckets=={'Q0_WEAK':596,'Q1_LOW':135,'Q2_MEDIUM':127,'Q3_BIG':103,'Q4_MEGA':67}
    decile={}
    for bl in range(1,9):
        rr=sorted([r for r in common if r['block']==bl],key=lambda r:(-r['pP'],r['entry_timestamp'],r['symbol'],r['entry_id']))
        for j,r in enumerate(rr):decile[r['entry_id']]=min(9,10*j//len(rr))
    assert decile=={r['entry_id']:r['pP_decile'] for r in rows(PRIVATE/'P_P_DECILES_OUTCOME_FREE.jsonl.gz')}
    predictions=rows(PRIVATE/'NEW_HEAD_OOF_PREDICTIONS.jsonl.gz')
    pm={(r['head'],r['entry_id']):r for r in predictions}
    assert len(pm)==len(predictions)==2078
    model_checks=[]
    for item in claim['claims']:
        head,block=item['head'],item['block'];name=f'{head}_BLOCK_{block:02d}'
        artifact=load(PRIVATE/'models'/(name+'.json'));state=np.load(PRIVATE/'models'/(name+'_FITTED_STATE.npz'),allow_pickle=False)
        done=load(PRIVATE/'fit_claims'/(name+'_COMPLETE.json'));started=load(PRIVATE/'fit_claims'/(name+'_STARTED.json'))
        assert started['attempt']==done['attempts']==artifact['fit_attempt']==1
        assert done['artifact_sha256']==sha(PRIVATE/'models'/(name+'.json')) and done['state_sha256']==sha(PRIVATE/'models'/(name+'_FITTED_STATE.npz'))
        assert done['prediction_sha256']==sha(PRIVATE/'predictions'/(name+'.jsonl.gz'))
        assert artifact['ConvergenceWarning_N']==done['ConvergenceWarning_N']==artifact['heldout_teacher_payload_reads']==0
        train=[rm[k] for k in artifact['train_entry_ids']];test=[r for r in runtime if r['session'] in split['blocks'][block-1]['test']]
        assert max(r['session'] for r in train)<min(r['session'] for r in test)
        original=load(INPUTS/'models'/f'MOVE_P_BLOCK_{block:02d}.json')
        assert artifact['train_entry_ids']==original['train_entry_ids'] and artifact['test_dates']==original['test_dates']
        training=rows(PRIVATE/'training'/f'BLOCK_{block:02d}_PAST_ONLY.jsonl.gz')
        assert [r['entry_id'] for r in training]==artifact['train_entry_ids']
        assert all(r['session'] in split['blocks'][block-1]['train'] and set(r)=={'entry_id','session','U2','U3'} for r in training)
        assert all(r['U2']==labels[r['entry_id']]['U2'] and r['U3']==labels[r['entry_id']]['U3'] for r in training)
        prep=independently_derived_prep(train,pre['feature_numeric_order'],pre['feature_categorical_order'])
        max_float=max(max_float,same_float(prep,artifact['preprocessing']),same_float(prep,original['preprocessing']))
        max_float=max(max_float,same_float(artifact['coef'],state['coef'][0].tolist()),same_float(artifact['intercept'],float(state['intercept'][0])))
        assert np.array_equal(state['classes'],[0,1]) and json.loads(str(state['preprocessing_json']))==prep
        assert json.loads(str(state['parameters_json']))==artifact['parameters']==pre['parameters']
        x=matrix(test,prep);prob=np.exp(-np.logaddexp(0,-(x@state['coef'][0]+state['intercept'][0])))
        delta=max(abs(float(p)-pm[(head,r['entry_id'])]['probability']) for r,p in zip(test,prob));assert delta<=1e-12
        max_float=max(max_float,delta)
        assert artifact['train_positive_N']==sum(labels[r['entry_id']][item['target']] for r in train)
        model_checks.append({'head':head,'block':block,'preprocessing_mismatch_N':0,'coef_intercept_snapshot_mismatch_N':0,'OOF_max_abs_difference':delta,'audit_refits':0})
    assert len(model_checks)==16 and len(list((PRIVATE/'models').glob('MOVE_U*_BLOCK_*.json')))==16
    assert fit['ConvergenceWarning_N']==0 and fit['fit_count']['total']==16
    imported=[]
    for n in ast.walk(ast.parse(Path(__file__).read_text())):
        if isinstance(n,ast.Import):imported += [a.name for a in n.names]
        elif isinstance(n,ast.ImportFrom):imported.append(n.module or '')
    assert not any(x in ['train_heads','evaluate','metrics','movement_preprocessing','control','sklearn'] for x in imported)
    baseline_freeze=load(OUT/'ZERO_FIT_BASELINE_FREEZE.json');actual=sha(OUT/'ZERO_FIT_BASELINE.json')
    parse_error=None
    try:load(OUT/'ZERO_FIT_BASELINE.json')
    except json.JSONDecodeError as exc:parse_error=str(exc)
    assert actual!=baseline_freeze['baseline_sha256'] and parse_error is not None
    assert claim['baseline_sha256']==actual
    checks=[
        ('identity',True),('mask',True),('train<test',True),('test label leakage0',True),
        ('future High in X=0',True),('PnL in X=0',True),('release in X=0',True),('future bar in X=0',True),
        ('prefix cutoff',True),('prior date',True),('Movement boundary',True),('identity/date feature0',True),
        ('U2/Weak complement',True),('U3 exact',True),('unknown impute0',True),('pP not in X',True),
        ('feature manifest exact',True),('preprocessing exact',True),('model config exact',True),
        ('search0',True),('within-block refit0',True),('split exact',True),('convergence warning0',True),
        ('hash',False),('OOF duplicates0',True),('bootstrap session',None),
        ('conditional decile outcome-free',True),('Safety false',True),('v8 research result read=0',True),
        ('v8R1 research result read=0',True),('Main B1/B2 outcome imported=0',True)]
    assert all(v is False for v in pre['Safety'].values())
    firewall=load(OUT/'ALLOCATION_FIREWALL.json')
    assert firewall['v8_research_result_read']==firewall['v8r1_research_result_read']==firewall['main_b1_b2_outcome_imported']==firewall['quality_results_exported_to_main']==0
    report={'exact_jst':now(),'status':'INTEGRITY_CONTRACT_FAIL_CONFIRMED','trainer_evaluator_metric_imports':0,
        'new_fits':0,'audit_refits':0,'bootstrap_runs':0,'head_quality_performance_evaluations':0,
        'labels_mask_split_preprocessing_coef_snapshot_OOF_mismatch_N':0,'max_abs_float_difference':max_float,
        'float_tolerance':1e-12,'model_checks':model_checks,
        'baseline_integrity_root_failure_N':1,'final_mismatch_N':1,
        'baseline':{'expected_Q4_sha256':baseline_freeze['baseline_sha256'],'actual_sha256':actual,
            'fit_claim_sha256':claim['baseline_sha256'],'parse_error':parse_error,'original_preserved':True,
            'full_frozen_original_bytes_recovered':False,'fit_claim_validated_current_bytes_but_omitted_Q4_equality_check':True},
        'canaries':[{'number':i,'name':name,'status':'PASS' if ok is True else 'FAIL' if ok is False else 'NOT_RUN_CONTRACT_STOP'} for i,(name,ok) in enumerate(checks,1)],
        'metric_audit_status':'NOT_RUN_CONTRACT_STOP: AUC/PR/TopK/conditional/same-session/bootstrap/status promotion blocked',
        'qualityStatus':'QUALITY_CONTRACT_FAIL','selectedAuxiliaryHeads':[],
        'selectedBigWinnerRank':'EXISTING_MOVE_P5','CapitalReplay':0,'MAX3Replay':0,
        'convergence_warning_N':0,'completed_fits_preserved_for_future_authorized_reuse':16,
        'source_actual_arrival_limitation':'Inherited bar-end assumption, actual arrival unknown',
        'firewall_research_information_import_export':0,'Safety':pre['Safety']}
    save(OUT/'INDEPENDENT_AUDIT.json',report)
    print(json.dumps({'status':report['status'],'structural_mismatch':0,'baseline_failure':1,'max_float':max_float,'fits':16,'audit_refits':0}))

if __name__=='__main__':main()
