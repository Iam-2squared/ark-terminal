"""Resume after P2's saved rows/counts. Reaggregate downstream; never draw a new sample."""
from context import *
from qualify import screen
from collections import defaultdict

def main():
    failure=json.loads((OUT/'failures/P2_SERIALIZATION_001.json').read_text())
    for name,h in failure['saved_intermediates'].items():assert sha(PRIVATE/name)==h
    joined=[json.loads(x) for x in gzip.open(PRIVATE/'PAST_SUPPORT_JOINED_ROWS.jsonl.gz','rt')]
    counts=[json.loads(x) for x in gzip.open(PRIVATE/'PAST_BOOTSTRAP_SESSION_COUNTS.jsonl.gz','rt')]
    groups=defaultdict(list)
    for c in counts:groups[c['block']].append(c)
    split=read('split');block_of={s:b['block'] for b in split['blocks'] for s in b['test']};tables=[];comparisons=0
    for b in split['blocks']:
        number=b['block'];first=min(b['test']);frame=[s for s in split['OOF38'] if block_of[s]<number]
        S=[{k:v for k,v in r.items() if k not in ('target_block','cohort')} for r in joined if r['target_block']==number and r['cohort']=='S']
        F=[{k:v for k,v in r.items() if k not in ('target_block','cohort')} for r in joined if r['target_block']==number and r['cohort']=='F']
        saved=groups[number]
        assert not saved or (len(saved)==1999 and all(r['frame']==frame and r['resample']==i for i,r in enumerate(saved)))
        table,recalc=screen(number,frame,S,F,bootstrap_counts=[r['counts'] for r in saved])
        for old,new in zip(saved,recalc):
            assert old['counts']==new['counts'] and old['frame']==new['frame'] and old['mean']==new['mean'];comparisons+=1
        table.update(first_current_block_session=first,table_available_before=first+'T09:00:00+09:00',
            original_prior_blocks=list(range(1,number)),original_block_split_hash=sha(INPUT/ROLES['split']),
            proposal_manifest_sha256=sha(OUT/'PAST_PROPOSAL_MANIFEST.json'),
            original_input_hashes={role:sha(INPUT/ROLES[role]) for role in ('packet','reference32','proposals','teachers','outcomes','native_trades')},
            current_or_future_outcome_inputs=0,warmup_OOF_samples=0,training_resub_OOF_samples=0)
        tables.append(table)
    qualification={'schema':'V5_R_PAST_QUALIFICATION_BY_BLOCK_V1','exact_jst':now(),'tables':tables,
        'PAST_QUALIFIED_block_N':sum(t['PAST_QUALIFIED'] for t in tables),'table_generation_N':8,
        'serialization_recovery_from_saved_counts':True,'new_bootstrap_draws_during_recovery':0,
        'policy_cutoffs_unchanged':True,'bootstrap_counts_artifact':'private/PAST_BOOTSTRAP_SESSION_COUNTS.jsonl.gz',
        'bootstrap_counts_sha256':sha(PRIVATE/'PAST_BOOTSTRAP_SESSION_COUNTS.jsonl.gz'),
        'joined_artifact':'private/PAST_SUPPORT_JOINED_ROWS.jsonl.gz','joined_sha256':sha(PRIVATE/'PAST_SUPPORT_JOINED_ROWS.jsonl.gz'),
        'proposal_collection_population_N':24,'new_portfolio_replays':0,
        'primary_status_if_pre_main_pass':'PAST_SUPPORT_NOT_ESTABLISHED' if not any(t['PAST_QUALIFIED'] for t in tables) else 'CONTINUE_TO_PREMAIN_FIRST_DIVERGENCE'}
    save('PAST_QUALIFICATION_BY_BLOCK.json',qualification)
    save('P2_SERIALIZATION_REPAIR_RECEIPT.json',{'schema':'V5_R_P2_PURE_SERIALIZATION_REPAIR_V1','exact_jst':now(),
        'failure_receipt_sha256':sha(OUT/'failures/P2_SERIALIZATION_001.json'),'fixed_code_sha256':sha(CODE/'qualify.py'),
        'resume_code_sha256':sha(CODE/'repair_qualification_serialization.py'),'saved_count_means_exact_checks':comparisons,
        'new_draws':0,'new_outcome_joins':0,'S_or_F_population_change':0,'policy_or_gate_changes':0,
        'strict_H3_test_unchanged':'CI lower >0; bool conversion preserves numpy truth value',
        'original_failed_evidence_preserved':True,'new_market_replays':0})
    checkpoint('P2','PAST_TABLES_FIXED',{'table_N':8,'qualified_block_N':qualification['PAST_QUALIFIED_block_N'],
        'serialization_recovery_saved_count_checks':comparisons,'new_draws':0,
        'by_block':[{'block':t['block'],'S_N':t['S']['total_N'],'F_N':t['F']['total_N'],'failed_Hi':t['failed_Hi']} for t in tables]},
        'Independent table/bootstrap/quantity verification and28 synthetic cases; no market Replay')
    print(json.dumps({'qualified_block_N':qualification['PAST_QUALIFIED_block_N'],
      'tables':[{'block':t['block'],'status':t['status'],'S_N':t['S']['total_N'],'F_N':t['F']['total_N'],
       'mean':t['metrics']['mean_S_net_return'],'CI95':t['metrics']['bootstrap_CI95'],'fail':t['failed_Hi'],
       'unknown_S':t['S']['unknown_N'],'unknown_F':t['F']['unknown_N']} for t in tables]}))

if __name__=='__main__':main()
