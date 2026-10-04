"""R6 freezes wrappers, independent audit and exact old gates before performance."""
from control import *

def main():
    assert read(OUT/'MODEL_ARTIFACT_AUDIT.json')['status']=='PASS'
    assert read(OUT/'BASELINE_INDEPENDENT_CERTIFICATION.json')['status']=='PASS'
    pre=read(OLD/'FEATURE_MODEL_SPLIT_PRECOMMIT.json')
    assert sha(OLD_METRICS)==METRIC_HASH
    names=['performance.py','independent_performance.py','independent_stats.py','independent_io.py','control.py','precommit_performance.py']
    codes={str((CODE/n).relative_to(ROOT)):sha(CODE/n) for n in names}
    codes[str(OLD_METRICS.relative_to(ROOT))]=METRIC_HASH
    record={'exact_jst':now(),'status':'PRECOMMITTED_BEFORE_FIRST_NEW_HEAD_PERFORMANCE',
        'metric_code_sha256':METRIC_HASH,'old_precommit_sha256':sha(OLD/'FEATURE_MODEL_SPLIT_PRECOMMIT.json'),
        'old_metrics_semantic_change':0,'old_gates_semantic_change':0,'old_decision_semantic_change':0,
        'code_sha256':codes,'common_rows_sha256':sha(PRIVATE/'QUALITY_COMMON_EVAL_ROWS_V1R1.jsonl.gz'),
        'common_rows_N':1028,'baseline_metrics_reuse':True,'Primary_performance_packages_max':1,
        'Independent_performance_packages_max':1,'bootstrap':pre['bootstrap'],
        'seed':5701005,'resamples_per_head':1999,'unit':'paired session cluster','fixed_deciles':True,
        'session_draw_hash_serialization':'canonical JSONL of 38 integer indices per draw in sorted session order; final newline1',
        'bootstrap_sample_capture':'read-only sys.setprofile observation of frozen interval inputs; no frozen function replacement or semantic changes',
        'thresholds_fixed':[.1,.2,.3,.4],'K':'ceil(N*fraction)','newFits':0,'refits':0,'auditRefits':0,
        'canary_plan':{'minimum':44,'all_required':'PASS'},'integrity_failure_status':'QUALITY_RECOVERY_CONTRACT_FAIL',
        'AntiWeak_gates':pre['AntiWeak_gates'],'MediumPlus_gates':pre['MediumPlus_gates'],
        'BigMega_guard':pre['BigMega_guard'],'final_status_mapping':pre['final_status_mapping'],
        'combined_score':0,'threshold_sweep':0,'CapitalReplay':0,'MAX3Replay':0,'Safety':SAFETY}
    save(OUT/'PERFORMANCE_EVAL_PRECOMMIT.json',record)
    for name,mode in [('PERFORMANCE_PRIMARY_EXECUTION_CLAIM','primary'),('PERFORMANCE_INDEPENDENT_EXECUTION_CLAIM','independent')]:
        save(OUT/(name+'.json'),{'exact_jst':now(),'mode':mode,'maximum_executions':1,'new_fits':0,
            'committed_before_execution':True,'actual_GET_before_execution_verified':True,'code_sha256':codes,
            'precommit_sha256':sha(OUT/'PERFORMANCE_EVAL_PRECOMMIT.json'),
            'ambiguous_execution_policy':'STOP; inspect receipts; never rerun completed/ambiguous evaluation or optimizer'})
    checkpoint('R6_PERFORMANCE_EVAL_PRECOMMIT',['fixed old metric/bootstrap/gates/decision; Primary and Independent single-package claims before evaluation'],
        {'primary_performance_evaluations':0,'independent_performance_evaluations':0,'bootstrap_executed':0,'newFits':0},
        'R7 one primary package; report conditional/ordinal/guards without extra result-driven analysis')
    print('R6 ready; new-head performance=0; bootstrap=0')

if __name__=='__main__':main()
