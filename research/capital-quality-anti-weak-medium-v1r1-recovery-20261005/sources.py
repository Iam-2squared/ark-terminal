"""Read-only old source authentication. Never computes head performance or fits."""
import hashlib
import math
import zipfile
from collections import Counter
from control import *

EXPECTED = {
    'private/COMMON_SAVED_SCORES.jsonl.gz':'6d91302d8adeb4043c4c7072a16070da8610b341d88ae9d7ad67f53f5c028be1',
    'private/NEW_HEAD_OOF_PREDICTIONS.jsonl.gz':'3d511d193e39d1b0811812dfaf1b0bcd887221bb2621b1e32912ea4594107cc8',
    'private/P_P_DECILES_OUTCOME_FREE.jsonl.gz':'e4bf41e04c1b48746625c948a9b5d1df009af08a9e74a7f20cd45c3a2e7daa68',
    'private/QUALITY_TEACHERS_EVAL.jsonl.gz':'2a33ff5da48a945a813e03d301ebaff7396836e480fea6f76f1684193ce3504f',
    'inputs/COMMON_EVAL_MASK.jsonl.gz':'e369d4000ec1c9083cc428a3a318c5d936763ee5497f2dca06213e52ec9e89d8',
    'inputs/MOVE_P5_SCORE_STREAM.jsonl.gz':'14c48e61554bd58c6d5289b410d6a8c859cb37efd0dbc5d98987fcb440aac2ed',
    'inputs/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz':'c446633dec923e3a80a534b19325ccff49f769a2ff1d29c7af1202202de614d4'}

def baseline_rows():
    # No corrupt Q4, new-head prediction or model state is opened here.
    for rel,h in EXPECTED.items():assert sha(OLD_WORK/rel)==h
    scores=rows(OLD_WORK/'private/COMMON_SAVED_SCORES.jsonl.gz')
    teachers=rows(OLD_WORK/'private/QUALITY_TEACHERS_EVAL.jsonl.gz')
    deciles=rows(OLD_WORK/'private/P_P_DECILES_OUTCOME_FREE.jsonl.gz')
    mask=rows(OLD_WORK/'inputs/COMMON_EVAL_MASK.jsonl.gz')
    sm={r['entry_id']:r for r in scores};tm={r['entry_id']:r for r in teachers}
    dm={r['entry_id']:r for r in deciles};mk={r['entry_id']:r for r in mask}
    assert len(scores)==len(sm)==1028 and len(teachers)==len(tm)==1600
    assert len(mask)==len(mk)==1039 and len(deciles)==len(dm)==1028
    included={r['entry_id'] for r in mask if r['included']}
    assert set(sm)==set(dm)==included=={r['entry_id'] for r in teachers if r['included_common_OOF']}
    result=[]
    for eid,s in sm.items():
        t=tm[eid];d=dm[eid];m=mk[eid]
        assert s['session']==t['session']==d['session']==m['session']
        assert s['block']==d['block']==m['block']
        assert s['entry_timestamp']==t['entry_timestamp']
        assert t['capture_complete'] and t['status']=='SUPPORTED_COMPLETE_CAPTURE' and t['entry_minute']<920
        assert all(t[f'U{u}'] in (0,1) for u in [2,3,5,10]) and t['WEAK2']==1-t['U2']
        assert all(math.isfinite(s[k]) for k in ['CORE_H2','CORE_H3','pP','legacy_ML','legacy_m2','legacy_m3','legacy_m5'])
        result.append({**s,**t})
    result.sort(key=key)
    assert Counter(r['bucket'] for r in result)=={'Q0_WEAK':596,'Q1_LOW':135,'Q2_MEDIUM':127,'Q3_BIG':103,'Q4_MEGA':67}
    assert {u:sum(r[f'U{u}'] for r in result) for u in [2,3,5,10]}=={2:432,3:297,5:170,10:67}
    assert len({r['session'] for r in result})==38
    return result,{eid:r['pP_decile'] for eid,r in dm.items()}

