import sys
from io_utils import *
from reset20 import run_batch

if __name__=='__main__':
    profile=sys.argv[1];allocator=None
    assert profile in ['V5_RESET20','V51_RESET20']
    if profile=='V51_RESET20':
        from v51_allocation import allocation as allocator
        pre=read(OUT/'V51_POLICY_PRECOMMIT.json')
        assert pre['candidate_id']=='V5.1' and pre['candidate_N']==1
        assert sha(Path(__file__).with_name('v51_allocation.py'))==pre['code_hashes']['v51_allocation.py']
        receipt=read(OUT/'V51_PRECOMMIT_READBACK.json')
        assert receipt['verified'] and receipt['precommit_sha256']==sha(OUT/'V51_POLICY_PRECOMMIT.json'),'GitHub precommit receipt required before candidate replay'
    stream=rows(INPUTS/'candidate_stream');books={r['entry_id']:r for r in rows(INPUTS/'books')};tables=read(INPUTS/'arrival')
    if profile=='V51_RESET20':
        scores={r['entry_id']:r for r in rows(INPUTS/'c7e10944822c_CURRENT_MRET_CAP_RUNTIME.jsonl.gz')}
        for row in stream:
            score=scores[row['entry_id']]
            assert all(row[k]==score[k] for k in ['entry_id','session','symbol','entry_minute','entry_timestamp','block','raw_reference'])
            row['lot_priority_pP']=score['pP']
    result=run_batch(profile,read(OUT/'COVERAGE_AND_WINDOWS.json'),stream,books,tables,allocator)
    checkpoint(profile+'_BATCH_COMPLETE',result['summary']['measurement_status'],'Independently audit raw-source accounting and join R labels',{'formal_batches':1,'window_attempts':result['window_attempt_N'],'day_attempts':result['day_attempt_N']},result['summary'])
    print(result['summary'])
