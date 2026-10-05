"""Resume only the unexecuted second arm after a fully recorded M1 fail-closed."""
from control import *
from replay import run
def main():
    claim=read(OUT/'MAIN_REPLAY_CLAIM.json');receipt=read(WORK/'publication_receipts/N12_MAIN_REPLAY_CLAIM_ACTUAL_GET.json')
    assert receipt['actual_GET_verified'] and claim['M1_replay']==claim['M2_replay']==1
    for p,h in claim['code_sha256'].items():assert sha(ROOT/p)==h,'FROZEN_CLAIM_CODE_CHANGED'
    for p,h in claim['input_sha256'].items():assert sha(ROOT.parent/p)==h,'FROZEN_CLAIM_INPUT_CHANGED'
    m1=read(OUT/f'{ARMS[0]}_RESULT.json');done=read(PRIVATE/f'{ARMS[0]}_COMPLETE.json')
    assert done['result_sha256']==sha(OUT/f'{ARMS[0]}_RESULT.json') and m1['measurement_status']=='CAPITAL_MEASUREMENT_BLOCKED_EXECUTION'
    for n,h in m1['ledger_sha256'].items():assert sha(PRIVATE/f'{ARMS[0]}_{n}.jsonl.gz')==h
    assert not (PRIVATE/f'{ARMS[1]}_STARTED.json').exists() and not (PRIVATE/f'{ARMS[1]}_COMPLETE.json').exists(),'M2_ALREADY_STARTED_NO_RETRY'
    arm=ARMS[1];save(PRIVATE/f'{arm}_STARTED.json',{'exact_jst':now(),'claim_sha256':sha(OUT/'MAIN_REPLAY_CLAIM.json'),'actual_claim_commit':receipt['HEAD'],'single_execution':True,'rerun_allowed':False,'first_incomplete_arm':True,'M1_rerun':False})
    stream=rows(PRIVATE/'CURRENT_MRET_CAP_RUNTIME.jsonl.gz');books={r['entry_id']:r for r in rows(MAIN/'inputs/execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};tables=read(PRIVATE/'PRIMARY_I2_PAST_TABLES.json')
    result,ds,tr,cu,it=run(arm,stream,books,tables)
    for name,data in [('DECISIONS',ds),('TRADES',tr),('CURVE',cu),('INTENTS',it),('DAILY',result['daily_series']),('ROLLING20',result.get('rolling20_windows',[]))]:gzsave(PRIVATE/f'{arm}_{name}.jsonl.gz',data)
    result['ledger_sha256']={n:sha(PRIVATE/f'{arm}_{n}.jsonl.gz') for n in ('DECISIONS','TRADES','CURVE','INTENTS','DAILY','ROLLING20')};save(OUT/f'{arm}_RESULT.json',result)
    save(PRIVATE/f'{arm}_COMPLETE.json',{'exact_jst':now(),'result_sha256':sha(OUT/f'{arm}_RESULT.json'),'ledgers':result['ledger_sha256'],'status':result.get('measurement_status','COMPLETE')})
    save(OUT/'MAIN_REPLAY_RESULT.json',{'exact_jst':now(),'arms':{ARMS[0]:m1,arm:result},'primary_replays':2,'M1_replay':1,'M2_replay':1,'saved_control_replays':0,'newFits':0,'M1_reexecution':0,'M2_first_incomplete_resume':True,'claim_sha256':sha(OUT/'MAIN_REPLAY_CLAIM.json'),'both_38_session_complete':all(r.get('valid_primary_day_N')==38 and r.get('blocked_execution_day_N')==0 for r in (m1,result)),'Safety':SAFETY})
    print(json.dumps({k:result.get(k) for k in ['profile','measurement_status','valid_primary_day_N','blocked_execution_day_N','funded_N','rolling20_median','rolling20_arithmetic_mean','geometric_mean_daily_return','final_equity']}),flush=True)
    checkpoint('N13_M1_M2_REPLAY_COMPLETE',{'M1_invocations':1,'M2_invocations':1,'M1_measurement_status':m1['measurement_status'],'M2_measurement_status':result.get('measurement_status','COMPLETE'),'M1_reexecution':0},'Read-only execution-source receipt audit; no incomplete-chain Capital claims')
if __name__=='__main__':main()
