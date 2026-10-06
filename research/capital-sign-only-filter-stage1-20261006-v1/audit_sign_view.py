"""Independent teacher-boundary audit; downstream receives only sign invariance receipts."""
from fractions import Fraction
from sign_io import *

def main():
    source=rows(OLD/'RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz')
    view={r['entry_id']:validate_sign(r) for r in rows(PRIVATE/'SIGN_LABEL_VIEW.jsonl.gz')}
    mismatches=[]; changed=[];same_payload=0
    for raw in source:
        if not raw['known'] or raw['buy_debit'] is None or raw['sell_credit'] is None:status='UNKNOWN';y=None
        else:
            diff=Fraction(raw['sell_credit'])-Fraction(raw['buy_debit'])
            status='NEGATIVE' if diff<0 else 'POSITIVE' if diff>0 else 'EXACT_ZERO';y=1 if diff<0 else 0 if diff>0 else None
        r=view[raw['entry_id']]
        if r['sign_status']!=status or r['y_neg']!=y:mismatches.append(raw['entry_id'])
        if y is not None:
            modified=dict(raw);modified['buy_debit']='1000';modified['sell_credit']='1' if y==1 else '1000000'
            diff=Fraction(modified['sell_credit'])-Fraction(modified['buy_debit'])
            assert int(diff<0)==y and diff!=0
            provenance=digest(modified);assert provenance!=r['source_hash']
            changed.append({**r,'source_hash':provenance});same_payload+=1
        else:changed.append(r)
    assert not mismatches
    gzsave(PRIVATE/'AUDIT_MAGNITUDE_CHANGED_SIGN_VIEW.jsonl.gz',changed,exclusive=True)
    save(OUT/'SIGN_BOUNDARY_AUDIT.json',{'status':'PASS','exact_jst':now(),'rows_checked':len(source),
        'credit_debit_sign_mismatch_N':len(mismatches),'changed_magnitude_same_sign_N':same_payload,
        'UNKNOWN_N':sum(r['sign_status']=='UNKNOWN' for r in view.values()),'EXACT_ZERO_N':sum(r['sign_status']=='EXACT_ZERO' for r in view.values()),
        'continuous_outcome_exported':False,'new_cost_application':0,'new_R_materialization':0,
        'modified_source_hash_recorded_separately':True,'modified_view_sha256':sha(PRIVATE/'AUDIT_MAGNITUDE_CHANGED_SIGN_VIEW.jsonl.gz')})
    print(canonical({'sign_boundary':'PASS','checked':len(source),'within_sign_changes':same_payload}))

if __name__=='__main__':main()
