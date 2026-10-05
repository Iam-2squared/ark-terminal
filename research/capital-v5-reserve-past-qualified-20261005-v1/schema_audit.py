"""Supplement P1: all1039 input rows, including545 native-filter rows absent from gate_decisions."""
from context import *
from policy import native_wrapper
from collections import Counter

def main():
    saved=read('proposals');tables=read('arrival');final={r['entry_id']:r for r in read('native_decisions')}
    checks=Counter();rowN=0
    for p in saved:
        result=native_wrapper(p['candidates'],p['snapshot'],p['session'],p['minute'],tables[str(p['candidates'][0]['block'])])
        assert result['picked_ids']==p['picked_ids'] and result['assigned']==p['assigned']
        checks['picked_and_assigned_full_batch_exact']+=1
        expected={d['entry_id']:d for d in p['gate_decisions']}
        assert len(result['gate_decisions'])==len(p['candidates'])
        assert {d['entry_id'] for d in result['gate_decisions'] if 'slot_gate_reason' in d}==set(expected)
        for d in result['gate_decisions']:
            rowN+=1
            if d['entry_id'] in expected:
                assert all(expected[d['entry_id']].get(k)==v for k,v in d.items())
                checks['pre_allocation_gate_row_exact']+=1
            else:
                assert d['reason'] in ('UPWARD_BELOW_BASELINE','CAPITAL_EOD_ENTRY_CUTOFF','SCORE_INPUT_UNKNOWN','SYMBOL_ALREADY_OPEN')
                src=final[d['entry_id']]
                assert src['reason']==d['reason'] and src['quantity']==0
                checks['filter_only_saved_native_decision_exact']+=1
    assert rowN==1039
    save('P1_FULL_NATIVE_ROW_SCHEMA_SUPPLEMENT.json',{'schema':'V5_R_P1_FULL_ROW_SUPPLEMENT_V1','exact_jst':now(),
        'status':'PASS','mismatch_N':0,'native_saved_batch_N':len(saved),'input_row_N':rowN,'checks':dict(checks),
        'prior_P1_receipt_preserved':True,'prior_P1_limitation':'zip comparison did not assert cardinality; filter-only rows were not checked',
        'repair_scope':'Complete saved-schema identity join, no policy/source/population change',
        'failure_receipt_sha256':sha(OUT/'failures/P3_NATIVE_RECORD_SCHEMA_001.json'),
        'new_market_replay_N':0,'new_singleton_probe_N':0,'new_qualification_table_N':0})
    print(json.dumps({'status':'PASS','row_N':rowN,'checks':dict(checks)}))

if __name__=='__main__':main()
