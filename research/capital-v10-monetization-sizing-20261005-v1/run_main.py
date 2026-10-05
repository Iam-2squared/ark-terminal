"""One Primary chain per arm; exclusive STARTED receipt prevents any retry."""
from control import *
from scores import tables
from replay import run
def main():
    claim=read(OUT/'MAIN_REPLAY_CLAIM.json');receipt=read(OUT/'receipts/M9_MAIN_REPLAY_CLAIM_ACTUAL_GET.json')
    assert claim['S1_replay']==claim['S2_replay']==1 and claim['primary_replays']==2 and receipt['actual_GET_verified']
    assert str((OUT/'MAIN_REPLAY_CLAIM.json').relative_to(ROOT)) in receipt['paths']
    for p,h in claim['code_sha256'].items():assert sha(ROOT/p)==h
    for p,h in claim['input_sha256'].items():assert sha(ROOT.parent/p)==h
    assert not any((PRIVATE/f'{a}_STARTED.json').exists() or (PRIVATE/f'{a}_COMPLETE.json').exists() for a in ARMS),'SINGLE_EXECUTION_ALREADY_STARTED_STOP'
    stream=rows(PRIVATE/'CURRENT_SIZING_RUNTIME.jsonl.gz');books={r['entry_id']:r for r in rows(MAIN/'inputs/execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};tt=tables();results={}
    for arm in ARMS:
        save(PRIVATE/f'{arm}_STARTED.json',{'exact_jst':now(),'claim_sha256':sha(OUT/'MAIN_REPLAY_CLAIM.json'),'actual_claim_commit':receipt['actual_HEAD'],'single_execution':True,'rerun_allowed':False})
        r,ds,tr,cu,it=run(arm,stream,books,tt)
        for name,data in [('DECISIONS',ds),('TRADES',tr),('CURVE',cu),('INTENTS',it),('DAILY',r['daily_series']),('ROLLING20',r.get('rolling20_windows',[]))]:gzsave(PRIVATE/f'{arm}_{name}.jsonl.gz',data)
        r['ledger_sha256']={name:sha(PRIVATE/f'{arm}_{name}.jsonl.gz') for name in ('DECISIONS','TRADES','CURVE','INTENTS','DAILY','ROLLING20')};save(OUT/f'{arm}_RESULT.json',r)
        save(PRIVATE/f'{arm}_COMPLETE.json',{'exact_jst':now(),'primary_result_sha256':sha(OUT/f'{arm}_RESULT.json'),'ledgers':r['ledger_sha256'],'status':r.get('measurement_status','COMPLETE')});results[arm]=r
        print(json.dumps({k:r.get(k) for k in ('profile','funded_N','rolling20_median','rolling20_arithmetic_mean','geometric_mean_daily_return','final_equity','max_drawdown')}),flush=True)
        assert r.get('valid_primary_day_N')==38 and r.get('blocked_execution_day_N')==0,'SHARED_EXECUTION_FAILURE_STOP_NO_REPLAY'
    save(OUT/'MAIN_REPLAY_RESULT.json',{'exact_jst':now(),'arms':results,'primary_replays':2,'S1_replay':1,'S2_replay':1,'saved_control_replays':0,'newFits':0,'claim_sha256':sha(OUT/'MAIN_REPLAY_CLAIM.json'),'Safety':SAFETY});checkpoint('M10_S1_S2_REPLAY_COMPLETE',{'primary_replays':2,'arms':{a:'COMPLETE' for a in ARMS}},'Read-only quality retention / paired sizing delta')
if __name__=='__main__':main()
