"""Freeze common honest population and saved-score fields before tournament."""
from collections import Counter, defaultdict
import hashlib
import json
from control import INPUTS, ROOT, OUT, PRIVATE, rows, now, save, sha, gzsave, checkpoint

def main():
    ledger=rows(PRIVATE/'TEACHER_SUPPORT_LEDGER.jsonl.gz')
    current=rows(INPUTS/'v4/capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')
    move=rows(INPUTS/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz')
    support={r['entry_id']:r for r in ledger}
    cm={r['entry_id']:r for r in current}; mm={r['entry_id']:r for r in move}
    accepted=[r['entry_id'] for r in current if r['entry_minute']<920 and
        support[r['entry_id']]['label_U5'] is not None and support[r['entry_id']]['label_U10'] is not None]
    assert len(accepted)==1028 and len(set(accepted))==1028
    split=json.loads((ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json').read_text())
    assert {r['session'] for r in current}==set(split['OOF38'])
    for key in accepted:
        c,m=cm[key],mm[key]
        assert (c['entry_id'],c['session'],c['symbol'],c['entry_timestamp'],c['entry_minute'],c['raw_reference'])==(m['entry_id'],m['session'],m['symbol'],m['entry_timestamp'],m['entry_minute'],m['raw_reference'])
        assert c['block']==m['block']
        assert c['session'] in split['blocks'][c['block']-1]['test']
    mask=[{'entry_id':r['entry_id'],'session':r['session'],'block':r['block'],
        'included':r['entry_id'] in set(accepted),'reason':'COMMON_SUPPORTED_PRE_CUTOFF_OOF' if r['entry_id'] in set(accepted) else 'NOT_MATURE_CUTOFF_OR_LATER',
        'PRR_status':'NOT_COMPARABLE_TARGET_DENOMINATOR_AND_POPULATION_CONTRACT'} for r in current]
    gzsave(PRIVATE/'COMMON_EVAL_MASK.jsonl.gz',mask)
    prr=rows(INPUTS/'prr/CANONICAL_OOF.jsonl.gz')
    assert len(prr)==1614
    assert sha(INPUTS/'prr/POTENTIAL_FIT_PROTOCOL.json')=='80fc1699457dfa725e032548f643241359468e0243ddc2671d4d0894d562e9bd'
    by_tuple=defaultdict(list)
    for r in prr:
        day,symbol,minute=r['entryId'].split('|')
        assert day==r['session']
        by_tuple[(day,symbol,int(minute))].append(r)
    matches=Counter()
    for key in accepted:
        c=cm[key]; pp=by_tuple.get((c['session'],c['symbol'],c['entry_minute']),[])
        matches['exact_timestamp_tuple_hit_N']+=bool(pp)
        matches['tuple_no_hit_N']+=not pp
        matches['tuple_multiple_arm_rows_N']+=len(pp)>1
    save(OUT/'PRR_COMPARABILITY_AUDIT.json',{
        'exact_jst':now(),'canonical_OOF_N':1614,'canonical_OOF_sha256':sha(INPUTS/'prr/CANONICAL_OOF.jsonl.gz'),
        'protocol_sha256':sha(INPUTS/'prr/POTENTIAL_FIT_PROTOCOL.json'),
        'current_common_N':len(accepted),'timestamp_tuple_diagnostic':dict(matches),
        'exact_eligible_join_N':0,'NOT_COMPARABLE_current_N':len(accepted),
        'reason':['PRR denominator effectiveEntryPrice, current denominator raw Entry reference',
            'PRR IM/R1 frozen policies and3 relevant original folds are different from current FIRST_ENTRY P1_Q70 and8 rolling-origin blocks',
            'Matching session/symbol/minute alone does not prove candidate, price, target horizon, or OOF training-population equivalence'],
        'forced_join_N':0,'PRR_relabel_N':0,'PRR_refit_N':0,'rank_reference_only':True,
        'previous_probability_status':'POTENTIAL_SKILL_FAIL preserved for both heads',
        'A2_EXISTING_PRR_HEAD5':'NOT_COMPARABLE','A3_EXISTING_PRR_HEAD10':'NOT_COMPARABLE'})
    manifest={'exact_jst':now(),'legacy_current_N':1039,'primary_common_supported_N':1028,
        'whole_frozen_pre_cutoff_population_N':1578,'warmup_unscored_N':550,
        'pre_cutoff_common_U5_positive_N':sum(support[k]['label_U5'] for k in accepted),
        'pre_cutoff_common_U10_positive_N':sum(support[k]['label_U10'] for k in accepted),
        'no_actual_high_complete_capture_negatives_retained_N':18,
        'excluded_from_primary_NOT_MATURE_N':11,'UNKNOWN_N':0,
        'rank_gate_population_filter_N':0,'liquidity_or_slot_filter_N':0,
        'score_fields':{'A0_CURRENT_V4_ML':'saved ML; original m5,m3,m2 descending ties then Entry timestamp/symbol',
            'A1_EXISTING_MOVE_P5':'saved pP (direct U5 OOF probability score); Entry timestamp/symbol ties; no lift/threshold/rank-band change'},
        'A1_field_reason':'Direct U5 model saved score; existing P_OOF_AUC uses pP. The earlier top20 enrichment used capital_score lift; its order is not silently substituted here.',
        'ordered_identity_sha256':hashlib.sha256(('\n'.join(accepted)+'\n').encode()).hexdigest(),
        'mask_sha256':sha(PRIVATE/'COMMON_EVAL_MASK.jsonl.gz'),
        'current_saved_score_sha256':sha(INPUTS/'v4/capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz'),
        'move_saved_score_sha256':sha(INPUTS/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz'),
        'teacher_sha256':sha(INPUTS/'v4/inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz'),
        'blocks':[{**b,'primary_N':sum(cm[k]['block']==b['block'] for k in accepted),
            'primary_U5_N':sum(support[k]['label_U5'] for k in accepted if cm[k]['block']==b['block']),
            'primary_U10_N':sum(support[k]['label_U10'] for k in accepted if cm[k]['block']==b['block'])} for b in split['blocks']],
        'mask_frozen_before_metrics':True,'fit_N':0,'replay_N':0}
    save(OUT/'COMMON_EVAL_MASK_FREEZE.json',manifest)
    checkpoint('R3_COMMON_EVAL_MASK_FREEZE','COMMON_SUPPORTED_MASK_FIXED_1028',
        ['All1578 pre-cutoff candidate population retained;550 warmup candidates are not OOF scored',
         '1028 common supported OOF identities;11 postcutoff exclusions fixed',
         'PRR both saved heads NOT_COMPARABLE; no forced joins'],
        {'N':1028,'U5_N':170,'U10_N':67,'retained_complete_capture_no_high_negative_N':18,'PRR_comparable_N':0},
        'Precommit metrics, ties, bootstrap and gate definitions; evaluate saved CURRENT ML and MOVE pP only, fit0')
    print(json.dumps({'N':1028,'PRR_tuple_checks':dict(matches),'PRR_eligible':0}))

if __name__=='__main__':main()
