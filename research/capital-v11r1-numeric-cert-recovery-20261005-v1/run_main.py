"""Exactly one Primary chain per frozen arm, after actual GET of Main claim."""
from control import *
from replay import run
def main():
    claim=read(OUT/'MAIN_REPLAY_CLAIM.json');receipt=read(WORK/'publication_receipts/N12_MAIN_REPLAY_CLAIM_ACTUAL_GET.json')
    assert claim['M1_replay']==claim['M2_replay']==1 and claim['primary_replays']==2 and receipt['actual_GET_verified']
    for p,h in claim['code_sha256'].items():assert sha(ROOT/p)==h,'CLAIMED_CODE_CHANGED'
    for p,h in claim['input_sha256'].items():assert sha(ROOT.parent/p)==h,'CLAIMED_INPUT_CHANGED'
    assert not any((PRIVATE/f'{a}_STARTED.json').exists() or (PRIVATE/f'{a}_COMPLETE.json').exists() for a in ARMS),'SINGLE_EXECUTION_STARTED_NO_REPLAY'
    stream=rows(PRIVATE/'CURRENT_MRET_CAP_RUNTIME.jsonl.gz');books={r['entry_id']:r for r in rows(MAIN/'inputs/execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};tables=read(PRIVATE/'PRIMARY_I2_PAST_TABLES.json');results={}
    for arm in ARMS:
        save(PRIVATE/f'{arm}_STARTED.json',{'exact_jst':now(),'claim_sha256':sha(OUT/'MAIN_REPLAY_CLAIM.json'),'actual_claim_commit':receipt['HEAD'],'single_execution':True,'rerun_allowed':False})
        result,ds,tr,cu,it=run(arm,stream,books,tables)
        for name,data in [('DECISIONS',ds),('TRADES',tr),('CURVE',cu),('INTENTS',it),('DAILY',result['daily_series']),('ROLLING20',result.get('rolling20_windows',[]))]:gzsave(PRIVATE/f'{arm}_{name}.jsonl.gz',data)
        result['ledger_sha256']={name:sha(PRIVATE/f'{arm}_{name}.jsonl.gz') for name in ('DECISIONS','TRADES','CURVE','INTENTS','DAILY','ROLLING20')};save(OUT/f'{arm}_RESULT.json',result)
        save(PRIVATE/f'{arm}_COMPLETE.json',{'exact_jst':now(),'result_sha256':sha(OUT/f'{arm}_RESULT.json'),'ledgers':result['ledger_sha256'],'status':result.get('measurement_status','COMPLETE')});results[arm]=result
        print(json.dumps({k:result.get(k) for k in ['profile','funded_N','rolling20_median','rolling20_arithmetic_mean','geometric_mean_daily_return','final_equity','max_drawdown']}),flush=True)
        assert result.get('valid_primary_day_N')==38 and result.get('blocked_execution_day_N')==0,'EXECUTION_FAILURE_STOP_NO_REPLAY'
    save(OUT/'MAIN_REPLAY_RESULT.json',{'exact_jst':now(),'arms':results,'primary_replays':2,'M1_replay':1,'M2_replay':1,'saved_control_replays':0,'newFits':0,'claim_sha256':sha(OUT/'MAIN_REPLAY_CLAIM.json'),'Safety':SAFETY})
    checkpoint('N13_M1_M2_REPLAY_COMPLETE',{'primary_replays':2,'M1':'COMPLETE','M2':'COMPLETE'},'Read-only Quality retention / exposure / Capital evaluation')
if __name__=='__main__':main()
