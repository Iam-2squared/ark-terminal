"""Promote pre-result drafts to formal contracts; never reads first-passage labels."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
def read(n):return json.loads((HERE/n).read_bytes())
def write(n,d):(HERE/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def freeze(stage):
    assert read('STATE9_ENTRY_TIMELINE_RECEIPT.json')['gate']=='PASS'
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
    if stage=='target':
        assert not (HERE/'LABEL_RECEIPT.json').exists()
        target=read('FIRST_PASSAGE_CONTRACT.DRAFT.json')
        target.update(status='FROZEN',frozen_at_jst=now,label_implementation_sha256=sha(HERE/'first_passage_labels.py'),
            arithmetic='saved canonical float64 P0 and saved OHLC; exact comparisons with no epsilon-imputation; independent Decimal audit checks first passage and reports any boundary mismatch',
            source_invalid_OHLC='DATA_UNAVAILABLE if an invalid/nonpositive/nonfinite OHLC bar precedes first passage; no invented ordering',
            current_primary_population=2155,current_candidate_rows=65312,current_sessions=58,
            source_raw_path_sha256=sha(HERE.parents[1]/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz'),
            source_outcomes_sha256=sha(HERE.parents[1]/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/outcomes.json.gz'),
            C1_receipt_sha256=sha(HERE/'STATE9_ENTRY_TIMELINE_RECEIPT.json'),new_fits=0,new_labels=0)
        write('FIRST_PASSAGE_CONTRACT.json',target)
        split=read('SPLIT_PRECOMMIT.DRAFT.json');split.update(status='FROZEN_BEFORE_TARGET_LABELS',frozen_at_jst=now,
            source_folds_sha256=sha(HERE/'R1_folds.json'),outer_test_opportunity_counts=[442,446,445,412,410],
            support_note='Each outer-fold threshold uses pooled inner OOF from its training-side Development sessions; no outer-test labels enter threshold/family selection. Outer OOF support and precision are reported separately, never retuned.',
            threshold_tie_break='maximum selected Opportunity coverage; then lower DOWN_FIRST rate, lower NO_ENTRY; exact within-family ties choose higher threshold',
            deployment_refit=0)
        assert split['source_folds_sha256']=='3342c68cc8a1987e11dda6f6c07757a47ff43d1e7f7f1506cb2e1ca0b3b41021'
        write('SPLIT_PRECOMMIT.json',split)
        write('C1_METRIC_COUNT_CLARIFICATION.json',dict(status='COUNT_LABEL_CLARIFICATION_ONLY',
            original_receipt_sha256=sha(HERE/'STATE9_ENTRY_TIMELINE_RECEIPT.json'),
            original_field='normalization80_120_checks',original_value=758640,
            correct_count_type='scheduled RC2 kernel steps, including missing-input steps; not a count of 758640 observed-price normalization checks',
            normalization_mismatches=0,factorization_golden_checks=12945,source_identity_changed=False,
            source_semantics_changed=False,original_C1_receipt_preserved=True))
    else:
        assert read('FIRST_PASSAGE_CONTRACT.json')['status']=='FROZEN'
        feature=read('FEATURE_FAMILY_FREEZE.DRAFT.json')
        feature.update(status='FROZEN_BEFORE_LABEL_RESULTS',frozen_at_jst=now,
            feature_numeric_scaling='After train-fold median/0 imputation: unweighted training-row mean and standard deviation; zero standard deviation=>1; standardize numeric values only, missing indicators remain 0/1.',
            feature_categorical_encoding='one-hot finite training-fold categories only; explicit MISSING/UNKNOWN/formal-null retained; unseen test category maps to all-zero known-category columns; no hashing or target encoding',
            H2_numeric=[k for k in feature['H2_added'] if k not in ('previous_distinct_formal_primary','previous_to_current_pair','last3_distinct_primary_sequence')],
            H2_categorical=['previous_distinct_formal_primary','previous_to_current_pair','last3_distinct_primary_sequence'],
            H2_history_scope='At the candidate intent, use only last closed RC2 endpoint and past events. Dwell is elapsed active minutes from observed ENTER; time since change is UNKNOWN until an actual TRANSITION; 5/10/15 counts require continuous observed support >= window. Last3 requires three distinct states in the same segment.',
            new_feature_source_sha256=sha(HERE/'h0_saved_feature_join.py'),
            H1_H2_saved_timeline_sha256=sha(HERE/'CAUSAL_STATE_CANDIDATE_ROWS.jsonl.gz'),
            raw_score='decision_function logit; never hand off as calibrated absolute probability',
            probability_metric_scope='Brier/LogLoss use uncalibrated sigmoid(logit) as evaluator-only diagnostic, not Entry probability.',
            selected_policy='Fold-wise train-inner-OOF selected family/threshold; selected arm can vary by outer fold; no final global refit.',
            planned_fits=60,model_search=0,bootstrap=0,productionReady=False)
        write('FEATURE_FAMILY_FREEZE.json',feature)
    print(json.dumps({'stage':stage,'status':'FROZEN','new_labels':0,'new_fits':0}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['target','feature']);freeze(ap.parse_args().stage)
