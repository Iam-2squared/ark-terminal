"""Q1 duplicate audit and immutable no-repeat decisions."""
from control import *

def main():
    audit = read(WORK/'duplicate_audit_source.json')
    assert len(audit['default_branch_code_metadata_search']) == 12
    assert all(r['total_count'] == 0 for r in audit['default_branch_code_metadata_search'])
    assert not audit['fixed_base_research_truncated']
    assert not audit['fixed_base_matching_target_paths']
    specifications = [
        ('Big Winner One-Shot', 'capital-bigwinner-one-shot-20261004-v1', 'ROLLING_ORIGIN_SCORE_RESULT.json', ['CORE_U5'], 'reuse only; direct CORE U5 refit prohibited'),
        ('Movement v2', 'capital-vnext-v2-movement-20261004-v1', 'ROLLING_ORIGIN_HEAD_FITS.json', ['CORE_P', 'MOVE_P', 'MOVE_R'], 'MOVE_P5 reused; CORE_P/MOVE_P/MOVE_R refit prohibited'),
        ('Quality v3', 'capital-max3-top3-quality-v3-20261004-v1', 'NEW_HEAD_FITS.json', ['H3', 'HF1', 'HL0'], 'H3 reused; HF1/HL0/LSAFE/Q1-Q8 not repeated'),
        ('Upward Staircase', 'capital-max3-upward-staircase-v4-20261004-v1', 'H2_FITS.json', ['H2', 'H3', 'H5'], 'H2/H3/H5 reused; new CORE fits prohibited'),
        ('Rank vNext', 'capital-rank-bigwinner-vnext-20261005-v1', 'SELECTED_RANK_CONTRACT.json', ['EXISTING_MOVE_P5'], 'pP model/features/preprocessing/split frozen'),
    ]
    matrix = []
    for work, directory, filename, heads, decision in specifications:
        p = ROOT/'docs/evidence'/directory/filename
        payload = read(p)
        matrix.append({'prior_work': work, 'heads': heads, 'source': str(p.relative_to(ROOT)),
            'source_sha256': sha(p), 'payload_keys_audited': list(payload), 'decision': decision,
            'new_fit_N': 0, 'new_replay_N': 0})
    matrix.append({'prior_work':'PRR 566', 'decision':'NOT_COMPARABLE population/Entry/fold; forced join and refit prohibited', 'new_fit_N':0})
    result = {'exact_jst': now(), 'base': BASE, 'GitHub_branches_metadata_N': audit['branches_total_metadata'],
        'metadata_only_searches': audit['default_branch_code_metadata_search'],
        'fixed_base_research_paths_N': audit['fixed_base_research_total_paths'],
        'matrix': matrix, 'v8_v8R1_research_content_reads': 0,
        'artifact_identity_dimensions': ['population', 'teacher', 'feature manifest', 'preprocessing', 'split', 'model config'],
        'same_completed_Movement_U2_U3_artifact_N': 0}
    save(OUT/'PRIOR_QUALITY_WORK_MATRIX.json', result)
    save(OUT/'DO_NOT_REPEAT.json', {'fixed_base': BASE, 'CORE_H2_H3_H5':0, 'pP_MOVE_P5':0,
        'MOVE_R':0, 'HF1_HL0_LSAFE_Q1_Q8':0, 'PRR566_join_or_fit':0,
        'Weak2_separate_fit':0, 'combined_score':0, 'Capital_MAX3_replay':0,
        'extra_family_hyperparameter_feature_threshold_search':0,
        'max_new_fits':16, 'teachers_fixed_by_user':True})
    save(OUT/'REUSE_DECISION.json', {'exact_jst':now(), 'completed_identical_U2_U3_found':False,
        'reuse_heads':['CORE_H2','CORE_H3','EXISTING_MOVE_P5','legacy_ML'],
        'fit_only_if_missing':['MOVE_U2','MOVE_U3'], 'maximum_fits_per_head':8,
        'reason':'No same completed Movement U2/U3 head in start-time GitHub metadata search or fixed-base work manifests. Existing heads are different targets or input families.',
        'main_allocation_information_imported':0})
    checkpoint('Q1_PRIOR_WORK_INVENTORY','COMPLETE', ['12 metadata code searches completed; all returned0',
        'Fixed-base work model ledgers inspected','Prior completed fits permanently excluded'],
        {'identical_heads_found':0, 'planned_new_fits_max':16}, 'Q2 teacher support and common mask freeze')
    print({'checkpoint':'Q1', 'same_completed_heads':0, 'planned_fits':16})

if __name__ == '__main__':
    main()
