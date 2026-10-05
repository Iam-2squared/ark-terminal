"""Audit checkpoint and single-execution claim; run needs an actual GET receipt."""
from control import *
import sys
def audited():
    a=read(OUT/'PRE_MAIN_INDEPENDENT_POLICY_AUDIT.json');assert a['status']=='PASS' and a['mismatch_N']==0 and a['numeric_boundary_disagreement_N']==0
    assert read(OUT/'CAUSAL_CANARY_RESULTS.json')['all_PASS']
    checkpoint('V7_PRE_MAIN_INDEPENDENT_AUDIT',{'mismatch_N':0,'checks_N':a['checks_N'],'action_cases_N':a['action_cases_N'],'numeric_boundary_disagreement_N':0,'Primary_imports':0},'Commit single-execution claim, actual GET, then run I1/I2 each once')
def claimed():
    assert (OUT/'receipts/V7_PRE_MAIN_INDEPENDENT_AUDIT_ACTUAL_GET.json').exists()
    assert not any((PRIVATE/f'{a}_STARTED.json').exists() for a in ARMS)
    code={str(p.relative_to(ROOT)):sha(p) for p in CODE.glob('*.py')}
    for path,h in read(OUT/'FROZEN_CODE_AND_TABLE_AUTHORITY.json')['parent_hashes'].items():assert sha(ROOT/path)==h;code[path]=h
    inp={str(p.relative_to(ROOT.parent)):sha(p) for folder in [MAIN,QUALITY] for p in folder.rglob('*') if p.is_file()}
    for name in ['CURRENT_CAUSAL_QUALITY_RUNTIME.jsonl.gz','QUALITY_TRAIN_SCORE_TABLE.jsonl.gz','I1_I2_PRESSURE_SUPPORT_STATES.jsonl.gz','INDEPENDENT_CURRENT_RUNTIME.jsonl.gz','INDEPENDENT_TRAIN_SCORES.jsonl.gz','INDEPENDENT_PAST_TABLES.json']:inp[str((PRIVATE/name).relative_to(ROOT.parent))]=sha(PRIVATE/name)
    save(OUT/'MAIN_REPLAY_CLAIM.json',{'exact_jst':now(),'branch':BRANCH,'basis':read(WORK/'latest_basis.json'),'Main_parent_SHA':MAIN_SHA,'Quality_parent_SHA':QUALITY_SHA,'I1_replay':1,'I2_replay':1,'primary_replays':2,'saved_control_replays':0,'newFits':0,'single_execution':True,'ambiguous_crash_rerun_allowed':False,'code_sha256':code,'input_sha256':inp,'pre_audit_sha256':sha(OUT/'PRE_MAIN_INDEPENDENT_POLICY_AUDIT.json'),'canary_sha256':sha(OUT/'CAUSAL_CANARY_RESULTS.json'),'Safety':SAFETY})
    checkpoint('V8_MAIN_REPLAY_CLAIM',{'I1_replay':1,'I2_replay':1,'total_budget':2,'code_frozen':len(code),'inputs_frozen':len(inp)},'After actual GET receipt only, run exactly once per policy')
def full():
    a=read(OUT/'INDEPENDENT_AUDIT.json')
    checkpoint('V12_FULL_INDEPENDENT_AUDIT',{'status':a['status'],'mismatch_N':a['mismatch_N'],'checks_N':a['checks_N'],'max_abs_float_difference':a['max_abs_float_difference'],'money_quantity_exact':a['money_quantity_exact']},'Fixed winner/diagnostic arm/bottleneck; no tuning or new replay')
if __name__=='__main__':{'audit':audited,'claim':claimed,'full':full}[sys.argv[1]]()
