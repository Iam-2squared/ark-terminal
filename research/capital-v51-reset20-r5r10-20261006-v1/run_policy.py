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
        assert pre.get('github_precommit_verified') is True,'GitHub precommit receipt required before candidate replay'
    stream=rows(INPUTS/'candidate_stream');books={r['entry_id']:r for r in rows(INPUTS/'books')};tables=read(INPUTS/'arrival')
    result=run_batch(profile,read(OUT/'COVERAGE_AND_WINDOWS.json'),stream,books,tables,allocator)
    checkpoint(profile+'_BATCH_COMPLETE',result['summary']['measurement_status'],'Independently audit raw-source accounting and join R labels',{'formal_batches':1,'window_attempts':result['window_attempt_N'],'day_attempts':result['day_attempt_N']},result['summary'])
    print(result['summary'])
