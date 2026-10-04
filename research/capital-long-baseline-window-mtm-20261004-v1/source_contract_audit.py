"""Actual source/suffix audit before replay. Primary/independent extract paths."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import copy,gzip,hashlib,json,sys
from collections import Counter
from window_mtm import latest_window_bar
from independent_audit import window_oracle,projection
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'capital-state9-liquidity-sameday-20261004-v1'))
from capital_contract import candidate_runtime

def main():
    root=Path(sys.argv[1]);out=root/'long_mtm_private';out.mkdir(exist_ok=True)
    read=lambda p:json.loads(gzip.open(p,'rt').read())
    entries=[e for e in map(json.loads,gzip.open(root/'eod_private/primary/entry.jsonl.gz','rt')) if e['entry_status']=='FIRST_ENTRY']
    a=read(root/'eod_private/primary/raw_paths.json.gz');b=read(root/'eod_private/independent/raw_paths.json.gz')
    counts=Counter();failures=[]
    def check(label,left,right):
        counts[label]+=1
        if left!=right:failures.append(label)
    for e in entries:
        runtime=candidate_runtime(e)
        check('independent_runtime_projection',runtime,projection(e))
        f=copy.deepcopy(e);f.update(profit=1e90,execution_evidence_status='UNKNOWN',next_day_price=.001,future_state='DROP')
        f['first_upside']={'5':{'minute':None}};f['pre_peak_mae_abs_pct']=1e9
        check('future_outcomes_do_not_change_rank_envelope',runtime,candidate_runtime(f))
        fill=datetime.fromisoformat(e['fill_timestamp']);m=fill.hour*60+fill.minute
        grid=(m//5+1)*5
        if grid>925 or 690<grid<755:continue
        key=e['watch_key'];first=latest_window_bar(a[key]['today'],grid);oracle=window_oracle(b[key]['today'],grid)
        check('independent_first_required_window_source',first,oracle)
        changed=[list(r) for r in a[key]['today']]
        for row in changed:
            if int(row[0])>=grid:row[4]=1e100
        check('future_window_price_suffix_current_mark_invariant',first,latest_window_bar(changed,grid))
        prior=[r for r in a[key]['today'] if int(r[0])<grid-5]
        check('cross_window_carry_never_allowed',None,latest_window_bar(prior,grid))
        if first:
            check('selected_mark_is_closed_same_window',True,grid-5<=int(first[0])<grid and int(first[0])+1<=grid)
            check('actual_Close_used_without_price_completion',Decimal(str(first[4])),Decimal(str(oracle[4])))
    hashes={name:hashlib.sha256((root/path).read_bytes()).hexdigest() for name,path in {
        'frozen_entry':'eod_private/primary/entry.jsonl.gz','frozen_exit':'eod_private/primary/exit_v3.jsonl.gz',
        'primary_raw':'eod_private/primary/raw_paths.json.gz','independent_raw':'eod_private/independent/raw_paths.json.gz',
        'capacities':'svnext_private/CAPACITIES_PRIVATE.json','primary_eod':'f1520_private/primary-v1/EOD1520_ADAPTER_ROWS.jsonl.gz',
        'independent_eod':'f1520_private/independent/INDEPENDENT_ROWS.jsonl.gz'}.items()}
    result={'jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'status':'PASS' if not failures else 'FAIL',
        'candidate_N':len(entries),'sessions_N':len({e['session'] for e in entries}),
        'checks_N':sum(counts.values()),'counts':dict(counts),'mismatch_N':len(failures),
        'failure_categories':dict(Counter(failures)),'source_hashes':hashes,
        'coverage_not_preBUY_filter':True,'source_suffix_audit_not_performance_replay':True,
        'new_estimator_fits':0,'new_state9_evaluations':0,'capital_performance_replays':0,
        'provider_requests':0,'missing_price_imputation_N':0}
    (out/'SOURCE_CONTRACT_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if failures:raise SystemExit(2)

if __name__=='__main__':main()
