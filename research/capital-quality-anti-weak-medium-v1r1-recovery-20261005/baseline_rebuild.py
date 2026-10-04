"""One claimed semantic baseline reconstruction using exact frozen metrics."""
from collections import Counter
from control import *
from sources import EXPECTED, baseline_rows

SCORES=['CORE_H2','CORE_H3','pP','legacy_ML']

def main():
    claim=guard_claim('BASELINE_PRIMARY_EXECUTION_CLAIM',[OUT/'BASELINE_RECOVERY_ROOT.json',PRIVATE/'BASELINE_METRICS_FULL.json.gz'])
    assert read(OUT/'BASELINE_RECOVERY_PRECOMMIT.json')['metric_code_sha256']==METRIC_HASH
    data,dec=baseline_rows();m=old_metrics()
    assert m.decile_rows(data)==dec
    mm={s:m.quality(data,s) for s in SCORES}
    cc={t:{s:m.conditional(data,s,t,dec) for s in SCORES} for t in ['U2','U3']}
    full={'N':1028,'metrics':mm,'conditional':cc,'new_fits':0,'metric_code_sha256':METRIC_HASH}
    compact={**full,'conditional':compact_conditionals(cc)}
    groups=[{'target':t,'score':s,'variant':v,**g} for t in ['U2','U3'] for s in SCORES
        for v in ['pP_conditional','same_session','same_session_pP_conditional'] for g in cc[t][s][v]['groups']]
    artifacts=[gzsave(PRIVATE/'BASELINE_METRICS_FULL.json.gz',full),
        gzsave(PRIVATE/'BASELINE_CONDITIONAL_GROUPS.jsonl.gz',groups,True),
        gzsave(PRIVATE/'BASELINE_ROWS_CANONICAL.jsonl.gz',data,True)]
    identity={'N':1028,'score_source_N':1028,'teacher_source_N':1600,'mask_source_N':1039,'decile_source_N':1028,
        'sessions':38,'blocks':8,'join_key':'entry_id','secondary_identity':['session','block','entry_timestamp'],
        'sort':['block ASC','session ASC','entry_timestamp ASC','symbol ASC','entry_id ASC'],
        'bucket_counts':dict(Counter(r['bucket'] for r in data)),
        'positive_counts':{f'U{u}':sum(r[f'U{u}'] for r in data) for u in [2,3,5,10]},
        'ordered_entry_ids_sha256':hashlib.sha256(('\n'.join(r['entry_id'] for r in data)+'\n').encode()).hexdigest(),
        'canonical_rows_uncompressed_sha256':artifacts[2]['uncompressed_sha256'],'identity_mismatch_N':0,
        'decile_mismatch_N':0,'unknown_negative_imputation':0,'new_head_performance_reads':0,'status':'PASS'}
    save(OUT/'BASELINE_METRICS_COMPACT.json',compact)
    save(OUT/'BASELINE_IDENTITY_AUDIT.json',identity)
    root={'cycle':'QUALITY_V1R1_SEMANTIC_BASELINE_RECOVERY','old_Q4_metric_input':False,'old_byte_hash_recovery':False,
        'metric_code_sha256':METRIC_HASH,'input_sha256':{p:h for p,h in EXPECTED.items() if p in [
            'private/COMMON_SAVED_SCORES.jsonl.gz','private/QUALITY_TEACHERS_EVAL.jsonl.gz',
            'private/P_P_DECILES_OUTCOME_FREE.jsonl.gz','inputs/COMMON_EVAL_MASK.jsonl.gz']},
        'N':1028,'canonical_serialization':{'UTF8':True,'sort_keys':True,'allow_nan':False,'separators':[',',':'],
            'final_newlines':1,'float':'Python finite decimal JSON representation','gzip_mtime':0,'gzip_filename_metadata':False},
        'private_artifacts':artifacts,'compact_sha256':sha(OUT/'BASELINE_METRICS_COMPACT.json'),
        'identity_audit_sha256':sha(OUT/'BASELINE_IDENTITY_AUDIT.json'),'newFits':0,
        'public_large_nested_group_lists':False,'independent_certification':'REQUIRED_BEFORE_NEW_HEAD_EVALUATION'}
    save(OUT/'BASELINE_RECOVERY_ROOT.json',root)
    for p in ['BASELINE_METRICS_COMPACT.json','BASELINE_IDENTITY_AUDIT.json','BASELINE_RECOVERY_ROOT.json']:
        assert (OUT/p).read_bytes()==canonical(read(OUT/p))
    checkpoint('R3_BASELINE_PRIMARY_REBUILD',['deterministic common1028 baseline reconstructed once from pre-Q4 row-level authorities',
        'full conditional details compressed privately; compact/public hash root canonical parse PASS'],
        {'N':1028,'newFits':0,'new_head_performance_reads':0,'baseline_root_sha256':sha(OUT/'BASELINE_RECOVERY_ROOT.json')},
        'Publish compact/root and actual GET bodies; independent baseline certification before new-head performance')
    print(json.dumps({'baseline_N':1028,'primary_builds':1,'compact_bytes':(OUT/'BASELINE_METRICS_COMPACT.json').stat().st_size,'new_head_performance_reads':0}))

if __name__=='__main__':main()
