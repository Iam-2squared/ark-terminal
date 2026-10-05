"""Freeze all policy inputs/code and issue a single-execution claim."""
from control import *
def main():
    assert read(OUT/'CAUSAL_CANARY_RESULTS.json')['all_PASS']
    assert read(OUT/'PRE_MAIN_INDEPENDENT_SIZING_AUDIT.json')['mismatch_N']==0
    assert not any((PRIVATE/f'{a}_STARTED.json').exists() for a in ARMS)
    inputs=[PRIVATE/'CURRENT_SIZING_RUNTIME.jsonl.gz',PRIVATE/'SIZING_TRAIN_SCORE_TABLE.jsonl.gz',PRIVATE/'INDEPENDENT_CURRENT_SIZING_RUNTIME.jsonl.gz',PRIVATE/'INDEPENDENT_PAST_TABLES.json',PRIVATE/'INDEPENDENT_TRAIN_SCORE_TABLE.jsonl.gz',MAIN/'inputs/execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz']
    code={str(p.relative_to(ROOT)):sha(p) for p in CODE.glob('*.py')};code.update(read(OUT/'V9_PARENT_AUTHORITY_FREEZE.json')['frozen_parent_source_sha256'])
    public=['SIZING_DESIGN_PRECOMMIT.json','SIZING_PERCENTILE_RUNTIME_FREEZE.json','CAUSAL_CANARY_RESULTS.json','PRE_MAIN_INDEPENDENT_SIZING_AUDIT.json']
    code.update({str((OUT/f).relative_to(ROOT)):sha(OUT/f) for f in public})
    save(OUT/'MAIN_REPLAY_CLAIM.json',{'exact_jst':now(),'S1_replay':1,'S2_replay':1,'primary_replays':2,'control_replays':0,'newFits':0,'single_execution':True,'interrupted_or_ambiguous_rerun_allowed':False,'code_sha256':code,'input_sha256':{str(p.relative_to(ROOT.parent)):sha(p) for p in inputs},'Safety':SAFETY})
    checkpoint('M9_MAIN_REPLAY_CLAIM',{'S1':1,'S2':1,'total_primary_replay_budget':2,'actual_GET_required':True},'Actual GET claim then execute both arms exactly once')
if __name__=='__main__':main()
