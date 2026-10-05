"""Single post-fit evaluation; the complete evaluation never runs twice."""
from control import *
from metrics import *
def point_gate(results,best,boot):
    a=results['mP'];c=results[best]
    improved=sum(a['blocks'][str(b)]['AUC']>c['blocks'][str(b)]['AUC'] for b in range(1,9))
    catastrophic=[b for b in range(1,9) if c['blocks'][str(b)]['AUC']>=.5 and a['blocks'][str(b)]['AUC']<.5 and a['blocks'][str(b)]['AUC']-c['blocks'][str(b)]['AUC']<=-.10]
    g={'S1':a['MRET']['AUC']>c['MRET']['AUC'],'S2':a['MRET']['PR_AUC']>c['MRET']['PR_AUC'],'S3':a['conditional']['concordance']>c['conditional']['concordance'],'S4':a['conditional']['concordance']>.5,'S5':a['realized']['positive_AUC']>c['realized']['positive_AUC'],'S6':improved>=5,'S7':not catastrophic,'S8':boot['deltas']['MRET_AUC_delta']['CI95'][0]>0}
    return {'best_existing_control':best,'conditions_before_independent_audit':g,'block_improved_N':improved,'catastrophic_blocks':catastrophic,'S9':'PENDING_INDEPENDENT_SIGNAL_AUDIT','adoption':False}
def main():
    assert read(OUT/'MRET_8_FITS_RESULT.json')['fits']==8
    save(PRIVATE/'claims/R7_EVALUATION_STARTED.json',{'exact_jst':now(),'basis':read(WORK/'latest_basis.json'),'resamples':1999,'reexecution_allowed':False})
    scores={r['entry_id']:r for r in rows(PRIVATE/'MRET_OOF_SCORES.jsonl.gz')}
    rr=[r|{'mP':scores[r['entry_id']]['mP']} for r in rows(PRIVATE/'MRET_EVALUATION_ROWS.jsonl.gz')]
    controls=read(OUT/'ZERO_FIT_MRET_CONTROL_RESULT.json');best=controls['best_existing_control'];results=controls['controls']|{'mP':summary(rr,'mP')}
    sessions=read(SPLIT)['OOF38'];assert len(sessions)==38 and set(r['session'] for r in rr)==set(sessions)
    boot,samples,cc=bootstrap(rr,best,sessions)
    gzsave(PRIVATE/'MRET_POST_FIT_EVALUATION_ROWS.jsonl.gz',rr);gzsave(PRIVATE/'SESSION_BOOTSTRAP_DELTAS.jsonl.gz',samples)
    gzsave(PRIVATE/'SESSION_BOOTSTRAP_COUNTS.jsonl.gz',[{'resample':i+1,'counts':c.tolist()} for i,c in enumerate(cc)])
    save(OUT/'MRET_PRIMARY_RESULT.json',{'scores':results,'best_existing_control':best,'OOF_N':len(rr),'raw_logistic_ordering_score':'not true probability','newFits':8,'performance_evaluations':1,'Safety':SAFETY})
    save(OUT/'SESSION_BOOTSTRAP_RESULT.json',boot)
    save(OUT/'POTENTIAL_BUCKET_REALIZED_CONCORDANCE.json',{'bucket_block':{s:r['conditional'] for s,r in results.items()},'same_session_bucket':{s:r['same_session_conditional'] for s,r in results.items()},'bootstrap_unit':'session','pair_N_not_independent_sample_N':True})
    diagnostic={}
    for name,q in [('whole_common',rr),('I2_admission',[r for r in rr if r['admitted']]),('I2_funded',[r for r in rr if r['I2_funded']])]:
        diagnostic[name]={'N':len(q),'scores':{s:{'positive_AUC':binary([int(r['realized']>0) for r in q],[r[s] for r in q])['AUC'],'ge1_AUC':binary([int(r['realized']>=.01) for r in q],[r[s] for r in q])['AUC'],'loser_AUC':binary([int(r['realized']<=0) for r in q],[r[s] for r in q])['AUC'],'Spearman':float(spearmanr([r[s] for r in q],[r['realized'] for r in q]).statistic)} for s in SCORES+['mP']}}
    save(OUT/'FROZEN_EXIT_REALIZED_DIAGNOSTICS.json',diagnostic)
    gate=point_gate(results,best,boot);save(OUT/'MRET_POINT_GATE_PENDING_INDEPENDENT_AUDIT.json',gate)
    save(PRIVATE/'claims/R7_EVALUATION_COMPLETE.json',{'exact_jst':now(),'results_sha256':sha(OUT/'MRET_PRIMARY_RESULT.json'),'bootstrap_sha256':sha(OUT/'SESSION_BOOTSTRAP_RESULT.json'),'resamples':1999,'reexecution_allowed':False})
    checkpoint('R7_MRET_PRIMARY_AND_CONDITIONAL_EVAL',gate,'R8 independent raw reconstruction, no optimizer refit')
    print(json.dumps({'scores':{s:{'AUC':r['MRET']['AUC'],'PR':r['MRET']['PR_AUC'],'concordance':r['conditional']['concordance'],'realized_positive_AUC':r['realized']['positive_AUC']} for s,r in results.items()},'bootstrap':boot['deltas'],'point_gate':gate}))
if __name__=='__main__':main()
