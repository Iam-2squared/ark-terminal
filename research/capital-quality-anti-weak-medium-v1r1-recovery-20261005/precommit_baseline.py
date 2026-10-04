"""R2: only hashes/contracts/claims, absolutely no performance metric calls."""
from control import *
from sources import EXPECTED

def main():
    assert read(OUT/'PRIVATE_PACK_AUTHENTICATION.json')['mismatch_N']==0
    assert read(OUT/'COMPLETED_FITS_REUSE_FREEZE.json')['fit_N']==16
    rootinputs={p:h for p,h in EXPECTED.items() if p in [
        'private/COMMON_SAVED_SCORES.jsonl.gz','private/QUALITY_TEACHERS_EVAL.jsonl.gz',
        'private/P_P_DECILES_OUTCOME_FREE.jsonl.gz','inputs/COMMON_EVAL_MASK.jsonl.gz']}
    names=['control.py','sources.py','baseline_rebuild.py','independent_stats.py','independent_io.py','independent_baseline.py','precommit_baseline.py']
    codes={str((CODE/n).relative_to(ROOT)):sha(CODE/n) for n in names}
    codes[str(OLD_METRICS.relative_to(ROOT))]=METRIC_HASH
    pre={'exact_jst':now(),'status':'PRECOMMITTED_BEFORE_ANY_RECOVERY_METRIC','input_sha256':rootinputs,
        'expected_rows':{'COMMON_SAVED_SCORES':1028,'QUALITY_TEACHERS_EVAL':1600,'P_P_DECILES_OUTCOME_FREE':1028,'COMMON_EVAL_MASK':1039},
        'expected_common_N':1028,'expected_buckets':{'Q0_WEAK':596,'Q1_LOW':135,'Q2_MEDIUM':127,'Q3_BIG':103,'Q4_MEGA':67},
        'join_key':'entry_id','secondary_identity':['session','block','entry_timestamp'],
        'sort':['block ASC','session ASC','entry_timestamp ASC','symbol ASC','entry_id ASC'],
        'metric_code_sha256':METRIC_HASH,'code_sha256':codes,'semantic_changes':0,
        'canonical_serialization':{'encoding':'UTF-8','sort_keys':True,'allow_nan':False,'separators':[',',':'],'ensure_ascii':True,
            'final_newlines':1,'float':'Python finite decimal representation','gzip_mtime':0,'gzip_filename_metadata':False},
        'public_policy':'compact JSON summaries and SHA/size/schema roots only; no giant conditional group lists; maximum120000 bytes/file',
        'private_policy':'full metrics JSON.gz; conditional group JSONL.gz; canonical row JSONL.gz; compressed and uncompressed SHA256',
        'independent_plan':'no primary baseline/evaluate/metrics imports; rank-sum ties ROC, threshold grouped AP, independent TopK and pairwise conditional; compare compact/full/root/identity <=1e-12',
        'publication':'latest GET before commit; actual immutable GET each body; parse and exact downloaded bytes/hash; then independent reconstruction',
        'failure_conditions':['source/hash/identity/count mismatch','noncanonical or nonfinite serialization','public actual GET mismatch','independent mismatch >1e-12','ambiguous execution'],
        'baseline_build_budget':{'primary':1,'independent':1},'newFits':0,'refits':0,'auditRefits':0,
        'old_corrupt_Q4_as_input':False,'old_cb1_hash_forced':False,'new_head_performance_before_baseline_certification':False,'Safety':SAFETY}
    save(OUT/'BASELINE_RECOVERY_PRECOMMIT.json',pre)
    for name,mode in [('BASELINE_PRIMARY_EXECUTION_CLAIM','primary'),('BASELINE_INDEPENDENT_EXECUTION_CLAIM','independent')]:
        save(OUT/(name+'.json'),{'exact_jst':now(),'stage':mode,'maximum_executions':1,'new_fits':0,
            'committed_before_execution':True,'actual_GET_before_execution_verified':True,
            'execution_requires_actual_GET_receipt':True,'code_sha256':codes,'precommit_sha256':sha(OUT/'BASELINE_RECOVERY_PRECOMMIT.json'),
            'ambiguous_execution_policy':'STOP; inspect receipts; never rerun completed or ambiguous build'})
    checkpoint('R2_BASELINE_RECOVERY_PRECOMMIT',['input/code/serialization/metric semantics frozen before metrics; single-execution primary and independent claims'],
        {'newFits':0,'baseline_primary':0,'baseline_independent':0,'new_head_performance_evaluation':0},'R3 exactly one primary semantic reconstruction; then actual GET and independent baseline')
    print('R2 precommit complete; metrics executed=0')

if __name__=='__main__':main()
