"""Fixed terminal decision before any claim, prefix sweep or market execution."""
from context import *

def main():
    q=json.loads((OUT/'PAST_QUALIFICATION_BY_BLOCK.json').read_text())
    audit=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text())
    pre=json.loads((OUT/'SYNTHETIC_AND_PREMAIN_AUDIT.json').read_text())
    assert len(q['tables'])==8 and not any(t['PAST_QUALIFIED'] for t in q['tables'])
    assert audit['status']=='PASS' and audit['mismatch_N']==0 and pre['status']=='PASS'
    reason='All8 original OOF blocks have PAST_QUALIFIED=false; Section9 fixed STOP, Capital Replay0.'
    save('FIRST_DIVERGENCE_CERTIFICATE.json',{'schema':'V5_R_FIRST_DIVERGENCE_V1','exact_jst':now(),
        'status':'NOT_EXECUTED','reason':reason,'primary_prefix_scan_N':0,'independent_prefix_scan_N':0,
        'first_divergence':None,'NO_EFFECT_PROVEN':False,'no_effect_or_improvement_claim':False,
        'qualification_sha256':sha(OUT/'PAST_QUALIFICATION_BY_BLOCK.json'),
        'instruction_priority':'PAST_SUPPORT_NOT_ESTABLISHED precedes NO_EFFECT_PROVEN; no full-prefix identity assertion made.'})
    save('EXECUTION_DECISION.json',{'schema':'V5_R_FIXED_EXECUTION_DECISION_V1','exact_jst':now(),
        'status':'PAST_SUPPORT_NOT_ESTABLISHED','reason':reason,'candidate_primary_replay_allowed':False,
        'single_replay_claim_created':False,'ambiguous_execution_claim':False,'candidate_primary_replay_N':0,
        'independent_R_reconstruction_N':0,'future_iteration_allowed_same_cycle':False,
        'policy_threshold_support_confidence_scope_changes':0,'Safety':SAFETY,
        'activeCapitalChampion':'V5','selectedCapitalCandidate':None,'selectedResearchCandidate':None,'championUpdated':False,
        'qualification_sha256':sha(OUT/'PAST_QUALIFICATION_BY_BLOCK.json'),
        'pre_main_sha256':sha(OUT/'SYNTHETIC_AND_PREMAIN_AUDIT.json'),'independent_sha256':sha(OUT/'INDEPENDENT_AUDIT.json')})
    checkpoint('P4','CONDITIONAL_EXECUTION_FIXED_STOP',{'status':'PAST_SUPPORT_NOT_ESTABLISHED','qualified_block_N':0,
        'first_divergence_status':'NOT_EXECUTED','primary_prefix_scan_N':0,'independent_prefix_scan_N':0},
        'P5 no execution claim; P6 no R reconstruction; finish retained-ledger report and closure')
    checkpoint('P5','NOT_EXECUTED_FIXED_GATE',{'claim_N':0,'primaryRReplays':0,'reason':reason},
        'No restart or alternate arm; P6 conditional reconstruction skipped')
    checkpoint('P6','NOT_EXECUTED_R_RECONSTRUCTION',{'independentRReconstructions':0,'primaryRReplays':0,
        'saved_case_pre_main_independent_status':'PASS','reason':reason},
        'P7 final saved V5 references, quality diagnostics, gates NOT_EVALUATED, PRIVATE and closure')
    print(json.dumps({'status':'PAST_SUPPORT_NOT_ESTABLISHED','primary_replays':0,'independent_R_reconstructions':0}))

if __name__=='__main__':main()
