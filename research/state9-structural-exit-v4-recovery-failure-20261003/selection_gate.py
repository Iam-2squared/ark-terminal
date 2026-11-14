"""User-specified conservative numerical gate. Fixed before outcomes."""
TARGET=['2–<3%','3–<4%','4–<5%']

def selection(primary,audit=None):
    g={r['group']:r for r in primary};c=g['2–<5%_COMBINED'];big=g['>=5%_PROTECTION']
    change=lambda r,k:r['return_common_group_difference'][k]
    exclusive={b:change(g[b],'mean') for b in TARGET}
    conditions={
        'combined_mean_strictly_greater':change(c,'mean')>0,
        'combined_median_strictly_greater':change(c,'median')>0,
        'three_exclusive_means_nonworse':all(v>=0 for v in exclusive.values()),
        'at_least_two_exclusive_means_strictly_greater':sum(v>0 for v in exclusive.values())>=2,
        'GE5_mean_nonworse':change(big,'mean')>=0,
        'GE5_median_nonworse':change(big,'median')>=0,
        'audit_zero':audit is not None and audit['mismatch_N']==audit['future_causal_leakage_N']==0,
    }
    if audit is not None and not conditions['audit_zero']:status=audit['status']
    elif not conditions['combined_mean_strictly_greater'] or not conditions['combined_median_strictly_greater']:status='V4_NOT_BETTER_KEEP_V3'
    elif not conditions['three_exclusive_means_nonworse'] or not conditions['GE5_mean_nonworse'] or not conditions['GE5_median_nonworse']:status='V4_MIXED_KEEP_HUMAN_JUDGMENT'
    elif not conditions['at_least_two_exclusive_means_strictly_greater']:status='V4_NOT_BETTER_KEEP_V3'
    else:status='V4_STRICT_IMPROVEMENT_CANDIDATE' if audit is not None else 'AUDIT_PENDING_STRICT_NUMERICAL_CONDITIONS_MET'
    return {'status':status,'provisional_until_independent_audit':audit is None,'fixed_conditions':conditions,'target_combined_common_filled_N':c['return_common_filled_N'],'target_combined_watch_N':c['denominator_N'],'exclusive_mean_delta_pp':exclusive,'combined_mean_delta_pp':change(c,'mean'),'combined_median_delta_pp':change(c,'median'),'GE5_mean_delta_pp':change(big,'mean'),'GE5_median_delta_pp':change(big,'median'),'fallback_policy':'STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD','V3_fallback_changes':0,'automatic_adoption':False,'later_missed_upside_single_FAIL':False,'qualitative_concentration_threshold':'Not numerically specified by user; no new numerical cutoff. Frozen contribution/breadth diagnostics and explicit report assessment.','STOP':True}
