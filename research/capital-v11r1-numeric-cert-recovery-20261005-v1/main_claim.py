"""One new-cycle Main claim. No retry or ambiguous receipt recovery by replay."""
from control import *
def main():
    assert read(OUT/'S9R_CERTIFICATION_DECISION.json')['S9R']=='PASS'
    assert read(OUT/'CAUSAL_CANARY_RESULTS.json')['all_PASS']
    assert read(OUT/'PRE_MAIN_INDEPENDENT_CAP_AUDIT.json')['mismatch_N']==0
    assert not any((PRIVATE/f'{a}_STARTED.json').exists() for a in ARMS)
    inputs=[PRIVATE/'CURRENT_MRET_CAP_RUNTIME.jsonl.gz',PRIVATE/'FROZEN_MRET_PERCENTILE_TRAIN_SCORES.jsonl.gz',PRIVATE/'PRIMARY_I2_PAST_TABLES.json',PRIVATE/'INDEPENDENT_CURRENT_MRET_CAP_RUNTIME.jsonl.gz',PRIVATE/'INDEPENDENT_I2_PAST_TABLES.json',PRIVATE/'INDEPENDENT_QUALITY_TRAIN_TABLE.jsonl.gz',MAIN/'inputs/execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz']
    code={str(p.relative_to(ROOT)):sha(p) for p in CODE.glob('*.py')}
    for directory in ['capital-v11-realized-monetization-signal-20261005-v1','capital-v9-quality-aware-max3-integration-20261005-v1','capital-v8r1-cash-constrained-online-max3-20261005-v1','capital-v7-rank-native-max3-20261005-v1','capital-v5-max3-slot-intelligence-20261004-v1']:
        for p in (ROOT/'research'/directory).glob('*.py'):code[str(p.relative_to(ROOT))]=sha(p)
    for name in ['S9R_CERTIFICATION_DECISION.json','M1_M2_POLICY_HASH_FREEZE.json','RUNTIME_MRET_PERCENTILE_FREEZE.json','CAUSAL_CANARY_RESULTS.json','PRE_MAIN_INDEPENDENT_CAP_AUDIT.json','PREPROCESSING_BIT_CERTIFICATION.json']:
        p=OUT/name;code[str(p.relative_to(ROOT))]=sha(p)
    save(OUT/'MAIN_REPLAY_CLAIM.json',{'exact_jst':now(),'M1_replay':1,'M2_replay':1,'primary_replays':2,'control_replays':0,'newFits':0,'single_execution':True,'interrupted_or_ambiguous_rerun_allowed':False,'code_sha256':code,'input_sha256':{str(p.relative_to(ROOT.parent)):sha(p) for p in inputs},'frozen_policy_sha256':sha(PARENT/'M1_M2_CAPITAL_POLICY_PRECOMMIT.json'),'Safety':SAFETY})
    checkpoint('N12_MAIN_REPLAY_CLAIM',{'M1':1,'M2':1,'total_replay_budget':2,'actual_GET_required':True},'Commit -> actual GET -> execute both arms exactly once')
if __name__=='__main__':main()
