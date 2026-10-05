"""Evaluation teachers are projected into past-only fit labels; runtime never reads them."""
from control import *
from bisect import bisect_right
from statistics import median
from math import isfinite
from metrics import summary,SCORES
BOUNDS=[.01,.02,.03,.04,.05,.10]
def eligible(t):return t.get('capture_complete') is True and t.get('strictly_after_entry_before_1520') is True and all(t.get(k) is not None and isfinite(t[k]) for k in ('potential_return','realized_net_return'))
def main():
    assert (WORK/'publication_receipts/R0_R3_SOURCE_NEGATIVE_AND_ALL_PRECOMMITS_BEFORE_TEACHERS_ACTUAL_GET.json').exists()
    save(PRIVATE/'claims/R4_TEACHER_CONTROLS_STARTED.json',{'exact_jst':now(),'basis':read(WORK/'latest_basis.json'),'reexecution_allowed':False})
    causal=rows(MAIN/'inputs/movement/RUNTIME_CAUSAL.jsonl.gz');tt={r['entry_id']:r for r in rows(MAIN/'inputs/evaluation/TEACHERS_EVALUATION.jsonl.gz')}
    current={r['entry_id']:r for r in rows(V10/'private/CURRENT_SIZING_RUNTIME.jsonl.gz')};mask={r['entry_id'] for r in rows(MAIN/'private/COMMON_EVAL_MASK.jsonl.gz') if r['included']}
    funded={r['entry_id'] for r in rows(V9/'private'/f'{I2}_TRADES.jsonl.gz')};tables=[];evaluation=[];exclusions=[]
    for block in read(SPLIT)['blocks']:
        b=block['block'];past=set(block['train']);test=set(block['test']);assert max(past)<min(test)
        train=[r for r in causal if r['session'] in past and r['entry_minute']<920 and eligible(tt[r['entry_id']])]
        gg={k:[] for k in range(7)}
        for r in train:
            t=tt[r['entry_id']];gg[bisect_right(BOUNDS,t['potential_return'])].append(t['realized_net_return'])
        assert all(len(v)>=10 for v in gg.values()),'MRET_TEACHER_SUPPORT_BLOCKED'
        med={k:median(v) for k,v in gg.items()};labels=[]
        for r in train:
            t=tt[r['entry_id']];k=bisect_right(BOUNDS,t['potential_return'])
            labels.append({'entry_id':r['entry_id'],'session':r['session'],'label':int(t['realized_net_return']>med[k])})
        gzsave(PRIVATE/f'train_labels/MRET_BLOCK_{b:02d}_PAST_ONLY.jsonl.gz',labels)
        blocktable={'block':b,'train_session_N':len(past),'train_through':max(past),'test_sessions':block['test'],'train_N':len(train),'train_positive_N':sum(r['label'] for r in labels),'buckets':{str(k):{'support':len(gg[k]),'median_realized':med[k],'exact_tie_N':sum(x==med[k] for x in gg[k]),'positive_N':sum(x>med[k] for x in gg[k])} for k in range(7)},'missing_realized_excluded_N':sum(tt[r['entry_id']].get('realized_net_return') is None for r in causal if r['session'] in past and r['entry_minute']<920),'potential_incomplete_excluded_N':sum(not tt[r['entry_id']].get('capture_complete',False) for r in causal if r['session'] in past and r['entry_minute']<920)}
        tables.append(blocktable)
        for r in causal:
            if r['session'] not in test:continue
            t=tt[r['entry_id']]
            if r['entry_id'] not in mask or not eligible(t):
                exclusions.append({'entry_id':r['entry_id'],'common_supported':r['entry_id'] in mask,'missing_realized':t.get('realized_net_return') is None,'potential_complete':t.get('capture_complete',False)});continue
            k=bisect_right(BOUNDS,t['potential_return']);c=current[r['entry_id']]
            evaluation.append({'entry_id':r['entry_id'],'session':r['session'],'block':b,'bucket':k,'potential':t['potential_return'],'realized':t['realized_net_return'],'median':med[k],'label':int(t['realized_net_return']>med[k]),'exact_tie':t['realized_net_return']==med[k],'pP':c['pP'],'q2':c['q2'],'q3':c['q3'],'consensus':c['consensus_weight'],'admitted':c['band'] in ('P_HIGH','P_MID','P_BASE'),'I2_funded':r['entry_id'] in funded})
    assert len(evaluation)==len({r['entry_id'] for r in evaluation})
    gzsave(PRIVATE/'MRET_EVALUATION_ROWS.jsonl.gz',evaluation);gzsave(PRIVATE/'MRET_EVALUATION_EXCLUSIONS.jsonl.gz',exclusions)
    save(OUT/'MRET_TEACHER_RESULT.json',{'status':'PASS','blocks':tables,'OOF_evaluable_N':len(evaluation),'OOF_positive_N':sum(r['label'] for r in evaluation),'OOF_exact_tie_N':sum(r['exact_tie'] for r in evaluation),'OOF_excluded_N':len(exclusions),'minimum_support':min(x['support'] for r in tables for x in r['buckets'].values()),'heldout_teacher_to_trainer':False,'backoff_merge':False,'Safety':SAFETY})
    controls={s:summary(evaluation,s) for s in SCORES};best=max(SCORES,key=lambda s:controls[s]['MRET']['AUC'])
    save(OUT/'ZERO_FIT_MRET_CONTROL_RESULT.json',{'controls':controls,'best_existing_control':best,'rule':'MRET target AUC maximum, C0-C3 tie order','newFits':0,'same_population':True,'HF1_HL0_refits':0})
    save(PRIVATE/'claims/R4_TEACHER_CONTROLS_COMPLETE.json',{'exact_jst':now(),'OOF_N':len(evaluation),'teacher_sha256':sha(PRIVATE/'MRET_EVALUATION_ROWS.jsonl.gz'),'newFits':0})
    checkpoint('R4_MRET_TEACHER_BUILD_AND_ZERO_FIT_CONTROLS',{'teacher':'PASS','OOF_N':len(evaluation),'best_existing_control':best},'R5 fit claim commit -> actual GET -> eight one-shot fits')
    print(json.dumps({'OOF_N':len(evaluation),'minimum_bucket_support':min(x['support'] for r in tables for x in r['buckets'].values()),'best_control':best,'controls_AUC':{s:controls[s]['MRET']['AUC'] for s in SCORES}}))
if __name__=='__main__':main()
