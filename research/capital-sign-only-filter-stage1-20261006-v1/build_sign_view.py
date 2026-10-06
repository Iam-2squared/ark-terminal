"""The sole outcome adapter allowed to read raw fixed debit/credit magnitudes."""
from fractions import Fraction
from collections import Counter
from sign_io import *

def sign_row(source):
    status='UNKNOWN'; y=None
    if source['known'] and source['buy_debit'] is not None and source['sell_credit'] is not None:
        debit=Fraction(str(source['buy_debit'])); credit=Fraction(str(source['sell_credit']))
        assert debit > 0
        status='POSITIVE' if credit>debit else 'NEGATIVE' if credit<debit else 'EXACT_ZERO'
        y={'POSITIVE':0,'NEGATIVE':1,'EXACT_ZERO':None}[status]
    return validate_sign({'entry_id':source['entry_id'], 'session':source['session'],
                          'sign_status':status, 'y_neg':y, 'label_maturity':source['label_maturity'],
                          'source_hash':digest(source)})

def main():
    PRIVATE.mkdir(exist_ok=True)
    source=rows(OLD/'RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz')
    target=[sign_row(s) for s in source]; runtime=rows(OLD/'RUNTIME_FEATURES.jsonl.gz')
    rm={r['entry_id']:r for r in runtime}; split=read(SPLIT)
    assert len(rm)==len(target)==1600 and {r['entry_id'] for r in target}==set(rm)
    known=[r for r in target if r['y_neg'] is not None]
    assert all(r['y_neg']==s['y_neg'] for r,s in zip(target,source) if r['y_neg'] is not None)
    if (PRIVATE/'SIGN_LABEL_VIEW.jsonl.gz').exists():
        assert rows(PRIVATE/'SIGN_LABEL_VIEW.jsonl.gz') == target
    else:
        gzsave(PRIVATE/'SIGN_LABEL_VIEW.jsonl.gz',target,exclusive=True)
    groups={
      'ALL_PERIOD_ALL_ENTRY':target,
      'WARMUP_ALL_ENTRY':[r for r in target if r['session'] in split['warmup20']],
      'WARMUP_EXECUTION_ELIGIBLE':[r for r in target if r['session'] in split['warmup20'] and rm[r['entry_id']]['execution_eligible']],
      'OOF_ALL_ENTRY':[r for r in target if r['session'] in split['OOF38']],
      'OOF_EXECUTION_ELIGIBLE':[r for r in target if r['session'] in split['OOF38'] and rm[r['entry_id']]['execution_eligible']],
      'OOF_RANK_PASS':[r for r in target if r['session'] in split['OOF38'] and rm[r['entry_id']]['execution_eligible'] and rm[r['entry_id']]['rank_pass']]}
    counts={k:{'rows':len(rr),'sessions':len({r['session'] for r in rr}),**{s:sum(r['sign_status']==s for r in rr) for s in ['POSITIVE','NEGATIVE','EXACT_ZERO','UNKNOWN']}} for k,rr in groups.items()}
    save(OUT/'SIGN_LABEL_COUNTS.json',{'counts':counts,'source_label_difference_N':0,'identity_difference_N':0,'strict_zero_not_nonnegative':True,'new_outcome_materialization':0})
    save(OUT/'SIGN_TARGET_CONTRACT.json',{'status':'PASS','authority':'Frozen Entry -> Frozen Structural EXIT plus inherited EOD settlement',
      'comparison':'Fraction(sell_credit) compared directly to Fraction(buy_debit)',
      'labels':{'POSITIVE':0,'NEGATIVE':1,'EXACT_ZERO':None,'UNKNOWN':None},'allowed_view_fields':sorted(SIGN_FIELDS),
      'cost':'inherited effective prices BUY=1.0005 SELL=0.9995 commission=0; no extra application',
      'original_binding_sha256':sha(OLD_OUT/'RNEG_TARGET_BINDING.json'),'original_target_sha256':sha(OLD/'RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz'),
      'sign_view_sha256':sha(PRIVATE/'SIGN_LABEL_VIEW.jsonl.gz'),'zero_tolerance':0,'weights':'all 1; sample_weight=None; class_weight=None',
      'source_hash_role':'audit provenance only; excluded from model/threshold/metric/gate mathematical payload',
      'forbidden_outcome_fields':['continuous_R','pnl','U/R_hierarchy','EXIT_reason','future_holding_duration','future_High_Low','quantity','portfolio_assets'],
      'outcome_files_read_by_fit_threshold_evaluator':['SIGN_LABEL_VIEW.jsonl.gz']})
    print(canonical({'sign_counts':counts,'known':len(known)}))

if __name__=='__main__':main()
