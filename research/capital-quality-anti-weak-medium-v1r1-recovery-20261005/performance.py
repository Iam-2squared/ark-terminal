"""Exactly one precommitted quality package; old metric/gate code unchanged."""
import csv
import sys
import numpy as np
from control import *

HEADS=[('MOVE_U2','CORE_H2','U2','A'),('MOVE_U3','CORE_H3','U3','M')]

def main():
    guard_claim('PERFORMANCE_PRIMARY_EXECUTION_CLAIM',[OUT/'PRIMARY_QUALITY_EVAL.json',PRIVATE/'PERFORMANCE_FULL.json.gz'])
    assert read(OUT/'BASELINE_INDEPENDENT_CERTIFICATION.json')['status']=='PASS'
    audit=read(OUT/'MODEL_ARTIFACT_AUDIT.json');assert audit['status']=='PASS'
    assert sha(PRIVATE/'QUALITY_COMMON_EVAL_ROWS_V1R1.jsonl.gz')==audit['joined_artifact']['sha256']
    data=rows(PRIVATE/'QUALITY_COMMON_EVAL_ROWS_V1R1.jsonl.gz');assert len(data)==1028 and data==sorted(data,key=key)
    m=old_metrics();dec=m.decile_rows(data)
    assert dec=={r['entry_id']:r['pP_decile'] for r in rows(OLD_WORK/'private/P_P_DECILES_OUTCOME_FREE.jsonl.gz')}
    baseline=json.loads(gzip.decompress((PRIVATE/'BASELINE_METRICS_FULL.json.gz').read_bytes()))
    # Frozen baseline results are reused, not rebuilt a second time.
    mm=baseline['metrics'];cc=baseline['conditional']
    for head,_,_,_ in HEADS:
        mm[head]=m.quality(data,head)
        for t in ['U2','U3']:cc[t][head]=m.conditional(data,head,t,dec)
    bb={};samples={}
    for head,control,target,_ in HEADS:
        print(json.dumps({'bootstrap_started':head,'resamples':1999,'seed':5701005,'unit':'session'}),flush=True)
        captured=[]
        def capture(frame,event,arg):
            # Read-only observation of frozen interval() inputs; no code/config change.
            if event=='call' and frame.f_code is m.interval.__code__:
                captured.append([float(v) for v in frame.f_locals['values']])
        prior=sys.getprofile();sys.setprofile(capture)
        try:bb[head]=m.bootstrap(data,head,control,target,dec)
        finally:sys.setprofile(prior)
        keys=['AUC_delta','PR_AUC_delta','pP_conditional','same_session','same_session_pP_conditional']
        assert len(captured)==5 and all(len(v)==1999 for v in captured)
        samples[head]=dict(zip(keys,captured))
        print(json.dumps({'bootstrap_completed':head,'AUC_CI':bb[head]['AUC_delta']}),flush=True)
    sessions=sorted({r['session'] for r in data});rng=np.random.default_rng(5701005)
    draws=[rng.integers(0,len(sessions),len(sessions)).tolist() for _ in range(1999)]
    draw_body=b''.join(canonical(x) for x in draws);drawsha=hashlib.sha256(draw_body).hexdigest()
    u2=m.primary_gates(mm,cc['U2'],bb['MOVE_U2'],'MOVE_U2','CORE_H2','U2','A')
    u3=m.primary_gates(mm,cc['U3'],bb['MOVE_U3'],'MOVE_U3','CORE_H3','U3','M')
    ordinal={s:m.ordinal(data,s) for s in ['CORE_H2','CORE_H3','pP','MOVE_U2','MOVE_U3']}
    guards={};p=mm['pP']['top'][2]
    for h,_,_,_ in HEADS:
        c=mm[h]['top'][2];v5=c['U5_capture']>=p['U5_capture'];v10=c['U10_capture']>=p['U10_capture']
        guards[h]={'budget':.3,'selected_N':c['selected_N'],'U5_capture':c['U5_capture'],'U10_capture':c['U10_capture'],
            'pP_U5_capture':p['U5_capture'],'pP_U10_capture':p['U10_capture'],'U5_preserved':v5,'U10_preserved':v10,
            'status':'BIG_WINNER_PRESERVING' if v5 and v10 else 'PARTIAL' if v5 or v10 else 'NOT_PRESERVING','diagnostic_only':True}
    decision=m.decision(u2,u3,True)
    primary={'N':1028,'metrics':mm,'AntiWeak':u2,'MediumPlus':u3,'bootstrap':bb,
        'session_draw_stream_sha256':drawsha,'session_order_sha256':hashlib.sha256(canonical(sessions)).hexdigest(),
        'integrity_status':'PENDING_INDEPENDENT_PERFORMANCE_AUDIT','realized_PnL':'diagnostic only',
        'candidate_budgets_fixed':True,'combined_score_created':0,'newFits':0,'CapitalReplay':0,'MAX3Replay':0}
    full={'primary':primary,'conditional':cc,'ordinal':ordinal,'guards':guards,'provisional_decision':decision}
    artifacts=[gzsave(PRIVATE/'PERFORMANCE_FULL.json.gz',full),
        gzsave(PRIVATE/'PERFORMANCE_CONDITIONAL_GROUPS.jsonl.gz',[
            {'target':t,'score':s,'variant':v,**g} for t in ['U2','U3'] for s in mm
            for v in ['pP_conditional','same_session','same_session_pP_conditional'] for g in cc[t][s][v]['groups']],True),
        gzsave(PRIVATE/'BOOTSTRAP_RESAMPLE_VALUES.json.gz',samples),
        gzsave(PRIVATE/'BOOTSTRAP_SESSION_DRAWS.jsonl.gz',draws,True)]
    save(OUT/'PRIMARY_QUALITY_EVAL.json',primary)
    save(OUT/'P_P_CONDITIONAL_INCREMENTAL.json',{'N':1028,'results':compact_conditionals(cc),'bootstrap_unit':'session',
        'fixed_outcome_free_pP_deciles':True,'pair_N_is_not_independent_sample_N':True,
        'bootstrap_deltas':{h:{k:bb[h][k] for k in ['pP_conditional','same_session','same_session_pP_conditional']} for h,_,_,_ in HEADS}})
    save(OUT/'SAME_SESSION_CONDITIONAL.json',{'N':1028,'results':{t:{s:{k:v for k,v in table[s].items()
        if k in ['same_session','same_session_pP_conditional']} for s in table} for t,table in compact_conditionals(cc).items()},
        'bootstrap_unit':'session','pairs_are_not_independent_samples':True})
    save(OUT/'ORDINAL_QUALITY.json',{'results':ordinal,'diagnostic_only':True,'result_based_blend':0})
    save(OUT/'BIG_WINNER_PRESERVATION.json',{'guards':guards,'selectedBigWinnerRank':'EXISTING_MOVE_P5','rank_replacement_or_blend':0})
    save(OUT/'QUALITY_DECISION_PENDING_AUDIT.json',{**decision,'integrity_status':'PENDING','final_decision_fixed':False,'heads_are_auxiliary_only':True})
    root={'N':1028,'metric_code_sha256':METRIC_HASH,'joined_rows_sha256':audit['joined_artifact']['sha256'],
        'private_artifacts':artifacts,'public_sha256':{p:sha(OUT/p) for p in ['PRIMARY_QUALITY_EVAL.json',
        'P_P_CONDITIONAL_INCREMENTAL.json','SAME_SESSION_CONDITIONAL.json','ORDINAL_QUALITY.json','BIG_WINNER_PRESERVATION.json','QUALITY_DECISION_PENDING_AUDIT.json']},
        'session_draw_stream_sha256':drawsha,'performance_packages':1,'newFits':0,'refits':0,'auditRefits':0}
    save(OUT/'PERFORMANCE_ARTIFACT_ROOT.json',root)
    columns=['score','fraction','selected_N','below2_N','below2_rate','below3_N','below3_rate','Medium_N','U5_N','U10_N','U3_capture','U5_capture','U10_capture']
    with (OUT/'FIXED_BUDGET_QUALITY.csv').open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for score,q in mm.items():
            for t in q['top'][1:]:writer.writerow({'score':score,**{k:t[k] for k in columns[1:]}})
    checkpoint('R7_ANTI_WEAK_MEDIUM_PRIMARY_EVAL',['one primary quality package completed; frozen metrics/gates; 1999 paired session resamples per head'],
        {'AntiWeak':u2,'MediumPlus':u3,'performance_packages':1,'newFits':0},'R8 publish pP conditional and same-session results from this same package')
    checkpoint('R8_P_P_CONDITIONAL_AND_SAME_SESSION',['fixed outcome-free pP deciles, pair-weighted conditional and same-session diagnostics'],
        {'U2_conditional_delta':u2['conditional_delta'],'U3_conditional_delta':u3['conditional_delta'],
        'bootstrap_unit':'session','pair_independence_claim':False},'R9 publish ordinal and Big/Mega guards from this same package')
    checkpoint('R9_ORDINAL_AND_BIG_WINNER_GUARD',['five-bucket percentile/NDCG and Top30 U5/U10 preservation diagnostics'],
        {'guards':guards,'pending_decision':decision,'pP_unchanged':True},'R10 independent full performance audit; no additional result-driven evaluation')
    print(json.dumps({'AntiWeak':u2,'MediumPlus':u3,'guards':guards,'provisional':decision}),flush=True)

if __name__=='__main__':main()
