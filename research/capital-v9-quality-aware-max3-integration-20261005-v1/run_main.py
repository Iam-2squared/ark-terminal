"""Exactly one claimed primary run per policy; interrupted runs are never retried."""
from control import *
from tables import primary_tables
from replay import run
def main():
    claim=read(OUT/'MAIN_REPLAY_CLAIM.json')
    assert claim['I1_replay']==claim['I2_replay']==1 and claim['primary_replays']==2
    assert read(OUT/'CAUSAL_CANARY_RESULTS.json')['all_PASS']
    assert read(OUT/'PRE_MAIN_INDEPENDENT_POLICY_AUDIT.json')['mismatch_N']==0
    assert read(OUT/'NUMERIC_DOMINANCE_BOUNDARY_AUDIT.json')['independent_boundary_disagreement_N']==0
    receipt=read(OUT/'receipts/V8_MAIN_REPLAY_CLAIM_ACTUAL_GET.json');assert receipt['actual_GET_verified'] and str((OUT/'MAIN_REPLAY_CLAIM.json').relative_to(ROOT)) in receipt['paths']
    for path,value in claim['code_sha256'].items():assert sha(ROOT/path)==value
    for path,value in claim['input_sha256'].items():assert sha(ROOT.parent/path)==value
    assert not any((PRIVATE/f'{a}_STARTED.json').exists() or (PRIVATE/f'{a}_COMPLETE.json').exists() for a in ARMS),'SINGLE_EXECUTION_ALREADY_CLAIMED_NO_RERUN'
    stream=rows(PRIVATE/'CURRENT_CAUSAL_QUALITY_RUNTIME.jsonl.gz');books={r['entry_id']:r for r in rows(MAIN/'inputs/execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};tables=primary_tables();results={}
    for arm in ARMS:
        save(PRIVATE/f'{arm}_STARTED.json',{'exact_jst':now(),'claim_sha256':sha(OUT/'MAIN_REPLAY_CLAIM.json'),'actual_claim_commit':receipt['actual_HEAD'],'single_execution':True,'rerun_allowed':False})
        result,ds,ts,cs,it=run(arm,stream,books,tables)
        for name,data in [('DECISIONS',ds),('TRADES',ts),('CURVE',cs),('INTENTS',it),('DAILY',result['daily_series']),('ROLLING20',result.get('rolling20_windows',[]))]:gzsave(PRIVATE/f'{arm}_{name}.jsonl.gz',data)
        result['ledger_sha256']={name:sha(PRIVATE/f'{arm}_{name}.jsonl.gz') for name in ('DECISIONS','TRADES','CURVE','INTENTS','DAILY','ROLLING20')}
        save(OUT/f'{arm}_RESULT.json',result);save(PRIVATE/f'{arm}_COMPLETE.json',{'exact_jst':now(),'primary_result_sha256':sha(OUT/f'{arm}_RESULT.json'),'ledgers':result['ledger_sha256'],'status':result.get('measurement_status','COMPLETE')});results[arm]=result
        print(json.dumps({k:result.get(k) for k in ('profile','measurement_status','funded_N','rolling20_median','rolling20_arithmetic_mean','north_star_hit_N','geometric_mean_daily_return','final_equity','max_drawdown')}),flush=True)
    save(OUT/'MAIN_REPLAY_RESULT.json',{'exact_jst':now(),'arms':results,'primary_replays':2,'I1_replay':1,'I2_replay':1,'saved_control_replays':0,'newFits':0,'claim_sha256':sha(OUT/'MAIN_REPLAY_CLAIM.json'),'Safety':SAFETY})
    checkpoint('V9_I1_I2_REPLAY_COMPLETE',{'primary_replays':2,'results':{a:r.get('measurement_status','COMPLETE') for a,r in results.items()}},'Join evaluation-only teachers for conservation, paired deltas and induced occupancy')
if __name__=='__main__':main()
