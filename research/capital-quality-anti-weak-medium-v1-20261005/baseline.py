"""Q4 zero-fit benchmarks using frozen probabilities/scores on common1028."""
from control import *
from metrics import quality, conditional, decile_rows

def main():
    assert counts()['total_fits']==0
    scores=rows(PRIVATE/'COMMON_SAVED_SCORES.jsonl.gz')
    teachers={r['entry_id']:r for r in rows(PRIVATE/'QUALITY_TEACHERS_EVAL.jsonl.gz')}
    data=[{**r,**teachers[r['entry_id']]} for r in scores]
    deciles=decile_rows(data)
    result={'exact_jst':now(),'stage':'ZERO_FIT_BASELINE_FROZEN','N':len(data),'new_fits':0,
        'metrics':{s:quality(data,s) for s in ['CORE_H2','CORE_H3','pP','legacy_ML']},
        'conditional':{target:{s:conditional(data,s,target,deciles) for s in ['CORE_H2','CORE_H3','pP','legacy_ML']} for target in ['U2','U3']},
        'decile_definition_outcome_reads':0,'future_outcomes_in_X':0,'CapitalReplay':0,'MAX3Replay':0}
    save(OUT/'ZERO_FIT_BASELINE.json',result)
    gzsave(PRIVATE/'P_P_DECILES_OUTCOME_FREE.jsonl.gz',[{'entry_id':r['entry_id'],'session':r['session'],'block':r['block'],'pP_decile':deciles[r['entry_id']]} for r in scores])
    save(OUT/'ZERO_FIT_BASELINE_FREEZE.json',{'exact_jst':now(),'baseline_sha256':sha(OUT/'ZERO_FIT_BASELINE.json'),
        'deciles_sha256':sha(PRIVATE/'P_P_DECILES_OUTCOME_FREE.jsonl.gz'),'saved_score_sha256':sha(PRIVATE/'COMMON_SAVED_SCORES.jsonl.gz'),
        'teachers_sha256':sha(PRIVATE/'QUALITY_TEACHERS_EVAL.jsonl.gz'),'new_fits':0})
    checkpoint('Q4_ZERO_FIT_BASELINE','COMPLETE',['A0 CORE_H2, A1 CORE_H3, A2 pP, A3 legacy ML on exact common1028',
        'Top10/20/30/40 and outcome-free pP deciles frozen before new fits'],
        {'N':len(data),'new_fits':0,'baseline_sha256':sha(OUT/'ZERO_FIT_BASELINE.json')},'Q5 fit claims and trainer code pin before executing8 fits per new head')
    print({s:{t:result['metrics'][s][t] for t in ['U2','U3']} for s in result['metrics']})

if __name__=='__main__':main()