def authenticate():
    pack=ROOT.parent/'deliverables/Ark_Capital_Quality_v1_20261005_PRIVATE_CONTRACT_FAIL.zip'
    checks=[]
    with zipfile.ZipFile(pack) as z:
        assert z.testzip() is None
        manifest=json.loads(z.read('DELIVERY_MANIFEST.json'))
        assert manifest['head']==OLD_HEAD and manifest['qualityStatus']=='QUALITY_CONTRACT_FAIL'
        assert manifest['completed_unique_fits']==16 and not manifest['git_backed_source_and_evidence_copies_included']
        assert len(manifest['files'])==125
        seen=set()
        for item in manifest['files']:
            rel=item['path'];assert rel not in seen;seen.add(rel)
            body=z.read(rel);h=hashlib.sha256(body).hexdigest()
            assert len(body)==item['size'] and h==item['sha256']==sha(OLD_WORK/rel)
            if rel in EXPECTED:assert h==EXPECTED[rel]
            checks.append(item)
        assert set(EXPECTED)<=seen
        manifest_sha=hashlib.sha256(z.read('DELIVERY_MANIFEST.json')).hexdigest()
    fit=read(OLD/'FITS_COMPLETE.json');claim=read(OLD/'FIT_CLAIM.json');pre=read(OLD/'FEATURE_MODEL_SPLIT_PRECOMMIT.json')
    assert fit['fit_count']['total']==16 and fit['fit_count']['MOVE_U2']==fit['fit_count']['MOVE_U3']==8
    assert fit['OOF_per_head_N']==1039 and fit['common_supported_per_head_N']==1028
    assert fit['ConvergenceWarning_N']==fit['OOF_duplicates']==0
    assert len(fit['fit_ledger'])==len(claim['claims'])==16
    mm={x['path']:x for x in checks};ledger=[]
    for c in claim['claims']:
        h,b=c['head'],c['block'];name=f'{h}_BLOCK_{b:02d}'
        model=read(OLD_WORK/'private/models'/(name+'.json'))
        done=read(OLD_WORK/'private/fit_claims'/(name+'_COMPLETE.json'))
        started=read(OLD_WORK/'private/fit_claims'/(name+'_STARTED.json'))
        authoritative=next(x for x in fit['fit_ledger'] if x['head']==h and x['block']==b)
        assert done==authoritative and done['status']=='COMPLETE' and started['status']=='STARTED'
        assert done['attempts']==started['attempt']==model['fit_attempt']==1
        assert done['ConvergenceWarning_N']==model['ConvergenceWarning_N']==0
        assert done['target']==c['target'] and c['max_attempts']==1
        assert model['parameters']==pre['parameters'] and model['preprocessing']==read(OLD_WORK/f'inputs/models/MOVE_P_BLOCK_{b:02d}.json')['preprocessing']
        files={'model':f'private/models/{name}.json','fitted_state':f'private/models/{name}_FITTED_STATE.npz',
            'prediction':f'private/predictions/{name}.jsonl.gz','STARTED':f'private/fit_claims/{name}_STARTED.json',
            'COMPLETE':f'private/fit_claims/{name}_COMPLETE.json','training_payload':f'private/training/BLOCK_{b:02d}_PAST_ONLY.jsonl.gz'}
        assert mm[files['model']]['sha256']==done['artifact_sha256']
        assert mm[files['fitted_state']]['sha256']==done['state_sha256']
        assert mm[files['prediction']]['sha256']==done['prediction_sha256']
        assert mm[files['training_payload']]['sha256']==c['training_payload_sha256']==started['training_sha256']
        assert started['claim_sha256']==sha(OLD/'FIT_CLAIM.json')
        assert c['preprocessing_authority_sha256']==sha(OLD_WORK/f'inputs/models/MOVE_P_BLOCK_{b:02d}.json')
        assert all(done[k]==model[k] for k in ['train_N','train_positive_N','iterations'])
        assert model['test_dates']==pre['split']['blocks'][b-1]['test']
        ledger.append({**c,**{k:done[k] for k in ['train_N','test_N','iterations','attempts','ConvergenceWarning_N']},
            'artifacts':{k:mm[v] for k,v in files.items()},'preprocessing_authority_sha256':c['preprocessing_authority_sha256']})
    assert sha(OLD_METRICS)==METRIC_HASH==claim['code_sha256']['metrics.py']
    closure=read(OLD/'CLOSURE.json')
    assert closure['qualityStatus']=='QUALITY_CONTRACT_FAIL' and closure['terminal_checkpoint']=='Q12_CLOSURE_FIXED_STOP'
    save(OUT/'PRIVATE_PACK_AUTHENTICATION.json',{'exact_jst':now(),'status':'PASS','pack_sha256':sha(pack),
        'pack_size':pack.stat().st_size,'DELIVERY_MANIFEST_sha256':manifest_sha,'member_N':len(checks),'mismatch_N':0,
        'user_specified_hashes':EXPECTED,'transport_members':checks,'new_head_prediction_performance_reads':0})
    save(OUT/'COMPLETED_FITS_REUSE_FREEZE.json',{'exact_jst':now(),'status':'AUTHENTICATED_FOR_EXACT_REUSE',
        'old_head':OLD_HEAD,'old_cycle_status':closure['qualityStatus'],'old_fit_claim_sha256':sha(OLD/'FIT_CLAIM.json'),
        'old_fits_complete_sha256':sha(OLD/'FITS_COMPLETE.json'),'old_precommit_sha256':sha(OLD/'FEATURE_MODEL_SPLIT_PRECOMMIT.json'),
        'fit_N':16,'MOVE_U2':8,'MOVE_U3':8,'OOF_per_head':1039,'common_supported':1028,'expected_extra_per_head':11,
        'join_verification_deferred_until_baseline_PASS':True,'ConvergenceWarning_N':0,'newFits':0,'refits':0,'auditRefits':0,
        'fit_ledger':ledger,'prediction_shards_read_for_metrics':0,'metrics_code_sha256':METRIC_HASH,'Safety':SAFETY})
    checkpoint('R1_PRIVATE_PACK_AND_FIT_REUSE_FREEZE',['125 transport members exact; 16 completed artifacts/receipts/claims authenticated'],
        {'member_hash_mismatch_N':0,'reusedCompletedFits':16,'newFits':0,'new_head_performance_evaluation':0},'R2 precommit deterministic baseline and independent code before metrics')
    print(json.dumps({'pack_members':125,'reuse':16,'newFits':0,'status':'PASS'}))

if __name__=='__main__':authenticate()
