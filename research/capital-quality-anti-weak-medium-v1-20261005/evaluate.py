"""Q7-Q9 fixed postfit quality diagnostics; no policy, fit, or score combination."""
import csv
from control import *
from metrics import quality, conditional, decile_rows, bootstrap, ordinal, primary_gates, decision

def main():
    assert counts()['total_fits']==16 and not (PRIVATE/'CONTRACT_FAIL.json').exists()
    fitclaim=read(OUT/'FIT_CLAIM.json')
    for name in ['metrics.py','movement_preprocessing.py']:
        assert sha(Path(__file__).parent/name)==fitclaim['code_sha256'][name]
    baseline=read(OUT/'ZERO_FIT_BASELINE_FREEZE.json')
    assert sha(OUT/'ZERO_FIT_BASELINE.json')==baseline['baseline_sha256']
    scores=rows(PRIVATE/'COMMON_SAVED_SCORES.jsonl.gz')
    tt={r['entry_id']:r for r in rows(PRIVATE/'QUALITY_TEACHERS_EVAL.jsonl.gz')}
    predictions=rows(PRIVATE/'NEW_HEAD_OOF_PREDICTIONS.jsonl.gz')
    pm={(r['head'],r['entry_id']):r for r in predictions};assert len(pm)==len(predictions)==2078
    data=[]
    for r in scores:
        row={**r,**tt[r['entry_id']]}
        for head in ['MOVE_U2','MOVE_U3']:
            p=pm[(head,r['entry_id'])];assert p['session']==r['session'] and p['block']==r['block']
            row[head]=p['probability']
        data.append(row)
    assert len(data)==1028
    deciles=decile_rows(data)
    assert deciles=={r['entry_id']:r['pP_decile'] for r in rows(PRIVATE/'P_P_DECILES_OUTCOME_FREE.jsonl.gz')}
    gzsave(PRIVATE/'QUALITY_COMMON_EVAL_ROWS.jsonl.gz',data)
    names=['CORE_H2','CORE_H3','pP','legacy_ML','MOVE_U2','MOVE_U3']
    mm={s:quality(data,s) for s in names}
    cc={t:{s:conditional(data,s,t,deciles) for s in names} for t in ['U2','U3']}
    bb={}
    for head,control,target in [('MOVE_U2','CORE_H2','U2'),('MOVE_U3','CORE_H3','U3')]:
        print(json.dumps({'bootstrap_started':head,'session_clusters':38,'resamples':1999}),flush=True)
        bb[head]=bootstrap(data,head,control,target,deciles)
        print(json.dumps({'bootstrap_complete':head,'AUC_delta_CI':bb[head]['AUC_delta']}),flush=True)
    u2=primary_gates(mm,cc['U2'],bb['MOVE_U2'],'MOVE_U2','CORE_H2','U2','A')
    u3=primary_gates(mm,cc['U3'],bb['MOVE_U3'],'MOVE_U3','CORE_H3','U3','M')
    primary={'exact_jst':now(),'N':1028,'metrics':mm,'AntiWeak':u2,'MediumPlus':u3,
        'bootstrap':bb,'integrity_status':'PENDING_INDEPENDENT_AUDIT','realized_PnL':'diagnostic only',
        'candidate_budgets_fixed':True,'combined_score_created':0,'CapitalReplay':0,'MAX3Replay':0}
    save(OUT/'PRIMARY_QUALITY_EVAL.json',primary)
    columns=['score','fraction','selected_N','below2_N','below2_rate','below3_N','below3_rate','Medium_N','U5_N','U10_N','U3_capture','U5_capture','U10_capture']
    with (OUT/'FIXED_BUDGET_QUALITY.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for name in names:
            for top in mm[name]['top']:
                if top['fraction'] in [.20,.30,.40]:writer.writerow({'score':name,**{k:top[k] for k in columns[1:]}})
    checkpoint('Q7_PRIMARY_QUALITY_EVAL','COMPLETE',['U2/U3 AUC/PR, block stability and fixed Top/Bottom budgets evaluated',
        'Paired session-cluster bootstrap completed; no retuning'],
        {'AntiWeak_point_gate_PASS':u2['point_gate_PASS'],'MediumPlus_point_gate_PASS':u3['point_gate_PASS'],
        'AntiWeak_AUC_delta':u2['AUC_delta'],'MediumPlus_AUC_delta':u3['AUC_delta']},'Q8 pP-conditional incremental and same-session diagnostics')
    conditional_result={'exact_jst':now(),'N':1028,'deciles_sha256':sha(PRIVATE/'P_P_DECILES_OUTCOME_FREE.jsonl.gz'),
        'boundary':'per supported test block; equal-count pP rank bins; outcome-free',
        'aggregation':'valid positive-negative pair weighted','bootstrap_unit':'session','pair_N_is_not_independent_sample_N':True,
        'results':cc,'bootstrap_deltas':{h:{k:v for k,v in b.items() if k in ['pP_conditional','same_session','same_session_pP_conditional']} for h,b in bb.items()}}
    save(OUT/'P_P_CONDITIONAL_INCREMENTAL.json',conditional_result)
    same_session={t:{s:{k:c[k] for k in ['same_session','same_session_pP_conditional']} for s,c in table.items()} for t,table in cc.items()}
    save(OUT/'SAME_SESSION_CONDITIONAL.json',{'exact_jst':now(),'results':same_session,'bootstrap_unit':'session','pair_independence_claim':False})
    ordinals={s:ordinal(data,s) for s in ['CORE_H2','CORE_H3','pP','MOVE_U2','MOVE_U3']}
    save(OUT/'ORDINAL_QUALITY.json',{'exact_jst':now(),'results':ordinals,'diagnostic_only':True,'result_based_blend':0})
    checkpoint('Q8_P_P_CONDITIONAL_INCREMENTAL','COMPLETE',['pP decile discrimination and same-session/decile pairwise evaluated',
        'Session-cluster bootstrap deltas and five-bucket ordinals reported'],
        {'U2_conditional_delta':u2['conditional_delta'],'U3_conditional_delta':u3['conditional_delta'],
        'pairs_as_independent_samples':False},'Q9 Big/Mega preservation diagnostics only')
    controltop=mm['pP']['top'][2];guards={}
    for head in ['MOVE_U2','MOVE_U3']:
        candidate=mm[head]['top'][2]
        preserved={u:candidate[f'U{u}_capture']>=controltop[f'U{u}_capture'] for u in [5,10]}
        status='BIG_WINNER_PRESERVING' if all(preserved.values()) else 'PARTIAL' if any(preserved.values()) else 'NOT_PRESERVING'
        guards[head]={'budget':.30,'selected_N':candidate['selected_N'],'U5_capture':candidate['U5_capture'],'U10_capture':candidate['U10_capture'],
            'pP_U5_capture':controltop['U5_capture'],'pP_U10_capture':controltop['U10_capture'],
            'U5_preserved':preserved[5],'U10_preserved':preserved[10],'status':status,'diagnostic_only':True}
    save(OUT/'BIG_WINNER_PRESERVATION.json',{'exact_jst':now(),'guards':guards,'selectedBigWinnerRank':'EXISTING_MOVE_P5','rank_replacement_or_blend':0})
    provisional=decision(u2,u3)
    save(OUT/'QUALITY_DECISION_PENDING_AUDIT.json',{'exact_jst':now(),**provisional,'integrity_status':'PENDING',
        'final_decision_fixed':False,'heads_are_auxiliary_only':True})
    checkpoint('Q9_BIG_WINNER_PRESERVATION','COMPLETE',['U5/U10 fixed-budget density/capture preserved as diagnostics',
        'Frozen Big-Winner pP unchanged; no combined score or integration'],
        {'guards':guards,'provisional_quality_status':provisional['qualityStatus']},'Q10 independent audit; no extra fits or evaluations chosen from outcomes')
    print(json.dumps({'AntiWeak':u2,'MediumPlus':u3,'guards':guards,'provisional':provisional}),flush=True)

if __name__=='__main__':main()
